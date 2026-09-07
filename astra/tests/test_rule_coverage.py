"""No v1.3 rule may vanish silently: it is either covered in v1.4 or waived in writing.

Two audits in a row found rules deleted by a rewrite, and both times the answer was a
hand-written list of the rules the auditor happened to name. That does not scale and it
is not verification. This test derives the inventory from the v1.3 text itself:

  1. every sentence carrying a normative marker (a ban, an obligation, a "is not") is
     extracted from bundle_v1_3/astra_command.md;
  2. its most DISTINCTIVE content word (the rarest one in the v1.3 text) is looked up
     in the v1.4 text;
  3. a sentence whose distinctive word is absent counts as UNCOVERED and must appear in
     astra/KAPSAM_MUAFIYET.md, keyed by a stable id, with a written reason.

The measure deliberately OVER-flags: a rule reworded with different words is flagged
too, and is then waived with "reworded as ...". Over-flagging costs a written line;
under-flagging loses a rule, which is what actually happened twice.

The lexical measure is a coarse instrument: it detects deletion, not meaning. A rule
rewritten with different words can still be flagged (then waived with "reworded as ...")
and a rule whose words survive while its sense is inverted will NOT be caught here.
That limit is the point of writing it down rather than claiming the test proves fidelity.
"""
import collections
import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = (ROOT / "bundle_v1_3" / "astra_command.md").read_text(encoding="utf-8")
NEW = (ROOT / "bundle_v1_4" / "astra_command.md").read_text(encoding="utf-8").lower()
WAIVER = ROOT / "KAPSAM_MUAFIYET.md"

NORMATIVE = re.compile(
    r"(yasak|zorunlu|sayılmaz|sayma\b|deme\b|üretme\b|kullanma\b|yazma\b|verme\b"
    r"|edilmez|ilmez|ılmaz|olamaz|olmaz|gerekir|değildir|yapılmaz|verilmez|geçemez)", re.I)
WORD = re.compile(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]{7,}")
FREQUENCY = collections.Counter(w.lower() for w in WORD.findall(OLD))


def rule_id(sentence):
    return hashlib.sha256(sentence.encode("utf-8")).hexdigest()[:12]


def sentences():
    for raw in re.split(r"(?<=[.;:])\s+|\n", OLD):
        text = raw.strip()
        if 40 < len(text) < 400 and NORMATIVE.search(text):
            yield text


def uncovered():
    for sentence in sentences():
        words = {w.lower() for w in WORD.findall(sentence)}
        if not words:
            continue
        distinctive = min(words, key=lambda w: (FREQUENCY[w], w))
        if distinctive not in NEW:
            yield rule_id(sentence), sentence


class RuleCoverageTests(unittest.TestCase):
    def test_every_uncovered_v1_3_rule_is_waived_in_writing(self):
        waived = WAIVER.read_text(encoding="utf-8") if WAIVER.exists() else ""
        missing = [(rid, text) for rid, text in uncovered() if rid not in waived]
        self.assertEqual(missing, [], "Bu v1.3 kuralları v1.4'te yok ve muafiyet kaydı da "
                                      "yok — ya metne geri alın ya da KAPSAM_MUAFIYET.md'ye "
                                      "gerekçesiyle yazın:\n" +
                         "\n".join(f"{rid}  {text}" for rid, text in missing))

    def test_waiver_entries_carry_a_reason(self):
        if not WAIVER.exists():
            return
        for line in WAIVER.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^- `([0-9a-f]{12})`\s*—\s*(.+)$", line.strip())
            if match:
                with self.subTest(rule=match.group(1)):
                    self.assertGreater(len(match.group(2).strip()), 30)

    def test_waiver_has_no_stale_entries(self):
        """A waiver for a rule that is now covered would hide a later deletion."""
        if not WAIVER.exists():
            return
        live = {rid for rid, _ in uncovered()}
        declared = set(re.findall(r"^- `([0-9a-f]{12})`", WAIVER.read_text(encoding="utf-8"), re.M))
        self.assertEqual(declared - live, set())


if __name__ == "__main__":
    unittest.main()
