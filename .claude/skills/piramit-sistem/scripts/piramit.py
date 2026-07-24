#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PİRAMİT SİSTEMİ — LLM → AI AJAN → ÇOKLU-AJAN → AGI → SI

Piramidin EN ALTINDAN başlar, EN ÜSTE çıkar. Her katman bir öncekinin
VEREMEDİĞİ bilgiyi ekler; eklemiyorsa katman değildir (kutu tiyatrosu yasak):

  K1 LLM         : ham veri + bütünlük denetimi. Çıkarım YOK, yalnız ölçüm.
                   (data-analysis-deep-scan / video-isleme / kline parser)
  K2 AI AJAN     : tek ajan + ARAÇ. Her motor kendi başına, birbirini görmeden
                   gerçek sayısal sonuç üretir. (karar-motoru, grafik-calisma,
                   turev-akis, backtest-motoru, setup_dogrulama)
  K3 ÇOKLU-AJAN  : motorlar DANIŞMAN kuruluna dönüşür; güven ağırlıkları
                   K5'in bir önceki koşuda ürettiği agirlik.json'dan gelir.
  K4 AGI         : alanlar-arası genelleme — çelişki matrisi, fail-closed
                   doğrulama (verifier), şişirilmiş-R denetimi (rr_denetim),
                   5 danışman merceğinin KANITA bağlanması (uzman-modu).
  K5 SI          : (a) ÖNCE güven-ağırlıklı en yüksek sentez (sentez.py),
                   (b) SONRA kendini-kalibre eden geri besleme: geçmiş
                   kararların ölçülmüş akıbetinden (defter.jsonl `gercek_r`)
                   Wilson alt sınırıyla motor ağırlıkları türetilir ve
                   agirlik.json'a yazılır → BİR SONRAKİ koşuyu değiştirir.

FAIL-CLOSED: her katmanın KAPISI vardır. Kapı geçilmezse üst katman KOŞMAZ;
rapor "hangi katmanda, neden durdu" bilgisiyle biter. Uydurma sayı üretilmez;
her sayı bir motorun dosyadan okunan çıktısıdır. Kalibre edilemeyen her sabit
çıktının `varsayimlar` defterine yazılır (etiketsiz gizli eşik yok).

Determinist: rastgelelik yok, duvar-saati yok (zaman damgası veriden alınır).

⚠️ Yalnız karar-destek. Canlı/otomatik emir (gerçek para) DAHİL DEĞİL.

Kullanım:
    python piramit.py --job job.json [--out rapor.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Depo yerleşimi
# --------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
SKILL_DIR = _HERE.parent
SKILLS = SKILL_DIR.parent
REPO = SKILLS.parent.parent
ENGINE = REPO / "engine"
STATE_DIR = SKILL_DIR / "state"

MOTOR = {
    "smc_tespit": SKILLS / "grafik-calisma" / "scripts" / "smc_tespit.py",
    "confluence": SKILLS / "grafik-calisma" / "scripts" / "confluence.py",
    "setup_dogrulama": SKILLS / "grafik-calisma" / "scripts" / "setup_dogrulama.py",
    "backtest": SKILLS / "backtest-motoru" / "scripts" / "backtest.py",
    "turev_akis": SKILLS / "turev-akis" / "scripts" / "turev_akis.py",
    "sentez": SKILLS / "karar-kurulu" / "scripts" / "sentez.py",
    "rr_denetim": SKILLS / "karar-kurulu" / "scripts" / "rr_denetim.py",
    "risk": SKILLS / "risk-yonetimi" / "scripts" / "risk.py",
    "portfolio": SKILLS / "portfoy-optimizasyonu" / "scripts" / "portfolio.py",
    "profile_data": SKILLS / "data-analysis-deep-scan" / "scripts" / "profile_data.py",
    "verify_data": SKILLS / "data-analysis-deep-scan" / "scripts" / "verify_data.py",
    "video_isle": SKILLS / "video-isleme" / "scripts" / "video_isle.py",
    "karar_motoru": ENGINE / "karar_motoru.py",
    "akibet_etiketle": SKILL_DIR / "scripts" / "akibet_etiketle.py",
}

# --------------------------------------------------------------------------
# KONVANSİYONLAR (piyasa eşiği DEĞİL; her çıktının `varsayimlar`ına yazılır)
# --------------------------------------------------------------------------
KONVANSIYON = {
    # karar-motoru → danışman güveni. Motorun KENDİ çıktısından türetilir:
    # zincir sırası (1 = tamamlanmış dönüş dizisi, motorun en güçlü zinciri)
    # + R'nin motorun kendi R_MIN kapısını (1.35) ne kadar aştığı.
    "conf_zincir": {"1": 0.70, "2": 0.60, "3": 0.50},
    "conf_bekle": 0.40,          # BEKLE = yön reddi değil, kalite hükmü (CLAUDE.md)
    "r_min": 1.35,               # karar-motoru R_MIN kapısı (motordan tek-kaynak)
    "r_bonus_max": 0.20,
    "conf_tavan": 0.95,
    # K5 kalibrasyon: ağırlık = clamp(2 × wilson_lo, alt, ust).
    # wilson_lo = 0.50 (yazı-tura alt sınırı) → ağırlık 1.00 (nötr, ceza yok).
    "agirlik_alt": 0.40, "agirlik_ust": 1.00, "agirlik_taban_wr": 0.50,
    # Kapılar
    "min_motor_k2": 2,           # K2: en az bu kadar motor sayısal sonuç üretmeli
    "min_danisman_k3": 2,        # K3: en az bu kadar YÖNLÜ danışman
    # backtest doğrulama kapısı (yalnız job'da `dogrular` beyan edilirse kullanılır)
    "bt_min_pf": 1.0, "bt_min_prob_profit": 0.60,
}

KATMANLAR = ["K1-LLM", "K2-AI-AJAN", "K3-COKLU-AJAN", "K4-AGI", "K5-SI"]
YOK = "VERİ YOK"


class PiramitError(Exception):
    pass


# --------------------------------------------------------------------------
# Yardımcılar
# --------------------------------------------------------------------------
def _num(x):
    """Sayıya çevir; çevrilemiyorsa None (uydurma yok)."""
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
        return v if v == v and abs(v) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _yol(p, taban: Path):
    """Job'daki yolu çöz: mutlak → aynen; değilse job dizini, sonra depo kökü."""
    if not p:
        return None
    q = Path(str(p)).expanduser()
    if q.is_absolute():
        return q if q.exists() else None
    for base in (taban, REPO):
        c = (base / q).resolve()
        if c.exists():
            return c
    return None


def _kos(script: Path, args: list, girdi_job: dict | None = None,
         calisma: Path | None = None) -> dict:
    """Motoru subprocess ile koştur. JSON stdout bekler; metin çıktıyı da saklar.

    Dönen: {"ok", "cikti"(dict|None), "metin", "hata", "kod", "motor"}
    """
    if not script.exists():
        return {"ok": False, "cikti": None, "metin": "", "kod": -1,
                "hata": f"Motor dosyası yok: {script}", "motor": script.name}
    tmp = None
    argv = [sys.executable, str(script)] + list(args)
    if girdi_job is not None:
        tmp = STATE_DIR / "_job" / f"{script.stem}_job.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(girdi_job, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        argv += ["--job", str(tmp)]
    try:
        pr = subprocess.run(argv, capture_output=True, text=True,
                            cwd=str(calisma or script.parent), timeout=900)
    except Exception as e:  # noqa: BLE001 — motor çökmesi rapora girer, gizlenmez
        return {"ok": False, "cikti": None, "metin": "", "kod": -1,
                "hata": f"{type(e).__name__}: {e}", "motor": script.name}
    out = pr.stdout.strip()
    obj = None
    if out.startswith("{") or out.startswith("["):
        try:
            obj = json.loads(out)
        except json.JSONDecodeError:
            obj = None
    return {"ok": pr.returncode == 0, "cikti": obj, "metin": out,
            "kod": pr.returncode, "hata": (pr.stderr.strip()[-800:] or None),
            "motor": script.name}


def _klines_to_candles(path: Path) -> list:
    """Kline dosyasını (Binance JSON / obje listesi / CSV) mum listesine çevirir.

    Parser motorun KENDİsinden alınır (engine/karar_motoru.parse_klines) —
    ikinci bir parser yazmak = ikinci bir doğruluk kaynağı = sapma riski.
    """
    if str(ENGINE) not in sys.path:
        sys.path.insert(0, str(ENGINE))
    import karar_motoru as km  # noqa: PLC0415 — yerel motor, isteğe bağlı yüklenir

    bars = km.parse_klines(str(path))
    return [{"open": b.o, "high": b.h, "low": b.l, "close": b.c, "volume": b.v,
             "time": b.t} for b in bars]


# ==========================================================================
# K1 — LLM (taban): ham veri + bütünlük. Çıkarım YOK.
# ==========================================================================
def k1_llm(job: dict, taban: Path) -> dict:
    veri = job.get("veri") or {}
    kanal, eksik, olcumler = {}, [], {}

    for ad in ("m15", "h4", "ohlcv_csv", "returns_csv", "video"):
        p = _yol(veri.get(ad), taban)
        kanal[ad] = str(p) if p else YOK
        if p is None and veri.get(ad):
            eksik.append(f"{ad}: dosya bulunamadı ({veri.get(ad)})")
        elif p is None:
            eksik.append(f"{ad}: {YOK}")

    # Bar sayıları — motorun kendi parser'ıyla ölçülür (uydurma yok)
    for ad in ("m15", "h4"):
        p = _yol(veri.get(ad), taban)
        if p:
            try:
                mumlar = _klines_to_candles(p)
                olcumler[f"{ad}_bar"] = len(mumlar)
                olcumler[f"{ad}_son_bar"] = mumlar[-1]["time"] if mumlar else YOK
            except Exception as e:  # noqa: BLE001
                olcumler[f"{ad}_bar"] = YOK
                eksik.append(f"{ad}: parse edilemedi ({type(e).__name__}: {e})")

    # data-analysis-deep-scan: tablo bütünlüğü (gerçek profil)
    profil = None
    p_csv = _yol(veri.get("ohlcv_csv"), taban)
    if p_csv:
        r = _kos(MOTOR["profile_data"], ["--input", str(p_csv)])
        if r["ok"] and isinstance(r["cikti"], dict):
            c = r["cikti"]
            profil = {"satir": c.get("row_count", c.get("rows", YOK)),
                      "kolon": c.get("column_count", YOK),
                      "motor": "profile_data.py"}
        else:
            profil = {"durum": "profil ÜRETİLEMEDİ", "hata": r["hata"]}

    # Veri sözleşmesi verilmişse fail-closed doğrulama
    sozlesme = None
    p_sz = _yol(veri.get("veri_sozlesmesi"), taban)
    if p_sz:
        r = _kos(MOTOR["verify_data"], ["--contract", str(p_sz)])
        sozlesme = {"gecti": bool(r["ok"]), "hata": r["hata"],
                    "ozet": (r["cikti"] or {}).get("status", YOK)
                    if isinstance(r["cikti"], dict) else YOK}

    # Video verilmişse kareler çıkarılır (okuma ELLE — mekanikleştirilmez)
    video = None
    p_vid = _yol(veri.get("video"), taban)
    if p_vid:
        r = _kos(MOTOR["video_isle"], [], girdi_job={
            "input": str(p_vid),
            "out_dir": str(STATE_DIR / "kareler"),
            "max_frames": int((veri.get("video_params") or {}).get("max_frames", 12)),
        })
        video = {"ok": r["ok"], "rapor": r["cikti"], "hata": r["hata"],
                 "not": "Kare OKUMA elle yapılır (grafik-calisma); mekanik değil."}

    m15_ok = isinstance(olcumler.get("m15_bar"), int) and olcumler["m15_bar"] > 0
    h4_ok = isinstance(olcumler.get("h4_bar"), int) and olcumler["h4_bar"] > 0
    gecti = (m15_ok and h4_ok) or bool(p_csv)
    kapi = ("K1 kapısı GEÇİLDİ: en az bir tam fiyat kanalı var."
            if gecti else
            "K1 kapısı KAPALI: ne (m15+h4) ne de ohlcv_csv okunabildi → "
            "üst katmanlar KOŞMAZ (uydurma veriyle karar üretilmez).")
    return {"katman": "K1-LLM", "rol": "ham veri + bütünlük denetimi (çıkarım yok)",
            "kanallar": kanal, "olcumler": olcumler, "profil": profil,
            "veri_sozlesmesi": sozlesme, "video": video, "eksikler": eksik,
            "gecti": gecti, "kapi": kapi}


# ==========================================================================
# K2 — AI AJAN: tek ajan + araç. Motorlar birbirini GÖRMEDEN koşar.
# ==========================================================================
def k2_ajan(job: dict, taban: Path, k1: dict) -> dict:
    veri = job.get("veri") or {}
    sonuc, hatalar = {}, []

    # --- karar-motoru (15M + 4H kline) --------------------------------------
    p15, ph4 = _yol(veri.get("m15"), taban), _yol(veri.get("h4"), taban)
    if p15 and ph4:
        sdir = Path(str(_yol(job.get("state_dir"), taban) or (ENGINE / "state")))
        sdir.mkdir(parents=True, exist_ok=True)
        r = _kos(MOTOR["karar_motoru"],
                 ["--m15", str(p15), "--h4", str(ph4), "--state-dir", str(sdir)],
                 calisma=ENGINE)
        durum_p = sdir / "durum.json"
        durum = None
        if r["ok"] and durum_p.exists():
            durum = json.loads(durum_p.read_text(encoding="utf-8"))
        if durum:
            sonuc["karar-motoru"] = {
                "karar": durum.get("karar"), "son_bar_utc": durum.get("son_bar_utc"),
                "akibet_onceki": durum.get("akibet_onceki"),
                "rejim_4h": durum.get("rejim_4h"),
                "rapor_metni": r["metin"][-1500:], "state_dir": str(sdir)}
        else:
            hatalar.append({"motor": "karar-motoru", "hata": r["hata"] or r["metin"][:300]})
    else:
        hatalar.append({"motor": "karar-motoru", "hata": f"m15/h4 {YOK}"})

    # --- grafik-calisma: smc_tespit → confluence ---------------------------
    smc_job = None
    p_csv = _yol(veri.get("ohlcv_csv"), taban)
    if p_csv:
        smc_job = {"input": str(p_csv)}
    elif p15:
        smc_job = {"candles": _klines_to_candles(p15)}
        if ph4:
            smc_job["htf_candles"] = _klines_to_candles(ph4)
    if smc_job is not None:
        if job.get("smc_params"):
            smc_job["params"] = job["smc_params"]
        r = _kos(MOTOR["smc_tespit"], [], girdi_job=smc_job)
        if r["ok"] and isinstance(r["cikti"], dict):
            smc = r["cikti"]
            sonuc["smc_tespit"] = {k: smc.get(k) for k in
                                   ("trend", "rejim", "atr", "olaylar", "htf",
                                    "swing_sayisi", "varsayimlar")}
            cj = smc.get("confluence_job")
            if cj:
                r2 = _kos(MOTOR["confluence"], [], girdi_job=cj)
                if r2["ok"] and isinstance(r2["cikti"], dict):
                    sonuc["grafik-calisma"] = r2["cikti"]
                else:
                    hatalar.append({"motor": "confluence",
                                    "hata": r2["hata"] or r2["metin"][:300]})
            else:
                hatalar.append({"motor": "confluence",
                                "hata": f"smc_tespit confluence_job üretmedi ({YOK})"})
        else:
            hatalar.append({"motor": "smc_tespit", "hata": r["hata"] or r["metin"][:300]})

    # --- setup_dogrulama: tarihsel edge kanıtı (kapı, yön değil) ------------
    if smc_job is not None and job.get("setup_dogrulama", True):
        sd_job = {k: v for k, v in smc_job.items() if k in ("input", "candles")}
        if job.get("setup_params"):
            sd_job["params"] = job["setup_params"]
        r = _kos(MOTOR["setup_dogrulama"], [], girdi_job=sd_job)
        if r["ok"] and isinstance(r["cikti"], dict):
            c = r["cikti"]
            sonuc["setup_dogrulama"] = {
                k: c.get(k) for k in ("SONUC", "sinyal_izni", "gerekce",
                                      "esik_kaynagi", "kalibrasyon", "varsayimlar")}
        else:
            hatalar.append({"motor": "setup_dogrulama",
                            "hata": r["hata"] or r["metin"][:300]})

    # --- turev-akis: kline-körlüğü panzehiri --------------------------------
    turev = veri.get("turev")
    if isinstance(turev, dict) and turev:
        r_full = _kos(MOTOR["turev_akis"], [], girdi_job=turev)
        r_adv = _kos(MOTOR["turev_akis"], ["--emit-advisor"], girdi_job=turev)
        if r_full["ok"] and isinstance(r_full["cikti"], dict):
            sonuc["turev-akis"] = {"rapor": r_full["cikti"],
                                   "danisman": (r_adv["cikti"] if r_adv["ok"] else None)}
        else:
            hatalar.append({"motor": "turev-akis",
                            "hata": r_full["hata"] or r_full["metin"][:300]})
    else:
        hatalar.append({"motor": "turev-akis",
                        "hata": f"türev paneli {YOK} — kurula EKLENMEZ (fail-closed)"})

    # --- backtest-motoru: mekanizma beklentisi ------------------------------
    bt = job.get("backtest")
    if isinstance(bt, dict) and bt:
        bt_job = dict(bt)
        bt_in = _yol(bt_job.get("input"), taban)
        if bt_in:
            bt_job["input"] = str(bt_in)
        r = _kos(MOTOR["backtest"], [], girdi_job=bt_job)
        if r["ok"] and isinstance(r["cikti"], dict):
            sonuc["backtest-motoru"] = {"rapor": r["cikti"],
                                        "dogrular": bt.get("dogrular")}
        else:
            hatalar.append({"motor": "backtest-motoru",
                            "hata": r["hata"] or r["metin"][:300]})

    n = len(sonuc)
    gecti = n >= KONVANSIYON["min_motor_k2"]
    kapi = (f"K2 kapısı GEÇİLDİ: {n} motor bağımsız sayısal sonuç üretti."
            if gecti else
            f"K2 kapısı KAPALI: yalnız {n} motor sonuç üretti "
            f"(gerek {KONVANSIYON['min_motor_k2']}) → tek motor ÇOKLU-AJAN değildir.")
    return {"katman": "K2-AI-AJAN", "rol": "tek ajan + araç; motorlar birbirini görmez",
            "motor_sonuclari": sonuc, "hatalar": hatalar,
            "motor_sayisi": n, "gecti": gecti, "kapi": kapi}


# ==========================================================================
# K3 — ÇOKLU-AJAN: motorlar → danışman kurulu (K5 ağırlıklarıyla)
# ==========================================================================
def _agirliklar() -> dict:
    p = STATE_DIR / "agirlik.json"
    if not p.exists():
        return {"agirliklar": {}, "kaynak": f"agirlik.json {YOK} — ilk koşu, "
                                            "tüm ağırlıklar 1.0 (nötr)"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"agirliklar": d.get("agirliklar", {}) or {},
                "kaynak": str(p), "uretildigi_bar": d.get("uretildigi_bar", YOK),
                "not": d.get("not")}
    except json.JSONDecodeError as e:
        return {"agirliklar": {}, "kaynak": f"agirlik.json BOZUK ({e}) → nötr 1.0"}


def k3_coklu(k2: dict) -> dict:
    m = k2["motor_sonuclari"]
    agir = _agirliklar()
    W = agir["agirliklar"]
    danismanlar, notlar, seviyeler = [], [], {}

    # --- karar-motoru -------------------------------------------------------
    km = m.get("karar-motoru")
    if km and isinstance(km.get("karar"), dict):
        k = km["karar"]
        yon = str(k.get("karar", "")).upper()
        stance = {"LONG": "long", "SHORT": "short"}.get(yon, "flat")
        r = _num(k.get("r"))
        if stance == "flat":
            conf = KONVANSIYON["conf_bekle"]
        else:
            base = KONVANSIYON["conf_zincir"].get(str(k.get("zincir")), 0.50)
            bonus = 0.0
            if r is not None:
                bonus = _clamp((r - KONVANSIYON["r_min"]) / KONVANSIYON["r_min"],
                               0.0, KONVANSIYON["r_bonus_max"])
            conf = min(base + bonus, KONVANSIYON["conf_tavan"])
        danismanlar.append({"name": "karar-motoru", "stance": stance,
                            "confidence": round(conf, 4),
                            "evidence": f"{yon} (zincir {k.get('zincir')}, R={k.get('r')}): "
                                        f"{k.get('neden')}"})
        if stance != "flat":
            seviyeler["karar-motoru"] = {
                "yon": stance, "entry": _num(k.get("giris")), "stop": _num(k.get("stop")),
                "target": _num(k.get("t1")), "kaynak": "karar-motoru (tek-kaynak çıktı)"}

    # --- grafik-calisma (confluence) ---------------------------------------
    gc = m.get("grafik-calisma")
    if isinstance(gc, dict):
        yb = _num(gc.get("yon_bias"))
        karar = str(gc.get("KARAR", "")).upper()
        stance = "flat" if "BEKLE" in karar or yb is None else ("long" if yb > 0 else "short")
        conf = _num(gc.get("confluence_skoru"))
        if conf is None:
            conf = 0.30
            notlar.append("grafik-calisma: confluence_skoru okunamadı → "
                          "güven 0.30 (varsayım, etiketli)")
        danismanlar.append({"name": "grafik-calisma", "stance": stance,
                            "confidence": round(_clamp(conf, 0.0, 1.0), 4),
                            "evidence": f"{gc.get('KARAR')} | confluence={gc.get('confluence_skoru')} "
                                        f"faktörler={gc.get('confluence_faktorleri')} | "
                                        f"rejim={gc.get('rejim')} | kapılar={gc.get('kapi_gerekceleri')}"})
        hed = gc.get("hedefler") or []
        if stance != "flat":
            seviyeler["grafik-calisma"] = {
                "yon": stance, "entry": _num(gc.get("giris_orta")),
                "stop": _num(gc.get("gecersizlik_sl")),
                "target": _num(hed[0]) if hed else None,
                "atr": _num(gc.get("atr_kullanildi")),
                "kaynak": "confluence.py (tek-kaynak çıktı)"}

    # --- turev-akis (motorun kendi danışman çıktısı) ------------------------
    tv = m.get("turev-akis")
    if isinstance(tv, dict) and isinstance(tv.get("danisman"), dict) \
            and tv["danisman"].get("name"):
        danismanlar.append(dict(tv["danisman"]))
    elif tv is not None:
        notlar.append(f"turev-akis: danışman üretilmedi ({YOK}) → kurula eklenmedi "
                      "(fail-closed)")

    # --- K5 geri beslemesi: güven × ağırlık --------------------------------
    for d in danismanlar:
        w = _num(W.get(d["name"]))
        d["_ham_confidence"] = d["confidence"]
        d["_agirlik"] = 1.0 if w is None else round(_clamp(w, 0.0, 1.0), 4)
        d["confidence"] = round(_clamp(d["confidence"] * d["_agirlik"], 0.0, 1.0), 4)

    yonlu = [d for d in danismanlar if d["stance"] != "flat"]
    gecti = len(danismanlar) >= KONVANSIYON["min_danisman_k3"]
    kapi = (f"K3 kapısı GEÇİLDİ: {len(danismanlar)} danışman "
            f"({len(yonlu)} yönlü)." if gecti else
            f"K3 kapısı KAPALI: {len(danismanlar)} danışman < "
            f"{KONVANSIYON['min_danisman_k3']} → kurul kurulamaz.")
    return {"katman": "K3-COKLU-AJAN",
            "rol": "motorlar → danışman kurulu; güven K5 ağırlıklarıyla ölçeklenir",
            "danismanlar": danismanlar, "seviyeler": seviyeler,
            "agirlik_kaynagi": agir, "notlar": notlar,
            "gecti": gecti, "kapi": kapi}


# ==========================================================================
# K4 — AGI: alanlar-arası genelleme, çelişki, fail-closed doğrulama, 5 mercek
# ==========================================================================
def _bt_dogrular(bt_kayit) -> tuple:
    """backtest raporundan doğrulama kararı (kendi metriğiyle, fail-closed)."""
    if not isinstance(bt_kayit, dict):
        return None, None
    rapor = bt_kayit.get("rapor") or {}
    met = rapor.get("metrics") or {}
    mc = rapor.get("monte_carlo") or {}
    pf = _num(met.get("profit_factor"))
    pp = _num(mc.get("prob_profit"))
    ok = (pf is not None and pf > KONVANSIYON["bt_min_pf"]) and \
         (pp is None or pp >= KONVANSIYON["bt_min_prob_profit"])
    return bool(ok), (f"backtest PF={pf}, MC p(kâr)={pp} "
                      f"(kapı: PF>{KONVANSIYON['bt_min_pf']}, "
                      f"p≥{KONVANSIYON['bt_min_prob_profit']})")


def k4_agi(job: dict, k2: dict, k3: dict) -> dict:
    m = k2["motor_sonuclari"]
    verifier, gerekce = {}, {}

    # karar-motoru: KENDİ R kapısı (R_MIN) doğrulayıcıdır
    km = m.get("karar-motoru")
    if km and isinstance(km.get("karar"), dict):
        k = km["karar"]
        r = _num(k.get("r"))
        ok = str(k.get("karar", "")).upper() in ("LONG", "SHORT") and \
            r is not None and r >= KONVANSIYON["r_min"]
        verifier["karar-motoru"] = {"confirmed": bool(ok)}
        gerekce["karar-motoru"] = (f"R={k.get('r')} vs R_MIN={KONVANSIYON['r_min']}; "
                                   f"karar={k.get('karar')}")

    # grafik-calisma: tarihsel edge kanıtı (setup_dogrulama) doğrulayıcıdır
    sd = m.get("setup_dogrulama")
    if any(d["name"] == "grafik-calisma" for d in k3["danismanlar"]):
        if isinstance(sd, dict):
            ok = bool(sd.get("sinyal_izni"))
            verifier["grafik-calisma"] = {"confirmed": ok,
                                          "reason": str(sd.get("gerekce"))[:200]}
            gerekce["grafik-calisma"] = f"setup_dogrulama: {sd.get('SONUC')} — {sd.get('gerekce')}"
        else:
            verifier["grafik-calisma"] = {"confirmed": False,
                                          "reason": f"tarihsel edge kanıtı {YOK}"}
            gerekce["grafik-calisma"] = f"setup_dogrulama koşmadı → {YOK} (fail-closed)"

    # backtest yalnız job'da hangi danışmanı doğruladığı BEYAN edilirse geçer
    bt = m.get("backtest-motoru")
    if isinstance(bt, dict) and bt.get("dogrular"):
        ok, ne = _bt_dogrular(bt)
        hedef = str(bt["dogrular"])
        if ok is not None:
            verifier[hedef] = {"confirmed": bool(ok), "reason": ne}
            gerekce[hedef] = ne

    # --- şişirilmiş-R denetimi (CLAUDE.md: mekanik, tetikleyicisiz) ---------
    rr = {}
    atr_ort = _num((m.get("smc_tespit") or {}).get("atr"))
    for ad, s in (k3.get("seviyeler") or {}).items():
        atr = _num(s.get("atr")) or atr_ort
        if None in (s.get("entry"), s.get("stop"), s.get("target")) or atr is None:
            rr[ad] = {"durum": f"{YOK} — entry/stop/target/ATR eksik, denetim yapılamadı",
                      "atr": atr}
            continue
        r = _kos(MOTOR["rr_denetim"], [], girdi_job={
            "yon": s["yon"], "entry": s["entry"], "stop": s["stop"],
            "target": s["target"], "atr": atr})
        rr[ad] = r["cikti"] if (r["ok"] and isinstance(r["cikti"], dict)) \
            else {"durum": "denetim ÇALIŞMADI", "hata": r["hata"]}

    # şişirilmiş R bulunursa ilgili danışman doğrulanmamış sayılır (fail-closed)
    for ad, rap in rr.items():
        if isinstance(rap, dict) and str(rap.get("verdict", "")).startswith("ŞİŞİ"):
            verifier[ad] = {"confirmed": False,
                            "reason": f"şişirilmiş R: rapor={rap.get('rapor_r', rap.get('r'))} "
                                      f"→ gerçekçi={rap.get('r_gercekci')}"}
            gerekce[ad] = f"rr_denetim: {rap.get('verdict')} — {rap.get('gerekce')}"

    # --- çelişki matrisi ----------------------------------------------------
    stances = {d["name"]: d["stance"] for d in k3["danismanlar"]}
    yonler = {s for s in stances.values() if s != "flat"}
    celiskiler = []
    if len(yonler) > 1:
        celiskiler.append(f"YÖN ÇELİŞKİSİ: {stances} — motorlar zıt yönde; "
                          "sentez güven-ağırlıklı çözer, çoğunluk oyu değil.")
    if km and isinstance(km.get("karar"), dict) and isinstance(m.get("smc_tespit"), dict):
        htf = (m["smc_tespit"].get("htf") or {})
        celiskiler.append(f"MTF bağlam: karar-motoru rejim={km.get('rejim_4h', {}).get('rejim', YOK)}"
                          f" | smc HTF={htf if htf else YOK}")
    if "turev-akis" not in stances:
        celiskiler.append("KLİNE KÖRLÜĞÜ AÇIK: türev kanalı (OI/funding/CVD/LSR/"
                          "likidasyon) kurula girmedi — karar yalnız fiyat yapısına dayanıyor.")

    # --- 5 danışman merceği: her mercek bir MOTOR kanıtına bağlanır ---------
    dis_goz_kaynak = ("setup_dogrulama" if isinstance(sd, dict)
                      else ("backtest-motoru" if isinstance(bt, dict) else None))
    # Muhalif = karara ALEYHTE en güçlü kanıt. Yalnız "zıt yön" değil: kapısı
    # kapanmış (flat) ya da doğrulaması çürütülmüş danışman da muhaliftir —
    # aksi halde tek-yönlü kurulda muhalif mercek sahte biçimde boş kalır.
    muhalif_ad = None
    if len(yonler) > 1:
        by = {}
        for d in k3["danismanlar"]:
            if d["stance"] != "flat":
                by.setdefault(d["stance"], []).append(d)
        if len(by) > 1:
            zayif = min(by.items(), key=lambda kv: sum(x["confidence"] for x in kv[1]))
            muhalif_ad = ", ".join(x["name"] for x in zayif[1])
    if muhalif_ad is None:
        aleyhte = [d["name"] for d in k3["danismanlar"]
                   if d["stance"] == "flat"
                   or verifier.get(d["name"], {}).get("confirmed") is False]
        muhalif_ad = ", ".join(aleyhte) or None
    mercek_tanim = {
        "muhalif": (muhalif_ad, "kurul içindeki zıt-yön danışman(lar)ı"),
        "ilk_prensipler": ("karar-motoru" if km else None,
                           "ham fiyattan zincirle türetilmiş karar (anlatısız)"),
        "genisletici": ("turev-akis" if "turev-akis" in stances else None,
                        "fiyat dışı kanal (OI/funding/CVD/LSR/likidasyon)"),
        "dis_goz": (dis_goz_kaynak, "tarihsel/örneklem-dışı kanıt (anlatıdan bağımsız)"),
        "uygulayici": ("grafik-calisma" if isinstance(m.get("grafik-calisma"), dict) else None,
                       "uygulanabilir seviye/işlem kalitesi"),
    }
    kul = job.get("mercekler") or {}
    mercekler, bagsiz = {}, []
    for ad, (kaynak, rol) in mercek_tanim.items():
        el = kul.get(ad)
        if isinstance(el, dict) and el.get("motor") in m:
            mercekler[ad] = {"kaynak": el["motor"], "rol": rol,
                             "not": el.get("not"), "baglanma": "job (elle)"}
        elif kaynak:
            mercekler[ad] = {"kaynak": kaynak, "rol": rol, "baglanma": "otomatik"}
        else:
            mercekler[ad] = {"kaynak": YOK, "rol": rol,
                             "baglanma": "BAĞLANMADI — kanıt yok"}
            bagsiz.append(ad)

    gecti = True  # K4 bilgi katmanıdır: bulguları K5'e taşır, kararı bastırmaz
    kapi = (f"K4 kapısı GEÇİLDİ: {len(verifier)} danışman doğrulamadan geçti, "
            f"{len([x for x in rr.values() if isinstance(x, dict) and x.get('verdict')])} "
            f"R denetlendi, {len(bagsiz)} mercek kanıta bağlanamadı.")
    return {"katman": "K4-AGI",
            "rol": "alanlar-arası genelleme: doğrulama + çelişki + şişirilmiş-R + 5 mercek",
            "verifier": verifier, "dogrulama_gerekceleri": gerekce,
            "rr_denetimi": rr, "celiskiler": celiskiler,
            "mercekler": mercekler, "baglanmayan_mercekler": bagsiz,
            "gecti": gecti, "kapi": kapi}


# ==========================================================================
# K5 — SI: (a) güven-ağırlıklı sentez → (b) kendini-kalibre eden geri besleme
# ==========================================================================
def _wilson_lo(wins: int, n: int) -> float:
    """kalibrasyon.py'nin Wilson alt sınırı — yeni istatistik YAZILMAZ."""
    yol = str(SKILLS / "grafik-calisma" / "scripts")
    if yol not in sys.path:
        sys.path.insert(0, yol)
    import kalibrasyon as kb  # noqa: PLC0415

    return float(kb.wilson_lo(wins, n)), int(kb.KONVANSIYON["n_taban"])


def _defter_oku(p: Path) -> dict:
    """Defterden ÖLÇÜLMÜŞ sonuçları çıkarır. Ölçülemeyen satır SAYILMAZ.

    R == 0 olan satır da SAYILMAZ: bu "pozisyon açılmadı" demektir (İPTAL /
    tetiklenmedi / belirsiz). Kayıp sayılırsa motor, hiç almadığı işlemden
    ceza alır — istatistik yanlı olur.
    """
    if not p.exists():
        return {"n": 0, "wins": 0, "kaynak": f"{p} {YOK}", "atlanan": 0,
                "pozisyonsuz": 0}
    n = w = atlanan = pozisyonsuz = 0
    for satir in p.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir:
            continue
        try:
            d = json.loads(satir)
        except json.JSONDecodeError:
            atlanan += 1
            continue
        r = _num(d.get("gercek_r"))
        if r is None:
            atlanan += 1      # sonucu ÖLÇÜLMEMİŞ karar istatistiğe girmez
            continue
        if r == 0.0:
            pozisyonsuz += 1  # pozisyon açılmadı → ne kazanç ne kayıp
            continue
        n += 1
        if r > 0:
            w += 1
    return {"n": n, "wins": w, "kaynak": str(p), "atlanan": atlanan,
            "pozisyonsuz": pozisyonsuz}


def k5_si(job: dict, taban: Path, k1: dict, k2: dict, k3: dict, k4: dict) -> dict:
    # ---------- (a) ÖNCE: güven-ağırlıklı en yüksek sentez ------------------
    sentez_job = {
        "question": job.get("soru") or job.get("sembol") or "nihai karar",
        "advisors": [{k: v for k, v in d.items() if not k.startswith("_")}
                     for d in k3["danismanlar"]],
        "verifier": {k: v for k, v in k4["verifier"].items()},
        "invalidation": job.get("gecersizlik") or _gecersizlik(k2),
    }
    if job.get("sentez_thresholds"):
        sentez_job["thresholds"] = job["sentez_thresholds"]
    r = _kos(MOTOR["sentez"], [], girdi_job=sentez_job)
    if not (r["ok"] and isinstance(r["cikti"], dict)):
        return {"katman": "K5-SI", "gecti": False,
                "kapi": f"K5 kapısı KAPALI: sentez motoru çalışmadı ({r['hata']})",
                "sentez": None, "kalibrasyon": None}
    sentez = r["cikti"]

    # ---------- işlem kalitesi: seviyeler MOTORDAN, R denetlenmiş -----------
    islem = _islem_kalitesi(k3, k4, sentez)

    # ---------- pozisyon boyutu (risk-yonetimi) ----------------------------
    boyut = None
    rj = job.get("risk")
    if isinstance(rj, dict) and rj:
        rjob = dict(rj)
        sev = (k3.get("seviyeler") or {}).get(rjob.pop("seviye_kaynagi", "karar-motoru"))
        if rjob.get("op") == "position_size" and rjob.get("method") == "fixed_fractional" \
                and sev and rjob.get("entry") is None:
            rjob["entry"], rjob["stop"] = sev.get("entry"), sev.get("stop")
        if rjob.get("entry") is None and rjob.get("method") == "fixed_fractional":
            boyut = {"durum": f"{YOK} — giriş/stop yok, boyut hesaplanmadı (fail-closed)"}
        else:
            rr_ = _kos(MOTOR["risk"], [], girdi_job=rjob)
            boyut = rr_["cikti"] if (rr_["ok"] and isinstance(rr_["cikti"], dict)) \
                else {"durum": "risk motoru ÇALIŞMADI", "hata": rr_["hata"]}

    # ---------- portföy ağırlığı (portfoy-optimizasyonu) -------------------
    portfoy = None
    pj = job.get("portfoy")
    if isinstance(pj, dict) and pj:
        pjob = dict(pj)
        pin = _yol(pjob.get("returns_csv"), taban)
        if pin:
            pjob["returns_csv"] = str(pin)
        pr = _kos(MOTOR["portfolio"], [], girdi_job=pjob)
        portfoy = pr["cikti"] if (pr["ok"] and isinstance(pr["cikti"], dict)) \
            else {"durum": "portföy motoru ÇALIŞMADI", "hata": pr["hata"]}

    # ---------- (b) SONRA: kendini-kalibre eden geri besleme ---------------
    sdir = (k2["motor_sonuclari"].get("karar-motoru") or {}).get("state_dir") \
        or str(ENGINE / "state")
    danisman_defter = _danisman_defterleri(k1, k2, k3, sdir)
    kal = _kalibre_et(job, taban, k2)
    kal["danisman_defterleri"] = danisman_defter

    return {"katman": "K5-SI",
            "rol": "(a) güven-ağırlıklı sentez → (b) geçmiş akıbetten ağırlık türetme",
            "sentez": sentez, "sentez_girdisi": sentez_job,
            "islem_kalitesi": islem, "pozisyon_boyutu": boyut, "portfoy": portfoy,
            "kalibrasyon": kal, "gecti": True,
            "kapi": "K5 kapısı GEÇİLDİ: nihai karar üretildi ve geri besleme yazıldı."}


def _islem_kalitesi(k3: dict, k4: dict, sentez: dict) -> dict:
    """İŞLEM KALİTESİ hükmü — YÖN'den AYRI (CLAUDE.md iki-satır kuralı).

    "BEKLE" bir işlem-kalitesi hükmüdür, yön reddi DEĞİLDİR. Temiz giriş için
    dört koşulun HEPSİ gerekir (fail-closed):
      1) YON_BIAS ile HİZALI, motordan okunan giriş/stop/hedef seti var
      2) rr_denetim verdict = TUTARLI (şişirilmiş R değil)
      3) R_gercekci ≥ R_MIN (karar-motorunun kendi kapısı)
      4) o danışmanın doğrulaması çürütülmemiş (verifier confirmed ≠ False)
    Eksik koşul(lar) gerekçe olarak AÇIKÇA yazılır — "kapı gerekçesi yok" gibi
    bilgisiz satır üretilmez.
    """
    bias = str(sentez.get("YON_BIAS", "")).lower()
    hedef_yon = {"long": "long", "short": "short"}.get(bias)
    sevs = k3.get("seviyeler") or {}
    rrs = k4.get("rr_denetimi") or {}
    ver = k4.get("verifier") or {}

    adaylar, engeller = [], []
    for ad, s in sevs.items():
        if hedef_yon and s.get("yon") != hedef_yon:
            engeller.append(f"{ad}: seviye yönü ({s.get('yon')}) YON_BIAS ({bias}) ile hizasız")
            continue
        rap = rrs.get(ad) or {}
        verdict = rap.get("verdict")
        r_ger = _num(rap.get("R_gercekci"))
        onay = ver.get(ad, {}).get("confirmed")
        neden = []
        if verdict != "TUTARLI":
            neden.append(f"rr_denetim={verdict or YOK}")
        if r_ger is None or r_ger < KONVANSIYON["r_min"]:
            neden.append(f"R_gerçekçi={r_ger if r_ger is not None else YOK} "
                         f"< R_MIN={KONVANSIYON['r_min']}")
        if onay is False:
            neden.append(f"doğrulama çürütüldü: {ver.get(ad, {}).get('reason', YOK)}")
        if neden:
            engeller.append(f"{ad}: " + "; ".join(neden))
        else:
            adaylar.append({"motor": ad, **s, "R_gercekci": r_ger,
                            "rr_verdict": verdict})

    if adaylar:
        a = max(adaylar, key=lambda x: x["R_gercekci"])
        hukum = "TEMİZ GİRİŞ VAR"
        ozet = (f"TEMİZ GİRİŞ VAR ({a['motor']}): giriş {a.get('entry')}, "
                f"stop {a.get('stop')}, T1 {a.get('target')}, "
                f"R_gerçekçi {a['R_gercekci']} (rr_denetim {a['rr_verdict']})")
    else:
        hukum = "TEMİZ GİRİŞ YOK — TEPKİ/SEVİYE BEKLE"
        ozet = (f"Yön {sentez.get('YON_BIAS')} ama temiz giriş yok — "
                + ("; ".join(engeller) if engeller
                   else f"motorlardan giriş/stop/hedef seti gelmedi ({YOK})"))
    return {"hukum": hukum, "ozet": ozet, "adaylar": adaylar, "engeller": engeller,
            "seviyeler": sevs, "rr_denetimi": rrs,
            "kapi_kurali": ("hizalı seviye + rr_denetim TUTARLI + "
                            f"R_gercekci ≥ {KONVANSIYON['r_min']} + doğrulama çürütülmemiş"),
            "not": "Seviyeler motorların tek-kaynak çıktısıdır; şişirilmiş R "
                   "rr_denetim.py ile mekanik elenmiştir. BEKLE = kalite hükmü, "
                   "yön reddi değil."}


def _gecersizlik(k2: dict) -> str:
    km = (k2["motor_sonuclari"].get("karar-motoru") or {}).get("karar") or {}
    return str(km.get("iptal_kural") or YOK)


def _danisman_defterleri(k1: dict, k2: dict, k3: dict, sdir) -> dict:
    """Her YÖNLÜ danışmanın kararını KENDİ defterine yazar.

    Ağırlık asimetrisi panzehiri: yalnız `karar-motoru`nun defteri olduğu
    sürece kalibrasyon tek motoru cezalandırır, diğerleri sonsuza dek 1.0
    kalır — bu adil değil, ölçülmemiş güven demektir. Artık her danışman
    kendi kararının sicilini tutar; etiketleyici hepsini aynı kuralla ölçer.

    `karar-motoru` HARİÇ: onun defterini motorun kendisi yazar (çift yazım
    istatistiği şişirirdi). Aynı bar için ikinci kayıt YAZILMAZ (tekilleme).
    """
    sdir = Path(str(sdir))
    t = (k1.get("olcumler") or {}).get("m15_son_bar")
    if not isinstance(t, int):
        return {"durum": f"{YOK} — karar barı zamanı okunamadı, danışman defteri yazılmadı"}
    sevs = k3.get("seviyeler") or {}
    yazilan, atlanan = {}, []
    for ad, s in sevs.items():
        if ad == "karar-motoru":
            continue                      # motorun kendi defteri var
        if None in (s.get("entry"), s.get("stop"), s.get("target")):
            atlanan.append(f"{ad}: giriş/stop/hedef eksik → yazılmadı ({YOK})")
            continue
        p = sdir / f"defter_{ad}.jsonl"
        if p.exists():                    # aynı bar iki kez yazılmasın
            var = [x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
            if var:
                try:
                    if json.loads(var[-1]).get("karar_zamani") == t:
                        atlanan.append(f"{ad}: bu bar zaten yazılmış (tekilleme)")
                        continue
                except json.JSONDecodeError:
                    pass
        gc = (k2["motor_sonuclari"].get(ad) or {})
        bolge = gc.get("giris_bolgesi") if isinstance(gc, dict) else None
        alt, ust = ((float(bolge[0]), float(bolge[1]))
                    if isinstance(bolge, list) and len(bolge) == 2
                    else (float(s["entry"]), float(s["entry"])))
        kayit = {
            "karar_zamani": t, "motor": ad, "kaynak": "piramit K5",
            "karar": {"karar": s["yon"].upper(), "yon": s["yon"].upper(),
                      "giris_alt": alt, "giris_ust": ust,
                      "giris": float(s["entry"]), "stop": float(s["stop"]),
                      "t1": float(s["target"]),
                      # confluence `iptal` üretmez → uydurulmaz: stop kullanılır
                      "iptal": float(s["stop"])},
            "varsayim": "iptal seviyesi motordan gelmedi → stop kullanıldı "
                        "(muhafazakâr; uydurma seviye üretilmedi)",
        }
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        yazilan[ad] = str(p)
    return {"yazilan": yazilan, "atlanan": atlanan, "karar_zamani": t}


def _etiketle(job: dict, taban: Path, defterler: dict, sdir) -> dict:
    """Akıbet etiketleyiciyi koştur: ölçülmemiş kararlara fiyat yolundan R yaz.

    Bar arşivi 15M penceresinin kaymasını telafi eder (eski karar pencereden
    düşse bile ölçülebilir). Arşiv fiyat GERÇEĞİdir, karar hafızası değildir —
    bu yüzden kum havuzu koşusunda bile gerçek arşive yazılabilir (job'daki
    `bar_arsivi` ile yönlendirilir).
    """
    m15 = _yol((job.get("veri") or {}).get("m15"), taban)
    if m15 is None:
        return {"durum": f"{YOK} — m15 yok, akıbet etiketlenmedi"}
    arsiv = _yol(job.get("bar_arsivi"), taban) or (
        Path(str(job.get("bar_arsivi"))) if job.get("bar_arsivi")
        else Path(str(sdir)) / "bar_arsivi.jsonl")
    raporlar = {}
    for motor, yol in defterler.items():
        p = _yol(yol, taban) or Path(str(yol))
        r = _kos(MOTOR["akibet_etiketle"],
                 ["--defter", str(p), "--m15", str(m15),
                  "--arsiv", str(arsiv), "--yaz"])
        if r["ok"] and isinstance(r["cikti"], dict):
            c = r["cikti"]
            raporlar[motor] = {k: c.get(k) for k in
                               ("etiketlenen", "elle_korunan", "olculemeyen",
                                "bar_havuzu", "arsiv")}
        else:
            raporlar[motor] = {"durum": "etiketleyici ÇALIŞMADI", "hata": r["hata"]}
    return raporlar


def _kalibre_et(job: dict, taban: Path, k2: dict) -> dict:
    """SI geri beslemesi: ölçülmüş akıbetlerden motor ağırlığı türet.

    Kural (fail-closed, konvansiyon — defterde raporlanır):
      - Yalnız `gercek_r` alanı ÖLÇÜLMÜŞ satırlar sayılır.
      - n < n_taban (kalibrasyon.py) → ağırlık DEĞİŞTİRİLMEZ (1.0). Kanıt yoksa
        ceza da ödül de yok; "öğrendim" iddiası üretilmez.
      - n ≥ n_taban → ağırlık = clamp(2 × wilson_lo, 0.40, 1.00).
        wilson_lo = 0.50 (yazı-tura alt sınırı) → 1.00 (nötr).
    Ağırlık BU koşuyu değil, BİR SONRAKİ koşunun K3 katmanını etkiler.
    """
    defterler = job.get("akibet_defterleri") or {}
    sdir = (k2["motor_sonuclari"].get("karar-motoru") or {}).get("state_dir")
    if "karar-motoru" not in defterler:
        defterler["karar-motoru"] = str(Path(sdir) / "defter.jsonl") if sdir \
            else str(ENGINE / "state" / "defter.jsonl")
    # Danışman defterleri (defter_<motor>.jsonl) otomatik dahil edilir →
    # her motor KENDİ siciliyle kalibre olur (ağırlık asimetrisi kapanır).
    kok = Path(sdir) if sdir else (ENGINE / "state")
    for p in sorted(kok.glob("defter_*.jsonl")):
        ad = p.stem[len("defter_"):]
        defterler.setdefault(ad, str(p))

    # --- ÖNCE etiketleme: ölçülmemiş kararların akıbeti fiyat yolundan yazılır
    # (elle yazım beklenmez; elle yazılmış gercek_r ezilmez). Bu adım olmadan
    # kalibrasyon sonsuza dek "n < n_taban" der ve SI katmanı öğrenemez.
    etiket = _etiketle(job, taban, defterler, sdir)

    agirliklar, ayrinti = {}, {}
    n_taban = None
    for motor, yol in defterler.items():
        p = _yol(yol, taban) or Path(str(yol))
        st = _defter_oku(p)
        wlo, n_taban = _wilson_lo(st["wins"], st["n"]) if st["n"] > 0 else (None, None)
        if n_taban is None:
            _, n_taban = _wilson_lo(0, 1)
        if st["n"] < n_taban:
            agirliklar[motor] = 1.0
            ayrinti[motor] = {**st, "wilson_lo": wlo, "agirlik": 1.0,
                              "durum": f"{YOK} — ölçülmüş sonuç {st['n']} < n_taban "
                                       f"{n_taban}; ağırlık DEĞİŞTİRİLMEDİ (fail-closed)"}
        else:
            w = round(_clamp(2.0 * wlo, KONVANSIYON["agirlik_alt"],
                             KONVANSIYON["agirlik_ust"]), 4)
            agirliklar[motor] = w
            ayrinti[motor] = {**st, "wilson_lo": round(wlo, 4), "agirlik": w,
                              "durum": f"kalibre edildi: {st['wins']}/{st['n']} "
                                       f"ölçülmüş kazanan"}

    bar = (k2["motor_sonuclari"].get("karar-motoru") or {}).get("son_bar_utc", YOK)
    kayit = {
        "agirliklar": agirliklar, "ayrinti": ayrinti, "uretildigi_bar": bar,
        "etiketleme": etiket,
        "kural": ("agirlik = clamp(2 × wilson_lo(kazanan, n), "
                  f"{KONVANSIYON['agirlik_alt']}, {KONVANSIYON['agirlik_ust']}); "
                  f"n < n_taban ({n_taban}) → 1.0 (değiştirilmez)"),
        "not": ("Bu ağırlıklar BİR SONRAKİ koşunun K3 katmanında uygulanır. "
                "Ölçülmemiş sonuç istatistiğe girmez — 'öğrendim' iddiası "
                "kanıtsız üretilmez."),
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "agirlik.json").write_text(
        json.dumps(kayit, ensure_ascii=False, indent=2), encoding="utf-8")
    return kayit


# ==========================================================================
# Orkestrasyon
# ==========================================================================
def kos(job: dict, taban: Path) -> dict:
    rapor = {
        "sistem": "PİRAMİT — LLM→AI AJAN→ÇOKLU-AJAN→AGI→SI",
        "soru": job.get("soru", YOK), "sembol": job.get("sembol", YOK),
        "katman_sirasi": KATMANLAR, "katmanlar": [],
        "varsayimlar": [
            f"karar-motoru güven eşlemesi: zincir tabanı {KONVANSIYON['conf_zincir']}, "
            f"BEKLE={KONVANSIYON['conf_bekle']}, R bonusu ≤{KONVANSIYON['r_bonus_max']} "
            f"(R_MIN={KONVANSIYON['r_min']} motordan) — KONVANSİYON, piyasa eşiği değil",
            "grafik-calisma güveni = confluence_skoru (motorun kendi çıktısı, eşleme yok)",
            "turev-akis güveni = motorun kendi to_advisor çıktısı (eşleme yok)",
            f"K2 kapısı ≥{KONVANSIYON['min_motor_k2']} motor, K3 kapısı "
            f"≥{KONVANSIYON['min_danisman_k3']} danışman — yapı kuralı",
            f"SI ağırlığı = clamp(2×wilson_lo, {KONVANSIYON['agirlik_alt']}, "
            f"{KONVANSIYON['agirlik_ust']}); taban wr={KONVANSIYON['agirlik_taban_wr']}",
        ],
        "not": ("Yalnız karar-destek. Canlı/otomatik emir DAHİL DEĞİL. "
                "Her sayı bir motorun dosyadan okunan çıktısıdır."),
    }

    k1 = k1_llm(job, taban)
    rapor["katmanlar"].append(k1)
    if not k1["gecti"]:
        return _durdur(rapor, "K1-LLM", k1["kapi"])

    k2 = k2_ajan(job, taban, k1)
    rapor["katmanlar"].append(k2)
    if not k2["gecti"]:
        return _durdur(rapor, "K2-AI-AJAN", k2["kapi"])

    k3 = k3_coklu(k2)
    rapor["katmanlar"].append(k3)
    if not k3["gecti"]:
        return _durdur(rapor, "K3-COKLU-AJAN", k3["kapi"])

    k4 = k4_agi(job, k2, k3)
    rapor["katmanlar"].append(k4)

    k5 = k5_si(job, taban, k1, k2, k3, k4)
    rapor["katmanlar"].append(k5)
    if not k5["gecti"]:
        return _durdur(rapor, "K5-SI", k5["kapi"])

    s = k5["sentez"]
    ik = k5["islem_kalitesi"]
    rapor["ZIRVE"] = {
        "YON_BIAS": s.get("YON_BIAS"),
        "ISLEM_KALITESI": ik["hukum"],
        "sentez_karari": s.get("KARAR"),
        "guven_skoru": s.get("guven_skoru"),
        "yon_skoru": s.get("yon_skoru"),
        "uzlasi": s.get("uzlasi"),
        "muhalefet": s.get("muhalefet"),
        "kapi_gerekceleri": (s.get("kapi_gerekceleri") or []) + ik["engeller"],
        "gecersizlik": sentez_gecersizlik(s),
        "seviyeler": ik["seviyeler"],
        "pozisyon_boyutu": k5.get("pozisyon_boyutu"),
        "ulasilan_katman": "K5-SI (zirve)",
        "iki_satir": {
            "1_YON": f"YÖN (bias): {s.get('YON_BIAS')} — ağırlıklı yön skoru "
                     f"{s.get('yon_skoru')}, uzlaşı {s.get('uzlasi')} "
                     "(kapıdan bağımsız; BEKLE yön reddi değildir)",
            "2_ISLEM_KALITESI": f"İŞLEM KALİTESİ: {ik['ozet']}",
        },
    }
    rapor["durum"] = "TAMAM — piramidin tepesine ulaşıldı"
    _deftere_yaz(rapor)
    return rapor


def sentez_gecersizlik(s: dict):
    """sentez.py geçersizlik alanını `gecersizlik_kosulu` adıyla verir."""
    return (s.get("gecersizlik_kosulu") or s.get("invalidation")
            or s.get("gecersizlik") or YOK)


def _durdur(rapor: dict, katman: str, kapi: str) -> dict:
    rapor["durum"] = f"DURDU — {katman}"
    rapor["ZIRVE"] = {"ulasilan_katman": katman, "neden": kapi,
                      "YON_BIAS": YOK, "ISLEM_KALITESI": "NÖTR-BEKLE (fail-closed)",
                      "not": "Alt katman kapısı geçilmeden üst katman koşmaz; "
                             "eksik veriyle karar UYDURULMAZ."}
    _deftere_yaz(rapor)
    return rapor


def _deftere_yaz(rapor: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    kayit = {"sembol": rapor.get("sembol"), "soru": rapor.get("soru"),
             "durum": rapor.get("durum"), "zirve": rapor.get("ZIRVE")}
    with (STATE_DIR / "piramit_defter.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def ozet_metin(rapor: dict) -> str:
    L = ["=" * 68, "PİRAMİT SİSTEMİ — " + str(rapor.get("sembol", YOK)), "=" * 68]
    for k in rapor["katmanlar"]:
        isaret = "✔" if k.get("gecti") else "✖"
        L.append(f"{isaret} {k['katman']:<14} {k.get('kapi', '')}")
    z = rapor.get("ZIRVE") or {}
    L.append("-" * 68)
    for k in rapor["katmanlar"]:
        if k["katman"] == "K3-COKLU-AJAN":
            for d in k.get("danismanlar", []):
                L.append(f"  · {d['name']:<16} {d['stance']:<6} güven={d['confidence']} "
                         f"(ham {d['_ham_confidence']} × ağırlık {d['_agirlik']})")
    L.append("-" * 68)
    if "iki_satir" in z:
        L.append(z["iki_satir"]["1_YON"])
        L.append(z["iki_satir"]["2_ISLEM_KALITESI"])
        L.append(f"GEÇERSİZLİK: {z.get('gecersizlik', YOK)}")
    else:
        L.append(f"ULAŞILAN KATMAN: {z.get('ulasilan_katman', YOK)}")
        L.append(f"NEDEN: {z.get('neden', YOK)}")
    L.append("=" * 68)
    L.append("⚠️ Yalnız karar-destek; canlı/otomatik emir DAHİL DEĞİL.")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Piramit sistemi (LLM→AI AJAN→ÇOKLU-AJAN→AGI→SI)")
    ap.add_argument("--job", required=True, help="JSON job dosyası")
    ap.add_argument("--out", help="Tam raporu bu dosyaya yaz")
    ap.add_argument("--ozet", action="store_true", help="Yalnız katman/zirve özeti bas")
    args = ap.parse_args(argv)

    p = Path(args.job).expanduser().resolve()
    job = json.loads(p.read_text(encoding="utf-8"))
    rapor = kos(job, p.parent)

    if args.out:
        Path(args.out).expanduser().write_text(
            json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.ozet:
        print(ozet_metin(rapor))
    else:
        print(json.dumps(rapor, ensure_ascii=False, indent=2))
    return 0 if str(rapor.get("durum", "")).startswith("TAMAM") else 2


if __name__ == "__main__":
    sys.exit(main())
