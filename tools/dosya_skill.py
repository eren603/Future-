#!/usr/bin/env python3
"""Dosya → skill hattı — bir belgeyi otomatik SKILL.md iskelesine çevirir.

K2.6/K3'ün "dosyayı agent skill'e çevir" yeteneğinin yerel karşılığı. belge_ingest
ile içeriği çıkarır, sık geçen anlamlı kelimelerden TETİKLEYİCİ üretir, başlıkları
bölümlere döker ve geçerli bir SKILL.md yazar. İçeriği UYDURMAZ — yalnız dosyadan
çıkanı yapılandırır; boşsa "VERİ YOK".

Kullanım:
  python3 tools/dosya_skill.py --file notlar.md --name benim-becerim \
      --out .claude/skills/benim-becerim/SKILL.md
  (ya da build_skill() import et)
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import belge_ingest  # noqa: E402


class SkillError(Exception):
    pass

# çok sık/anlamsız kelimeler (TR+EN) — tetikleyiciye alınmaz
_STOP = set("""
ve veya ile için gibi daha çok bir bu şu o da de ki mi mu ama fakat çünkü
the a an and or of to in on for with is are be this that it as at by from
""".split())


def _text_of(ing: dict) -> str:
    if "text" in ing and ing["text"]:
        return ing["text"]
    if ing.get("type") == "docx":
        return "\n".join(ing.get("paragraphs", []))
    if ing.get("type") in ("csv", "tsv"):
        return "\n".join(" ".join(map(str, r)) for r in ing.get("rows", []))
    if ing.get("type") == "xlsx":
        parts = []
        for rows in ing.get("sheets", {}).values():
            for r in rows:
                parts.append(" ".join(str(c) for c in r if c is not None))
        return "\n".join(parts)
    if ing.get("type") == "json":
        return json.dumps(ing.get("data", {}), ensure_ascii=False)
    return ""


def _triggers(text: str, k: int = 12) -> list[str]:
    words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{4,}", text.lower())
    freq = Counter(w for w in words if w not in _STOP)
    return [w for w, _ in freq.most_common(k)]


def _headings(text: str) -> list[str]:
    heads = []
    for ln in text.splitlines():
        s = ln.strip()
        if re.match(r"^#{1,6}\s+\S", s):          # markdown başlık
            heads.append(re.sub(r"^#{1,6}\s+", "", s))
        elif s and len(s) <= 60 and s.endswith(":"):  # "Başlık:" kalıbı
            heads.append(s.rstrip(":"))
    return heads[:20]


def build_skill(file: str, name: str) -> str:
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,48}$", name):
        raise SkillError("name: küçük harf/rakam/tire, 2–49 karakter olmalı")
    ing = belge_ingest.ingest(file)
    text = _text_of(ing).strip()
    if not text:
        raise SkillError("VERİ YOK: dosyadan metin çıkmadı — skill üretilmez")
    trig = _triggers(text)
    heads = _headings(text)
    trig_line = ", ".join(trig) if trig else name
    desc = (f"{name} becerisi — '{Path(file).name}' belgesinden otomatik "
            f"üretildi. Tetikleyici kelimeler: {trig_line}.")

    body = [f"---\nname: {name}\ndescription: >-\n  {desc}\n---\n",
            f"# {name}", "",
            f"> Bu iskele `{Path(file).name}` belgesinden `dosya_skill.py` ile "
            "otomatik üretildi. İçeriği gözden geçir, motor/akış ekle.", ""]
    if trig:
        body += ["## Tetikleyiciler", ", ".join(trig), ""]
    if heads:
        body += ["## Bölümler (belge başlıklarından)"]
        for h in heads:
            body.append(f"### {h}\n(içeriği doldur)\n")
    else:
        # başlık yoksa ilk paragrafları özet olarak koy
        snippet = text[:800].strip()
        body += ["## İçerik özeti", snippet, ""]
    body += ["## Doğruluk sözleşmesi",
             "- Uydurma yok; eksik veri VERİ YOK.",
             "- Her sayısal iddia bir dayanağa bağlanır.", ""]
    return "\n".join(body)


def main() -> int:
    ap = argparse.ArgumentParser(description="Dosya → SKILL.md iskelesi")
    ap.add_argument("--file", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", default=None, help="yazılacak SKILL.md yolu")
    args = ap.parse_args()
    try:
        md = build_skill(args.file, args.name)
    except (SkillError, belge_ingest.IngestError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(json.dumps({"ok": True, "written": str(out),
                          "bytes": len(md)}, ensure_ascii=False))
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
