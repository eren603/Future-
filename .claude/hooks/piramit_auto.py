#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UserPromptSubmit kancası — piramit sistemini TETİKLEYİCİSİZ devreye alır.

Her kullanıcı isteminde çalışır (kullanıcı hiçbir `/komut` yazmaz):

1. Duran kuralı bağlama enjekte eder: piyasa analizi/kararı için VARSAYILAN yol
   `piramit-sistem` boru hattıdır (elle motor zincirleme değil).
2. `engine/girdi/` verisinin parmak izini alır:
   - veri DEĞİŞMİŞSE  → boru hattını koşar, iki-satır özetini enjekte eder.
   - veri AYNIYSA     → son koşunun özetini taşır (gereksiz koşu yok, motor
                        hafızası her istemde kirlenmez).
3. Herhangi bir hata olursa TEK satır tanı basar ve sessizce çekilir.

Sözleşme: bu kanca karar ÜRETMEZ, yalnız motorun ürettiğini bağlama taşır.
Uydurma yok — özet doğrudan `piramit.py` çıktısındandır. Çıkış kodu DAİMA 0;
kanca istemi asla bloklamaz.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get("CLAUDE_PROJECT_DIR")
            or Path(__file__).resolve().parents[2])
SKILL = REPO / ".claude" / "skills" / "piramit-sistem"
PIRAMIT = SKILL / "scripts" / "piramit.py"
GIRDI = REPO / "engine" / "girdi"
DURUM = SKILL / "state" / "otomatik.json"
GOREV = REPO / "engine" / "gorev.json"          # duran görev (yeni pencere okur)
PAKET_DEFTER = SKILL / "state" / "alinan_paketler.json"
ZAMAN_ASIMI = 240          # saniye — boru hattı ölçülen koşuda ~1.6 s
MAX_OZET = 4000            # enjekte edilen özet için üst sınır (bağlam korunur)

# Kullanıcının GÖNDERDİĞİ paket depoya kendiliğinden girmeliydi; girmiyordu —
# yüklenen dosyalar oturuma özel dizinde durur, kanca oraya BAKMIYORDU. Sonuç:
# yeni pencerede "veri gönderdim ama hiçbir şey olmadı" (2026-07-25).
PAKET_DIZINLERI = [
    Path.home() / ".claude" / "uploads",        # yüklenen dosyalar (oturum altdizinleri)
    Path("/root/.claude/uploads"),
    REPO / "gelen",
    Path.home() / "Downloads",
    REPO,
]
PAKET_KALIP = "*piramit_veri_*.json"

# İKİNCİ SEMBOL: veri varsa kendiliğinden koşar (elle koşu artık gerekmiyor).
IKINCI = {
    "ad": "ETH", "girdi": GIRDI / "eth",
    "state": REPO / "engine" / "state" / "eth",
    "profil": GIRDI / "eth_profil.json",
}

KURAL = (
    "[PİRAMİT — duran kural, tetikleyicisiz] Piyasa analizi/kararı üretilecekse "
    "motorlar ELLE zincirlenmez: `.claude/skills/piramit-sistem/scripts/piramit.py` "
    "boru hattı koşulur (K1 LLM → K2 AI AJAN → K3 ÇOKLU-AJAN → K4 AGI → K5 SI). "
    "Çıktı iki satırdır: YÖN (bias) + İŞLEM KALİTESİ. Boru hattı bir katman "
    "kapısında durursa durduğu katman ve gerekçesi GİZLENMEZ; eksik veriyle karar "
    "uydurulmaz. Boru hattı koşamıyorsa elle koşuya düşülür ve bu açıkça söylenir."
)


# Otomatik yolda okunan OPSİYONEL kanallar: dosya varsa ilgili motor boru
# hattına KENDİLİĞİNDEN girer, yoksa fail-closed atlanır (uydurma girdi yok).
EK_KANAL = {
    "turev.json": ("veri", "turev"),        # turev-akis (kline-körlüğü panzehiri)
    "ohlcv.csv": ("veri", "ohlcv_csv"),     # tablo kaynağı (data-analysis + SMC)
    "risk.json": (None, "risk"),            # risk-yonetimi (pozisyon boyutu)
    "backtest.json": (None, "backtest"),    # backtest-motoru
    "portfoy.json": (None, "portfoy"),      # portfoy-optimizasyonu
    "video.mp4": ("veri", "video"),         # video-isleme (kare çıkarma)
    "veri_sozlesmesi.json": ("veri", "veri_sozlesmesi"),  # verify_data
}


def _fp() -> str | None:
    """Girdi verisinin parmak izi (ek kanallar + ikinci sembol dahil).

    İkinci sembolün verisi de parmak izine girer: yalnız ETH tazelenmişse de
    boru hattı yeniden koşmalı (yoksa ETH sessizce eski barla kalırdı).
    """
    h = hashlib.sha256()
    var = False
    for ad in ("m15.json", "h4.json", *EK_KANAL):
        p = GIRDI / ad
        if p.exists():
            h.update(ad.encode())
            h.update(p.read_bytes())
            var = var or ad in ("m15.json", "h4.json")
        else:
            h.update(b"YOK")
    for ad in ("m15.json", "h4.json", "turev.json"):
        p = IKINCI["girdi"] / ad
        h.update(p.read_bytes() if p.exists() else b"YOK")
    return h.hexdigest() if var else None


# --------------------------------------------------------------------------
# GÖNDERİLEN PAKETİ DEPOYA AL (kullanıcı elle komut yazmaz)
# --------------------------------------------------------------------------
def _paket_adaylari() -> list:
    """Gönderilmiş veri paketlerini bul (yeni → eski)."""
    bulunan = {}
    for d in PAKET_DIZINLERI:
        try:
            if not d.is_dir():
                continue
            # yükleme kökü oturum altdizinlidir; depo kökü düz taranır (ucuz)
            adaylar = list(d.glob(PAKET_KALIP)) + list(d.glob("*/" + PAKET_KALIP))
            for p in adaylar:
                if p.is_file():
                    bulunan[p.resolve()] = p.stat().st_mtime
        except OSError:
            continue
    return [p for p, _ in sorted(bulunan.items(), key=lambda kv: -kv[1])]


def _son_bar_ms(kline) -> float | None:
    try:
        son = kline[-1]
        return float(son[0] if isinstance(son, list) else
                     (son.get("open_time") or son.get("t")))
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def _paket_zamani(p: Path) -> tuple:
    """(paketin son bar zamanı ms, paket sözlüğü) — okunamazsa (None, None)."""
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    aday = []
    for kok in ([d] + list((d.get("semboller") or {}).values())
                if isinstance(d.get("semboller"), dict) else [d]):
        for anahtar in ("m15", "klines_15m", "kline_15m"):
            v = (kok.get("veri") or kok).get(anahtar) if isinstance(kok, dict) else None
            t = _son_bar_ms(v) if isinstance(v, list) else None
            if t:
                aday.append(t)
    return (max(aday) if aday else None), d


def _girdi_son_bar() -> float | None:
    try:
        return _son_bar_ms(json.loads((GIRDI / "m15.json").read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return None


def _paket_al() -> dict:
    """En yeni İŞLENMEMİŞ paketi depoya aç (paket_ac.py doğrulamasıyla).

    İki korkuluk:
      - Defter içerik SHA'sı üzerinden tutulur: aynı dosya yeniden yüklense
        bile ikinci kez açılmaz.
      - Paketin verisi depodakinden YENİ DEĞİLSE alınmaz. Bu olmadan eski bir
        paket yeni veriyi geri sarıyordu (BTC 22:04 → 19:35 geri gitti,
        ETH 22:00'de kaldı = sembolleri ayrışmış sahte kıyas). 2026-07-25.
    """
    acici = SKILL / "scripts" / "paket_ac.py"
    if not acici.exists():
        return {}
    try:
        defter = json.loads(PAKET_DEFTER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        defter = {}
    islenen = set(defter.get("islenen") or [])
    mevcut = _girdi_son_bar()
    for p in _paket_adaylari():
        try:
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            continue
        if sha in islenen:
            continue
        paket_ms, _ = _paket_zamani(p)
        if mevcut is not None and paket_ms is not None and paket_ms <= mevcut:
            islenen.add(sha)                    # bir daha bakma
            _defter_yaz(islenen, p, sha)
            return {"paket": p.name, "atlandi": (
                "paketin verisi depodakinden yeni DEĞİL "
                f"(paket son bar {int(paket_ms)} ≤ depo {int(mevcut)}) → "
                "veri geri sarılmadı")}
        try:
            pr = subprocess.run([sys.executable, str(acici), "--paket", str(p)],
                                capture_output=True, text=True, timeout=120,
                                cwd=str(REPO))
            sonuc = json.loads(pr.stdout) if pr.stdout.strip().startswith("{") else {}
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            return {"paket": p.name, "hata": f"{type(e).__name__}: {e}"}
        islenen.add(sha)
        _defter_yaz(islenen, p, sha)
        return {"paket": p.name, "sonuc": sonuc, "yol": str(p)}
    return {}


def _defter_yaz(islenen: set, p: Path, sha: str) -> None:
    try:
        PAKET_DEFTER.parent.mkdir(parents=True, exist_ok=True)
        PAKET_DEFTER.write_text(json.dumps(
            {"islenen": sorted(islenen), "son": {"dosya": str(p), "sha": sha}},
            ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


GORSEL_UZANTI = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm")


def _okunmamis_gorseller() -> list:
    """Gönderilmiş ama HENÜZ OKUNMAMIŞ görsel/video dosyaları.

    Kanca görüntü OKUYAMAZ (bu elle yapılır). Yapabileceği: yeni gelen
    görseli görünür kılmak. Ölçüt tazelik damgasıdır — `gorsel_okuma.json`
    damgasından SONRA gelen dosya henüz okunmamış sayılır. Böylece "görsel
    gönderdim ama kimse bakmadı" sessizliği kalkar.
    """
    damga = 0.0
    gp = GIRDI / "gorsel_okuma.json"
    if gp.exists():
        try:
            damga = gp.stat().st_mtime
        except OSError:
            damga = 0.0
    yeni = []
    for d in PAKET_DIZINLERI:
        try:
            if not d.is_dir():
                continue
            for p in list(d.glob("*")) + list(d.glob("*/*")):
                if (p.is_file() and p.suffix.lower() in GORSEL_UZANTI
                        and p.stat().st_mtime > damga):
                    yeni.append(p)
        except OSError:
            continue
    return sorted(set(yeni), key=lambda p: -p.stat().st_mtime)[:12]


def _gorev_bas() -> None:
    """Duran görevi bağlama bas — yeni pencere görevi/hedefi tekrar sormaz."""
    try:
        g = json.loads(GOREV.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    prof = g.get("eth_profili", {})
    print("[PİRAMİT — DURAN GÖREV] " + g.get("gorev", ""))
    print("   sıra: " + " ".join(g.get("sira", [])))
    if prof:
        print(f"   ETH profili: {prof.get('kontrat_eth')} ETH kontrat, "
              f"sermaye {prof.get('sermaye_usd')} USD, kaldıraç {prof.get('kaldirac')}x, "
              f"stop {prof.get('stop_usdt')} USDT (sabit), hedef "
              f"{prof.get('hedef_usdt_brut')} USDT brüt, R_min {prof.get('r_min')}, "
              f"kurulum ölçeği {prof.get('kurulum_olcegi')}")
    print(f"   hafıza: {', '.join(f'{k}={v}' for k, v in (g.get('hafiza') or {}).items())}")


def _ek_kanallar(job: dict) -> list:
    """engine/girdi altındaki opsiyonel dosyaları job'a bağla; hangileri girdi?"""
    giren = []
    for ad, (bolum, anahtar) in EK_KANAL.items():
        p = GIRDI / ad
        if not p.exists():
            continue
        try:
            deger = (json.loads(p.read_text(encoding="utf-8"))
                     if p.suffix == ".json" else str(p))
        except (OSError, json.JSONDecodeError) as e:
            giren.append(f"{ad}: OKUNAMADI ({type(e).__name__}) — atlandı")
            continue
        if bolum == "veri":
            job["veri"][anahtar] = deger
        else:
            job[anahtar] = deger
        giren.append(ad)
    return giren


def _turev_uret(onceki: dict, girdi: Path | None = None,
                seri: Path | None = None) -> dict:
    """Türev girdisini KENDİLİĞİNDEN üret (kline körlüğü panzehiri).

    CVD kullanıcının kendi kline'ından çevrimdışı hesaplanır — panel
    beklenmez. OI anlık görüntü defterinden, funding/LSR ağ izin verirse
    Binance vadeli genel uçlarından gelir. Ağ bir kez engellenirse bu oturum
    boyunca yeniden denenmez (her istemde boşuna beklenmesin).
    """
    girdi = girdi or GIRDI
    seri = seri or (REPO / "engine" / "state" / "turev_seri.jsonl")
    uretec = SKILL / "scripts" / "turev_girdi.py"
    m15 = girdi / "m15.json"
    if not (uretec.exists() and m15.exists()):
        return {"durum": "üreteç ya da m15 yok — türev girdisi üretilmedi"}
    argv = [sys.executable, str(uretec), "--m15", str(m15),
            "--seri", str(seri),
            "--ham", str(girdi / "turev_ham"),
            "--out", str(girdi / "turev.json")]
    if not onceki.get("http_engelli"):
        argv.append("--http")
    try:
        pr = subprocess.run(argv, capture_output=True, text=True, timeout=60,
                            cwd=str(REPO))
        job = json.loads(pr.stdout) if pr.stdout.strip().startswith("{") else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        return {"durum": f"türev üreteci çalışmadı ({type(e).__name__})"}
    return {"kaynaklar": job.get("_kaynaklar", {}), "eksikler": job.get("_eksikler", []),
            "http_engelli": bool(job.get("_ag_hatalari"))}


def _durum_oku() -> dict:
    try:
        return json.loads(DURUM.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _zaten_islendi(girdi: Path | None = None, state: Path | None = None) -> bool:
    """Motor bu barı zaten işledi mi? (durum.json son_bar == verinin son barı)

    Neden gerekli: aynı veriyle ikinci koşu, motorun takip ettiği açık kararı
    "DEVRİLDİ" diye deftere yazar — bu SAHTE bir akıbettir (karar değişmedi,
    yalnız koşu tekrarlandı). Böyle bir durumda boru hattı KUM HAVUZUNA yazar;
    karar aynı çıkar (motor kararı geçmişten bağımsızdır — engine/karar_motoru:
    "önceki YÖN yeni karara ağırlık olarak GİRMEZ"), gerçek hafıza kirlenmez.
    """
    girdi = girdi or GIRDI
    state = state or (REPO / "engine" / "state")
    try:
        d = json.loads((state / "durum.json").read_text(encoding="utf-8"))
        m = json.loads((girdi / "m15.json").read_text(encoding="utf-8"))
        son = m[-1][0] if isinstance(m[-1], list) else (
            m[-1].get("open_time") or m[-1].get("t"))
        return d.get("son_bar") == son
    except (OSError, json.JSONDecodeError, IndexError, KeyError, TypeError):
        return False


def _kos() -> tuple[str, int]:
    """Boru hattını koştur; (özet metni, çıkış kodu)."""
    kum = _zaten_islendi()
    sdir = (SKILL / "state" / "kum_havuzu") if kum else (REPO / "engine" / "state")
    if kum:
        sdir.mkdir(parents=True, exist_ok=True)
    job = {
        "soru": "otomatik koşu — engine/girdi verisi değişti",
        "sembol": "engine/girdi",
        "veri": {"m15": str(GIRDI / "m15.json"), "h4": str(GIRDI / "h4.json")},
        "state_dir": str(sdir),
        # Bar arşivi fiyat GERÇEĞİdir (karar hafızası değil) — kum havuzu
        # koşusunda bile gerçek arşive yazılır ki kayan pencere telafi edilsin.
        "bar_arsivi": str(REPO / "engine" / "state" / "bar_arsivi.jsonl"),
        # Sicil OKUMA dizini daima GERÇEK hafızadır: kum havuzu koşusu yeni
        # kararı sahte akıbetle yazmaz ama geçmiş sicili okur ve etiketler —
        # yoksa öğrenilmiş ağırlıklar her kum havuzu koşusunda silinirdi.
        "defter_dizini": str(REPO / "engine" / "state"),
        "_hafiza": ("KUM HAVUZU — motor bu barı zaten işlemişti; gerçek defter "
                    "korunuyor" if kum else "GERÇEK — yeni bar, hafıza güncellenir"),
    }
    # Karşılaştırma sembolü varsa korelasyon boru hattına girer (gözlemci
    # kapsamında koşar — elle koşu artık gerekmiyor).
    eth_m15 = GIRDI / "eth" / "m15.json"
    if eth_m15.exists():
        job["korelasyon"] = {"a": str(GIRDI / "m15.json"), "b": str(eth_m15),
                             "ad_a": "BTC", "ad_b": "ETH"}
    ek = _ek_kanallar(job)
    if ek:
        print(f"[PİRAMİT] Ek kanal(lar) otomatik bağlandı: {', '.join(ek)}")
    return _job_kos(job, "otomatik_job.json", "son_rapor.json")


def _job_kos(job: dict, job_ad: str, rapor_ad: str) -> tuple[str, int]:
    jp = SKILL / "state" / "_job" / job_ad
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    pr = subprocess.run(
        [sys.executable, str(PIRAMIT), "--job", str(jp),
         "--out", str(SKILL / "state" / rapor_ad), "--ozet"],
        capture_output=True, text=True, timeout=ZAMAN_ASIMI, cwd=str(REPO))
    metin = (pr.stdout or "").strip() or (pr.stderr or "").strip()[-600:]
    return metin[:MAX_OZET], pr.returncode


def _ikinci_job() -> dict | None:
    """İkinci sembol (ETH) job'u — verisi varsa; yoksa None (uydurma yok).

    Bu adım kancada YOKTU: ETH boru hattı yalnız ELLE koşuluyordu, yeni
    pencerede hiç koşmadı. Artık ana sembolle aynı istemde kendiliğinden
    koşar; sabit-USDT profili (usd_hedef) ve korelasyon job'da BEYAN edilir —
    beyan edilip koşmazsa gözlemci EKSİK_AKTARIM ihlali verir.
    """
    g, st = IKINCI["girdi"], IKINCI["state"]
    if not ((g / "m15.json").exists() and (g / "h4.json").exists()):
        return None
    kum = _zaten_islendi(g, st)
    sdir = (SKILL / "state" / "kum_havuzu_eth") if kum else st
    sdir.mkdir(parents=True, exist_ok=True)
    st.mkdir(parents=True, exist_ok=True)
    veri = {"m15": str(g / "m15.json"), "h4": str(g / "h4.json"),
            "likidasyon": str(g / "turev_ham" / "likidasyon.json"),
            "gorsel": str(g / "gorsel_okuma.json")}
    tp = g / "turev.json"
    if tp.exists():
        try:
            veri["turev"] = json.loads(tp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    job = {
        "soru": f"otomatik koşu — {IKINCI['ad']} (ana sembolle korelasyonlu)",
        "sembol": f"engine/girdi/{IKINCI['girdi'].name}",
        "veri": veri, "state_dir": str(sdir), "defter_dizini": str(st),
        "bar_arsivi": str(st / "bar_arsivi.jsonl"),
        "korelasyon": {"a": str(GIRDI / "m15.json"), "b": str(g / "m15.json"),
                       "ad_a": "BTC", "ad_b": IKINCI["ad"]},
        "_hafiza": ("KUM HAVUZU — bu bar zaten işlenmişti" if kum
                    else "GERÇEK — yeni bar"),
    }
    if IKINCI["profil"].exists():
        job["usd_profil"] = str(IKINCI["profil"])
    return job


def main() -> int:
    print(KURAL)
    _gorev_bas()

    if not PIRAMIT.exists():
        print("[PİRAMİT] Boru hattı dosyası bulunamadı — elle koşuya düşülür.")
        return 0

    # 0) GÖNDERİLEN PAKETİ AL — elle `paket_ac` komutu beklenmez.
    alinan = _paket_al()
    if alinan:
        if alinan.get("hata"):
            print(f"[PİRAMİT] Paket açılamadı ({alinan['paket']}): {alinan['hata']}"
                  " — veri depoya GİRMEDİ, eski veriyle karar üretilmez.")
        elif alinan.get("atlandi"):
            print(f"[PİRAMİT] Paket ATLANDI ({alinan['paket']}): {alinan['atlandi']}")
        else:
            s = alinan.get("sonuc") or {}
            yaz = s.get("yazilan") or s.get("yazildi") or s
            print(f"[PİRAMİT] Gönderilen paket depoya alındı: {alinan['paket']} → "
                  f"{json.dumps(yaz, ensure_ascii=False)[:600]}")

    gorseller = _okunmamis_gorseller()
    if gorseller:
        print("[PİRAMİT] OKUNMAMIŞ GÖRSEL/VİDEO (zorunlu girdi — kanca görüntü "
              "okuyamaz, ELLE okunacak → engine/girdi/gorsel_okuma.json + "
              "turev_ham/likidasyon.json, `zaman_utc` damgasıyla):")
        for p in gorseller:
            print(f"   · {p}")

    fp = _fp()
    if fp is None:
        print("[PİRAMİT] engine/girdi/ altında m15/h4 YOK — otomatik koşu "
              "yapılmadı. Kullanıcı kline gönderirse veri oraya yazılır ve "
              "sonraki istemde boru hattı kendiliğinden koşar.")
        return 0

    onceki = _durum_oku()
    # Türev girdisi HER İSTEMDE tazelenir (CVD determinist: aynı kline = aynı
    # dosya → gereksiz koşu tetiklenmez). Parmak izi bundan SONRA alınır ki
    # yeni OI görüntüsü/funding boru hattını kendiliğinden yeniden koştursun.
    turev = _turev_uret(onceki)
    if turev.get("kaynaklar") is not None:
        onceki["http_engelli"] = turev.get("http_engelli", onceki.get("http_engelli"))
        var = ", ".join(turev["kaynaklar"]) or "yok"
        print(f"[PİRAMİT] Türev kanalı otomatik üretildi → dolu: {var} | "
              f"eksik: {len(turev.get('eksikler', []))} kanal (uydurulmadı)")
    # İkinci sembolün türevi de KENDİ kline'ından üretilir (CVD çevrimdışı).
    if (IKINCI["girdi"] / "m15.json").exists():
        _turev_uret(onceki, IKINCI["girdi"],
                    IKINCI["state"] / "turev_seri.jsonl")
    fp = _fp()
    if onceki.get("fp") == fp and onceki.get("ozet"):
        print("[PİRAMİT] Girdi verisi DEĞİŞMEDİ — yeniden koşulmadı; son koşunun "
              "sonucu (motor hafızası kirletilmedi):")
        print(onceki["ozet"])
        return 0

    try:
        ozet, kod = _kos()
    except subprocess.TimeoutExpired:
        print(f"[PİRAMİT] Boru hattı {ZAMAN_ASIMI}s içinde bitmedi — elle koşuya "
              "düşülür (bu AÇIKÇA söylenmeli).")
        return 0
    except Exception as e:  # noqa: BLE001 — kanca istemi asla bloklamaz
        print(f"[PİRAMİT] Boru hattı çalıştırılamadı ({type(e).__name__}: {e}) — "
              "elle koşuya düşülür (bu AÇIKÇA söylenmeli).")
        return 0

    hafiza = ("KUM HAVUZU (motor bu barı zaten işlemişti — gerçek defter "
              "korundu)" if _zaten_islendi() else "GERÇEK hafıza (yeni bar)")
    print(f"[PİRAMİT] Boru hattı koştu — hafıza: {hafiza} "
          f"(çıkış kodu {kod}; 0=zirve, 2=bir katman kapısında durdu):")
    print(ozet)

    # --- İKİNCİ SEMBOL: aynı istemde, aynı disiplinle (elle koşu yok) -------
    ij = _ikinci_job()
    if ij is None:
        print(f"[PİRAMİT] İkinci sembol ({IKINCI['ad']}) verisi YOK "
              f"({IKINCI['girdi']}/m15.json) — koşulmadı, uydurulmadı.")
    else:
        try:
            ozet2, kod2 = _job_kos(ij, "otomatik_job_eth.json",
                                   "son_rapor_eth.json")
            print(f"[PİRAMİT] İkinci sembol {IKINCI['ad']} koştu "
                  f"(çıkış kodu {kod2}; sabit-USDT profili "
                  f"{'BAĞLI' if ij.get('usd_profil') else 'YOK'}):")
            print(ozet2)
            ozet = f"{ozet}\n{ozet2}"
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"[PİRAMİT] İkinci sembol koşulamadı ({type(e).__name__}: {e}) "
                  "— elle koşuya düşülür (bu AÇIKÇA söylenmeli).")
    try:
        DURUM.parent.mkdir(parents=True, exist_ok=True)
        DURUM.write_text(json.dumps({"fp": fp, "ozet": ozet, "kod": kod,
                                     "http_engelli": bool(onceki.get("http_engelli"))},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001 — son emniyet: istem asla bloklanmaz
        print(f"[PİRAMİT] kanca hatası ({type(e).__name__}: {e})")
        sys.exit(0)
