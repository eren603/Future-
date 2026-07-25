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
ZAMAN_ASIMI = 240          # saniye — boru hattı ölçülen koşuda ~1.6 s
MAX_OZET = 4000            # enjekte edilen özet için üst sınır (bağlam korunur)

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
    """Girdi verisinin parmak izi (ek kanallar dahil). Dosya yoksa None."""
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
    return h.hexdigest() if var else None


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


def _turev_uret(onceki: dict) -> dict:
    """Türev girdisini KENDİLİĞİNDEN üret (kline körlüğü panzehiri).

    CVD kullanıcının kendi kline'ından çevrimdışı hesaplanır — panel
    beklenmez. OI anlık görüntü defterinden, funding/LSR ağ izin verirse
    Binance vadeli genel uçlarından gelir. Ağ bir kez engellenirse bu oturum
    boyunca yeniden denenmez (her istemde boşuna beklenmesin).
    """
    uretec = SKILL / "scripts" / "turev_girdi.py"
    m15 = GIRDI / "m15.json"
    if not (uretec.exists() and m15.exists()):
        return {"durum": "üreteç ya da m15 yok — türev girdisi üretilmedi"}
    argv = [sys.executable, str(uretec), "--m15", str(m15),
            "--seri", str(REPO / "engine" / "state" / "turev_seri.jsonl"),
            "--ham", str(GIRDI / "turev_ham"),
            "--out", str(GIRDI / "turev.json")]
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


def _zaten_islendi() -> bool:
    """Motor bu barı zaten işledi mi? (durum.json son_bar == verinin son barı)

    Neden gerekli: aynı veriyle ikinci koşu, motorun takip ettiği açık kararı
    "DEVRİLDİ" diye deftere yazar — bu SAHTE bir akıbettir (karar değişmedi,
    yalnız koşu tekrarlandı). Böyle bir durumda boru hattı KUM HAVUZUNA yazar;
    karar aynı çıkar (motor kararı geçmişten bağımsızdır — engine/karar_motoru:
    "önceki YÖN yeni karara ağırlık olarak GİRMEZ"), gerçek hafıza kirlenmez.
    """
    try:
        d = json.loads((REPO / "engine" / "state" / "durum.json")
                       .read_text(encoding="utf-8"))
        m = json.loads((GIRDI / "m15.json").read_text(encoding="utf-8"))
        son = m[-1][0] if isinstance(m[-1], list) else (
            m[-1].get("open_time") or m[-1].get("t"))
        return d.get("son_bar") == son
    except (OSError, json.JSONDecodeError, IndexError, KeyError, TypeError):
        return False


def _kos() -> tuple[str, int, bool]:
    """Boru hattını koştur; (özet metni, çıkış kodu, kum_havuzu_mu).

    `kum` KOŞUDAN ÖNCE ölçülür ve çağırana geri döner: koşu bittikten sonra
    `_zaten_islendi()` GERÇEK koşuda da True olur (motor durum.json'a yeni barı
    yazmıştır), yani sonradan sorulursa her koşu "kum havuzu" görünür ve
    kullanıcıya "gerçek defter korundu" diye YANLIŞ rapor edilirdi.
    """
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
    jp = SKILL / "state" / "_job" / "otomatik_job.json"
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    pr = subprocess.run(
        [sys.executable, str(PIRAMIT), "--job", str(jp),
         "--out", str(SKILL / "state" / "son_rapor.json"), "--ozet"],
        capture_output=True, text=True, timeout=ZAMAN_ASIMI, cwd=str(REPO))
    metin = (pr.stdout or "").strip() or (pr.stderr or "").strip()[-600:]
    return metin[:MAX_OZET], pr.returncode, kum


def main() -> int:
    print(KURAL)

    if not PIRAMIT.exists():
        print("[PİRAMİT] Boru hattı dosyası bulunamadı — elle koşuya düşülür.")
        return 0

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
    fp = _fp()
    if onceki.get("fp") == fp and onceki.get("ozet"):
        print("[PİRAMİT] Girdi verisi DEĞİŞMEDİ — yeniden koşulmadı; son koşunun "
              "sonucu (motor hafızası kirletilmedi):")
        print(onceki["ozet"])
        return 0

    try:
        ozet, kod, kum = _kos()
    except subprocess.TimeoutExpired:
        print(f"[PİRAMİT] Boru hattı {ZAMAN_ASIMI}s içinde bitmedi — elle koşuya "
              "düşülür (bu AÇIKÇA söylenmeli).")
        return 0
    except Exception as e:  # noqa: BLE001 — kanca istemi asla bloklamaz
        print(f"[PİRAMİT] Boru hattı çalıştırılamadı ({type(e).__name__}: {e}) — "
              "elle koşuya düşülür (bu AÇIKÇA söylenmeli).")
        return 0

    hafiza = ("KUM HAVUZU (motor bu barı zaten işlemişti — gerçek defter "
              "korundu)" if kum else "GERÇEK hafıza (yeni bar)")
    print(f"[PİRAMİT] Boru hattı koştu — hafıza: {hafiza} "
          f"(çıkış kodu {kod}; 0=zirve, 2=bir katman kapısında durdu):")
    print(ozet)
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
