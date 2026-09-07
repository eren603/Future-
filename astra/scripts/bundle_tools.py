#!/usr/bin/env python3
"""ASTRA belge <-> paket araçları.

  extract  <belge.md> <hedef_dizin>   : gömülü dosyaları çıkarır, manifest hash/boyut denetler
  build    <kaynak_dizin> <sablon.md> <cikti.md> : dizindeki dosyaları belgeye gömer,
                                        BUNDLE_MANIFEST.json'ı yeniden üretir
  verify   <belge.md>                   : yalnız envanter + hash denetimi (dosya yazmaz)

Hash kimlik doğrulama imzası değildir; yalnız içerik bütünlüğü denetimidir.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BLOCK = re.compile(
    r"<!-- BEGIN FILE: ([^>]+) -->\n```(python|json|markdown|text)\n(.*?)\n```\n<!-- END FILE -->",
    re.S,
)
LANG = {".py": "python", ".json": "json", ".md": "markdown", ".txt": "text"}


def blocks(doc: str) -> list[tuple[str, str, str]]:
    return [(name, lang, body) for name, lang, body in BLOCK.findall(doc)]


def check_paths(names):
    for name in names:
        p = Path(name)
        if p.is_absolute() or ".." in p.parts:
            raise SystemExit(f"Unsafe embedded path: {name}")


def verify(doc_path: Path) -> dict:
    doc = doc_path.read_text(encoding="utf-8")
    found = blocks(doc)
    names = [n for n, _, _ in found]
    if len(names) != len(set(names)):
        raise SystemExit("Duplicate embedded file names")
    check_paths(names)
    by_name = {n: body for n, _, body in found}
    if "BUNDLE_MANIFEST.json" not in by_name:
        raise SystemExit("BUNDLE_MANIFEST.json missing")
    manifest = json.loads(by_name["BUNDLE_MANIFEST.json"])
    listed = {r["path"] for r in manifest["files"]}
    embedded = set(names) - {"BUNDLE_MANIFEST.json"}
    if listed != embedded:
        raise SystemExit(f"Manifest inventory mismatch: only-manifest={sorted(listed-embedded)} only-doc={sorted(embedded-listed)}")
    bad = []
    for record in manifest["files"]:
        raw = by_name[record["path"]].encode("utf-8")
        if len(raw) != record["size_bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
            bad.append(record["path"])
    if bad:
        raise SystemExit("Content hash mismatch: " + ", ".join(bad))
    return {"files": len(names), "manifest_files": len(listed), "ok": True}


def extract(doc_path: Path, target: Path) -> None:
    verify(doc_path)
    doc = doc_path.read_text(encoding="utf-8")
    target.mkdir(parents=True, exist_ok=False)
    for name, _, body in blocks(doc):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    print("Extracted:", target.resolve())


def build(source: Path, template: Path, output: Path, version: str) -> None:
    """Belgedeki gömülü blokları `source` dizinindeki güncel dosyalarla değiştirir.

    Şablon: gömülü bloklar bölümü '**Gömülü dosyalar**' başlığından sonra gelir;
    bu başlıktan önceki metin olduğu gibi korunur, sonrası yeniden üretilir.
    """
    files = sorted(p for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    records, embedded = [], {}
    for p in files:
        rel = p.relative_to(source).as_posix()
        raw = p.read_bytes()
        text = raw.decode("utf-8")
        embedded[rel] = text
        if rel != "BUNDLE_MANIFEST.json":
            records.append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)})
    manifest = {"version": version, "created_at": datetime.now(timezone.utc).isoformat(), "files": records}
    embedded["BUNDLE_MANIFEST.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (source / "BUNDLE_MANIFEST.json").write_text(embedded["BUNDLE_MANIFEST.json"], encoding="utf-8")
    head = template.read_text(encoding="utf-8")
    marker = "**Gömülü dosyalar**"
    if marker not in head:
        raise SystemExit("Template lacks the embedded-files marker")
    head = head.split(marker)[0] + marker + "\n\n"
    parts = [head]
    order = ["BUNDLE_MANIFEST.json"] + sorted(n for n in embedded if n != "BUNDLE_MANIFEST.json")
    for name in order:
        lang = LANG.get(Path(name).suffix, "text")
        parts.append(f"\n<!-- BEGIN FILE: {name} -->\n```{lang}\n{embedded[name]}\n```\n<!-- END FILE -->\n\n")
    output.write_text("".join(parts), encoding="utf-8")
    print("Built:", output, "files:", len(embedded))


def main(argv):
    if len(argv) >= 3 and argv[1] == "extract":
        extract(Path(argv[2]), Path(argv[3]))
    elif len(argv) >= 5 and argv[1] == "build":
        build(Path(argv[2]), Path(argv[3]), Path(argv[4]), argv[5] if len(argv) > 5 else "1.4")
    elif len(argv) >= 3 and argv[1] == "verify":
        print(json.dumps(verify(Path(argv[2]))))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
