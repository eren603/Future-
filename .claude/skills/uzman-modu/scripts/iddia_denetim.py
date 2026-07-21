#!/usr/bin/env python3
"""İddia Denetçisi — "ikinci göz". Cevap yayınlanmadan önce her iddiayı
mekanik olarak sınar. Süslü/hafızadan/dairesel/dayanaksız iddiayı KARANTİNA'ya alır.

Girdi JSON:
{
  "claims": [
    {"id":"c1","text":"BTC 4h golden zone geri test etti",
     "type":"gerçek","evidence":"grafik-calisma motoru: 0.618 seviyesi 24170",
     "verified":true},
    {"id":"c2","text":"Bu yükseliş devam eder","type":"yorum","evidence":"","verified":false}
  ]
}

Kurallar (fail-closed):
- type ∈ {gerçek, varsayım, yorum}. Başka değer → hata.
- 'gerçek' iddia: evidence DOLU + verified=true olmalı; değilse KARANTİNA.
- 'varsayım'/'yorum': etiketli olması yeterli (kabul), ama dayanaksız 'gerçek'
  gibi sunulmamalı.
- Dairesellik: evidence boşsa VEYA evidence ≈ text (kendine atıf) → KARANTİNA
  (hafızadan/dairesel işareti).
- Herhangi bir 'gerçek' iddia KARANTİNA ise genel sonuç REVİZE (yayınlama).
Determinist — rastgelelik yok.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

VALID_TYPES = {"gerçek", "gercek", "varsayım", "varsayim", "yorum"}
FACT = {"gerçek", "gercek"}


class DenetimError(Exception):
    pass


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _circular(text: str, evidence: str) -> bool:
    t, e = _norm(text), _norm(evidence)
    if not e:
        return True
    # kanıt metnin kendisiyse veya metnin alt-dizesiyse: dairesel/kendine-atıf
    if e == t:
        return True
    if len(e) >= 8 and (e in t or t in e):
        return True
    return False


def audit_claim(c: dict) -> dict:
    cid = str(c.get("id", "?"))
    text = str(c.get("text", "")).strip()
    ctype = _norm(c.get("type", ""))
    evidence = str(c.get("evidence", "")).strip()
    verified = bool(c.get("verified", False))
    if not text:
        raise DenetimError(f"{cid}: boş iddia metni")
    if ctype not in VALID_TYPES:
        raise DenetimError(f"{cid}: geçersiz type '{c.get('type')}' (gerçek/varsayım/yorum)")

    reasons = []
    verdict = "GEÇTİ"

    if ctype in FACT:
        # Kanıt/doğrulama/dairesellik kapıları YALNIZ 'gerçek' iddialara uygulanır
        if _circular(text, evidence):
            verdict = "KARANTİNA"
            reasons.append("dayanaksız/dairesel: kanıt yok ya da kendine atıf (hafızadan)")
        if not evidence:
            verdict = "KARANTİNA"; reasons.append("'gerçek' iddia kanıtsız")
        if not verified:
            verdict = "KARANTİNA"; reasons.append("'gerçek' iddia ikinci gözle doğrulanmadı")
    else:
        # varsayım/yorum: etiketli olduğu sürece kabul (kanıt aranmaz)
        reasons.append("etiketli varsayım/yorum — kabul; 'gerçek' gibi sunma")

    return {"id": cid, "type": ctype, "verdict": verdict,
            "reasons": reasons, "text": text}


def run_job(job: dict) -> dict:
    claims = job.get("claims") or []
    if not claims:
        raise DenetimError("En az 1 iddia gerekli")
    audited = [audit_claim(c) for c in claims]
    quarantined = [a for a in audited if a["verdict"] == "KARANTİNA"]
    fact_quarantined = [a for a in quarantined if a["type"] in FACT]
    overall = "REVİZE" if fact_quarantined else "YAYINLANABİLİR"
    return {
        "genel_sonuc": overall,
        "toplam": len(audited),
        "gecti": sum(1 for a in audited if a["verdict"] == "GEÇTİ"),
        "karantina": len(quarantined),
        "revize_gerekce": ([a["id"] for a in fact_quarantined] or None),
        "iddia_denetimi": audited,
        "not": ("Dayanaksız 'gerçek' iddia(lar) var → cevabı yayınlama, düzelt."
                if overall == "REVİZE" else
                "Tüm 'gerçek' iddialar kanıtlı ve doğrulandı."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="İddia denetçisi (ikinci göz)")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(run_job(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
