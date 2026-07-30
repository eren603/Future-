#!/usr/bin/env python3
"""grafik-calisma öz-testi: confluence + smc_tespit + setup_dogrulama.
Yön, geometri, confluence, ATR/MTF/rejim kapıları, otomatik tespit ve
tarihsel doğrulama (edge kanıtı) sınanır. SELF_TEST_OK basar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import confluence as cf  # noqa: E402
import smc_tespit as st  # noqa: E402
import setup_dogrulama as sd  # noqa: E402
import kalibrasyon as kb  # noqa: E402


def bars(moves, start=100.0, wick=0.2):
    """Deterministik sentetik mumlar: open=önceki kapanış. Fitiller yön-asimetrik
    (hareket yönünde tam, ters yönde yarım) ki ekstrem mum kesin ekstremi taşısın."""
    out = []
    prev = start
    for m in moves:
        op, cl = prev, prev + m
        if cl >= op:   # boğa mumu: üst fitil tam, alt fitil yarım
            hi, lo = cl + wick, op - wick / 2
        else:          # ayı mumu: alt fitil tam, üst fitil yarım
            hi, lo = op + wick / 2, cl - wick
        out.append({"open": op, "high": hi, "low": lo, "close": cl})
        prev = cl
    return out


def main():
    # ================= CONFLUENCE =================
    long_job = {
        "structure": {"event": "CHoCH", "direction": "bull"},
        "impulse": {"start": 100.0, "end": 120.0},   # golden zone ~[104.28,107.64]
        "order_blocks": [{"low": 104, "high": 106, "type": "demand"}],
        "liquidity": [{"price": 125, "type": "buyside"},
                      {"price": 95, "type": "sellside"}],
    }
    r = cf.synth(long_job)
    assert r["KARAR"] == "LONG", r
    assert r["golden_zone"][1] < 120, r
    assert 104 <= r["giris_bolgesi"][0] and r["giris_bolgesi"][1] <= 107.65, r
    assert r["gecersizlik_sl"] < r["giris_orta"], r
    assert r["hedefler"][0] == 125 and r["rr"] >= 2.0, r
    assert not r["kapi_gerekceleri"], r

    short_job = {
        "structure": {"event": "CHoCH", "direction": "bear"},
        "impulse": {"start": 120.0, "end": 100.0},
        "order_blocks": [{"low": 113, "high": 116, "type": "supply"}],
        "liquidity": [{"price": 95, "type": "sellside"},
                      {"price": 125, "type": "buyside"}],
    }
    r = cf.synth(short_job)
    assert r["KARAR"] == "SHORT", r
    assert r["golden_zone"][0] > 100, r
    assert r["gecersizlik_sl"] > r["giris_orta"], r
    assert r["hedefler"][0] == 95 and r["rr"] >= 2.0, r
    assert not r["kapi_gerekceleri"], r

    # yalnız fib → BEKLE
    r = cf.synth({"structure": {"event": "BOS", "direction": "bull"},
                  "impulse": {"start": 100.0, "end": 120.0},
                  "liquidity": [{"price": 125, "type": "buyside"}]})
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("confluence eksik" in g for g in r["kapi_gerekceleri"]), r

    # yapı-impuls çelişkisi → BEKLE
    r = cf.synth({"structure": {"event": "CHoCH", "direction": "bull"},
                  "impulse": {"start": 120.0, "end": 100.0},
                  "order_blocks": [{"low": 113, "high": 116, "type": "demand"}]})
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("çelişiyor" in g for g in r["kapi_gerekceleri"]), r

    # düşük R:R → BEKLE
    r = cf.synth({"structure": {"event": "CHoCH", "direction": "bull"},
                  "impulse": {"start": 100.0, "end": 120.0},
                  "order_blocks": [{"low": 104, "high": 106, "type": "demand"}],
                  "liquidity": [{"price": 108, "type": "buyside"}]})
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("R:R" in g for g in r["kapi_gerekceleri"]), r

    # golden zone geometri
    r = cf.synth(long_job)
    assert abs(r["golden_zone"][0] - 104.28) < 0.01, r
    assert abs(r["golden_zone"][1] - 107.64) < 0.01, r

    # CANLILIK: gerçek confluence + makul hedef → hep ateşler
    fired = trials = 0
    for L in (15.0, 20.0, 25.0, 30.0):
        low = 100.0; high = low + L
        gz_lo, gz_hi = high - 0.786 * L, high - 0.618 * L
        c = (gz_lo + gz_hi) / 2.0
        for tmult in (0.15, 0.3, 0.6, 1.0):
            trials += 1
            rr = cf.synth({
                "structure": {"event": "CHoCH", "direction": "bull"},
                "impulse": {"start": low, "end": high},
                "order_blocks": [{"low": c - 0.4, "high": c + 0.4, "type": "demand"}],
                "liquidity": [{"price": high + tmult * L, "type": "buyside"}],
            })
            if rr["KARAR"] == "LONG":
                fired += 1
    assert fired == trials, f"CANLILIK KIRILDI: {fired}/{trials}"

    # ATR-uyarlı SL: atr=2.0 → SL = min(100,104.28) - 1.0*2.0 = 98.0
    j = dict(long_job); j["atr"] = 2.0
    r = cf.synth(j)
    assert r["gecersizlik_sl"] == 98.0 and r["atr_kullanildi"] == 2.0, r
    assert r["KARAR"] == "LONG", r

    # MTF kapısı: HTF ters yönde → BEKLE
    j = dict(long_job); j["htf_bias"] = "bear"
    r = cf.synth(j)
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("MTF" in g for g in r["kapi_gerekceleri"]), r

    # Rejim kapısı: range + BOS(devam) → BEKLE; range + CHoCH(dönüş) → serbest
    j = dict(long_job); j["structure"] = {"event": "BOS", "direction": "bull"}
    j["regime"] = {"durum": "range"}
    r = cf.synth(j)
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("rejim" in g for g in r["kapi_gerekceleri"]), r
    j = dict(long_job); j["regime"] = {"durum": "range"}   # CHoCH kalır
    r = cf.synth(j)
    assert r["KARAR"] == "LONG", r

    # Yüksek-vol: R:R eşiği +0.5 → rr~2.2 normalde LONG, yüksek-vol'da BEKLE
    j = dict(long_job); j["liquidity"] = [{"price": 118.65, "type": "buyside"}]
    r = cf.synth(j)
    assert r["KARAR"] == "LONG" and 2.0 <= r["rr"] < 2.5, r
    j2 = dict(j); j2["regime"] = {"durum": "trend", "yuksek_vol": True}
    r = cf.synth(j2)
    assert r["KARAR"] == "NÖTR-BEKLE", r
    assert any("yüksek-vol" in g for g in r["kapi_gerekceleri"]), r

    # ================= SMC TESPİT =================
    # FVG birimi: 3. mumun low'u 1. mumun high'ından yukarıda → bull FVG
    import pandas as pd
    fdf = pd.DataFrame([{"open": 100, "high": 101, "low": 99, "close": 100.5},
                        {"open": 100.5, "high": 103, "low": 100.4, "close": 102.8},
                        {"open": 102.8, "high": 104, "low": 102.2, "close": 103.5}])
    fv = st.find_fvgs(fdf)
    assert len(fv) == 1 and fv[0]["type"] == "bull" and not fv[0]["dolu"], fv
    assert fv[0]["low"] == 101 and fv[0]["high"] == 102.2, fv

    # FVG MİTİGASYON REGRESYONU: orta noktaya DEĞEN ama uzak kenara değmeyen bar.
    # Yukarıdaki test 1.0/0.5/0.0 eşiklerinin ÜÇÜNDE de aynı sonucu verir (4. bar
    # yok → dolu hep False), yani kuralı sınamaz. Bu test kural geri alınırsa KIRILIR.
    mdf = pd.concat([fdf, pd.DataFrame([{"open": 103.5, "high": 103.6,
                                         "low": 101.4, "close": 101.5}])],
                    ignore_index=True)   # 101.4: ce'nin (101.6) altı, uzak kenarın (101) üstü
    assert st.find_fvgs(mdf, 1.0)[0]["dolu"] is False, "1.0 eşiğinde AÇIK kalmalı"
    assert st.find_fvgs(mdf, 0.5)[0]["dolu"] is True, "0.5 eşiğinde DOLU olmalı"
    assert st.find_fvgs(mdf)[0]["dolu"] is True, "varsayılan 0.5 davranışını vermeli"
    # sabit çalışma anında okunmalı (varsayılan argümana bağlanmamalı)
    _onceki = st.FVG_MITIGASYON
    st.FVG_MITIGASYON = 1.0
    try:
        assert st.find_fvgs(mdf)[0]["dolu"] is False, "sabit çağrı anında okunmalı"
    finally:
        st.FVG_MITIGASYON = _onceki
    # detect() eşiği params ile ezilebilmeli + varsayimlar'da BEYAN edilmeli
    # DAVRANIŞ assert'i — yalnız varsayimlar METNİNE bakmak sahte güvencedir:
    # detect() içindeki find_fvgs(df, p[...]) bağı koparılsa bile metin p'den
    # üretildiği için testi geçerdi. Bu yüzden ÇIKTI farkı sınanır.
    # Fixture eşiği AYIRT ETMELİ: gap'e girip orta noktayı geçen ama uzak
    # kenara değmeyen bir geri çekilme şart. Düz zigzag bunu üretmez (1.0 ile
    # 0.0 aynı sonucu verir) — o yüzden bölge ve dokunuş elle kurulur.
    _c = bars([0.0] * 22)          # DÜZ taban: kendi başına hiç FVG üretmez
    _c += [{"open": 100.0, "high": 100.2, "low": 99.9, "close": 100.1},
           {"open": 100.1, "high": 106.0, "low": 100.0, "close": 105.8},  # displacement
           {"open": 105.8, "high": 106.5, "low": 103.0, "close": 105.0},  # bull FVG 100.2–103.0
           {"open": 105.0, "high": 105.2, "low": 101.4, "close": 102.0},  # ce=101.6 GEÇİLDİ,
           {"open": 102.0, "high": 103.2, "low": 101.8, "close": 102.5}]  # uzak kenar 100.2 sağlam
    _r05 = st.detect({"candles": _c, "params": {"fvg_mitigasyon": 0.0}})
    _r10 = st.detect({"candles": _c, "params": {"fvg_mitigasyon": 1.0}})
    assert len(_r10["acik_fvgler"]) > len(_r05["acik_fvgler"]), (
        "params gerçekten UYGULANMALI: 1.0 daha çok açık FVG bırakmalı "
        "(1.0=%d, 0.0=%d)" % (len(_r10["acik_fvgler"]), len(_r05["acik_fvgler"])))
    assert any("FVG mitigasyon" in v for v in _r10["varsayimlar"]), _r10["varsayimlar"]
    assert any("1.0" in v for v in _r10["varsayimlar"] if "FVG mitigasyon" in v), \
        "params ile ezilen değer varsayimlar'a da yansımalı"
    # iki motorun sabiti AYNI olmak zorunda
    import importlib.util as _ilu
    _p = Path(__file__).resolve().parents[4] / "engine" / "karar_motoru.py"
    assert _p.exists(), "karar_motoru.py bulunamadı: %s (sabit eşitliği SINANMADI)" % _p
    _s = _ilu.spec_from_file_location("_km_sabit", _p)
    _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
    assert _m.FVG_MITIGASYON == st.FVG_MITIGASYON, \
        "karar_motoru=%r smc_tespit=%r — iki motor ayrışmış" % (
            _m.FVG_MITIGASYON, st.FVG_MITIGASYON)

    # Eşit tepe/dip likiditesi: W deseni → buyside + sellside kümeleri
    w = bars([+1]*5 + [-1]*5 + [+1]*5 + [-1]*5 + [+1]*2)
    rep = st.detect({"candles": w})
    kinds = {q["kind"] for q in rep["likidite"]}
    assert "esit-tepe" in kinds and "esit-dip" in kinds, rep["likidite"]

    # Trend serisi → rejim "trend"; karışık zigzag → trend DEĞİL
    rep = st.detect({"candles": bars([+1.0] * 60)})
    assert rep["rejim"]["durum"] == "trend", rep["rejim"]
    rep = st.detect({"candles": bars([+0.6, -0.5, +0.4, -0.6, +0.5, -0.4] * 15)})
    assert rep["rejim"]["durum"] != "trend", rep["rejim"]

    # Yapı + uçtan uca: yükselen döngüler → bull olaylar, OB, ATR; confluence_job çalışır
    up_cycles = bars(([+1.0] * 10 + [-1.0] * 7) * 60)
    rep = st.detect({"candles": up_cycles})
    assert rep["trend"] == "bull", rep["trend"]
    assert rep["olaylar"] and rep["olaylar"][-1]["direction"] == "bull", rep["olaylar"][-2:]
    assert any(ob["type"] == "demand" for ob in rep["order_blocks"]), rep["order_blocks"]
    assert isinstance(rep["atr"], float) and rep["atr"] > 0, rep["atr"]
    cj = rep["confluence_job"]
    assert cj is not None and cj["impulse"]["end"] > cj["impulse"]["start"], cj
    out = cf.synth(cj)
    assert out["KARAR"] in ("LONG", "SHORT", "NÖTR-BEKLE"), out

    # MTF uçtan uca: LTF boğa + HTF ayı → confluence MTF kapısı BEKLE der
    down_htf = bars(([-1.0] * 10 + [+1.0] * 7) * 20, start=400.0)
    rep = st.detect({"candles": up_cycles, "htf_candles": down_htf})
    assert rep["htf"]["trend"] == "bear", rep["htf"]
    cj = rep["confluence_job"]
    assert cj["htf_bias"] == "bear", cj
    out = cf.synth(cj)
    assert out["KARAR"] == "NÖTR-BEKLE", out
    assert any("MTF" in g for g in out["kapi_gerekceleri"]), out

    # ================= KALİBRASYON (istatistik birimleri) =================
    # Wilson alt sınırı: 50/100 → ~0.402; 0/10 → 0
    assert abs(kb.wilson_lo(50, 100) - 0.402) < 0.01, kb.wilson_lo(50, 100)
    assert kb.wilson_lo(0, 10) == 0.0

    # Dinamik min R:R: kazanma belirsizleştikçe gereken R:R yükselir + korkuluklar
    assert kb.dinamik_min_rr(30, 30)["min_rr"] == 1.0          # hep kazanç → alt korkuluk
    orta = kb.dinamik_min_rr(10, 30)["min_rr"]
    assert 3.0 < orta <= 5.0, orta                             # wr~0.33 → R:R ~4.2
    assert kb.dinamik_min_rr(1, 30)["min_rr"] == 5.0           # umutsuz → üst korkuluk
    assert kb.dinamik_min_rr(0, 0)["min_rr"] == 5.0            # işlem yok → fail-closed

    # Bootstrap CI: determinist (aynı tohum = aynı sonuç), lo<hi, pozitif seri → lo>0
    rs = [1.0, 1.2, -1.0, 1.5, 0.8, 1.1, -1.0, 1.3, 0.9, 1.4]
    ci1 = kb.bootstrap_ci(rs, seed=3)
    ci2 = kb.bootstrap_ci(rs, seed=3)
    assert ci1 == ci2 and ci1[0] < ci1[1], (ci1, ci2)

    # MAE→ATR çarpanı: veri yoksa varsayım; küçük MAE → alt, dev MAE → üst korkuluk
    assert kb.mae_atr_mult([])["atr_mult"] == 1.0
    assert kb.mae_atr_mult([0.1] * 10)["atr_mult"] == 0.5
    assert kb.mae_atr_mult([4.0] * 10)["atr_mult"] == 3.0

    # Permütasyon: monotonluk — güçlü gerçek beklenti küçük p, kötü beklenti büyük p
    import pandas as pd2
    updf = st.load_frame({"candles": up_cycles})
    ha, la, ca = (updf["high"].to_numpy(), updf["low"].to_numpy(),
                  updf["close"].to_numpy())
    atr_a = st.wilder_atr(updf).to_numpy()
    p_iyi = kb.permutation_pvalue(ha, la, ca, atr_a, 5.0, ["long"] * 20,
                                  1.0, 1.5, 60, n_perm=99, seed=5)["p"]
    p_kotu = kb.permutation_pvalue(ha, la, ca, atr_a, -5.0, ["long"] * 20,
                                   1.0, 1.5, 60, n_perm=99, seed=5)["p"]
    assert p_iyi < 0.05 < p_kotu, (p_iyi, p_kotu)

    # ================= TARİHSEL DOĞRULAMA (kalibre mod: varsayılan) ==========
    # Düzenli OTE-retest'li yükseliş → LONG edge: permütasyon + bootstrap + MAE
    r = sd.simulate({"candles": up_cycles})
    assert r["islem_sayisi"] >= 12, r["islem_sayisi"]
    assert r["beklenti_R"] > 0, r
    assert r["sinyal_izni"] is True, (r["SONUC"], r["gerekce"])
    assert all(t["dir"] == "long" for t in r["islemler_son10"]), r["islemler_son10"]
    k = r["kalibrasyon"]
    assert k["permutasyon"]["p"] <= 0.05, k["permutasyon"]
    assert k["bootstrap_ci_R"][0] > 0, k["bootstrap_ci_R"]
    assert 0.5 <= k["atr_mult_kalibre"]["atr_mult"] <= 3.0, k["atr_mult_kalibre"]
    assert 1.0 <= k["onerilen_min_rr"]["min_rr"] <= 5.0, k["onerilen_min_rr"]
    assert "veri-türevi" in r["esik_kaynagi"], r["esik_kaynagi"]
    assert r["varsayimlar"], "varsayım defteri boş olamaz"

    # Ayna düşüş → SHORT edge (yön: short dediğinde short)
    down_cycles = bars(([-1.0] * 10 + [+1.0] * 7) * 60, start=400.0)
    r = sd.simulate({"candles": down_cycles})
    assert r["sinyal_izni"] is True, (r["SONUC"], r["gerekce"])
    assert all(t["dir"] == "short" for t in r["islemler_son10"]), r["islemler_son10"]

    # Kenar/testere piyasa → kanıt YOK → sinyal izni YOK (fail-closed)
    saw = bars(([+1.0] * 5 + [-1.0] * 5) * 40)
    r = sd.simulate({"candles": saw})
    assert r["sinyal_izni"] is False, r
    assert r["SONUC"] in ("VERİ YETERSİZ", "EDGE KANITLANAMADI", "ZAYIF EDGE"), r

    # Legacy mod hâlâ çalışır ve varsayım olarak ETİKETLİDİR
    r = sd.simulate({"candles": up_cycles,
                     "params": {"kalibrasyon": False, "min_trades": 12}})
    assert r["esik_kaynagi"].startswith("statik varsayım"), r["esik_kaynagi"]
    assert r["sinyal_izni"] is True, (r["SONUC"], r["gerekce"])

    # Confluence eşik-kaynak etiketi: kalibre bilgisi verilirse yankılanır
    j = dict(long_job)
    j["thresholds_kaynak"] = "kalibrasyon (veri-türevi, setup_dogrulama)"
    r = cf.synth(j)
    assert "kalibrasyon" in r["esik_kaynagi"], r["esik_kaynagi"]
    r = cf.synth(long_job)
    assert "varsayım" in r["esik_kaynagi"], r["esik_kaynagi"]

    print("SELF_TEST_OK: confluence(long/short/yalniz-fib/celiski/rr/geometri/"
          "canlilik/atr-sl/mtf-kapi/rejim-kapi/yuksek-vol/esik-kaynak), "
          "smc-tespit(fvg/likidite/rejim/yapi/uctan-uca/mtf), "
          "kalibrasyon(wilson/dinamik-rr/bootstrap/mae/permutasyon), "
          "dogrulama(kalibre-long/short/fail-closed/legacy-etiket)")


if __name__ == "__main__":
    main()
