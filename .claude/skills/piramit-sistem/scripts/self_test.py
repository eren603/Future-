#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Piramit sistemi öz-testi — iddia edilen her mekanizma KANITLANIR.

Sınananlar:
  T1 zirveye tırmanma  : gerçek depo verisiyle K1→K5, ZIRVE üretilir
  T2 K1 fail-closed    : veri yoksa K1 kapısı kapanır, üst katman KOŞMAZ
  T3 K2 fail-closed    : tek motor koşarsa K2 kapısı kapanır
  T4 SI kalibrasyonu   : n ≥ n_taban olan defterde ağırlık formülle ÖLÇÜLÜR
  T5 SI geri beslemesi : üretilen ağırlık BİR SONRAKİ koşunun güvenini böler
  T6 işlem kalitesi    : "TEMİZ GİRİŞ VAR" ancak rr TUTARLI + R ≥ R_MIN ise
  T7 determinizm       : aynı girdi = aynı zirve

Çalıştırma: python self_test.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import piramit as P  # noqa: E402
import akibet_etiketle as AE  # noqa: E402
import turev_girdi as TG  # noqa: E402
import paket_ac as PA  # noqa: E402
import gozlemci as GZ  # noqa: E402
import iddia_denetle as ID  # noqa: E402
import usd_hedef as UH  # noqa: E402
import korelasyon as KOR  # noqa: E402
import kiyas as KY  # noqa: E402
sys.path.insert(0, str(P.SKILLS / "karar-kurulu" / "scripts"))
import sentez as SZ  # noqa: E402

sys.path.insert(0, str(P.SKILLS / "grafik-calisma" / "scripts"))
import kalibrasyon as kb  # noqa: E402

GECEN, KALAN = [], []


def kontrol(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECEN if kosul else KALAN).append(f"{ad}{(' — ' + ayrinti) if ayrinti else ''}")
    print(f"{'✔' if kosul else '✖'} {ad}{(' — ' + ayrinti) if ayrinti else ''}")


def _job(tmp: Path, veri: dict, **ek) -> Path:
    j = {"soru": "öz-test", "sembol": "TEST", "veri": veri,
         "state_dir": str(tmp / "state"), **ek}
    p = tmp / "job.json"
    p.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
    return p


def _kos(job_path: Path) -> dict:
    return P.kos(json.loads(job_path.read_text(encoding="utf-8")), job_path.parent)


def main() -> int:
    m15 = P.ENGINE / "girdi" / "m15.json"
    h4 = P.ENGINE / "girdi" / "h4.json"
    if not (m15.exists() and h4.exists()):
        print(f"ATLANDI: {P.ENGINE/'girdi'} altında m15/h4 yok — test verisi gerekli.")
        return 1

    agirlik_p = P.AGIRLIK_DOSYA
    yedek = agirlik_p.read_text(encoding="utf-8") if agirlik_p.exists() else None
    tmp = Path(tempfile.mkdtemp(prefix="piramit_test_"))
    try:
        if agirlik_p.exists():
            agirlik_p.unlink()   # T1 temiz başlasın (ağırlık 1.0 nötr)

        # ---- T1: zirveye tırmanma -----------------------------------------
        (tmp / "state").mkdir(parents=True, exist_ok=True)
        r1 = _kos(_job(tmp, {"m15": str(m15), "h4": str(h4)}))
        katmanlar = [k["katman"] for k in r1["katmanlar"]]
        kontrol("T1 zirveye tırmanma",
                katmanlar == P.KATMANLAR and r1["ZIRVE"].get("YON_BIAS") in
                ("LONG", "SHORT", "NÖTR"),
                f"katmanlar={len(katmanlar)}/5, YON_BIAS={r1['ZIRVE'].get('YON_BIAS')}")

        # ---- T2: K1 fail-closed (dosya yok → hiç üst katman koşmaz) --------
        r2 = _kos(_job(tmp, {"m15": "yok_boyle_bir_dosya.json"}))
        kontrol("T2 K1 fail-closed",
                (not r2["katmanlar"][0]["gecti"]) and len(r2["katmanlar"]) == 1
                and r2["ZIRVE"]["YON_BIAS"] == P.YOK
                and r2["ZIRVE"]["ulasilan_katman"] == "K1-LLM",
                f"durdu={r2['durum']}")

        # ---- T3: K2 fail-closed — K1 GEÇER (csv var) ama motorlar üretemez -
        # 8 satırlık CSV: tablo okunur (K1 ✔) ama hiçbir SMC motoru istatistik
        # kuramaz → K2 kapısı kapanmalı. Aksi halde "yetersiz veriyle karar".
        kisa = tmp / "kisa.csv"
        kisa.write_text("open,high,low,close,volume\n" +
                        "\n".join(f"{100+i},{101+i},{99+i},{100+i},{10+i}"
                                  for i in range(8)) + "\n", encoding="utf-8")
        r3 = _kos(_job(tmp, {"ohlcv_csv": str(kisa)}))
        k1_3 = r3["katmanlar"][0]
        k2_3 = next((k for k in r3["katmanlar"] if k["katman"] == "K2-AI-AJAN"), None)
        kontrol("T3 K2 fail-closed (K1 geçti, motorlar üretemedi)",
                k1_3["gecti"] and k2_3 is not None and not k2_3["gecti"]
                and r3["ZIRVE"]["ulasilan_katman"] == "K2-AI-AJAN",
                f"K1={k1_3['gecti']}, K2 motor sayısı="
                f"{k2_3['motor_sayisi'] if k2_3 else P.YOK}, durum={r3['durum']}")

        # ---- T4: SI kalibrasyonu (n ≥ n_taban) -----------------------------
        st = tmp / "kal_state"
        st.mkdir(parents=True, exist_ok=True)
        rs = [0.9, -1.0, 1.4, -1.0, 0.7, 1.1, -1.0, 0.6, -1.0, 1.2, 0.8, -1.0]
        with (st / "defter.jsonl").open("w", encoding="utf-8") as f:
            for i, r in enumerate(rs):
                f.write(json.dumps({"karar_zamani": i, "gercek_r": r,
                                    "karar": {"karar": "LONG"}}) + "\n")
        wins = sum(1 for r in rs if r > 0)
        beklenen = round(max(P.KONVANSIYON["agirlik_alt"],
                             min(P.KONVANSIYON["agirlik_ust"],
                                 2.0 * kb.wilson_lo(wins, len(rs)))), 4)
        jp = _job(tmp, {"m15": str(m15), "h4": str(h4)})
        j = json.loads(jp.read_text(encoding="utf-8"))
        j["state_dir"] = str(st)
        jp.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
        r4 = _kos(jp)
        kal = [k for k in r4["katmanlar"] if k["katman"] == "K5-SI"][0]["kalibrasyon"]
        olculen = kal["agirliklar"].get("karar-motoru")
        kontrol("T4 SI kalibrasyonu (n≥n_taban)",
                olculen == beklenen and kal["ayrinti"]["karar-motoru"]["n"] == len(rs)
                and kal["ayrinti"]["karar-motoru"]["wins"] == wins,
                f"{wins}/{len(rs)} → wilson_lo="
                f"{round(kb.wilson_lo(wins, len(rs)), 4)} → ağırlık={olculen} "
                f"(beklenen {beklenen})")

        # ---- T5: geri besleme bir SONRAKİ koşuyu değiştirir ----------------
        r5 = _kos(jp)
        d5 = {d["name"]: d for d in
              [k for k in r5["katmanlar"] if k["katman"] == "K3-COKLU-AJAN"][0]["danismanlar"]}
        km = d5.get("karar-motoru", {})
        uygulandi = (km.get("_agirlik") == beklenen and
                     km.get("confidence") == round(km.get("_ham_confidence", 0) * beklenen, 4))
        kontrol("T5 SI geri beslemesi K3'e uygulandı", bool(uygulandi),
                f"ham={km.get('_ham_confidence')} × ağırlık={km.get('_agirlik')} "
                f"= {km.get('confidence')}")

        # ---- T6: işlem kalitesi hükmü kanıta bağlı -------------------------
        ik = [k for k in r1["katmanlar"] if k["katman"] == "K5-SI"][0]["islem_kalitesi"]
        if ik["hukum"] == "TEMİZ GİRİŞ VAR":
            a = ik["adaylar"][0]
            ok = a["rr_verdict"] == "TUTARLI" and a["R_gercekci"] >= P.KONVANSIYON["r_min"]
            det = f"aday {a['motor']} R={a['R_gercekci']} rr={a['rr_verdict']}"
        else:
            ok = bool(ik["engeller"]) or not ik["seviyeler"]
            det = f"BEKLE gerekçeli: {ik['engeller'] or 'seviye yok'}"
        kontrol("T6 işlem kalitesi hükmü kanıta bağlı", ok, det)

        # ---- T7: determinizm ------------------------------------------------
        r7 = _kos(jp)
        a, b = r5["ZIRVE"], r7["ZIRVE"]
        kontrol("T7 determinizm",
                (a["YON_BIAS"], a["yon_skoru"], a["ISLEM_KALITESI"]) ==
                (b["YON_BIAS"], b["yon_skoru"], b["ISLEM_KALITESI"]),
                f"{a['YON_BIAS']}/{a['yon_skoru']} == {b['YON_BIAS']}/{b['yon_skoru']}")

        # ================= AKIBET ETİKETLEYİCİ (SI döngüsünün yakıtı) =======
        P_ET = {**AE.KONVANSIYON, "azami_bekleme": 3, "azami_tutma": 5}
        # `giris_tipi: market` ARTIK ZORUNLU: eşit sınırlar tek başına market
        # sayılmıyor (tetiklenmemiş işleme R yazma kusuru, T32).
        MARKET_SHORT = {"karar": "SHORT", "yon": "SHORT", "giris_alt": 100.0,
                        "giris_ust": 100.0, "giris": 100.0, "stop": 102.0,
                        "t1": 96.0, "iptal": 101.0, "giris_tipi": "market"}

        def _bar(t, o, h, l, c):
            return (t, o, h, l, c, 1.0)

        # T8: hedef vuruldu → R = |giriş-T1| / |giriş-stop| = 4/2 = +2.0
        b8 = [_bar(1, 100, 100.5, 99.5, 100), _bar(2, 100, 100.2, 95.5, 96)]
        s8 = AE.simule_et(MARKET_SHORT, 1, b8, P_ET)
        kontrol("T8 etiketleyici: hedef → +2.0R",
                s8["olculebilir"] and s8["sonuc"] == "T1" and s8["r"] == 2.0,
                f"{s8['sonuc']} r={s8.get('r')}")

        # T9: stop vuruldu → R = -1.0 (aynı barda hedef de olsa STOP sayılır)
        b9 = [_bar(1, 100, 100.5, 99.5, 100), _bar(2, 100, 102.5, 95.0, 102)]
        s9 = AE.simule_et(MARKET_SHORT, 1, b9, P_ET)
        kontrol("T9 etiketleyici: stop → -1.0R (aynı barda hedef olsa da)",
                s9["olculebilir"] and s9["sonuc"] == "STOP" and s9["r"] == -1.0,
                f"{s9['sonuc']} r={s9.get('r')}")

        # T10: LIMIT bölgeye dokunulmadı → pozisyon yok, R YAZILMAZ
        limit = {**MARKET_SHORT, "giris_alt": 105.0, "giris_ust": 106.0,
                 "iptal": 107.0, "giris_tipi": "limit"}   # market bayrağı DÜŞER
        b10 = [_bar(i, 100, 100.5, 99.0, 100) for i in range(1, 7)]
        s10 = AE.simule_et(limit, 1, b10, P_ET)
        kontrol("T10 etiketleyici: dolmayan limit → R yazılmaz",
                (not s10["olculebilir"]) and "İPTAL" in s10["sonuc"],
                s10["sonuc"])

        # T11: elle yazılmış gercek_r EZİLMEZ; ölçülebilir satır etiketlenir
        dft = tmp / "defter_test.jsonl"
        dft.write_text(
            json.dumps({"karar_zamani": 1, "karar": MARKET_SHORT,
                        "gercek_r": -0.526, "not": "elle düzeltme"},
                       ensure_ascii=False) + "\n" +
            json.dumps({"karar_zamani": 1, "karar": MARKET_SHORT},
                       ensure_ascii=False) + "\n", encoding="utf-8")
        rap = AE.etiketle(dft, b8, P_ET, yaz=True)
        satir = [json.loads(x) for x in dft.read_text(encoding="utf-8").splitlines() if x.strip()]
        kontrol("T11 etiketleyici: elle etiket korunur, boş olan doldurulur",
                rap["elle_korunan"] == 1 and rap["etiketlenen"] == 1
                and satir[0]["gercek_r"] == -0.526 and satir[1]["gercek_r"] == 2.0
                and satir[1]["etiketleyici"].startswith("otomatik"),
                f"korunan={rap['elle_korunan']}, etiketlenen={rap['etiketlenen']}, "
                f"yeni r={satir[1]['gercek_r']}")

        # ---- T13: danışman defterleri (ağırlık asimetrisi panzehiri) -------
        sd13 = tmp / "d13"
        sd13.mkdir(parents=True, exist_ok=True)
        k1f = {"olcumler": {"m15_son_bar": 12345}}
        k2f = {"motor_sonuclari": {"grafik-calisma": {"giris_bolgesi": [100.0, 101.0]}}}
        k3f = {"seviyeler": {
            "grafik-calisma": {"yon": "short", "entry": 100.5, "stop": 102.0,
                               "target": 96.0},
            "karar-motoru": {"yon": "short", "entry": 1.0, "stop": 2.0, "target": 0.5}}}
        y1 = P._danisman_defterleri(k1f, k2f, k3f, sd13)
        y2 = P._danisman_defterleri(k1f, k2f, k3f, sd13)   # aynı bar → tekilleme
        dp = sd13 / "defter_grafik-calisma.jsonl"
        satirlar = [x for x in dp.read_text(encoding="utf-8").splitlines() if x.strip()]
        kayit = json.loads(satirlar[0])
        kontrol("T13 danışman defteri: yazıldı, karar-motoru hariç, tekilleme çalışıyor",
                list(y1["yazilan"]) == ["grafik-calisma"] and len(satirlar) == 1
                and not y2["yazilan"] and kayit["karar"]["giris_alt"] == 100.0
                and kayit["karar"]["iptal"] == 102.0
                and not (sd13 / "defter_karar-motoru.jsonl").exists(),
                f"yazılan={list(y1['yazilan'])}, satır={len(satirlar)}, "
                f"2. çağrı atlandı={bool(y2['atlanan'])}")

        # ---- T14: CVD çevrimdışı hesabı (kline körlüğü panzehiri) ---------
        # 12 alanlı Binance kline: alan 5 = hacim, alan 9 = taker ALIŞ hacmi.
        # delta = 2×taker − hacim → 2×60−100 = +20/bar → kümülatif 20, 40, 60
        kl = tmp / "kline12.json"
        kl.write_text(json.dumps([
            [i * 900000, "100", "101", "99", "100", "100.0", 0, "0", 10,
             "60.0", "0", "0"] for i in range(3)]), encoding="utf-8")
        c14 = TG.cvd_serisi(kl)
        # taker < yarı hacim → satıcı baskısı (negatif delta) kontrolü
        kl2 = tmp / "kline12b.json"
        kl2.write_text(json.dumps([
            [i * 900000, "100", "101", "99", "100", "100.0", 0, "0", 10,
             "30.0", "0", "0"] for i in range(2)]), encoding="utf-8")
        c14b = TG.cvd_serisi(kl2)
        kontrol("T14 CVD çevrimdışı: alıcı +20/bar, satıcı -40/bar",
                c14["cvd_series"] == [20.0, 40.0, 60.0]
                and c14b["cvd_series"] == [-40.0, -80.0],
                f"alıcı={c14['cvd_series']} satıcı={c14b['cvd_series']}")

        # ---- T15: eksik kanal UYDURULMAZ (fail-closed) --------------------
        seri15 = tmp / "seri15.jsonl"
        TG.snapshot_ekle(seri15, {"ts": "a", "price": 100.0, "oi": 10.0})
        tekrar = TG.snapshot_ekle(seri15, {"ts": "a", "price": 100.0, "oi": 10.0})
        job15 = TG.uret(kl, seri15, {}, None)
        kontrol("T15 eksik türev kanalı uydurulmaz + tekilleme",
                (not tekrar["eklendi"]) and "oi_series" not in job15
                and "funding" not in job15 and "liq_long" not in job15
                and any("oi:" in e for e in job15["_eksikler"])
                and job15.get("cvd_series"),
                f"tekilleme={not tekrar['eklendi']}, eksik={len(job15['_eksikler'])} kanal, "
                f"CVD var={bool(job15.get('cvd_series'))}")

        # ---- T16: tarayıcıdan yapıştırılan ham Binance yanıtları ----------
        hd = tmp / "ham"
        hd.mkdir(parents=True, exist_ok=True)
        (hd / "premiumIndex.json").write_text(json.dumps(
            {"symbol": "BTCUSDT", "lastFundingRate": "0.00021000",
             "time": 1784889000000}), encoding="utf-8")
        (hd / "openInterestHist.json").write_text(json.dumps([
            {"symbol": "BTCUSDT", "sumOpenInterest": "80000.0",
             "sumOpenInterestValue": "5200000000.0", "timestamp": 1784888100000},
            {"symbol": "BTCUSDT", "sumOpenInterest": "79000.0",
             "sumOpenInterestValue": "5135000000.0", "timestamp": 1784889000000}]),
            encoding="utf-8")
        (hd / "takerlongshortRatio.json").write_text(json.dumps([
            {"buySellRatio": "0.8500", "symbol": "BTCUSDT",
             "timestamp": 1784889000000}]), encoding="utf-8")
        h16 = TG.ham_oku(hd, "BTCUSDT")
        j16 = TG.uret(kl, None, {}, None, h16)
        # yanlış sembol karara GİREMEZ
        (hd / "takerlongshortRatio.json").write_text(json.dumps([
            {"buySellRatio": "9.9", "symbol": "ETHUSDT",
             "timestamp": 1784889000000}]), encoding="utf-8")
        h16b = TG.ham_oku(hd, "BTCUSDT")
        j16b = TG.uret(kl, None, {}, None, h16b)
        kontrol("T16 ham yapıştırma: 4 kanal okunur, yanlış sembol reddedilir",
                j16.get("funding") == 0.021 and j16.get("taker_lsr") == 0.85
                and j16.get("oi_series") == [80000.0, 79000.0]
                and j16.get("price_series") == [65000.0, 65000.0]
                and "taker_lsr" not in j16b and any("ETHUSDT" in e for e in h16b["hatalar"]),
                f"funding={j16.get('funding')} lsr={j16.get('taker_lsr')} "
                f"oi={j16.get('oi_series')} | yanlış sembol reddi="
                f"{'taker_lsr' not in j16b}")

        # ---- T17: veri paketi açıcı (telefondan tek dosya) ----------------
        gercek_m15 = json.loads(m15.read_text(encoding="utf-8"))
        gercek_h4 = json.loads(h4.read_text(encoding="utf-8"))
        paket = {"paket": "piramit-veri", "surum": 1, "sembol": "BTCUSDT",
                 "cekim_utc": "test", "veri": {
                     "m15": gercek_m15, "h4": gercek_h4,
                     "openInterestHist": [
                         {"symbol": "BTCUSDT", "sumOpenInterest": "80000.0",
                          "sumOpenInterestValue": "5.2e9",
                          "timestamp": gercek_m15[-1][0]}],
                     "premiumIndex": {"symbol": "BTCUSDT",
                                      "lastFundingRate": "0.0002"},
                     "takerlongshortRatio": [
                         {"symbol": "BTCUSDT", "buySellRatio": "0.85",
                          "timestamp": gercek_m15[-1][0]}]}}
        hedef = tmp / "acilan"
        eski_girdi, eski_ham = PA.GIRDI, PA.HAM
        PA.GIRDI, PA.HAM = hedef, hedef / "turev_ham"
        try:
            r17 = PA.ac(paket, "BTCUSDT")
            # yanlış sembol REDDEDİLMELİ
            red = False
            try:
                PA.ac({**paket, "sembol": "ETHUSDT"}, "BTCUSDT")
            except SystemExit:
                red = True
            # kısa kline YAZILMAMALI
            kisa_paket = {**paket, "veri": {**paket["veri"], "m15": gercek_m15[:10]}}
            r17b = PA.ac(kisa_paket, "BTCUSDT")
        finally:
            PA.GIRDI, PA.HAM = eski_girdi, eski_ham
        kontrol("T17 paket açıcı: 5 kanal yazıldı, yanlış sembol + kısa kline reddedildi",
                len(r17["yazilan"]) == 5 and (hedef / "m15.json").exists()
                and (hedef / "turev_ham" / "premiumIndex.json").exists()
                and red and "m15" not in r17b["yazilan"]
                and any("asgari" in a for a in r17b["atlanan"]),
                f"yazılan={len(r17['yazilan'])}, yanlış sembol reddi={red}, "
                f"kısa kline reddi={'m15' not in r17b['yazilan']}")

        # ---- T18: motor geometri kapısı (bayat kurulum reddi) -------------
        sys.path.insert(0, str(P.ENGINE))
        import karar_motoru as KM  # noqa: PLC0415
        # gerçek olay: SHORT ama stop girişin ALTINDA (fiyat kurulumun üstüne döndü)
        bozuk, sebep = KM.geometri_gecerli("SHORT", 64213.8, 64170.0, 64104.1)
        saglam, _ = KM.geometri_gecerli("SHORT", 64213.8, 64290.0, 64104.1)
        long_bozuk, _ = KM.geometri_gecerli("LONG", 100.0, 105.0, 110.0)
        long_saglam, _ = KM.geometri_gecerli("LONG", 100.0, 98.0, 110.0)
        kontrol("T18 motor geometri kapısı: bayat/ters kurulum reddedilir",
                (not bozuk) and saglam and (not long_bozuk) and long_saglam
                and "short sırası bozuk" in sebep,
                f"short-bozuk reddi={not bozuk}, short-sağlam kabul={saglam}, "
                f"long-bozuk reddi={not long_bozuk}")

        # ---- T19: zorunlu girdiler + görsel/mekanik karşılıklı teyit ------
        gp = tmp / "gorsel.json"
        lp = tmp / "likidasyon.json"
        # Damga zorunlu (T28 tazelik kuralı): fixture'lar veri barıyla damgalanır.
        import datetime as _dt19  # noqa: PLC0415
        _son19 = json.loads(m15.read_text(encoding="utf-8"))[-1][0]
        DAMGA19 = _dt19.datetime.fromtimestamp(
            _son19 / 1000, _dt19.timezone.utc).strftime("%Y-%m-%d %H:%M")
        lp.write_text(json.dumps({"liq_long": 12.4, "liq_short": 31.8,
                                  "zaman_utc": DAMGA19}), encoding="utf-8")
        # (a) EKSİK durumda uyarı taşınmalı. Yollar AÇIKÇA olmayan dosyaya
        # verilir — aksi halde test, depoda gerçek likidasyon/görsel dosyası
        # bulunup bulunmamasına göre değişir (gerçek koşuda yakalandı).
        r19a = _kos(_job(tmp, {"m15": str(m15), "h4": str(h4),
                               "likidasyon": str(tmp / "yok_likidasyon.json"),
                               "gorsel": str(tmp / "yok_gorsel.json")}))
        eksik_var = len(r19a["ZIRVE"].get("ZORUNLU_EKSIK", [])) == 2
        # (b) görsel MEKANİKLE UYUMLU → doğrulanır
        smc_trend = None
        for k in r19a["katmanlar"]:
            if k["katman"] == "K2-AI-AJAN":
                smc_trend = (k["motor_sonuclari"].get("smc_tespit") or {}).get("trend")
        gp.write_text(json.dumps({"trend": smc_trend, "guven": 0.9,
                                  "zaman_dilimi": "15m",
                                  "zaman_utc": DAMGA19}), encoding="utf-8")
        r19b = _kos(_job(tmp, {"m15": str(m15), "h4": str(h4),
                               "gorsel": str(gp), "likidasyon": str(lp)}))
        K19 = {k["katman"]: k for k in r19b["katmanlar"]}
        adv = {d["name"]: d for d in K19["K3-COKLU-AJAN"]["danismanlar"]}
        gt = adv.get("gorsel-teyit", {})
        onay = K19["K4-AGI"]["verifier"].get("gorsel-teyit", {}).get("confirmed")
        # (c) görsel TERS → çürütülür + çelişki bayrağı
        ters = "bull" if smc_trend == "bear" else "bear"
        gp.write_text(json.dumps({"trend": ters, "guven": 0.9,
                                  "zaman_utc": DAMGA19}), encoding="utf-8")
        r19c = _kos(_job(tmp, {"m15": str(m15), "h4": str(h4),
                               "gorsel": str(gp), "likidasyon": str(lp)}))
        K19c = {k["katman"]: k for k in r19c["katmanlar"]}
        red = K19c["K4-AGI"]["verifier"].get("gorsel-teyit", {}).get("confirmed") is False
        bayrak = any("GÖRSEL-MEKANİK ÇELİŞKİSİ" in c
                     for c in K19c["K4-AGI"]["celiskiler"])
        kontrol("T19 zorunlu girdi kapısı + görsel/mekanik karşılıklı teyit",
                eksik_var and gt.get("stance") in ("long", "short")
                and gt.get("confidence") <= P.KONVANSIYON["gorsel_tavan"]
                and onay is True and red and bayrak
                and not r19b["ZIRVE"]["ZORUNLU_EKSIK"],
                f"eksik uyarısı={eksik_var}, görsel güven={gt.get('confidence')} "
                f"(tavan {P.KONVANSIYON['gorsel_tavan']}), uyumlu onay={onay}, "
                f"ters red={red}, çelişki bayrağı={bayrak}")

        # ---- T20: gözlemci ajanlar ihlali GERÇEKTEN yakalıyor mu? ---------
        temiz = GZ.denetle(r1)
        # (a) UYDURMA: kaynağı olmayan danışman enjekte et
        import copy  # noqa: PLC0415
        sahte = copy.deepcopy(r1)
        Ks = {k["katman"]: k for k in sahte["katmanlar"]}
        Ks["K3-COKLU-AJAN"]["danismanlar"].append(
            {"name": "hayalet-motor", "stance": "long", "confidence": 0.9,
             "evidence": "kaynaksız", "_ham_confidence": 0.9, "_agirlik": 1.0})
        d_uyd = GZ.denetle(sahte)
        # (b) EKSIK_AKTARIM: K3 danışmanını sentezden düşür
        sahte2 = copy.deepcopy(r1)
        Ks2 = {k["katman"]: k for k in sahte2["katmanlar"]}
        Ks2["K5-SI"]["sentez"]["danisman_ozeti"] = \
            Ks2["K5-SI"]["sentez"]["danisman_ozeti"][:1]
        d_eks = GZ.denetle(sahte2)
        # (c) MEMNUN_ETME: yön skoru ile YON_BIAS'ı çelişir yap
        sahte3 = copy.deepcopy(r1)
        Ks3 = {k["katman"]: k for k in sahte3["katmanlar"]}
        Ks3["K5-SI"]["sentez"]["YON_BIAS"] = "LONG"
        Ks3["K5-SI"]["sentez"]["yon_skoru"] = -0.5
        d_mem = GZ.denetle(sahte3)
        kontrol("T20 gözlemci ajanlar ihlali yakalıyor (uydurma/eksik/memnun etme)",
                (not temiz["muhurlendi"])
                and any("UYDURMA" in x for x in d_uyd["kritik_ihlal"])
                and any("EKSIK_AKTARIM" in x for x in d_eks["kritik_ihlal"])
                and any("MEMNUN_ETME" in x for x in d_mem["kritik_ihlal"])
                and d_uyd["muhurlendi"] and d_eks["muhurlendi"] and d_mem["muhurlendi"],
                f"temiz koşu mühürsüz={not temiz['muhurlendi']}, "
                f"uydurma yakalandı={bool(d_uyd['kritik_ihlal'])}, "
                f"eksik aktarım={bool(d_eks['kritik_ihlal'])}, "
                f"memnun etme={bool(d_mem['kritik_ihlal'])}")

        # ---- T21: iddia denetçisi kaynaksız sayıyı yakalıyor mu? ----------
        kaynakli_sayi = r1["ZIRVE"]["yon_skoru"]
        # Uydurma sayı, raporda GERÇEKTEN olmayan bir değer olmalı: sabit bir
        # sayı seçilirse rapor büyüdükçe tesadüfen "kaynaklı" çıkabilir (bir kez
        # oldu: eşik kalibrasyonu rapora 87 yazdı, test %87.3 kullanıyordu ve
        # %0.5 toleransa takıldı). Bu yüzden değer rapordan UZAK seçilir.
        _kaynak_sayilari = ID.rapor_sayilari(r1)
        uydurma = 87.3
        while any(abs(uydurma - k) <= 0.005 * max(1.0, abs(k))
                  for k in _kaynak_sayilari):
            uydurma += 0.37
        m_iyi = f"Yön skoru {kaynakli_sayi} olarak ölçüldü."
        m_kotu = f"Yön skoru {kaynakli_sayi} ve isabet oranı %{uydurma:.2f} idi."
        i_iyi = ID.denetle(m_iyi, r1)
        i_kotu = ID.denetle(m_kotu, r1)
        kontrol("T21 iddia denetçisi: kaynaksız sayı yakalanır",
                i_iyi["gecti"] and (not i_kotu["gecti"])
                and any(abs(k["deger"] - round(uydurma, 2)) < 1e-9
                        for k in i_kotu["KAYNAKSIZ"]),
                f"kaynaklı metin geçti={i_iyi['gecti']}, uydurma "
                f"%{uydurma:.2f} yakalandı={not i_kotu['gecti']}")

        # ---- T22: sabit-USDT hedef motoru kapıları ------------------------
        TABAN = {"sembol": "ETHUSDT", "yon": "long", "kontrat": 3.0,
                 "teminat": 400.0, "stop_usdt": 100.0, "hedef_usdt": [135, 150],
                 "fiyat": 1859.61, "atr_kurulum": 23.58,
                 "giris_adaylari": [1859.61],
                 "likidite_hedefleri": [1906.0],          # band İÇİNDE
                 "karsi_yapi_seviyeleri": [1847.89]}
        iyi = UH.hesapla(TABAN)
        # (a) R kapısı: hedef 90–120 → R 0.9–1.2 < 1.35
        dusuk_r = UH.hesapla({**TABAN, "hedef_usdt": [90, 120]})
        # (b) stop ölçeği: 15m ATR ile stop 7.14×ATR → ölçek dışı
        yanlis_tf = UH.hesapla({**TABAN, "atr_kurulum": 4.67})
        # (c) yapı kapısı: likidite bandın dışında
        yapisiz = UH.hesapla({**TABAN, "likidite_hedefleri": [1909.9]})
        # (d) tasfiye kapısı: teminat 90 USDT → tasfiye 30 puan < stop 33.33
        tasfiye = UH.hesapla({**TABAN, "teminat": 90.0})
        # çevrim aritmetiği birebir doğru mu?
        c = iyi["cevrim"]
        aritmetik = (abs(c["stop_mesafe_puan"] - 100/3) < 1e-3  # çıktı 4 haneye yuvarlı
                     and c["hedef_mesafe_puan"] == [45.0, 50.0]
                     and c["R_band"] == [1.35, 1.5])
        # brüt/net ayrımı: net istenirse komisyon eklenip brüte çevrilmeli
        brut = UH.hesapla(TABAN)                      # varsayılan brüt
        net = UH.hesapla({**TABAN, "hedef_tipi": "net"})
        brut_net_ok = (brut["cevrim"]["hedef_brut_usdt"] == [135.0, 150.0]
                       and net["cevrim"]["hedef_brut_usdt"][0] > 135.0
                       and abs(net["cevrim"]["net_kazanc_band_usdt"][0] - 135.0) < 0.01)
        kontrol("T22b brüt/net ayrımı", brut_net_ok,
                f"brüt hedef {brut['cevrim']['hedef_brut_usdt']} → net "
                f"{brut['cevrim']['net_kazanc_band_usdt']} | net istenirse brüt "
                f"{net['cevrim']['hedef_brut_usdt']} → net "
                f"{net['cevrim']['net_kazanc_band_usdt']}")

        kontrol("T22 sabit-USDT motoru: çevrim + 5 kapı",
                iyi["HUKUM"] == "UYGUN" and aritmetik
                and "R ≥ r_min" in dusuk_r["dusen_kapilar"]
                and "stop ölçeği" in yanlis_tf["dusen_kapilar"]
                and "yapı hedefi bandın içinde" in yapisiz["dusen_kapilar"]
                and "tasfiye > stop" in tasfiye["dusen_kapilar"],
                f"uygun={iyi['HUKUM']}, düşük-R reddi={bool(dusuk_r['dusen_kapilar'])}, "
                f"15m ölçek reddi={'stop ölçeği' in yanlis_tf['dusen_kapilar']}, "
                f"yapısız hedef reddi={'yapı hedefi bandın içinde' in yapisiz['dusen_kapilar']}, "
                f"tasfiye reddi={'tasfiye > stop' in tasfiye['dusen_kapilar']}")

        # ---- T23: çift sembollü paket (v2) doğru klasörlere açılıyor mu? ---
        gercek_m15 = json.loads(m15.read_text(encoding="utf-8"))
        gercek_h4 = json.loads(h4.read_text(encoding="utf-8"))
        paket2 = {"paket": "piramit-veri", "surum": 2,
                  "semboller": ["BTCUSDT", "ETHUSDT"], "cekim_utc": "test",
                  "veri": {"BTCUSDT": {"m15": gercek_m15, "h4": gercek_h4,
                                       "premiumIndex": {"symbol": "BTCUSDT",
                                                        "lastFundingRate": "0.0001"}},
                           "ETHUSDT": {"m15": gercek_m15, "h4": gercek_h4}}}
        kok = tmp / "coklu"
        eski_g, eski_h = PA.GIRDI, PA.HAM
        PA.GIRDI, PA.HAM = kok, kok / "turev_ham"
        try:
            r23 = PA.ac_coklu(paket2)
        finally:
            PA.GIRDI, PA.HAM = eski_g, eski_h
        btc_yer = (kok / "m15.json").exists()
        eth_yer = (kok / "eth" / "m15.json").exists()
        ayri = btc_yer and eth_yer
        kontrol("T23 çift sembollü paket: BTC ana dizine, ETH alt dizine",
                ayri and set(r23["semboller"]) == {"BTCUSDT", "ETHUSDT"}
                and r23["ana_sembol"] == "BTCUSDT"
                and r23["sonuc"]["ETHUSDT"]["yazilan"].get("m15"),
                f"BTC={btc_yer}, ETH={eth_yer}, ana={r23['ana_sembol']}")

        # ---- T24: korelasyon motoru --------------------------------------
        # (a) AYNI seri → ρ = 1.0 → KOPYA POZİSYON
        r24a = KOR.olc(kok / "m15.json", kok / "eth" / "m15.json",
                       "BTC", "ETH", KOR.KONVANSIYON)
        # (b) zıt seri → ρ = -1.0 (mutlak değer eşiği kopya der)
        ters = [[x[0], x[1], x[2], x[3], str(2 * 65000 - float(x[4])), *x[5:]]
                for x in gercek_m15]
        (kok / "ters.json").write_text(json.dumps(ters), encoding="utf-8")
        r24b = KOR.olc(kok / "m15.json", kok / "ters.json", "BTC", "TERS",
                       KOR.KONVANSIYON)
        # (c) yetersiz hizalı bar → fail-closed
        az = gercek_m15[:5]
        (kok / "az.json").write_text(json.dumps(az), encoding="utf-8")
        try:
            KOR.olc(kok / "m15.json", kok / "az.json", "BTC", "AZ", KOR.KONVANSIYON)
            fail_closed = False
        except KOR.KorelasyonError:
            fail_closed = True
        kontrol("T24 korelasyon: aynı seri ρ=1, ters seri ρ<0, az veri fail-closed",
                abs(r24a["korelasyon"] - 1.0) < 1e-6
                and r24a["HUKUM"] == "KOPYA POZİSYON"
                and r24a["toplam_risk_carpani"] == 2.0
                and r24b["korelasyon"] < -0.9 and fail_closed,
                f"aynı ρ={r24a['korelasyon']} ({r24a['HUKUM']}), "
                f"ters ρ={r24b['korelasyon']}, az veri reddi={fail_closed}")

        # ---- T25: korelasyon + usd_hedef BORU HATTINDA ve DENETLENİYOR ----
        prof = tmp / "profil.json"
        prof.write_text(json.dumps({"sembol": "TEST", "kontrat": 3.0,
                                    "teminat": 400.0, "stop_usdt": 100.0,
                                    "hedef_usdt": [135, 150],
                                    "hedef_tipi": "brut"}), encoding="utf-8")
        j25 = _job(tmp, {"m15": str(m15), "h4": str(h4)})
        d25 = json.loads(j25.read_text(encoding="utf-8"))
        d25["korelasyon"] = {"a": str(m15), "b": str(m15), "ad_a": "X", "ad_b": "Y"}
        d25["usd_profil"] = str(prof)
        j25.write_text(json.dumps(d25, ensure_ascii=False), encoding="utf-8")
        r25 = _kos(j25)
        K25 = {k["katman"]: k for k in r25["katmanlar"]}
        kor = K25["K2-AI-AJAN"]["motor_sonuclari"].get("korelasyon")
        usd = K25["K5-SI"].get("usd_hedef")
        g25 = r25["DENETIM"]["gozlemciler"]
        # gözlemci kanıtları: beyan denetimi + usd girdi kaynağı
        k2_beyan = any("beyan edilen" in b["kanit"] for b in g25["K2-AI-AJAN"])
        k5_usd = any("sabit-USDT" in b["kanit"] for b in g25["K5-SI"])
        kor_celiski = any("KORELASYON" in c for c in K25["K4-AGI"]["celiskiler"])
        # (b) BEYAN edilip koşmazsa İHLAL: motor yolunu boz
        import copy  # noqa: PLC0415
        sahte = copy.deepcopy(r25)
        Ks = {k["katman"]: k for k in sahte["katmanlar"]}
        del Ks["K2-AI-AJAN"]["motor_sonuclari"]["korelasyon"]
        d_ihlal = GZ.denetle(sahte)
        kontrol("T25 korelasyon+usd_hedef boru hattında ve gözlemci kapsamında",
                isinstance(kor, dict) and kor.get("HUKUM") == "KOPYA POZİSYON"
                and isinstance(usd, dict) and usd.get("HUKUM")
                and k2_beyan and k5_usd and kor_celiski
                and any("sessizce atlandı" in x for x in d_ihlal["kritik_ihlal"]),
                f"korelasyon={kor.get('HUKUM') if kor else None}, usd={usd.get('HUKUM') if usd else None}, "
                f"K2 beyan denetimi={k2_beyan}, K5 usd denetimi={k5_usd}, "
                f"K4 çelişki={kor_celiski}, atlama yakalandı="
                f"{bool(d_ihlal['kritik_ihlal'])}")

        # ---- T26: HESAP VERME + KIYAS (önceki karar tuttu mu, piyasa döndü mü)
        # (a) akıbet: bilinen sonuçlu senaryo — SHORT hedefe gitti
        b26 = [(1, 100, 100.5, 99.5, 100, 1.0), (2, 100, 100.2, 95.5, 96, 1.0)]
        onceki = {"son_bar": 1, "son_bar_utc": "T-1", "YON_BIAS": "SHORT",
                  "yon_skoru": -0.5, "son_kapanis": 100.0,
                  "islem_seviyeleri": {"giris": 100.0, "stop": 102.0, "hedef": 96.0},
                  "danismanlar": {"m1": "short", "m2": "long"},
                  "surucu": {"trend": "bear", "adx": 25.0, "turev_skor": 0.7}}
        a26 = KY.akibet_olc(onceki, b26, {"azami_bekleme": 3, "azami_tutma": 5})
        # (b) kıyas: yön DÖNÜŞÜ + sürücü değişimi yakalanmalı
        yeni = {"son_bar_utc": "T0", "YON_BIAS": "LONG", "yon_skoru": 0.4,
                "son_kapanis": 96.0,
                "danismanlar": {"m1": "long", "m2": "long"},
                "surucu": {"trend": "bull", "adx": 25.5, "turev_skor": -0.6}}
        k26 = KY.kiyasla(onceki, yeni)
        yd = k26["YON_DEGISIMI"]
        # (c) kayıt yoksa UYDURMA yok — VERİ YOK demeli
        bos = KY.kiyasla({}, yeni)
        bos_a = KY.akibet_olc({}, b26)
        kontrol("T26 hesap verme + kıyas (akıbet ölçümü, yön dönüşü, fail-closed)",
                a26["durum"] == "ÖLÇÜLDÜ" and a26["sonuc"] == "T1"
                and a26["gercek_r"] == 2.0
                and yd["etiket"] == "DÖNÜŞ" and yd["skor_delta"] == 0.9
                and any("türev" in d for d in k26["onemli_degisimler"])
                and any("m1" in d for d in k26["danisman_donusleri"])
                and P.YOK in bos["durum"] and P.YOK in bos_a["durum"],
                f"akıbet={a26['sonuc']} R={a26['gercek_r']}, yön={yd['etiket']} "
                f"Δskor={yd['skor_delta']}, sürücü={len(k26['onemli_degisimler'])} "
                f"değişim, kayıtsız fail-closed=True")

        # ---- T27: çapraz-sembol hafıza izolasyonu -------------------------
        # İkinci sembol (ör. ETH) kendi state dizininde koşunca ana sembolün
        # öğrenilmiş ağırlığı EZİLMEMELİ. Bu bir P0'dı: tek global agirlik.json
        # ETH koşusunda BTC sicilinin yerine geçiyordu (2026-07-24).
        ana = P.ENGINE / "state"
        ikinci = P.ENGINE / "state" / "eth"
        kum = tmp / "kum_havuzu"
        y_ana, y_ikinci = P._hafiza_yolu(ana), P._hafiza_yolu(ikinci)
        # kum havuzu: YAZMA geçici dizine, OKUMA gerçek sicile → ana hafıza
        y_kum = P._hafiza_yolu(P._okuma_dizini(
            {"state_dir": str(kum), "defter_dizini": str(ana)}, tmp))
        # T4/T5 sicili (engine/state dışı): hafıza sicilin yanında, depo
        # hafıza dizini geçici koşularla KİRLENMEZ
        y_test = P._hafiza_yolu(tmp / "kal_state")
        kontrol("T27 çapraz-sembol hafıza izolasyonu",
                y_ana == P.AGIRLIK_DOSYA and y_ikinci != y_ana
                and y_ikinci.name == "agirlik_eth.json" and y_kum == y_ana
                and y_test == (tmp / "kal_state" / "agirlik.json").resolve()
                and P.HAFIZA_DIR not in y_test.parents,
                f"ana={y_ana.name}, ikinci={y_ikinci.name}, "
                f"kum_havuzu→{y_kum.name} (gerçek sicil), "
                f"geçici sicil→kendi dizini ({y_test.parent.name}/)")

        # ---- T28: zorunlu girdi TAZELİĞİ ----------------------------------
        # Eski panel okuması yeni kline'la birlikte "güncel" sayılamaz; damgasız
        # okuma da kanıtsızdır (fail-closed). Kusur 2026-07-25'te bulundu.
        z_dir = tmp / "zorunlu"
        (z_dir / "turev_ham").mkdir(parents=True, exist_ok=True)
        m15v = json.loads(m15.read_text(encoding="utf-8"))
        son_ms = m15v[-1][0]
        eski = son_ms - (P.KONVANSIYON["zorunlu_damga_tolerans_dk"] + 60) * 60_000
        import datetime as _dt

        def _utc(ms):
            return _dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc
                                              ).strftime("%Y-%m-%d %H:%M")
        senaryo = {}
        for ad, lik in (("taze", {"liq_long": 1.0, "liq_short": 2.0,
                                  "zaman_utc": _utc(son_ms)}),
                        ("bayat", {"liq_long": 1.0, "liq_short": 2.0,
                                   "zaman_utc": _utc(eski)}),
                        ("damgasiz", {"liq_long": 1.0, "liq_short": 2.0})):
            (z_dir / "turev_ham" / "likidasyon.json").write_text(
                json.dumps(lik), encoding="utf-8")
            (z_dir / "gorsel.json").write_text(json.dumps(
                {"trend": "bear", "zaman_utc": _utc(son_ms)}), encoding="utf-8")
            jz = _job(tmp, {"m15": str(m15), "h4": str(h4),
                            "likidasyon": str(z_dir / "turev_ham" / "likidasyon.json"),
                            "gorsel": str(z_dir / "gorsel.json")})
            j = json.loads(jz.read_text(encoding="utf-8"))
            j["state_dir"] = str(tmp / f"z_{ad}")
            jz.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
            k1z = [k for k in _kos(jz)["katmanlar"] if k["katman"] == "K1-LLM"][0]
            senaryo[ad] = (k1z.get("zorunlu_girdiler", {}).get("likidasyon") is not None,
                           " ".join(k1z.get("zorunlu_eksik") or []))
        kontrol("T28 zorunlu girdi tazeliği (bayat/damgasız kabul edilmez)",
                senaryo["taze"][0] and not senaryo["bayat"][0]
                and "BAYAT" in senaryo["bayat"][1]
                and not senaryo["damgasiz"][0]
                and "damgası YOK" in senaryo["damgasiz"][1],
                f"taze kabul={senaryo['taze'][0]}, bayat red={not senaryo['bayat'][0]}, "
                f"damgasız red={not senaryo['damgasiz'][0]}")

        # ---- T29: kanca — paket alımı geri sarmaz, ikinci sembol koşar -----
        sys.path.insert(0, str(P.REPO / ".claude" / "hooks"))
        import piramit_auto as HOOK                                # noqa: PLC0415
        pk = tmp / "piramit_veri_TEST_1.json"
        pk.write_text(json.dumps({"veri": {"m15": m15v}}), encoding="utf-8")
        eski_pk = tmp / "piramit_veri_TEST_0.json"
        eski_pk.write_text(json.dumps(
            {"veri": {"m15": m15v[:-4]}}), encoding="utf-8")     # 4 bar geride
        # _paket_zamani artık SEMBOL→bar haritası döner (v2 paket desteği)
        pms = (HOOK._paket_zamani(pk)[0] or {}).get("_ANA")
        ems = (HOOK._paket_zamani(eski_pk)[0] or {}).get("_ANA")
        # v2 çok-sembollü paket de okunabilmeli (adversarial denetimde kırıldı)
        v2 = tmp / "piramit_veri_BTC_ETH_2.json"
        v2.write_text(json.dumps({
            "semboller": ["BTCUSDT", "ETHUSDT"], "ana_sembol": "BTCUSDT",
            "veri": {"BTCUSDT": {"m15": m15v}, "ETHUSDT": {"m15": m15v[:-8]}}}),
            encoding="utf-8")
        v2h = HOOK._paket_zamani(v2)[0] or {}
        v2_ok = (v2h.get("_ANA") == son_ms and v2h.get("ETHUSDT") is not None
                 and v2h["ETHUSDT"] < son_ms)
        # şema tanınmazsa fail-closed: bar okunamaz → harita boş
        bos = tmp / "piramit_veri_BOZUK.json"
        bos.write_text(json.dumps({"veri": {"beklenmeyen": 1}}), encoding="utf-8")
        fc_ok = not (HOOK._paket_zamani(bos)[0] or {})
        ij = HOOK._ikinci_job()
        kontrol("T29 kanca: paket zamanı okunur, ikinci sembol job'u kurulur",
                pms == son_ms and ems is not None and ems < pms
                and ij is not None and ij.get("usd_profil")
                and ij.get("korelasyon") and "eth" in ij["defter_dizini"]
                and v2_ok and fc_ok,
                f"paket son bar={int(pms)} > eski={int(ems)}, "
                f"ikinci sembol job: usd_profil={bool(ij and ij.get('usd_profil'))}, "
                f"korelasyon={bool(ij and ij.get('korelasyon'))} | "
                f"v2 çok-sembollü paket okundu={v2_ok}, tanınmayan şema "
                f"fail-closed={fc_ok}")

        # ---- T30: karar kapıları VERİDEN türetiliyor -----------------------
        sys.path.insert(0, str(_HERE))
        import esik_kalibre as EK                                # noqa: PLC0415
        # (a) bölünmüş kurul daha YÜKSEK score eşiği ister (gürültü büyük)
        birlik = [{"name": f"m{i}", "stance": "short", "confidence": 0.8}
                  for i in range(4)]
        bolunmus = [{"name": "m0", "stance": "short", "confidence": 0.8},
                    {"name": "m1", "stance": "long", "confidence": 0.8},
                    {"name": "m2", "stance": "short", "confidence": 0.8},
                    {"name": "m3", "stance": "long", "confidence": 0.8}]
        ver = {f"m{i}": {"confirmed": True} for i in range(4)}
        e_bir = EK.esikler({"advisors": birlik, "verifier": ver,
                            "m15": str(m15), "r_min": 1.35})
        e_bol = EK.esikler({"advisors": bolunmus, "verifier": ver,
                            "m15": str(m15), "r_min": 1.35})
        # (b) determinizm: aynı girdi = aynı eşik
        e_bir2 = EK.esikler({"advisors": birlik, "verifier": ver,
                             "m15": str(m15), "r_min": 1.35})
        # (c) veri yoksa STATİK korkuluğa düşer ve etiketler
        e_yok = EK.esikler({"advisors": birlik, "verifier": ver, "r_min": 1.35})
        # (d) yön ağırlığı eşiği ÖLÇEKLİ: toplam ağırlıkla büyür (0.60 sabiti değil)
        iki = EK.esikler({"advisors": birlik[:2], "verifier": ver,
                          "m15": str(m15), "r_min": 1.35})
        kontrol("T30 karar kapıları veriden türetiliyor (kurul + rejim)",
                e_bol["esikler"]["score"] > e_bir["esikler"]["score"]
                and e_bir2["esikler"] == e_bir["esikler"]
                and "STATİK" in e_yok["kaynak"]
                and e_yok["esikler"] == EK.KONVANSIYON["statik"]
                and e_bir["esikler"]["min_side_weight"] >
                iki["esikler"]["min_side_weight"],
                f"birlik score={e_bir['esikler']['score']} < bölünmüş "
                f"{e_bol['esikler']['score']}; determinist=True; verisiz→statik; "
                f"yön ağırlığı 4 danışman {e_bir['esikler']['min_side_weight']} > "
                f"2 danışman {iki['esikler']['min_side_weight']}")

        # ---- T31: rejim ölçümü + sertlik yönü -----------------------------
        # Sentetik seriler (determinist LCG): sürüklenen rastgele yürüyüş
        # (yön devam eder) vs Ornstein-Uhlenbeck (ortalamaya döner).
        _r = EK._rng(11)
        x, ou = 100.0, []
        for _ in range(400):
            x = x + 0.5 * (100.0 - x) + 2.0 * (_r() - 0.5)
            ou.append(x)
        y, rw = 100.0, []
        for _ in range(400):
            y = y * (1.0 + 0.002 + 0.004 * (_r() - 0.5))
            rw.append(y)
        r_tr, r_ou = EK.rejim_olc(rw, 1.35, 8), EK.rejim_olc(ou, 1.35, 8)
        vr_tr, vr_ou = EK.varyans_orani(rw, 8), EK.varyans_orani(ou, 8)
        sf = EK.signflip_tani(SZ.satirlar(birlik, ver), 0.05, 200, 7)
        kontrol("T31 rejim ölçümü: trend gevşetmez, dönüş rejimi SIKILAŞTIRIR",
                r_tr["sertlik"] == 1.0 and r_ou["sertlik"] > 1.0
                and vr_tr["VR"] > 1.0 and vr_ou["VR"] < 1.0
                and r_tr["devamlilik"]["p_wilson_lo"] >
                r_ou["devamlilik"]["p_wilson_lo"]
                and sf["alpha_ulasilabilir"] is False,
                f"trend: VR={vr_tr['VR']} p_lo={r_tr['devamlilik']['p_wilson_lo']} "
                f"sertlik={r_tr['sertlik']} | dönüş: VR={vr_ou['VR']} "
                f"p_lo={r_ou['devamlilik']['p_wilson_lo']} sertlik={r_ou['sertlik']} "
                f"| sign-flip α ulaşılabilir={sf['alpha_ulasilabilir']} "
                f"(p_min={sf['p_min_ulasilabilir']})")

        # ---- T32: TETİKLENMEMİŞ işleme R YAZILMAZ (market-dolum kusuru) ----
        # Gerçek olayda yakalandı (2026-07-25): anlık görüntü yalnız tek `giris`
        # taşıyordu, akıbet ölçer bunu "market dolum" sanıp fiyat oraya HİÇ
        # gitmediği halde +1.9073 R / T1 yazdı. Artık dolum ancak fiyat
        # DOKUNURSA sayılır; market yalnız AÇIKÇA beyan edilirse.
        b32 = [_bar(i, 100 - i, 101 - i, 99 - i, 100 - i) for i in range(12)]
        # SHORT, giriş fiyatın ÜSTÜNDE: fiyat yukarı hiç gitmiyor → dolmamalı
        k32 = {"karar": "SHORT", "yon": "SHORT", "giris": 130.0,
               "giris_alt": 130.0, "giris_ust": 130.0,
               "stop": 140.0, "t1": 95.0, "iptal": 140.0}
        s_limit = AE.simule_et(k32, 0, b32, P_ET)
        s_market = AE.simule_et({**k32, "giris_tipi": "market"}, 0, b32, P_ET)
        # anlık görüntü bölgeyi taşıyor mu?
        ag = P._anlik_goruntu(
            *[[k for k in r1["katmanlar"] if k["katman"] == x][0]
              for x in ("K1-LLM", "K2-AI-AJAN", "K3-COKLU-AJAN", "K5-SI")],
            r1["ZIRVE"])
        sev = ag.get("islem_seviyeleri") or {}
        bolge_var = (not sev) or all(a in sev for a in
                                     ("giris_alt", "giris_ust", "iptal", "giris_tipi"))
        kontrol("T32 tetiklenmemiş işleme R yazılmaz + bölge kaydediliyor",
                (not s_limit["olculebilir"]) and "R yazılmaz" in s_limit["sonuc"]
                and s_market["olculebilir"] and bolge_var,
                f"limit (dokunulmadı)={s_limit['sonuc'][:38]}… | market beyan "
                f"edilince ölçüldü={s_market.get('sonuc')} r={s_market.get('r')} | "
                f"anlık görüntüde bölge alanları={bolge_var}")

        # ---- T33: EMİR PLANI — karar MARKET/LIMIT emrine çevriliyor -------
        import emir_plani as EP                                  # noqa: PLC0415
        # (a) sabit-USDT profiliyle: seviyeler üretilmeli, hepsi TUTARLI.
        # SABİT FIXTURE — canlı `engine/girdi/eth` DEĞİL. Test canlı piyasa
        # verisine bağlıyken, o günün yapısı aday üretmeyince ("0 aday") test
        # kırmızıya düşüyor ve KOD sağlamken REGRESYON gibi görünüyordu. Bir
        # öz-test kodu sınar, piyasayı değil; girdi bu yüzden dondurulmuştur.
        SABIT = P.SKILL_DIR / "tests" / "sabit"
        e_eth = EP.plan({"sembol": "ETHTEST", "yon": "LONG",
                         "m15": str(SABIT / "eth_m15.json"),
                         "h4": str(SABIT / "eth_h4.json"),
                         "profil": {"kontrat": 3.0, "teminat": 400.0,
                                    "stop_usdt": 100.0, "hedef_usdt": [135.0, 150.0],
                                    "hedef_tipi": "brut",
                                    "esikler": {"r_min": 1.35}}})
        ad = e_eth.get("adaylar") or []
        # stop mesafesi profilden gelmeli: 100/3 = 33.3333 puan
        mesafe_ok = all(abs(abs(a["giris"] - a["stop"]) - 100 / 3.0) < 0.01 for a in ad)
        tip_ok = all(a["emir_tipi"] in ("MARKET", "LIMIT") for a in ad)
        rr_ok = all(a["rr_denetim"] == "TUTARLI" and a["R"] >= 1.35 for a in ad)
        usd_ok = all((a.get("usd_hedef") or {}).get("HUKUM") == "UYGUN" for a in ad)
        # (b) yön NÖTR ise emir üretilmez (fail-closed)
        e_notr = EP.plan({"yon": "NÖTR", "m15": str(m15), "h4": str(h4)})
        # (c) uydurma seviye yok: her giriş ölçülen yapıdan gelmeli
        gerekce_ok = all(("FVG" in a["giris_gerekcesi"] or "swing" in a["giris_gerekcesi"]
                          or "fiyat" in a["giris_gerekcesi"]) for a in ad)
        kontrol("T33 emir planı: MARKET/LIMIT + ölçülmüş seviye + denetim",
                bool(ad) and mesafe_ok and tip_ok and rr_ok and usd_ok and gerekce_ok
                and e_notr["EMIR"] == "EMİR YOK",
                f"{len(ad)} aday, hepsi TUTARLI+UYGUN={rr_ok and usd_ok}, "
                f"stop mesafesi profilden={mesafe_ok}, emir tipi={tip_ok}, "
                f"yönsüzde emir yok={e_notr['EMIR'] == 'EMİR YOK'}")

        # ---- T34: ÇELİŞKİ TURU — yön doğrulanmamışa dayanıyorsa NÖTR ------
        sj = {"question": "çelişki testi",
              # a: DOĞRULANMAMIŞ long (ceza sonrası 1.0×0.25=0.25)
              # b: DOĞRULANMIŞ short (0.2) → tüm kurul LONG, doğrulanmış kurul SHORT
              "advisors": [{"name": "a", "stance": "long", "confidence": 1.0},
                           {"name": "b", "stance": "short", "confidence": 0.2}],
              "verifier": {"b": {"confirmed": True}}}   # LONG doğrulanmamış
        s_ilk = SZ.synth(sj)          # ilk sentez (tüm kurul)
        ct = P._celiski_turu(sj, s_ilk)
        # doğrulanmamış (a) dışlanınca yön SHORT'a döner → DAYANIKSIZ
        kontrol("T34 çelişki turu: doğrulanmamışa dayanan yön fail-closed",
                ct["kostu"] and ct["yon_dayaniksiz"]
                and "DAYANIKSIZ" in ct["hukum"],
                f"ilk yön={ct.get('yon_ilk')} → doğrulanmış kurul="
                f"{ct.get('yon_dogrulanmis_kurul')} | dayanıksız={ct['yon_dayaniksiz']}")

        # ---- T35: turev-akis BAĞIMSIZ doğrulanır (kendi beyanıyla DEĞİL) ---
        # Protokol: "hiçbir kaynak kendini doğrulamaz". Kapsam, motorun
        # GİRDİSİNDEN (turev.json) ölçülür; motorun `rapor.kapsam` beyanı yalnız
        # ÇAPRAZ KONTROL içindir — ayrışırsa motor kendi kapsamını yanlış
        # raporluyordur ve danışman ÇÜRÜTÜLÜR (fail-closed).
        def _tv_k4(bagimsiz, beyan):
            k2f = {"motor_sonuclari": {"turev-akis": {
                       "rapor": {"kapsam": beyan},
                       "danisman": {"name": "turev-akis", "stance": "long",
                                    "confidence": 0.7},
                       "_bagimsiz_kapsam": {"kapsam": bagimsiz,
                                            "dolu_kanallar": ["cvd"],
                                            "eksik_kanallar": []}}},
                   "hatalar": []}
            k3f = {"danismanlar": [
                       {"name": "turev-akis", "stance": "long", "confidence": 0.7},
                       {"name": "gorsel-teyit", "stance": "long", "confidence": 0.4}],
                   "seviyeler": {}}
            r = P.k4_agi({}, {"zorunlu_girdiler": {}, "zorunlu_eksik": []}, k2f, k3f)
            return r["verifier"].get("turev-akis", {}), r["dogrulama_gerekceleri"]

        # (a) kanal ölçümü: ağırlıklar turev_akis'in aynası
        tam = {"oi_series": [1, 2], "price_series": [1, 2], "funding": 0.01,
               "cvd_series": [1, 2], "taker_lsr": 1.1, "liq_long": 1.0,
               "liq_short": 2.0}
        olc_tam = P._turev_kanal_olc(tam)["kapsam"]
        olc_oisiz = P._turev_kanal_olc(
            {k: v for k, v in tam.items()
             if k not in ("oi_series", "price_series")})["kapsam"]
        olc_tek = P._turev_kanal_olc({**tam, "cvd_series": [1]})["kapsam"]
        # (b) üç doğrulama senaryosu
        v_ok, g_ok = _tv_k4(1.0, 1.0)          # tam kapsam, beyan uyuşuyor
        v_dus, _ = _tv_k4(0.18, 0.18)          # eşik altı → çürütülür
        v_carp, _ = _tv_k4(0.34, 1.0)          # motor kapsamı ŞİŞİRMİŞ → çürütülür
        v_yok, _ = _tv_k4(None, 1.0)           # ölçüm yok → fail-closed
        # (c) DAİRESELLİK: gerekçe motorun KENDİ adına değil GİRDİ dosyasına dayanmalı
        dairesel_degil = "turev_girdi.py" in g_ok.get("turev-akis", "")
        kontrol("T35 turev-akis bağımsız doğrulanır (dairesel değil)",
                olc_tam == 1.0 and abs(olc_oisiz - 0.66) < 1e-9 and abs(olc_tek - 0.82) < 1e-9
                and v_ok.get("confirmed") is True
                and v_dus.get("confirmed") is False
                and v_carp.get("confirmed") is False
                and "ÇARPIŞMA" in v_carp.get("reason", "")
                and v_yok.get("confirmed") is False
                and dairesel_degil,
                f"ölçüm tam={olc_tam} OI'siz={olc_oisiz} tek-nokta={olc_tek} | "
                f"onay={v_ok.get('confirmed')} eşik-altı={v_dus.get('confirmed')} "
                f"çarpışma={v_carp.get('confirmed')} ölçümsüz={v_yok.get('confirmed')} | "
                f"gerekçe girdiye dayanıyor={dairesel_degil}")

        # T12: bar arşivi — karar penceresi kaysa bile akıbet ölçülebilir
        ars = tmp / "arsiv.jsonl"
        AE.arsiv_guncelle(ars, b8)                       # eski pencere arşive girdi
        yeni_pencere = [_bar(9, 90, 91, 89, 90)]         # karar barı ARTIK yok
        kapsamsiz = AE.simule_et(MARKET_SHORT, 1, yeni_pencere, P_ET)
        birlesik = AE.bar_yukle([str(ars)])
        kapsamli = AE.simule_et(MARKET_SHORT, 1, birlesik, P_ET)
        kontrol("T12 bar arşivi kayan pencereyi telafi eder",
                (not kapsamsiz["olculebilir"]) and kapsamli["olculebilir"]
                and kapsamli["r"] == 2.0,
                f"arşivsiz={kapsamsiz['sonuc'][:28]}… | arşivli r={kapsamli.get('r')}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if yedek is not None:
            agirlik_p.write_text(yedek, encoding="utf-8")
        elif agirlik_p.exists():
            agirlik_p.unlink()

    print("-" * 60)
    print(f"GEÇEN {len(GECEN)} / {len(GECEN) + len(KALAN)}")
    if KALAN:
        print("KALAN:")
        for k in KALAN:
            print("  ✖", k)
    return 0 if not KALAN else 1


if __name__ == "__main__":
    sys.exit(main())
