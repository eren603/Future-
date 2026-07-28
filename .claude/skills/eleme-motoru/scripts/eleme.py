#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ELEME MOTORU — danışman/motor iddialarını 3 katmanda eler (yanlış-pozitif kırıcı).

KAYNAK (birebir okundu, hafızadan yazılmadı):
  claudecode/findings_filter.py   (sha a18eb6a21120)
      FilterStats            :16-24   -> ElemeIstatistigi
      desen aileleri         :31-79   -> 7 desen ailesi
      get_exclusion_reason   :81-154  -> sert_eleme_gerekcesi + bağlam kapıları
      .md kapısı             :92-94   -> kaynak kapısı
      C/C++ kapısı           :133-143 -> tür ev-ailesi kapısı  (2. katman)
      HTML kapısı            :145-152 -> squeeze/kaskad kapısı (2. katman)
      filter_findings        :197-343 -> ElemeMotoru.ele
  claudecode/claude_api_client.py (sha 32b5ca67c3d2)
      HARD EXCLUSIONS        :243-259 (16 madde)  -> emsaller/emsal_defteri.yaml
      SIGNAL QUALITY CRITERIA:261-265             -> somutluk (EMSAL-11)
      PRECEDENTS             :267-284 (17 madde)  -> emsaller/emsal_defteri.yaml
      confidence 1-10        :292-295             -> guven_10 bantları

ALAN ÇEVİRİSİ (güvenlik -> finans):
  "bulgu" = güvenlik bulgusu  ==>  DANIŞMAN/MOTOR İDDİASI.
  Şema, karar-kurulu/scripts/sentez.py'nin danışman şemasıdır:
      {"name":..., "stance": long|short|flat, "confidence": 0..1,
       "evidence": "...", "_verifier_confirmed": bool}
  Ek alanlar (bu motorun okuduğu):
      "kaynak"    -> iddiayı üreten motor dosyası  (kaynaktaki `file`)
      "baslik"    -> kısa başlık                   (kaynaktaki `title`)
      "zaman_utc" -> elle okumanın damgası (tazelik kapısı)

BAĞLAM (`baglam`) — 2. katman kapıları bunu okur, hepsi DEPODAN gerçek alan:
  {"rejim": {"durum":"trend|range|gecis|VERİ YOK","adx":..,"yuksek_vol":..},
   "turev_kapsam": 0.0..1.0,          # turev_akis.analyze -> "kapsam"
   "turev_faktorler": [{"faktor":"liquidation","skor":None|float}, ...],
   "son_bar_utc": "2026-07-28T12:00:00Z"}

DÜRÜSTLÜK: bu motor bir KARAR vermez, yalnız gürültüyü ayıklar. Elenen her
iddia gerekçesiyle raporlanır (sessiz kayıp yasak — gozlemci.py EKSIK_AKTARIM).
Eksik alan UYDURULMAZ; güven yokken fail-closed davranır.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple

try:  # yaml depoda kurulu (6.0.1); yoksa emsal katmanı fail-closed kapanır
    import yaml
except Exception:  # pragma: no cover
    yaml = None

VARSAYILAN_DEFTER = Path(__file__).resolve().parent.parent / "emsaller" / "emsal_defteri.yaml"
YOK = "VERİ YOK"


# --------------------------------------------------------------------------
# KONVANSİYONLAR — hiçbiri bu dosyada icat edilmedi; her biri depodaki bir
# motordan TEK-KAYNAK alınır ve çıktının `varsayimlar`ına yazılır.
# --------------------------------------------------------------------------
KONVANSIYON = {
    # turev-akis/scripts/turev_akis.py KONVANSIYON["kapsam_esigi"]
    "turev_kapsam_esigi": 0.5,
    # piramit-sistem/scripts/piramit.py KONVANSIYON["gorsel_tavan"]
    "gorsel_tavan": 0.50,
    # piramit-sistem/scripts/piramit.py KONVANSIYON["zorunlu_damga_tolerans_dk"]
    "damga_tolerans_dk": 240,
    # karar-kurulu/scripts/sentez.py thresholds.refute_penalty varsayılanı
    "refute_penalty": 0.25,
    # claude_api_client.py:293-295 güven bantları (1-10 ölçeği)
    "guven_dusuk_ust": 3.0,     # "1-3: Low confidence, likely false positive or noise"
    "guven_orta_alt": 4.0,      # "4-6: Medium confidence, needs investigation"
    "guven_orta_ust": 6.0,
}

# gozlemci.py AILE sözlüğünden birebir (kanıt aileleri — tünel görüşü ölçümü)
AILE = {
    "karar-motoru": "fiyat-yapisi",
    "grafik-calisma": "fiyat-yapisi",
    "smc_tespit": "fiyat-yapisi",
    "turev-akis": "turev-akis",
    "setup_dogrulama": "tarihsel-kanit",
    "backtest-motoru": "tarihsel-kanit",
    "gorsel-teyit": "gorsel",
}

# Motor kaynakları (EMSAL-04 / EMSAL-08 `kaynak_motor` yüklemi için)
MOTOR_KAYNAK = re.compile(
    r"(karar_motoru|smc_tespit|confluence|setup_dogrulama|turev_akis|"
    r"emir_plani|rr_denetim|sentez|backtest|risk\.py|portfolio|korelasyon|"
    r"usd_hedef|esik_kalibre|akibet_etiketle|kiyas)", re.IGNORECASE)


def _kucult(s: Any) -> str:
    """Türkçe-güvenli küçültme: 'İ'.lower() birleşik nokta üretir, önce eşlenir."""
    return str(s or "").replace("İ", "i").replace("I", "ı").lower()


# ==========================================================================
# İSTATİSTİK — kaynak: findings_filter.py:15-24 (FilterStats)
# ==========================================================================
@dataclass
class ElemeIstatistigi:
    """Eleme sürecinin istatistiği.

    Kaynak FilterStats'ın 7 alanının BİREBİR karşılıkları:
        total_findings       -> toplam_bulgu
        hard_excluded        -> sert_elenen
        claude_excluded      -> emsal_elenen
        kept_findings        -> tutulan
        exclusion_breakdown  -> eleme_dagilimi
        confidence_scores    -> guven_skorlari
        runtime_seconds      -> sure_saniye
    EK ALAN (kaynakta yok): baglam_elenen — kaynakta bağlam kapıları
    get_exclusion_reason içinde sert kuralla aynı sayaca yazılıyordu; burada
    2. katman ayrı sayılır ki hangi kapının elediği görünsün (KANIT.md/SAPMALAR).
    """
    toplam_bulgu: int = 0
    sert_elenen: int = 0
    baglam_elenen: int = 0
    emsal_elenen: int = 0
    tutulan: int = 0
    eleme_dagilimi: Dict[str, int] = field(default_factory=dict)
    guven_skorlari: List[float] = field(default_factory=list)
    sure_saniye: float = 0.0

    def dokum(self) -> str:
        ort = (sum(self.guven_skorlari) / len(self.guven_skorlari)
               if self.guven_skorlari else None)
        satir = [
            "ElemeIstatistigi",
            f"  toplam_bulgu   : {self.toplam_bulgu}",
            f"  sert_elenen    : {self.sert_elenen}",
            f"  baglam_elenen  : {self.baglam_elenen}   (EK ALAN — kaynakta yok)",
            f"  emsal_elenen   : {self.emsal_elenen}",
            f"  tutulan        : {self.tutulan}",
            f"  sure_saniye    : {self.sure_saniye:.4f}",
            f"  guven_skorlari : {[round(g, 2) for g in self.guven_skorlari]}"
            f"  (ortalama={round(ort, 2) if ort is not None else YOK})",
            "  eleme_dagilimi :",
        ]
        if not self.eleme_dagilimi:
            satir.append("      (boş)")
        for k, v in sorted(self.eleme_dagilimi.items(), key=lambda x: (-x[1], x[0])):
            satir.append(f"      {v:>3} × {k}")
        return "\n".join(satir)


# ==========================================================================
# KATMAN 1 — SERT KURALLAR (regex, deterministik, bağlamsız)
# Kaynak: findings_filter.py:27-131 (HardExclusionRules)
# ==========================================================================
class SertElemeKurallari:
    """Yaygın yanlış-pozitifler için sert eleme kuralları.

    Kaynak yapısına sadık: önceden derlenmiş desen aileleri + tek bir
    `eleme_gerekcesi()` sınıf metodu, elenecekse GEREKÇE string'i döner.
    """

    # <- _DOS_PATTERNS (findings_filter.py:31-35): ölçülmemiş felaket/tükenme
    _GENEL_RISK_DESENLERI: List[Pattern] = [
        re.compile(r'\b(piyasa|fiyat|borsa)\s+(çöker|çökebilir|çökecek|patlar)\b'),
        re.compile(r'\b(likidite|hacim)\s+(kurur|kuruyabilir|biter|tükenir)\b'),
        re.compile(r'\b(sonsuz|sınırsız|dipsiz)\s+(düşüş|yükseliş|kayıp)\b'),
        re.compile(r'\b(kara kuğu|black swan|felaket senaryosu|her şey çöker)\b'),
    ]

    # <- _RATE_LIMITING_PATTERNS (:38-43): seviyesiz genel öğüt
    _GENEL_TAVSIYE_DESENLERI: List[Pattern] = [
        re.compile(r'\b(stop|zarar durdur)\s*(kullanılmalı|kullanın|koyun|şart)'),
        re.compile(r'\b(risk yönetimi|pozisyon boyutu)\s*(uygulanmalı|şart|önemli|unutulmamalı)'),
        re.compile(r'\b(pozisyon|kaldıraç)\s*(küçültülmeli|azaltılmalı|düşürülmeli)\b'),
        re.compile(r'\b(dikkatli olun|temkinli olun|takip edilmeli|izlenmeli)\b'),
        re.compile(r'\b(en iyi uygulama|best practice|ideal olarak|yapılmalıydı)\b'),
        re.compile(r'\b(alan|parametre|girdi)\s+(doğrulanmıyor|kontrol edilmiyor|doğrulanmamış)\b'),
    ]

    # <- _RESOURCE_PATTERNS (:45-51): işletim/bakım — yön sinyali değil
    _ISLETIM_DESENLERI: List[Pattern] = [
        re.compile(r'\b(api anahtarı|api key|cüzdan anahtarı|kimlik bilgisi|parola)\b'),
        re.compile(r'\b(bellek|ram|cpu|disk)\s*(şişti|doldu|yetersiz|sızıntı|tüketimi)\b'),
        re.compile(r'\b(boru hattı|motor|betik|script)\s+(yavaş|donuyor|takıldı)\b'),
        re.compile(r'\b(bağlantı|soket|dosya)\s+(koptu|sızıntısı|kapatılmamış|açık kaldı)\b'),
        re.compile(r'\b(veri|panel|okuma)\s+(eski|bayat|güncel değil)\b'),
        re.compile(r'\b(uç|endpoint|ağ|network)\s+(erişilemedi|kapalı|çekilemedi|yok)\b'),
        re.compile(r'\b(motor|betik|script)\s+(çöktü|hata verdi|exception|traceback)\b'),
        re.compile(r'\balan(ı|ları)?\s+(none|null|boş)\b'),
        re.compile(r'\bkullanıcı(nın)?\s+(dediği|iddiası|beyanı|söylediği)\b'),
    ]

    # <- _OPEN_REDIRECT_PATTERNS (:53-57): düşük etkili / teorik
    _DUSUK_ETKI_DESENLERI: List[Pattern] = [
        re.compile(r'\b(tek|bir)\s+(fitil|wick|mum|bar)\s+(gürültüsü|sapması|etkisi)\b'),
        re.compile(r'\b(1|bir|birkaç)\s*(tick|pip)\s*(sapma|fark|kayma)\b'),
        re.compile(r'\b(spread|slipaj|yuvarlak rakam)\s+(etkisi|gürültüsü)\b'),
        re.compile(r'\b(teorik olarak|kuramsal olarak|varsayımsal olarak)\b'),
    ]

    # <- _REGEX_INJECTION (:71-75): bu deponun kapsamı dışı
    _KAPSAM_DISI_DESENLERI: List[Pattern] = [
        re.compile(r'\b(canlı|otomatik)\s+(emir|işlem|al[-\s]?sat)\b'),
        re.compile(r'\b(emri|emir)\s+(gönder|ilet|aç)(in|elim)?\b'),
        re.compile(r'\b(bot|ea|expert advisor)\s+(çalıştır|başlat|bağla)\b'),
        re.compile(r'\b(gerçek para|canlı hesap)\s+(ile|üzerinde)\b'),
    ]

    # Kaynak kapıları: .md (findings_filter.py:92-94) + test dosyası (SERT-11)
    _BELGE_UZANTI = (".md", ".txt", ".rst")
    _TEST_KAYNAK = re.compile(
        r'(self_test|_test\.py|test_|/tests?/|örnek|ornek|kum[_ ]havuzu|sandbox|demo)')

    @classmethod
    def eleme_gerekcesi(cls, bulgu: Dict[str, Any]) -> Optional[str]:
        """İddia sert kurallarla elenmeli mi?

        Kaynak: findings_filter.py:81-131 get_exclusion_reason (bağlamsız kısım).
        Dönüş: elenecekse gerekçe string'i, aksi halde None.
        """
        # --- kaynak kapısı (<- .md kapısı, :91-94) -------------------------
        kaynak = _kucult(bulgu.get("kaynak"))
        if kaynak.endswith(cls._BELGE_UZANTI):
            return "İddia belge/anlatı dosyasından (motor çıktısı değil)"
        if kaynak and cls._TEST_KAYNAK.search(kaynak):
            return "Test/kum-havuzu kaynaklı iddia (gerçek koşu değil)"

        # --- metin birleşimi (<- :96-105, None yönetimi dahil) -------------
        aciklama = bulgu.get("evidence")
        if aciklama is None:
            aciklama = bulgu.get("kanit")
        baslik = bulgu.get("baslik")
        if baslik is None:
            baslik = bulgu.get("name")
        if aciklama is None:
            aciklama = ""
        if baslik is None:
            baslik = ""
        metin = _kucult(f"{baslik} {aciklama}")

        for desen in cls._GENEL_RISK_DESENLERI:
            if desen.search(metin):
                return "Genel felaket/tükenme iddiası (ölçüme bağlı değil, düşük sinyal)"

        for desen in cls._GENEL_TAVSIYE_DESENLERI:
            if desen.search(metin):
                return "Seviyesiz genel tavsiye (ölçülmüş seviye yok)"

        for desen in cls._ISLETIM_DESENLERI:
            if desen.search(metin):
                return "İşletim/bakım bulgusu (yön sinyali değil)"

        for desen in cls._DUSUK_ETKI_DESENLERI:
            if desen.search(metin):
                return "Düşük etkili / teorik mikro-yapı iddiası (ATR ölçeğinde anlamsız)"

        for desen in cls._KAPSAM_DISI_DESENLERI:
            if desen.search(metin):
                return "Kapsam dışı iddia (canlı/otomatik emir — bu depo yalnız karar-desteği)"

        return None


# ==========================================================================
# KATMAN 2 — BAĞLAM-DUYARLI KAPILAR
# Kaynak: findings_filter.py:133-143 (C/C++ kapısı) ve :145-152 (HTML kapısı)
# Oradaki mantık: desen ailesi KOŞULLUDUR — yalnız belirli bağlamda geçerli.
# ==========================================================================
class BaglamKapilari:
    """Bir iddia yalnız belirli rejim/kapsam/aile/tazelik bağlamında geçerlidir."""

    # <- _MEMORY_SAFETY_PATTERNS (:59-69): yalnız üretebilen yüzeyde geçerli
    _TUREV_DESENLERI: List[Pattern] = [
        re.compile(r'\b(açık faiz|acik faiz|open interest|\boi\b)\b'),
        re.compile(r'\b(funding|fonlama)\s*(oranı|rate)?\b'),
        re.compile(r'\b(cvd|kümülatif hacim delta|volume delta)\b'),
        re.compile(r'\b(taker\s*)?(lsr|long[/\s-]?short ratio)\b'),
        re.compile(r'\b(likidasyon|tasfiye|liquidation)\b'),
        re.compile(r'\b(deleveraging|kaldıraç boşal|pozisyon boşal)'),
    ]

    # <- _SSRF_PATTERNS (:77-79): tek desenli aile, tek koşullu kapı
    _SQUEEZE_DESENLERI: List[Pattern] = [
        re.compile(r'\b(squeeze|sıkışma tetiği|kaskad|cascade|taze short)\b'),
    ]

    @staticmethod
    def _metin(bulgu: Dict[str, Any]) -> str:
        return _kucult(f"{bulgu.get('baslik') or bulgu.get('name') or ''} "
                       f"{bulgu.get('evidence') or bulgu.get('kanit') or ''}")

    @staticmethod
    def _elle_okuma(bulgu: Dict[str, Any]) -> bool:
        return (bulgu.get("elle") is True
                or str(bulgu.get("name", "")) == "gorsel-teyit"
                or "elle" in _kucult(bulgu.get("_kaynak")))

    @classmethod
    def eleme_gerekcesi(cls, bulgu: Dict[str, Any],
                        baglam: Optional[Dict[str, Any]] = None) -> Optional[str]:
        baglam = baglam or {}
        metin = cls._metin(bulgu)
        ad = str(bulgu.get("name", ""))
        aile = AILE.get(ad)

        turev_iddiasi = any(d.search(metin) for d in cls._TUREV_DESENLERI)

        # --- KAPI 1a (<- C/C++ kapısı): iddiayı üretemeyen aile -----------
        # karar-motoru YALNIZ kline görür; OI/funding/CVD/likidasyona KÖRDÜR
        # (engine/README.md; turev_akis.py:4-8). Fiyat-yapısı ailesinden gelen
        # türev iddiası yapısal olarak imkânsızdır.
        if turev_iddiasi and aile in ("fiyat-yapisi", "tarihsel-kanit"):
            return (f"Türev iddiası '{aile}' ailesinden ({ad}) — bu motor türev "
                    "kanallarına kördür (yapısal olarak üretemez)")

        # --- KAPI 1b: türev iddiası ama okunan kapsam eşiğin altında -------
        kapsam = baglam.get("turev_kapsam")
        esik = KONVANSIYON["turev_kapsam_esigi"]
        if turev_iddiasi and isinstance(kapsam, (int, float)) and float(kapsam) < esik:
            return (f"Türev yön iddiası, kapsam {round(float(kapsam), 2)} < {esik} "
                    "(fail-closed: doğrulanmamış türev)")

        # --- KAPI 2a (<- HTML kapısı): squeeze/kaskad + rejim yatay --------
        # smc_tespit rejim.durum ∈ {trend, range, gecis, VERİ YOK}; ADX < adx_range
        # iken (range) sıkışma/kaskad bayrağı yönsel iddia taşıyamaz.
        rejim = baglam.get("rejim") or {}
        durum = _kucult(rejim.get("durum"))
        if durum == "range" and any(d.search(metin) for d in cls._SQUEEZE_DESENLERI):
            adx = rejim.get("adx")
            return (f"Squeeze/kaskad bayrağı RANGE rejiminde (adx={adx if adx is not None else YOK}) "
                    "— yönsel dayanağı yok")

        # --- KAPI 2b (<- SERT-13): dayandığı faktör okunamamış -------------
        if any(d.search(metin) for d in cls._SQUEEZE_DESENLERI):
            for f in (baglam.get("turev_faktorler") or []):
                if f.get("faktor") == "liquidation" and f.get("skor") is None:
                    return ("Kaskad/squeeze bayrağı ama likidasyon faktörü VERİ YOK "
                            "(dayanaksız bayrak)")

        # --- KAPI 3: elle okumanın tazeliği (damga) ------------------------
        if cls._elle_okuma(bulgu):
            tol = KONVANSIYON["damga_tolerans_dk"]
            damga = bulgu.get("zaman_utc")
            son_bar = baglam.get("son_bar_utc")
            if not damga:
                return (f"Damgasız elle okuma → BAYAT sayıldı (zaman_utc yok; "
                        f"tolerans {tol} dk)")
            yas = _yas_dk(damga, son_bar)
            if yas is None:
                return f"Damga çözümlenemedi ({damga}) → BAYAT (fail-closed)"
            if yas > tol:
                return (f"BAYAT elle okuma: son bardan {yas:.0f} dk eski "
                        f"(tolerans {tol} dk)")
        return None


def _zaman(s: Any) -> Optional[datetime]:
    if not s:
        return None
    t = str(s).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _yas_dk(damga: Any, son_bar: Any) -> Optional[float]:
    """Okumanın son bara göre yaşı (dakika). Referans yoksa şimdi kullanılır."""
    d = _zaman(damga)
    if d is None:
        return None
    ref = _zaman(son_bar) or datetime.now(timezone.utc)
    return (ref - d).total_seconds() / 60.0


# ==========================================================================
# KATMAN 3 — EMSAL DENETİMİ (emsaller/emsal_defteri.yaml)
# Kaynak karşılığı: Claude API eleme aşaması (findings_filter.py:255-306) —
# orada bir LLM, HARD EXCLUSIONS + PRECEDENTS metnini uygulardı. Burada aynı
# 33 madde DEFTERE yazılır ve makineyle koşulur (LLM yok → determinist).
# ==========================================================================
class EmsalDenetimi:
    def __init__(self, defter_yolu: Optional[Path] = None):
        self.yol = Path(defter_yolu or VARSAYILAN_DEFTER)
        self.emsaller: List[Dict[str, Any]] = []
        self.uyarilar: List[str] = []
        self._yukle()

    def _yukle(self) -> None:
        if yaml is None:
            self.uyarilar.append("yaml yok → emsal katmanı KAPALI (fail-closed)")
            return
        if not self.yol.exists():
            self.uyarilar.append(f"emsal defteri bulunamadı: {self.yol} → katman KAPALI")
            return
        veri = yaml.safe_load(self.yol.read_text(encoding="utf-8")) or {}
        self.emsaller = list(veri.get("emsaller") or [])
        for e in self.emsaller:
            k = e.get("kontrol")
            if isinstance(k, dict):
                for alan in ("desen", "istisna_desen"):
                    if k.get(alan):
                        k[f"_{alan}_c"] = re.compile(k[alan])

    # --- adlandırılmış yüklemler (defterdeki `kosul` alanı) ---------------
    @staticmethod
    def _kosul_saglandi(ad: str, bulgu: Dict[str, Any], metin: str,
                        guven: float) -> bool:
        if ad == "kaynak_motor":
            return bool(MOTOR_KAYNAK.search(str(bulgu.get("kaynak") or ""))
                        or AILE.get(str(bulgu.get("name", ""))) in
                        ("fiyat-yapisi", "turev-akis", "tarihsel-kanit"))
        if ad == "elle_kaynak":
            return BaglamKapilari._elle_okuma(bulgu)
        if ad == "guven_bandi_orta_sayisiz":
            orta = (KONVANSIYON["guven_orta_alt"] <= guven
                    <= KONVANSIYON["guven_orta_ust"])
            return orta and not re.search(r"\d", metin)
        return False

    def eleme_gerekcesi(self, bulgu: Dict[str, Any], guven: float,
                        baglam: Optional[Dict[str, Any]] = None) -> Optional[str]:
        metin = BaglamKapilari._metin(bulgu)

        # (a) güven bandı — claude_api_client.py:293 "1-3: Low confidence,
        #     likely false positive or noise" + findings_filter.py:283 gerekçesi
        if guven < KONVANSIYON["guven_dusuk_ust"]:
            return f"Düşük güven skoru: {round(guven, 2)} (1-3 bandı: gürültü)"

        # (b) defterdeki makine-denetlenebilir emsaller
        for e in self.emsaller:
            if e.get("uygulanamaz"):
                continue
            k = e.get("kontrol")
            if not isinstance(k, dict):
                continue
            desen = k.get("_desen_c")
            if desen is not None and not desen.search(metin):
                continue
            istisna = k.get("_istisna_desen_c")
            if istisna is not None and istisna.search(metin):
                continue
            kosul = k.get("kosul")
            if kosul and not self._kosul_saglandi(kosul, bulgu, metin, guven):
                continue
            if desen is None and not kosul:
                continue  # boş kontrol → hiçbir şeyi eleme (fail-closed)
            return f"{e['id']}: {k.get('eleme_gerekcesi') or e.get('kural')}"
        return None


# ==========================================================================
# GÜVEN — claude_api_client.py:292-295 (1-10 ölçeği) + sentez.py:88 (etkin ağırlık)
# ==========================================================================
def guven_10(bulgu: Dict[str, Any], uyarilar: List[str]) -> float:
    """İddianın 1-10 güven skoru.

    Ölçek kaynaktan: "Assign a confidence score from 1-10" (:292).
    Taban: danışmanın `confidence` (0..1) × 10.
    Doğrulanmamışsa sentez.py:88'in ETKİN AĞIRLIK aritmetiği uygulanır
    (eff = conf × refute_penalty) — kaynak burada fail-OPEN'dır (API hatasında
    10.0 verir, :271/:302); bu depo fail-closed olmak zorundadır (CLAUDE.md).
    """
    ham = bulgu.get("confidence", bulgu.get("guven"))
    if ham is None:
        uyarilar.append(f"{bulgu.get('name', '?')}: confidence VERİ YOK → "
                        "fail-closed taban 0.0 (kaynak fail-OPEN 10.0 verirdi)")
        ham = 0.0
    try:
        c = float(ham)
    except (TypeError, ValueError):
        c = 0.0
    c = min(max(c, 0.0), 1.0)

    # gorsel_tavan: elle görsel okuma ÖLÇÜM DEĞİLDİR (piramit.py:724-732)
    if BaglamKapilari._elle_okuma(bulgu) and c > KONVANSIYON["gorsel_tavan"]:
        uyarilar.append(f"{bulgu.get('name', '?')}: elle okuma güveni "
                        f"{KONVANSIYON['gorsel_tavan']} tavanıyla sınırlandı")
        c = KONVANSIYON["gorsel_tavan"]

    onaylı = bulgu.get("_verifier_confirmed")
    if onaylı is not True:
        c *= KONVANSIYON["refute_penalty"]
    return round(min(max(c * 10.0, 0.0), 10.0), 4)


# ==========================================================================
# ANA MOTOR — kaynak: findings_filter.py:157-343 (FindingsFilter)
# ==========================================================================
class ElemeMotoru:
    def __init__(self, sert: bool = True, baglam_kapilari: bool = True,
                 emsal: bool = True, defter_yolu: Optional[Path] = None):
        self.sert = sert
        self.baglam_kapilari = baglam_kapilari
        self.emsal_acik = emsal
        self.emsal = EmsalDenetimi(defter_yolu) if emsal else None

    @staticmethod
    def _dagilim(ist: ElemeIstatistigi, gerekce: str) -> None:
        # kaynak: findings_filter.py:246 -> key = reason.split('(')[0].strip()
        anahtar = gerekce.split("(")[0].strip()
        ist.eleme_dagilimi[anahtar] = ist.eleme_dagilimi.get(anahtar, 0) + 1

    def ele(self, bulgular: List[Dict[str, Any]],
            baglam: Optional[Dict[str, Any]] = None
            ) -> Tuple[bool, Dict[str, Any], ElemeIstatistigi]:
        """İddiaları ele. Dönüş: (basari, sonuc, istatistik).

        Kaynak imzası: filter_findings -> Tuple[bool, Dict, FilterStats] (:197-199).
        """
        t0 = time.time()
        baglam = baglam or {}
        uyarilar: List[str] = list(self.emsal.uyarilar) if self.emsal else []

        if not bulgular:  # <- findings_filter.py:211-222 (boş girdi erken dönüş)
            ist = ElemeIstatistigi(toplam_bulgu=0, sure_saniye=0.0)
            return True, {"tutulan_bulgular": [], "elenen_bulgular": [],
                          "ozet": {"toplam_bulgu": 0, "tutulan": 0, "elenen": 0,
                                   "eleme_dagilimi": {}},
                          "uyarilar": uyarilar,
                          "not": "Girdi boş — eleme yapılmadı."}, ist

        ist = ElemeIstatistigi(toplam_bulgu=len(bulgular))
        tutulan: List[Dict[str, Any]] = []
        elenen: List[Dict[str, Any]] = []

        for i, bulgu in enumerate(bulgular):
            # --- Katman 1 ---------------------------------------------------
            if self.sert:
                g = SertElemeKurallari.eleme_gerekcesi(bulgu)
                if g:
                    elenen.append({"bulgu": bulgu, "sira": i, "eleme_gerekcesi": g,
                                   "katman": "1-sert-kural"})
                    ist.sert_elenen += 1
                    self._dagilim(ist, g)
                    continue

            # --- Katman 2 ---------------------------------------------------
            if self.baglam_kapilari:
                g = BaglamKapilari.eleme_gerekcesi(bulgu, baglam)
                if g:
                    elenen.append({"bulgu": bulgu, "sira": i, "eleme_gerekcesi": g,
                                   "katman": "2-baglam-kapisi"})
                    ist.baglam_elenen += 1
                    self._dagilim(ist, g)
                    continue

            # --- Güven (1-10) ----------------------------------------------
            guven = guven_10(bulgu, uyarilar)
            ist.guven_skorlari.append(guven)

            # --- Katman 3 ---------------------------------------------------
            if self.emsal is not None:
                g = self.emsal.eleme_gerekcesi(bulgu, guven, baglam)
                if g:
                    elenen.append({"bulgu": bulgu, "sira": i, "guven_skoru": guven,
                                   "eleme_gerekcesi": g, "katman": "3-emsal"})
                    ist.emsal_elenen += 1
                    self._dagilim(ist, g)
                    continue

            zengin = dict(bulgu)
            zengin["_eleme_verisi"] = {
                "guven_skoru": guven,
                "gerekce": "3 katmandan da geçti",
                "aile": AILE.get(str(bulgu.get("name", ""))) or YOK,
            }
            tutulan.append(zengin)
            ist.tutulan += 1

        ist.sure_saniye = time.time() - t0
        ort = (sum(ist.guven_skorlari) / len(ist.guven_skorlari)
               if ist.guven_skorlari else None)
        sonuc = {
            "tutulan_bulgular": tutulan,
            "elenen_bulgular": elenen,
            "ozet": {
                "toplam_bulgu": ist.toplam_bulgu,
                "tutulan": ist.tutulan,
                "elenen": len(elenen),
                "sert_elenen": ist.sert_elenen,
                "baglam_elenen": ist.baglam_elenen,
                "emsal_elenen": ist.emsal_elenen,
                "eleme_dagilimi": ist.eleme_dagilimi,
                "ortalama_guven": round(ort, 4) if ort is not None else None,
                "sure_saniye": round(ist.sure_saniye, 4),
            },
            "uyarilar": uyarilar,
            "esik_kaynagi": (
                "eşikler DEPODAKİ motorlardan tek-kaynak: turev kapsam_esigi=0.5 "
                "(turev_akis.py), gorsel_tavan=0.50 ve damga toleransı=240dk "
                "(piramit.py), refute_penalty=0.25 (sentez.py), güven bantları "
                "1-3/4-6/7-10 (claude_api_client.py:292-295)"),
            "varsayimlar": [
                "Eleme bir KARAR değildir; yalnız gürültü ayıklar (yön hükmü sentez.py'den).",
                "Elenen her iddia gerekçesiyle raporlanır (sessiz kayıp yasak).",
                "confidence yoksa fail-closed 0.0 alınır (kaynak fail-OPEN 10.0 verirdi).",
                "Emsal katmanı yalnız defterde `kontrol` bloğu olan maddeleri makineyle "
                "koşar; geri kalanı defter kaydıdır (elle ikinci-göz).",
            ],
            "not": "Karar-destek çıktısıdır. Canlı/otomatik emir DAHİL DEĞİL.",
        }
        return True, sonuc, ist


# ==========================================================================
# ÖZ-TEST
# ==========================================================================
def _self_test() -> int:
    baglam_dar = {
        "rejim": {"durum": "range", "adx": 14.2, "yuksek_vol": False},
        "turev_kapsam": 0.30,
        "turev_faktorler": [{"faktor": "liquidation", "skor": None}],
        "son_bar_utc": "2026-07-28T12:00:00Z",
    }
    baglam_genis = {
        "rejim": {"durum": "trend", "adx": 31.4, "yuksek_vol": True},
        "turev_kapsam": 0.85,
        "turev_faktorler": [{"faktor": "liquidation", "skor": -0.8}],
        "son_bar_utc": "2026-07-28T12:00:00Z",
    }

    vakalar: List[Tuple[str, Dict[str, Any], Dict[str, Any], str]] = [
        ("V01 temiz motor iddiası",
         {"name": "karar-motoru", "stance": "long", "confidence": 0.70,
          "kaynak": "engine/karar_motoru.py", "_verifier_confirmed": True,
          "evidence": "zincir-1 kurulum: giriş 65890, stop 65210, T1 67250, R 1.62, ATR15 218"},
         baglam_genis, "TUTULDU"),
        ("V02 belge kaynağı (.md kapısı)",
         {"name": "grafik-calisma", "stance": "short", "confidence": 0.6,
          "kaynak": "docs/notlar.md", "_verifier_confirmed": True,
          "evidence": "4h yapı ayı, CHoCH 66120"},
         baglam_genis, "1-sert-kural"),
        ("V03 genel felaket iddiası",
         {"name": "grafik-calisma", "stance": "short", "confidence": 0.8,
          "kaynak": "smc_tespit.py", "_verifier_confirmed": True,
          "evidence": "Piyasa çökebilir, likidite kuruyabilir"},
         baglam_genis, "1-sert-kural"),
        ("V04 seviyesiz genel tavsiye",
         {"name": "risk-yonetimi", "stance": "flat", "confidence": 0.5,
          "kaynak": "risk.py", "_verifier_confirmed": True,
          "evidence": "Risk yönetimi uygulanmalı, pozisyon küçültülmeli"},
         baglam_genis, "1-sert-kural"),
        ("V05 işletim bulgusu",
         {"name": "turev-akis", "stance": "short", "confidence": 0.7,
          "kaynak": "turev_akis.py", "_verifier_confirmed": True,
          "evidence": "Binance ucu erisilemedi, bağlantı koptu"},
         baglam_genis, "1-sert-kural"),
        ("V06 kapsam dışı (canlı emir)",
         {"name": "karar-motoru", "stance": "long", "confidence": 0.9,
          "kaynak": "engine/karar_motoru.py", "_verifier_confirmed": True,
          "evidence": "Canlı emir gönderilsin, bot çalıştır"},
         baglam_genis, "1-sert-kural"),
        ("V07 düşük etkili/teorik",
         {"name": "grafik-calisma", "stance": "long", "confidence": 0.6,
          "kaynak": "smc_tespit.py", "_verifier_confirmed": True,
          "evidence": "Teorik olarak tek fitil gürültüsü stopu alabilir"},
         baglam_genis, "1-sert-kural"),
        ("V08 türev iddiası, kapsam düşük (KAPI 1b)",
         {"name": "turev-akis", "stance": "short", "confidence": 0.62,
          "kaynak": "turev_akis.py", "_verifier_confirmed": True,
          "evidence": "Açık faiz %2.1 arttı, funding pozitif; ayı baskısı"},
         baglam_dar, "2-baglam-kapisi"),
        ("V09 türev iddiası fiyat-yapısı ailesinden (KAPI 1a)",
         {"name": "grafik-calisma", "stance": "short", "confidence": 0.75,
          "kaynak": "smc_tespit.py", "_verifier_confirmed": True,
          "evidence": "CVD düşüyor ve likidasyon dengesizliği ayı gösteriyor"},
         baglam_genis, "2-baglam-kapisi"),
        ("V10 squeeze bayrağı RANGE rejiminde (KAPI 2a)",
         {"name": "backtest-motoru", "stance": "long", "confidence": 0.66,
          "kaynak": "backtest.py", "_verifier_confirmed": True,
          "evidence": "Yukarı squeeze ihtimali yüksek, sıkışma tetiği hazır"},
         baglam_dar, "2-baglam-kapisi"),
        ("V11 bayat elle görsel okuma (KAPI 3)",
         {"name": "gorsel-teyit", "stance": "long", "confidence": 0.5,
          "kaynak": "engine/girdi/gorsel_okuma.json", "elle": True,
          "zaman_utc": "2026-07-27T12:00:00Z", "_verifier_confirmed": True,
          "evidence": "Göz: 4h bull yapı, 65200 destek tepkisi"},
         baglam_genis, "2-baglam-kapisi"),
        ("V12 doğrulanmamış → düşük güven bandı",
         {"name": "backtest-motoru", "stance": "long", "confidence": 0.60,
          "kaynak": "backtest.py",
          "evidence": "PF 1.8, MC p50 pozitif, 240 işlem"},
         baglam_genis, "3-emsal"),
        ("V13 EMSAL-11 orta güven + sayısız kanıt",
         {"name": "grafik-calisma", "stance": "long", "confidence": 0.55,
          "kaynak": "confluence.py", "_verifier_confirmed": True,
          "evidence": "Yapı boğa görünüyor, akış olumlu, kurulum makul"},
         baglam_genis, "3-emsal"),
        ("V14 EMSAL-04 motor değerine 'manipüle edilebilir' itirazı",
         {"name": "karar-motoru", "stance": "flat", "confidence": 0.8,
          "kaynak": "engine/karar_motoru.py", "_verifier_confirmed": True,
          "evidence": "ATR 218 ve ADX 31 değerleri manipüle edilebilir, güvenilmez"},
         baglam_genis, "3-emsal"),
        ("V15 temiz türev iddiası (kapsam yeterli)",
         {"name": "turev-akis", "stance": "short", "confidence": 0.71,
          "kaynak": "turev_akis.py", "_verifier_confirmed": True,
          "evidence": "OI %2.4 arttı + fiyat düştü → taze short; funding %0.041; skor -0.52"},
         baglam_genis, "TUTULDU"),
        ("V16 test kaynağı",
         {"name": "karar-motoru", "stance": "long", "confidence": 0.9,
          "kaynak": ".claude/skills/piramit-sistem/scripts/self_test.py",
          "_verifier_confirmed": True, "evidence": "R 2.10 kurulum, giriş 100"},
         baglam_genis, "1-sert-kural"),
    ]

    motor = ElemeMotoru()
    if motor.emsal is not None and not motor.emsal.emsaller:
        print("HATA: emsal defteri yüklenemedi:", motor.emsal.uyarilar)
        return 1

    gecen = 0
    for ad, bulgu, baglam, beklenen in vakalar:
        _, sonuc, _ = motor.ele([bulgu], baglam)
        if sonuc["tutulan_bulgular"]:
            gercek, gerekce = "TUTULDU", "3 katmandan da geçti"
        else:
            e = sonuc["elenen_bulgular"][0]
            gercek, gerekce = e["katman"], e["eleme_gerekcesi"]
        ok = gercek == beklenen
        gecen += ok
        print(f"  [{'OK ' if ok else 'HATA'}] {ad}\n"
              f"        beklenen={beklenen} gerçek={gercek}\n"
              f"        gerekçe : {gerekce}")

    print(f"\n  {gecen}/{len(vakalar)} vaka geçti")

    # Toplu koşu — istatistik dökümü
    print("\n" + "=" * 74)
    print("TOPLU KOŞU (16 iddia birlikte, baglam=geniş)")
    print("=" * 74)
    _, sonuc, ist = motor.ele([v[1] for v in vakalar], baglam_genis)
    print(ist.dokum())
    print(f"\n  tutulan iddialar: {[b['name'] for b in sonuc['tutulan_bulgular']]}")
    if sonuc["uyarilar"]:
        print("  uyarılar:")
        for u in sonuc["uyarilar"]:
            print(f"    - {u}")

    # Alan sözleşmesi: FilterStats'ın 7 alanı karşılanmış mı?
    zorunlu = ["toplam_bulgu", "sert_elenen", "emsal_elenen", "tutulan",
               "eleme_dagilimi", "guven_skorlari", "sure_saniye"]
    eksik = [a for a in zorunlu if not hasattr(ist, a)]
    print(f"\n  FilterStats 7 alan karşılığı: "
          f"{'TAM' if not eksik else 'EKSİK ' + str(eksik)}")

    tamam = (gecen == len(vakalar)) and not eksik
    print("\n" + ("ÖZ-TEST GEÇTİ" if tamam else "ÖZ-TEST BAŞARISIZ"))
    return 0 if tamam else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Eleme motoru — danışman/motor iddialarını 3 katmanda eler")
    ap.add_argument("--job", help="JSON iş dosyası: {'bulgular':[...], 'baglam':{...}}")
    ap.add_argument("--defter", help="emsal_defteri.yaml yolu (varsayılan: beceri içi)")
    ap.add_argument("--self-test", action="store_true", help="öz-test koş")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()
    if not args.job:
        ap.error("--job ya da --self-test gerekli")

    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    motor = ElemeMotoru(defter_yolu=Path(args.defter) if args.defter else None)
    _, sonuc, ist = motor.ele(job.get("bulgular") or [], job.get("baglam") or {})
    sonuc["istatistik"] = {
        "toplam_bulgu": ist.toplam_bulgu, "sert_elenen": ist.sert_elenen,
        "baglam_elenen": ist.baglam_elenen, "emsal_elenen": ist.emsal_elenen,
        "tutulan": ist.tutulan, "eleme_dagilimi": ist.eleme_dagilimi,
        "guven_skorlari": ist.guven_skorlari,
        "sure_saniye": round(ist.sure_saniye, 4),
    }
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
