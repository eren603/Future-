"""bundle_tools must produce a document that rebuilds the package it came from."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "scripts" / "bundle_tools.py"
BUNDLE = ROOT / "bundle_v1_4"
HEADER = ROOT / "astra_tamir_v1_4_HEADER.md"
DOCUMENT = ROOT / "astra_tamir_v1_4.md"


def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(TOOLS), *args], capture_output=True,
                          text=True, timeout=300, cwd=cwd)


class BundleDocumentTests(unittest.TestCase):
    def test_document_verifies(self):
        done = run("verify", str(DOCUMENT))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(json.loads(done.stdout)["ok"])

    def test_header_command_matches_the_embedded_command(self):
        """K-16: the document header and the packaged command must not drift apart."""
        text = DOCUMENT.read_text(encoding="utf-8")
        command = (BUNDLE / "astra_command.md").read_text(encoding="utf-8")
        head = text.split("**Gömülü dosyalar**")[0]
        self.assertIn(command.strip(), head)
        self.assertNotIn("<!-- ASTRA_COMMAND_HERE -->", text)

    def test_header_does_not_claim_a_downloadable_archive(self):
        # makyaj-7: there is no archive; the document IS the delivery. Only the header
        # speaks for the document — embedded files are the package's own text.
        head = DOCUMENT.read_text(encoding="utf-8").split("**Gömülü dosyalar**")[0].lower()
        for word in (".zip", ".tar", "arşiv dosyası", "indirilecek paket"):
            with self.subTest(word=word):
                self.assertNotIn(word, head)

    def test_roundtrip_extracts_and_passes_its_own_tests(self):
        done = run("roundtrip", str(DOCUMENT))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        report = json.loads(done.stdout)
        self.assertTrue(report["tests_ok"])
        self.assertGreater(report["tests_run"], 100)

    def test_extracted_tree_matches_the_working_bundle(self):
        with tempfile.TemporaryDirectory(prefix="astra-roundtrip-") as workdir:
            target = Path(workdir) / "out"
            done = run("extract", str(DOCUMENT), str(target))
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            source_files = {p.relative_to(BUNDLE).as_posix()
                            for p in BUNDLE.rglob("*")
                            if p.is_file() and "__pycache__" not in p.parts}
            extracted = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
            self.assertEqual(source_files, extracted)
            for name in sorted(source_files - {"BUNDLE_MANIFEST.json"}):
                with self.subTest(name=name):
                    self.assertEqual((target / name).read_text(encoding="utf-8"),
                                     (BUNDLE / name).read_text(encoding="utf-8"))

    def test_version_is_declared_once_and_is_1_4(self):
        text = DOCUMENT.read_text(encoding="utf-8")
        manifest = json.loads(re.search(
            r"<!-- BEGIN FILE: BUNDLE_MANIFEST\.json -->\n```json\n(.*?)\n```\n<!-- END FILE -->",
            text, re.S).group(1))
        self.assertEqual(manifest["version"], "1.4")
        self.assertIn("ASTRA v1.4", text.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
