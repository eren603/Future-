#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIYAS MOTORU — "önceki karar tuttu mu?" + "piyasa döndü mü?"

Her yeni veri geldiğinde, YENİ analizden ÖNCE iki soru cevaplanır:

  1. HESAP VERME (akıbet): Bir önceki koşuda verilen giriş/stop/hedef
     seviyeleri, o günden bu yana gelen barlarda ne oldu? Tetiklendi mi,
     stop mu oldu, hedefe mi gitti? Gerçekleşen R kaç?
     → Ölçüm `akibet_etiketle.simule_et` ile yapılır (aynı muhafazakâr
       kurallar: aleyhte kenardan dolum, aynı barda stop+hedef → STOP).

  2. KIYAS (rejim değişimi): Eski veri neyi gösteriyordu, yeni veri neyi
     gösteriyor? Yön DEVAM mı etti, DÖNDÜ mü? Hangi sürücü değişti —
     OI, funding, CVD, taker-LSR, likidasyon, trend, ADX, ATR?

Neden zorunlu: yön aynı kalsa bile SÜRÜCÜ değişmiş olabilir (ör. "short
devam" ama artık taze short girişi yok, sadece eski pozisyonlar kapanıyor).
Bu ayrım yeni kararın kalitesini belirler ve kıyas yapılmazsa görünmez.

Dürüstlük: önceki koşu kaydı yoksa `VERİ YOK` denir — geçmiş uydurulmaz.
Akıbet ölçülemiyorsa (bar yok/pencere dışı) nedeni yazılır. Determinist.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import akibet_etiketle as AE  # noqa: E402

YOK = "VERİ YOK"

# Sürücü kanalları: (etiket, önem eşiği, yön yorumu)
SURUCULER = {
    "trend": "yapı yönü", "adx": "trend gücü", "atr": "oynaklık",
    "turev_skor": "türev yön skoru", "turev_kapsam": "türev veri kapsamı",
    "funding": "fonlama", "lsr": "taker long/short", "cvd_delta": "CVD eğimi",
    "oi_delta": "açık faiz değişimi", "liq_long": "long likidasyon",
    "liq_short": "short likidasyon",
}
# Anlamlı değişim eşikleri (konvansiyon — çıktıda raporlanır)
KONVANSIYON = {"skor_esik": 0.15, "oran_esik": 0.10, "adx_esik": 3.0}


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# 1) AKIBET — önceki seviyeler tuttu mu?
# --------------------------------------------------------------------------
def akibet_olc(onceki: dict, barlar: list, p: dict | None = None) -> dict:
    """Önceki koşunun verdiği seviyeleri yeni barlarda ileriye simüle et."""
    p = {**AE.KONVANSIYON, **(p or {})}
    sev = (onceki or {}).get("islem_seviyeleri") or {}
    karar_zamani = (onceki or {}).get("son_bar")
    yon = str((onceki or {}).get("YON_BIAS", "")).lower()

    if not onceki:
        return {"durum": f"{YOK} — önceki koşu kaydı yok (ilk analiz)"}
    if not sev or _f(sev.get("giris")) is None:
        return {"durum": f"{YOK} — önceki koşuda işlem seviyesi verilmemişti "
                         f"(hüküm: {onceki.get('islem_kalitesi', YOK)})",
                "onceki_yon": onceki.get("YON_BIAS", YOK),
                "onceki_bar_utc": onceki.get("son_bar_utc", YOK)}
    if yon not in ("long", "short"):
        return {"durum": f"{YOK} — önceki yön long/short değil ({yon})"}

    karar = {"karar": yon.upper(), "yon": yon.upper(),
             "giris_alt": _f(sev.get("giris_alt")) or _f(sev["giris"]),
             "giris_ust": _f(sev.get("giris_ust")) or _f(sev["giris"]),
             "giris": _f(sev["giris"]), "stop": _f(sev.get("stop")),
             "t1": _f(sev.get("hedef")) or _f(sev.get("t1")),
             "iptal": _f(sev.get("iptal")) or _f(sev.get("stop"))}
    if karar["stop"] is None or karar["t1"] is None:
        return {"durum": f"{YOK} — stop/hedef eksik, akıbet ölçülemez"}
    # karar_zamani AE.simule_et içinde int()'e verilir (S1): kayıtta son_bar yok
    # ya da 'VERİ YOK' dizgesiyse TypeError/ValueError fırlar ve kıyas motoru
    # komple çökerdi (HESAP VERME raporu hiç üretilmezdi) — önce koru.
    if not isinstance(karar_zamani, (int, float)):
        return {"durum": f"{YOK} — önceki koşunun karar barı (son_bar) kayıtta "
                         "yok/sayısal değil, akıbet ölçülemez"}

    s = AE.simule_et(karar, karar_zamani, barlar, p)
    return {
        "durum": ("ÖLÇÜLDÜ" if s.get("olculebilir") else "ÖLÇÜLEMEDİ"),
        "sonuc": s.get("sonuc"), "gercek_r": s.get("r"),
        "onceki_yon": yon.upper(),
        "onceki_bar_utc": onceki.get("son_bar_utc", YOK),
        "verilen_seviyeler": {"giris": karar["giris"], "stop": karar["stop"],
                              "hedef": karar["t1"]},
        "ayrinti": {k: v for k, v in s.items()
                    if k not in ("olculebilir", "sonuc", "r")},
        "kural": ("dolum bölgenin aleyhte kenarından; aynı barda stop+hedef → "
                  "STOP; iptal gövde kapanışıyla (muhafazakâr)"),
    }


# --------------------------------------------------------------------------
# 2) KIYAS — piyasa döndü mü, hangi sürücü değişti?
# --------------------------------------------------------------------------
def _degisim_etiketi(onceki_yon: str, yeni_yon: str) -> tuple:
    o, y = str(onceki_yon).upper(), str(yeni_yon).upper()
    if o == y and o in ("LONG", "SHORT"):
        return "DEVAM", f"{o} yönü korundu"
    if {o, y} == {"LONG", "SHORT"}:
        return "DÖNÜŞ", f"{o} → {y}: piyasa yön DEĞİŞTİRDİ"
    if y == "NÖTR":
        return "NÖTRE ÇEKİLDİ", f"{o} → NÖTR: kanıt dengelendi"
    if o == "NÖTR":
        return "YÖN OLUŞTU", f"NÖTR → {y}: kanıt bir yöne kaydı"
    return "BELİRSİZ", f"{o} → {y}"


def kiyasla(onceki: dict, yeni: dict, p: dict | None = None) -> dict:
    """İki koşu anlık görüntüsünü karşılaştır: yön + sürücü değişimi."""
    p = {**KONVANSIYON, **(p or {})}
    if not onceki:
        return {"durum": f"{YOK} — kıyas için önceki koşu kaydı yok (ilk analiz)"}

    o_yon, y_yon = onceki.get("YON_BIAS", YOK), yeni.get("YON_BIAS", YOK)
    etiket, aciklama = _degisim_etiketi(o_yon, y_yon)
    o_skor, y_skor = _f(onceki.get("yon_skoru")), _f(yeni.get("yon_skoru"))
    skor_delta = (round(y_skor - o_skor, 4)
                  if None not in (o_skor, y_skor) else YOK)

    # sürücü karşılaştırması
    o_sur, y_sur = onceki.get("surucu") or {}, yeni.get("surucu") or {}
    satirlar, degisen = [], []
    for ad, etiket_ad in SURUCULER.items():
        a, b = o_sur.get(ad), y_sur.get(ad)
        if a is None and b is None:
            continue
        fa, fb = _f(a), _f(b)
        if fa is not None and fb is not None:
            delta = round(fb - fa, 6)
            taban = max(abs(fa), 1e-9)
            onemli = (abs(delta) >= p["adx_esik"] if ad == "adx"
                      else abs(delta) >= p["skor_esik"] if ad.endswith("skor")
                      else abs(delta) / taban >= p["oran_esik"])
            satirlar.append({"kanal": etiket_ad, "onceki": fa, "yeni": fb,
                             "delta": delta, "onemli": bool(onemli)})
            if onemli:
                degisen.append(f"{etiket_ad}: {fa} → {fb} ({delta:+g})")
        else:
            ayni = (str(a) == str(b))
            satirlar.append({"kanal": etiket_ad, "onceki": a if a is not None else YOK,
                             "yeni": b if b is not None else YOK,
                             "delta": "—", "onemli": not ayni})
            if not ayni:
                degisen.append(f"{etiket_ad}: {a} → {b}")

    # danışman duruş değişimi
    o_d, y_d = onceki.get("danismanlar") or {}, yeni.get("danismanlar") or {}
    donen = [f"{ad}: {o_d.get(ad, YOK)} → {y_d.get(ad, YOK)}"
             for ad in sorted(set(o_d) | set(y_d))
             if o_d.get(ad) != y_d.get(ad)]

    o_fiyat, y_fiyat = _f(onceki.get("son_kapanis")), _f(yeni.get("son_kapanis"))
    fiyat = ({"onceki": o_fiyat, "yeni": y_fiyat,
              "delta": round(y_fiyat - o_fiyat, 4),
              "yuzde": round((y_fiyat / o_fiyat - 1) * 100, 3)}
             if None not in (o_fiyat, y_fiyat) and o_fiyat else YOK)

    return {
        "durum": "KIYASLANDI",
        "onceki_bar_utc": onceki.get("son_bar_utc", YOK),
        "yeni_bar_utc": yeni.get("son_bar_utc", YOK),
        "YON_DEGISIMI": {"onceki": o_yon, "yeni": y_yon, "etiket": etiket,
                         "aciklama": aciklama, "skor_onceki": o_skor,
                         "skor_yeni": y_skor, "skor_delta": skor_delta},
        "fiyat": fiyat,
        "surucu_tablosu": satirlar,
        "onemli_degisimler": degisen or ["kayda değer sürücü değişimi yok"],
        "danisman_donusleri": donen or ["danışman duruşları aynı"],
        "varsayimlar": [
            f"anlamlı değişim eşikleri: skor {p['skor_esik']}, oransal "
            f"%{p['oran_esik']*100:.0f}, ADX {p['adx_esik']} (konvansiyon)",
            "yön DEVAM etse bile sürücü değişimi kararın kalitesini değiştirir",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Önceki karar akıbeti + rejim kıyası")
    ap.add_argument("--onceki", required=True, help="önceki koşu anlık görüntüsü")
    ap.add_argument("--yeni", help="yeni koşu anlık görüntüsü (kıyas için)")
    ap.add_argument("--m15", help="yeni kline (akıbet ölçümü için)")
    ap.add_argument("--arsiv", help="bar arşivi (kayan pencere telafisi)")
    a = ap.parse_args(argv)

    onceki = json.loads(Path(a.onceki).read_text(encoding="utf-8"))
    out = {}
    if a.m15 or a.arsiv:
        barlar = AE.bar_yukle([x for x in (a.m15, a.arsiv) if x])
        out["AKIBET"] = akibet_olc(onceki, barlar)
    if a.yeni:
        out["KIYAS"] = kiyasla(onceki, json.loads(
            Path(a.yeni).read_text(encoding="utf-8")))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
