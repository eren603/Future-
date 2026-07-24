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
        MARKET_SHORT = {"karar": "SHORT", "yon": "SHORT", "giris_alt": 100.0,
                        "giris_ust": 100.0, "giris": 100.0, "stop": 102.0,
                        "t1": 96.0, "iptal": 101.0}

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
                 "iptal": 107.0}
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
        lp.write_text(json.dumps({"liq_long": 12.4, "liq_short": 31.8}),
                      encoding="utf-8")
        # (a) EKSİK durumda uyarı taşınmalı
        r19a = _kos(_job(tmp, {"m15": str(m15), "h4": str(h4)}))
        eksik_var = len(r19a["ZIRVE"].get("ZORUNLU_EKSIK", [])) == 2
        # (b) görsel MEKANİKLE UYUMLU → doğrulanır
        smc_trend = None
        for k in r19a["katmanlar"]:
            if k["katman"] == "K2-AI-AJAN":
                smc_trend = (k["motor_sonuclari"].get("smc_tespit") or {}).get("trend")
        gp.write_text(json.dumps({"trend": smc_trend, "guven": 0.9,
                                  "zaman_dilimi": "15m"}), encoding="utf-8")
        r19b = _kos(_job(tmp, {"m15": str(m15), "h4": str(h4),
                               "gorsel": str(gp), "likidasyon": str(lp)}))
        K19 = {k["katman"]: k for k in r19b["katmanlar"]}
        adv = {d["name"]: d for d in K19["K3-COKLU-AJAN"]["danismanlar"]}
        gt = adv.get("gorsel-teyit", {})
        onay = K19["K4-AGI"]["verifier"].get("gorsel-teyit", {}).get("confirmed")
        # (c) görsel TERS → çürütülür + çelişki bayrağı
        ters = "bull" if smc_trend == "bear" else "bear"
        gp.write_text(json.dumps({"trend": ters, "guven": 0.9}), encoding="utf-8")
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
        m_iyi = f"Yön skoru {kaynakli_sayi} olarak ölçüldü."
        m_kotu = f"Yön skoru {kaynakli_sayi} ve isabet oranı %87.3 idi."
        i_iyi = ID.denetle(m_iyi, r1)
        i_kotu = ID.denetle(m_kotu, r1)
        kontrol("T21 iddia denetçisi: kaynaksız sayı yakalanır",
                i_iyi["gecti"] and (not i_kotu["gecti"])
                and any(abs(k["deger"] - 87.3) < 1e-9 for k in i_kotu["KAYNAKSIZ"]),
                f"kaynaklı metin geçti={i_iyi['gecti']}, uydurma %87.3 yakalandı="
                f"{not i_kotu['gecti']}")

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
