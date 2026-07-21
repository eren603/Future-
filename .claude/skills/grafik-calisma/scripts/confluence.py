#!/usr/bin/env python3
"""Confluence motoru — yön + giriş/çıkış seviyesi hesaplama.

Fibonacci TEK BAŞINA yeterli değildir. Bu motor giriş bölgesini KATMAN
sırasına göre üretir:

    Bağlam(HTF) → yapı(SMC) → arz-talep(OB/FVG) → likidite → [fib] → onay → risk

Kural: güçlü giriş bölgesi = golden zone (0.618–0.786) + order block/FVG +
likidite AYNI noktada buluştuğunda (confluence). Yalnız fib → confluence
eksik → NÖTR-BEKLE (fail-closed).

Girdi JSON:
{
  "structure": {"event": "CHoCH"|"BOS", "direction": "bull"|"bear"},
  "impulse":   {"start": 100.0, "end": 120.0},   # start→end = impuls bacağı
  "htf_bias":  "bull"|"bear"|null,                # üst zaman dilimi yönü (ops.)
  "order_blocks": [{"low":104,"high":106,"type":"demand"}],   # demand|supply
  "fvgs":         [{"low":104.5,"high":105.5,"type":"bull"}], # bull|bear
  "liquidity":    [{"price":125,"type":"buyside"},{"price":95,"type":"sellside"}],
  "thresholds": {"min_confluence":0.5,"min_rr":2.0,"sl_buffer_frac":0.05}
}

Determinist — rastgelelik yok. Uydurma yok: seviyeler yalnız verilen
girdiden hesaplanır; eksik girdi kararı BEKLE'ye çeker (fail-closed).
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Golden zone (OTE) sınırları
GZ_LO, GZ_HI = 0.618, 0.786

# Confluence ağırlıkları (toplam 1.0)
W = {"structure": 0.30, "htf": 0.15, "ob": 0.25, "fvg": 0.15, "liquidity": 0.15}


class ConfluenceError(Exception):
    pass


def _overlap(a, b):
    """İki [lo,hi] aralığının kesişimi; yoksa None."""
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return [lo, hi] if lo <= hi else None


def _golden_zone(start: float, end: float):
    """İmpuls bacağından golden zone [lo, hi] (yönden bağımsız fiyat aralığı)."""
    rng = abs(end - start)
    if rng <= 0:
        raise ConfluenceError("impuls bacağı sıfır uzunlukta (start==end)")
    if end > start:            # yukarı impuls → long retracement (end'in altı)
        return [end - GZ_HI * rng, end - GZ_LO * rng], rng, "up"
    else:                      # aşağı impuls → short retracement (end'in üstü)
        return [end + GZ_LO * rng, end + GZ_HI * rng], rng, "down"


def synth(job: dict) -> dict:
    st = job.get("structure") or {}
    event = str(st.get("event", "")).upper()
    sdir = str(st.get("direction", "")).lower()
    if event not in {"CHOCH", "BOS"}:
        raise ConfluenceError("structure.event CHoCH|BOS olmalı")
    if sdir not in {"bull", "bear"}:
        raise ConfluenceError("structure.direction bull|bear olmalı")

    imp = job.get("impulse") or {}
    try:
        start, end = float(imp["start"]), float(imp["end"])
    except (KeyError, TypeError, ValueError):
        raise ConfluenceError("impulse.start ve impulse.end sayısal gerekli")

    th = job.get("thresholds", {})
    min_conf = float(th.get("min_confluence", 0.5))
    min_rr = float(th.get("min_rr", 2.0))
    sl_buf_frac = float(th.get("sl_buffer_frac", 0.05))

    gz, rng, imp_dir = _golden_zone(start, end)

    # --- KATMAN 2: yapı yönü ile impuls yönü tutarlı mı? (fail-closed) ---
    want = "up" if sdir == "bull" else "down"
    gates = []
    contradiction = (imp_dir != want)
    if contradiction:
        gates.append(f"yapı({sdir}) ile impuls({imp_dir}) çelişiyor")

    is_long = (sdir == "bull")
    score = W["structure"]
    factors = ["yapı(SMC): " + event + "/" + sdir]

    # --- KATMAN 1: HTF bias hizası ---
    htf = job.get("htf_bias")
    if htf and str(htf).lower() == sdir:
        score += W["htf"]; factors.append("HTF bias hizalı")

    # --- KATMAN 3: arz-talep bölgeleri golden zone ile çakışıyor mu? ---
    want_ob = "demand" if is_long else "supply"
    want_fvg = "bull" if is_long else "bear"
    overlaps = []   # golden zone ile kesişen bölgeler
    ob_hit = fvg_hit = False
    for ob in job.get("order_blocks", []) or []:
        if str(ob.get("type", "")).lower() != want_ob:
            continue
        ov = _overlap(gz, [float(ob["low"]), float(ob["high"])])
        if ov:
            ob_hit = True; overlaps.append(ov)
    for f in job.get("fvgs", []) or []:
        if str(f.get("type", "")).lower() != want_fvg:
            continue
        ov = _overlap(gz, [float(f["low"]), float(f["high"])])
        if ov:
            fvg_hit = True; overlaps.append(ov)
    if ob_hit:
        score += W["ob"]; factors.append("order block çakışması")
    if fvg_hit:
        score += W["fvg"]; factors.append("FVG çakışması")

    # --- KATMAN 4: likidite (hedef yönde havuz var mı?) ---
    liq = job.get("liquidity", []) or []
    if is_long:
        targets = sorted(float(l["price"]) for l in liq
                         if str(l.get("type", "")).lower() == "buyside"
                         and float(l["price"]) > gz[1])
    else:
        targets = sorted((float(l["price"]) for l in liq
                          if str(l.get("type", "")).lower() == "sellside"
                          and float(l["price"]) < gz[0]), reverse=True)
    if targets:
        score += W["liquidity"]; factors.append("likidite hedefi var")
    else:
        # fallback: impuls uç noktası (önceki swing) — likidite orada birikir
        targets = [end]
        factors.append("likidite girilmedi → impuls ucu hedef (varsayım)")

    score = round(min(score, 1.0), 4)

    # --- Giriş bölgesi: golden zone ∩ (OB/FVG). Çakışma yoksa yalnız golden. ---
    if overlaps:
        entry = [max(o[0] for o in overlaps), min(o[1] for o in overlaps)]
        if entry[0] > entry[1]:  # çoklu ayrık çakışma → en geniş tekli çakışma
            entry = max(overlaps, key=lambda o: o[1] - o[0])
    else:
        entry = gz[:]  # yalnız fib (confluence eksik → aşağıda kapıya takılır)
    entry_mid = (entry[0] + entry[1]) / 2.0

    # --- KATMAN 7: risk. Geçersizlik = impulsu başlatan swing ötesi (+tampon) ---
    buf = sl_buf_frac * rng
    if is_long:
        sl_ref = min([start] + [o[0] for o in overlaps])
        sl = sl_ref - buf
        t1 = targets[0]
        rr = (t1 - entry_mid) / (entry_mid - sl) if entry_mid > sl else 0.0
    else:
        sl_ref = max([start] + [o[1] for o in overlaps])
        sl = sl_ref + buf
        t1 = targets[0]
        rr = (entry_mid - t1) / (sl - entry_mid) if sl > entry_mid else 0.0
    rr = round(rr, 3)

    # --- KARAR KAPILARI (fail-closed) ---
    if not (ob_hit or fvg_hit):
        gates.append("confluence eksik: golden zone hiçbir OB/FVG ile çakışmıyor (yalnız fib)")
    if score < min_conf:
        gates.append(f"confluence skoru {score:.2f} < {min_conf}")
    if rr < min_rr:
        gates.append(f"R:R {rr:.2f} < {min_rr}")

    if gates:
        decision = "NÖTR-BEKLE"
    else:
        decision = "LONG" if is_long else "SHORT"

    return {
        "KARAR": decision,
        "yon_bias": sdir,
        "confluence_skoru": score,
        "confluence_faktorleri": factors,
        "golden_zone": [round(gz[0], 6), round(gz[1], 6)],
        "giris_bolgesi": [round(entry[0], 6), round(entry[1], 6)],
        "giris_orta": round(entry_mid, 6),
        "gecersizlik_sl": round(sl, 6),
        "hedefler": [round(t, 6) for t in targets[:2]],
        "rr": rr,
        "kapi_gerekceleri": gates,
        "katman_sirasi": "bağlam→yapı→arz-talep→likidite→fib→onay→risk",
        "not": ("Karar-destek; olasılık senaryosu, sinyal/garanti değil. "
                "Onay (alt-TF tetik) girişten önce beklenir. Canlı emir DAHİL DEĞİL."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Confluence giriş/çıkış motoru")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(synth(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
