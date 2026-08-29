"""Provider-independent adapters for OpenAI-compatible and generic JSON agents."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.request import Request, urlopen

from .core import EvidenceRegistry


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
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "")
        self.model = model
        self.timeout = timeout
        if not self.api_key:
            raise ValueError(f"API anahtarı bulunamadı: {api_key_env}")

    def complete(self, system: str, user: str, schema: dict | None = None) -> AgentResponse:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
        }
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "konsey_result", "schema": schema}}
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            raw = json.loads(response.read().decode())
        message = raw["choices"][0]["message"]["content"]
        structured = None
        if schema:
            structured = json.loads(message) if isinstance(message, str) else message
        return AgentResponse(self.provider, raw, message if isinstance(message, str) else json.dumps(message), structured)


class GenericJSONAdapter(AgentAdapter):
    """Call an arbitrary endpoint that accepts JSON and returns JSON.

    Request and response field names can be mapped by the caller. This keeps
    the core engine independent from any one vendor's API contract.
    """
    provider = "generic-json"

    def __init__(self, endpoint: str, api_key_env: str | None = None, timeout: int = 90):
        self.endpoint = endpoint
        self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        self.timeout = timeout

    def complete(self, system: str, user: str, schema: dict | None = None) -> AgentResponse:
        payload = {"system": system, "user": user, "schema": schema}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(self.endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=self.timeout) as response:
            raw = json.loads(response.read().decode())
        structured = raw.get("structured") or raw.get("result") or raw.get("output")
        text = raw.get("text", "")
        return AgentResponse(self.provider, raw, text, structured if isinstance(structured, dict) else None)


def build_prompt(registry: EvidenceRegistry) -> tuple[str, str]:
    system = (
        "KONSEY kanıt protokolünü uygula. Modelin kendi doğrulama beyanını kanıt sayma. "
        "Yalnızca verilen kaynak ve kanıt kayıtlarına dayan. Kritik iddiaları CLAIM_ID ve "
        "EVIDENCE_ID ile bağla; bilinmeyeni UNKNOWN bırak; karşıt kanıt ve sınırlılıkları yaz. "
        "Comparison-article görevinde karar odaklı ve dengeli çıktı üret."
    )
    user = json.dumps(registry.to_dict(), ensure_ascii=False, indent=2)
    return system, user


# ---------------------------------------------------------------------------
# EK BAGLAYICI — README s.58: "Yeni bir ajan icin bu siniflardan birini kullan
# veya AgentAdapter.complete() sozlesmesini uygulayan yeni bir baglayici yaz."
# Bu baglayici AG GEREKTIRMEZ: LLM isleyisini deponun OLCEN motorlariyla
# yurutur (smc_tespit / karar_motoru / turev_akis / emir_plani). Cikti yine
# yalnizca `model_output`tur; nihai karari core.EvidenceRegistry.audit verir.
# ---------------------------------------------------------------------------
class YerelOlcumAdapter(AgentAdapter):
    """Ag gerektirmeyen yerel ajan: kararini SADECE registry kayitlarindan uretir.

    `complete()` cagrildiginda registry'deki olculmus kanit satirlarini okur ve
    DEFAULT_SCHEMA'ya uyan yapili sonucu dondurur. Hicbir sayi uydurmaz: her
    alan bir EVIDENCE_ID'ye baglidir, baglanamayan alan UNKNOWN kalir.
    """
    provider = "yerel-olcum"

    def __init__(self, karar_fn):
        # karar_fn(registry_dict) -> structured dict  (sinyal.py saglar)
        self.karar_fn = karar_fn
        self._registry_dict: dict | None = None

    def bagla(self, registry) -> "YerelOlcumAdapter":
        self._registry_dict = registry.to_dict()
        return self

    def complete(self, system: str, user: str, schema: dict | None = None) -> AgentResponse:
        veri = self._registry_dict if self._registry_dict is not None else json.loads(user)
        structured = self.karar_fn(veri)
        return AgentResponse(self.provider, {"system": system, "kaynak": "yerel-olcum"},
                             json.dumps(structured, ensure_ascii=False), structured)
