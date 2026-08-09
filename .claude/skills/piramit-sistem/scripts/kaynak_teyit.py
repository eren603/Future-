#!/usr/bin/env python3
"""Bağlayıcı kaynak-teyidi — bağımsız borsadan çekilen veriyle kline çapraz sınavı.

Neden var: paketteki Binance kline'ı tek kaynaktır; kullanıcı "bağlayıcı
teyidini her koşuda otomatik yap" dedi (2026-08-09). Bu ortamda dış borsa
API'sine kancadan erişim YOK (api.crypto.com CONNECT 403 — proxy engeli);
çekimi yalnız Claude MCP bağlayıcısıyla yapabilir. Bu betik o çekimin HAM
dökümünü alır ve karşılaştırmayı MEKANİK yapar — elle takdir edilen sayı yok.

Girdi (--ham): Claude'un MCP sonucundan OLDUĞU GİBİ yazdığı JSON:
{
  "kaynak": "Crypto.com Exchange (MCP bağlayıcısı)",
  "zaman_utc": "2026-08-09 20:20",
  "BTCUSDT": {"ticker": {"last","high","low",...},
               "candles": [{"timestamp":"...Z","open","high","low","close"},...]},
  "ETHUSDT": {...}
}

Ölçümler (sembol başına):
  1. Kapanmış ortak barların kapanış sapması (en yeni ≤8 bar; iki tarafın da
     SON barı canlı olabileceği için dışlanır).
  2. 24S uçlar: bizim son-96-bar max/min ↔ bağlayıcı ticker high/low.
  3. Paket-sonrası sürüklenme: bağlayıcıda bizim son barımızdan YENİ barlar
     varsa son kapanışın yönü (BİLGİ — skorlanmaz).
Hüküm: BAYAT / VERİ YOK / UYUM / ÇELİŞKİ (fail-closed: tazelik ya da kesişim
yetersizse UYUM denmez). Eşik borsalar-arası baz payı KONVANSİYONUDUR
(kalibre edilmemiş) ve varsayım defterine yazılır.

⚠ Teyit bir KARAR girdisi değildir: motor kararına geri beslenmez (dairesel
kanıt yasak); yalnız veri bütünlüğü sınavıdır ve çıktıda gösterilir.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ESIK_PCT = 0.15          # borsalar-arası baz payı (KONVANSİYON — varsayım defterinde)
TAZELIK_DK = 240         # panel tazelik kuralıyla aynı pencere (gorev.json kadans)
MIN_ORTAK_BAR = 3        # kesişim bundan azsa hüküm VERİ YOK (fail-closed)
MAX_BAR = 8              # en yeni bu kadar kapanmış ortak bar karşılaştırılır

VARSAYIMLAR = [
    f"uyum eşiği |Δ%| ≤ {ESIK_PCT} borsalar-arası baz KONVANSİYONUDUR (kalibre edilmemiş)",
    f"tazelik penceresi {TAZELIK_DK} dk — panel/likidasyon kuralıyla aynı",
    "farklı borsaların perp defterleri birebir eşit OLAMAZ; sınanan şey bar-bar tutarlı küçük baz",
    "teyit karara geri beslenmez (dairesel kanıt yasak) — yalnız veri bütünlüğü sınavı",
]


def _ham_ms(z: str) -> int | None:
    """'YYYY-MM-DD HH:MM' → epoch ms (UTC); bozuksa None (uydurulmaz)."""
    try:
        return int(dt.datetime.strptime(z.strip(), "%Y-%m-%d %H:%M")
                   .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    except (ValueError, AttributeError):
        return None


def _iso_ms(z: str) -> int | None:
    try:
        return int(dt.datetime.fromisoformat(z.replace("Z", "+00:00"))
                   .timestamp() * 1000)
    except (ValueError, AttributeError):
        return None


def _utc(ms: int) -> str:
    return dt.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")


def sembol_teyit(kline: list, cc: dict, ham_ms: int | None) -> dict:
    """Tek sembolün mekanik teyidi; dönen sözlükte HUKUM + ölçümler."""
    if not kline:
        return {"HUKUM": "VERİ YOK", "neden": "kline boş"}
    son_ms = int(kline[-1][0])
    r: dict = {"son_bar_utc": _utc(son_ms), "son_bar_ms": son_ms}

    # Tazelik: çekim damgası son bardan TAZELIK_DK'dan eskiyse hüküm verilmez.
    if ham_ms is None:
        return {**r, "HUKUM": "VERİ YOK", "neden": "ham dökümde zaman_utc yok/bozuk"}
    if son_ms - ham_ms > TAZELIK_DK * 60 * 1000:
        return {**r, "HUKUM": "BAYAT",
                "neden": f"çekim son bardan {int((son_ms - ham_ms) / 60000)} dk eski "
                         f"(tolerans {TAZELIK_DK} dk)"}

    mumlar = {m: kapanis for m, kapanis in (
        (_iso_ms(c.get("timestamp", "")), c.get("close"))
        for c in (cc.get("candles") or [])) if m is not None and kapanis is not None}
    if not mumlar:
        return {**r, "HUKUM": "VERİ YOK", "neden": "bağlayıcı mumu yok"}

    cc_son = max(mumlar)
    bizim = {int(b[0]): float(b[4]) for b in kline}
    # İki tarafın da son barı canlı olabilir → kapanmış kesişim.
    ortak = sorted((m for m in mumlar if m in bizim and m < son_ms and m < cc_son),
                   reverse=True)[:MAX_BAR]
    barlar = [{"bar_utc": _utc(m), "binance": bizim[m], "cc": float(mumlar[m]),
               "sapma_pct": round((bizim[m] - float(mumlar[m])) / bizim[m] * 100, 4)}
              for m in ortak]

    # 24S uçlar (bizim son 96 bar ↔ ticker).
    son96 = kline[-96:]
    t = cc.get("ticker") or {}
    uclar = {}
    try:
        b_max, b_min = max(float(b[2]) for b in son96), min(float(b[3]) for b in son96)
        c_max, c_min = float(t["high"]), float(t["low"])
        uclar = {"binance_max": b_max, "cc_max": c_max,
                 "max_sapma_pct": round((b_max - c_max) / b_max * 100, 4),
                 "binance_min": b_min, "cc_min": c_min,
                 "min_sapma_pct": round((b_min - c_min) / b_min * 100, 4)}
    except (KeyError, ValueError, TypeError):
        uclar = {"durum": "VERİ YOK — ticker high/low okunamadı"}

    # Paket-sonrası sürüklenme (BİLGİ — skorlanmaz, karara girmez).
    yeni = sorted(m for m in mumlar if m > son_ms)
    if yeni:
        son_cc = float(mumlar[yeni[-1]])
        fark = son_cc - bizim[son_ms]
        r["paket_sonrasi"] = {
            "yeni_bar": len(yeni), "cc_son_kapanis": son_cc,
            "bizim_son_kapanis": bizim[son_ms],
            "yon": "aşağı" if fark < 0 else ("yukarı" if fark > 0 else "yatay"),
            "not": "bilgi — borsalar arası baz içerir, skorlanmaz"}

    r["barlar"] = barlar
    r["uclar"] = uclar
    if len(barlar) < MIN_ORTAK_BAR:
        return {**r, "HUKUM": "VERİ YOK",
                "neden": f"kapanmış ortak bar {len(barlar)} < {MIN_ORTAK_BAR}"}

    sapmalar = [abs(b["sapma_pct"]) for b in barlar]
    for ad in ("max_sapma_pct", "min_sapma_pct"):
        if ad in uclar:
            sapmalar.append(abs(uclar[ad]))
    r["max_sapma_pct"] = max(sapmalar)
    r["ortalama_baz_pct"] = round(sum(b["sapma_pct"] for b in barlar) / len(barlar), 4)
    r["HUKUM"] = "UYUM" if r["max_sapma_pct"] <= ESIK_PCT else "ÇELİŞKİ"
    if r["HUKUM"] == "ÇELİŞKİ":
        r["neden"] = (f"en büyük sapma %{r['max_sapma_pct']} > eşik %{ESIK_PCT} — "
                      "iki kaynak aynı piyasayı anlatmıyor; veri şüphesi ÇIKTIDA gösterilir")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ham", required=True)
    ap.add_argument("--m15", default="engine/girdi/m15.json")
    ap.add_argument("--eth-m15", default="engine/girdi/eth/m15.json")
    ap.add_argument("--out", default="engine/state/kaynak_teyit.json")
    a = ap.parse_args()

    try:
        ham = json.loads(Path(a.ham).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"kaynak_teyit: ham döküm okunamadı ({e}) — teyit YAPILAMADI (fail-closed)")
        return 2
    ham_ms = _ham_ms(str(ham.get("zaman_utc", "")))

    rapor = {"kaynak": ham.get("kaynak", "VERİ YOK"),
             "cekim_utc": ham.get("zaman_utc", "VERİ YOK"),
             "esik_pct": ESIK_PCT, "varsayimlar": VARSAYIMLAR, "semboller": {}}
    for sembol, yol in (("BTCUSDT", a.m15), ("ETHUSDT", a.eth_m15)):
        try:
            kline = json.loads(Path(yol).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            rapor["semboller"][sembol] = {"HUKUM": "VERİ YOK", "neden": f"{yol} okunamadı"}
            continue
        rapor["semboller"][sembol] = sembol_teyit(kline, ham.get(sembol) or {}, ham_ms)

    hukumler = [s.get("HUKUM") for s in rapor["semboller"].values()]
    rapor["HUKUM_GENEL"] = ("ÇELİŞKİ" if "ÇELİŞKİ" in hukumler else
                            "BAYAT" if "BAYAT" in hukumler else
                            "VERİ YOK" if "VERİ YOK" in hukumler else "UYUM")
    # Kancanın bastığı tek satır — sayılar bu rapordan, elle yazılmaz.
    parcalar = []
    for sembol, s in rapor["semboller"].items():
        if s.get("HUKUM") == "UYUM":
            ps = s.get("paket_sonrasi", {})
            parcalar.append(
                f"{sembol} UYUM (n={len(s['barlar'])} bar, maks sapma "
                f"%{s['max_sapma_pct']}, baz %{s['ortalama_baz_pct']}"
                + (f"; paket-sonrası {ps['yon']}" if ps else "") + ")")
        else:
            parcalar.append(f"{sembol} {s.get('HUKUM')} ({s.get('neden', '')})")
    rapor["ozet"] = (f"{rapor['kaynak']} @{rapor['cekim_utc']} → "
                     + " | ".join(parcalar))
    # Kanca bar eşleşmesini bununla yapar (ana sembol esas alınır).
    ana = rapor["semboller"].get("BTCUSDT", {})
    rapor["son_bar_ms"] = ana.get("son_bar_ms")
    rapor["son_bar_utc"] = ana.get("son_bar_utc")

    cikti = Path(a.out)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    tmp = cikti.with_suffix(".tmp")
    tmp.write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(cikti)
    print(rapor["ozet"])
    return 0 if rapor["HUKUM_GENEL"] == "UYUM" else 2


if __name__ == "__main__":
    sys.exit(main())
