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
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import gozlemci as GZ  # noqa: E402

# --------------------------------------------------------------------------
# Depo yerleşimi
# --------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
SKILL_DIR = _HERE.parent
SKILLS = SKILL_DIR.parent
REPO = SKILLS.parent.parent
ENGINE = REPO / "engine"
STATE_DIR = SKILL_DIR / "state"        # KOŞU ARTIĞI: silinebilir, gitignore'da
# HAFIZA: öğrenilmiş ağırlıklar. Koşu artıklarından AYRI dizinde tutulur —
# aynı klasörde olsaydı bir temizlik komutu (rm -rf state) SI hafızasını
# sessizce silerdi (bir kez oldu: commit 9a86f62'de index'ten düştü).
HAFIZA_DIR = SKILL_DIR / "hafiza"
AGIRLIK_DOSYA = HAFIZA_DIR / "agirlik.json"    # ana sembol (engine/state)
ESKI_AGIRLIK = STATE_DIR / "agirlik.json"      # geriye uyumluluk (taşıma)

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
    "korelasyon": SKILL_DIR / "scripts" / "korelasyon.py",
    "usd_hedef": SKILL_DIR / "scripts" / "usd_hedef.py",
    "kiyas": SKILL_DIR / "scripts" / "kiyas.py",
    "esik_kalibre": SKILL_DIR / "scripts" / "esik_kalibre.py",
    "emir_plani": SKILL_DIR / "scripts" / "emir_plani.py",
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
    "gorsel_tavan": 0.50,        # elle görsel okumanın azami güveni (ölçüm değil)
    "min_motor_k2": 2,           # K2: en az bu kadar motor sayısal sonuç üretmeli
    "min_danisman_k3": 2,        # K3: en az bu kadar YÖNLÜ danışman
    # backtest doğrulama kapısı (yalnız job'da `dogrular` beyan edilirse kullanılır)
    "bt_min_pf": 1.0, "bt_min_prob_profit": 0.60,
    # ZORUNLU GİRDİ TAZELİĞİ: elle gelen likidasyon/görsel okuma HANGİ veriye
    # ait olduğunu damgasıyla kanıtlamalı. Damgasız ya da son bardan bu kadar
    # dakikadan daha eski okuma BAYAT sayılır (yeni kline + eski panel = sahte
    # güncellik). 4H panel okuması bir 4H bar boyu geçerli kabul edilir.
    "zorunlu_damga_tolerans_dk": 240,
    # Eşik kalibrasyonu ufku: kaç barlık yön devamlılığı ölçülecek. 15M seride
    # 8 bar = 2 saat — kurulum tetiği ile T1 arası tipik pencere.
    "esik_ufuk_bar": 8,
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


_DAMGA_ALAN = ("bar_ms", "bar_utc", "zaman_utc", "okuma_utc", "zaman_ms",
               "timestamp", "ts", "zaman", "bar")
_DAMGA_BICIM = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M")


def _damga_ms(d: dict):
    """Elle gelen zorunlu girdinin zaman damgası (ms, UTC) — yoksa None.

    Sayı (s ya da ms epoch) ya da 'YYYY-MM-DD HH:MM' metni kabul edilir.
    Metinde damgadan sonra açıklama olabilir (ör. '… (yerel) / veri barı …');
    yalnız baştaki damga okunur. Çözülemeyen damga = damga YOK (fail-closed).
    """
    if not isinstance(d, dict):
        return None
    for ad in _DAMGA_ALAN:
        if ad not in d:
            continue
        v = d[ad]
        n = _num(v)
        if n is not None and n > 1e8:
            return n * 1000.0 if n < 1e11 else n      # saniye → ms
        if isinstance(v, str):
            m = re.match(r"\s*(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)", v)
            if not m:
                continue
            for b in _DAMGA_BICIM:
                try:
                    t = datetime.datetime.strptime(m.group(1), b)
                    return t.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000.0
                except ValueError:
                    continue
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

    # --- ZORUNLU GİRDİLER (kullanıcı sözleşmesi: her koşuda gelmeli) --------
    # Bunlar "opsiyonel kanal" DEĞİLDİR. Eksikse koşu durmaz ama eksiklik
    # çıktının EN ÜSTÜNDE taşınır — sessizce atlanamaz.
    zorunlu, zorunlu_eksik = {}, []
    son_ms = _num(olcumler.get("m15_son_bar"))
    tol_dk = KONVANSIYON["zorunlu_damga_tolerans_dk"]

    def _taze(d: dict, ad: str) -> tuple:
        """Bu okuma BU verinin barına mı ait? Damgasız/eski = BAYAT (fail-closed).

        Neden: eski panel okuması yeni kline'la birlikte sessizce 'güncel'
        sayılıyordu — zorunlu girdi var görünüp aslında dünün ölçümüydü.
        """
        ms = _damga_ms(d)
        if ms is None:
            return False, (f"{ad}: zaman damgası YOK (`bar_utc`/`zaman_utc`) → hangi "
                           "veriye ait olduğu kanıtlanamıyor, BAYAT sayıldı")
        if son_ms is None:
            return True, f"{ad}: damga var, kline son barı ölçülemedi — kıyaslanmadı"
        yas = (son_ms - ms) / 60000.0
        if yas > tol_dk:
            return False, (f"{ad}: BAYAT — okuma son bardan {yas:.0f} dk eski "
                           f"(tolerans {tol_dk:.0f} dk); yeni kline eski panel "
                           "okumasıyla birleştirilmez")
        return True, f"{ad}: taze (son bara göre {yas:.0f} dk)"

    tazelik = []
    lik = _yol((veri.get("likidasyon") or "engine/girdi/turev_ham/likidasyon.json"), taban)
    if lik:
        try:
            d = json.loads(lik.read_text(encoding="utf-8"))
            taze, gerekce = _taze(d, "likidasyon")
            tazelik.append(gerekce)
            if not taze:
                zorunlu_eksik.append(gerekce)
            elif _num(d.get("liq_long")) is not None and _num(d.get("liq_short")) is not None:
                zorunlu["likidasyon"] = {"liq_long": _num(d["liq_long"]),
                                         "liq_short": _num(d["liq_short"]),
                                         "kaynak": str(d.get("kaynak", "elle/CoinGlass")),
                                         "tazelik": gerekce}
            else:
                zorunlu_eksik.append("likidasyon: dosya var ama liq_long/liq_short sayısal değil")
        except (OSError, json.JSONDecodeError) as e:
            zorunlu_eksik.append(f"likidasyon: okunamadı ({type(e).__name__})")
    else:
        zorunlu_eksik.append("likidasyon: CoinGlass long/short değerleri GELMEDİ "
                             "→ türev kapsamı eksik kalır")
    gor = _yol((veri.get("gorsel") or "engine/girdi/gorsel_okuma.json"), taban)
    if gor:
        try:
            g = json.loads(gor.read_text(encoding="utf-8"))
            taze, gerekce = _taze(g, "görsel okuma")
            tazelik.append(gerekce)
            if not taze:
                zorunlu_eksik.append(gerekce)
            elif str(g.get("trend", "")).lower() in ("bull", "bear", "yatay"):
                zorunlu["gorsel"] = {**g, "tazelik": gerekce}
            else:
                zorunlu_eksik.append("görsel okuma: `trend` alanı bull|bear|yatay değil")
        except (OSError, json.JSONDecodeError) as e:
            zorunlu_eksik.append(f"görsel okuma: okunamadı ({type(e).__name__})")
    else:
        zorunlu_eksik.append("görsel okuma: grafik ekran görüntüsü/video GELMEDİ "
                             "→ mekanik SMC tespiti karşılıklı teyit edilemez")

    # --- HESAP VERME: önceki koşunun verdiği seviyeler tuttu mu? ----------
    # Bu bir ÖLÇÜMDÜR (çıkarım değil) → K1'e aittir. Yeni analizden ÖNCE
    # cevaplanır; kayıt yoksa "ilk analiz" denir, geçmiş uydurulmaz.
    akibet = {"durum": f"{YOK} — önceki koşu kaydı aranmadı"}
    onceki_kayit = _onceki_kosu(job, taban)
    p15o = _yol(veri.get("m15"), taban)
    if p15o is not None:
        try:
            if str(_SCRIPTS) not in sys.path:
                sys.path.insert(0, str(_SCRIPTS))
            import kiyas as KY  # noqa: PLC0415
            import akibet_etiketle as _AE  # noqa: PLC0415
            arsiv = _yol(job.get("bar_arsivi"), taban) or (
                Path(str(job.get("bar_arsivi"))) if job.get("bar_arsivi") else None)
            kaynaklar = [str(p15o)] + ([str(arsiv)] if arsiv and arsiv.exists() else [])
            akibet = KY.akibet_olc(onceki_kayit, _AE.bar_yukle(kaynaklar))
        except Exception as e:  # noqa: BLE001 — ölçüm hatası gizlenmez
            akibet = {"durum": f"ölçüm HATASI ({type(e).__name__}: {e})"}

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
            "zorunlu_girdiler": zorunlu, "zorunlu_eksik": zorunlu_eksik,
            "zorunlu_tazelik": tazelik or [f"{YOK} — zorunlu girdi dosyası yok"],
            "onceki_karar_akibeti": akibet, "onceki_kayit_var": bool(onceki_kayit),
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

    # --- grafik-calisma 4H: KURULUM ölçeği (sabit-USDT motorunun ATR/likidite
    # kaynağı; ölçümle 4H seçildi — 15m yapısı 33 puanlık stopla ilgisiz) -----
    if ph4:
        r = _kos(MOTOR["smc_tespit"], [],
                 girdi_job={"candles": _klines_to_candles(ph4)})
        if r["ok"] and isinstance(r["cikti"], dict):
            c = r["cikti"]
            sonuc["smc_tespit_h4"] = {k: c.get(k) for k in
                                      ("trend", "rejim", "atr", "likidite",
                                       "order_blocks", "acik_fvgler", "olaylar")}
        else:
            hatalar.append({"motor": "smc_tespit_h4",
                            "hata": r["hata"] or r["metin"][:300]})

    # --- korelasyon: ikinci sembol bağımsız bahis mi, kopya mı? -------------
    kor = job.get("korelasyon")
    if isinstance(kor, dict) and kor:
        pa = _yol(kor.get("a"), taban) or p15
        pb = _yol(kor.get("b"), taban)
        if pa and pb:
            r = _kos(MOTOR["korelasyon"],
                     ["--a", str(pa), "--b", str(pb),
                      "--ad-a", str(kor.get("ad_a", "A")),
                      "--ad-b", str(kor.get("ad_b", "B"))])
            if r["ok"] and isinstance(r["cikti"], dict):
                sonuc["korelasyon"] = r["cikti"]
            else:
                hatalar.append({"motor": "korelasyon",
                                "hata": r["hata"] or r["metin"][:300]})
        else:
            hatalar.append({"motor": "korelasyon",
                            "hata": f"karşılaştırma serisi {YOK} (a/b yolu çözülemedi)"})

    # --- turev-akis: kline-körlüğü panzehiri --------------------------------
    turev = veri.get("turev")
    # TAZE LİKİDASYON ÜSTÜN GELİR: turev.json kancada, elle girilen
    # likidasyon.json'dan ÖNCE üretilmiş olabilir. O zaman aynı raporda iki
    # farklı likidasyon dolaşır: zorunlu-girdi denetimi taze dosyayı okur,
    # türev motoru bayat kopyayı kullanır (2026-07-25'te yakalandı: panel
    # short-ağırlıklı iken motor hâlâ "long kaskad" diyordu). Damgası
    # doğrulanmış zorunlu girdi, önbelleği EZER.
    z_lik = ((k1.get("zorunlu_girdiler") or {}).get("likidasyon") or {})
    lik_bayat = any(str(x).startswith("likidasyon")
                    for x in (k1.get("zorunlu_eksik") or []))
    if isinstance(turev, dict) and turev and not z_lik and lik_bayat:
        # BAYAT/damgasız likidasyon türev motoruna VERİLMEZ. turev.json'u kanca
        # üretir ve damgaya BAKMAZ; K1 bayat deyip dışlarken K2 aynı bayat
        # değeri kullanıyordu (adversarial denetim: bayat likidasyon kararı
        # çeviriyordu). Kanal düşünce turev-akis ağırlıkları normalize eder ve
        # `kapsam` 1.0'ın altına iner — "kapsam tam" yalanı da biter.
        atilan = (turev.get("liq_long"), turev.get("liq_short"))
        turev = {k: v for k, v in turev.items()
                 if k not in ("liq_long", "liq_short")}
        turev["_likidasyon_kaynagi"] = (
            f"BAYAT/damgasız zorunlu girdi → türev motoruna VERİLMEDİ "
            f"(atılan bayat kopya {atilan}; fail-closed)")
    if isinstance(turev, dict) and turev and z_lik:
        eski = (turev.get("liq_long"), turev.get("liq_short"))
        yeni = (z_lik.get("liq_long"), z_lik.get("liq_short"))
        if None not in yeni and eski != yeni:
            turev = {**turev, "liq_long": yeni[0], "liq_short": yeni[1],
                     "_likidasyon_kaynagi": (
                         f"zorunlu girdi (damgalı) {yeni} — turev.json'daki "
                         f"bayat kopya {eski} EZİLDİ")}
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
def _okuma_dizini(job: dict, taban: Path, k2: dict | None = None) -> Path:
    """Defter OKUMA dizini (sicil buradan okunur; yazma dizininden AYRI).

    Kum havuzu koşusunda `state_dir` geçici dizindir ama `defter_dizini` gerçek
    sicili gösterir — sicil oradan okunur, öğrenilmiş ağırlık silinmez.
    """
    p = _yol(job.get("defter_dizini"), taban)
    if p is not None:
        return Path(str(p))
    if job.get("defter_dizini"):
        return Path(str(job["defter_dizini"]))
    sdir = None
    if k2:
        sdir = ((k2.get("motor_sonuclari") or {}).get("karar-motoru")
                or {}).get("state_dir")
    if not sdir:
        sdir = _yol(job.get("state_dir"), taban) or job.get("state_dir")
    return Path(str(sdir)) if sdir else (ENGINE / "state")


def _hafiza_yolu(okuma) -> Path:
    """Ağırlık dosyası defter-okuma dizinine göre AD ALANLIDIR.

    Neden: ikinci bir sembolü (ör. ETH) kendi state dizininde koşturmak, tek
    global agirlik.json'u O SEMBOLÜN siciliyle EZİYORDU — BTC'nin öğrenilmiş
    ağırlığı sessizce 1.0'a dönerdi (çapraz-sembol hafıza çarpışması, 2026-07-24
    ETH koşusunda gözlendi). Her sicil kendi hafızasını taşır; ana sembol
    (engine/state) geriye uyumlu olarak agirlik.json'da kalır.
    """
    okuma = Path(str(okuma))
    try:
        r_ok, r_var = okuma.resolve(), (ENGINE / "state").resolve()
    except OSError:
        return AGIRLIK_DOSYA
    if r_ok == r_var:
        return AGIRLIK_DOSYA
    try:
        ad = "_".join(r_ok.relative_to(r_var).parts)      # engine/state/eth → eth
    except ValueError:
        # engine/state DIŞI sicil (geçici test dizini, harici defter): hafıza
        # sicilin yanında tutulur — depo hafıza dizini geçici koşularla
        # kirlenmez, ama aynı sicil aynı dosyayı bulur (determinist).
        return r_ok / "agirlik.json"
    return HAFIZA_DIR / f"agirlik_{ad}.json"


def _agirliklar(hafiza_p: Path | None = None) -> dict:
    hafiza_p = hafiza_p or AGIRLIK_DOSYA
    p = hafiza_p if hafiza_p.exists() else (
        ESKI_AGIRLIK if hafiza_p == AGIRLIK_DOSYA else hafiza_p)
    if not p.exists():
        return {"agirliklar": {}, "kaynak": f"{p.name} {YOK} — bu sicilin ilk "
                                            "koşusu, tüm ağırlıklar 1.0 (nötr)"}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"agirliklar": d.get("agirliklar", {}) or {},
                "kaynak": str(p), "uretildigi_bar": d.get("uretildigi_bar", YOK),
                "not": d.get("not")}
    except json.JSONDecodeError as e:
        return {"agirliklar": {}, "kaynak": f"agirlik.json BOZUK ({e}) → nötr 1.0"}


def k3_coklu(k1: dict, k2: dict, hafiza_p: Path | None = None) -> dict:
    m = k2["motor_sonuclari"]
    agir = _agirliklar(hafiza_p)
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

    # --- görsel okuma (ELLE) — mekanik SMC'nin karşılıklı teyidi -----------
    # Ölçüm DEĞİL, okumadır: güveni tavanla sınırlanır ve doğrulaması
    # smc_tespit ile UYUŞMASINA bağlıdır (K4). Uyuşmazsa çürütülür.
    g = (k1.get("zorunlu_girdiler") or {}).get("gorsel")
    if isinstance(g, dict):
        trend = str(g.get("trend", "")).lower()
        stance = {"bull": "long", "bear": "short"}.get(trend, "flat")
        conf = _num(g.get("guven"))
        conf = KONVANSIYON["gorsel_tavan"] if conf is None else \
            _clamp(conf, 0.0, KONVANSIYON["gorsel_tavan"])
        kanit = (f"Görsel okuma ({g.get('zaman_dilimi', '?')}): trend={trend}, "
                 f"yapı={g.get('yapi_olayi', YOK)}, seviyeler={g.get('seviyeler', YOK)}. "
                 f"{g.get('not', '')}".strip())
        danismanlar.append({"name": "gorsel-teyit", "stance": stance,
                            "confidence": round(conf, 4), "evidence": kanit,
                            "_kaynak": "ELLE GÖRSEL OKUMA (ölçüm değil)"})
        notlar.append(f"gorsel-teyit güveni {KONVANSIYON['gorsel_tavan']} tavanıyla "
                      "sınırlandı: elle okuma mekanik ölçümle eş tutulmaz")

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


def k4_agi(job: dict, k1: dict, k2: dict, k3: dict) -> dict:
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

    celiskiler = []          # tek liste: görsel teyit + zorunlu eksik + matris

    # --- GÖRSEL ↔ MEKANİK karşılıklı teyit (kullanıcı sözleşmesi) ----------
    # Elle görsel okuma, mekanik smc_tespit ile UYUŞUYORSA doğrulanır; aksi
    # halde çürütülür. İki bağımsız yol aynı yapıyı görüyorsa güven artar;
    # görmüyorsa bu bir UYARIDIR, gizlenmez.
    gor = (k1.get("zorunlu_girdiler") or {}).get("gorsel")
    if isinstance(gor, dict) and any(d["name"] == "gorsel-teyit" for d in k3["danismanlar"]):
        smc_trend = str((m.get("smc_tespit") or {}).get("trend", "")).lower()
        gor_trend = str(gor.get("trend", "")).lower()
        uyum = (smc_trend == gor_trend) and smc_trend in ("bull", "bear")
        verifier["gorsel-teyit"] = {
            "confirmed": bool(uyum),
            "reason": (f"mekanik smc_tespit trend={smc_trend or YOK} vs görsel "
                       f"okuma trend={gor_trend or YOK} — "
                       f"{'UYUMLU' if uyum else 'UYUMSUZ'}")}
        gerekce["gorsel-teyit"] = verifier["gorsel-teyit"]["reason"]
        if not uyum:
            celiskiler.append(f"GÖRSEL-MEKANİK ÇELİŞKİSİ: göz {gor_trend or YOK} "
                              f"diyor, algoritma {smc_trend or YOK} diyor — "
                              "biri yanılıyor; karar bu belirsizlikle veriliyor.")

    # --- KORELASYON RİSKİ: ikinci pozisyon gizli kaldıraç mı? -------------
    kor = m.get("korelasyon")
    if isinstance(kor, dict) and _num(kor.get("korelasyon")) is not None:
        rho, hk = _num(kor["korelasyon"]), str(kor.get("HUKUM", YOK))
        carp = _num(kor.get("toplam_risk_carpani")) or 1.0
        if carp > 1.0:
            celiskiler.append(
                f"KORELASYON RİSKİ: {kor.get('cift', YOK)} ρ={rho} → {hk}; aynı yönde "
                f"ikinci pozisyon bağımsız bahis DEĞİL, toplam risk ×{carp} sayılmalı.")
        else:
            celiskiler.append(f"Korelasyon ölçüldü: ρ={rho} → {hk} (risk ×{carp}).")

    # --- ZORUNLU GİRDİ EKSİKLERİ (sessizce atlanamaz) ---------------------
    for e in (k1.get("zorunlu_eksik") or []):
        celiskiler.append(f"ZORUNLU GİRDİ EKSİK — {e}")

    # --- çelişki matrisi ----------------------------------------------------
    stances = {d["name"]: d["stance"] for d in k3["danismanlar"]}
    yonler = {s for s in stances.values() if s != "flat"}
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
    # --- KARAR KAPILARI: her koşuda VERİDEN türetilir (sabit eşik yok) ------
    # Eşikler eskiden tasarım varsayımıydı (0.15/0.55/0.60). Artık esik_kalibre
    # motoru bu koşunun kurulundan (bootstrap gürültü tabanı) ve bu koşunun
    # kline'ından (rejim sertliği) türetir; türetemezse statik korkuluğa düşer
    # ve bunu AÇIKÇA etiketler. Job elle eşik verirse o üstün gelir (elle
    # müdahale gizlenmez, kaynağı yazılır).
    esik = _kos(MOTOR["esik_kalibre"], [], girdi_job={
        "advisors": sentez_job["advisors"], "verifier": sentez_job["verifier"],
        "m15": str(_yol((job.get("veri") or {}).get("m15"), taban) or ""),
        "r_min": KONVANSIYON["r_min"],
        "ufuk_bar": job.get("esik_ufuk_bar") or KONVANSIYON["esik_ufuk_bar"]})
    esik_rapor = (esik["cikti"] if esik["ok"] and isinstance(esik["cikti"], dict)
                  else {"esikler": None, "kaynak": f"KALİBRE EDİLEMEDİ ({esik['hata']}) "
                        "→ sentez kendi statik korkuluğunu kullanır"})
    if esik_rapor.get("esikler"):
        sentez_job["thresholds"] = dict(esik_rapor["esikler"])
        sentez_job["esik_kaynagi"] = esik_rapor.get("kaynak")
    if job.get("sentez_thresholds"):
        sentez_job["thresholds"] = job["sentez_thresholds"]
        sentez_job["esik_kaynagi"] = "job'da ELLE verildi (kalibrasyon ezildi)"
    r = _kos(MOTOR["sentez"], [], girdi_job=sentez_job)
    if not (r["ok"] and isinstance(r["cikti"], dict)):
        return {"katman": "K5-SI", "gecti": False,
                "kapi": f"K5 kapısı KAPALI: sentez motoru çalışmadı ({r['hata']})",
                "sentez": None, "kalibrasyon": None}
    sentez = r["cikti"]

    # ---------- ÇELİŞKİ TURU (adversarial ikinci koşu) ----------------------
    # Soru: kararın YÖNÜ, doğrulanmamış/çürütülmüş danışmanlara mı dayanıyor?
    # Sentez ikinci kez, YALNIZ doğrulanmış danışmanlarla koşulur. Yön
    # değişiyorsa kanıt dayanıksızdır → fail-closed NÖTR.
    celiski_turu = _celiski_turu(sentez_job, sentez)
    if celiski_turu.get("yon_dayaniksiz"):
        # YÖN GİZLENMEZ (duran kural): YON_BIAS ham skorun işareti olarak KALIR.
        # Kapanan şey KARAR ve İŞLEMDİR. İlk sürüm YON_BIAS'ı NÖTR yapıyordu;
        # bu hem "yön asla saklanmaz" sözleşmesini çiğniyor hem de skor≠0 iken
        # yön=NÖTR olduğu için gözlemcide MEMNUN_ETME ihlali doğuruyordu —
        # yani doğru çalışan fail-closed her koşuda mühür yiyordu.
        sentez = {**sentez, "KARAR": "NÖTR-BEKLE",
                  "kapi_gerekceleri": (sentez.get("kapi_gerekceleri") or [])
                  + [celiski_turu["hukum"]]}

    # ---------- işlem kalitesi: seviyeler MOTORDAN, R denetlenmiş -----------
    islem = _islem_kalitesi(k3, k4, sentez)

    # ---------- sabit-USDT hedef motoru (kullanıcı profili) ----------------
    usd = _usd_hedef(job, taban, k2, k3, sentez)

    # ---------- EMİR PLANI: karar → MARKET/LIMIT seviyeleri ----------------
    if celiski_turu.get("yon_dayaniksiz"):
        emir = {"EMIR": "EMİR YOK", "gerekce": celiski_turu["hukum"],
                "red_nedenleri": [celiski_turu["hukum"]]}
    else:
        emir = _emir_plani(job, taban, k1, sentez)

    # ---------- pozisyon boyutu (risk-yonetimi) ----------------------------
    boyut = None
    rj = job.get("risk")
    if isinstance(rj, dict) and rj:
        rjob = dict(rj)
        sev = (k3.get("seviyeler") or {}).get(rjob.pop("seviye_kaynagi", "karar-motoru"))
        boyut_kaynagi = None
        if rjob.get("op") == "position_size" and rjob.get("method") == "fixed_fractional" \
                and sev and rjob.get("entry") is None:
            rjob["entry"], rjob["stop"] = sev.get("entry"), sev.get("stop")
            boyut_kaynagi = "K3 danışman seviyeleri"
        # YEDEK KAYNAK: danışman seviye vermediyse (karar-motoru BEKLE derse
        # `seviyeler` boştur) ama emir_plani DENETİMDEN GEÇMİŞ bir emir
        # ürettiyse, boyut o emrin giriş/stopundan hesaplanır. Aksi halde risk
        # motoru beyan edilse bile DAİMA "VERİ YOK" derdi ve pozisyon boyutu
        # hiç ölçülmezdi. Uydurma yok: seviyeler emir_plani'nin rr_denetim +
        # usd_hedef kapılarından geçmiş adayından gelir.
        if rjob.get("entry") is None and isinstance(emir, dict):
            ad0 = (emir.get("adaylar") or [None])[0]
            if isinstance(ad0, dict) and ad0.get("giris") is not None \
                    and ad0.get("stop") is not None:
                rjob["entry"], rjob["stop"] = ad0["giris"], ad0["stop"]
                boyut_kaynagi = "emir_plani birincil adayı (denetimden geçmiş)"
        if rjob.get("entry") is None and rjob.get("method") == "fixed_fractional":
            boyut = {"durum": f"{YOK} — giriş/stop yok, boyut hesaplanmadı (fail-closed)"}
        else:
            rr_ = _kos(MOTOR["risk"], [], girdi_job=rjob)
            boyut = rr_["cikti"] if (rr_["ok"] and isinstance(rr_["cikti"], dict)) \
                else {"durum": "risk motoru ÇALIŞMADI", "hata": rr_["hata"]}
            if isinstance(boyut, dict) and boyut_kaynagi:
                boyut["_seviye_kaynagi"] = boyut_kaynagi
                boyut["_giris"], boyut["_stop"] = rjob["entry"], rjob["stop"]

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
            "sentez": sentez, "sentez_girdisi": sentez_job, "usd_hedef": usd,
            "esik_kalibrasyonu": esik_rapor, "celiski_turu": celiski_turu,
            "emir_plani": emir,
            "islem_kalitesi": islem, "pozisyon_boyutu": boyut, "portfoy": portfoy,
            "kalibrasyon": kal, "gecti": True,
            "kapi": "K5 kapısı GEÇİLDİ: nihai karar üretildi ve geri besleme yazıldı."}


def _celiski_turu(sentez_job: dict, sentez: dict) -> dict:
    """Adversarial ikinci sentez: yön yalnız DOĞRULANMIŞ danışmanlarla da aynı mı?

    Kullanıcı sözleşmesi: "çelişki olursa piramit yeniden analiz edecek."
    Mekanik karşılığı: aynı kurulu, çürütülmüş görüşler DIŞARIDA bırakılarak
    yeniden sentezle. Yön değişiyorsa karar doğrulanmamış kanıta yaslanmıştır
    → fail-closed NÖTR (yön gizlenmez, ama işleme çevrilmez).
    """
    ver = sentez_job.get("verifier") or {}
    tumu = sentez_job.get("advisors") or []
    dogrulanan = [a for a in tumu
                  if (ver.get(str(a.get("name")), {}) or {}).get("confirmed") is True
                  or a.get("_verifier_confirmed") is True]
    if not dogrulanan or len(dogrulanan) == len(tumu):
        return {"kostu": False,
                "hukum": ("ÇELİŞKİ TURU: gerekmedi — "
                          + ("doğrulanmış danışman yok" if not dogrulanan
                             else "tüm danışmanlar doğrulanmış")),
                "yon_dayaniksiz": False}
    r = _kos(MOTOR["sentez"], [], girdi_job={**sentez_job, "advisors": dogrulanan})
    if not (r["ok"] and isinstance(r["cikti"], dict)):
        return {"kostu": False, "hukum": f"ÇELİŞKİ TURU koşamadı ({r['hata']})",
                "yon_dayaniksiz": False}
    ikinci = r["cikti"]
    ilk_yon, ik_yon = sentez.get("YON_BIAS"), ikinci.get("YON_BIAS")
    dayaniksiz = (ilk_yon in ("LONG", "SHORT") and ik_yon != ilk_yon)
    return {
        "kostu": True, "yon_ilk": ilk_yon, "yon_dogrulanmis_kurul": ik_yon,
        "skor_ilk": sentez.get("yon_skoru"), "skor_ikinci": ikinci.get("yon_skoru"),
        "danisman_ilk": len(tumu), "danisman_dogrulanmis": len(dogrulanan),
        "yon_dayaniksiz": bool(dayaniksiz),
        "hukum": (f"ÇELİŞKİ TURU: yön DAYANIKSIZ — tüm kurul {ilk_yon}, yalnız "
                  f"doğrulanmış {len(dogrulanan)} danışmanla {ik_yon} "
                  "→ fail-closed NÖTR" if dayaniksiz else
                  f"ÇELİŞKİ TURU: yön DAYANIKLI — doğrulanmış {len(dogrulanan)} "
                  f"danışmanla da {ik_yon}"),
    }


def _emir_plani(job: dict, taban: Path, k1: dict, sentez: dict) -> dict:
    """Kararı MARKET/LIMIT emrine çevir (seviyeler ölçümden, R denetlenmiş)."""
    veri = job.get("veri") or {}
    p15, ph4 = _yol(veri.get("m15"), taban), _yol(veri.get("h4"), taban)
    if not (p15 and ph4):
        return {"EMIR": "EMİR YOK", "gerekce": f"{YOK} — m15/h4 yolu çözülemedi"}
    ej = {"sembol": job.get("sembol", YOK), "yon": sentez.get("YON_BIAS"),
          "m15": str(p15), "h4": str(ph4), "r_min": KONVANSIYON["r_min"]}
    prof = _yol(job.get("usd_profil"), taban)
    if prof:
        try:
            ej["profil"] = json.loads(prof.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    r = _kos(MOTOR["emir_plani"], [], girdi_job=ej)
    if r["ok"] and isinstance(r["cikti"], dict):
        return r["cikti"]
    return {"EMIR": "EMİR YOK", "gerekce": f"emir planı motoru çalışmadı ({r['hata']})"}


def _onceki_kosu(job: dict, taban: Path) -> dict:
    """Önceki koşunun anlık görüntüsü (varsa). Okuma dizini GERÇEK hafızadır."""
    okuma = _yol(job.get("defter_dizini"), taban) or (
        Path(str(job["defter_dizini"])) if job.get("defter_dizini")
        else (_yol(job.get("state_dir"), taban) or ENGINE / "state"))
    p = Path(okuma) / "onceki_kosu.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _anlik_goruntu(k1: dict, k2: dict, k3: dict, k5: dict, zirve: dict) -> dict:
    """Bu koşunun kıyaslanabilir özeti — BİR SONRAKİ koşu bununla karşılaştırır."""
    m = k2.get("motor_sonuclari") or {}
    smc = m.get("smc_tespit") or {}
    rej = smc.get("rejim") or {}
    tv = (m.get("turev-akis") or {}).get("rapor") or {}
    fak = {f.get("faktor"): f.get("skor") for f in (tv.get("faktorler") or [])}
    ik = k5.get("islem_kalitesi") or {}
    aday = (ik.get("adaylar") or [{}])[0] if ik.get("adaylar") else {}
    kmk = m.get("karar-motoru") or {}      # bölge alanları motorun kararından
    return {
        "sembol": zirve.get("sembol"),
        "son_bar": (k1.get("olcumler") or {}).get("m15_son_bar"),
        "son_bar_utc": (m.get("karar-motoru") or {}).get("son_bar_utc", YOK),
        "son_kapanis": _num((m.get("karar-motoru") or {}).get("karar", {}).get("giris")),
        "YON_BIAS": zirve.get("YON_BIAS"), "yon_skoru": zirve.get("yon_skoru"),
        "guven_skoru": zirve.get("guven_skoru"), "uzlasi": zirve.get("uzlasi"),
        "islem_kalitesi": zirve.get("ISLEM_KALITESI"),
        # GİRİŞ BÖLGESİ tam kaydedilir: yalnız tek `giris` yazılırsa bir sonraki
        # koşu bölgeyi kaybeder ve akıbet ölçümü "market dolum" sanıp
        # TETİKLENMEMİŞ bir işleme R yazar (2026-07-25'te yakalandı).
        "islem_seviyeleri": ({
            "giris": aday.get("entry"), "stop": aday.get("stop"),
            "hedef": aday.get("target"),
            "giris_alt": aday.get("giris_alt", (kmk.get("karar") or {}).get("giris_alt")),
            "giris_ust": aday.get("giris_ust", (kmk.get("karar") or {}).get("giris_ust")),
            "iptal": aday.get("iptal", (kmk.get("karar") or {}).get("iptal")),
            "giris_tipi": aday.get("giris_tipi", "limit"),
        } if aday else {}),
        "danismanlar": {d["name"]: d["stance"] for d in (k3.get("danismanlar") or [])},
        "surucu": {
            "trend": smc.get("trend"), "adx": _num(rej.get("adx")),
            "atr": _num(smc.get("atr")), "rejim": rej.get("durum"),
            "turev_skor": _num(tv.get("yon_skoru")),
            "turev_kapsam": _num(tv.get("kapsam")),
            "funding": fak.get("funding"), "lsr": fak.get("taker_lsr"),
            "cvd_delta": fak.get("cvd"), "oi_delta": fak.get("oi_price"),
            "liq_long": fak.get("liquidation"),
        },
    }


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


def _usd_hedef(job: dict, taban: Path, k2: dict, k3: dict, sentez: dict) -> dict:
    """Sabit-USDT profilini (ör. 3 ETH / stop -100 / hedef 135-150) boru hattına
    bağlar: seviye adayları K3'ten, ATR ve likidite 4H yapı motorundan gelir.

    Profil job'da yoksa çalışmaz — ama BEYAN edilip çalışmazsa gözlemci bunu
    EKSİK_AKTARIM olarak yakalar (sessiz atlama yok).
    """
    prof = job.get("usd_profil")
    if isinstance(prof, str):
        p = _yol(prof, taban)
        if p is None:
            return {"durum": f"{YOK} — usd_profil dosyası bulunamadı: {prof}"}
        try:
            prof = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return {"durum": f"profil okunamadı ({type(e).__name__})"}
    if not isinstance(prof, dict) or not prof:
        return {"durum": f"{YOK} — usd_profil beyan edilmedi (motor koşmadı)"}

    m = k2["motor_sonuclari"]
    h4 = m.get("smc_tespit_h4") or {}
    atr = _num(h4.get("atr"))
    if atr is None:
        return {"durum": f"{YOK} — 4H ATR yok (kurulum ölçeği belirlenemedi)"}
    # Referans fiyat = GÜNCEL kapanış (nominal/kaldıraç bunun üzerinden).
    # Giriş adayları ayrıca motorlardan gelir; market girişi de daima adaydır.
    p15 = _yol((job.get("veri") or {}).get("m15"), taban)
    fiyat = _num(_klines_to_candles(p15)[-1]["close"]) if p15 else None
    km = (m.get("karar-motoru") or {}).get("karar") or {}
    if fiyat is None:
        fiyat = _num(km.get("giris")) or _num((m.get("grafik-calisma") or {}).get("giris_orta"))
    if fiyat is None:
        return {"durum": f"{YOK} — referans fiyat okunamadı"}

    yon = str(sentez.get("YON_BIAS", "")).lower()
    if yon not in ("long", "short"):
        return {"durum": f"{YOK} — YON_BIAS long/short değil ({yon})"}

    lik = [_num(x.get("price")) for x in (h4.get("likidite") or [])]
    lik = [x for x in lik if x is not None]
    hedefler = sorted([x for x in lik if x < fiyat], reverse=True)[:6] if yon == "short" \
        else sorted([x for x in lik if x > fiyat])[:6]
    karsi = sorted([x for x in lik if x > fiyat])[:6] if yon == "short" \
        else sorted([x for x in lik if x < fiyat], reverse=True)[:6]

    adaylar = [fiyat]                      # market girişi daima aday
    for sv in (k3.get("seviyeler") or {}).values():
        v = _num(sv.get("entry"))
        if v is not None:
            adaylar.append(v)
    gc_orta = _num((m.get("grafik-calisma") or {}).get("giris_orta"))
    if gc_orta is not None:
        adaylar.append(gc_orta)             # confluence bölgesi de aday
    ujob = {**{k: v for k, v in prof.items() if not str(k).startswith("_")},
            "yon": yon, "fiyat": fiyat, "atr_kurulum": atr,
            "giris_adaylari": sorted(set(adaylar)),
            "likidite_hedefleri": hedefler, "karsi_yapi_seviyeleri": karsi}
    r = _kos(MOTOR["usd_hedef"], [], girdi_job=ujob)
    if r["ok"] and isinstance(r["cikti"], dict):
        return {**r["cikti"], "_girdi_kaynagi": {
            "atr_kurulum": "smc_tespit_h4.atr (4H — kurulum ölçeği)",
            "fiyat": "karar-motoru.giris / confluence / son kapanış",
            "likidite": f"smc_tespit_h4.likidite ({len(lik)} seviye)"}}
    return {"durum": "usd_hedef motoru ÇALIŞMADI", "hata": r["hata"]}


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
    # Henüz var olmayan dosya için _yol None döner; göreli yol CWD'ye DEĞİL
    # depo köküne çözülür (alt-süreçler script dizininde koştuğu için aksi
    # halde arşiv yanlış klasöre düşer — gerçek koşuda yakalandı).
    ham_arsiv = job.get("bar_arsivi")
    if ham_arsiv:
        q = Path(str(ham_arsiv)).expanduser()
        arsiv = q if q.is_absolute() else (REPO / q)
    else:
        arsiv = Path(str(sdir)) / "bar_arsivi.jsonl"
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
    # Defter OKUMA dizini yazma dizininden AYRIDIR: kum havuzu koşusunda
    # (motor bu barı zaten işlemiş) yeni karar sahte akıbetle deftere yazılmaz,
    # ama GEÇMİŞ sicil yine GERÇEK defterden okunur. Aksi halde kum havuzu
    # koşusu öğrenilmiş ağırlıkları siler ve sistem hafızasını kaybeder.
    okuma = _okuma_dizini(job, taban, k2)
    if "karar-motoru" not in defterler:
        defterler["karar-motoru"] = str(okuma / "defter.jsonl")
    # Danışman defterleri (defter_<motor>.jsonl) otomatik dahil edilir →
    # her motor KENDİ siciliyle kalibre olur (ağırlık asimetrisi kapanır).
    kok = okuma
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
    # Ağırlık dosyası SİCİLE göre ad alanlıdır: ikinci sembolün koşusu ana
    # sembolün öğrenilmiş ağırlığını EZEMEZ (çapraz-sembol hafıza çarpışması).
    hafiza_p = _hafiza_yolu(okuma)
    kayit["sicil_dizini"] = str(okuma)
    kayit["hafiza_dosyasi"] = str(hafiza_p)
    hafiza_p.parent.mkdir(parents=True, exist_ok=True)
    hafiza_p.write_text(json.dumps(kayit, ensure_ascii=False, indent=2),
                        encoding="utf-8")
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

    # Gözlemci "beyan edilip koşmayan motor" denetimi yapabilsin diye job'un
    # beyan alanları rapora taşınır (tam job DEĞİL — yalnız beyanlar).
    rapor["_job"] = {k: job.get(k) for k in
                     ("korelasyon", "usd_profil", "backtest", "risk", "portfoy")
                     if job.get(k)}

    k1 = k1_llm(job, taban)
    rapor["katmanlar"].append(k1)
    if not k1["gecti"]:
        return _durdur(rapor, "K1-LLM", k1["kapi"])

    k2 = k2_ajan(job, taban, k1)
    rapor["katmanlar"].append(k2)
    if not k2["gecti"]:
        return _durdur(rapor, "K2-AI-AJAN", k2["kapi"])

    # K3 OKUMA ile K5 YAZMA aynı ad alanını kullanır (aynı sicil → aynı dosya).
    hafiza_p = _hafiza_yolu(_okuma_dizini(job, taban, k2))
    rapor["hafiza_dosyasi"] = str(hafiza_p)
    k3 = k3_coklu(k1, k2, hafiza_p)
    rapor["katmanlar"].append(k3)
    if not k3["gecti"]:
        return _durdur(rapor, "K3-COKLU-AJAN", k3["kapi"])

    k4 = k4_agi(job, k1, k2, k3)
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
        "ZORUNLU_EKSIK": k1.get("zorunlu_eksik") or [],
        "zorunlu_girdiler": list((k1.get("zorunlu_girdiler") or {}).keys()),
        "EMIR": (k5.get("emir_plani") or {}).get("EMIR", YOK),
        "EMIR_GEREKCE": (k5.get("emir_plani") or {}).get("gerekce", ""),
        "emir_adaylari": (k5.get("emir_plani") or {}).get("adaylar") or [],
        "emir_red_nedenleri": (k5.get("emir_plani") or {}).get("red_nedenleri") or [],
        "CELISKI_TURU": (k5.get("celiski_turu") or {}).get("hukum", YOK),
        "iki_satir": {
            "1_YON": f"YÖN (bias): {s.get('YON_BIAS')} — ağırlıklı yön skoru "
                     f"{s.get('yon_skoru')}, uzlaşı {s.get('uzlasi')} "
                     "(kapıdan bağımsız; BEKLE yön reddi değildir)",
            "2_ISLEM_KALITESI": f"İŞLEM KALİTESİ: {ik['ozet']}",
        },
    }
    # --- KIYAS: eski veri neyi gösteriyordu, yeni veri neyi gösteriyor? ---
    onceki = _onceki_kosu(job, taban)
    yeni_gor = _anlik_goruntu(k1, k2, k3, k5, rapor["ZIRVE"])
    yeni_gor["sembol"] = job.get("sembol", YOK)
    try:
        if str(_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS))
        import kiyas as KY  # noqa: PLC0415
        kiyas = KY.kiyasla(onceki, yeni_gor)
    except Exception as e:  # noqa: BLE001
        kiyas = {"durum": f"kıyas HATASI ({type(e).__name__}: {e})"}
    rapor["KIYAS"] = kiyas
    rapor["ZIRVE"]["ONCEKI_AKIBET"] = k1.get("onceki_karar_akibeti")
    rapor["ZIRVE"]["KIYAS"] = {
        "yon": kiyas.get("YON_DEGISIMI"), "fiyat": kiyas.get("fiyat"),
        "onemli_degisimler": kiyas.get("onemli_degisimler"),
        "danisman_donusleri": kiyas.get("danisman_donusleri")}
    # anlık görüntüyü YAZ (bir sonraki koşu bununla kıyaslayacak)
    try:
        sdir = Path(str(_yol(job.get("state_dir"), taban)
                        or job.get("state_dir") or (ENGINE / "state")))
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "onceki_kosu.json").write_text(
            json.dumps(yeni_gor, ensure_ascii=False, indent=2), encoding="utf-8")
        rapor["ZIRVE"]["_anlik_goruntu"] = str(sdir / "onceki_kosu.json")
    except OSError as e:
        rapor["ZIRVE"]["_anlik_goruntu"] = f"YAZILAMADI ({e})"

    # --- GÖZLEMCİ AJANLAR: her katmanın çalışması artefaktla denetlenir ---
    denetim = GZ.denetle(rapor)
    rapor["DENETIM"] = denetim
    rapor["ZIRVE"]["DENETIM"] = {
        "ozet": denetim["ozet"], "ihlal": denetim["ihlal"],
        "uyari": denetim["uyari"], "muhurlendi": denetim["muhurlendi"]}
    if denetim["muhurlendi"]:
        # Kritik ihlal: YÖN gösterilir (kanıt yönü gizlenmez) ama işlem MÜHÜRLÜ.
        rapor["ZIRVE"]["ISLEM_KALITESI"] = "DENETİM İHLALİ — İŞLEM YOK (mühürlendi)"
        # Mühür varken EMİR de kapanır: kullanıcı mühürlü koşuda uygulanabilir
        # seviye görmemeli (adversarial denetim: mühürlü ETH koşusunda R 2.55'lik
        # emir hâlâ basılıyordu).
        rapor["ZIRVE"]["EMIR"] = "EMİR YOK — DENETİM MÜHÜRÜ"
        rapor["ZIRVE"]["EMIR_GEREKCE"] = ("gözlemci kritik ihlali: "
                                          + " | ".join(denetim["kritik_ihlal"])[:200])
        rapor["ZIRVE"]["emir_adaylari"] = []
        rapor["ZIRVE"]["iki_satir"]["2_ISLEM_KALITESI"] = (
            "İŞLEM KALİTESİ: DENETİM İHLALİ — işlem yok. Gözlemci bulguları: "
            + " | ".join(denetim["kritik_ihlal"]))
    rapor["durum"] = ("TAMAM — piramidin tepesine ulaşıldı"
                      + (" (DENETİM MÜHÜRÜ)" if denetim["muhurlendi"] else ""))
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
    ak = z.get("ONCEKI_AKIBET") or {}
    ky = (z.get("KIYAS") or {}).get("yon") or {}
    if ak or ky:
        L.append("① ÖNCEKİ KARARIN AKIBETİ (hesap verme):")
        if ak.get("durum") == "ÖLÇÜLDÜ":
            sv = ak.get("verilen_seviyeler") or {}
            L.append(f"   {ak.get('onceki_yon')} — verilen: giriş {sv.get('giris')}, "
                     f"stop {sv.get('stop')}, hedef {sv.get('hedef')}")
            L.append(f"   SONUÇ: {ak.get('sonuc')} | gerçekleşen R = {ak.get('gercek_r')}")
        else:
            L.append(f"   {ak.get('durum', YOK)}")
        if ky:
            L.append("② KIYAS (eski veri → yeni veri):")
            L.append(f"   {ky.get('etiket')} — {ky.get('aciklama')} "
                     f"(skor {ky.get('skor_onceki')} → {ky.get('skor_yeni')})")
            fy = (z.get("KIYAS") or {}).get("fiyat")
            if isinstance(fy, dict):
                L.append(f"   fiyat {fy.get('onceki')} → {fy.get('yeni')} "
                         f"({fy.get('yuzde'):+g}%)")
            for d in ((z.get("KIYAS") or {}).get("onemli_degisimler") or [])[:4]:
                L.append(f"   • {d}")
            for d in ((z.get("KIYAS") or {}).get("danisman_donusleri") or [])[:3]:
                L.append(f"   ↻ {d}")
        L.append("-" * 68)
    if z.get("ZORUNLU_EKSIK"):
        L.append("⚠ ZORUNLU GİRDİ EKSİK (sözleşme gereği her koşuda gelmeli):")
        for e in z["ZORUNLU_EKSIK"]:
            L.append(f"   ✖ {e}")
        L.append("-" * 68)
    if "iki_satir" in z:
        L.append(z["iki_satir"]["1_YON"])
        L.append(z["iki_satir"]["2_ISLEM_KALITESI"])
        L.append(f"EMİR: {z.get('EMIR', YOK)}")
        for a in (z.get("emir_adaylari") or [])[1:4]:
            L.append(f"   ↳ alternatif: {a['emir_tipi']} {a['yon']} @{a['giris']} | "
                     f"stop {a['stop']} | T1 {a['hedef']} | R {a['R']}")
        if str(z.get("EMIR", "")).startswith("EMİR YOK"):
            # Gerekçe HER KOLDA basılır: "yön nötr", "yapı okunamadı", "yol
            # çözülemedi", "motor çalışmadı" kollarında red_nedenleri boştur ve
            # kullanıcıya çıplak "EMİR YOK" gidiyordu (adversarial denetim).
            nedenler = (z.get("emir_red_nedenleri")
                        or ([z["EMIR_GEREKCE"]] if z.get("EMIR_GEREKCE")
                            else [f"{YOK} — gerekçe motordan taşınmadı (korkuluk)"]))
            for x in nedenler[:3]:
                L.append(f"   ✖ {x[:104]}")
        L.append(f"GEÇERSİZLİK: {z.get('gecersizlik', YOK)}")
        L.append(z.get("CELISKI_TURU", YOK))
    else:
        L.append(f"ULAŞILAN KATMAN: {z.get('ulasilan_katman', YOK)}")
        L.append(f"NEDEN: {z.get('neden', YOK)}")
    d = (rapor.get("DENETIM") or {})
    if d:
        L.append("-" * 68)
        L.append(f"GÖZLEMCİ DENETİMİ: {d.get('ozet', YOK)}"
                 + ("  ⛔ MÜHÜRLÜ" if d.get("muhurlendi") else "  ✔ temiz"))
        for x in (d.get("ihlal") or [])[:4]:
            L.append(f"   ⛔ {x[:110]}")
        for x in (d.get("uyari") or [])[:4]:
            L.append(f"   ⚠ {x[:110]}")
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
