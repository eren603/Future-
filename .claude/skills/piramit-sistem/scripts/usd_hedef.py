#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SABİT-USDT HEDEF MOTORU — "kazanç 135–150 USDT, risk 100 USDT" kısıtını
fiyat seviyesine çevirir ve piyasa yapısıyla uyumunu MEKANİK sınar.

Sorun: kullanıcı hedefini R cinsinden değil DOLAR cinsinden tanımlıyor
(3 ETH ile 135 USDT kazanç = 45 puan hareket). Bu kısıt ancak kontrat
büyüklüğü verilince fiyata çevrilebilir; sonra da o mesafenin piyasanın
oynaklığıyla ve YAPISIYLA uyumlu olup olmadığı sınanmalıdır. Uyumsuzsa
hedef tutturulamaz — bandı tutturmak için seviye UYDURULMAZ.

Çevrim (tek kaynak, uydurma yok):
    fiyat_mesafesi = usdt_miktar / kontrat
    R              = hedef_usdt / stop_usdt
    net_kazanc     = brut - komisyon(gidiş+dönüş, nominal üzerinden)

KAPILAR (fail-closed — hepsi geçmezse "UYGUN DEĞİL"):
  1. R ≥ r_min                     (depo kuralı; kullanıcı 1.35 seçti)
  2. stop ∈ [0.8, 2.0] × ATR_kurulum   (stop gürültüde değil, ölçek dışı değil)
  3. hedef ≤ 3.0 × ATR_kurulum     (uzak hedef + dar stop = şişirilmiş R)
  4. yapı hedefi bandın İÇİNDE     (gerçek likidite seviyesi 135–150 bandına
                                    düşmeli; düşmüyorsa hedef yapıya dayanmıyor)
  5. sabit stop, karşı yapı seviyesinin ÖTESİNDE (stopun içeride kalması =
                                    yapı tarafından süpürülme)
  6. tasfiye mesafesi > stop mesafesi (teminat/kontrat)

Kapı eşikleri `rr_denetim.py` konvansiyonuyla AYNI kaynaktan gelir —
iki farklı doğruluk kaynağı bırakılmaz.

Determinist. ⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

YOK = "VERİ YOK"

KONVANSIYON = {
    "r_min": 1.35,            # depo kuralı (karar_motoru.R_MIN ile aynı)
    "min_stop_atr": 0.8,      # rr_denetim.ESIK ile aynı
    "max_stop_atr": 2.0,      # rr_denetim.swing_stop_atr
    "far_target_atr": 3.0,    # rr_denetim.far_target_atr
    "komisyon_bps_tek_yon": 4.0,   # Binance vadeli taker %0.04 (varsayım, etiketli)
}


class HedefError(Exception):
    pass


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def hesapla(job: dict) -> dict:
    p = {**KONVANSIYON, **(job.get("esikler") or {})}
    kontrat = _f(job.get("kontrat"))
    teminat = _f(job.get("teminat"))
    stop_usdt = _f(job.get("stop_usdt"))
    hedef_band = job.get("hedef_usdt") or []
    fiyat = _f(job.get("fiyat"))
    atr_kur = _f(job.get("atr_kurulum"))
    yon = str(job.get("yon", "")).lower()

    eksik = [ad for ad, v in (("kontrat", kontrat), ("stop_usdt", stop_usdt),
                              ("fiyat", fiyat), ("atr_kurulum", atr_kur))
             if v is None or v <= 0]
    if eksik:
        raise HedefError(f"{YOK} — zorunlu alan(lar) eksik/geçersiz: {eksik}")
    if len(hedef_band) != 2:
        raise HedefError(f"{YOK} — hedef_usdt [alt, üst] olmalı")
    if yon not in ("long", "short"):
        raise HedefError("yon long|short olmalı")

    h_lo, h_hi = sorted(float(x) for x in hedef_band)
    s = 1 if yon == "long" else -1
    hedef_tipi = str(job.get("hedef_tipi", "brut")).lower()
    if hedef_tipi not in ("brut", "net"):
        raise HedefError("hedef_tipi 'brut' ya da 'net' olmalı")

    # --- çevrim: USDT → fiyat mesafesi ---
    stop_mesafe = stop_usdt / kontrat
    hedef_lo_mesafe = h_lo / kontrat
    hedef_hi_mesafe = h_hi / kontrat
    nominal = kontrat * fiyat
    komisyon = nominal * (p["komisyon_bps_tek_yon"] / 10000.0) * 2
    # NET hedef istenmişse komisyon eklenerek BRÜT hedefe çevrilir; kapılar
    # daima brüt üzerinden işler (fiyat mesafesi brüt hedefle belirlenir).
    brut_lo, brut_hi = ((h_lo, h_hi) if hedef_tipi == "brut"
                        else (h_lo + komisyon, h_hi + komisyon))
    h_lo, h_hi = brut_lo, brut_hi

    cevrim = {
        "hedef_tipi": hedef_tipi,
        "hedef_brut_usdt": [round(h_lo, 2), round(h_hi, 2)],
        "nominal_usdt": round(nominal, 2),
        "stop_mesafe_puan": round(stop_mesafe, 4),
        "hedef_mesafe_puan": [round(hedef_lo_mesafe, 4), round(hedef_hi_mesafe, 4)],
        "R_band": [round(h_lo / stop_usdt, 4), round(h_hi / stop_usdt, 4)],
        "stop_atr_kat": round(stop_mesafe / atr_kur, 4),
        "hedef_atr_kat": [round(hedef_lo_mesafe / atr_kur, 4),
                          round(hedef_hi_mesafe / atr_kur, 4)],
        "komisyon_gidis_donus_usdt": round(komisyon, 2),
        "net_kazanc_band_usdt": [round(h_lo - komisyon, 2), round(h_hi - komisyon, 2)],
        "gercek_kaldirac": (round(nominal / teminat, 2) if teminat else YOK),
        "tasfiye_mesafe_puan": (round(teminat / kontrat, 4) if teminat else YOK),
    }

    # --- kapılar ---
    kapilar, gecen = [], True

    r_lo = h_lo / stop_usdt
    ok1 = r_lo >= p["r_min"]
    kapilar.append({"kapi": "R ≥ r_min", "gecti": ok1,
                    "kanit": f"R alt sınırı {r_lo:.2f} vs r_min {p['r_min']}"})
    gecen &= ok1

    ok2 = p["min_stop_atr"] <= cevrim["stop_atr_kat"] <= p["max_stop_atr"]
    kapilar.append({"kapi": "stop ölçeği", "gecti": ok2,
                    "kanit": f"stop {cevrim['stop_atr_kat']}×ATR, kabul "
                             f"[{p['min_stop_atr']}, {p['max_stop_atr']}]"})
    gecen &= ok2

    ok3 = cevrim["hedef_atr_kat"][1] <= p["far_target_atr"]
    kapilar.append({"kapi": "hedef ölçeği", "gecti": ok3,
                    "kanit": f"hedef üst {cevrim['hedef_atr_kat'][1]}×ATR vs "
                             f"uzak eşiği {p['far_target_atr']}"})
    gecen &= ok3

    if teminat:
        ok6 = (teminat / kontrat) > stop_mesafe
        kapilar.append({"kapi": "tasfiye > stop", "gecti": ok6,
                        "kanit": f"tasfiye {teminat/kontrat:.2f} puan vs stop "
                                 f"{stop_mesafe:.2f} puan"})
        gecen &= ok6

    # --- giriş adayları: her aday için seviye seti + yapı sınavı ---
    likidite = [_f(x) for x in (job.get("likidite_hedefleri") or [])]
    likidite = [x for x in likidite if x is not None]
    yapi_seviyeleri = [_f(x) for x in (job.get("karsi_yapi_seviyeleri") or [])]
    yapi_seviyeleri = [x for x in yapi_seviyeleri if x is not None]

    adaylar = []
    for giris in [_f(x) for x in (job.get("giris_adaylari") or [])]:
        if giris is None:
            continue
        stop = giris - s * stop_mesafe
        tp_lo = giris + s * hedef_lo_mesafe
        tp_hi = giris + s * hedef_hi_mesafe
        # kapı 4: bandın içine düşen GERÇEK likidite hedefi var mı?
        band = sorted((tp_lo, tp_hi))
        icerdeki = [x for x in likidite
                    if band[0] <= x <= band[1] and (x - giris) * s > 0]
        # kapı 5: sabit stop, karşı yapı seviyesinin ötesinde mi?
        if yapi_seviyeleri:
            if yon == "long":
                engel = [x for x in yapi_seviyeleri if x < giris]
                en_yakin = max(engel) if engel else None
                stop_otede = (stop < en_yakin) if en_yakin is not None else None
            else:
                engel = [x for x in yapi_seviyeleri if x > giris]
                en_yakin = min(engel) if engel else None
                stop_otede = (stop > en_yakin) if en_yakin is not None else None
        else:
            en_yakin, stop_otede = None, None
        adaylar.append({
            "giris": round(giris, 4), "stop": round(stop, 4),
            "hedef_min": round(tp_lo, 4), "hedef_max": round(tp_hi, 4),
            "band_ici_likidite": [round(x, 4) for x in icerdeki],
            "yapi_hedefi_var": bool(icerdeki),
            "en_yakin_karsi_yapi": (round(en_yakin, 4) if en_yakin is not None else YOK),
            "stop_yapinin_otesinde": (stop_otede if stop_otede is not None else YOK),
        })

    yapi_ok = any(a["yapi_hedefi_var"] for a in adaylar) if adaylar else None
    if adaylar:
        kapilar.append({"kapi": "yapı hedefi bandın içinde", "gecti": bool(yapi_ok),
                        "kanit": (f"{sum(a['yapi_hedefi_var'] for a in adaylar)}/"
                                  f"{len(adaylar)} adayda gerçek likidite hedefi banda düşüyor"
                                  if likidite else f"{YOK} — likidite hedefi verilmedi")})
        gecen &= bool(yapi_ok)

    hukum = ("UYGUN" if gecen and adaylar else
             ("UYGUN DEĞİL" if adaylar else f"{YOK} — giriş adayı verilmedi"))

    return {
        "sembol": job.get("sembol", YOK), "yon": yon,
        "HUKUM": hukum,
        "cevrim": cevrim,
        "kapilar": kapilar,
        "adaylar": adaylar,
        "dusen_kapilar": [k["kapi"] for k in kapilar if not k["gecti"]],
        "varsayimlar": [
            f"komisyon {p['komisyon_bps_tek_yon']} bps/tek yön taker (borsa varsayımı)",
            (f"hedef BRÜT tanımlı (kullanıcı kararı): kapılar brüt üzerinden; "
             f"net kazanç ayrıca raporlanır"
             if hedef_tipi == "brut" else
             "hedef NET tanımlı: komisyon eklenip brüte çevrildi, kapılar brütle"),
            f"stop ölçek bandı [{p['min_stop_atr']}, {p['max_stop_atr']}]×ATR ve uzak "
            f"hedef eşiği {p['far_target_atr']}×ATR — rr_denetim konvansiyonuyla AYNI",
            "tasfiye mesafesi kaba: teminat/kontrat (bakım teminatı ve fonlama hariç)",
            f"r_min={p['r_min']} kullanıcı kuralı (risk 100 USDT, hedef ≥135 USDT)",
        ],
        "not": ("Kısıt DOLAR cinsindendir; fiyata çevrimi kontrat büyüklüğüne bağlıdır. "
                "Bandı tutturmak için seviye uydurulmaz — yapı hedefi banda düşmüyorsa "
                "kapı kapanır. Canlı/otomatik emir DAHİL DEĞİL."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sabit-USDT hedef motoru")
    ap.add_argument("--job", required=True)
    a = ap.parse_args(argv)
    job = json.loads(Path(a.job).expanduser().read_text(encoding="utf-8"))
    print(json.dumps(hesapla(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
