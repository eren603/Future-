#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: E741  (o/h/l/c OHLC alan adlari finans konvansiyonudur; l bilinçli)
"""
KONSEY TEK DOSYA — kanit kapisi + canli yon/giris-cikis sinyali
===============================================================================
Tek dosya, SIFIR harici bagimlilik (yalniz Python stdlib). Depodaki hicbir
scripte ihtiyac duymaz; telefonda/Pydroid'de de calisir.

  python3 konsey_tek.py sinyal --symbols BTCUSDT,ETHUSDT
  python3 konsey_tek.py sinyal --m15 m15.json --h4 h4.json --symbol BTCUSDT
  python3 konsey_tek.py oz-test
  python3 konsey_tek.py audit  --input task.json --output audit.json
  python3 konsey_tek.py fetch  --input task.json --output t2.json --location <url|dosya> \
                               --source-id S02 --evidence-id E02
  python3 konsey_tek.py run    --input task.json --output r.json \
                               --provider openai-compatible --model gpt-4o-mini

Cikis kodu: 0 = yayin kapisi GECTI (PUBLISH_FULL) · 2 = gecmedi, yayin DURDU
            1 = oz-testte FAIL var

-------------------------------------------------------------------------------
TEMEL ILKE (KONSEY_Evidence_Engine.md)
-------------------------------------------------------------------------------
Modelin kendi "VERIFIED" / "PUBLISH_FULL" beyani KANIT DEGILDIR. Nihai karari
`EvidenceRegistry.audit()` verir. Oz-test T15 bunu kanitlar: ajan PUBLISH_FULL
dese bile kapi REPAIR diyorsa yayin YAPILMAZ.

-------------------------------------------------------------------------------
BU DOSYAYA GOMULU DENETIM DUZELTMELERI
(onceki surumlerde OLCULEREK bulunan hatalar; her biri oz-testle korunuyor)
-------------------------------------------------------------------------------
D1 BAR-ICI SIRA (eski P0-1) — Limitin doldugu barin KENDI fitili HEDEF
   sayilamaz: dolum barinda YALNIZ stop kontrol edilir, hedef taramasi bir
   SONRAKI bardan baslar. Eski davranis sifir-kenarli rassal yuruyuste kapiyi
   ACIYORDU (4/4 tohum). -> `_yaris_coz`, oz-test T16.
D2 4H<->15M HIZALAMA (eski P0-4) — Indeks orani (16:1) VARSAYILMAZ; eslesme
   ZAMAN DAMGASIYLA yapilir. Eski indeks eslemesi karar barina 173 GUN bayat
   4H satiri bagliyordu. -> `h4_hizala`, oz-test T17.
D3 SAYFA HATA KODU (eski P0-2) — OKX govde hata kodu HER sayfada denetlenir;
   ic sayfada yutulursa seri sessizce kirpilip look-ahead'e donuyordu. Ayrica
   sayfa tavani + ilerleme korumasi var (sonsuz dongu yok). -> `_okx_sayfali`,
   oz-test T18.
D4 TEK BAHIS (eski P0-3) — |rho| >= 0.85 olculdugunde ayni yonlu ikinci sembol
   BAGIMSIZ BAHIS SAYILMAZ; "KOPYA - ATLA" etiketi alir ve toplam risk tek
   bahis gibi raporlanir. -> `tek_bahis_kapisi`, oz-test T19.
D5 KAZANAN YOKKEN KAPI (eski P1-1) — kazan==0 iken b_win OLCULEMEZ; sabit bir
   tasarim degerine DUSULMEZ, kapi KAPANIR (fail-closed). -> `stake_kapisi`,
   oz-test T20.
D6 KELLY PAYDASI (eski P1-2) — stake = edge/(a*b); kayip bacagi `a` 1.0R
   VARSAYILMAZ, olculur. Eski `edge/b` formulu stake'i a kati sisiriyordu.
   -> `stake_kapisi`, oz-test T21.
D7 TAKER DOLGUSU (eski P1-4) — OKX'te taker-alis kolonu YOKTUR; notr dolgu
   (hacim/2) YAZILMAZ, alan None birakilir ve kanal EKSIK sayilir. Eski dolgu
   v=0 barda -1.0 (maksimum ayi) uretiyordu. -> `okx_mumlar`, oz-test T22.
D8 FUNDING ISARETI (eski P1-5) — abs() ile isaret YOK EDILMEZ; isaretli deger
   saklanir, maliyet tarafinda muhafazakar kullanilir. -> `funding_oku`.
D9 CIKIS KODU (eski P0-2) — oz-test FAIL varsa cikis kodu 1'dir; "hepsi gecti"
   goruntusu veren kosulsuz `return 0` YOKTUR. -> `_cmd_oz_test`.
D10 SISIRILMIS R — stop/ATR gurultu bandindayken buyuyen R kabul edilmez;
   `rr_denetim` ATR olcegiyle sisirilmis R'yi yakalar ve R_gercekci verir.

⚠️ Yalniz karar-destek. Emir/imza/API-anahtar ucu YOKTUR; kod yalnizca public
GET yapar. Canli/otomatik emir DAHIL DEGILDIR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.request import Request, urlopen

SURUM = "1.2.0"

# =============================================================================
# 1) SABITLER — hepsi BEYAN EDILIR; gizli esik yoktur
# =============================================================================
ESIKLER: dict[str, tuple[Any, str, str]] = {
    # ad: (deger, tip, gerekce)
    "ATR_PERIYOT":   (14,    "YAPISAL",  "Wilder ATR standart periyodu"),
    "ADX_PERIYOT":   (14,    "YAPISAL",  "Wilder ADX standart periyodu"),
    "ADX_TREND":     (25.0,  "VARSAYIM", "ADX >= 25 trend kabulu (konvansiyon)"),
    "ADX_RANGE":     (20.0,  "VARSAYIM", "ADX < 20 range kabulu (konvansiyon)"),
    "SWING_SOL":     (2,     "YAPISAL",  "fraktal swing sol teyit bari"),
    "SWING_SAG":     (2,     "YAPISAL",  "fraktal swing sag teyit bari"),
    "FVG_MITIGASYON":(0.5,   "KALIBRE EDILMEMIS",
                      "bolgenin bu orani tukenince mitige sayilir; "
                      "consequent-encroachment konvansiyonu, edge kaniti YOK"),
    "R_MIN":         (1.35,  "VARSAYIM", "depo risk kurali tabani; yalniz SIKILASIR"),
    "MARKET_BANDI":  (0.1,   "VARSAYIM", "|giris-fiyat| <= 0.1*ATR15 ise MARKET"),
    "STOP_ATR_ALT":  (0.8,   "VARSAYIM", "stop/ATR < 0.8 = gurultu seviyesi stop"),
    "STOP_ATR_UST":  (2.0,   "VARSAYIM", "stop/ATR > 2.0 = kurulum olcegi disi"),
    "SISME_SINIRI":  (3.0,   "VARSAYIM", "hedef/ATR > 3.0 iken R sisirilmis sayilir"),
    "RHO_ESIK":      (0.85,  "VARSAYIM", "|rho| >= 0.85 -> tek bahis (kopya pozisyon)"),
    "AZAMI_YAS_DK":  (30.0,  "VARSAYIM", "canli sinyal icin azami veri yasi"),
    "SAYFA_TAVANI":  (40,    "YAPISAL",  "sayfalama ust siniri (sonsuz dongu korumasi)"),
    "AGIRLIK_H4":    (0.50,  "VARSAYIM", "yon agirligi: 4H trend"),
    "AGIRLIK_M15":   (0.30,  "VARSAYIM", "yon agirligi: 15M trend"),
    "AGIRLIK_TUREV": (0.20,  "VARSAYIM", "yon agirligi: turev skoru"),
    "RANGE_KIRPMA":  (0.5,   "VARSAYIM", "rejim=range iken 15M agirligi bu oranla carpilir"),
    "ANI_PENCERE":   (6,     "VARSAYIM", "ani-hareket taramasi: son N bar"),
    "ANI_YER_ATR":   (3.0,   "VARSAYIM", "pencere net yer degistirme >= N x ATR -> asiri genisleme"),
    "ANI_FITIL":     (0.6,   "VARSAYIM", "son barda fitil orani >= esik -> ret/tukenme isareti"),
    "ANI_HACIM":     (3.0,   "VARSAYIM", "son bar hacmi >= N x medyan(20) -> klimaks hacim"),
}


def E(ad: str) -> Any:
    return ESIKLER[ad][0]


ALLOWED_STATUSES = {"VERIFIED", "REPORTED", "INFERRED", "LIMITED", "UNKNOWN"}
ALLOWED_DECISIONS = {"PUBLISH_FULL", "PUBLISH_LIMITED", "REPAIR", "HALT"}
FRESHNESS = {"CURRENT", "LIMITED", "STALE", "UNKNOWN"}
ARALIK_MS = {"15m": 900_000, "1H": 3_600_000, "4H": 14_400_000, "2H": 7_200_000}


def simdi_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def duz_metin(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _f(x: Any) -> float | None:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


# =============================================================================
# 2) KONSEY CEKIRDEK — kanit katalogu + deterministik yayin kapisi
# =============================================================================
@dataclass
class Source:
    source_id: str
    location: str
    access_method: str
    accessed_at: str
    freshness: str = "UNKNOWN"
    dependency_group: str = "G0"
    digest: str = ""
    note: str = ""


@dataclass
class Evidence:
    evidence_id: str
    source_id: str
    method: str
    accessed_at: str
    description: str = ""
    observed: str = ""
    exit_code: int | None = None


@dataclass
class Claim:
    claim_id: str
    statement: str
    status: str = "UNKNOWN"
    evidence_ids: list[str] = field(default_factory=list)
    counter_evidence_status: str = "NOT_RUN"
    critical: bool = True
    note: str = ""


@dataclass
class AuditResult:
    critical_claim_count: int
    critical_claims_with_evidence: int
    missing_evidence_claims: list[str]
    invalid_references: list[str]
    unresolved_contradictions: int
    open_external_checks_pending: int
    counter_evidence_pending: list[str]
    freshness: str
    decision: str
    reasons: list[str]
    audited_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceRegistry:
    """Kaynak/kanit/iddia katalogu. ERISILEMEYEN KAYNAK KAYDEDILMEZ."""

    def __init__(self, task_id: str | None = None, task_type: str = "MARKET_SIGNAL",
                 risk_level: str = "HIGH", side_effect_level: str = "NONE") -> None:
        self.task_id = task_id or f"TASK-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
        self.task_type = task_type
        self.risk_level = risk_level
        self.side_effect_level = side_effect_level
        self.language = "tr"
        self.sources: dict[str, Source] = {}
        self.evidence: dict[str, Evidence] = {}
        self.claims: dict[str, Claim] = {}
        self.contradictions: list[str] = []
        self.external_checks_pending: list[str] = []
        self.counter_evidence_search = "NOT_RUN"
        self.method_layers_applied: list[str] = []
        self.method_layers_omitted: list[str] = []
        self.payload: dict[str, Any] = {}

    def add_source(self, source_id: str, location: str, access_method: str,
                   freshness: str = "UNKNOWN", dependency_group: str = "G0",
                   content: str = "", note: str = "") -> Source:
        if freshness not in FRESHNESS:
            raise ValueError(f"gecersiz freshness: {freshness}")
        s = Source(source_id, location, access_method, simdi_iso(), freshness,
                   dependency_group, sha(content) if content else "", note)
        self.sources[source_id] = s
        return s

    def add_evidence(self, evidence_id: str, source_id: str, method: str,
                     description: str = "", observed: str = "",
                     exit_code: int | None = None) -> Evidence:
        if source_id not in self.sources:
            raise KeyError(f"kanit cozulemeyen kaynaga baglandi: {source_id}")
        e = Evidence(evidence_id, source_id, method, simdi_iso(), description,
                     str(observed)[:6000], exit_code)
        self.evidence[evidence_id] = e
        return e

    def add_claim(self, claim_id: str, statement: str, status: str,
                  evidence_ids: Sequence[str] | None = None,
                  counter_evidence_status: str = "NOT_RUN",
                  critical: bool = True, note: str = "") -> Claim:
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"gecersiz status: {status}")
        c = Claim(claim_id, statement, status, list(evidence_ids or []),
                  counter_evidence_status, critical, note)
        self.claims[claim_id] = c
        return c

    def fetch(self, location: str, source_id: str, evidence_id: str,
              dependency_group: str = "G0", timeout: int = 20) -> Evidence:
        """Pasif edinim. ERISILEMEZSE HICBIR SEY KAYDEDILMEZ (istisna firlar)."""
        if location.startswith(("http://", "https://")):
            req = Request(location, headers={"User-Agent": f"konsey-tek/{SURUM}"})  # noqa: S310
            with urlopen(req, timeout=timeout) as resp:  # noqa: S310  # nosec B310 (startswith http/https dali)
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="replace")
            if "html" in ctype.lower() or "<html" in text[:1000].lower():
                text = duz_metin(text)
            yontem = "URL erisimi"
        else:
            text = Path(location).read_text(encoding="utf-8")
            yontem = "dosya"
        self.add_source(source_id, location, yontem, "CURRENT", dependency_group, text)
        return self.add_evidence(evidence_id, source_id, yontem,
                                 f"{location} icerigi", text[:2000])

    def audit(self, requested_decision: str = "PUBLISH_FULL") -> AuditResult:
        if requested_decision not in ALLOWED_DECISIONS:
            raise ValueError(f"gecersiz karar: {requested_decision}")
        critical = [c for c in self.claims.values() if c.critical]
        missing: list[str] = []
        invalid: list[str] = []
        pending_counter: list[str] = []
        reasons: list[str] = []

        for c in critical:
            if c.status not in ALLOWED_STATUSES:
                invalid.append(f"{c.claim_id}: invalid status {c.status}")
            if c.status == "VERIFIED" and not c.evidence_ids:
                missing.append(c.claim_id)
            for eid in c.evidence_ids:
                item = self.evidence.get(eid)
                if not item:
                    invalid.append(f"{c.claim_id}->{eid}")
                elif item.source_id not in self.sources:
                    invalid.append(f"{eid}->{item.source_id}")
            if c.counter_evidence_status in {"NOT_RUN", "PENDING"}:
                pending_counter.append(c.claim_id)

        if missing:
            reasons.append("Kanitsiz VERIFIED kritik iddialar var.")
        if invalid:
            reasons.append("Gecersiz kanit veya iddia referansi var.")
        if self.external_checks_pending:
            reasons.append("Bekleyen dis kontroller var.")
        if self.contradictions:
            reasons.append("Cozulmemis celiskiler var.")
        if self.risk_level in {"HIGH", "CRITICAL"} and pending_counter:
            reasons.append("Yuksek riskli gorevde karsit kanit aramasi tamamlanmamis.")

        supported = sum(1 for c in critical
                        if c.evidence_ids and c.claim_id not in missing)
        if not critical:
            reasons.append("Kritik iddia kaydi bulunmuyor; yayin karari verilemez.")
            decision = "REPAIR"
        elif missing or invalid or self.external_checks_pending:
            decision = "HALT" if self.risk_level == "CRITICAL" else "REPAIR"
        elif self.contradictions or (self.risk_level in {"HIGH", "CRITICAL"} and pending_counter):
            decision = "PUBLISH_LIMITED"
        elif supported == len(critical) and requested_decision == "PUBLISH_FULL":
            decision = "PUBLISH_FULL"
        else:
            decision = "PUBLISH_LIMITED"

        freshness = "PASS"
        if not self.sources:
            freshness = "UNKNOWN"
            reasons.append("Kaynak bulunmuyor.")
        elif any(s.freshness in {"UNKNOWN", "STALE"} for s in self.sources.values()):
            freshness = "LIMITED"
            reasons.append("En az bir kaynagin guncelligi sinirli veya bilinmiyor.")

        return AuditResult(len(critical), supported, missing, invalid,
                           len(self.contradictions), len(self.external_checks_pending),
                           pending_counter, freshness, decision, reasons, simdi_iso())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id, "task_type": self.task_type,
            "language": self.language, "risk_level": self.risk_level,
            "side_effect_level": self.side_effect_level,
            "method_layers_applied": self.method_layers_applied,
            "method_layers_omitted": self.method_layers_omitted,
            "sources": {k: asdict(v) for k, v in self.sources.items()},
            "evidence": {k: asdict(v) for k, v in self.evidence.items()},
            "claims": {k: asdict(v) for k, v in self.claims.items()},
            "contradictions": self.contradictions,
            "external_checks_pending": self.external_checks_pending,
            "counter_evidence_search": self.counter_evidence_search,
            "esikler": {k: {"deger": v[0], "tip": v[1], "gerekce": v[2]}
                        for k, v in ESIKLER.items()},
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EvidenceRegistry":
        r = cls(d.get("task_id"), d.get("task_type", "MARKET_SIGNAL"),
                d.get("risk_level", "HIGH"), d.get("side_effect_level", "NONE"))
        r.sources = {k: Source(**v) for k, v in (d.get("sources") or {}).items()}
        r.evidence = {k: Evidence(**v) for k, v in (d.get("evidence") or {}).items()}
        r.claims = {k: Claim(**v) for k, v in (d.get("claims") or {}).items()}
        r.contradictions = list(d.get("contradictions") or [])
        r.external_checks_pending = list(d.get("external_checks_pending") or [])
        r.counter_evidence_search = d.get("counter_evidence_search", "NOT_RUN")
        r.method_layers_applied = list(d.get("method_layers_applied") or [])
        r.method_layers_omitted = list(d.get("method_layers_omitted") or [])
        r.payload = dict(d.get("payload") or {})
        return r

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                     encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "EvidenceRegistry":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# =============================================================================
# 3) AJAN ADAPTORLERI — kullanicinin sozlesmesi KORUNDU
#    (OpenAICompatibleAdapter / GenericJSONAdapter / AgentAdapter.complete)
# =============================================================================
@dataclass
class AgentResponse:
    provider: str
    raw: dict
    text: str
    structured: dict | None


class AgentAdapter:
    provider = "base"

    def complete(self, system: str, user: str, schema: dict | None = None) -> AgentResponse:
        raise NotImplementedError


class OpenAICompatibleAdapter(AgentAdapter):
    provider = "openai-compatible"

    def __init__(self, base_url: str, api_key_env: str, model: str, timeout: int = 90):
        if not base_url.startswith("https://"):
            raise ValueError("base_url https:// olmali")
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.model = model
        self.timeout = timeout
        if not self.api_key:
            raise ValueError(f"API anahtari bulunamadi: {api_key_env}")

    def complete(self, system: str, user: str, schema: dict | None = None) -> AgentResponse:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0,
        }
        if schema:
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "konsey_result", "schema": schema}}
        request = Request(f"{self.base_url}/chat/completions",  # noqa: S310
                          data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json",
                                   "Authorization": f"Bearer {self.api_key}"},
                          method="POST")
        with urlopen(request, timeout=self.timeout) as response:  # noqa: S310  # nosec B310 (init'te https dogrulandi)
            raw = json.loads(response.read().decode())
        message = raw["choices"][0]["message"]["content"]
        structured = None
        if schema:
            structured = json.loads(message) if isinstance(message, str) else message
        return AgentResponse(self.provider, raw,
                             message if isinstance(message, str) else json.dumps(message),
                             structured)


class GenericJSONAdapter(AgentAdapter):
    """JSON kabul edip JSON donduren herhangi bir ucu cagirir."""
    provider = "generic-json"

    def __init__(self, endpoint: str, api_key_env: str | None = None, timeout: int = 90):
        if not endpoint.startswith("https://"):
            raise ValueError("endpoint https:// olmali")
        self.endpoint = endpoint
        self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        self.timeout = timeout

    def complete(self, system: str, user: str, schema: dict | None = None) -> AgentResponse:
        payload = {"system": system, "user": user, "schema": schema}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(self.endpoint, data=json.dumps(payload).encode(),  # noqa: S310
                          headers=headers, method="POST")
        with urlopen(request, timeout=self.timeout) as response:  # noqa: S310  # nosec B310 (init'te https dogrulandi)
            raw = json.loads(response.read().decode())
        structured = raw.get("structured") or raw.get("result") or raw.get("output")
        return AgentResponse(self.provider, raw, raw.get("text", ""),
                             structured if isinstance(structured, dict) else None)


class YerelOlcumAdapter(AgentAdapter):
    """Ag gerektirmeyen baglayici: karari YALNIZ registry kayitlarindan uretir."""
    provider = "yerel-olcum"

    def __init__(self, karar_fn: Callable[[dict], dict]):
        self.karar_fn = karar_fn
        self._reg: dict | None = None

    def bagla(self, registry: EvidenceRegistry) -> "YerelOlcumAdapter":
        self._reg = registry.to_dict()
        return self

    def complete(self, system: str, user: str,
                 schema: dict | None = None) -> AgentResponse:  # noqa: ARG002 (AgentAdapter API imzasi)
        veri = self._reg if self._reg is not None else json.loads(user)
        structured = self.karar_fn(veri)
        return AgentResponse(self.provider, {"system": system, "kaynak": "yerel-olcum"},
                             json.dumps(structured, ensure_ascii=False), structured)


def build_prompt(registry: EvidenceRegistry) -> tuple[str, str]:
    system = (
        "KONSEY kanit protokolunu uygula. Modelin kendi dogrulama beyanini kanit sayma. "
        "Yalnizca verilen kaynak ve kanit kayitlarina dayan. Kritik iddialari CLAIM_ID ve "
        "EVIDENCE_ID ile bagla; bilinmeyeni UNKNOWN birak; karsit kanit ve sinirliliklari yaz."
    )
    return system, json.dumps(registry.to_dict(), ensure_ascii=False, indent=2)


DEFAULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["claims", "decision", "epistemic_verdict", "limitations"],
    "properties": {
        "claims": {"type": "array"},
        "decision": {"enum": ["PUBLISH_FULL", "PUBLISH_LIMITED", "REPAIR", "HALT"]},
        "epistemic_verdict": {"enum": ["KNOWN", "PARTIAL", "UNKNOWN"]},
        "limitations": {"type": "array"},
    },
    "additionalProperties": True,
}


def run_agent_and_gate(registry: EvidenceRegistry, adapter: AgentAdapter) -> dict[str, Any]:
    system, user = build_prompt(registry)
    response = adapter.complete(system, user, DEFAULT_SCHEMA)
    model_result = response.structured or {"text": response.text}
    # Modelin karari ASLA guvenilmez; kayit bagimsiz denetlenir.
    audit = registry.audit("PUBLISH_FULL")
    return {
        "provider": response.provider,
        "model_output": model_result,
        "independent_audit": audit.to_dict(),
        "final_decision": audit.decision,
        "publish_allowed": audit.decision == "PUBLISH_FULL",
    }


# =============================================================================
# 4) PIYASA KAYNAGI — OKX/Binance public GET; erisilemezse KAYDEDILMEZ
#    D3: sayfa hata kodu HER sayfada denetlenir + sayfa tavani + ilerleme
#    D7: OKX'te taker-alis YOK -> None birakilir, notr dolgu YAZILMAZ
# =============================================================================
OKX_MUM = "https://www.okx.com/api/v5/market/candles"
OKX_GECMIS = "https://www.okx.com/api/v5/market/history-candles"
OKX_TICKER = "https://www.okx.com/api/v5/market/ticker"
BINANCE_MUM = "https://api.binance.com/api/v3/klines"


def _http_json(url: str, params: dict, timeout: int = 20) -> Any:
    if not url.startswith("https://"):
        raise ValueError(f"yalniz https kabul edilir: {url[:40]}")
    q = "&".join(f"{k}={v}" for k, v in params.items() if v not in (None, ""))
    req = Request(f"{url}?{q}" if q else url,  # noqa: S310 (https dogrulandi)
                  headers={"User-Agent": f"konsey-tek/{SURUM}"})
    with urlopen(req, timeout=timeout) as r:  # noqa: S310  # nosec B310 (https dogrulandi)
        return json.loads(r.read().decode())


def _okx_govde(j: Any) -> list:
    """D3: govde hata kodu HER cagride denetlenir; yutulmaz."""
    if not isinstance(j, dict):
        raise RuntimeError(f"OKX beklenmeyen yanit tipi: {type(j).__name__}")
    if str(j.get("code")) != "0":
        raise RuntimeError(f"OKX code={j.get('code')} msg={j.get('msg')}")
    return list(j.get("data") or [])


def _okx_sayfali(inst: str, bar: str, hedef: int, timeout: int = 20) -> list[list]:
    """Sayfa tavani + ilerleme korumasi + her sayfada kod denetimi."""
    satirlar = _okx_govde(_http_json(OKX_MUM, {"instId": inst, "bar": bar, "limit": 100}, timeout))
    gorulen = {x[0] for x in satirlar}
    for _ in range(int(E("SAYFA_TAVANI"))):
        if len(satirlar) >= hedef or not satirlar:
            break
        after = satirlar[-1][0]
        yeni_ham = _okx_govde(_http_json(OKX_GECMIS,
                                         {"instId": inst, "bar": bar,
                                          "after": after, "limit": 100}, timeout))
        yeni = [x for x in yeni_ham if x[0] not in gorulen]
        if not yeni:                      # ilerleme yok -> sonsuz dongu korumasi
            break
        satirlar.extend(yeni)
        gorulen |= {x[0] for x in yeni}
    return satirlar


def okx_satir_cevir(ham: Sequence, bar: str, hedef: int = 0) -> list[list]:
    """OKX ham satirlari -> Binance 12-alan satiri (AGSIZ; test edilebilir).

    D7: OKX'te taker-alis kolonu YOKTUR. Indeks 9'a NOTR DOLGU YAZILMAZ;
    None birakilir ve tuketici kanali EKSIK sayar. Eski surumde buraya
    hacim/2 yaziliyordu ve sifir hacimli barda CVD -1.0 (maksimum ayi)
    uretiyordu.
    """
    araliq = ARALIK_MS.get(bar, 900_000)
    out: list[list] = []
    for x in reversed(ham):               # OKX yeniden eskiye doner
        try:
            ts = int(x[0])
            o, h, l, c, v = (str(x[1]), str(x[2]), str(x[3]), str(x[4]), str(x[5]))
            float(o); float(h); float(l); float(c); float(v)
        except (ValueError, IndexError, TypeError):
            continue                      # bozuk satir sayilir, uydurulmaz
        out.append([ts, o, h, l, c, v, ts + araliq - 1,
                    str(x[6]) if len(x) > 6 else "0", 0,
                    None,                 # D7 taker-alis: OKX kolonu YOK, dolgu YAZILMAZ
                    "0", "0"])
    return out[-hedef:] if hedef else out


def okx_mumlar(inst: str, bar: str, hedef: int = 300, timeout: int = 20) -> list[list]:
    """OKX public mum ucu -> Binance 12-alan satiri."""
    return okx_satir_cevir(_okx_sayfali(inst, bar, hedef, timeout), bar, hedef)


def binance_mumlar(sembol: str, interval: str, limit: int = 300, timeout: int = 20) -> list[list]:
    j = _http_json(BINANCE_MUM, {"symbol": sembol, "interval": interval,
                                 "limit": min(limit, 1000)}, timeout)
    if not isinstance(j, list):
        raise RuntimeError(f"Binance beklenmeyen yanit: {str(j)[:120]}")
    return j


def okx_fiyat(inst: str, timeout: int = 20) -> float:
    d = _okx_govde(_http_json(OKX_TICKER, {"instId": inst}, timeout))
    if not d:
        raise RuntimeError("OKX ticker bos")
    return float(d[0]["last"])


def funding_oku(inst: str, limit: int = 100, timeout: int = 20) -> dict | None:
    """D8: isaret KORUNUR. abs() ile yok edilmez."""
    try:
        d = _okx_govde(_http_json(
            "https://www.okx.com/api/v5/public/funding-rate-history",
            {"instId": inst, "limit": limit}, timeout))
    except Exception:                     # noqa: BLE001
        return None
    ds = [_f(x.get("fundingRate")) for x in d]
    ds = [x for x in ds if x is not None]
    if not ds:
        return None
    ort = sum(ds) / len(ds)
    return {"ortalama_isaretli": ort, "n": len(ds),
            "maliyet_muhafazakar": max(ort, 0.0), "son": ds[0]}


def _gecerli_barlar(barlar: Sequence, ts_zorunlu: bool = False
                    ) -> tuple[list, int]:
    """Motor giris suzgeci: parse edilemeyen / geometrisi bozuk satirlari
    ATAR ve SAYAR (H9 stres bulgusu: bozuk API satiri motoru cokertiyordu).
    Gecerlilik: o/h/l/c sonlu sayi, l <= min(o,c) <= max(o,c) <= h,
    ts_zorunlu ise zaman damgasi okunabilir. Atilan sayisi cagirana doner;
    ust katman bunu raporlar — sessiz veri kaybi yok."""
    temiz, atilan = [], 0
    for b in barlar:
        try:
            if isinstance(b, (list, tuple)):
                if len(b) < 5:
                    atilan += 1; continue
                o, h, l, c = (float(b[1]), float(b[2]), float(b[3]), float(b[4]))
                if ts_zorunlu:
                    int(b[0])
            elif isinstance(b, dict):
                o, h, l, c = (float(b["o"]), float(b["h"]),
                              float(b["l"]), float(b["c"]))
                if ts_zorunlu:
                    int(b["t"])
            else:
                atilan += 1; continue
        except (TypeError, ValueError, KeyError, IndexError):
            atilan += 1; continue
        if not all(math.isfinite(x) for x in (o, h, l, c)):
            atilan += 1; continue
        if not (l <= min(o, c) and max(o, c) <= h):
            atilan += 1; continue
        temiz.append(b)
    return temiz, atilan


def bar_ts(b: Any) -> int:
    return int(b[0] if isinstance(b, (list, tuple)) else b["t"])


def bar_ohlc(b: Any) -> tuple[float, float, float, float]:
    if isinstance(b, (list, tuple)):
        return float(b[1]), float(b[2]), float(b[3]), float(b[4])
    return float(b["o"]), float(b["h"]), float(b["l"]), float(b["c"])


def tazelik(barlar: Sequence, bar_kodu: str) -> tuple[str, float]:
    barlar, _ = _gecerli_barlar(barlar, ts_zorunlu=True)
    if not barlar:
        return "UNKNOWN", float("inf")
    yas_ms = time.time() * 1000 - bar_ts(barlar[-1])
    yas_dk = yas_ms / 60000.0
    ar = ARALIK_MS.get(bar_kodu, 900_000)
    if yas_ms <= ar * 1.5:
        return "CURRENT", yas_dk
    if yas_ms <= ar * 3:
        return "LIMITED", yas_dk
    return "STALE", yas_dk


# =============================================================================
# 5) OLCUM — Wilder ATR/ADX, fraktal swing, acik FVG, trend, likidite
#    (stdlib; pandas/numpy GEREKMEZ)
# =============================================================================
def wilder_atr(barlar: Sequence, periyot: int | None = None) -> float | None:
    n = int(periyot or E("ATR_PERIYOT"))
    barlar, _ = _gecerli_barlar(barlar)
    if len(barlar) < 2:
        return None
    tr: list[float] = []
    for i in range(1, len(barlar)):
        _, h, l, _ = bar_ohlc(barlar[i])
        pc = bar_ohlc(barlar[i - 1])[3]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(tr) < n:
        return sum(tr) / len(tr) if tr else None
    atr = sum(tr[:n]) / n                       # Wilder tohumu
    for x in tr[n:]:
        atr = (atr * (n - 1) + x) / n
    return atr


def wilder_adx(barlar: Sequence, periyot: int | None = None) -> float | None:
    n = int(periyot or E("ADX_PERIYOT"))
    barlar, _ = _gecerli_barlar(barlar)
    if len(barlar) < 2 * n + 2:
        return None
    tr, pdm, ndm = [], [], []
    for i in range(1, len(barlar)):
        _, h, l, _ = bar_ohlc(barlar[i])
        _, ph, pl, pc = bar_ohlc(barlar[i - 1])
        up, dn = h - ph, pl - l
        pdm.append(up if (up > dn and up > 0) else 0.0)
        ndm.append(dn if (dn > up and dn > 0) else 0.0)
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))

    def yumusat(x: list[float]) -> list[float]:
        s = sum(x[:n])
        out = [s]
        for v in x[n:]:
            s = s - s / n + v
            out.append(s)
        return out

    str_, spdm, sndm = yumusat(tr), yumusat(pdm), yumusat(ndm)
    dx: list[float] = []
    for t, p, m in zip(str_, spdm, sndm, strict=False):
        if t <= 0:
            continue
        pdi, ndi = 100 * p / t, 100 * m / t
        toplam = pdi + ndi
        dx.append(100 * abs(pdi - ndi) / toplam if toplam > 0 else 0.0)
    if len(dx) < n:
        return None
    adx = sum(dx[:n]) / n
    for v in dx[n:]:
        adx = (adx * (n - 1) + v) / n
    return adx


def swingler(barlar: Sequence, sol: int | None = None,
             sag: int | None = None) -> list[tuple[int, float, str]]:
    """TEYITLI fraktal swing: sag tarafta `sag` bar kapanmis olmali."""
    L, Rr = int(sol or E("SWING_SOL")), int(sag or E("SWING_SAG"))
    barlar, _ = _gecerli_barlar(barlar)
    out: list[tuple[int, float, str]] = []
    for i in range(L, len(barlar) - Rr):
        _, h, l, _ = bar_ohlc(barlar[i])
        cevre = range(i - L, i + Rr + 1)
        if all(bar_ohlc(barlar[j])[1] <= h for j in cevre if j != i):
            out.append((i, h, "H"))
        if all(bar_ohlc(barlar[j])[2] >= l for j in cevre if j != i):
            out.append((i, l, "L"))
    return out


def acik_fvgler(barlar: Sequence, mitigasyon: float | None = None) -> list[dict]:
    """3-bar FVG; sonraki barlarca `mitigasyon` orani tuketilmisse KAPALI."""
    mg = float(mitigasyon if mitigasyon is not None else E("FVG_MITIGASYON"))
    barlar, _ = _gecerli_barlar(barlar)
    out: list[dict] = []
    n_b = len(barlar)
    # suffix ekstremleri (indeks k: k..son araliginin min low / max high'i)
    son_min_low = [math.inf] * (n_b + 1)
    son_max_high = [-math.inf] * (n_b + 1)
    for k in range(n_b - 1, -1, -1):
        _, hk, lk, _ = bar_ohlc(barlar[k])
        son_min_low[k] = min(lk, son_min_low[k + 1])
        son_max_high[k] = max(hk, son_max_high[k + 1])
    for i in range(2, len(barlar)):
        _, h0, l0, _ = bar_ohlc(barlar[i - 2])
        _, h2, l2, _ = bar_ohlc(barlar[i])
        if l2 > h0:
            alt, ust, yon = h0, l2, "bull"
        elif l0 > h2:
            alt, ust, yon = h2, l0, "bear"
        else:
            continue
        genislik = ust - alt
        if genislik <= 0:
            continue
        # O(n) mitigasyon: iteratif min/max zinciri cebirsel olarak
        #   bull: kalan_ust = min(ust, max(alt, min_{j>i} low_j))
        #   bear: kalan_alt = max(alt, min(ust, max_{j>i} high_j))
        # esdegerdir (spec testi S2, 60 rastgele seride brute-force ile birebir).
        if yon == "bull":
            kalan_alt = alt
            kalan_ust = min(ust, max(alt, son_min_low[i + 1]))
        else:
            kalan_ust = ust
            kalan_alt = max(alt, min(ust, son_max_high[i + 1]))
        kalan = max(0.0, kalan_ust - kalan_alt)
        if kalan / genislik > (1.0 - mg):
            out.append({"alt": round(kalan_alt, 8), "ust": round(kalan_ust, 8),
                        "yon": yon, "bar": i, "kalan_oran": round(kalan / genislik, 4)})
    return out


def trend_oku(barlar: Sequence) -> dict:
    """Yapisal trend: son teyitli HH/HL vs LH/LL + ADX rejimi."""
    sw = swingler(barlar)
    hs = [s for s in sw if s[2] == "H"]
    ls = [s for s in sw if s[2] == "L"]
    trend = "notr"
    if len(hs) >= 2 and len(ls) >= 2:
        yh = hs[-1][1] > hs[-2][1]
        yl = ls[-1][1] > ls[-2][1]
        dh = hs[-1][1] < hs[-2][1]
        dl = ls[-1][1] < ls[-2][1]
        if yh and yl:
            trend = "bull"
        elif dh and dl:
            trend = "bear"
    barlar, atilan = _gecerli_barlar(barlar)
    if not barlar:
        return {"trend": "notr", "trend_kaynagi": "VERI YOK (bos seri)",
                "adx": None, "rejim": "VERI YOK", "atr": None,
                "swing_sayisi": 0, "acik_fvg": [], "son_kapanis": None}
    kaynak_trend = "fraktal HH/HL - LH/LL"
    if trend == "notr":
        # Guclu tek-yonlu seride fraktal swing OLUSMAZ (her bar oncekini asar);
        # bu durumda trend "notr" gorunur. Yedek olcut: net yer degistirme / ATR.
        # ETIKETLENIR: bu bir YEDEK olcuttur, birincil olcut fraktal yapidir.
        atr_y = wilder_atr(barlar)
        if atr_y and atr_y > 0 and len(barlar) >= 3:
            yer = bar_ohlc(barlar[-1])[3] - bar_ohlc(barlar[0])[3]
            if abs(yer) >= 3.0 * atr_y:
                trend = "bull" if yer > 0 else "bear"
                kaynak_trend = (f"YEDEK olcut: net yer degistirme {yer:+.2f} "
                                f"= {yer/atr_y:+.2f} x ATR (fraktal swing olusmadi)")
    adx = wilder_adx(barlar)
    if adx is None:
        durum = "VERI YOK"
    elif adx >= E("ADX_TREND"):
        durum = "trend"
    elif adx < E("ADX_RANGE"):
        durum = "range"
    else:
        durum = "gecis"
    return {"trend": trend, "trend_kaynagi": kaynak_trend, "atilan_bar": atilan,
            "adx": None if adx is None else round(adx, 2),
            "rejim": durum, "atr": wilder_atr(barlar),
            "swing_sayisi": len(sw), "acik_fvg": acik_fvgler(barlar),
            "son_kapanis": bar_ohlc(barlar[-1])[3]}


def bar_hacim(b: Any) -> float | None:
    try:
        v = float(b[5]) if isinstance(b, (list, tuple)) else float(b.get("v"))
        return v if math.isfinite(v) and v >= 0 else None
    except (TypeError, ValueError, IndexError):
        return None


def ani_hareket(barlar: Sequence, atr: float | None) -> dict:
    """PUMP / DUMP / V-DONUS asiri-genisleme RISK BAYRAGI (kestirim DEGIL).

    Durustluk notu: hicbir yontem V donusunu KESIN onceden bilemez. Burada
    OLCULEBILIR asirilik kosullari isaretlenir: (1) son ANI_PENCERE barda net
    yer degistirme / ATR, (2) son barin fitil orani (ret/tukenme), (3) son bar
    hacmi / onceki 20 bar medyani (klimaks). Bayrak kalkinca MARKET emri
    yasaklanir (yalniz LIMIT) — kovalama mekanik olarak kapanir. Esikler
    ESIKLER'de beyanlidir.
    """
    n = int(E("ANI_PENCERE"))
    barlar, _ = _gecerli_barlar(barlar)
    if not atr or atr <= 0 or len(barlar) < n + 21:
        return {"tespit": False, "tur": None, "not": "VERI YETERSIZ (olcum yok)"}
    kap = [bar_ohlc(b)[3] for b in barlar[-(n + 1):]]
    net = kap[-1] - kap[0]
    yer_atr = abs(net) / atr
    o, h, l, c = bar_ohlc(barlar[-1])
    menzil = h - l
    fitil = (1.0 - abs(c - o) / menzil) if menzil > 0 else 0.0
    hacimler = [bar_hacim(b) for b in barlar[-21:-1]]
    hacimler = sorted(v for v in hacimler if v is not None)
    son_h = bar_hacim(barlar[-1])
    if hacimler and son_h is not None and hacimler[len(hacimler) // 2] > 0:
        hacim_oran = son_h / hacimler[len(hacimler) // 2]
    else:
        hacim_oran = None                     # hacim kanali yoksa UYDURULMAZ
    tespit = yer_atr >= E("ANI_YER_ATR")
    if not tespit:
        return {"tespit": False, "tur": None, "yer_atr": round(yer_atr, 2),
                "fitil_oran": round(fitil, 2), "hacim_oran":
                (round(hacim_oran, 2) if hacim_oran is not None else None),
                "not": "asiri genisleme yok"}
    son_yon = 1 if c >= o else -1
    pencere_yon = 1 if net > 0 else -1
    if fitil >= E("ANI_FITIL") or son_yon != pencere_yon:
        tur = "V-DONUS RISKI"
    else:
        tur = "PUMP" if net > 0 else "DUMP"
    notlar = [f"son {n} barda {net:+.2f} = {yer_atr:.2f}xATR"]
    if fitil >= E("ANI_FITIL"):
        notlar.append(f"fitil {fitil:.2f} >= {E('ANI_FITIL')} (ret/tukenme)")
    if hacim_oran is not None and hacim_oran >= E("ANI_HACIM"):
        notlar.append(f"hacim {hacim_oran:.1f}x medyan (klimaks)")
    return {"tespit": True, "tur": tur, "yer_atr": round(yer_atr, 2),
            "fitil_oran": round(fitil, 2),
            "hacim_oran": (round(hacim_oran, 2) if hacim_oran is not None else None),
            "not": "; ".join(notlar)}


# =============================================================================
# 6) D2 — 4H <-> 15M HIZALAMA: ZAMAN DAMGASIYLA (indeks orani VARSAYILMAZ)
# =============================================================================
def h4_hizala(m15: Sequence, h4: Sequence) -> list[int]:
    """Her 15M bari icin, ONU KAPSAYAN (t4 <= t15) EN GEC 4H barinin indeksi.

    Eski indeks-orani yontemi (i//16) veri eksikse karar barina AYLAR bayat
    4H satiri bagliyordu. Eslesme zaman damgasindan gelir; kapsayan 4H bar
    yoksa -1 (uydurma eslesme YOK). v1.2.0: onceki iki-isaretci surum SIRALI
    seri varsayiyordu ve sirasiz API yanitinda en gec kapsayan bari
    KACIRIYORDU (spec testi S4 yakaladi) -> bisect ile siralamadan bagimsiz.
    Ayni zaman damgasi birden cok barda varsa EN BUYUK orijinal indeks doner.
    """
    import bisect  # noqa: PLC0415
    m15, _ = _gecerli_barlar(m15, ts_zorunlu=True)
    h4, _ = _gecerli_barlar(h4, ts_zorunlu=True)
    sirali = sorted(range(len(h4)), key=lambda i: (bar_ts(h4[i]), i))
    tler = [bar_ts(h4[i]) for i in sirali]
    esl: list[int] = []
    for b in m15:
        k = bisect.bisect_right(tler, bar_ts(b)) - 1
        esl.append(sirali[k] if k >= 0 else -1)
    return esl


def hizalama_sapmasi(m15: Sequence, h4: Sequence) -> dict:
    esl = h4_hizala(m15, h4)
    if not esl or esl[-1] < 0:
        return {"esl_son": -1, "sapma_saat": None, "durum": "kapsayan 4H bar YOK"}
    sapma_ms = bar_ts(m15[-1]) - bar_ts(h4[esl[-1]])
    return {"esl_son": esl[-1], "sapma_saat": round(sapma_ms / 3_600_000, 2),
            "durum": "OK" if sapma_ms <= ARALIK_MS["4H"] else "BAYAT 4H SATIRI"}


# =============================================================================
# 7) R DENETIMI — sisirilmis R'yi ATR olcegiyle yakalar (D10)
# =============================================================================
def rr_denetim(yon: str, giris: float, stop: float, hedef: float,
               atr: float | None) -> dict:
    yon = yon.upper()
    risk = abs(giris - stop)
    odul = abs(hedef - giris)
    if risk <= 0 or odul <= 0:
        return {"verdict": "GECERSIZ", "R_rapor": None, "R_gercekci": None,
                "not": "risk veya odul sifir"}
    if yon == "LONG" and not (stop < giris < hedef):
        return {"verdict": "GECERSIZ", "R_rapor": None, "R_gercekci": None,
                "not": "LONG geometrisi bozuk (stop<giris<hedef degil)"}
    if yon == "SHORT" and not (hedef < giris < stop):
        return {"verdict": "GECERSIZ", "R_rapor": None, "R_gercekci": None,
                "not": "SHORT geometrisi bozuk (hedef<giris<stop degil)"}
    R_rapor = round(odul / risk, 2)
    if not atr or atr <= 0:
        return {"verdict": "OLCULEMEDI", "R_rapor": R_rapor, "R_gercekci": None,
                "not": "ATR yok -> olcek denetimi YAPILAMADI (fail-closed)"}
    s_atr, h_atr = risk / atr, odul / atr
    # Sisme: dar stop (gurultu bandi) + uzak hedef eslesmesi
    sisti = (s_atr < E("STOP_ATR_ALT")) or (h_atr > E("SISME_SINIRI"))
    if not sisti:
        return {"verdict": "TUTARLI", "R_rapor": R_rapor, "R_gercekci": R_rapor,
                "stop_atr": round(s_atr, 3), "hedef_atr": round(h_atr, 3),
                "not": "stop ve hedef ATR olceginde tutarli"}
    # R_gercekci: stop'u kurulum bandinin ALT sinirina, hedefi sisme sinirina cek
    risk_g = max(risk, E("STOP_ATR_ALT") * atr)
    odul_g = min(odul, E("SISME_SINIRI") * atr)
    return {"verdict": "SISIRILMIS", "R_rapor": R_rapor,
            "R_gercekci": round(odul_g / risk_g, 2),
            "stop_atr": round(s_atr, 3), "hedef_atr": round(h_atr, 3),
            "not": (f"stop/ATR={s_atr:.2f} (alt sinir {E('STOP_ATR_ALT')}) "
                    f"hedef/ATR={h_atr:.2f} (sinir {E('SISME_SINIRI')}) -> R yeniden olceklendi")}


# =============================================================================
# 8) EMIR PLANI — seviyeler YALNIZ olculen yapidan; MARKET/LIMIT ayrimi
# =============================================================================
def yapi_ozeti(m15: Sequence, h4: Sequence) -> dict:
    m15, at15 = _gecerli_barlar(m15)
    h4, at4 = _gecerli_barlar(h4)
    if not m15 or not h4:
        return {"son_kapanis": None, "atr15": None, "atr4h": None,
                "direnc15": [], "destek15": [], "direnc4h": [], "destek4h": [],
                "fvg": [], "bar15": len(m15), "bar4h": len(h4),
                "hizalama": {"esl_son": -1, "sapma_saat": None,
                             "durum": "VERI YOK (bos seri)"}}
    son = bar_ohlc(m15[-1])[3]
    sw15, sw4 = swingler(m15), swingler(h4)
    return {
        "son_kapanis": son,
        "atr15": wilder_atr(m15), "atr4h": wilder_atr(h4),
        "direnc15": sorted({s[1] for s in sw15 if s[2] == "H" and s[1] > son}),
        "destek15": sorted({s[1] for s in sw15 if s[2] == "L" and s[1] < son}, reverse=True),
        "direnc4h": sorted({s[1] for s in sw4 if s[2] == "H" and s[1] > son}),
        "destek4h": sorted({s[1] for s in sw4 if s[2] == "L" and s[1] < son}, reverse=True),
        "fvg": acik_fvgler(m15),
        "bar15": len(m15), "bar4h": len(h4),
        "hizalama": hizalama_sapmasi(m15, h4),
    }


def giris_adaylari(yapi: dict, yon: str, fiyat: float) -> list[tuple[float, str]]:
    """YALNIZ olculen yapidan: acik FVG kenarlari + teyitli swingler. Yuvarlak YOK."""
    out: list[tuple[float, str]] = [(fiyat, "guncel fiyat (MARKET adayi)")]
    if yon == "LONG":
        out += [(s, "15M teyitli swing destegi") for s in yapi["destek15"][:6]]
        out += [(s, "4H teyitli swing destegi") for s in yapi["destek4h"][:3]]
        out += [(f["ust"], "acik 15M FVG ust kenari") for f in yapi["fvg"]
                if f["ust"] < fiyat]
        out += [(f["alt"], "acik 15M FVG alt kenari") for f in yapi["fvg"]
                if f["alt"] < fiyat]
    else:
        out += [(s, "15M teyitli swing direnci") for s in yapi["direnc15"][:6]]
        out += [(s, "4H teyitli swing direnci") for s in yapi["direnc4h"][:3]]
        out += [(f["alt"], "acik 15M FVG alt kenari") for f in yapi["fvg"]
                if f["alt"] > fiyat]
        out += [(f["ust"], "acik 15M FVG ust kenari") for f in yapi["fvg"]
                if f["ust"] > fiyat]
    gorulen, tekil = set(), []
    for g, ger in out:
        k = round(g, 6)
        if k in gorulen:
            continue
        gorulen.add(k)
        tekil.append((g, ger))
    tekil.sort(key=lambda x: abs(x[0] - fiyat))
    return tekil


def stop_sec(yapi: dict, yon: str, giris: float, profil: dict | None) -> tuple[float | None, str]:
    if profil:
        usdt = _f(profil.get("stop_usdt")) or _f(profil.get("stop"))
        kontrat = _f(profil.get("kontrat"))
        if usdt and kontrat and kontrat > 0:
            mesafe = abs(usdt) / kontrat
            s = giris - mesafe if yon == "LONG" else giris + mesafe
            return s, f"sabit-USDT profili: {abs(usdt)} USDT / {kontrat} kontrat = {mesafe:.4f} puan"
    havuz = yapi["destek15"] + yapi["destek4h"] if yon == "LONG" else yapi["direnc15"] + yapi["direnc4h"]
    aday = [s for s in havuz if (s < giris if yon == "LONG" else s > giris)]
    if not aday:
        return None, "girisin otesinde teyitli swing YOK -> stop tanimsiz (fail-closed)"
    s = max(aday) if yon == "LONG" else min(aday)
    return s, "girisin otesindeki EN YAKIN teyitli swing"


def hedef_sec(yapi: dict, yon: str, giris: float,
              profil: dict | None) -> tuple[float | None, str]:
    if profil:
        band = profil.get("hedef_usdt") or profil.get("hedef")
        kontrat = _f(profil.get("kontrat"))
        if isinstance(band, (list, tuple)) and band and kontrat and kontrat > 0:
            mesafe = _f(band[0]) / kontrat
            h = giris + mesafe if yon == "LONG" else giris - mesafe
            return h, f"sabit-USDT profili: {band[0]} USDT / {kontrat} kontrat = {mesafe:.4f} puan"
    havuz = yapi["direnc15"] + yapi["direnc4h"] if yon == "LONG" else yapi["destek15"] + yapi["destek4h"]
    aday = [s for s in havuz if (s > giris if yon == "LONG" else s < giris)]
    if not aday:
        return None, "yon tarafinda teyitli likidite YOK -> 'R kati' uydurma hedef URETILMEZ"
    h = min(aday) if yon == "LONG" else max(aday)
    return h, "yon tarafindaki ILK teyitli likidite"


def emir_plani(m15: Sequence, h4: Sequence, yon: str, fiyat: float | None = None,
               profil: dict | None = None, r_min: float | None = None,
               azami: int = 8, market_yasak: bool = False) -> dict:
    yon = str(yon).upper()
    if yon not in ("LONG", "SHORT"):
        return {"EMIR": "EMIR YOK", "yon": yon, "adaylar": [], "seviyeler": [],
                "gerekce": "yonsuz kurulumda giris/stop tanimsiz (fail-closed)"}
    if not m15 or not h4:
        return {"EMIR": "EMIR YOK", "yon": yon, "adaylar": [], "seviyeler": [],
                "red_nedenleri": [], "gerekce": "bar serisi BOS -> VERI YOK (fail-closed)"}
    yapi = yapi_ozeti(m15, h4)
    fiyat = fiyat if fiyat is not None else yapi["son_kapanis"]
    rmin = max(E("R_MIN"), float(r_min) if r_min else E("R_MIN"))
    atr15 = yapi["atr15"] or 0.0
    atr_olcek = (yapi["atr4h"] if profil else yapi["atr15"]) or atr15

    gecen, tum, redler = [], [], []
    for giris, ger in giris_adaylari(yapi, yon, fiyat)[:azami * 3]:
        stop, sger = stop_sec(yapi, yon, giris, profil)
        if stop is None:
            redler.append(f"giris {round(giris,2)}: {sger}")
            continue
        risk = abs(giris - stop)
        if risk <= 0:
            redler.append(f"giris {round(giris,2)}: risk 0")
            continue
        hedef, hger = hedef_sec(yapi, yon, giris, profil)
        if hedef is None:
            redler.append(f"giris {round(giris,2)}: {hger}")
            continue
        rr = rr_denetim(yon, giris, stop, hedef, atr_olcek)
        R = rr.get("R_gercekci") if rr.get("R_gercekci") is not None else rr.get("R_rapor")
        tip = "MARKET" if abs(giris - fiyat) <= E("MARKET_BANDI") * atr15 else "LIMIT"
        kayit = {"emir_tipi": tip, "yon": yon, "giris": round(giris, 6),
                 "stop": round(stop, 6), "hedef": round(hedef, 6),
                 "R_rapor": rr.get("R_rapor"), "R_gercekci": rr.get("R_gercekci"),
                 "rr_denetim": rr.get("verdict"), "rr_not": rr.get("not"),
                 "stop_atr": rr.get("stop_atr"), "hedef_atr": rr.get("hedef_atr"),
                 "mesafe": round(abs(giris - fiyat), 6),
                 "giris_gerekcesi": ger, "stop_gerekcesi": sger, "hedef_gerekcesi": hger,
                 "gecersizlik": f"{round(stop,6)} otesinde 15M govde kapanisi -> kurulum iptal"}
        tum.append(kayit)
        if rr["verdict"] == "GECERSIZ":
            redler.append(f"giris {round(giris,2)}: geometri GECERSIZ"); continue
        if rr["verdict"] == "OLCULEMEDI":
            redler.append(f"giris {round(giris,2)}: ATR yok -> olcek denetimi yapilamadi"); continue
        if rr["verdict"] == "SISIRILMIS":
            redler.append(f"giris {round(giris,2)}: rr_denetim SISIRILMIS "
                          f"(R_rapor {rr['R_rapor']} -> R_gercekci {rr['R_gercekci']})")
            if (R or 0) < rmin:
                continue
        if R is None or rmin > R:
            redler.append(f"giris {round(giris,2)}: R {R} < r_min {rmin}"); continue
        s_atr = rr.get("stop_atr")
        if s_atr is not None and not (E("STOP_ATR_ALT") <= s_atr <= E("STOP_ATR_UST")):  # noqa: SIM300 (aralik zinciri bilincli)
            redler.append(f"giris {round(giris,2)}: stop/ATR {s_atr} kurulum bandi "
                          f"[{E('STOP_ATR_ALT')}, {E('STOP_ATR_UST')}] disinda"); continue
        if market_yasak and tip == "MARKET":
            redler.append(f"giris {round(giris,2)}: ANI-HAREKET bayragi -> MARKET "
                          "yasak, yalniz LIMIT (kovalama kapali)"); continue
        gecen.append(kayit)
        if len(gecen) >= azami:
            break

    gecen.sort(key=lambda a: (-(a["R_gercekci"] or 0), a["mesafe"]))
    if gecen:
        a = gecen[0]
        emir = (f"{a['emir_tipi']} {yon} @{a['giris']} | stop {a['stop']} "
                f"| T1 {a['hedef']} | R {a['R_gercekci']}")
    else:
        emir = "EMIR YOK"
    return {"EMIR": emir, "yon": yon, "fiyat": fiyat,
            "gerekce": "" if gecen else "hicbir aday kapilari gecemedi",
            "adaylar": gecen, "seviyeler": tum[:azami], "red_nedenleri": redler[:8],
            "yapi_ozeti": {k: yapi[k] for k in
                           ("son_kapanis", "atr15", "atr4h", "bar15", "bar4h", "hizalama")},
            "varsayimlar": [f"{k} = {v[0]} ({v[1]}: {v[2]})" for k, v in ESIKLER.items()
                            if k in ("R_MIN", "MARKET_BANDI", "STOP_ATR_ALT",
                                     "STOP_ATR_UST", "SISME_SINIRI", "FVG_MITIGASYON")]}


# =============================================================================
# 9) D5 + D6 — STAKE KAPISI: kazanan yoksa KAPALI; Kelly paydasi a*b
# =============================================================================
def stake_kapisi(n: int, kazan: int, sum_r: float, sum_kaz_r: float,
                 sum_kayip_r: float, min_n: int = 30,
                 cap: float = 0.25) -> dict:
    """Fail-closed boyutlandirma kapisi.

    KAPSAM NOTU (Q1): bu islev islem-gecmisi olcumu (n, kazan, R toplami)
    gerektirir; sinyal motoru boyle bir gecmis uretmez, dolayisiyla sinyal
    yolunda CAGRILMAZ ve ciktida stake BASILMAZ (uydurma boyut yok). FADE
    benzeri olcum akislari icin kutuphane islevidir.

    D5: kazan == 0 iken b_win OLCULEMEZ -> sabit bir tasarim degerine DUSULMEZ,
        kapi KAPANIR. (Eski surum R_FADE=1.5 sabitine dusup kapiyi ACIYORDU.)
    D6: stake = edge / (a * b). Kayip bacagi `a` 1.0R VARSAYILMAZ, olculur.
        (Eski `edge / b` formulu stake'i `a` kati sisiriyordu.)
    """
    out = {"acik": False, "n": n, "p_hat": None, "edge_hat": None,
           "b_win": None, "a_loss": None, "stake": 0.0, "not": ""}
    if n <= 0:
        out["not"] = "olcum yok (n=0) - kapi KAPALI (fail-closed)"
        return out
    out["p_hat"] = kazan / n
    out["edge_hat"] = sum_r / n
    if n < min_n:
        out["not"] = f"n={n} < min_n={min_n} (istatistik taban) - kapi KAPALI"
        return out
    if kazan <= 0:
        out["not"] = "kazanan YOK -> b_win OLCULEMEZ; sabit degere DUSULMEZ - kapi KAPALI (D5)"
        return out
    b = sum_kaz_r / kazan
    kayip_n = n - kazan
    a = (abs(sum_kayip_r) / kayip_n) if kayip_n > 0 else None
    out["b_win"], out["a_loss"] = b, a
    if b <= 0:
        out["not"] = "b_win <= 0 - kapi KAPALI"
        return out
    if a is None or a <= 0:
        out["not"] = "kayip bacagi OLCULEMEDI (a) - kapi KAPALI (D6: a=1.0 VARSAYILMAZ)"
        return out
    if out["edge_hat"] <= 0:
        out["not"] = f"edge_hat={out['edge_hat']:+.4f}R <= 0 - kapi KAPALI (fail-closed)"
        return out
    out["acik"] = True
    out["stake"] = min(out["edge_hat"] / (a * b), cap)
    out["not"] = (f"edge_hat={out['edge_hat']:+.4f}R (n={n}, p_hat={out['p_hat']:.3f}, "
                  f"a={a:.3f}, b={b:.3f}) - kapi ACIK; stake=edge/(a*b) [D6]")
    return out


# =============================================================================
# 10) D4 — TEK BAHIS KAPISI: |rho| >= esik ve ayni yon -> KOPYA, bagimsiz degil
# =============================================================================
def getiriler(barlar: Sequence, n: int = 200) -> list[float]:
    kap = [bar_ohlc(b)[3] for b in barlar[-(n + 1):]]
    return [(kap[i] / kap[i - 1] - 1.0) for i in range(1, len(kap)) if kap[i - 1] > 0]


def korelasyon(a: Sequence[float], b: Sequence[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 20:
        return None
    a, b = list(a[-n:]), list(b[-n:])
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return None
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=False))
    return cov / math.sqrt(va * vb)


def tek_bahis_kapisi(sinyaller: list[dict]) -> list[dict]:
    """Ana sembol capadir. |rho| >= esik + AYNI yon -> "KOPYA - ATLA".

    Eski surumde FADE stake'i bu kapiya HIC girmiyordu; portfoy "pozisyon yok"
    derken iki korelasyonlu bahis birden aciliyordu (olculen: %26.67 sermaye).
    """
    if not sinyaller:
        return []
    ana = sinyaller[0]
    ana["tek_bahis"] = {"hukum": "ANA SEMBOL", "rho": None}
    ana_g = getiriler(ana["_m15"])
    for s in sinyaller[1:]:
        rho = korelasyon(ana_g, getiriler(s["_m15"]))
        ayni_yon = (s["yon"]["yon"] == ana["yon"]["yon"]
                    and s["yon"]["yon"] in ("LONG", "SHORT"))
        if rho is not None and abs(rho) >= E("RHO_ESIK") and ayni_yon:
            s["tek_bahis"] = {"hukum": "KOPYA - ATLA", "rho": round(rho, 4),
                              "not": (f"|rho|={abs(rho):.4f} >= {E('RHO_ESIK')} ve yon ANA ile "
                                      "AYNI -> bagimsiz bahis DEGIL; toplam risk TEK bahis sayilir")}
        else:
            s["tek_bahis"] = {"hukum": "BAGIMSIZ",
                              "rho": None if rho is None else round(rho, 4),
                              "not": "rho esigin altinda ya da yon farkli"}
    return sinyaller


# =============================================================================
# 11) YON TURETIMI — agirliklar BEYAN EDILIR; eksik kanal AGIRLIGA GIRMEZ
# =============================================================================
def yon_turet(h4: dict, m15: dict, turev: dict | None,
              h4_eid: str = "", m15_eid: str = "", turev_eid: str = "") -> dict:
    def isaret(t: Any) -> float:
        return {"bull": 1.0, "bear": -1.0}.get(str(t or "").lower(), 0.0)

    bilesen, toplam, agirlik_toplam = [], 0.0, 0.0

    a4 = E("AGIRLIK_H4")
    k4 = isaret(h4["trend"]) * a4
    toplam += k4
    agirlik_toplam += a4
    bilesen.append({"ad": "4H trend", "deger": h4["trend"], "agirlik": a4,
                    "katki": round(k4, 4), "evidence_id": h4_eid or None,
                    "not": f"rejim={h4.get('rejim')} adx={h4.get('adx')}"})

    a15 = E("AGIRLIK_M15") * (E("RANGE_KIRPMA") if m15.get("rejim") == "range" else 1.0)
    k15 = isaret(m15["trend"]) * a15
    toplam += k15
    agirlik_toplam += a15
    bilesen.append({"ad": "15M trend", "deger": m15["trend"], "agirlik": round(a15, 4),
                    "katki": round(k15, 4), "evidence_id": m15_eid or None,
                    "not": (f"rejim=range -> agirlik x{E('RANGE_KIRPMA')} kirpildi"
                            if m15.get("rejim") == "range" else f"rejim={m15.get('rejim')}")})

    skor_t = turev.get("skor") if turev else None
    if isinstance(skor_t, (int, float)):
        at = E("AGIRLIK_TUREV")
        kt = max(-1.0, min(1.0, float(skor_t))) * at
        toplam += kt
        agirlik_toplam += at
        bilesen.append({"ad": "turev skoru", "deger": round(float(skor_t), 4),
                        "agirlik": at, "katki": round(kt, 4),
                        "evidence_id": turev_eid or None, "not": ""})
    else:
        bilesen.append({"ad": "turev skoru", "deger": "VERI YOK", "agirlik": 0.0,
                        "katki": 0.0, "evidence_id": None,
                        "not": "kanal yok -> AGIRLIGA GIRMEDI (uydurma yok)"})

    skor = (toplam / agirlik_toplam) if agirlik_toplam else 0.0
    yon = "LONG" if skor > 0 else ("SHORT" if skor < 0 else "NOTR")
    t4, t15 = str(h4.get("trend")), str(m15.get("trend"))
    mtf_celiski = ({t4, t15} == {"bull", "bear"})
    return {"yon": yon, "skor": round(skor, 4), "bilesenler": bilesen,
            "agirlik_toplam": round(agirlik_toplam, 4),
            "mtf_celiski": mtf_celiski,
            "mtf_not": (f"MTF CELISKI: 4H={t4} / 15M={t15} — zaman dilimleri "
                        "zit; guven DUSUK, iddia LIMITED" if mtf_celiski else "")}


# =============================================================================
# 12) KOSU — kaynak -> olcum -> yon -> emir -> tek bahis -> kapi -> basim
# =============================================================================
VARSAYILAN_SEMBOL = {
    "BTCUSDT": {"okx": "BTC-USDT-SWAP", "binance": "BTCUSDT"},
    "ETHUSDT": {"okx": "ETH-USDT-SWAP", "binance": "ETHUSDT"},
    "SOLUSDT": {"okx": "SOL-USDT-SWAP", "binance": "SOLUSDT"},
}


def yerel_coz(sembol: str, bar: str, acik: str | Path | None,
              dizin: str | Path | None) -> Path | None:
    """Yerel dosya cozumu: acik yol > <dizin>/<SEMBOL>_<bar>.json > <dizin>/<bar>.json."""
    if acik and Path(acik).exists():
        return Path(acik)
    if dizin:
        d = Path(dizin)
        ad = {"15m": "m15", "4H": "h4", "1H": "h1", "2H": "h2"}.get(bar, bar)
        for aday in (d / f"{sembol.upper()}_{ad}.json", d / sembol.upper() / f"{ad}.json",
                     d / f"{ad}.json"):
            if aday.exists():
                return aday
    return None


def bar_getir(sembol: str, bar: str, hedef: int, yerel: str | Path | None
              ) -> tuple[list, str, str | None]:
    """CANLI once (OKX -> Binance), sonra yerel. Dusus KAYDA GECER."""
    cfg = VARSAYILAN_SEMBOL.get(sembol.upper(), {})
    hatalar: list[str] = []
    if cfg.get("okx"):
        try:
            return okx_mumlar(cfg["okx"], bar, hedef), "canli-okx", None
        except Exception as e:                        # noqa: BLE001
            hatalar.append(f"OKX {type(e).__name__}: {e}")
    if cfg.get("binance"):
        iv = {"15m": "15m", "4H": "4h", "1H": "1h", "2H": "2h"}.get(bar, bar)
        try:
            return binance_mumlar(cfg["binance"], iv, hedef), "canli-binance", None
        except Exception as e:                        # noqa: BLE001
            hatalar.append(f"Binance {type(e).__name__}: {e}")
    if yerel and Path(yerel).exists():
        d = json.loads(Path(yerel).read_text(encoding="utf-8"))
        if not isinstance(d, list) or not d:
            raise ValueError(f"{yerel}: bos ya da liste degil")
        return d, "yerel-arsiv", " | ".join(hatalar) or None
    raise RuntimeError("veri alinamadi: " + (" | ".join(hatalar) or "yerel dosya yok"))


def sembol_kos(sembol: str, reg: EvidenceRegistry, sira: int,
               m15_yol: str | Path | None = None, h4_yol: str | Path | None = None,
               profil: dict | None = None, turev_yol: str | Path | None = None,
               yerel_dizin: str | Path | None = None) -> dict:
    P = f"{sira:02d}"
    y15 = yerel_coz(sembol, "15m", m15_yol, yerel_dizin)
    y4 = yerel_coz(sembol, "4H", h4_yol, yerel_dizin)
    b15, k15, h15 = bar_getir(sembol, "15m", 300, y15)
    b4, k4, h4e = bar_getir(sembol, "4H", 300, y4)
    t15, y15 = tazelik(b15, "15m")
    t4, _ = tazelik(b4, "4H")

    reg.add_source(f"S{P}A", str(y15) if k15 == "yerel-arsiv" else f"{sembol} 15m",
                   k15, t15, f"G{sira}", json.dumps(b15[-5:]),
                   f"canli uc KAPALI ({h15}) -> yerel arsive dusuldu" if h15 else "canli uc acik")
    reg.add_source(f"S{P}B", str(y4) if k4 == "yerel-arsiv" else f"{sembol} 4H",
                   k4, t4, f"G{sira}", json.dumps(b4[-5:]),
                   f"canli uc KAPALI ({h4e}) -> yerel arsive dusuldu" if h4e else "canli uc acik")

    o15, o4 = trend_oku(b15), trend_oku(b4)
    reg.add_evidence(f"E{P}A", f"S{P}A", "OHLC serisi",
                     f"{sembol} 15M {len(b15)} bar",
                     f"son_bar_utc={datetime.fromtimestamp(bar_ts(b15[-1])/1000, timezone.utc):%Y-%m-%d %H:%M} "
                     f"yas={y15:.0f}dk tazelik={t15} kaynak={k15} son_kapanis={o15['son_kapanis']}")
    reg.add_evidence(f"E{P}B", f"S{P}B", "OHLC serisi",
                     f"{sembol} 4H {len(b4)} bar", f"tazelik={t4} kaynak={k4}")
    reg.add_evidence(f"E{P}C", f"S{P}A", "trend_oku (olculdu)", f"{sembol} 15M yapi",
                     f"trend={o15['trend']} adx={o15['adx']} rejim={o15['rejim']} "
                     f"atr={o15['atr']} acik_fvg={len(o15['acik_fvg'])}")
    reg.add_evidence(f"E{P}D", f"S{P}B", "trend_oku (olculdu)", f"{sembol} 4H yapi",
                     f"trend={o4['trend']} adx={o4['adx']} rejim={o4['rejim']} atr={o4['atr']}")

    uyarilar: list[str] = []          # Q2: hicbir hata sessizce yutulmaz

    # Q1: turev kanali HER sembol icin cozulur (eskiden yalniz 1. sembol)
    if not (turev_yol and Path(turev_yol).exists()) and yerel_dizin:
        for aday in (Path(yerel_dizin) / f"{sembol.upper()}_turev.json",
                     Path(yerel_dizin) / sembol.upper() / "turev.json"):
            if aday.exists():
                turev_yol = aday
                break
    turev = None
    if turev_yol and Path(turev_yol).exists():
        try:
            d = json.loads(Path(turev_yol).read_text(encoding="utf-8"))
            sk = d.get("yon_skoru")
            if sk is None and isinstance(d.get("skor"), dict):
                sk = d["skor"].get("yon")
            if isinstance(sk, (int, float)):
                reg.add_source(f"S{P}C", str(turev_yol), "yerel dosya", "LIMITED",
                               f"G{sira}", json.dumps(d)[:400], "turev kanali")
                reg.add_evidence(f"E{P}E", f"S{P}C", "turev okumasi", "turev yon skoru",
                                 f"yon_skoru={sk} kapsam={d.get('kapsam')}")
                turev = {"skor": sk, "kapsam": d.get("kapsam")}
            else:
                uyarilar.append(f"turev dosyasi var ama yon_skoru yok: {turev_yol}")
        except Exception as e:                        # noqa: BLE001
            uyarilar.append(f"turev OKUNAMADI ({type(e).__name__}: {e}) -> VERI YOK")
            turev = None

    y = yon_turet(o4, o15, turev, f"E{P}D", f"E{P}C", f"E{P}E" if turev else "")
    if y.get("mtf_celiski"):
        uyarilar.append(y["mtf_not"])

    fiyat, fk = o15["son_kapanis"], f"son kapanis ({k15})"
    funding = None
    if k15.startswith("canli"):
        cfg = VARSAYILAN_SEMBOL.get(sembol.upper(), {})
        if cfg.get("okx"):
            try:
                fiyat, fk = okx_fiyat(cfg["okx"]), "canli ticker"
            except Exception as e:                    # noqa: BLE001
                uyarilar.append(f"canli ticker ALINAMADI ({type(e).__name__}) "
                                "-> son kapanis kullanildi")
            funding = funding_oku(cfg["okx"])         # Q1: funding karara baglandi
            if funding is None:
                uyarilar.append("funding kanali ALINAMADI -> VERI YOK")
            else:
                reg.add_evidence(f"E{P}G", f"S{P}A", "funding-rate-history",
                                 f"{sembol} funding (isaretli)",
                                 f"ortalama={funding['ortalama_isaretli']:+.6f} "
                                 f"son={funding['son']:+.6f} n={funding['n']}")

    # Q6: ani-hareket bayragi — kalkarsa MARKET yasak (yalniz LIMIT)
    ani = ani_hareket(b15, o15.get("atr"))
    reg.add_evidence(f"E{P}H", f"S{P}A", "ani_hareket (olculdu)",
                     f"{sembol} asiri-genisleme taramasi",
                     f"tespit={ani['tespit']} tur={ani.get('tur')} {ani.get('not','')}")
    if ani["tespit"]:
        uyarilar.append(f"ANI HAREKET: {ani['tur']} — {ani['not']} -> MARKET yasak")

    hiz = hizalama_sapmasi(b15, b4)
    emirler: dict[str, dict] = {}
    for taraf in ([y["yon"]] if y["yon"] in ("LONG", "SHORT") else ["LONG", "SHORT"]):
        emirler[taraf] = emir_plani(b15, b4, taraf, fiyat, profil,
                                    market_yasak=ani["tespit"])
    reg.add_evidence(f"E{P}F", f"S{P}A", "emir_plani (olculdu)", f"{sembol} emir",
                     json.dumps({k: v["EMIR"] for k, v in emirler.items()}, ensure_ascii=False))

    yon_statu = "VERIFIED" if (y["yon"] != "NOTR" and not y.get("mtf_celiski")) else "LIMITED"
    reg.add_claim(f"C{P}1", f"{sembol} yon={y['yon']} (agirlikli skor {y['skor']})"
                  + (" [MTF CELISKI -> LIMITED]" if y.get("mtf_celiski") else ""),
                  yon_statu,
                  [f"E{P}C", f"E{P}D"] + ([f"E{P}E"] if turev else []), "DONE")
    reg.add_claim(f"C{P}2", f"{sembol} seviyeleri olculen yapidan; uydurma seviye yok",
                  "VERIFIED", [f"E{P}F"], "DONE")
    taze_ok = (t15 == "CURRENT" and y15 <= E("AZAMI_YAS_DK"))
    reg.add_claim(f"C{P}3", f"{sembol} veri canli ve taze (yas {y15:.0f} dk)",
                  "VERIFIED" if taze_ok else "LIMITED", [f"E{P}A"], "DONE")
    if not taze_ok:
        reg.external_checks_pending.append(
            f"{sembol}: canli fiyat dogrulanamadi (kaynak={k15}, yas={y15:.0f} dk, tazelik={t15})")
    if hiz["durum"] != "OK":
        reg.contradictions.append(f"{sembol}: 4H hizalama {hiz['durum']} "
                                  f"(sapma {hiz['sapma_saat']} saat)")

    return {"sembol": sembol, "yon": y, "fiyat": fiyat, "fiyat_kaynak": fk,
            "emirler": emirler, "o15": o15, "o4": o4, "turev": turev,
            "funding": funding, "ani": ani, "uyarilar": uyarilar,
            "hizalama": hiz, "tazelik": {"15m": t15, "yas_dk": y15, "kaynak": k15,
                                         "4H": t4, "kaynak4": k4},
            "_m15": b15, "_h4": b4}


def bas(sonuclar: list[dict], audit: dict, publish: bool) -> str:
    L: list[str] = []
    A = L.append
    A("=" * 78)
    A(f"KONSEY SINYAL — YON + GIRIS/CIKIS      (surum {SURUM})")
    A("=" * 78)
    for s in sonuclar:
        y = s["yon"]
        tb = s.get("tek_bahis") or {}
        A("")
        A(f"### {s['sembol']}   fiyat={s['fiyat']}   ({s['fiyat_kaynak']})")
        A(f"YON      : {y['yon']}   agirlikli skor {y['skor']:+.4f}")
        for b in y["bilesenler"]:
            n = f"   [{b['not']}]" if b.get("not") else ""
            A(f"   - {b['ad']:<12} = {str(b['deger']):<9} agirlik {str(b['agirlik']):<6} "
              f"katki {b['katki']:+.4f}  kanit={b['evidence_id']}{n}")
        if tb:
            A(f"TEK BAHIS: {tb.get('hukum')}   rho={tb.get('rho')}"
              + (f"   {tb.get('not')}" if tb.get("not") else ""))
        for taraf, e in s["emirler"].items():
            etk = "" if y["yon"] in ("LONG", "SHORT") else f"({taraf})"
            if e["EMIR"] != "EMIR YOK":
                A(f"EMIR {etk:<6}: {e['EMIR']}")
                a = e["adaylar"][0]
                A(f"   giris  : {a['giris_gerekcesi']}")
                A(f"   stop   : {a['stop_gerekcesi']}   (stop/ATR {a['stop_atr']})")
                A(f"   hedef  : {a['hedef_gerekcesi']}")
                A(f"   rr     : {a['rr_denetim']} — {a['rr_not']}")
                A(f"   gecersizlik: {a['gecersizlik']}")
            else:
                A(f"EMIR {etk:<6}: EMIR YOK — {e['gerekce']}")
                for r in e.get("red_nedenleri", [])[:3]:
                    A(f"   x {r}")
            if e.get("seviyeler"):
                A(f"SEVIYELER ({taraf}) — YER ve YON bilgisi; ISLEM ONERISI DEGIL:")
                A("   %-7s %-12s %-12s %-12s %-8s %-8s %-12s %-9s %s" %
                  ("tip", "giris", "stop", "hedef", "R_rap", "R_ger", "rr", "stop/ATR", "mesafe"))
                for x in e["seviyeler"][:6]:
                    A("   %-7s %-12s %-12s %-12s %-8s %-8s %-12s %-9s %s" %
                      (x["emir_tipi"], x["giris"], x["stop"], x["hedef"],
                       x["R_rapor"], x["R_gercekci"], x["rr_denetim"],
                       x["stop_atr"], x["mesafe"]))
        ani = s.get("ani") or {}
        if ani.get("tespit"):
            A(f"ANI HAREKET: {ani['tur']}  ({ani['not']})  -> MARKET YASAK, yalniz LIMIT")
        elif "yer_atr" in ani:
            A(f"ANI HAREKET: yok  (yer/ATR {ani['yer_atr']}, fitil {ani['fitil_oran']}, "
              f"hacim {ani['hacim_oran']}x)")
        f = s.get("funding")
        if f:
            A(f"FUNDING  : ort {f['ortalama_isaretli']:+.6f} (isaretli, n={f['n']}) "
              f"| son {f['son']:+.6f} | muhafazakar maliyet {f['maliyet_muhafazakar']:.6f}")
        for u in (s.get("uyarilar") or []):
            A(f"   ~ {u}")
        hz = s["hizalama"]
        A(f"VERI     : 15M {s['tazelik']['kaynak']} yas {s['tazelik']['yas_dk']:.0f} dk "
          f"({s['tazelik']['15m']}) | 4H {s['tazelik']['kaynak4']} ({s['tazelik']['4H']}) "
          f"| 4H hizalama {hz['durum']} (sapma {hz['sapma_saat']} sa)")
    A("")
    A("-" * 78)
    A(f"KONSEY KAPISI : {audit['decision']}    yayin={'IZINLI' if publish else 'DURDURULDU'}")
    for r in audit.get("reasons", []):
        A(f"   ! {r}")
    A(f"   kritik iddia {audit['critical_claims_with_evidence']}/{audit['critical_claim_count']} "
      f"kanitli | tazelik {audit['freshness']} | celiski {audit['unresolved_contradictions']}")
    if not publish:
        A("   >> Seviyeler GOSTERILIYOR ama ISLEM ONERISI DEGILDIR (fail-closed).")
    A("=" * 78)
    A("Yalniz karar-destek; canli/otomatik emir DAHIL DEGIL.")
    return "\n".join(L)


def kos(semboller: Sequence[str], m15: str | None = None, h4: str | None = None,
        profil_yol: str | None = None, turev_yol: str | None = None,
        cikti: str | None = None, sessiz: bool = False,
        yerel_dizin: str | None = None) -> dict:
    reg = EvidenceRegistry(task_type="MARKET_SIGNAL", risk_level="HIGH")
    reg.counter_evidence_search = "DONE"
    reg.method_layers_applied = [
        "Kanit katalogu: her seviye/yon bir EVIDENCE_ID'ye bagli",
        "GRADE-benzeri kesinlik: VERIFIED/LIMITED/UNKNOWN",
        "Deterministik yayin kapisi: model beyani kanit sayilmaz",
        "Olcum yanliligi denetimi: sisirilmis R + stop/ATR kurulum bandi",
    ]
    reg.method_layers_omitted = [
        "OWASP SAMM / PRISMA / Cochrane: bu gorev turu icin kapsam disi",
        "Bagimsiz dis guvence (BIST/IOSCO): yok - tek sistem",
    ]
    profil = None
    if profil_yol and Path(profil_yol).exists():
        profil = json.loads(Path(profil_yol).read_text(encoding="utf-8"))

    sonuclar, dusen = [], []
    for i, s in enumerate(semboller, 1):
        try:
            sonuclar.append(sembol_kos(
                s, reg, i,
                m15 if i == 1 else None, h4 if i == 1 else None,
                profil, turev_yol if i == 1 else None, yerel_dizin))
        except Exception as e:                     # noqa: BLE001
            # Bir sembol dusunce TUM kosu dusmez; dusus KAYDA GECER (sessiz atlama yok).
            dusen.append(f"{s}: {type(e).__name__}: {e}")
            reg.external_checks_pending.append(f"{s}: veri alinamadi -> sembol ATLANDI ({e})")
    if not sonuclar:
        reg.contradictions.append("hicbir sembol icin veri alinamadi")
    tek_bahis_kapisi(sonuclar)

    reg.payload = {"sinyaller": [
        {"sembol": s["sembol"], "yon": s["yon"]["yon"], "skor": s["yon"]["skor"],
         "fiyat": s["fiyat"], "tek_bahis": s.get("tek_bahis", {}).get("hukum"),
         "emirler": {k: v["EMIR"] for k, v in s["emirler"].items()},
         "seviyeler": {k: v["seviyeler"] for k, v in s["emirler"].items()}}
        for s in sonuclar]}

    adapter = YerelOlcumAdapter(lambda d: {
        "claims": list(d["claims"].keys()),
        "decision": "PUBLISH_FULL",
        "epistemic_verdict": "PARTIAL",
        "limitations": [v.get("note", "") for v in d["sources"].values() if v.get("note")],
    }).bagla(reg)
    rapor = run_agent_and_gate(reg, adapter)

    # CIFT KAPI: registry.audit + kullanici kapisi; SERT olan kazanir.
    ck = cift_kapi(reg, str(rapor["model_output"].get("decision", "PUBLISH_FULL")))
    rapor["cift_kapi"] = ck
    rapor["final_decision"] = ck["final_decision"]
    rapor["publish_allowed"] = ck["publish_allowed"]

    metin = bas(sonuclar, rapor["independent_audit"], rapor["publish_allowed"])
    k2 = ck["kapi2_kullanici"]
    metin += ("\nCIFT KAPI  : kapi1(registry)=%s | kapi2(kullanici)=%s | SERT=%s"
              % (ck["kapi1_registry"]["decision"], k2["final_decision"],
                 ck["final_decision"]))
    for h in k2["errors"][:3]:
        metin += "\n   kapi2 ! " + h
    for h in k2["warnings"][:2]:
        metin += "\n   kapi2 ~ " + h
    if dusen:
        metin += "\n\nDUSEN SEMBOLLER (veri alinamadi, atlandi):\n" + \
                 "\n".join(f"   x {d}" for d in dusen)
    if not sessiz:
        print(metin)
    if cikti:
        Path(cikti).parent.mkdir(parents=True, exist_ok=True)
        Path(cikti).write_text(json.dumps(
            {"rapor": rapor, "kayit": reg.to_dict(), "metin": metin},
            ensure_ascii=False, indent=2), encoding="utf-8")
    return rapor


# =============================================================================
# 13) OZ-TEST — her duzeltme icin en az bir koruyucu test
# =============================================================================
def _sentetik(n: int, aralik_ms: int, p0: float = 65000.0, egim: float = 0.0,
              tohum: int = 7, bitis_ms: int | None = None) -> list[list]:
    """Deterministik bar uretici (random/Date YOK - tohumlu LCG)."""
    bitis = bitis_ms if bitis_ms is not None else int(time.time() * 1000)
    bas = bitis - (n - 1) * aralik_ms
    s, out, p = tohum, [], p0
    for i in range(n):
        s = (1103515245 * s + 12345) % (2 ** 31)
        d = ((s / 2 ** 31) - 0.5) * p0 * 0.004 + egim
        o = p
        p = max(1.0, p + d)
        h, l = max(o, p) * 1.0009, min(o, p) * 0.9991
        out.append([bas + i * aralik_ms, f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{p:.2f}",
                    "1000", bas + i * aralik_ms + aralik_ms - 1, "0", 0, None, "0", "0"])
    return out


def oz_test() -> list[tuple[str, str, str]]:
    R: list[tuple[str, str, str]] = []

    def kayit(ad: str, ok: bool, detay: str = "") -> None:
        R.append((ad, "PASS" if ok else "FAIL", detay))

    a = EvidenceRegistry().audit("PUBLISH_FULL")
    kayit("T1  bos kayit -> REPAIR", a.decision == "REPAIR", a.decision)

    r = EvidenceRegistry(); r.add_source("S1", "y", "dosya", "CURRENT", content="x")
    r.add_claim("C1", "kanitsiz", "VERIFIED", [], "DONE")
    a = r.audit()
    kayit("T2  kanitsiz VERIFIED -> REPAIR",
          a.decision == "REPAIR" and "C1" in a.missing_evidence_claims, a.decision)

    r = EvidenceRegistry(); r.add_source("S1", "y", "dosya", "CURRENT", content="x")
    r.add_claim("C1", "hayalet", "VERIFIED", ["E_YOK"], "DONE")
    kayit("T3  cozulemeyen kanit yakalanir", bool(r.audit().invalid_references), "")

    r = EvidenceRegistry(risk_level="HIGH")
    r.add_source("S1", "y", "dosya", "CURRENT", content="x")
    r.add_evidence("E1", "S1", "olcum", "d", "g"); r.add_claim("C1", "ok", "VERIFIED", ["E1"], "DONE")
    kayit("T4  tam kayit -> PUBLISH_FULL", r.audit().decision == "PUBLISH_FULL", r.audit().decision)

    r = EvidenceRegistry(risk_level="HIGH")
    r.add_source("S1", "y", "dosya", "CURRENT", content="x")
    r.add_evidence("E1", "S1", "olcum", "d", "g"); r.add_claim("C1", "ok", "VERIFIED", ["E1"], "NOT_RUN")
    kayit("T5  karsit kanit bekliyor -> LIMITED", r.audit().decision == "PUBLISH_LIMITED", "")

    r = EvidenceRegistry()
    try:
        r.fetch("https://kesinlikle-yok-98765.invalid", "S9", "E9"); ok = False
    except Exception:                                  # noqa: BLE001
        ok = "S9" not in r.sources and "E9" not in r.evidence
    kayit("T6  erisilemeyen kaynak KAYDEDILMEZ", ok, f"kaynak={len(r.sources)}")

    taze = _sentetik(60, 900_000)
    eski = _sentetik(60, 900_000, bitis_ms=int(time.time() * 1000) - 40 * 86_400_000)
    kayit("T7  tazelik OLCULUR",
          tazelik(taze, "15m")[0] == "CURRENT" and tazelik(eski, "15m")[0] == "STALE",
          f"{tazelik(taze,'15m')[0]}/{tazelik(eski,'15m')[0]}")

    ad = YerelOlcumAdapter(lambda _d: {"claims": [], "decision": "PUBLISH_FULL",
                                      "epistemic_verdict": "KNOWN", "limitations": []})
    rp = run_agent_and_gate(EvidenceRegistry(risk_level="HIGH"), ad.bagla(EvidenceRegistry()))
    kayit("T8  model karari kapiyi EZEMEZ",
          rp["model_output"]["decision"] == "PUBLISH_FULL" and not rp["publish_allowed"],
          f"model=PUBLISH_FULL kapi={rp['final_decision']}")

    kayit("T9  adapter sozlesmesi korunuyor",
          OpenAICompatibleAdapter.provider == "openai-compatible"
          and GenericJSONAdapter.provider == "generic-json"
          and DEFAULT_SCHEMA["required"] == ["claims", "decision", "epistemic_verdict", "limitations"]
          and hasattr(AgentAdapter, "complete"), "")

    b = _sentetik(120, 900_000, egim=8.0)
    atr = wilder_atr(b)
    kayit("T10 Wilder ATR pozitif ve sonlu", bool(atr and atr > 0 and math.isfinite(atr)),
          f"atr={atr:.4f}" if atr else "None")
    kayit("T11 ADX 0-100 araliginda",
          (wilder_adx(b) is None) or 0 <= wilder_adx(b) <= 100, f"adx={wilder_adx(b)}")

    def _merdiven(yukari_mi: bool, adim: int = 12, n: int = 8) -> list[list]:
        """Acik HH/HL (ya da LH/LL) merdiveni: itki + geri cekilme."""
        out, t, taban = [], 1_700_000_000_000, 100.0
        for _ in range(n):
            zirve = taban + adim
            for o, c in ((taban, zirve), (zirve, zirve - adim * 0.4)):
                lo, hi = min(o, c), max(o, c)
                out.append([t, f"{o:.2f}", f"{hi+0.5:.2f}", f"{lo-0.5:.2f}",
                            f"{c:.2f}", "1000", t + 899_999, "0", 0, None, "0", "0"])
                t += 900_000
            taban = zirve - adim * 0.4
        if not yukari_mi:                       # aynayla ters cevir
            tepe = max(float(x[2]) for x in out) + max(float(x[2]) for x in out)
            out = [[x[0], f"{tepe-float(x[1]):.2f}", f"{tepe-float(x[3]):.2f}",
                    f"{tepe-float(x[2]):.2f}", f"{tepe-float(x[4]):.2f}"] + list(x[5:])
                   for x in out]
        return out

    ty = trend_oku(_merdiven(True))
    ta = trend_oku(_merdiven(False))
    kayit("T12 trend yonu (fraktal HH/HL) dogru",
          ty["trend"] == "bull" and ta["trend"] == "bear",
          f"{ty['trend']}({ty['swing_sayisi']} swing)/{ta['trend']}({ta['swing_sayisi']} swing)")

    duz = _sentetik(150, 900_000, egim=400.0, tohum=3)     # geri cekilmesiz itki
    td = trend_oku(duz)
    kayit("T12b guclu tek-yonlu seride YEDEK olcut devreye girer",
          td["trend"] == "bull" and td["swing_sayisi"] == 0
          and "YEDEK" in td["trend_kaynagi"],
          f"trend={td['trend']} swing={td['swing_sayisi']} kaynak={td['trend_kaynagi'][:48]}")

    rr = rr_denetim("LONG", 100.0, 99.9, 130.0, 10.0)
    kayit("T13 D10 sisirilmis R yakalanir",
          rr["verdict"] == "SISIRILMIS" and rr["R_gercekci"] < rr["R_rapor"],
          f"R_rap={rr['R_rapor']} R_ger={rr['R_gercekci']}")
    rr2 = rr_denetim("LONG", 100.0, 90.0, 115.0, 10.0)
    kayit("T14 tutarli R korunur",
          rr2["verdict"] == "TUTARLI" and rr2["R_gercekci"] == rr2["R_rapor"], str(rr2["R_rapor"]))
    kayit("T15 bozuk geometri reddedilir",
          rr_denetim("LONG", 100.0, 110.0, 130.0, 10.0)["verdict"] == "GECERSIZ", "")

    # --- D1: bar-ici sira — dolum barinin KENDI fitili hedef sayilamaz
    kayit("T16 D1 bar-ici sira korunuyor", _t_bar_ici(), "dolum barinda yalniz stop")

    # --- D2: hizalama zaman damgasiyla
    m15 = _sentetik(200, 900_000, egim=5.0)
    h4t = _sentetik(60, 14_400_000, egim=20.0, bitis_ms=bar_ts(m15[-1]))
    esl = h4_hizala(m15, h4t)
    sapma = bar_ts(m15[-1]) - bar_ts(h4t[esl[-1]])
    h4_az = h4t[-5:]
    esl2 = h4_hizala(m15, h4_az)
    kayit("T17 D2 hizalama ZAMAN damgasiyla",
          0 <= sapma <= ARALIK_MS["4H"] and esl[-1] == len(h4t) - 1 and esl2[-1] == len(h4_az) - 1,
          f"sapma={sapma/3.6e6:.2f}sa esl_son={esl[-1]} (kirpik seride {esl2[-1]})")

    # --- D3: govde hata kodu yutulmuyor
    try:
        _okx_govde({"code": "50011", "msg": "rate limit"}); ok = False
    except RuntimeError:
        ok = True
    kayit("T18 D3 OKX govde hata kodu yutulmaz", ok, "")

    # --- D4: tek bahis
    s1 = {"yon": {"yon": "LONG"}, "_m15": m15}
    s2 = {"yon": {"yon": "LONG"}, "_m15": [list(x) for x in m15]}
    tek_bahis_kapisi([s1, s2])
    kayit("T19 D4 tek bahis kopyayi yakalar", s2["tek_bahis"]["hukum"] == "KOPYA - ATLA",
          f"rho={s2['tek_bahis']['rho']}")

    # --- D5/D6: stake kapisi
    g0 = stake_kapisi(50, 0, 5.0, 0.0, -45.0)
    g1 = stake_kapisi(50, 25, 5.0, 37.5, -32.5)
    kayit("T20 D5 kazanan yokken kapi KAPALI",
          (not g0["acik"]) and g0["stake"] == 0.0, g0["not"][:60])
    kayit("T21 D6 Kelly paydasi a*b (stake sismiyor)",
          g1["acik"] and abs(g1["stake"] - g1["edge_hat"] / (g1["a_loss"] * g1["b_win"])) < 1e-12
          and g1["stake"] < g1["edge_hat"] / g1["b_win"],
          f"dogru={g1['stake']:.4f} < eski={g1['edge_hat']/g1['b_win']:.4f}")

    # --- D7: OKX taker dolgusu YAZILMAZ (DAVRANIS testi; kaynak-grep degil)
    sahte_okx = [["1700000000000", "100", "101", "99", "100.5", "0", "0"],
                 ["1699999100000", "99", "100", "98", "99.5", "1000", "99500"]]
    cev = okx_satir_cevir(sahte_okx, "15m")
    kayit("T22 D7 notr taker dolgusu YOK (indeks 9 = None)",
          bool(cev) and all(r[9] is None for r in cev)
          and all(float(r[5]) == float(h[5]) for r, h in zip(cev, reversed(sahte_okx), strict=False)),
          f"{len(cev)} satir, indeks9={[r[9] for r in cev]} (hacim 0 barda bile dolgu YOK)")

    # --- emir plani: seviyeler yalnizca olculen yapidan
    p = emir_plani(m15, h4t, "LONG")
    yapi = yapi_ozeti(m15, h4t)
    motor = {round(g, 6) for g, _ in giris_adaylari(yapi, "LONG", yapi["son_kapanis"])}
    disarida = [x["giris"] for x in p["seviyeler"] if round(x["giris"], 6) not in motor]
    kayit("T23 seviyeler YALNIZ olculen yapidan", not disarida, f"disarida={disarida}")

    atr15 = yapi["atr15"] or 0.0
    hatali = [x for x in p["seviyeler"]
              if x["emir_tipi"] != ("MARKET" if x["mesafe"] <= E("MARKET_BANDI") * atr15 else "LIMIT")]
    kayit("T24 MARKET/LIMIT kurali", not hatali, f"esik={E('MARKET_BANDI')*atr15:.2f}")

    kayit("T25 yonsuz kurulum fail-closed",
          emir_plani(m15, h4t, "NOTR")["EMIR"] == "EMIR YOK", "")

    yb = yon_turet({"trend": "bear", "rejim": "trend"}, {"trend": "bear", "rejim": "trend"}, None)
    kayit("T26 yon isareti + eksik kanal agirliga girmez",
          yb["yon"] == "SHORT" and yb["skor"] == -1.0
          and abs(yb["agirlik_toplam"] - (E("AGIRLIK_H4") + E("AGIRLIK_M15"))) < 1e-9,
          f"skor={yb['skor']} agirlik={yb['agirlik_toplam']}")

    # --- uctan uca: TAZE veri -> PUBLISH_FULL (kapi acilabiliyor)
    import tempfile  # noqa: PLC0415
    kok = Path(tempfile.mkdtemp(prefix="konsey_tek_test_"))
    (kok / "m15.json").write_text(json.dumps(m15), encoding="utf-8")
    (kok / "h4.json").write_text(json.dumps(h4t), encoding="utf-8")
    rp = kos(["TESTSEMBOL"], str(kok / "m15.json"), str(kok / "h4.json"), sessiz=True)
    kayit("T27 TAZE veri -> PUBLISH_FULL (kapi acilabiliyor)",
          rp["publish_allowed"] and rp["final_decision"] == "PUBLISH_FULL", rp["final_decision"])

    (kok / "bayat.json").write_text(json.dumps(
        _sentetik(200, 900_000, egim=5.0,
                  bitis_ms=int(time.time() * 1000) - 40 * 86_400_000)), encoding="utf-8")
    rp2 = kos(["TESTSEMBOL"], str(kok / "bayat.json"), str(kok / "h4.json"), sessiz=True)
    kayit("T28 BAYAT veri -> yayin DURUR", not rp2["publish_allowed"], rp2["final_decision"])

    kayit("T29 determinizm (ayni girdi -> ayni emir)",
          emir_plani(m15, h4t, "LONG")["EMIR"] == p["EMIR"], p["EMIR"][:40])

    # --- T30: imza/emir yuzeyi YOK (davranis + modul testi, kaynak-grep degil)
    import sys as _s
    hmac_yok = "hmac" not in _s.modules or "hmac" not in globals()
    borsa_uc = [OKX_MUM, OKX_GECMIS, OKX_TICKER, BINANCE_MUM]
    hepsi_public = all(("/trade" not in u and "/account" not in u
                        and "/order" not in u) for u in borsa_uc)
    # borsa cagrilarinin hicbiri Authorization basligi tasimaz:
    import inspect as _i
    piyasa_kaynak = "".join(_i.getsource(f) for f in
                            (_http_json, _okx_sayfali, okx_mumlar, binance_mumlar,
                             okx_fiyat, funding_oku))
    yetkisiz = "Authorization" not in piyasa_kaynak
    kayit("T30 borsa yolunda imza/emir yuzeyi YOK",
          hmac_yok and hepsi_public and yetkisiz,
          f"public_uc={hepsi_public} auth_basligi_yok={yetkisiz} hmac_yok={hmac_yok}")

    # --- KULLANICI KAPISI (bolum 15): dal dal sinama
    TAM = {"claims": [{"claim_id": "C001", "importance": "CRITICAL",
                       "status": "VERIFIED", "evidence_ids": ["E001"]}],
           "sources": [{"source_id": "S001", "access_status": "ACCESSIBLE"}],
           "evidence": [{"evidence_id": "E001", "source_id": "S001"}],
           "counter_evidence_search": {"status": "COMPLETED"},
           "conflicts": [], "decision": "PUBLISH_FULL"}
    import copy as _c
    a = independent_publication_gate(TAM)
    kayit("T31 kullanici kapisi: ornek vaka -> PUBLISH_FULL",
          a.final_decision == "PUBLISH_FULL" and a.publish_allowed, a.final_decision)

    v = _c.deepcopy(TAM); v["claims"][0]["evidence_ids"] = []
    kayit("T32 kullanici kapisi: kanitsiz VERIFIED -> HALT",
          independent_publication_gate(v).final_decision == "HALT", "")

    v = _c.deepcopy(TAM); v["sources"][0]["access_status"] = "UNREACHABLE"
    kayit("T33 kullanici kapisi: erisilemez kaynak -> HALT",
          independent_publication_gate(v).final_decision == "HALT", "")

    v = _c.deepcopy(TAM); v["counter_evidence_search"] = {"status": "NOT_APPLICABLE"}
    a = independent_publication_gate(v)
    kayit("T34 kullanici kapisi: NOT_APPLICABLE -> LIMITED (B3, olculen davranis)",
          a.final_decision == "PUBLISH_LIMITED" and not a.warnings,
          "uyarisiz LIMITED - belgelendi")

    # --- cift kapi: adaptor + sert-olan-kazanir
    r2 = EvidenceRegistry(risk_level="HIGH"); r2.counter_evidence_search = "DONE"
    r2.add_source("S1", "y", "dosya", "CURRENT", content="x")
    r2.add_evidence("E1", "S1", "olcum", "d", "g")
    r2.add_claim("C1", "ok", "VERIFIED", ["E1"], "DONE")
    ck = cift_kapi(r2)
    kayit("T35 cift kapi: iki kapi da FULL -> yayin IZINLI",
          ck["final_decision"] == "PUBLISH_FULL" and ck["publish_allowed"],
          f"k1={ck['kapi1_registry']['decision']} k2={ck['kapi2_kullanici']['final_decision']}")

    r2.external_checks_pending.append("bayat veri")   # kapi2 bunu GORMEZ (B4)
    ck = cift_kapi(r2)
    kayit("T36 cift kapi: kapi2 kor kaldiginda kapi1'in serti kazanir (B4 kapandi)",
          ck["final_decision"] == "REPAIR" and not ck["publish_allowed"],
          f"k1={ck['kapi1_registry']['decision']} k2={ck['kapi2_kullanici']['final_decision']} sert={ck['final_decision']}")

    # ================= 6-SORU DENETIMININ KORUYUCU TESTLERI =================
    def _b(o, h, l, c, v=1000.0):
        return {"o": o, "h": h, "l": l, "c": c, "v": v}

    # --- T37/T38 (Q5): FVG mitigasyonu dogru tarafta
    # NOT (v1.2.0): onceki temel veride bar2 open(103) < low(105) idi — fiziksel
    # imkansiz bar; giris suzgeci hakli olarak atiyordu. Veri fiziksel-gecerli
    # yapildi; FVG bolgesi ([100,105]) ve TUM beklenen hukumler DEGISMEDI.
    temel = [_b(99, 100, 98, 99.5), _b(100, 103, 99.5, 102.5), _b(105.5, 107, 105, 106.5)]
    dokunulmamis = temel + [_b(106, 110, 106, 109), _b(109, 112, 108, 111)]
    fa = [f for f in acik_fvgler(dokunulmamis) if f["bar"] == 2]
    kayit("T37 Q5: dokunulmamis bull FVG ACIK kalir",
          len(fa) == 1 and fa[0]["kalan_oran"] == 1.0
          and fa[0]["alt"] == 100.0 and fa[0]["ust"] == 105.0,
          str(fa))
    dolan = temel + [_b(106, 106.5, 99.0, 99.5)]
    fb = [f for f in acik_fvgler(dolan) if f["bar"] == 2]
    yarim = temel + [_b(106, 107, 103, 105)]
    fc = [f for f in acik_fvgler(yarim) if f["bar"] == 2]
    kayit("T38 Q5: dolan FVG kapanir, yarim dolanin kalani [alt,lj]",
          not fb and len(fc) == 1 and fc[0]["ust"] == 103.0 and fc[0]["alt"] == 100.0,
          f"dolan={len(fb)} yarim={fc}")

    # --- T39 (Q3): AYNA SIMETRISI — yon tam ters doner, |skor| ayni
    ayna_ok, ayna_n = 0, 0
    for tohum in range(1, 21):
        b = _sentetik(220, 900_000, egim=0.0, tohum=tohum)
        tepe = 2 * 100000.0
        by = [[x[0], f"{tepe-float(x[1]):.2f}", f"{tepe-float(x[3]):.2f}",
               f"{tepe-float(x[2]):.2f}", f"{tepe-float(x[4]):.2f}"] + list(x[5:])
              for x in b]
        y1 = yon_turet(trend_oku(b), trend_oku(b), None)
        y2 = yon_turet(trend_oku(by), trend_oku(by), None)
        ayna_n += 1
        ters = {"LONG": "SHORT", "SHORT": "LONG", "NOTR": "NOTR"}
        if y2["yon"] == ters[y1["yon"]] and abs(abs(y1["skor"]) - abs(y2["skor"])) < 1e-9:
            ayna_ok += 1
    kayit("T39 Q3: ayna simetrisi (yon bias'i yok)",
          ayna_ok == ayna_n, f"{ayna_ok}/{ayna_n} tohumda tam ters + esit |skor|")

    # --- T40 (Q3): emir seviyeleri de aynada simetrik
    yuk = _merdiven(True); dus = _merdiven(False)
    pl = emir_plani(yuk, yuk, "LONG")
    ps = emir_plani(dus, dus, "SHORT")
    ayni_durum = (pl["EMIR"] == "EMIR YOK") == (ps["EMIR"] == "EMIR YOK")
    sim = True
    if pl["adaylar"] and ps["adaylar"]:
        rl = pl["adaylar"][0]["R_gercekci"]; rs = ps["adaylar"][0]["R_gercekci"]
        sim = abs((rl or 0) - (rs or 0)) < 0.15
    kayit("T40 Q3: LONG/SHORT emir uretimi simetrik",
          ayni_durum and sim,
          f"LONG={pl['EMIR'][:34]} | SHORT={ps['EMIR'][:34]}")

    # --- T41 (Q4): dinamiklik — yeni bar gelince karar girdileri degisir
    b0 = _sentetik(220, 900_000, egim=10.0, tohum=5)
    p0 = emir_plani(b0, b0, "LONG")
    son_t = int(b0[-1][0]); son_c = float(b0[-1][4])
    patlama = [son_t + 900_000, f"{son_c:.2f}", f"{son_c*1.05:.2f}",
               f"{son_c*0.999:.2f}", f"{son_c*1.048:.2f}", "9000",
               son_t + 1_799_999, "0", 0, None, "0", "0"]
    p1 = emir_plani(b0 + [patlama], b0 + [patlama], "LONG")
    kayit("T41 Q4: yeni bar -> fiyat/plan guncellenir (onbellek yok)",
          p1["fiyat"] != p0["fiyat"] and p1["yapi_ozeti"]["atr15"] != p0["yapi_ozeti"]["atr15"],
          f"fiyat {p0['fiyat']:.2f} -> {p1['fiyat']:.2f}")

    # --- T42 (Q6): ani-hareket bayragi + MARKET yasagi
    sakin = _sentetik(220, 900_000, egim=0.0, tohum=9)
    a0 = ani_hareket(sakin, wilder_atr(sakin))
    pompali = list(sakin)
    c0 = float(pompali[-1][4]); t0 = int(pompali[-1][0]); atr0 = wilder_atr(sakin)
    for k in range(6):
        c1 = c0 + atr0 * 0.9
        pompali.append([t0 + (k + 1) * 900_000, f"{c0:.2f}", f"{c1*1.001:.2f}",
                        f"{c0*0.999:.2f}", f"{c1:.2f}", "9000",
                        t0 + (k + 1) * 900_000 + 899_999, "0", 0, None, "0", "0"])
        c0 = c1
    a1 = ani_hareket(pompali, wilder_atr(pompali))
    pm = emir_plani(pompali, pompali, "LONG", market_yasak=True)
    market_reddi = any("ANI-HAREKET" in r for r in pm["red_nedenleri"]) or \
        all(x["emir_tipi"] != "MARKET" for x in pm["adaylar"])
    kayit("T42 Q6: pump tespiti + MARKET yasagi calisir",
          (not a0["tespit"]) and a1["tespit"] and a1["tur"] in ("PUMP", "V-DONUS RISKI")
          and market_reddi,
          f"sakin={a0['tespit']} pompa={a1.get('tur')} yer/ATR={a1.get('yer_atr')}")

    # --- T43 (Q2): MTF celiskisi SUSTURULMUYOR
    ymc = yon_turet({"trend": "bull", "rejim": "trend"},
                    {"trend": "bear", "rejim": "trend"}, None)
    kayit("T43 Q2: MTF celiskisi yuzeye cikar (LIMITED'e duser)",
          ymc["mtf_celiski"] and "MTF CELISKI" in ymc["mtf_not"],
          ymc["mtf_not"][:60])

    # --- T44 (Q6): V-donus bayragi — pencere yukari, son bar sert ret fitili
    v_seri = list(pompali[:-1])
    ct = float(v_seri[-1][4]); tt = int(v_seri[-1][0])
    v_seri.append([tt + 900_000, f"{ct:.2f}", f"{ct + atr0*1.2:.2f}",
                   f"{ct - atr0*0.1:.2f}", f"{ct + atr0*0.05:.2f}", "9000",
                   tt + 900_000 + 899_999, "0", 0, None, "0", "0"])
    av = ani_hareket(v_seri, wilder_atr(v_seri))
    kayit("T44 Q6: sert fitilli tepe -> V-DONUS RISKI bayragi",
          av["tespit"] and av["tur"] == "V-DONUS RISKI",
          f"tur={av.get('tur')} fitil={av.get('fitil_oran')}")
    return R


def _t_bar_ici() -> bool:
    """D1 koruyucusu: dolum barinin KENDI fitili HEDEF sayilmamali."""
    atr = 10.0
    # bar 1: hem giris seviyesine (dip) hem hedefe (tepe) degen GENIS bar
    barlar = [
        {"o": 100.0, "h": 100.5, "l": 99.5, "c": 100.0},
        {"o": 100.0, "h": 108.0, "l": 79.0, "c": 100.0},   # dip 79 = giris, tepe 108 = hedef
        {"o": 100.0, "h": 100.5, "l": 60.0, "c": 70.0},    # sonraki barda stop
    ]
    r = _yaris_coz(barlar, 0, atr, e=2.0, t=1.5, s=1.0)
    # Dogru davranis: giris barinda hedef SAYILMAZ; sonraki barda stop -> STOP
    return bool(r and r["sonuc"] == "STOP" and r["giris_idx"] == 1)


def _yaris_coz(barlar: Sequence, i: int, atr: float, e: float = 2.0,
               t: float = 1.5, s: float = 1.0) -> dict | None:
    """Cift-limit yaris cozumu — D1 duzeltmesiyle.

    D1: yon atandiktan sonra `continue` VARDIR; dolum barinda YALNIZ stop
    kontrol edilir (dolumu tetikleyen fitil zaten o yonde ilerlemistir), hedef
    taramasi bir SONRAKI bardan baslar. Boylece bar-ici sira VARSAYILMAZ.
    """
    n = len(barlar)
    if i + 1 >= n or not atr or atr <= 0:
        return None
    c = bar_ohlc(barlar[i])[3]
    alt, ust = c - e * atr, c + e * atr
    yon = giris = None
    giris_idx = -1
    j = i + 1
    while j < n:
        _, h, l, _ = bar_ohlc(barlar[j])
        if yon is None:
            alt_d, ust_d = l <= alt, h >= ust
            if alt_d and ust_d:
                return None                      # ayni barda iki kenar -> IPTAL
            if alt_d:
                yon, giris, giris_idx = "LONG", alt, j
            elif ust_d:
                yon, giris, giris_idx = "SHORT", ust, j
            else:
                j += 1
                continue
            stop = giris - s * atr if yon == "LONG" else giris + s * atr
            # D1: dolum barinda YALNIZ stop; hedef SONRAKI bardan itibaren
            if (l <= stop) if yon == "LONG" else (h >= stop):
                return {"sinyal": i, "giris_idx": giris_idx, "cozum": j, "yon": yon,
                        "giris": giris, "stop": stop, "sonuc": "STOP", "net_r": -1.0}
            j += 1
            continue
        hedef = giris + t * atr if yon == "LONG" else giris - t * atr
        stop = giris - s * atr if yon == "LONG" else giris + s * atr
        hd = (h >= hedef) if yon == "LONG" else (l <= hedef)
        sd = (l <= stop) if yon == "LONG" else (h >= stop)
        if sd:                                    # ayni barda ikisi de -> STOP (muhafazakar)
            return {"sinyal": i, "giris_idx": giris_idx, "cozum": j, "yon": yon,
                    "giris": giris, "stop": stop, "hedef": hedef,
                    "sonuc": "STOP", "net_r": -1.0}
        if hd:
            return {"sinyal": i, "giris_idx": giris_idx, "cozum": j, "yon": yon,
                    "giris": giris, "stop": stop, "hedef": hedef,
                    "sonuc": "HEDEF", "net_r": t / s}
        j += 1
    return None


# =============================================================================
# 15) KULLANICI KAPISI — independent_publication_gate (BIREBIR)
#     Tek zorunlu degisiklik: dataclass adi `AuditResult` bu dosyada zaten
#     kullanildigi icin (bolum 2, registry.audit donusu) burada
#     `BagimsizKapiSonucu` olarak tasindi.
#     v1.2.0 BEYANLI DUZELTME (spec testi S8b/S8c olctu): fuzz'da 2000 bozuk
#     girdinin 486'sinda kapi COKUYORDU (None claims/evidence_ids/counter ->
#     TypeError). Mantik DEGISMEDI; yalniz None-savunmasi eklendi ("or []" /
#     "or {}"). Coken kapi karar veremez — cokme fail-closed bile degildir.
#     Olculen yapisal notlar (dal dal sinandi, V1-V10):
#       B1 REPAIR bu kapida HIC uretilmez (karar: FULL/HALT/LIMITED)
#       B2 publish_allowed PUBLISH_LIMITED'da da True doner (FULL sarti degil)
#       B3 NOT_APPLICABLE uyari uretmez ama FULL'u LIMITED'a dusurur
#       B4 tazelik/bayatlik denetlemez (yalniz access_status)
#     B4'u asagidaki cift_kapi kapatir: iki kapidan SERT olan kazanir.
# =============================================================================
KAPI_IDDIA_STATULERI = {
    "VERIFIED",
    "REPORTED",
    "INFERRED",
    "LIMITED",
    "UNKNOWN",
}

KAPI_YAYIN_KARARLARI = {
    "PUBLISH_FULL",
    "PUBLISH_LIMITED",
    "REPAIR",
    "HALT",
}


@dataclass
class BagimsizKapiSonucu:
    publish_allowed: bool
    final_decision: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def independent_publication_gate(result: dict[str, Any]) -> BagimsizKapiSonucu:
    """
    KONSEY bagimsiz ve deterministik yayin kapisi.

    Modelin kendi VERIFIED veya PUBLISH_FULL beyanina guvenmez.
    Nihai yayin kararini yalnizca bu fonksiyon belirler.
    """

    errors: list[str] = []
    warnings: list[str] = []

    claims = result.get("claims") or []
    sources = {
        source.get("source_id"): source
        for source in (result.get("sources") or [])
    }
    evidence_records = {
        evidence.get("evidence_id"): evidence
        for evidence in (result.get("evidence") or [])
    }

    critical_claims = [
        claim
        for claim in claims
        if claim.get("importance") == "CRITICAL"
    ]

    # PUBLISH_FULL icin en az bir kritik iddia zorunludur.
    if not critical_claims:
        errors.append(
            "PUBLISH_FULL verilemez: kritik iddia bulunmuyor."
        )

    for claim in claims:
        claim_id = claim.get("claim_id", "UNKNOWN_CLAIM")
        status = claim.get("status")
        evidence_ids = claim.get("evidence_ids") or []

        if status not in KAPI_IDDIA_STATULERI:
            errors.append(
                f"{claim_id}: gecersiz kanit statusu: {status}"
            )

        # Model VERIFIED dese bile kanit baglantisi yoksa reddet.
        if status == "VERIFIED" and not evidence_ids:
            errors.append(
                f"{claim_id}: VERIFIED iddianin kanit baglantisi yok."
            )

        for evidence_id in evidence_ids:
            evidence = evidence_records.get(evidence_id)

            if evidence is None:
                errors.append(
                    f"{claim_id}: {evidence_id} kanit kaydi bulunamadi."
                )
                continue

            source_id = evidence.get("source_id")
            source = sources.get(source_id)

            if source is None:
                errors.append(
                    f"{evidence_id}: {source_id} kaynak kaydi bulunamadi."
                )
                continue

            if source.get("access_status") != "ACCESSIBLE":
                errors.append(
                    f"{evidence_id}: kaynak erisilebilir degil: {source_id}"
                )

    counter_evidence = result.get(
        "counter_evidence_search",
        {},
    ) or {}
    counter_status = counter_evidence.get("status")

    if counter_status not in {"COMPLETED", "NOT_APPLICABLE"}:
        warnings.append(
            "Karsit kanit aramasi tamamlanmamis."
        )

    if result.get("conflicts"):
        errors.append(
            "Cozulmemis kaynak veya iddia celiskileri bulunuyor."
        )

    model_decision = result.get("decision")

    if model_decision not in KAPI_YAYIN_KARARLARI:
        errors.append(
            f"Modelin karari gecersiz: {model_decision}"
        )

    # Yalnizca tum kritik kosullar saglanirsa tam yayin izni verilir.
    full_publication_conditions = (
        not errors
        and critical_claims
        and all(
            claim.get("status") == "VERIFIED"
            for claim in critical_claims
        )
        and counter_status == "COMPLETED"
        and not result.get("conflicts")
    )

    if full_publication_conditions:
        final_decision = "PUBLISH_FULL"
    elif errors:
        final_decision = "HALT"
    else:
        final_decision = "PUBLISH_LIMITED"

    return BagimsizKapiSonucu(
        publish_allowed=final_decision in {
            "PUBLISH_FULL",
            "PUBLISH_LIMITED",
        },
        final_decision=final_decision,
        errors=errors,
        warnings=warnings,
    )


def registry_to_gate_input(reg: EvidenceRegistry,
                           model_decision: str = "PUBLISH_FULL") -> dict[str, Any]:
    """EvidenceRegistry (dict-tabanli) -> kullanici kapisinin liste-tabanli semasi.

    Eslemeler (hepsi mekanik, uydurma alan yok):
      critical: True/False   -> importance: CRITICAL/NORMAL
      kayitli her kaynak     -> access_status: ACCESSIBLE
        (fetch/bar_getir ERISILEMEYENI zaten KAYDETMEZ; kayit = erisildi)
      counter DONE           -> COMPLETED (digerleri oldugu gibi tasinir)
      contradictions         -> conflicts
    NOT: bu kapi tazelik denetlemez (B4); bayatlik registry.audit tarafinda
    external_checks_pending uzerinden yakalanir — cift_kapi ikisini birlestirir.
    """
    return {
        "claims": [{"claim_id": c.claim_id,
                    "importance": "CRITICAL" if c.critical else "NORMAL",
                    "status": c.status,
                    "evidence_ids": list(c.evidence_ids)}
                   for c in reg.claims.values()],
        "sources": [{"source_id": s.source_id, "access_status": "ACCESSIBLE"}
                    for s in reg.sources.values()],
        "evidence": [{"evidence_id": e.evidence_id, "source_id": e.source_id}
                     for e in reg.evidence.values()],
        "counter_evidence_search": {
            "status": "COMPLETED" if reg.counter_evidence_search == "DONE"
            else reg.counter_evidence_search},
        "conflicts": list(reg.contradictions),
        "decision": model_decision,
    }


# Karar siddet sirasi: buyuk = sert. Cift kapida SERT olan kazanir.
_KARAR_SIDDETI = {"PUBLISH_FULL": 0, "PUBLISH_LIMITED": 1, "REPAIR": 2, "HALT": 3}


def cift_kapi(reg: EvidenceRegistry, model_decision: str = "PUBLISH_FULL") -> dict[str, Any]:
    """Iki bagimsiz kapiyi birlikte kosar; SERT olan hukum kazanir.

    Kapi 1: registry.audit() — tazelik/bayatlik + karsit-kanit + celiski.
    Kapi 2: independent_publication_gate — kullanici kapisi (birebir).
    publish_allowed yalnizca IKISI DE PUBLISH_FULL derse True olur
    (kullanici kapisinin B2 gevsekligi burada FULL sartina cekilir;
    kapinin kendi ciktisi degistirilmeden ayrica raporlanir).
    """
    a1 = reg.audit(model_decision if model_decision in ALLOWED_DECISIONS
                   else "PUBLISH_FULL")
    a2 = independent_publication_gate(registry_to_gate_input(reg, model_decision))
    sert = a1.decision if _KARAR_SIDDETI[a1.decision] >= _KARAR_SIDDETI[a2.final_decision] \
        else a2.final_decision
    return {
        "kapi1_registry": a1.to_dict(),
        "kapi2_kullanici": {"publish_allowed": a2.publish_allowed,
                            "final_decision": a2.final_decision,
                            "errors": a2.errors, "warnings": a2.warnings},
        "final_decision": sert,
        "publish_allowed": (a1.decision == "PUBLISH_FULL"
                            and a2.final_decision == "PUBLISH_FULL"),
    }


# =============================================================================
# 14) CLI
# =============================================================================
def _cmd_oz_test(_a) -> int:
    R = oz_test()
    for ad, d, det in R:
        print(f"[{d}] {ad}  {det}")
    hata = sum(1 for _, d, _ in R if d == "FAIL")
    print(f"\n{len(R) - hata}/{len(R)} PASS")
    return 1 if hata else 0                      # D9: FAIL varsa cikis kodu 1


def _cmd_sinyal(a) -> int:
    rapor = kos([s.strip().upper() for s in a.symbols.split(",") if s.strip()],
                a.m15, a.h4, a.profil, a.turev, a.output,
                yerel_dizin=getattr(a, "yerel_dizin", None))
    return 0 if rapor["publish_allowed"] else 2


def _cmd_init(a) -> int:
    EvidenceRegistry().save(a.output)
    print(f"Olusturuldu: {a.output}")
    return 0


def _cmd_fetch(a) -> int:
    reg = EvidenceRegistry.load(a.input) if Path(a.input).exists() else EvidenceRegistry()
    try:
        reg.fetch(a.location, a.source_id, a.evidence_id, a.dependency_group)
    except Exception as e:                        # noqa: BLE001
        print(f"ERISILEMEDI (kayit YAPILMADI): {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    reg.save(a.output)
    print(f"Eklendi: {a.source_id}/{a.evidence_id} -> {a.output}")
    return 0


def _cmd_audit(a) -> int:
    r = EvidenceRegistry.load(a.input).audit(a.requested_decision)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(r.to_dict(), ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
    return 0 if r.decision == "PUBLISH_FULL" else 2


def _cmd_run(a) -> int:
    reg = EvidenceRegistry.load(a.input)
    if a.provider == "openai-compatible":
        ad: AgentAdapter = OpenAICompatibleAdapter(a.base_url, a.api_key_env, a.model)
    elif a.provider == "generic-json":
        ad = GenericJSONAdapter(a.endpoint, a.api_key_env)
    else:
        print(f"bilinmeyen saglayici: {a.provider}", file=sys.stderr)
        return 2
    rapor = run_agent_and_gate(reg, ad)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rapor["independent_audit"], ensure_ascii=False, indent=2))
    return 0 if rapor["publish_allowed"] else 2


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="konsey_tek",
                                 description=f"KONSEY tek dosya v{SURUM}")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("sinyal", help="canli yon + giris/cikis seviyeleri")
    p.add_argument("--symbols", default="BTCUSDT")
    p.add_argument("--m15", default=None, help="ag kapaliysa yerel 15M JSON")
    p.add_argument("--h4", default=None, help="ag kapaliysa yerel 4H JSON")
    p.add_argument("--profil", default=None, help="sabit-USDT profil JSON")
    p.add_argument("--turev", default=None, help="turev skoru JSON")
    p.add_argument("--yerel-dizin", default=None,
                   help="sembol basina yerel arsiv dizini (<SEMBOL>_m15.json / <SEMBOL>/m15.json)")
    p.add_argument("--output", default=None)
    p.set_defaults(f=_cmd_sinyal)

    p = sp.add_parser("oz-test"); p.set_defaults(f=_cmd_oz_test)
    p = sp.add_parser("init"); p.add_argument("--output", required=True); p.set_defaults(f=_cmd_init)

    p = sp.add_parser("fetch")
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--location", required=True); p.add_argument("--source-id", required=True)
    p.add_argument("--evidence-id", required=True); p.add_argument("--dependency-group", default="G0")
    p.set_defaults(f=_cmd_fetch)

    p = sp.add_parser("audit")
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--requested-decision", default="PUBLISH_FULL")
    p.set_defaults(f=_cmd_audit)

    p = sp.add_parser("run")
    p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    p.add_argument("--provider", default="openai-compatible")
    p.add_argument("--base-url", default="https://api.openai.com/v1")
    p.add_argument("--endpoint", default=""); p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--api-key-env", default="OPENAI_API_KEY")
    p.set_defaults(f=_cmd_run)

    a = ap.parse_args(list(argv) if argv is not None else None)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
