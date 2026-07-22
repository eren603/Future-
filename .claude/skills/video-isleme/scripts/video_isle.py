#!/usr/bin/env python3
"""Video işleme motoru — kendi-kendini onaran (ffmpeg yoksa kurar).

Yaptıkları:
1. ensure_ffmpeg: ffmpeg/ffprobe yoksa apt-get ile kurar (idempotent).
   Kurulamazsa hatayı AÇIKÇA raporlar — sessiz başarısızlık yok.
2. probe: süre, çözünürlük, fps, codec (ffprobe JSON).
3. Kare çıkarma:
   - mode="scene": sahne-değişimi tespiti (select=gt(scene,esik)); bulunan
     sahne sayısı max_frames'in yarısından azsa uniform örneklemeyle tamamlar.
   - mode="uniform": eşit aralıklı max_frames kare.
   Kareler PNG olarak out_dir'e yazılır; rapor zaman damgalarını listeler.

Girdi JSON:
{"input":"video.mp4","out_dir":"frames","max_frames":12,
 "mode":"scene","scene_esik":0.3}

Determinist: aynı video + aynı parametre = aynı kareler.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULTS = {"max_frames": 12, "mode": "scene", "scene_esik": 0.3}


class VideoError(Exception):
    pass


def ensure_ffmpeg() -> dict:
    """ffmpeg/ffprobe garantisi. Yoksa kurar; kuramazsa açık hata döner."""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return {"ffmpeg": "hazır"}
    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
    steps = [["apt-get", "update", "-qq"],
             ["apt-get", "install", "-y", "-qq", "ffmpeg"]]
    for cmd in steps:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True,
                           timeout=600)
        if r.returncode != 0:
            raise VideoError(
                "ffmpeg kurulamadı (sessiz geçilmiyor): "
                f"`{' '.join(cmd)}` rc={r.returncode}: {r.stderr[-400:]}")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise VideoError("Kurulum bitti ama ffmpeg/ffprobe hâlâ PATH'te yok")
    return {"ffmpeg": "şimdi kuruldu"}


def _run(cmd: list, timeout: int = 600) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise VideoError(f"`{cmd[0]}` hata rc={r.returncode}: {r.stderr[-400:]}")
    return r


def probe(path: Path) -> dict:
    r = _run(["ffprobe", "-v", "error", "-print_format", "json",
              "-show_format", "-show_streams", str(path)])
    meta = json.loads(r.stdout)
    v = next((s for s in meta.get("streams", [])
              if s.get("codec_type") == "video"), None)
    if v is None:
        raise VideoError("Dosyada video akışı yok")
    dur = float(meta.get("format", {}).get("duration") or 0.0)
    num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
    try:
        fps = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        fps = None
    return {"sure_sn": round(dur, 3), "genislik": v.get("width"),
            "yukseklik": v.get("height"), "codec": v.get("codec_name"),
            "fps": round(fps, 3) if fps else "VERİ YOK"}


def _scene_times(path: Path, esik: float, dur: float) -> list:
    """Sahne değişim zamanları (saniye)."""
    r = _run(["ffmpeg", "-i", str(path), "-vf",
              f"select='gt(scene,{esik})',showinfo",
              "-f", "null", "-"])
    times = []
    for line in r.stderr.splitlines():
        if "showinfo" in line and "pts_time:" in line:
            try:
                t = float(line.split("pts_time:")[1].split()[0])
                if 0.0 <= t <= dur + 1:
                    times.append(round(t, 3))
            except (ValueError, IndexError):
                continue
    return sorted(set(times))


def _grab(path: Path, t: float, out_png: Path):
    _run(["ffmpeg", "-y", "-ss", f"{max(t, 0.0):.3f}", "-i", str(path),
          "-frames:v", "1", "-q:v", "2", str(out_png)])


def isle(job: dict) -> dict:
    p = {**DEFAULTS, **job}
    src = Path(str(p.get("input", ""))).expanduser()
    if not src.exists():
        raise VideoError(f"Girdi dosyası yok: {src}")
    out_dir = Path(str(p.get("out_dir") or (src.parent / "frames"))).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    max_frames = int(p["max_frames"])

    kurulum = ensure_ffmpeg()
    meta = probe(src)
    dur = float(meta["sure_sn"])
    if dur <= 0:
        raise VideoError("Video süresi okunamadı/sıfır")

    times = []
    kaynak = p["mode"]
    if p["mode"] == "scene":
        times = _scene_times(src, float(p["scene_esik"]), dur)[:max_frames]
        if len(times) < max(2, max_frames // 2):
            kaynak = f"scene({len(times)})+uniform tamamlama"
            n_uni = max_frames - len(times)
            uni = [round(dur * (i + 0.5) / n_uni, 3) for i in range(n_uni)]
            times = sorted(set(times + uni))[:max_frames]
    else:
        times = [round(dur * (i + 0.5) / max_frames, 3) for i in range(max_frames)]

    frames = []
    for i, t in enumerate(times):
        png = out_dir / f"kare_{i:03d}_t{t:.2f}s.png"
        _grab(src, t, png)
        if png.exists() and png.stat().st_size > 0:
            frames.append({"dosya": str(png), "t_sn": t})

    if not frames:
        raise VideoError("Hiç kare çıkarılamadı")

    return {"girdi": str(src), "kurulum": kurulum, "metadata": meta,
            "ornekleme": kaynak, "kare_sayisi": len(frames), "kareler": frames,
            "not": ("Kareler anlık görüntüdür; örneklenen saniyeler listelendi "
                    "(kapsam gizlenmez). Ses dökümü bu motorda YOK.")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Video işleme motoru")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    job = json.loads(Path(args.job).expanduser().resolve().read_text(encoding="utf-8"))
    print(json.dumps(isle(job), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
