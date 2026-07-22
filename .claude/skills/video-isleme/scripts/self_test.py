#!/usr/bin/env python3
"""video_isle.py öz-testi. Sentetik video üretir (ffmpeg testsrc + renk
sahneleri), kare çıkarmayı uçtan uca sınar. SELF_TEST_OK basar."""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_isle as vi  # noqa: E402


def main():
    # 0) ffmpeg garantisi (yoksa motor kendisi kurar — kendi-kendini onarma testi)
    k = vi.ensure_ffmpeg()
    assert k["ffmpeg"] in ("hazır", "şimdi kuruldu"), k

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        vid = td / "test.mp4"
        # 6 sn: 3 ayrı renk sahnesi (2'şer sn) → sahne-değişimi tespit edilebilir
        subprocess.run(
            ["ffmpeg", "-y",
             "-f", "lavfi", "-i", "color=red:s=320x240:d=2",
             "-f", "lavfi", "-i", "color=green:s=320x240:d=2",
             "-f", "lavfi", "-i", "color=blue:s=320x240:d=2",
             "-filter_complex", "[0][1][2]concat=n=3:v=1:a=0",
             "-pix_fmt", "yuv420p", str(vid)],
            check=True, capture_output=True, timeout=300)
        assert vid.exists() and vid.stat().st_size > 0

        # 1) metadata
        m = vi.probe(vid)
        assert m["genislik"] == 320 and m["yukseklik"] == 240, m
        assert 5.5 <= m["sure_sn"] <= 6.5, m

        # 2) uniform mod: tam 6 kare, hepsi diskte, zaman artan sırada
        r = vi.isle({"input": str(vid), "out_dir": str(td / "u"),
                     "max_frames": 6, "mode": "uniform"})
        assert r["kare_sayisi"] == 6, r["kare_sayisi"]
        ts = [f["t_sn"] for f in r["kareler"]]
        assert ts == sorted(ts) and all(0 <= t <= 6.5 for t in ts), ts
        assert all(Path(f["dosya"]).stat().st_size > 0 for f in r["kareler"])

        # 3) scene mod: renk geçişleri yakalanmalı ya da uniform tamamlanmalı;
        #    her durumda kare üretilir (fail-açık değil)
        r = vi.isle({"input": str(vid), "out_dir": str(td / "s"),
                     "max_frames": 8, "mode": "scene"})
        assert r["kare_sayisi"] >= 2, r
        assert all(Path(f["dosya"]).exists() for f in r["kareler"])

        # 4) hata dürüstlüğü: olmayan dosya → açık VideoError (sessiz geçmek yok)
        try:
            vi.isle({"input": str(td / "yok.mp4")})
            raise AssertionError("olmayan dosya hata vermeliydi")
        except vi.VideoError as e:
            assert "yok" in str(e).lower() or "Girdi" in str(e), e

    print("SELF_TEST_OK: ensure-ffmpeg, probe, uniform-kare, scene-kare, hata-durustlugu")


if __name__ == "__main__":
    main()
