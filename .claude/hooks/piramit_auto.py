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
import time

# KÜRESEL KANCA BÜTÇESİ (S8): tüm alt-süreç timeout'larının TOPLAMI settings.json'daki
# UserPromptSubmit tavanını (900 sn) aşabiliyordu (paket_ac 120 + türev 60×2 + boru
# hattı 240×2 + grafik 120×2 = 960 > 900). Kötü günde harness kancayı 900. sn'de
# öldürür ve DURUM/özet yazımı (en sonda) HİÇ olmaz. Her subprocess.run'a
# timeout=min(yerel, kalan_bütçe) verilir; bütçe biterse adım açıkça atlanır.
_KANCA_BASLANGIC = time.monotonic()
KANCA_BUTCE = 850          # sn — 900 tavanının altında güvenlik payıyla


def _kalan_butce() -> float:
    return max(1.0, KANCA_BUTCE - (time.monotonic() - _KANCA_BASLANGIC))


def _atomik_yaz(hedef, metin: str) -> None:
    """Atomik JSON yazımı (S6): geçici dosya + os.replace. Kanca subprocess'leri
    ya da harness kesmesi yazım ORTASINDA öldürebilir; yarım defter/durum dosyası
    bir sonraki koşuda bozuk okunup SHA/fp geçmişini sıfırlamasın."""
    from pathlib import Path as _P
    hedef = _P(hedef)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    tmp = hedef.with_suffix(hedef.suffix + ".tmp")
    tmp.write_text(metin, encoding="utf-8")
    os.replace(tmp, hedef)
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
    Path("/mnt/user-data/uploads"),             # bazı yüzeylerin yükleme kökü
    REPO / "gelen",
    Path.home() / "Downloads",
    REPO,
]
PAKET_KALIP = "*piramit_veri_*.json"

# Bu deponun tanıdığı semboller: ana slot BTCUSDT, ikinci slot ETHUSDT
# (engine/gorev.json ile aynı). Yabancı sembolün paketi ana slotu EZEMEZ.
BEKLENEN_SEMBOL = {"BTCUSDT", "ETHUSDT"}

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
    # ZORUNLU GİRDİ olan görsel okuma + elle likidasyon da parmak izine girer
    # (B4): yalnız görsel/likidasyon tazelendiğinde de boru hattı yeniden
    # koşmalı — yoksa gorsel-teyit danışmanı sessizce eski okumayla kalırdı.
    for ad in ("m15.json", "h4.json", *EK_KANAL,
               "gorsel_okuma.json", "turev_ham/likidasyon.json"):
        p = GIRDI / ad
        try:
            if p.is_file():
                h.update(ad.encode())
                h.update(p.read_bytes())
                var = var or ad in ("m15.json", "h4.json")
            else:
                h.update(b"YOK")
        except OSError:
            # dizin-adlı/okunamayan girdi kancayı ÖLDÜRMEZ (kalıcı sessizlik
            # yerine parmak izine "OKUNAMADI" girer, koşu devam eder)
            h.update(b"OKUNAMADI")
    for ad in ("m15.json", "h4.json", "turev.json",
               "gorsel_okuma.json", "turev_ham/likidasyon.json"):
        p = IKINCI["girdi"] / ad
        try:
            h.update(p.read_bytes() if p.is_file() else b"YOK")
        except OSError:
            h.update(b"OKUNAMADI")
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
            adaylar = (list(d.glob(PAKET_KALIP)) + list(d.glob("*/" + PAKET_KALIP))
                       + list(d.glob("*/*/" + PAKET_KALIP)))
            for p in adaylar:
                if p.is_file():
                    bulunan[p.resolve()] = p.stat().st_mtime
        except OSError:
            continue
    return [p for p, _ in sorted(bulunan.items(), key=lambda kv: -kv[1])]


def _son_bar_ms(kline) -> float | None:
    try:
        son = kline[-1]
        if isinstance(son, list):
            return float(son[0])
        if isinstance(son, dict):
            return float(son.get("open_time") or son.get("t"))
        return None                    # dize/sayı vb. son bar → ölçülemez (uydurma yok)
    except (IndexError, KeyError, TypeError, ValueError, AttributeError):
        return None


def _paket_zamani(p: Path) -> tuple:
    """(paketin sembol → son bar zamanı haritası, paket sözlüğü).

    v1 paket düz (`veri.m15`), v2 paket çok sembollüdür (`veri.BTCUSDT.m15`) ve
    `semboller` bir LİSTEdir. Eski sürüm yalnız `semboller` SÖZLÜK olduğunda alt
    bloklara iniyordu; v2'de hiçbir bar bulamayıp None dönüyordu ve geri-sarma
    korkuluğu SESSİZCE ÖLÜYORDU. Adversarial denetimde ölçüldü (2026-07-25):
    17 sa 45 dk eski paket depoyu geri sardı ve BTC yönü LONG → SHORT döndü.
    """
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, None
    if not isinstance(d, dict):
        return {}, None

    def _bar_of(blok) -> float | None:
        if not isinstance(blok, dict):
            return None
        for anahtar in ("m15", "klines_15m", "kline_15m"):
            v = blok.get(anahtar)
            t = _son_bar_ms(v) if isinstance(v, list) else None
            if t:
                return t
        return None

    harita: dict = {}
    veri = d.get("veri")
    ana = str(d.get("ana_sembol") or "").upper()
    if isinstance(veri, dict):
        # v2: veri.<SEMBOL>.m15 ; v1: veri.m15
        t = _bar_of(veri)
        if t:
            harita["_ANA"] = t
        for ad, blok in veri.items():
            t = _bar_of(blok)
            if t:
                harita[str(ad).upper()] = t
    if isinstance(d.get("semboller"), dict):
        for ad, blok in d["semboller"].items():
            t = _bar_of(blok)
            if t:
                harita[str(ad).upper()] = t
    if ana and ana in harita:
        harita["_ANA"] = harita[ana]
    elif "_ANA" not in harita and harita:
        harita["_ANA"] = max(harita.values())
    return harita, d


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
    redded = dict(defter.get("reddedilen") or {})   # sha → gerekçe (görünür kalır)
    # STAT ÖN-FİLTRESİ (S8): SHA için dosyanın TAMAMI okunur; kanca her istemde
    # koştuğu için taranan tüm dizinlerdeki paketler baştan sona okunuyordu.
    # (mtime, size) değişmemişse SHA'yı ön-bellekten al, read_bytes'ı ATLA.
    stat_cache = dict(defter.get("stat") or {})     # yol → [mtime, size, sha]
    for p in _paket_adaylari():
        try:
            st = p.stat()
            anahtar = str(p)
            onbellek = stat_cache.get(anahtar)
            if onbellek and onbellek[0] == st.st_mtime and onbellek[1] == st.st_size:
                sha = onbellek[2]
            else:
                sha = hashlib.sha256(p.read_bytes()).hexdigest()
                stat_cache[anahtar] = [st.st_mtime, st.st_size, sha]
        except OSError:
            continue
        if sha in islenen or sha in redded:
            continue
        harita, ham = _paket_zamani(p)
        paket_ms = harita.get("_ANA")
        # FAIL-CLOSED: paketin barı OKUNAMIYORSA alınmaz. Eskiden None "sorun
        # yok, al" diye yorumlanıyordu; biçim değişince korkuluk sessizce
        # ölüyordu (v2 paketinde tam olarak bu oldu).
        if paket_ms is None:
            redded[sha] = "son bar okunamadı (tanınmayan şema)"
            _defter_yaz(islenen, p, sha, redded)
            return {"paket": p.name, "atlandi": (
                "paketin son barı OKUNAMADI (tanınmayan şema) → ALINMADI "
                "(fail-closed: tazeliği kanıtlanamayan paket depoya girmez)")}
        # SEMBOL KİMLİĞİ: yanlış sembolün paketi ana (BTC) slotunu ezemez.
        beyan = {str(s).upper() for s in harita if s != "_ANA"}
        tek = str((ham or {}).get("sembol") or "").upper()
        if tek:
            beyan.add(tek)
        if beyan and beyan.isdisjoint(BEKLENEN_SEMBOL):
            redded[sha] = f"sembol {sorted(beyan)} ∉ beklenen {sorted(BEKLENEN_SEMBOL)}"
            _defter_yaz(islenen, p, sha, redded)
            return {"paket": p.name, "atlandi": (
                f"paket sembolleri {sorted(beyan)} bu deponun sembolleriyle "
                f"({sorted(BEKLENEN_SEMBOL)}) eşleşmiyor → ALINMADI "
                "(yanlış sembol ana slotu ezemez; fail-closed)")}
        surum = int((ham or {}).get("surum") or 1)
        if surum < 2 and tek == "ETHUSDT":
            redded[sha] = "tek-sembollü ETH paketi ana slota yazılırdı"
            _defter_yaz(islenen, p, sha, redded)
            return {"paket": p.name, "atlandi": (
                "tek-sembollü ETHUSDT paketi ana (BTC) slotunu ezerdi → ALINMADI; "
                "ETH için çift-sembollü v2 paketi gönder (veri_topla.py)")}
        # SEMBOL BAZINDA kıyas: BTC'si eski / ETH'si yeni bir paket, BTC'yi
        # geri sardırmamalı. BTCUSDT anahtarı varsa _ANA yerine o kullanılır
        # (_ANA=max(tümü) idi: yeni ETH, eski BTC'yi maskeliyordu).
        geri, taze = [], []
        # BTCUSDT satırı için _ANA vekili KALDIRILDI (B1): paket BTCUSDT'yi
        # AÇIKÇA beyan etmiyorsa BTC slotu bu paketten yazılmaz (paket_ac ana=
        # kimlikten seçer), dolayısıyla ETH'nin barını BTC deposuyla kıyaslamak
        # sahte tazelik üretirdi. BTCUSDT anahtarı yoksa o satır atlanır.
        for ad, yedek, yol in (("BTCUSDT", None, GIRDI / "m15.json"),
                               ("ETHUSDT", None, IKINCI["girdi"] / "m15.json")):
            p_ms = harita.get(ad)
            if p_ms is None and yedek:
                p_ms = harita.get(yedek)
            if p_ms is None:
                continue
            try:
                d_ms = _son_bar_ms(json.loads(yol.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                d_ms = None
            if d_ms is not None and p_ms <= d_ms:
                geri.append(f"{ad}: paket {int(p_ms)} ≤ depo {int(d_ms)}")
            else:
                taze.append(ad)
        if geri and not taze:
            redded[sha] = f"tümü bayat: {'; '.join(geri)}"
            _defter_yaz(islenen, p, sha, redded)
            return {"paket": p.name, "atlandi": (
                "paketin verisi depodakinden yeni DEĞİL → veri GERİ SARILMADI "
                f"({'; '.join(geri)})")}
        if geri:
            # KARIŞIK paket: taze sembol kara listeye GÖMÜLMEZ (deftere
            # yazılmaz) — uyarı her istemde görünür kalır, taze tam paket
            # gelince o işlenir. Eskiden SHA kalıcı yazılıyordu = taze veri
            # sonsuza dek kayboluyordu.
            return {"paket": p.name, "atlandi": (
                f"KARIŞIK paket: {', '.join(taze)} taze ama {'; '.join(geri)} "
                "bayat → kısmi geri sarma olmasın diye ALINMADI. Bütün "
                "sembolleri taze TEK paket gönder (bu uyarı o gelene dek "
                "tekrarlanır; paket kara listeye YAZILMADI)")}
        argv = [sys.executable, str(acici), "--paket", str(p)]
        if surum < 2 and tek in BEKLENEN_SEMBOL:
            argv += ["--sembol", tek]          # paket_ac içinde ikinci kilit
        try:
            pr = subprocess.run(argv, capture_output=True, text=True,
                                timeout=min(120, _kalan_butce()), cwd=str(REPO))
        except (subprocess.TimeoutExpired, OSError) as e:
            return {"paket": p.name, "hata": f"{type(e).__name__}: {e}"}
        # ÇIKIŞ KODU DENETLENİR: paket_ac reddettiyse (exit≠0) bu "alındı"
        # DEĞİLDİR ve SHA kara listeye GÖMÜLMEZ — gerçek hata görünür kalır,
        # düzeltilmiş paket/yeniden deneme mümkün olur. (Eskiden returncode
        # hiç bakılmadan 'depoya alındı → {}' basılıyordu.)
        if pr.returncode != 0:
            hata = (pr.stderr.strip() or pr.stdout.strip())[-300:] \
                or f"paket_ac çıkış kodu {pr.returncode}"
            return {"paket": p.name, "hata": hata}
        try:
            sonuc = json.loads(pr.stdout) if pr.stdout.strip().startswith("{") else {}
        except json.JSONDecodeError as e:
            return {"paket": p.name, "hata": f"JSONDecodeError: {e}"}
        islenen.add(sha)
        _defter_yaz(islenen, p, sha, redded, stat=stat_cache)
        return {"paket": p.name, "sonuc": sonuc, "yol": str(p)}
    # Paket alınmadı (yaygın durum): güncellenen stat ön-belleğini kalıcılaştır ki
    # sonraki istem değişmemiş dosyaları yeniden okumasın.
    if stat_cache != (defter.get("stat") or {}):
        try:
            _atomik_yaz(PAKET_DEFTER, json.dumps(
                {"islenen": sorted(islenen), "reddedilen": redded,
                 "son": defter.get("son") or {}, "stat": stat_cache},
                ensure_ascii=False, indent=2))
        except OSError:
            pass
    return {}


def _defter_yaz(islenen: set, p: Path, sha: str, redded: dict | None = None,
                stat: dict | None = None) -> None:
    if stat is None:                     # mevcut stat ön-belleğini KORU (S8 prefilter)
        try:
            stat = (json.loads(PAKET_DEFTER.read_text(encoding="utf-8")) or {}).get("stat")
        except (OSError, json.JSONDecodeError):
            stat = None
    try:
        _atomik_yaz(PAKET_DEFTER, json.dumps(
            {"islenen": sorted(islenen), "reddedilen": redded or {},
             "son": {"dosya": str(p), "sha": sha},
             **({"stat": stat} if stat else {})},
            ensure_ascii=False, indent=2))
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


def _acik_emri_olc(kayit: dict, girdi_dizin: Path, state_dizin: Path) -> dict:
    """AÇIK sunulan emri BU koşunun barlarıyla ÖLÇ (kapandı mı, R kaç?).

    Neden: `sunulan_karar.json` kendi açıklamasında "her koşuda simule_et ile
    ölçülür, kapanınca düşülür" diyordu ama bu ölçüm HİÇBİR YERDE YAPILMIYORDU —
    dosya yalnız BASILIYORDU. Sonuç: 2026-07-28 16:45'te stop olan ETH SHORT'u
    (stop 1924.993333, o barın tepesi 1928.31) sistem günlerce "AÇIK" diye
    raporladı; kullanıcı var olmayan bir pozisyonun riskini taşıdı, strateji
    süzgecinin EKLEME YASAĞI gerçek olmayan pozisyon yüzünden yeni emirleri
    bloklamaya devam etti ve -1R sicile hiç yazılmadı.

    Ölçüm akıbet motorunun AYNI muhafazakâr kurallarıyla yapılır (aynı barda
    stop+hedef → STOP; market dolum açık beyanla). Ölçülemezse kayıt AÇIK kalır
    (fail-closed: kanıtsız kapatma yok).
    """
    bos = {"kapandi": False, "sonuc": "VERİ YOK"}
    try:
        scripts = SKILL / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import akibet_etiketle as AE                              # noqa: PLC0415
    except Exception:                                             # noqa: BLE001
        return bos
    try:
        giris = float(kayit["giris"]); stop = float(kayit["stop"])
        t1 = float(kayit["t1"]); zaman = int(kayit["karar_bari"])
    except (KeyError, TypeError, ValueError):
        return {"kapandi": False, "sonuc": "VERİ YOK — kayıt şema dışı"}
    karar = {
        "karar": str(kayit.get("yon", "")).upper(),
        "yon": str(kayit.get("yon", "")).upper(),
        "giris": giris,
        "giris_alt": float(kayit.get("giris_alt", giris)),
        "giris_ust": float(kayit.get("giris_ust", giris)),
        "stop": stop, "t1": t1,
        "iptal": float(kayit.get("iptal", stop)),
        "giris_tipi": kayit.get("giris_tipi", "market"),
    }
    # Bar havuzu: bu koşunun kline'ı + arşiv (kayan pencere telafisi — karar barı
    # 200-barlık pencereden düşmüş olabilir, arşiv onu geri getirir).
    try:
        barlar = AE.bar_yukle([str(state_dizin / "bar_arsivi.jsonl"),
                               str(girdi_dizin / "m15.json")])
    except Exception:                                             # noqa: BLE001
        return bos
    if not barlar:
        return bos
    try:
        s = AE.simule_et(karar, zaman, barlar, AE.KONVANSIYON)
    except Exception as e:                                        # noqa: BLE001
        return {"kapandi": False, "sonuc": f"VERİ YOK — ölçüm hatası ({type(e).__name__})"}
    kod = str(s.get("sonuc", ""))
    terminal = any(x in kod for x in ("STOP", "T1", "T2", "INVALIDATION", "İPTAL"))
    return {"kapandi": bool(s.get("olculebilir") and terminal) or "İPTAL" in kod,
            "sonuc": kod, "r": s.get("r"),
            "cikis_bar_utc": s.get("cikis_bar_utc") or s.get("cikis_bar")}


def _gorev_bas() -> None:
    """Duran görevi bağlama bas — yeni pencere görevi/hedefi tekrar sormaz.

    FAIL-VISIBLE: görev okunamazsa boru hattı YİNE koşar, ama kaybın kendisi
    açıkça yazılır. İlk sürüm yalnız (OSError, JSONDecodeError) yakalıyordu;
    şema dışı bir gorev.json (ör. kök liste) AttributeError fırlatıp main()'i
    komple düşürüyordu → K1→K5 hiç koşmuyor, kullanıcıya yalnız "kanca hatası"
    gidiyordu (adversarial denetimde ölçüldü: 76 satır → 2 satır).
    """
    try:
        g = json.loads(GOREV.read_text(encoding="utf-8"))
        if not isinstance(g, dict):
            raise TypeError(f"kök tip {type(g).__name__}, sözlük bekleniyordu")
        prof = g.get("eth_profili")
        prof = prof if isinstance(prof, dict) else {}
        sira = g.get("sira")
        sira = sira if isinstance(sira, list) else []
        print("[PİRAMİT — DURAN GÖREV] " + str(g.get("gorev", "")))
        if sira:
            print("   sıra: " + " ".join(str(x) for x in sira))
        if prof:
            print(f"   ETH profili: {prof.get('kontrat_eth')} ETH kontrat, "
                  f"sermaye {prof.get('sermaye_usd')} USD, kaldıraç "
                  f"{prof.get('kaldirac')}x, stop {prof.get('stop_usdt')} USDT "
                  f"(sabit), hedef {prof.get('hedef_usdt_brut')} USDT brüt, "
                  f"R_min {prof.get('r_min')}, kurulum ölçeği "
                  f"{prof.get('kurulum_olcegi')}")
        if g.get("strateji_kurali"):
            print("   strateji: " + str(g.get("strateji_kurali")))
        # BEKLEYEN İŞLER: kullanıcının "sonra yapacağız" dediği maddeler. Dosyada
        # durup basılmazsa yeni pencere onları göremez ve iş sessizce kaybolur
        # (EKSİK_AKTARIM). Yalnız AÇIK olanlar basılır.
        _bekleyen = g.get("bekleyen_isler")
        for _b in (_bekleyen if isinstance(_bekleyen, list) else []):
            if not isinstance(_b, dict):
                continue
            if str(_b.get("durum", "")).upper().startswith("KAPANDI"):
                continue
            print(f"   ⏳ BEKLEYEN İŞ [{_b.get('id', '?')}] {_b.get('durum', '')} — "
                  f"{_b.get('ne', '')}")
            if _b.get("olculen_durum"):
                print(f"      ölçülen durum: {_b['olculen_durum']}")
            if _b.get("on_kosul"):
                print(f"      ön koşul: {_b['on_kosul']}")
        for _ad, _sk, _gd, _st in (
                ("BTCUSDT", REPO / "engine" / "state" / "sunulan_karar.json",
                 GIRDI, REPO / "engine" / "state"),
                ("ETHUSDT", IKINCI["state"] / "sunulan_karar.json",
                 IKINCI["girdi"], IKINCI["state"])):
            try:
                if _sk.exists():
                    _s = json.loads(_sk.read_text(encoding="utf-8"))
                    _sonuc = _acik_emri_olc(_s, _gd, _st)
                    if _sonuc.get("kapandi"):
                        # KAPANDI: kayıt DÜŞÜLÜR ve sonuç görünür kılınır. Eskiden
                        # bu ölçüm HİÇ yapılmıyordu (dosya yalnız basılıyordu):
                        # 2026-07-28 16:45'te stop olan ETH emri günlerce "AÇIK"
                        # görünüp kullanıcıya var olmayan pozisyon raporluyordu.
                        print(f"   ✔ KAPANDI [{_ad}]: {_s.get('yon')} @{_s.get('giris')} → "
                              f"{_sonuc['sonuc']}"
                              + (f" | gerçekleşen R = {_sonuc['r']}"
                                 if _sonuc.get("r") is not None else "")
                              + f" (karar barı {_s.get('karar_bari_utc')}) — kayıt düşüldü")
                        _arsiv = _sk.with_name("kapanan_kararlar.jsonl")
                        try:
                            with _arsiv.open("a", encoding="utf-8") as _f:
                                _f.write(json.dumps({**_s, "kapanis": _sonuc},
                                                    ensure_ascii=False) + "\n")
                            _sk.unlink()
                        except OSError:
                            pass
                    else:
                        print(f"   AÇIK SUNULAN EMİR [{_ad}]: {_s.get('yon')} "
                              f"@{_s.get('giris')} | stop {_s.get('stop')} | "
                              f"T1 {_s.get('t1')} (karar barı {_s.get('karar_bari_utc')}; "
                              f"ÖLÇÜLDÜ: {_sonuc.get('sonuc', 'VERİ YOK')})")
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                print(f"   ⚠ {_sk.name} [{_ad}] okunamadı — açık emir kaydı elle kontrol edilmeli")
        _hafiza_bas(g)
    except Exception as e:  # noqa: BLE001 — görev bloğu boru hattını DÜŞÜREMEZ
        print(f"[PİRAMİT] ⚠ DURAN GÖREV OKUNAMADI ({type(e).__name__}: {e}) — "
              f"{GOREV} yok ya da şema dışı. Görev/hedef/ETH profili bağlama "
              "GİRMEDİ; kullanıcıya sorulmalı (uydurulmaz). Boru hattı koşar.")


def _hafiza_bas(g: dict) -> None:
    """Hafıza YOLUNU değil İÇERİĞİNİ bas: yeni pencere son durumu görsün."""
    hafiza = g.get("hafiza")
    if not isinstance(hafiza, dict):
        return
    for ad, yol in hafiza.items():
        p = Path(str(yol).split(" —")[0].strip())
        if not p.is_absolute():
            p = REPO / p
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            print(f"   hafıza[{ad}]: OKUNAMADI ({p}) — geçmiş UYDURULMAZ")
            continue
        if not isinstance(d, dict):
            print(f"   hafıza[{ad}]: şema dışı ({p})")
            continue
        ozet = _kayit_ozeti(d)
        if not ozet:
            # Devir-teslim gibi SEMBOL BLOKLU dosyalar bir kat derindedir;
            # düz okuyunca "kayıt boş" deyip önceki pencerenin sonucunu
            # yutuyordu. Bir kat in, her sembolü ayrı özetle.
            alt = {k: _kayit_ozeti(v) for k, v in d.items()
                   if isinstance(v, dict) and _kayit_ozeti(v)}
            ozet = alt or None
        print(f"   hafıza[{ad}]: "
              + (json.dumps(ozet, ensure_ascii=False) if ozet else "kayıt boş"))


def _kayit_ozeti(d) -> dict:
    """Bir anlık görüntü/karar bloğundan taşınabilir özet çıkar."""
    if not isinstance(d, dict):
        return {}
    ozet = {k: d.get(k) for k in
            ("sembol", "son_bar_utc", "YON_BIAS", "yon_skoru", "KARAR",
             "islem_kalitesi", "EMIR") if d.get(k) is not None}
    for alan in ("islem_seviyeleri", "seviyeler", "emir"):
        sev = d.get(alan)
        if isinstance(sev, dict) and sev:
            ozet["seviyeler"] = {k: sev.get(k) for k in
                                 ("giris", "stop", "hedef", "T1", "R")
                                 if sev.get(k) is not None}
            break
    return ozet


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
                seri: Path | None = None, sembol: str = "BTCUSDT") -> dict:
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
            "--sembol", sembol,
            "--ham", str(girdi / "turev_ham"),
            "--out", str(girdi / "turev.json")]
    if not onceki.get("http_engelli"):
        argv.append("--http")
    try:
        pr = subprocess.run(argv, capture_output=True, text=True, timeout=min(60, _kalan_butce()),
                            cwd=str(REPO))
        job = json.loads(pr.stdout) if pr.stdout.strip().startswith("{") else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        return {"durum": f"türev üreteci çalışmadı ({type(e).__name__})"}
    return {"kaynaklar": job.get("_kaynaklar", {}), "eksikler": job.get("_eksikler", []),
            "http_engelli": bool(job.get("_ag_hatalari"))}


def _karar_grafigi() -> list:
    """Koşu sonrası karar grafiği (SVG) — çizim karar ÜRETMEZ, kararı BASAR.

    Seviyeler smc_tespit'in ölçtüğü yapıdan (grafik-cizim `otomatik.smc`),
    emir kutusu son raporun birincil emrinden gelir. Çizim karara GERİ
    BESLENMEZ: aynı ölçümler karara zaten smc_tespit/emir_plani üzerinden
    giriyor; grafiği danışman yapmak DAİRESEL kanıt olurdu (gözlemci yasağı).
    """
    cizici = REPO / ".claude" / "skills" / "grafik-cizim" / "scripts" / "cizim.py"
    if not cizici.exists():
        return []
    uret = []
    isler = (("BTCUSDT", GIRDI / "m15.json", "son_rapor.json", "btc_karar.svg"),
             ("ETHUSDT", IKINCI["girdi"] / "m15.json", "son_rapor_eth.json",
              "eth_karar.svg"))
    for ad, kline, rapor_ad, svg_ad in isler:
        if not kline.exists():
            continue
        try:
            z = (json.loads((SKILL / "state" / rapor_ad)
                            .read_text(encoding="utf-8")).get("ZIRVE") or {})
        except (OSError, json.JSONDecodeError):
            z = {}
        oto = {"smc": True, "ma": [{"tip": "ema", "period": 50, "renk": "#ff9800"}]}
        emir0 = ((z.get("emir_adaylari") or [{}])[0]
                 if str(z.get("EMIR", "")).startswith(("MARKET", "LIMIT")) else None)
        if emir0 and None not in (emir0.get("giris"), emir0.get("stop"),
                                  emir0.get("hedef")):
            oto["emir"] = {"giris": emir0["giris"], "stop": emir0["stop"],
                           "hedef": emir0["hedef"],
                           "yon": str(emir0.get("yon", "")).lower()}
        cikti = REPO / "engine" / "cikti" / svg_ad
        skor = z.get("yon_skoru")
        job = {"veri": {"kline": str(kline)},
               "baslik": f"{ad} · 15M · Binance",
               "alt_baslik": (f"otomatik SMC katmanı — YÖN: "
                              f"{z.get('YON_BIAS', 'VERİ YOK')}"
                              + (f" (skor {skor})" if skor is not None else "")
                              + f" | {str(z.get('EMIR', 'VERİ YOK'))[:64]}"),
               "tema": "koyu", "paneller": [{"tip": "hacim", "yukseklik": 0.12}],
               "otomatik": oto, "cikti": str(cikti)}
        jp = SKILL / "state" / "_job" / f"cizim_{svg_ad}.json"
        try:
            jp.parent.mkdir(parents=True, exist_ok=True)
            cikti.parent.mkdir(parents=True, exist_ok=True)
            jp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            pr = subprocess.run([sys.executable, str(cizici), "--job", str(jp)],
                                capture_output=True, text=True, timeout=min(120, _kalan_butce()),
                                cwd=str(REPO))
            if pr.returncode == 0 and cikti.exists():
                uret.append(str(cikti.relative_to(REPO)))
            else:
                print(f"[PİRAMİT] Karar grafiği çizilemedi ({ad}): "
                      f"{(pr.stderr or pr.stdout).strip()[:120]}")
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"[PİRAMİT] Karar grafiği çizilemedi ({ad}): {type(e).__name__}")
    return uret


def _durum_oku() -> dict:
    try:
        d = json.loads(DURUM.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    # kök sözlük değilse (elle bozulmuş liste vb.) "geçmiş yok" sayılır —
    # aksi halde onceki.get() her istemde AttributeError ile kancayı
    # öldürüyordu ve dosya hiç yeniden yazılmadığı için durum KALICIYDI.
    return d if isinstance(d, dict) else {}


def _durum_yaz(d: dict) -> None:
    try:
        _atomik_yaz(DURUM, json.dumps(d, ensure_ascii=False, indent=2))
    except OSError:
        pass


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


def _kos() -> tuple[str, int, bool]:
    """Boru hattını koştur; (özet metni, çıkış kodu, kum_havuzu_mu).

    `kum` KOŞU ÖNCESİ hesaplanıp DÖNDÜRÜLÜR (B6): gerçek koşu durum.json'a yeni
    barı yazdığı için koşudan SONRA _zaten_islendi() True döner ve gerçek koşu
    yanlışlıkla "KUM HAVUZU — defter korundu" diye etiketlenirdi."""
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
        # KORELASYON TAZELİĞİ ana yolda da uygulanır (B1): iki serinin son barları
        # 240 dk'dan fazla ayrışıksa ρ bayat hizalı pencereden ölçülür ve "güncel"
        # sanılırdı. ETH yolunda (_ikinci_job) bu kapı vardı, ana yolda YOKTU.
        ana_ms = _girdi_son_bar()
        try:
            eth_ms = _son_bar_ms(json.loads(eth_m15.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            eth_ms = None
        if (ana_ms is not None and eth_ms is not None
                and abs(ana_ms - eth_ms) > 240 * 60 * 1000):
            job["_korelasyon_uyarisi"] = (
                "KORELASYON ATLANDI (ana yol): BTC/ETH son barları 240 dk'dan "
                f"fazla ayrışık (BTC {int(ana_ms)} / ETH {int(eth_ms)}) — bayat "
                "hizalı pencereyle ρ ölçülmez (fail-closed)")
        else:
            job["korelasyon"] = {"a": str(GIRDI / "m15.json"), "b": str(eth_m15),
                                 "ad_a": "BTC", "ad_b": "ETH"}
    ek = _ek_kanallar(job)
    if ek:
        print(f"[PİRAMİT] Ek kanal(lar) otomatik bağlandı: {', '.join(ek)}")
    ozet, kod = _job_kos(job, "otomatik_job.json", "son_rapor.json")
    return ozet, kod, kum


def _job_kos(job: dict, job_ad: str, rapor_ad: str) -> tuple[str, int]:
    jp = SKILL / "state" / "_job" / job_ad
    jp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    pr = subprocess.run(
        [sys.executable, str(PIRAMIT), "--job", str(jp),
         "--out", str(SKILL / "state" / rapor_ad), "--ozet"],
        capture_output=True, text=True, timeout=min(ZAMAN_ASIMI, _kalan_butce()), cwd=str(REPO))
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
    # KORELASYON TAZELİĞİ: iki serinin son barları 240 dk'dan fazla ayrışıksa
    # ρ bayat hizalı pencereden ölçülür ve "güncel" sanılır — beyan düşürülür
    # (fail-closed) ve uyarı görünür kılınır.
    ana_ms = _girdi_son_bar()
    try:
        eth_ms = _son_bar_ms(json.loads((g / "m15.json").read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        eth_ms = None
    kor_bayat = (ana_ms is not None and eth_ms is not None
                 and abs(ana_ms - eth_ms) > 240 * 60 * 1000)
    job = {
        "soru": f"otomatik koşu — {IKINCI['ad']} (ana sembolle korelasyonlu)",
        "sembol": f"engine/girdi/{IKINCI['girdi'].name}",
        "veri": veri, "state_dir": str(sdir), "defter_dizini": str(st),
        "bar_arsivi": str(st / "bar_arsivi.jsonl"),
        "_hafiza": ("KUM HAVUZU — bu bar zaten işlenmişti" if kum
                    else "GERÇEK — yeni bar"),
        # Gözlemci "ikinci sembol" kuralını buradan tanır (ana sembolde YOK).
        "_ikinci_sembol": IKINCI["ad"],
    }
    if kor_bayat:
        job["_korelasyon_uyarisi"] = (
            "KORELASYON ATLANDI: BTC/ETH son barları 240 dk'dan fazla ayrışık "
            f"(BTC {int(ana_ms)} / ETH {int(eth_ms)}) — bayat hizalı pencereyle "
            "ρ ölçülmez (fail-closed); iki sembolü de taze tek paket gönder")
    else:
        job["korelasyon"] = {"a": str(GIRDI / "m15.json"),
                             "b": str(g / "m15.json"),
                             "ad_a": "BTC", "ad_b": IKINCI["ad"]}
    # PROFİL KOŞULSUZ BEYAN EDİLİR. Eskiden `if exists()` idi: dosya yoksa
    # beyan düşüyor, gözlemci "beyan edilmedi"yi denetlemediği için ihlal
    # üretilmiyor ve sistem SESSİZCE daha agresif emir yayınlıyordu (sabit
    # -100 USDT stop yerine 5.55 puanlık stop, R 1.35 yerine 2.55).
    # Koşulsuz beyanla dosya yoksa akış "beyan edildi ama koşmadı" dalına
    # düşer → EKSIK_AKTARIM ihlali → işlem MÜHÜRLENİR (fail-closed).
    job["usd_profil"] = str(IKINCI["profil"])
    if not IKINCI["profil"].exists():
        job["_profil_uyarisi"] = (f"sabit-USDT profili DOSYASI YOK "
                                  f"({IKINCI['profil']}) — kısıt uygulanamaz")
    return job


def _kaynak_teyit_bas() -> None:
    """Bağlayıcı kaynak-teyidi raporunu bas (salt-okunur; kanca AĞA ÇIKMAZ).

    Kullanıcı kuralı (2026-08-09): her koşuda bağımsız kaynak teyidi. Dış borsa
    API'si kancadan erişilemez (api.crypto.com CONNECT 403 — proxy engeli);
    çekim yalnız Claude'un MCP bağlayıcısıyla yapılır → engine/state/
    kaynak_ham.json → scripts/kaynak_teyit.py → engine/state/kaynak_teyit.json.
    Kanca burada yalnız raporu okur: bu barın taze teyidi varsa özetini basar,
    yoksa GÖRÜNÜR "TEYİT GEREKLİ" uyarısı basar ki adım sessizce atlanamasın.
    Teyit karara GERİ BESLENMEZ (dairesel kanıt yasak) — veri bütünlüğü sınavıdır.
    """
    tp = REPO / "engine" / "state" / "kaynak_teyit.json"
    gerekli = ("[PİRAMİT] ⚠ KAYNAK TEYİDİ GEREKLİ (duran görev adım 8): MCP "
               "bağlayıcısından (Crypto.com get_ticker + get_candlestick 15m, "
               "BTCUSD-PERP/ETHUSD-PERP) taze veri çekilip engine/state/"
               "kaynak_ham.json'a `zaman_utc` damgasıyla yazılır ve `python3 "
               ".claude/skills/piramit-sistem/scripts/kaynak_teyit.py --ham "
               "engine/state/kaynak_ham.json` koşulur — ağ kancadan 403-engelli, "
               "çekim yalnız Claude/MCP katmanında yapılabilir.")
    try:
        son = _girdi_son_bar()
        if son is None:
            return
        if not tp.exists():
            print(gerekli)
            return
        t = json.loads(tp.read_text(encoding="utf-8"))
        if t.get("son_bar_ms") != son:
            print(f"[PİRAMİT] ⚠ KAYNAK TEYİDİ BAYAT — rapor {t.get('son_bar_utc')} "
                  "barına ait, girdi ilerledi.")
            print(gerekli)
            return
        print("[PİRAMİT] KAYNAK TEYİDİ (bağlayıcı): " + str(t.get("ozet", "özet alanı yok")))
        if t.get("HUKUM_GENEL") != "UYUM":
            print("[PİRAMİT] ⚠ KAYNAK TEYİDİ UYUMSUZ — veri şüphesi çıktıda "
                  "GİZLENMEZ; işlem hükmü verilmeden önce kaynak ayrışması "
                  "açıklanmalı (fail-closed).")
    except Exception as e:  # noqa: BLE001 — teyit bloğu kancayı düşüremez
        print(f"[PİRAMİT] ⚠ kaynak_teyit okunamadı ({type(e).__name__}: {e}) — "
              "teyit elle yapılmalı (uydurulmaz).")


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
    http_once = bool(onceki.get("http_engelli"))
    # Türev girdisi HER İSTEMDE tazelenir (CVD determinist: aynı kline = aynı
    # dosya → gereksiz koşu tetiklenmez). Parmak izi bundan SONRA alınır ki
    # yeni OI görüntüsü/funding boru hattını kendiliğinden yeniden koştursun.
    turev = _turev_uret(onceki)
    if turev.get("kaynaklar") is not None:
        # http mandalı TEK YÖNLÜ (S8): bir kez engellenince True kalır; False'a
        # ezilmez. Eskiden mandal True iken --http verilmiyor → ağ hatası olmuyor
        # → dönüş http_engelli=False → mandal sıfırlanıp her istem ağı yeniden
        # deniyordu (docstring vaadinin tersi).
        if turev.get("http_engelli"):
            onceki["http_engelli"] = True
        var = ", ".join(turev["kaynaklar"]) or "yok"
        print(f"[PİRAMİT] Türev kanalı otomatik üretildi → dolu: {var} | "
              f"eksik: {len(turev.get('eksikler', []))} kanal (uydurulmadı)")
    # İkinci sembolün türevi de KENDİ kline'ından üretilir (CVD çevrimdışı).
    # Sembol AÇIKÇA geçilir (B5): yoksa turev_girdi varsayılanı BTCUSDT'ye düşer
    # ve ETH'nin funding/LSR/OI'si BTC verisiyle kirlenirdi.
    if (IKINCI["girdi"] / "m15.json").exists():
        # ETH dönüşü ATILMAZ (B3): başarısızlık/eksik kanal raporlanır, mandal taşınır.
        t2 = _turev_uret(onceki, IKINCI["girdi"],
                         IKINCI["state"] / "turev_seri.jsonl", sembol="ETHUSDT")
        if t2.get("http_engelli"):
            onceki["http_engelli"] = True
        if t2.get("kaynaklar") is not None:
            v2 = ", ".join(t2["kaynaklar"]) or "yok"
            print(f"[PİRAMİT] ETH türev kanalı üretildi → dolu: {v2} | "
                  f"eksik: {len(t2.get('eksikler', []))} kanal")
        elif t2.get("durum"):
            print(f"[PİRAMİT] ETH türev üretilemedi: {t2['durum']}")
    fp = _fp()
    if onceki.get("fp") == fp and onceki.get("ozet"):
        if bool(onceki.get("http_engelli")) != http_once:
            _durum_yaz(onceki)   # ağ-engeli bayrağı bu yolda da KALICI olsun
        print("[PİRAMİT] Girdi verisi DEĞİŞMEDİ — yeniden koşulmadı; son koşunun "
              "sonucu (motor hafızası kirletilmedi):")
        print(onceki["ozet"])
        _kaynak_teyit_bas()
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
    # ÇÖKME ÖNBELLEĞE YAZILMAZ: geçerli rapor işareti yoksa (traceback vb.)
    # özet DURUM'a girmez — girseydi sonraki her istem traceback'i "son
    # koşunun sonucu" diye taşırdı ve fp aynı kaldığı için yeniden denenmezdi.
    if kod not in (0, 2) or "PİRAMİT SİSTEMİ" not in ozet:
        print(f"[PİRAMİT] Boru hattı ÇÖKTÜ (çıkış kodu {kod}) — çıktı önbelleğe "
              "YAZILMADI, sonraki istemde yeniden denenir; elle koşuya düşülür "
              "(bu AÇIKÇA söylenmeli). Son çıktı:")
        print(ozet[-1200:])
        return 0

    hafiza = ("KUM HAVUZU (motor bu barı zaten işlemişti — gerçek defter "
              "korundu)" if kum else "GERÇEK hafıza (yeni bar)")
    print(f"[PİRAMİT] Boru hattı koştu — hafıza: {hafiza} "
          f"(çıkış kodu {kod}; 0=zirve, 2=bir katman kapısında durdu):")
    print(ozet)

    # --- İKİNCİ SEMBOL: aynı istemde, aynı disiplinle (elle koşu yok) -------
    ij = _ikinci_job()
    if ij is None:
        print(f"[PİRAMİT] İkinci sembol ({IKINCI['ad']}) verisi YOK "
              f"({IKINCI['girdi']}/m15.json) — koşulmadı, uydurulmadı.")
    else:
        if ij.get("_korelasyon_uyarisi"):
            print(f"[PİRAMİT] {ij['_korelasyon_uyarisi']}")
        try:
            ozet2, kod2 = _job_kos(ij, "otomatik_job_eth.json",
                                   "son_rapor_eth.json")
            if kod2 not in (0, 2) or "PİRAMİT SİSTEMİ" not in ozet2:
                print(f"[PİRAMİT] İkinci sembol {IKINCI['ad']} ÇÖKTÜ (çıkış kodu "
                      f"{kod2}) — çıktısı önbelleğe YAZILMADI; elle koşuya "
                      "düşülür (bu AÇIKÇA söylenmeli). Son çıktı:")
                print(ozet2[-800:])
            else:
                print(f"[PİRAMİT] İkinci sembol {IKINCI['ad']} koştu "
                      f"(çıkış kodu {kod2}; sabit-USDT profili "
                      f"{'BAĞLI' if ij.get('usd_profil') else 'YOK'}):")
                print(ozet2)
                ozet = f"{ozet}\n{ozet2}"
        except (subprocess.TimeoutExpired, OSError) as e:
            print(f"[PİRAMİT] İkinci sembol koşulamadı ({type(e).__name__}: {e}) "
                  "— elle koşuya düşülür (bu AÇIKÇA söylenmeli).")
    # Karar grafiği: her koşudan sonra ölçülen yapı SVG'ye basılır (çizim
    # karar üretmez; karara geri beslenmez — dairesel kanıt yasak).
    grafikler = _karar_grafigi()
    if grafikler:
        satir = ("[PİRAMİT] Karar grafikleri çizildi (görsel çıktı; karar "
                 "ÜRETMEZ): " + ", ".join(grafikler))
        print(satir)
        ozet = f"{ozet}\n{satir}"
    _kaynak_teyit_bas()
    try:
        _atomik_yaz(DURUM, json.dumps(
            {"fp": fp, "ozet": ozet, "kod": kod,
             "http_engelli": bool(onceki.get("http_engelli"))},
            ensure_ascii=False, indent=2))
    except OSError:
        pass
    return 0


def _sessiz_cik(kod: int = 0):
    """stdout kapalıyken çıkışta ikinci BrokenPipeError üretme.

    Python yorumlayıcısı çıkışta stdout'u flush eder; boru kapalıysa bu flush
    yeni bir BrokenPipeError doğurur ve süreç 1 ile ölür. stdout'u /dev/null'a
    çevirip öyle çıkmak standart çözümdür.
    """
    try:
        sys.stdout.flush()
    except (BrokenPipeError, ValueError, OSError):
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except (OSError, ValueError):
            pass
    sys.exit(kod)


if __name__ == "__main__":
    try:
        _sessiz_cik(main() or 0)
    except BrokenPipeError:
        # Okuyan taraf çıktıyı erken kapattı (ör. `| head`). Kanca SÖZLEŞMESİ
        # "çıkış kodu DAİMA 0; istem asla bloklanmaz" — boru kırılması bu
        # sözleşmeyi çiğnemiyordu ama süreç 1 ile ölüyor ve DURUM yazımı
        # yarıda kalıyordu (çapraz doğrulama ajanı ölçtü). Sessizce 0 ile çık.
        _sessiz_cik(0)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — son emniyet: istem asla bloklanmaz
        try:
            print(f"[PİRAMİT] kanca hatası ({type(e).__name__}: {e})")
        except (BrokenPipeError, ValueError, OSError):
            pass          # tanı basılamıyorsa bile çıkış kodu 0 KALIR
        _sessiz_cik(0)
