# META3 KARARGAH v1.0 — Recursive Self-Improving calisma dongusu
# ====================================================================
# KAYNAK SEMA: "META3 — Nihai Recursive Self-Improving Research System"
# (kullanicinin yukledigi PDF; metin cikarimi: scratchpad/meta3.txt).
# Bu modul o semanin bu depodaki DURUST uygulamasidir:
#
#   GOAL -> AGENT -> EVALUATE -> EXPERIMENT MEMORY -> META -> META2
#        -> META3 -> NEXT GENERATION  (hepsi IMMUTABLE CONTROL PLANE icinde)
#
# Sema -> kod eslemesi (PDF bolum numaralariyla):
#   #1/#22 IMMUTABLE CONTROL PLANE  -> IMMUTABLE_PLANE + kapi muhru (hash)
#   #3     AGENT                    -> btc_karargah_v5_4 motoru (karar_uret)
#   #4     EVALUATOR (hakem)        -> degerlendir(): J = wQ*Q + wR*R + wS*S
#                                      - wC*C - wL*L  (agirliklar SABIT ve
#                                      recursive katmanlarca DEGISTIRILEMEZ)
#   #5     AUTORESEARCH dongusu     -> her kosuda varyant deneyi (sandbox=
#                                      golge-degerlendirme; canli emir YOK)
#   #6     META                     -> varyant KEEP/REJECT/ROLLBACK (olcumle)
#   #7     META2                    -> Meta'nin kesif orani eps'i [0,0.3]
#                                      bandinda olcumle ayarlar
#   #8     META3                    -> META2'nin pencere W'sini [5,50]
#                                      bandinda olcumle ayarlar
#   #10    EXPERIMENT MEMORY        -> meta3_bellek.json (deney kaydi:
#                                      experiment_id, parent_version,
#                                      optimizer_version, hypothesis, patch,
#                                      metrics, cost, latency, risk, decision)
#   #11    EVOLUTION GRAPH          -> bellekteki "evrim" listesi (soy zinciri)
#   #12    FAILURE INTELLIGENCE     -> basarisizlik siniflari + karantina
#                                      ("neyi artik denememeliyim")
#   #16    SANDBOX + VERSIONING     -> bellek anlik-goruntusu (.bak) + geri alma
#   #19    DURMA KOSULLARI          -> dongu_kontrol(): STOP/ROLLBACK/HOLD/HALT
#   #24    BILIMSEL SINIR           -> asagida acikca korunur (garanti yok)
#
# DURUSTLUK SOZLESMESI (deponun anayasasi + Constitution v2 ile uyum):
#  - "En yuksek dogruluk" bir GARANTI degil, MEKANIZMADIR: sistem her kosuda
#    ONCEKI kosunun verdigi seviyelerin GERCEK akibetini olcer (HESAP VERME),
#    yalnizca OLCULEBILIR iyilesme gosteren degisikligi tutar (KEEP), gerileyeni
#    geri alir (ROLLBACK). PDF'in kendi 24. bolumu de ayni siniri koyar.
#  - Meta katmanlari kapilari GEVSETEMEZ: varyant uzayi yalnizca SIKILASTIRMA
#    (filtre EKLEME) icerir; bu yapisal olarak boyledir (varyant = taban
#    kararin uzerine 'and' kosulu). Gevseten aday uretilemez (K22).
#  - Kod kendi kaynagini DEGISTIRMEZ: "patch" soyutlamasi burada yalnizca
#    YAPILANDIRMA (config) duzeyindedir. Kaynak-kodu kendini yamalayan bir
#    sistem depo sozlesmesinin K16/K22 kurallariyla celisirdi; bu sinir
#    ACIKCA beyan edilir (sessiz daraltma degil).
#  - YON ZORUNLU: her sembolde YON (bias) ve GIRIS/STOP/HEDEF seviyeleri HER
#    KOSUDA basilir. Kapi kapaliysa seviyeler "BILGI" etiketi tasir, "EMIR
#    -ADAYI" degil — yon asla "BEKLE" arkasina gizlenmez.
#  - Canli/otomatik emir YOK. create_order yok, API anahtari yok.
# ====================================================================

import hashlib
import json
import os
import time
import traceback

import numpy as np
import pandas as pd

import btc_karargah_v5_4 as motor

# --------------------------------------------------------------------
# IMMUTABLE CONTROL PLANE (PDF #17/#22)
# Bu blok recursive katmanlarca DEGISTIRILEMEZ. Kosuda butunluk muhru
# dogrulanir; bozulmussa HALT (PDF #19: safety violation -> HALT).
# --------------------------------------------------------------------
_KAPI_SABITLERI = (
    "FEE_TAKER", "SLIPPAGE", "ATR_LEN", "ATR_SL_MULT", "TIME_STOP_BARS",
    "ALPHA", "MIN_TRADES", "N_FOLDS", "EMBARGO", "BOOTSTRAP_B",
    "PUMP_THRESHOLD_Z", "PUMP_TICK_WATCH", "FR_TOLERANCE_BPS", "LOB_DEPTH",
)

IMMUTABLE_PLANE = {
    # Evaluator agirliklari (PDF #4). HIPOTEZ etiketli sabitlerdir; ama
    # immutable plane icindedirler: recursive katmanlar bunlari OYNAYAMAZ
    # (evaluator kendi optimize ettigi seyin hakemi olamaz — PDF #4/#24).
    "w_Q": 1.0, "w_R": 0.5, "w_S": 1.0, "w_C": 0.1, "w_L": 0.05,
    # Kaynak/butce sinirlari (PDF #17: maximum budget / recursive depth)
    "kosu_basi_deney_butcesi": 2,     # her kosuda en fazla 2 varyant degerlendirilir
    "recursive_derinlik": 3,          # META -> META2 -> META3; daha derini YOK
    "min_akibet_n": 8,                # bundan az olculmus akibetle KEEP/REJECT
                                      # verilemez -> HOLD (PDF #19 evaluator unstable)
    "eps_bant": (0.0, 0.3),           # META2'nin oynayabilecegi kesif-orani bandi
    "W_bant": (5, 50),                # META3'un oynayabilecegi pencere bandi
    "karantina_esigi": 3,             # ayni varyant 3 kez ust uste basarisizsa
                                      # karantina (PDF #12: neyi denememeliyim)
}

BELLEK_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "meta3_bellek.json")
OVERRIDE_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "meta3_override.json")


def kapi_muhru():
    """Motor kapi sabitlerinin butunluk muhru (SHA256).

    Meta katmanlari motora config verir, sabitlere dokunamaz; bu muhur her
    kosuda dogrulanir. Beklenen deger ILK kosuda bellege yazilir ve sonraki
    kosularda karsilastirilir (sabitler degistiyse HALT + acik rapor).
    """
    parcalar = []
    for ad in _KAPI_SABITLERI:
        parcalar.append(f"{ad}={getattr(motor, ad)!r}")
    return hashlib.sha256("|".join(parcalar).encode()).hexdigest()


# --------------------------------------------------------------------
# VARYANT UZAYI (META'nin arama uzayi — PDF #5/#6)
# YAPISAL KURAL: her varyant taban karara yalnizca EK kosul (and) koyar.
# Gevsetme ureten varyant TANIMLANAMAZ — uzay listesi budur, uretici yok.
# Filtre girdileri KOSU ANINDA OLCULEN degerlerdir (golge bayraklari);
# boylece akibet olculdugunde varyantin karsi-olgusal sonucu KESIN olarak
# hesaplanir (varyant = taban islemlerinin alt kumesi).
# --------------------------------------------------------------------
VARYANTLAR = {
    "V0_taban": {
        "aciklama": "v5.4 motoru oldugu gibi (WF+FDR+bootstrap kapilari)",
        "filtreler": [],
    },
    "V1_komposit_teyit": {
        "aciklama": ("taban + bilesik oncu skorun isareti yonle AYNI ve "
                     "kapsam >= 0.5 olmali (yalnizca SIKILASTIRMA)"),
        "filtreler": ["komposit_uyum"],
    },
    "V2_cift_teyit": {
        "aciklama": ("V1 + tick momentum isareti de yonle ayni olmali "
                     "(daha da siki)"),
        "filtreler": ["komposit_uyum", "tick_uyum"],
    },
}
_VARYANT_SIRA = ["V0_taban", "V1_komposit_teyit", "V2_cift_teyit"]


def filtre_gecer(filtre_adi, golge):
    """Golge bayraklarindan filtre karari. Bayrak OLCULEMEDIYSE (None)
    fail-closed: filtre GECMEZ (eksik veriyle sikilastirma gevsetilmez)."""
    deger = golge.get(filtre_adi)
    return deger is True


# --------------------------------------------------------------------
# EXPERIMENT MEMORY (PDF #10/#11) + SANDBOX/VERSIONING (PDF #16)
# --------------------------------------------------------------------
def bellek_yukle():
    if not os.path.exists(BELLEK_YOLU):
        return {
            "surum": 1,
            "kapi_muhru": None,
            "aktif_varyant": "V0_taban",
            "eps": 0.15,          # META baslangic kesif orani (HIPOTEZ)
            "W": 12,              # META2 degerlendirme penceresi (HIPOTEZ)
            "kosu_sayaci": 0,
            "deneyler": [],       # PDF #10 alanlariyla
            "akibetler": [],      # olculmus gercek sonuclar (HESAP VERME)
            "oneriler": [],       # onceki kosunun acik onerileri (akibet bekliyor)
            "evrim": [{"surum": 1, "ebeveyn": None, "varyant": "V0_taban",
                       "neden": "baslangic"}],
            "karantina": {},      # varyant -> ardisik basarisizlik sayisi
        }
    with open(BELLEK_YOLU, encoding="utf-8") as f:
        return json.load(f)


def bellek_kaydet(bellek):
    # PDF #16: once anlik goruntu (.bak), sonra yaz — yazim yarida kalirsa
    # onceki surum geri alinabilir (ROLLBACK).
    if os.path.exists(BELLEK_YOLU):
        os.replace(BELLEK_YOLU, BELLEK_YOLU + ".bak")
    with open(BELLEK_YOLU, "w", encoding="utf-8") as f:
        json.dump(bellek, f, ensure_ascii=False, indent=1)


def deney_kaydi(bellek, optimizer, hipotez, patch, metrikler, maliyet_sn,
                risk, karar):
    """PDF #10'un zorunlu alanlariyla deney kaydi."""
    kayit = {
        "experiment_id": f"E{len(bellek['deneyler']) + 1:05d}",
        "parent_version": bellek["surum"],
        "optimizer_version": optimizer,     # "meta" | "meta2" | "meta3"
        "hypothesis": hipotez,
        "patch": patch,                     # config degisikligi (kod DEGIL)
        "metrics": metrikler,
        "cost": round(maliyet_sn, 3),
        "latency": round(maliyet_sn, 3),
        "risk": risk,
        "decision": karar,                  # KEEP | REJECT | HOLD | ROLLBACK
    }
    bellek["deneyler"].append(kayit)
    return kayit


# --------------------------------------------------------------------
# EVALUATOR (PDF #4) — IMMUTABLE; recursive katmanlar cagirir ama DEGISTIREMEZ
# --------------------------------------------------------------------
def degerlendir(Q, R, S, C, L):
    """J = wQ*Q + wR*R + wS*S - wC*C - wL*L  (PDF #4 formulu).

    Q: olculmus kalite (oncelik: gercek akibet ortalama R'si; yoksa OOS ort.)
    R: saglamlik = 1 - bootstrap p_max (olculen)
    S: guvenlik = kapilar/muhur ihlalsiz mi (1.0 / 0.0)
    C: maliyet = kosu suresi / 60 sn (olculen, normalize)
    L: gecikme = veri yasi / 3600 sn (olculen, normalize)
    Bilesenlerden herhangi biri OLCULEMEDIYSE None gecilir ve J=None doner
    (uydurma bileşenle skor uretilmez — fail-closed)."""
    if any(x is None for x in (Q, R, S, C, L)):
        return None
    P = IMMUTABLE_PLANE
    return (P["w_Q"] * Q + P["w_R"] * R + P["w_S"] * S
            - P["w_C"] * C - P["w_L"] * L)


# --------------------------------------------------------------------
# HESAP VERME — onceki kosunun onerilerinin GERCEK akibeti (Q'nun zemini)
# Kurallar muhafazakar (repo sozlesmesi): ayni barda stop+hedef -> STOP;
# giris dolumu bar araligiyla; tetiklenmemis oneri IPTAL, R yazilmaz.
# --------------------------------------------------------------------
def akibet_olc(oneri, df_15m):
    """oneri: {sembol, yon, giris, stop, hedef, bar_ts(ms), etiket}
    df_15m: guncel 15M kline (kapanmis barlar). Donus: dict ya da None
    (yeni bar yoksa None = henuz olculemiyor)."""
    barlar = df_15m[df_15m.index > pd.Timestamp(oneri["bar_ts"], unit="ms",
                                                tz="UTC")]
    if barlar.empty:
        return None
    giris, stop, hedef = oneri["giris"], oneri["stop"], oneri["hedef"]
    yon = oneri["yon"]
    dolum = False
    for ts, bar in barlar.iterrows():
        lo, hi = float(bar["low"]), float(bar["high"])
        if not dolum:
            if lo <= giris <= hi:
                dolum = True
            else:
                continue
        # dolumdan sonra (ayni bar dahil): once STOP kontrolu (muhafazakar)
        if yon == "LONG":
            if lo <= stop:
                return {"sonuc": "STOP", "r": -1.0}
            if hi >= hedef:
                return {"sonuc": "HEDEF",
                        "r": round(abs(hedef - giris) /
                                   max(abs(giris - stop), 1e-9), 3)}
        else:
            if hi >= stop:
                return {"sonuc": "STOP", "r": -1.0}
            if lo <= hedef:
                return {"sonuc": "HEDEF",
                        "r": round(abs(giris - hedef) /
                                   max(abs(stop - giris), 1e-9), 3)}
    if not dolum:
        # TIME_STOP_BARS kadar bar gectiyse dolmayan emir IPTAL (R yazilmaz)
        if len(barlar) >= motor.TIME_STOP_BARS:
            return {"sonuc": "IPTAL", "r": None}
        return None  # hala bekliyor
    return None      # dolum var, sonuc yok — acik pozisyon, olcum surer


# --------------------------------------------------------------------
# AGENT KATMANI (PDF #3) — v5.4 motorunun VERI donduren sarmali
# signal_engine print-tabanli oldugundan ayni olcum bloklari burada VERI
# olarak uretilir. Formuller v5.4 ile BIREBIR aynidir (test dosyasi iki
# yolun ayni sayilari urettigini assert eder — kopya sapmasi kaniti).
# --------------------------------------------------------------------
def karar_uret(symbol, df_4h, df_15m, btc_4h, btc_15m):
    """Tek sembol icin olculmus karar verisi. Donus dict:
    yon, yon_kaynak, kapi (ACIK/KAPALI/VETO), kapi_gerekce, giris, stop,
    hedef, etiket (EMIR-ADAYI/BILGI), kural, oos, p_max, golge (varyant
    bayraklari), bar_ts, ek olculer."""
    t0 = time.monotonic()
    sonuc = {"sembol": symbol, "yon": "NOTR", "yon_kaynak": "VERI YOK",
             "kapi": "KAPALI", "kapi_gerekce": "", "etiket": "BILGI",
             "giris": None, "stop": None, "hedef": None, "kural": None,
             "oos": None, "p_max": None, "golge": {}, "bar_ts": None}

    state, conf = motor.regime_detector(df_15m["close"], df_4h["close"])
    btc_state, _ = motor.regime_detector(btc_15m["close"], btc_4h["close"])

    # --- YON (bias) — ZORUNLU, asla gizlenmez ---------------------------
    # Oncelik sirasi (HIPOTEZ etiketli siralama; her aday OLCULMUS deger):
    #  1) rejim BULL/BEAR  2) 4H EMA50-EMA200 egiminin isareti (CALM'da)
    #  3) bilesik oncu skorun isareti (kapsam>=0.5 ise)  4) NOTR (gercek 0)
    ef = df_4h["close"].ewm(span=50, adjust=False).mean()
    es = df_4h["close"].ewm(span=200, adjust=False).mean()
    egim = float(((ef - es) / df_4h["close"]).iloc[-1])
    if state == "BULL":
        sonuc["yon"], sonuc["yon_kaynak"] = "LONG", f"rejim BULL (guven={conf:.2f})"
    elif state == "BEAR":
        sonuc["yon"], sonuc["yon_kaynak"] = "SHORT", f"rejim BEAR (guven={conf:.2f})"
    elif abs(egim) > 1e-12:
        sonuc["yon"] = "LONG" if egim > 0 else "SHORT"
        sonuc["yon_kaynak"] = (f"rejim {state}; 4H EMA50-EMA200 egimi "
                               f"{egim:+.5f} (zayif kanit — bilgi)")
    # (3/4 asagida, komposit hesaplandiktan sonra tamamlanir)

    # --- oncu katman olcumleri (v5.4 ile ayni fonksiyonlar) -------------
    trades = motor.fetch_recent_trades(symbol)
    bids, asks = motor.fetch_order_book(symbol)
    fr_df, oi = motor.fetch_funding_oi(symbol)
    fr_latest = 0.0
    fr_var = (not fr_df.empty) and ("fundingRate" in fr_df.columns)
    if fr_var:
        fr_latest = float(fr_df["fundingRate"].iloc[-1])
    score15, note15 = motor.pump_anomaly(df_15m["volume"])
    yon_pd, yon_move = motor.pump_dump_direction(trades, df_15m["close"])
    tscore = motor.tick_confirm_score(symbol, trades)
    obi_var = (bids is not None and asks is not None
               and not bids.empty and not asks.empty)
    komp = motor.composite_leading_score({
        "pump_skor": score15, "pump_not": note15, "tick_z": tscore,
        "obi": motor.lob_imbalance(bids, asks)[0] if obi_var else None,
        "funding": fr_latest if fr_var else None,
        "oi": oi if np.isfinite(oi) else None,
        "yon_move": yon_move,
    })
    sonuc["komposit"] = komp

    if sonuc["yon"] == "NOTR":
        if komp.get("skor") is not None and komp.get("kapsam", 0) >= 0.5 \
                and abs(komp["skor"]) > 1e-12:
            sonuc["yon"] = "LONG" if komp["skor"] > 0 else "SHORT"
            sonuc["yon_kaynak"] = (f"bilesik oncu skor {komp['skor']:+.2f} "
                                   f"(kapsam {komp['kapsam']:.2f}; zayif kanit)")
        else:
            sonuc["yon_kaynak"] = ("gercek berabere: rejim CALM, egim ~0, "
                                   "komposit olculemedi/sifir")

    # --- GOLGE BAYRAKLARI (varyant filtreleri icin; kosu aninda olculur) -
    yon_isaret = {"LONG": 1.0, "SHORT": -1.0}.get(sonuc["yon"], 0.0)
    if komp.get("skor") is not None and komp.get("kapsam", 0) >= 0.5:
        sonuc["golge"]["komposit_uyum"] = (komp["skor"] * yon_isaret) > 0
    else:
        sonuc["golge"]["komposit_uyum"] = None   # olculemedi -> fail-closed
    if abs(yon_move) > 1e-12:
        sonuc["golge"]["tick_uyum"] = (yon_move * yon_isaret) > 0
    else:
        sonuc["golge"]["tick_uyum"] = None

    # --- SEVIYELER — HER KOSUDA (olculen yapidan; uydurma yok) ----------
    close = df_15m["close"].astype(float)
    sma20 = close.rolling(window=20).mean()
    sd20 = close.rolling(window=20).std(ddof=0)
    z_ser = ((close - sma20) / (sd20 + 1e-12)).shift(periods=1)
    hl = (df_15m["high"] - df_15m["low"]).abs()
    hc = (df_15m["high"] - close.shift(periods=1)).abs()
    lc = (df_15m["low"] - close.shift(periods=1)).abs()
    tr_df = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr_ser = tr_df.rolling(motor.ATR_LEN).mean().shift(periods=1)
    son_kapanis = float(close.iloc[-1])
    atr_i = float(atr_ser.iloc[-1]) if np.isfinite(atr_ser.iloc[-1]) else None
    hedef_px = float(sma20.iloc[-1]) if np.isfinite(sma20.iloc[-1]) else None
    if atr_i is not None and hedef_px is not None and yon_isaret != 0.0:
        sonuc["giris"] = son_kapanis
        sonuc["stop"] = (son_kapanis - motor.ATR_SL_MULT * atr_i
                         if sonuc["yon"] == "LONG"
                         else son_kapanis + motor.ATR_SL_MULT * atr_i)
        sonuc["hedef"] = hedef_px
        sonuc["bar_ts"] = int(df_15m.index[-1].value // 1_000_000)

    # --- VETO / KAPI zinciri (v5.4 signal_engine ile ayni sira) ---------
    note = note15
    if note15 in ("NORMAL", "WATCH") and tscore is not None \
            and note15 == "WATCH" and tscore >= motor.PUMP_TICK_WATCH:
        note = "PUMP_OR_DUMP_RISK"
    if note == "PUMP_OR_DUMP_RISK":
        sonuc["kapi"], sonuc["kapi_gerekce"] = "VETO", \
            f"pump/dump vetosu (score={score15:.2f}, yon={yon_pd})"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    if symbol != "BTC/USDT" and state in ("BULL", "BEAR") \
            and btc_state != state:
        sonuc["kapi_gerekce"] = f"BTC {btc_state} ile {state} uyumsuz"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    direction = "LONG" if state == "BULL" else \
        "SHORT" if state == "BEAR" else None
    if direction is None:
        sonuc["kapi_gerekce"] = "rejim CALM/UNKNOWN — istatistik kapisi acilmadi"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc

    # --- WF + FDR + bootstrap (v5.4 ile birebir ayni mekanik) -----------
    df = df_15m.copy()
    df["z"] = z_ser
    df["atr"] = atr_ser
    df["rsi"] = motor.wilder_rsi(close, motor.RSI_LEN)
    df["target"] = sma20
    df = df.dropna(subset=["z", "atr", "rsi"])
    if len(df) < 700:
        sonuc["kapi_gerekce"] = f"yetersiz veri ({len(df)} mum)"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    feat = {k: df[k].to_numpy(dtype=float) for k in
            ["open", "close", "low", "high", "z", "atr", "rsi"]}
    rule_grid = [(zt, ro) for zt in motor.Z_GRID for ro in (False, True)]
    rule_trades = {rule: [] for rule in rule_grid}
    folds = 0
    for tr_idx, te_idx in motor.walkforward_splits(len(df), motor.N_FOLDS,
                                                   motor.EMBARGO):
        for rule in rule_grid:
            zt, ro = rule
            rule_trades[rule].extend(motor.simulate(feat, te_idx, zt, ro,
                                                    direction))
        folds += 1
    if folds == 0:
        sonuc["kapi_gerekce"] = "walk-forward split yok"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    stats = {rule: motor.oos_stats(rule_trades[rule]) for rule in rule_grid}
    pvals = {r: 2.0 * (1.0 - motor.norm_cdf(abs(s["t"])))
             for r, s in stats.items() if s is not None}
    if not pvals:
        sonuc["kapi_gerekce"] = "yeterli OOS islem yok"
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    keys = list(pvals.keys())
    accepted = motor.fdr_bh([pvals[k] for k in keys], motor.ALPHA)
    accepted_rules = [r for r, ok in zip(keys, accepted) if ok]
    p_max = motor.bootstrap_max_t(rule_trades)
    sonuc["p_max"] = p_max
    if not accepted_rules or p_max >= motor.ALPHA:
        sonuc["kapi_gerekce"] = (f"anti-overfit kapi kapali "
                                 f"(kabul={len(accepted_rules)}, p={p_max:.3f})")
        sonuc["sure_sn"] = time.monotonic() - t0
        return sonuc
    best_rule = max(accepted_rules, key=lambda r: stats[r]["mean"])
    best_z, best_rsi = best_rule
    sonuc["kural"] = f"z={best_z}" + ("+RSI" if best_rsi else "")
    sonuc["oos"] = stats[best_rule]
    cur, prev = df.iloc[-1], df.iloc[-2]
    zi, rsi_i = float(cur["z"]), float(cur["rsi"])
    if direction == "LONG":
        fired = (zi <= -best_z) and (zi > -4.0) and (float(prev["z"]) < zi) \
            and (zi > float(np.min(df["z"].iloc[-4:-1])))
    else:
        fired = (zi >= best_z) and (zi < 4.0) and (float(prev["z"]) > zi) \
            and (zi < float(np.max(df["z"].iloc[-4:-1])))
    if fired and best_rsi:
        rsi_ok = np.isfinite(rsi_i) and (
            rsi_i < motor.RSI_LONG_MAX if direction == "LONG"
            else rsi_i > motor.RSI_SHORT_MIN)
        if not rsi_ok:
            fired = False
            sonuc["kapi_gerekce"] = (f"z sarti sagladi ama RSI sarti "
                                     f"saglanmadi (rsi={rsi_i:.1f})")
    if fired:
        sonuc["kapi"] = "ACIK"
        sonuc["etiket"] = "EMIR-ADAYI"
        sonuc["kapi_gerekce"] = (f"WF+FDR+bootstrap onayli; kural="
                                 f"{sonuc['kural']}, z={zi:.2f}")
        # kapi acikken giris/stop v5.4'un canli tetik hesabiyla ayni
        sonuc["giris"] = float(cur["close"])
        sonuc["stop"] = (sonuc["giris"] - motor.ATR_SL_MULT * float(cur["atr"])
                         if direction == "LONG"
                         else sonuc["giris"] + motor.ATR_SL_MULT * float(cur["atr"]))
        sonuc["hedef"] = float(cur["target"])
        sonuc["yon"] = direction
        sonuc["yon_kaynak"] = f"rejim {state} + tetik ({sonuc['kural']})"
    elif not sonuc["kapi_gerekce"]:
        sonuc["kapi_gerekce"] = (f"kenar onayli; tetik yok (z={zi:.2f}, "
                                 f"esik={best_z}, kural={sonuc['kural']})")
    sonuc["sure_sn"] = time.monotonic() - t0
    return sonuc


def varyant_karari(karar, varyant_adi):
    """Aktif varyantin filtrelerini taban karara uygular (yalnizca
    SIKILASTIRMA: kapi ACIKsa kapatabilir, KAPALIYI ACAMAZ)."""
    if karar["kapi"] != "ACIK":
        return karar, []
    dusen = []
    for f in VARYANTLAR[varyant_adi]["filtreler"]:
        if not filtre_gecer(f, karar["golge"]):
            dusen.append(f)
    if dusen:
        karar = dict(karar)
        karar["kapi"] = "KAPALI"
        karar["etiket"] = "BILGI"
        karar["kapi_gerekce"] += (f" | varyant {varyant_adi} filtresi dusurdu: "
                                  f"{','.join(dusen)} (sikilastirma)")
    return karar, dusen


# --------------------------------------------------------------------
# META (PDF #6) — varyant secimi, KEEP/REJECT/ROLLBACK; olcum = akibet
# --------------------------------------------------------------------
def _varyant_akibet_ozeti(bellek, varyant_adi):
    """Bir varyantin karsi-olgusal akibet ozeti: taban onerilerin olculmus
    R'leri uzerinden, o varyantin golge bayraklariyla ALACAGI alt kume."""
    rler = []
    for a in bellek["akibetler"]:
        if a.get("r") is None:
            continue
        golge = a.get("golge", {})
        alir = all(filtre_gecer(f, golge)
                   for f in VARYANTLAR[varyant_adi]["filtreler"])
        if alir:
            rler.append(a["r"])
    if not rler:
        return {"n": 0, "ort_r": None}
    return {"n": len(rler), "ort_r": float(np.mean(rler))}


def meta_dongusu(bellek, kosu_suresi_sn, veri_yasi_sn):
    """PDF #6: analyze -> hypothesis -> (config) patch -> evaluate ->
    keep/reject. Donus: (karar_str, detay)."""
    P = IMMUTABLE_PLANE
    aktif = bellek["aktif_varyant"]
    ozet_aktif = _varyant_akibet_ozeti(bellek, aktif)
    C = min(kosu_suresi_sn / 60.0, 10.0)
    L = min(veri_yasi_sn / 3600.0, 10.0)

    if ozet_aktif["n"] < P["min_akibet_n"]:
        deney_kaydi(bellek, "meta",
                    f"aktif {aktif}: olculmus akibet n={ozet_aktif['n']} < "
                    f"{P['min_akibet_n']}",
                    {"varyant": aktif}, {"akibet": ozet_aktif},
                    kosu_suresi_sn, "dusuk", "HOLD")
        return "HOLD", (f"olculmus akibet yetersiz "
                        f"(n={ozet_aktif['n']}/{P['min_akibet_n']}) — "
                        f"evaluator kararsiz, degisiklik yok (fail-closed)")

    # aday sec (eps-acgozlu; karantinadakiler atlanir — PDF #12)
    adaylar = [v for v in _VARYANT_SIRA if v != aktif and
               bellek["karantina"].get(v, 0) < P["karantina_esigi"]]
    degerlendirilen = 0
    en_iyi = (aktif, ozet_aktif)
    for aday in adaylar:
        if degerlendirilen >= P["kosu_basi_deney_butcesi"]:
            break
        ozet = _varyant_akibet_ozeti(bellek, aday)
        degerlendirilen += 1
        if ozet["n"] < P["min_akibet_n"]:
            deney_kaydi(bellek, "meta",
                        f"aday {aday}: karsi-olgusal n={ozet['n']} yetersiz",
                        {"varyant": aday}, {"akibet": ozet},
                        kosu_suresi_sn, "dusuk", "HOLD")
            continue
        J_aday = degerlendir(ozet["ort_r"], None if bellek.get(
            "_son_p_max") is None else 1.0 - bellek["_son_p_max"],
            1.0, C, L)
        J_iyi = degerlendir(en_iyi[1]["ort_r"], None if bellek.get(
            "_son_p_max") is None else 1.0 - bellek["_son_p_max"],
            1.0, C, L)
        if J_aday is not None and J_iyi is not None and J_aday > J_iyi:
            en_iyi = (aday, ozet)
            deney_kaydi(bellek, "meta",
                        f"{aday} J={J_aday:.3f} > {en_iyi[0]} eski J",
                        {"varyant": aday},
                        {"akibet": ozet, "J": J_aday},
                        kosu_suresi_sn, "orta", "KEEP")
        else:
            bellek["karantina"][aday] = bellek["karantina"].get(aday, 0) + 1
            deney_kaydi(bellek, "meta",
                        f"{aday} olcumde ustun degil",
                        {"varyant": aday},
                        {"akibet": ozet,
                         "J": None if J_aday is None else round(J_aday, 3)},
                        kosu_suresi_sn, "dusuk", "REJECT")
    if en_iyi[0] != aktif:
        bellek["surum"] += 1
        bellek["evrim"].append({"surum": bellek["surum"],
                                "ebeveyn": bellek["surum"] - 1,
                                "varyant": en_iyi[0],
                                "neden": "meta KEEP (olculmus J ustunlugu)"})
        bellek["aktif_varyant"] = en_iyi[0]
        bellek["karantina"][en_iyi[0]] = 0
        return "KEEP", f"aktif varyant {aktif} -> {en_iyi[0]} (olcumle)"
    # gerileme kontrolu: aktif varyant tabandan olcumle kotuyse ROLLBACK
    taban = _varyant_akibet_ozeti(bellek, "V0_taban")
    if aktif != "V0_taban" and taban["n"] >= P["min_akibet_n"] \
            and ozet_aktif["ort_r"] is not None \
            and taban["ort_r"] is not None \
            and ozet_aktif["ort_r"] < taban["ort_r"]:
        bellek["surum"] += 1
        bellek["evrim"].append({"surum": bellek["surum"],
                                "ebeveyn": bellek["surum"] - 1,
                                "varyant": "V0_taban",
                                "neden": "ROLLBACK (aktif, tabandan olcumle kotu)"})
        bellek["aktif_varyant"] = "V0_taban"
        deney_kaydi(bellek, "meta", f"{aktif} tabandan kotu: "
                    f"{ozet_aktif['ort_r']:.3f} < {taban['ort_r']:.3f}",
                    {"varyant": "V0_taban"},
                    {"aktif": ozet_aktif, "taban": taban},
                    kosu_suresi_sn, "orta", "ROLLBACK")
        return "ROLLBACK", f"{aktif} -> V0_taban (olculmus gerileme)"
    return "TUT", f"aktif {aktif} korunuyor (olcumle ustun ya da esit)"


# --------------------------------------------------------------------
# META2 (PDF #7) ve META3 (PDF #8) — ust katmanlar, dusuk frekans
# Yalnizca IMMUTABLE bantlar icinde, OLCUME dayali ayar; her karar kayitli.
# --------------------------------------------------------------------
def meta2_dongusu(bellek):
    P = IMMUTABLE_PLANE
    W = bellek["W"]
    if bellek["kosu_sayaci"] % W != 0 or bellek["kosu_sayaci"] == 0:
        return None
    son = [d for d in bellek["deneyler"] if d["optimizer_version"] == "meta"][-3 * W:]
    kesifler = [d for d in son if d["decision"] in ("KEEP", "REJECT")]
    if len(kesifler) < 4:
        deney_kaydi(bellek, "meta2", "kesif orneklemi yetersiz", {},
                    {"n": len(kesifler)}, 0.0, "dusuk", "HOLD")
        return "HOLD"
    verim = sum(1 for d in kesifler if d["decision"] == "KEEP") / len(kesifler)
    eski = bellek["eps"]
    # verim yuksekse kesif artar, dusukse azalir — bant DISINA CIKAMAZ
    yeni = min(max(eski + (0.05 if verim > 0.25 else -0.05),
                   P["eps_bant"][0]), P["eps_bant"][1])
    bellek["eps"] = yeni
    deney_kaydi(bellek, "meta2",
                f"kesif verimi {verim:.2f} -> eps {eski:.2f}->{yeni:.2f} "
                f"(bant {P['eps_bant']})", {"eps": yeni},
                {"verim": round(verim, 3)}, 0.0, "dusuk",
                "KEEP" if yeni != eski else "TUT")
    return "KEEP" if yeni != eski else "TUT"


def meta3_dongusu(bellek):
    P = IMMUTABLE_PLANE
    W = bellek["W"]
    if bellek["kosu_sayaci"] % (W * W) != 0 or bellek["kosu_sayaci"] == 0:
        return None
    m2 = [d for d in bellek["deneyler"] if d["optimizer_version"] == "meta2"]
    if len(m2) < 3:
        deney_kaydi(bellek, "meta3", "meta2 orneklemi yetersiz", {},
                    {"n": len(m2)}, 0.0, "dusuk", "HOLD")
        return "HOLD"
    # meta2 kararlari hep TUT ise pencere buyutulur (daha seyrek, daha ucuz),
    # sik KEEP ise kucultulur — bant DISINA CIKAMAZ (PDF #15/#20 ruhu)
    son3 = [d["decision"] for d in m2[-3:]]
    eski = bellek["W"]
    if all(k == "TUT" for k in son3):
        yeni = min(eski + 5, P["W_bant"][1])
    elif son3.count("KEEP") >= 2:
        yeni = max(eski - 3, P["W_bant"][0])
    else:
        yeni = eski
    bellek["W"] = yeni
    deney_kaydi(bellek, "meta3",
                f"meta2 son3={son3} -> W {eski}->{yeni} (bant {P['W_bant']})",
                {"W": yeni}, {"son3": son3}, 0.0, "dusuk",
                "KEEP" if yeni != eski else "TUT")
    return "KEEP" if yeni != eski else "TUT"


# --------------------------------------------------------------------
# IC DENETCI (kosu ici; PDF AUDIT + kullanicinin denetci sarti)
# Kosu bittikten sonra kaydi denetler; kritik ihlalde EMIR-ADAYI etiketleri
# MUHURLENIR (fail-closed: BILGI'ye dusurulur) ve ihlal ACIKCA basilir.
# --------------------------------------------------------------------
def ic_denetim(bellek, kararlar, muhur_ok):
    ihlaller = []
    if not muhur_ok:
        ihlaller.append("MUHUR: kapi sabitleri degismis (HALT gerektirir)")
    for k in kararlar:
        if k["yon"] not in ("LONG", "SHORT", "NOTR"):
            ihlaller.append(f"{k['sembol']}: yon alani bozuk")
        if k["yon"] == "NOTR" and "berabere" not in k["yon_kaynak"] \
                and "VERI YOK" not in k["yon_kaynak"]:
            ihlaller.append(f"{k['sembol']}: NOTR gerekcesiz (yon gizlenemez)")
        if k["etiket"] == "EMIR-ADAYI" and k["kapi"] != "ACIK":
            ihlaller.append(f"{k['sembol']}: kapi acik degilken EMIR-ADAYI")
    # bellek tutarliligi: son meta KEEP kayitlari J olcumu tasimali
    for d in bellek["deneyler"][-10:]:
        if d["optimizer_version"] == "meta" and d["decision"] == "KEEP" \
                and "J" not in d["metrics"] and "akibet" not in d["metrics"]:
            ihlaller.append(f"{d['experiment_id']}: KEEP olcumsuz")
    if ihlaller:
        for k in kararlar:
            if k["etiket"] == "EMIR-ADAYI":
                k["etiket"] = "BILGI (MUHURLU — ic denetim ihlali)"
    return ihlaller


def override_kontrol():
    """PDF #17 Human Override: meta3_override.json {'dur': true} -> HALT."""
    if os.path.exists(OVERRIDE_YOLU):
        try:
            with open(OVERRIDE_YOLU, encoding="utf-8") as f:
                ov = json.load(f)
            if ov.get("dur") is True:
                return "HALT"
        except Exception:
            return "HALT"   # bozuk override dosyasi da guvenli tarafta durdurur
    return None


# --------------------------------------------------------------------
# NIHAI CALISMA DONGUSU (PDF #21) — her calistirmada
# --------------------------------------------------------------------
def kosu():
    print("META3 KARARGAH v1.0 — recursive karar dongusu "
          "(karar-destek; emir gondermez)")
    print("=" * 70)
    if override_kontrol() == "HALT":
        print("HALT: insan override bayragi aktif (meta3_override.json). "
              "Hicbir islem yapilmadi.")
        return
    bellek = bellek_yukle()
    muhur = kapi_muhru()
    muhur_ok = True
    if bellek["kapi_muhru"] is None:
        bellek["kapi_muhru"] = muhur
        print(f"Kapi muhru ILK kosuda kaydedildi: {muhur[:16]}…")
    elif bellek["kapi_muhru"] != muhur:
        muhur_ok = False
        print("!!! HALT: kapi sabitleri onceki kosudan FARKLI (muhur tutmadi)."
              " Recursive katmanlar sabit degistiremez; degisiklik insan"
              " elinden geldiyse bellek sifirlanmali (meta3_bellek.json sil).")
        return

    t_kosu = time.monotonic()
    motor.selftest()
    try:
        btc_4h = motor.fetch_ohlcv("BTC/USDT", motor.TF_4H, motor.LIMIT_4H)
        btc_15m = motor.fetch_ohlcv("BTC/USDT", motor.TF_15M, motor.LIMIT_15M)
    except Exception:
        traceback.print_exc()
        print("\nKosu BASARISIZ: BTC referans verisi alinamadi.")
        return
    veri_yasi_sn = max(0.0, (pd.Timestamp.now(tz="UTC")
                             - btc_15m.index[-1]).total_seconds())

    # ---- 1) HESAP VERME: onceki onerilerin GERCEK akibeti --------------
    print("\n[HESAP VERME] onceki kosunun onerileri:")
    bekleyen = []
    olculen = 0
    for oneri in bellek["oneriler"]:
        try:
            df15 = (btc_15m if oneri["sembol"] == "BTC/USDT"
                    else motor.fetch_ohlcv(oneri["sembol"], motor.TF_15M, 200))
        except Exception:
            bekleyen.append(oneri)
            continue
        sonuc = akibet_olc(oneri, df15)
        if sonuc is None:
            bekleyen.append(oneri)
            continue
        olculen += 1
        bellek["akibetler"].append({
            "sembol": oneri["sembol"], "varyant": oneri.get("varyant"),
            "etiket": oneri.get("etiket"), "golge": oneri.get("golge", {}),
            "sonuc": sonuc["sonuc"], "r": sonuc["r"],
        })
        r_str = "R yazilmaz" if sonuc["r"] is None else f"R={sonuc['r']:+.2f}"
        print(f"  {oneri['sembol']}: {sonuc['sonuc']} ({r_str})")
    if not bellek["oneriler"]:
        print("  kayit yok (ilk kosu ya da onceki kosuda oneri yoktu) — "
              "gecmis UYDURULMAZ")
    elif olculen == 0:
        print(f"  {len(bekleyen)} oneri hala olculemedi (yeni bar/veri yok)")
    bellek["oneriler"] = bekleyen

    # ---- 2) AGENT: her sembol icin karar (aktif varyantla) -------------
    aktif = bellek["aktif_varyant"]
    print(f"\n[AGENT] aktif varyant: {aktif} — "
          f"{VARYANTLAR[aktif]['aciklama']}")
    kararlar = []
    p_maxlar = []
    for sym in motor.SYMBOLS:
        try:
            if sym == "BTC/USDT":
                a4, a15 = btc_4h, btc_15m
            else:
                a4 = motor.fetch_ohlcv(sym, motor.TF_4H, motor.LIMIT_4H)
                a15 = motor.fetch_ohlcv(sym, motor.TF_15M, motor.LIMIT_15M)
            k = karar_uret(sym, a4, a15, btc_4h, btc_15m)
            k, dusen = varyant_karari(k, aktif)
            kararlar.append(k)
            if k["p_max"] is not None:
                p_maxlar.append(k["p_max"])
        except Exception:
            traceback.print_exc()
            print(f"  [{sym}] atlandi.")
    bellek["_son_p_max"] = (float(np.median(p_maxlar)) if p_maxlar else None)

    # ---- 3) CIKTI: YON + SEVIYELER her sembolde ZORUNLU ---------------
    print("\n[KARARLAR]")
    for k in kararlar:
        print(f"\n=== {k['sembol']} ===")
        print(f"  YON: {k['yon']}  (kaynak: {k['yon_kaynak']})")
        if k["giris"] is not None:
            print(f"  SEVIYELER [{k['etiket']}]: giris {k['giris']:.4f} | "
                  f"stop {k['stop']:.4f} | hedef {k['hedef']:.4f} | "
                  f"zaman-stop {motor.TIME_STOP_BARS} bar")
        else:
            print(f"  SEVIYELER: VERI YOK (ATR/SMA olculemedi ya da yon NOTR"
                  f" — uydurma seviye basilmaz)")
        print(f"  KAPI: {k['kapi']} — {k['kapi_gerekce']}")
        if k.get("oos"):
            print(f"  OLCUM: kural={k['kural']} | OOS ort "
                  f"%{k['oos']['mean'] * 100:.3f} | n={k['oos']['n']} | "
                  f"p_max={k['p_max']:.3f}")
        # oneri kaydi: SEVIYESI OLAN her karar akibet defterine girer
        # (BILGI dahil — dogruluk olcumu icin; EMIR-ADAYI ayrica etiketli)
        if k["giris"] is not None and k["bar_ts"] is not None:
            bellek["oneriler"].append({
                "sembol": k["sembol"], "yon": k["yon"], "giris": k["giris"],
                "stop": k["stop"], "hedef": k["hedef"], "bar_ts": k["bar_ts"],
                "etiket": k["etiket"], "varyant": aktif,
                "golge": k["golge"],
            })

    # ---- 4) META / META2 / META3 (PDF #21 sirasi) ----------------------
    kosu_suresi = time.monotonic() - t_kosu
    print("\n[META]")
    m_karar, m_detay = meta_dongusu(bellek, kosu_suresi, veri_yasi_sn)
    print(f"  META: {m_karar} — {m_detay}")
    bellek["kosu_sayaci"] += 1
    m2 = meta2_dongusu(bellek)
    if m2 is not None:
        print(f"  META2: {m2} (eps={bellek['eps']:.2f})")
    m3 = meta3_dongusu(bellek)
    if m3 is not None:
        print(f"  META3: {m3} (W={bellek['W']})")

    # ---- 5) IC DENETIM (audit) + bellek yazimi -------------------------
    ihlaller = ic_denetim(bellek, kararlar, muhur_ok)
    if ihlaller:
        print("\n[IC DENETIM] IHLAL — emir-adayi etiketleri MUHURLENDI:")
        for i in ihlaller:
            print(f"  - {i}")
    else:
        print("\n[IC DENETIM] ihlal yok "
              f"(muhur {bellek['kapi_muhru'][:12]}…, "
              f"{len(bellek['deneyler'])} deney kaydi, "
              f"{len(bellek['akibetler'])} olculmus akibet)")
    bellek_kaydet(bellek)
    n_olc = len([a for a in bellek["akibetler"] if a.get("r") is not None])
    print(f"\n[OZET] surum v{bellek['surum']} | aktif {bellek['aktif_varyant']}"
          f" | kosu #{bellek['kosu_sayaci']} | olculmus akibet: {n_olc}"
          f" | eps={bellek['eps']:.2f} W={bellek['W']}")
    print("Dogruluk sozlesmesi: bu sistem dogrulugu GARANTI ETMEZ; her "
          "kosuda kendi isabetini OLCER ve yalnizca olculebilir iyilesmeyi "
          "tutar (PDF bolum 24 — bilimsel sinir).")


if __name__ == "__main__":
    kosu()
