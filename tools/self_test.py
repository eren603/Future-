#!/usr/bin/env python3
"""tools/ öz-testi — 5 aracı sentetik veriyle doğrular. SELF_TEST_OK basar.
Ek bağımlılık yok. Video testi ffmpeg yoksa atlanır (fail değil)."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import belge_ingest  # noqa: E402
import gorsel_dongu  # noqa: E402
import suru  # noqa: E402
import dosya_skill  # noqa: E402
import benchmark  # noqa: E402


def _make_xlsx(p: Path):
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("xl/sharedStrings.xml",
                   f'<sst {ns}><si><t>Ad</t></si><si><t>Deger</t></si></sst>')
        z.writestr("xl/workbook.xml",
                   f'<workbook {ns}><sheets><sheet name="Sayfa1" sheetId="1"/>'
                   f'</sheets></workbook>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet {ns}><sheetData>'
                   f'<row r="1"><c r="A1" t="s"><v>0</v></c>'
                   f'<c r="B1" t="s"><v>1</v></c></row>'
                   f'<row r="2"><c r="A2"><v>42</v></c></row>'
                   f'</sheetData></worksheet>')


def _make_docx(p: Path):
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("word/document.xml",
                   f'<w:document {w}><w:body>'
                   f'<w:p><w:r><w:t>Merhaba dünya</w:t></w:r></w:p>'
                   f'<w:p><w:r><w:t>ikinci paragraf analiz</w:t></w:r></w:p>'
                   f'</w:body></w:document>')


def _make_pdf(p: Path):
    content = b"BT /F1 12 Tf (Merhaba PDF metni) Tj ET"
    comp = zlib.compress(content)
    p.write_bytes(b"%PDF-1.4\n5 0 obj\n<< /Length 99 >>\nstream\n"
                  + comp + b"\nendstream\nendobj\n%%EOF")


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)

        # 1) belge_ingest — xlsx
        xp = tmp / "t.xlsx"; _make_xlsx(xp)
        r = belge_ingest.ingest(str(xp))
        assert r["type"] == "xlsx" and "Sayfa1" in r["sheets"], r
        flat = json.dumps(r, ensure_ascii=False)
        assert "Ad" in flat and "42" in flat, r

        # belge_ingest — docx
        dp = tmp / "t.docx"; _make_docx(dp)
        r = belge_ingest.ingest(str(dp))
        assert r["type"] == "docx" and r["para_count"] == 2, r
        assert "Merhaba" in r["text"], r

        # belge_ingest — pdf (FlateDecode)
        pp = tmp / "t.pdf"; _make_pdf(pp)
        r = belge_ingest.ingest(str(pp))
        assert r["type"] == "pdf" and r["extracted"] and "Merhaba" in r["text"], r

        # belge_ingest — csv/json/txt
        cp = tmp / "t.csv"; cp.write_text("a,b\n1,2\n3,4\n")
        r = belge_ingest.ingest(str(cp))
        assert r["type"] == "csv" and r["row_count"] == 3, r
        jp = tmp / "t.json"; jp.write_text('{"x":1}')
        assert belge_ingest.ingest(str(jp))["data"] == {"x": 1}

        # belge_ingest — video (ffmpeg varsa)
        if shutil.which("ffmpeg"):
            vp = tmp / "t.mp4"
            gen = subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i",
                 "testsrc=duration=1:size=128x72:rate=2", str(vp)],
                capture_output=True, text=True)
            if gen.returncode == 0 and vp.exists():
                r = belge_ingest.ingest(str(vp), str(tmp / "kareler"), fps=1)
                assert r["type"] == "video" and r["frame_count"] >= 1, r

        # 2) gorsel_dongu — kapalı loop, sentetik yükseliş
        n = 60
        close = [100 + i * 0.5 for i in range(n)]
        high = [c + 1 for c in close]
        low = [c - 1 for c in close]
        g = gorsel_dongu.run_loop({"high": high, "low": low, "close": close,
                                   "target_rr": 2.0, "max_iter": 15, "tol": 0.05})
        assert g["iterations"] >= 1 and g["best"]["rr"] > 0, g
        assert 0.50 <= g["best"]["fib_level"] <= 0.786, g

        # 3) suru — gerçek paralel alt-süreç (risk.py motoruna)
        plan = {"tasks": [
            {"name": "risk", "weight": 1.0,
             "script": ".claude/skills/risk-yonetimi/scripts/risk.py",
             "job": {"op": "position_size", "method": "fixed_fractional",
                     "equity": 10000, "risk_pct": 1.0, "entry": 100, "stop": 98}},
            {"name": "yok", "script": "yok/olmayan.py", "job": {}},
        ], "timeout": 60}
        s = suru.run_swarm(plan, REPO)
        assert s["ok_count"] == 1 and "yok" in s["failed"], s
        risk_row = [x for x in s["results"] if x["name"] == "risk"][0]
        assert risk_row["ok"] and abs(risk_row["result"]["units"] - 50.0) < 1e-6, s

        # 4) dosya_skill — belge → SKILL.md iskelesi
        mp = tmp / "notlar.md"
        mp.write_text("# Başlık Bir\nanaliz veri strateji analiz veri\n"
                      "## Başlık İki\nrisk yönetimi risk yönetimi\n")
        md = dosya_skill.build_skill(str(mp), "test-beceri")
        assert md.startswith("---\nname: test-beceri"), md[:60]
        assert "Başlık Bir" in md and "Tetikleyiciler" in md, md
        # geçersiz isim reddedilir
        try:
            dosya_skill.build_skill(str(mp), "Geçersiz İsim")
            raise AssertionError("geçersiz isim kabul edildi")
        except dosya_skill.SkillError:
            pass

        # 5) benchmark — keşif + rapor biçimi (recursion'a girmeden)
        tests = benchmark.discover_self_tests()
        assert len(tests) >= 5, tests
        fake = {"engine_count": 2, "passed": 1, "failed": 1, "pass_rate": 0.5,
                "total_seconds": 1.0,
                "rows": [{"skill": "a", "passed": True, "seconds": 0.5,
                          "detail": "OK"},
                         {"skill": "b", "passed": False, "seconds": 0.5,
                          "detail": "boom"}]}
        mdb = benchmark.to_markdown(fake)
        assert "✅ PASS" in mdb and "❌ FAIL" in mdb and "50.0%" in mdb, mdb

    print("SELF_TEST_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
