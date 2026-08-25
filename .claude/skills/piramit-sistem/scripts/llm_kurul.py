#!/usr/bin/env python3
"""LLM KURULU — Kimi K3 ↔ Kimi Code adversarial tartışması.

Piramidin LLM merceğini Opus/Claude yerine İKİ KİMİ MODELİ koşturur ve onları
BİRBİRİNE KARŞI tartıştırır. Çıktı, kurula iki danışman olarak girer:
`kimi-k3` (tez) ve `kimi-code` (antitez).

Neden iki model: tek modelin kendi anlatısını doğrulaması DAİRESEL'dir. İkinci
model BİRİNCİNİN ÇIKTISINI GÖRÜR ve onu ÇÜRÜTMEKLE görevlidir. Anlaşırlarsa
güven artar, çelişirlerse ikisi de kurula girer ve K4/K5 kapıları karar verir.

Sözleşme:
  · Sayı UYDURULMAZ. Modele YALNIZ motorların ölçtüğü sayılar verilir; modelden
    yalnız YÖN + GÜVEN + GEREKÇE istenir. Modelin ürettiği yeni sayı ATILIR.
  · Güven tavanı `llm_tavan` (0.50) — LLM okuması ÖLÇÜM DEĞİLDİR, tıpkı
    gorsel-teyit gibi tavanla sınırlanır.
  · Anahtar/ağ yoksa ya da model şema dışı cevap verirse → "VERİ YOK",
    danışman EKLENMEZ (fail-closed). Sessiz varsayılan yok.

Anahtar: KIMI_API_KEY (yoksa MOONSHOT_API_KEY, yoksa ANTHROPIC_AUTH_TOKEN).
Uç    : KIMI_BASE_URL (varsayılan https://api.moonshot.ai/anthropic)

Kullanım:
    python3 llm_kurul.py --job job.json          # job: {"kanit": {...}}
    python3 llm_kurul.py --job job.json --out engine/girdi/llm_kurul.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

YOK = "VERİ YOK"

KONVANSIYON = {
    "llm_tavan": 0.50,        # LLM danışmanının azami güveni (ölçüm değil)
    "zaman_asimi": 90,        # saniye
    "azami_token": 1200,
    "model_tez": "kimi-k3",           # tez: kanıtı okur, yön önerir
    "model_antitez": "kimi-k2.7-code",  # antitez: tezi ÇÜRÜTMEKLE görevli
    "taban_uc": "https://api.moonshot.ai/anthropic",
}

SEMA = ("SADECE şu JSON'u döndür, başka hiçbir şey yazma:\n"
        '{"yon":"long|short|flat","guven":0.0-1.0,"gerekce":"<en fazla 2 cümle,'
        ' YALNIZ sana verilen sayılara atıf yap>","curutme":"<varsa karşı '
        'argümanın zayıf noktası, yoksa null>"}')

ROL_TEZ = (
    "Sen bir vadeli piyasa analisti danışmanısın. Sana AŞAĞIDAKİ ÖLÇÜLMÜŞ motor "
    "çıktıları verildi. Görevin: bu kanıttan bir YÖN çıkarmak.\n"
    "KATI KURALLAR:\n"
    "1. Sana verilmeyen HİÇBİR sayıyı kullanma, üretme, tahmin etme.\n"
    "2. Fiyat seviyesi, hedef, stop UYDURMA — onları motorlar üretir.\n"
    "3. Kanıt zayıfsa 'flat' de ve güveni düşük tut. Emin gibi davranma.\n"
    "4. Hikâye anlatma; gerekçe en fazla 2 cümle ve sayıya bağlı olsun.\n")

ROL_ANTITEZ = (
    "Sen bir ŞÜPHECİ denetçisin. Aynı ölçülmüş motor çıktıları ve BİR BAŞKA "
    "MODELİN vardığı sonuç sana verildi. Görevin o sonucu ÇÜRÜTMEYE çalışmak.\n"
    "KATI KURALLAR:\n"
    "1. Sana verilmeyen HİÇBİR sayıyı kullanma, üretme, tahmin etme.\n"
    "2. Diğer modele katılmak için baskı hissetme; kanıt onu desteklemiyorsa "
    "karşı yönü ya da 'flat' söyle.\n"
    "3. Kanıt gerçekten onu destekliyorsa katıl — muhalefet için muhalefet etme.\n"
    "4. 'curutme' alanına diğer modelin en zayıf noktasını yaz.\n")


class KurulError(Exception):
    pass


def _anahtar() -> str | None:
    for ad in ("KIMI_API_KEY", "MOONSHOT_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        v = (os.environ.get(ad) or "").strip()
        if v and not v.startswith("BURAYA"):
            return v
    return None


def _cagir(model: str, sistem: str, kullanici: str, anahtar: str,
           taban: str, p: dict) -> dict:
    """Anthropic-uyumlu /v1/messages çağrısı. Hata → KurulError (uydurma yok)."""
    url = taban.rstrip("/") + "/v1/messages"
    govde = json.dumps({
        "model": model,
        "max_tokens": int(p["azami_token"]),
        "system": sistem,
        "messages": [{"role": "user", "content": kullanici}],
    }).encode("utf-8")
    istek = urllib.request.Request(url, data=govde, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": anahtar,
        "authorization": f"Bearer {anahtar}",
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(istek, timeout=int(p["zaman_asimi"])) as r:
            ham = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detay = e.read().decode("utf-8", "replace")[:200]
        raise KurulError(f"HTTP {e.code} — {detay}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise KurulError(f"ağ: {type(e).__name__}: {e}") from e
    except json.JSONDecodeError as e:
        raise KurulError(f"cevap JSON değil: {e}") from e

    parcalar = [b.get("text", "") for b in (ham.get("content") or [])
                if isinstance(b, dict) and b.get("type") == "text"]
    metin = "".join(parcalar).strip()
    if not metin:
        raise KurulError("model boş metin döndürdü")
    return _sema_ayikla(metin)


def _sema_ayikla(metin: str) -> dict:
    """Modelin cevabından şemayı çıkar. Şema tutmuyorsa hata (fail-closed)."""
    s, e = metin.find("{"), metin.rfind("}")
    if s < 0 or e <= s:
        raise KurulError(f"şema yok: {metin[:120]}")
    try:
        d = json.loads(metin[s:e + 1])
    except json.JSONDecodeError as ex:
        raise KurulError(f"şema bozuk: {ex}") from ex
    yon = str(d.get("yon", "")).strip().lower()
    if yon not in ("long", "short", "flat"):
        raise KurulError(f"geçersiz yön: {yon!r}")
    try:
        guven = float(d.get("guven"))
    except (TypeError, ValueError) as ex:
        raise KurulError("güven sayı değil") from ex
    if not 0.0 <= guven <= 1.0:
        raise KurulError(f"güven aralık dışı: {guven}")
    return {"yon": yon, "guven": guven,
            "gerekce": str(d.get("gerekce") or "")[:400],
            "curutme": (str(d["curutme"])[:400]
                        if d.get("curutme") not in (None, "", "null") else None)}


def _kanit_metni(kanit: dict) -> str:
    """Modele giden kanıt — YALNIZ motorların ölçtüğü sayılar, düz metin."""
    satir = ["ÖLÇÜLMÜŞ MOTOR ÇIKTILARI (başka veri yok):"]
    for ad, v in (kanit or {}).items():
        satir.append(f"- {ad}: {json.dumps(v, ensure_ascii=False)[:600]}")
    return "\n".join(satir) if len(satir) > 1 else f"- {YOK}"


def kurul(job: dict) -> dict:
    p = {**KONVANSIYON, **(job.get("esikler") or {})}
    taban = (job.get("taban_uc") or os.environ.get("KIMI_BASE_URL")
             or p["taban_uc"])
    anahtar = job.get("anahtar") or _anahtar()
    kanit = job.get("kanit") or {}
    ortak = {"taban_uc": taban, "model_tez": p["model_tez"],
             "model_antitez": p["model_antitez"], "llm_tavan": p["llm_tavan"]}

    if not anahtar:
        return {"durum": f"{YOK} — API anahtarı yok (KIMI_API_KEY / "
                         "MOONSHOT_API_KEY / ANTHROPIC_AUTH_TOKEN)",
                "danismanlar": [], **ortak}
    if not kanit:
        return {"durum": f"{YOK} — kanıt boş, modele soru sorulmadı "
                         "(fail-closed)", "danismanlar": [], **ortak}

    metin = _kanit_metni(kanit)
    danismanlar, hatalar = [], []
    tavan = float(p["llm_tavan"])

    # ---- 1) TEZ: kimi-k3 --------------------------------------------------
    tez = None
    try:
        tez = _cagir(p["model_tez"], ROL_TEZ + "\n" + SEMA, metin,
                     anahtar, taban, p)
        danismanlar.append({
            "name": "kimi-k3", "stance": tez["yon"],
            "confidence": round(min(tez["guven"], tavan), 4),
            "evidence": f"Kimi K3 (tez): {tez['gerekce']}",
            "_kaynak": "LLM OKUMASI (ölçüm değil)", "_ham_guven": tez["guven"]})
    except KurulError as e:
        hatalar.append(f"{p['model_tez']}: {e}")

    # ---- 2) ANTİTEZ: kimi-code, tezi görerek ------------------------------
    if tez is not None:
        karsi = (metin + "\n\nDİĞER MODELİN SONUCU (çürütmeye çalış):\n"
                 + json.dumps({"yon": tez["yon"], "guven": tez["guven"],
                               "gerekce": tez["gerekce"]}, ensure_ascii=False))
        try:
            anti = _cagir(p["model_antitez"], ROL_ANTITEZ + "\n" + SEMA, karsi,
                          anahtar, taban, p)
            danismanlar.append({
                "name": "kimi-code", "stance": anti["yon"],
                "confidence": round(min(anti["guven"], tavan), 4),
                "evidence": f"Kimi Code (antitez): {anti['gerekce']}"
                            + (f" | çürütme: {anti['curutme']}"
                               if anti["curutme"] else ""),
                "_kaynak": "LLM OKUMASI (ölçüm değil)",
                "_ham_guven": anti["guven"]})
        except KurulError as e:
            hatalar.append(f"{p['model_antitez']}: {e}")

    # ---- 3) TARTIŞMA HÜKMÜ ------------------------------------------------
    if len(danismanlar) == 2:
        a, b = danismanlar[0]["stance"], danismanlar[1]["stance"]
        if a == b:
            hukum = f"UZLAŞI — iki model de {a}"
        elif "flat" in (a, b):
            hukum = f"KISMİ AYRIŞMA — {a} vs {b}"
        else:
            hukum = (f"ÇELİŞKİ — {a} vs {b}; iki danışman da kurula girer, "
                     "kapılar karar verir (fail-closed)")
    elif danismanlar:
        hukum = ("TEK TARAFLI — antitez alınamadı, tez tek başına kurula girer "
                 "(dairesellik riski: gözlemci TÜNEL uyarısı verebilir)")
    else:
        hukum = f"{YOK} — hiçbir model cevap vermedi"

    return {"durum": "koştu" if danismanlar else f"{YOK} — model cevabı yok",
            "HUKUM": hukum, "danismanlar": danismanlar,
            "hatalar": hatalar, **ortak,
            "varsayimlar": [
                f"LLM güven tavanı {tavan} (okuma ölçüm değildir)",
                "modele YALNIZ motor sayıları verildi; ürettiği yeni sayı ATILIR",
                "antitez modeli tezi GÖRÜR — bağımsız değil, kasten adversarial"],
            "not": "Karar-destek; canlı/otomatik emir DAHİL DEĞİL."}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kimi K3 ↔ Kimi Code kurulu")
    ap.add_argument("--job", required=True)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        job = json.loads(Path(a.job).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"durum": f"job okunamadı: {e}", "danismanlar": []},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    r = kurul(job)
    metin = json.dumps(r, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).expanduser().parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).expanduser().write_text(metin + "\n", encoding="utf-8")
    print(metin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
