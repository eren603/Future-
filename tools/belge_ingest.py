#!/usr/bin/env python3
"""Belge + video ingest — KAPALI HAT (host modelin görüşüne bağlı değil).

Dosyayı yerelde yapılandırılmış veriye çevirir; hayalden metin üretmez, çıkaramazsa
"VERİ YOK" işaretler (fail-closed). Ek bağımlılık YOK: ofis belgeleri stdlib
zipfile+xml, PDF zlib ile; video ffmpeg/ffprobe ile.

Desteklenen: .xlsx .docx .pdf .csv .tsv .json .md .txt ve video (.mp4/.mov/.webm/.mkv/.avi)

Kullanım:
  python3 belge_ingest.py --file rapor.xlsx
  python3 belge_ingest.py --file klip.mp4 --frames-dir /tmp/kareler --fps 0.5
  (ya da ingest() import et)
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path


class IngestError(Exception):
    pass


def _localname(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


# --------------------------------------------------------------------------- #
# XLSX  (OOXML = zip + xml, harici kütüphane gerekmez)
# --------------------------------------------------------------------------- #
def read_xlsx(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        # paylaşılan dizeler
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root:
                txt = "".join(t.text or "" for t in si.iter()
                              if _localname(t.tag) == "t")
                shared.append(txt)
        # sayfa adları
        sheet_names = []
        if "xl/workbook.xml" in names:
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            for e in wb.iter():
                if _localname(e.tag) == "sheet":
                    sheet_names.append(e.get("name", "?"))
        sheets = {}
        sheet_files = sorted(n for n in names
                             if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        for i, sf in enumerate(sheet_files):
            root = ET.fromstring(z.read(sf))
            rows = []
            for row in root.iter():
                if _localname(row.tag) != "row":
                    continue
                cells = []
                for c in row:
                    if _localname(c.tag) != "c":
                        continue
                    t = c.get("t")
                    val = None
                    for ch in c:
                        if _localname(ch.tag) == "v":
                            val = ch.text
                        elif _localname(ch.tag) == "is":
                            val = "".join(x.text or "" for x in ch.iter()
                                          if _localname(x.tag) == "t")
                    if t == "s" and val is not None:
                        try:
                            val = shared[int(val)]
                        except (ValueError, IndexError):
                            pass
                    cells.append(val)
                if any(x is not None for x in cells):
                    rows.append(cells)
            name = sheet_names[i] if i < len(sheet_names) else f"sheet{i+1}"
            sheets[name] = rows
    total = sum(len(r) for r in sheets.values())
    if total == 0:
        raise IngestError("VERİ YOK: xlsx boş ya da okunamadı")
    return {"type": "xlsx", "sheets": sheets,
            "row_counts": {k: len(v) for k, v in sheets.items()}}


# --------------------------------------------------------------------------- #
# DOCX
# --------------------------------------------------------------------------- #
def read_docx(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        if "word/document.xml" not in z.namelist():
            raise IngestError("VERİ YOK: word/document.xml yok")
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []
    for p in root.iter():
        if _localname(p.tag) != "p":
            continue
        txt = "".join(t.text or "" for t in p.iter()
                      if _localname(t.tag) == "t")
        if txt.strip():
            paras.append(txt)
    if not paras:
        raise IngestError("VERİ YOK: docx metni çıkarılamadı")
    return {"type": "docx", "paragraphs": paras,
            "text": "\n".join(paras), "para_count": len(paras)}


# --------------------------------------------------------------------------- #
# PDF  (best-effort: FlateDecode akışları zlib ile açılır, Tj/TJ metni çekilir)
# --------------------------------------------------------------------------- #
def read_pdf(path: Path) -> dict:
    raw = path.read_bytes()
    chunks = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.DOTALL):
        data = m.group(1)
        try:
            data = zlib.decompress(data)
        except zlib.error:
            continue
        # ( ... ) ve <hex> içindeki metin parçaları
        for tm in re.finditer(rb"\((?:\\.|[^\\()])*\)", data):
            s = tm.group(0)[1:-1]
            s = re.sub(rb"\\([()\\])", rb"\1", s)
            try:
                chunks.append(s.decode("latin-1"))
            except Exception:
                pass
    text = " ".join(chunks).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return {"type": "pdf", "text": "",
                "note": "VERİ YOK: metin çıkarılamadı (taranmış/şifreli olabilir; "
                        "OCR ya da pypdf gerekir)", "extracted": False}
    return {"type": "pdf", "text": text, "char_count": len(text),
            "extracted": True,
            "note": "best-effort çıkarım — doğruluğu kaynakla teyit et"}


# --------------------------------------------------------------------------- #
# Düz metin / tablo
# --------------------------------------------------------------------------- #
def read_text(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()
    if ext == ".json":
        try:
            return {"type": "json", "data": json.loads(txt)}
        except json.JSONDecodeError as e:
            raise IngestError(f"VERİ YOK: geçersiz JSON ({e})")
    if ext in (".csv", ".tsv"):
        sep = "\t" if ext == ".tsv" else ","
        rows = [ln.split(sep) for ln in txt.splitlines() if ln.strip()]
        if not rows:
            raise IngestError("VERİ YOK: tablo boş")
        return {"type": ext[1:], "rows": rows, "row_count": len(rows)}
    return {"type": "text", "text": txt, "char_count": len(txt)}


# --------------------------------------------------------------------------- #
# Video → kareler (ffmpeg). Kapalı hat: kareler grafik-calisma'ya beslenmeye hazır.
# --------------------------------------------------------------------------- #
def read_video(path: Path, frames_dir: Path, fps: float) -> dict:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(path)], capture_output=True, text=True)
    meta = {}
    if probe.returncode == 0:
        try:
            meta = json.loads(probe.stdout)
        except json.JSONDecodeError:
            meta = {}
    frames_dir.mkdir(parents=True, exist_ok=True)
    out_pat = str(frames_dir / "kare_%04d.png")
    ex = subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-vf", f"fps={fps}", out_pat],
        capture_output=True, text=True)
    if ex.returncode != 0:
        raise IngestError(f"VERİ YOK: ffmpeg kare çıkaramadı: {ex.stderr[-300:]}")
    frames = sorted(str(p) for p in frames_dir.glob("kare_*.png"))
    if not frames:
        raise IngestError("VERİ YOK: kare üretilmedi")
    dur = None
    try:
        dur = float(meta.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        pass
    return {"type": "video", "frames": frames, "frame_count": len(frames),
            "fps_extracted": fps, "duration_sec": dur,
            "next": "kareler grafik-calisma/scripts/smc_tespit.py'ye beslenmeye hazır"}


_TEXTLIKE = {".csv", ".tsv", ".json", ".md", ".txt", ".log"}
_VIDEO = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}


def ingest(file: str, frames_dir: str | None = None, fps: float = 0.5) -> dict:
    path = Path(file).expanduser()
    if not path.exists():
        raise IngestError(f"VERİ YOK: dosya yok: {path}")
    ext = path.suffix.lower()
    if ext == ".xlsx":
        return read_xlsx(path)
    if ext == ".docx":
        return read_docx(path)
    if ext == ".pdf":
        return read_pdf(path)
    if ext in _VIDEO:
        fd = Path(frames_dir) if frames_dir else path.with_suffix("").parent / (path.stem + "_kareler")
        return read_video(path, fd, fps)
    if ext in _TEXTLIKE:
        return read_text(path)
    raise IngestError(f"desteklenmeyen uzantı: {ext}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Belge/video ingest — kapalı hat")
    ap.add_argument("--file", required=True)
    ap.add_argument("--frames-dir", default=None)
    ap.add_argument("--fps", type=float, default=0.5)
    args = ap.parse_args()
    try:
        res = ingest(args.file, args.frames_dir, args.fps)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    except IngestError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
