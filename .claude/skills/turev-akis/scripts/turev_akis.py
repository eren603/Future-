#!/usr/bin/env python3
"""Türev-akış motoru — perp türev verisinden yönsel erken-uyarı skoru.

Sorun (bu motorun var oluş sebebi): karar-motoru YALNIZ kline görür; OI,
funding, CVD, taker LSR, likidasyon kaskadı gibi türev kanallarına KÖRDÜR
(engine/README.md "bilinen sınırlar"). Bu veriler bugüne kadar yalnız
sözel yorum olarak kurula giriyordu — hiçbir mekanik motora bağlı değildi.
Bu motor onları SAYISAL bir yön skoruna çevirir; kurul artık lafla değil
ölçülen sinyalle beslenir.

Girdi JSON (CoinGlass/borsa panelinden okunan değerler; eksik alan "VERİ YOK"):
{
  "price_series": [66711, 66500, 66044, 65505, 65890],  # OI ile HİZALI kronolojik fiyat
  "oi_series":    [107.3, 106.1, 104.3, 103.0, 102.5],   # Açık Faiz (K BTC ya da $)
  "funding": 0.0025,          # % (Binance 8h funding, panelde gösterilen)
  "cvd_series":   [12.5, 13.1, 11.0, 15.3],              # Kümülatif Hacim Deltası
  "taker_lsr": 0.7988,        # Aggregated Long/Short Ratio (Taker Buy/Sell)
  "liq_long": 1.0,            # son pencere long likidasyon ($M)
  "liq_short": 8.6,           # son pencere short likidasyon ($M)
  "params": { ... }           # opsiyonel eşik override (varsayım etiketlenir)
}

Çıktı: yön skoru [-1,+1] (negatif=ayı baskısı), rejim etiketi, faktör dökümü,
erken-uyarı bayrakları, güven ve AÇIK varsayım defteri. Determinist.

Dürüstlük: bu motor geleceği bilmez; yalnız ŞU AN gözden kaçan türev verisini
karara dahil eder. Kanıtsız hiçbir sayı üretmez; eksik girdi skoru VERİ YOK'a
çeker (fail-closed). Canlı/otomatik emir DAHİL DEĞİL.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


class TurevError(Exception):
    pass


# Eşik KONVANSİYONLARI (piyasa parametresi değil; çıktıda 'varsayimlar'da raporlanır).
# Funding: Binance perp 8h; |f| bu eşiği aşarsa "kalabalık" sayılır (contrarian).
KONVANSIYON = {
    # Funding eşikleri (Binance 8h perp). ÖNEMLİ: Binance'in taban/nötr fonlaması
    # ~%0.01/8h'tir (yıllık ~%10.95 faiz bileşeni) — bu KALABALIK değil, normaldir.
    # Eski eşik 0.01 + ">=" bu tabanı "aşırı-long contrarian AYI" işaretliyordu →
    # sistematik aşağı yanlılık. Kalabalık/aşırı funding piyasa konvansiyonunda
    # ~%0.05/8h ve üstüdür; taban ~%0.01 ve altı soğuk/nötrdür.
    "funding_asiri": 0.05,        # % — üstü aşırı-long (contrarian ayı), altı-negatif aşırı-short
    "funding_ilimli": 0.01,       # % — |f| bunun altı "soğuk/nötr" (Binance taban fonlaması)
    "oi_delta_min": 0.005,        # OI serisinin göreli değişimi bu eşiği aşmalı (gürültü filtresi)
    "cvd_delta_min": 0.0,         # CVD yönü işareti (>0 alıcı)
    "lsr_ust": 1.05, "lsr_alt": 0.95,   # taker LSR nötr bandı
    "liq_orani": 2.0,             # bir taraf diğerinin bu katıysa kaskad sinyali
    # Faktör ağırlıkları (toplam 1.0) — OI/fiyat matrisi en ağır (erken-uyarının kalbi)
    "w_oi": 0.34, "w_funding": 0.18, "w_cvd": 0.18, "w_lsr": 0.15, "w_liq": 0.15,
    # to_advisor eşleme eşikleri (tek-kaynak; gizli sabit yok — deftere yazılır)
    "stance_esigi": 0.2,          # |yon_skoru| bunun altı → flat (kararsız)
    "kapsam_esigi": 0.5,          # okunan kapsam bunun altı → doğrulanmamış (fail-closed)
    # Faktör skor büyüklükleri (yön işareti kanıttan; büyüklük konvansiyon).
    # Deftere yazılır: OI/fiyat ±1.0 (taze giriş) / ±0.6 (deleveraging) / +0.4 (zayıf),
    # funding ±1.0 (aşırı) / ±0.3 (ılımlı), CVD ±0.7, LSR ±0.5, likidasyon ±0.8.
    "mag_oi_taze": 1.0, "mag_oi_delev": 0.6, "mag_oi_zayif": 0.4,
    "mag_funding_asiri": 1.0, "mag_funding_ilimli": 0.3,
    "mag_cvd": 0.7, "mag_lsr": 0.5, "mag_liq": 0.8,
}


def varsayim_defteri(extra=None):
    k = KONVANSIYON
    d = [
        f"funding aşırı eşiği=%{k['funding_asiri']} / ılımlı=%{k['funding_ilimli']} (Binance 8h perp konvansiyonu)",
        f"OI göreli değişim gürültü filtresi={k['oi_delta_min']} (|Δ| altı = yatay sayılır)",
        f"taker LSR nötr bandı=[{k['lsr_alt']},{k['lsr_ust']}]",
        f"likidasyon kaskad oranı={k['liq_orani']}x (bir taraf diğerinin katı; tek-taraflı kaskad dahil)",
        f"ağırlıklar OI/funding/CVD/LSR/liq = {k['w_oi']}/{k['w_funding']}/{k['w_cvd']}/{k['w_lsr']}/{k['w_liq']}",
        (f"faktör skor büyüklükleri (yön işareti kanıttan, büyüklük konvansiyon): "
         f"OI taze=±{k['mag_oi_taze']}/deleveraging=∓{k['mag_oi_delev']}/zayıf=+{k['mag_oi_zayif']}, "
         f"funding aşırı=±{k['mag_funding_asiri']}/ılımlı=±{k['mag_funding_ilimli']}, "
         f"CVD=±{k['mag_cvd']}, LSR=±{k['mag_lsr']}, likidasyon=±{k['mag_liq']}"),
        (f"danışman eşleme eşikleri: stance |skor|≥{k['stance_esigi']} yön verir, "
         f"okunan kapsam≥{k['kapsam_esigi']} doğrulanmış sayılır (altı fail-closed çürütme)"),
        "Bu skor türev verisini KARARA DAHİL EDER; geleceği bilmez, garanti vermez.",
    ]
    return d + list(extra or [])


def _rel_change(series):
    """Serinin baştan sona göreli değişimi; <2 nokta → None (VERİ YOK)."""
    s = [float(x) for x in series if x is not None]
    if len(s) < 2 or s[0] == 0:
        return None
    return (s[-1] - s[0]) / abs(s[0])


def _oi_price_signal(oi_series, price_series, p):
    """OI/fiyat matrisi — türev erken-uyarısının kalbi.
    up/up=sağlıklı trend(+), up/down=taze short(−), down/up=short kapama zayıf(+ hafif),
    down/down=long tasfiyesi/deleveraging(−)."""
    if not oi_series or not price_series:
        return None, "VERİ YOK (OI veya fiyat serisi eksik)"
    doi = _rel_change(oi_series)
    dpx = _rel_change(price_series)
    if doi is None or dpx is None:
        return None, "VERİ YOK (seri <2 nokta)"
    thr = p["oi_delta_min"]
    oi_up = doi > thr
    oi_dn = doi < -thr
    px_up = dpx > 0
    if not oi_up and not oi_dn:
        return 0.0, f"OI yatay (Δ%{doi*100:.2f}) → türev-yönsüz"
    if oi_up and px_up:
        return +p["mag_oi_taze"], f"OI↑%{doi*100:.2f} + fiyat↑ → taze LONG / sağlıklı trend (boğa)"
    if oi_up and not px_up:
        return -p["mag_oi_taze"], f"OI↑%{doi*100:.2f} + fiyat↓ → taze SHORT giriyor (ayı baskısı)"
    if oi_dn and px_up:
        return +p["mag_oi_zayif"], f"OI↓%{doi*100:.2f} + fiyat↑ → short kapama (zayıf boğa, konviksiyonsuz)"
    # oi_dn and price down
    return -p["mag_oi_delev"], f"OI↓%{doi*100:.2f} + fiyat↓ → long tasfiyesi / deleveraging (ayı, ama dip-tükenme olabilir)"


def _funding_signal(funding, p):
    if funding is None:
        return None, "VERİ YOK (funding)"
    f = float(funding)
    if f >= p["funding_asiri"]:
        return -p["mag_funding_asiri"], f"funding %{f} ≥ %{p['funding_asiri']} → aşırı-long kalabalık (contrarian AYI)"
    if f <= -p["funding_asiri"]:
        return +p["mag_funding_asiri"], f"funding %{f} ≤ -%{p['funding_asiri']} → aşırı-short kalabalık (contrarian BOĞA)"
    if abs(f) <= p["funding_ilimli"]:
        return 0.0, f"funding %{f} soğuk/nötr (|f| ≤ %{p['funding_ilimli']}) → kaldıraç iştahı düşük"
    # ılımlı pozitif/negatif: hafif contrarian
    return (-p["mag_funding_ilimli"] if f > 0 else +p["mag_funding_ilimli"]), f"funding %{f} ılımlı → hafif contrarian eğilim"


def _cvd_signal(cvd_series, p):
    if not cvd_series:
        return None, "VERİ YOK (CVD)"
    d = _rel_change(cvd_series)
    if d is None:
        return None, "VERİ YOK (CVD serisi <2 nokta)"
    if d > p["cvd_delta_min"]:
        return +p["mag_cvd"], f"CVD↑ (Δ%{d*100:.1f}) → net alıcı emici (boğa)"
    if d < -p["cvd_delta_min"]:
        return -p["mag_cvd"], f"CVD↓ (Δ%{d*100:.1f}) → net satıcı (ayı)"
    return 0.0, "CVD yatay"


def _lsr_signal(taker_lsr, p):
    if taker_lsr is None:
        return None, "VERİ YOK (taker LSR)"
    r = float(taker_lsr)
    # Taker LSR: >1 takerlar net ALICI. Ama aşırı kalabalık contrarian okunur.
    # Basit yön: bandın içinde nötr; üstü boğa, altı ayı — ama momentum sinyali olarak.
    if r > p["lsr_ust"]:
        return +p["mag_lsr"], f"taker LSR {r} > {p['lsr_ust']} → takerlar net alıcı (momentum boğa)"
    if r < p["lsr_alt"]:
        return -p["mag_lsr"], f"taker LSR {r} < {p['lsr_alt']} → takerlar net satıcı (momentum ayı)"
    return 0.0, f"taker LSR {r} nötr bandda"


def _liq_signal(liq_long, liq_short, p):
    if liq_long is None or liq_short is None:
        return None, "VERİ YOK (likidasyon)"
    ll, ls = abs(float(liq_long)), abs(float(liq_short))
    if ll == 0 and ls == 0:
        return 0.0, "likidasyon yok"
    # Long tasfiyesi baskın → aşağı kaskad (ayı); short tasfiyesi baskın → yukarı squeeze (boğa).
    # NOT: bir taraf tam 0 olan TEK-TARAFLI kaskad en güçlü sinyaldir; eski `ls>0`/`ll>0`
    # bekçileri bu durumu "dengeli" 0.0'a düşürüp motoru tam gerektiğinde susturuyordu.
    # max(...,1e-9) sıfıra-bölmeyi zaten engellediği için bekçiler kaldırıldı.
    if ll >= p["liq_orani"] * max(ls, 1e-9):
        return -p["mag_liq"], f"long likidasyon {ll} >> short {ls} → aşağı kaskad (ayı)"
    if ls >= p["liq_orani"] * max(ll, 1e-9):
        return +p["mag_liq"], f"short likidasyon {ls} >> long {ll} → yukarı squeeze (boğa)"
    return 0.0, f"likidasyon dengeli (long {ll} / short {ls})"


def analyze(job: dict) -> dict:
    p = {**KONVANSIYON, **(job.get("params") or {})}
    factors = []
    weighted_sum = 0.0
    weight_used = 0.0
    warnings = []

    parts = [
        ("oi_price", p["w_oi"], _oi_price_signal(job.get("oi_series"), job.get("price_series"), p)),
        ("funding", p["w_funding"], _funding_signal(job.get("funding"), p)),
        ("cvd", p["w_cvd"], _cvd_signal(job.get("cvd_series"), p)),
        ("taker_lsr", p["w_lsr"], _lsr_signal(job.get("taker_lsr"), p)),
        ("liquidation", p["w_liq"], _liq_signal(job.get("liq_long"), job.get("liq_short"), p)),
    ]
    for name, w, (score, note) in parts:
        entry = {"faktor": name, "agirlik": w, "skor": score, "aciklama": note}
        factors.append(entry)
        if score is not None:
            weighted_sum += w * score
            weight_used += w

    if weight_used == 0:
        return {
            "KARAR_TUREV": "VERİ YOK",
            "yon_skoru": None,
            "guven": 0.0,
            "faktorler": factors,
            "erken_uyari": ["Hiçbir türev alanı okunamadı — fail-closed."],
            "esik_kaynagi": "tasarım varsayımı (fail-closed)",
            "varsayimlar": varsayim_defteri(),
            "not": "Karar-destek; türev verisi eksik → yön üretilmedi. Canlı emir DAHİL DEĞİL.",
        }

    # Eksik faktör varsa ağırlığı yeniden normalize et (körü körüne 0 sayma)
    score = weighted_sum / weight_used
    kapsam = weight_used  # okunabilen ağırlık toplamı (1.0 = tüm alanlar geldi)

    if score <= -0.5:
        etiket = "AYI baskısı (güçlü)"
    elif score <= -0.2:
        etiket = "AYI eğilimli"
    elif score < 0.2:
        etiket = "NÖTR / karışık"
    elif score < 0.5:
        etiket = "BOĞA eğilimli"
    else:
        etiket = "BOĞA baskısı (güçlü)"

    # Erken-uyarı bayrakları (kural tabanlı, en kritik kombinasyonlar)
    doi = _rel_change(job.get("oi_series") or [])
    dpx = _rel_change(job.get("price_series") or [])
    if doi is not None and dpx is not None:
        if doi < -p["oi_delta_min"] and dpx < 0:
            warnings.append("DELEVERAGING: OI↓ + fiyat↓ — long tasfiyesi sürüyor; trend zayıf, dip-tükenme veya devam riski.")
        if doi > p["oi_delta_min"] and dpx < 0:
            warnings.append("TAZE SHORT: OI↑ + fiyat↓ — yeni satıcı parası; düşüş konviksiyonlu.")
    fnd = job.get("funding")
    if fnd is not None and abs(float(fnd)) <= p["funding_ilimli"] and doi is not None and doi < 0:
        warnings.append("SOĞUMA: funding nötr + OI düşüyor — kaldıraç boşalıyor, momentum sönük (kenar zayıf).")

    # Güven: okunan kapsam × sinyal netliği
    guven = round(min(1.0, kapsam) * min(1.0, abs(score) + 0.2), 4)

    return {
        "KARAR_TUREV": etiket,
        "yon_skoru": round(score, 4),
        "kapsam": round(kapsam, 4),
        "guven": guven,
        "faktorler": factors,
        "erken_uyari": warnings or ["Kritik erken-uyarı kombinasyonu yok."],
        "esik_kaynagi": "eşikler istatistik/piyasa konvansiyonu (varsayimlar defterinde açık; gizli sabit yok)",
        "varsayimlar": varsayim_defteri(
            [f"okunan kapsam={round(kapsam,2)} (1.0=tüm türev alanları geldi; eksikse ağırlık yeniden normalize edildi)"]),
        "not": ("Karar-destek çıktısıdır — türev verisini KARARA DAHİL EDER, kesinlik/sinyal değil. "
                "Geleceği bilmez. Canlı/otomatik emir DAHİL DEĞİL."),
    }


def to_advisor(result: dict, p: dict | None = None) -> dict | None:
    """Motor çıktısını karar-kurulu danışmanına ÇEVİRİR (öznel yorum devreden çıkar).

    Eşleme kuralı (deterministik; eşikler KONVANSIYON'dan tek-kaynak, params ile ezilebilir):
      - stance: |yon_skoru| ≥ stance_esigi → long/short ; arası → flat
      - confidence: motorun `guven` alanı (kapsam × sinyal netliği)
      - evidence: KARAR_TUREV + faktör dökümü + erken-uyarılar
      - _verifier_confirmed: kapsam ≥ kapsam_esigi ise true (yetersiz veri → çürütme penaltısı)
    VERİ YOK ise None döner → kurula danışman EKLENMEZ (fail-closed).
    """
    p = p or KONVANSIYON
    if result.get("KARAR_TUREV") == "VERİ YOK" or result.get("yon_skoru") is None:
        return None
    score = float(result["yon_skoru"])
    if score >= p["stance_esigi"]:
        stance = "long"
    elif score <= -p["stance_esigi"]:
        stance = "short"
    else:
        stance = "flat"
    fac = [f"{f['faktor']}={f['skor']}" for f in result.get("faktorler", [])
           if f.get("skor") is not None]
    uy = [w for w in result.get("erken_uyari", []) if "yok" not in w.lower()]
    ev = (f"Türev motoru: {result['KARAR_TUREV']} (skor {score}, kapsam "
          f"{result.get('kapsam')}). Faktörler: {', '.join(fac)}. "
          + (("Erken-uyarı: " + " | ".join(uy)) if uy else "Kritik erken-uyarı yok."))
    return {
        "name": "turev-akis",
        "stance": stance,
        "confidence": float(result.get("guven", 0.3)),
        "evidence": ev,
        "_verifier_confirmed": bool((result.get("kapsam") or 0.0) >= p["kapsam_esigi"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Türev-akış motoru (OI/funding/CVD/LSR/likidasyon → yön skoru)")
    ap.add_argument("--job", required=True, help="JSON job dosyası")
    ap.add_argument("--emit-advisor", action="store_true",
                    help="Çıktıyı karar-kurulu danışman formatında ver (stance/confidence/evidence + _verifier_confirmed)")
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    result = analyze(job)
    if args.emit_advisor:
        adv = to_advisor(result, {**KONVANSIYON, **(job.get("params") or {})})
        print(json.dumps(adv, ensure_ascii=False, indent=2) if adv is not None
              else json.dumps({"danisman": None, "neden": "VERİ YOK — kurula eklenmez"}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
