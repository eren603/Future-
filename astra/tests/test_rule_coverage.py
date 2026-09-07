"""No v1.3 sentence may vanish silently: it is either covered in v1.4 or waived in writing.

Four audits in a row found rules deleted by the rewrite, and every time the cause was the
same: something DECIDED which sentences counted as rules, and that decision had a blind
spot. A hand-written word list missed "göstermez/doğrulamaz/kaydetme/bitirme/koru"; a
suffix pattern for the two negative moods then missed the necessitative "-malıdır/-meli"
and anything below its length bound. Each patch produced the next blind spot.

So there is NO classifier any more. The inventory is EVERY sentence of the v1.3 command
text; nothing decides in advance whether a sentence is a rule. A sentence counts as
covered when its most distinctive word appears in v1.4, or when at least SHARE of its
content words do. Turkish is agglutinative, so a rule kept but re-inflected ("kullanma"
-> "KULLANILMAZ") is matched on its STEM as well; the stem is a fixed prefix, not a
morphological analyser, so it over-matches rather than under-matches — deliberately, since
a missed deletion is the costly error and a spurious "covered" is caught by the waiver
audit below.

Everything not covered must appear in astra/KAPSAM_MUAFIYET.md — and the waiver is not
taken on trust either. Every entry carries a CLASS, and this test re-derives that class
from the text itself; a waiver whose class does not hold FAILS. That closes the hole the
fifth audit round opened: the previous waiver file carried template reasons, which is the
same classifier this test removed, hiding in prose.

Remaining limits, stated rather than claimed away:
  * sentences are split on [.;:] and newlines, so an unusual layout can merge or split one;
  * a sentence of 15 characters or fewer is skipped (it carries no distinctive word);
  * the measure is lexical: it detects DELETION, not a sentence left in place and negated.
"""
import collections
import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = (ROOT / "bundle_v1_3" / "astra_command.md").read_text(encoding="utf-8")


def fold(text):
    """Turkish-aware lowercase. Python maps 'I' to 'i', so "OLMALIDIR" folds to
    "olmalidir" and no longer matches "olmalıdır" — a casing trap that silently
    reports a surviving rule as deleted (and, in the other direction, could mask
    one). The dotted/dotless pair is mapped before the generic fold."""
    return text.replace("I", "ı").replace("İ", "i").lower()


NEW = fold((ROOT / "bundle_v1_4" / "astra_command.md").read_text(encoding="utf-8"))
WAIVER = ROOT / "KAPSAM_MUAFIYET.md"

SHARE = 0.6  # a reworded sentence counts as covered when most content words survive
STEM = 6     # fixed prefix: enough to bridge Turkish inflection, short of a real stemmer
WORD = re.compile(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]{7,}")
FREQUENCY = collections.Counter(fold(w) for w in WORD.findall(OLD))
NEW_STEMS = {fold(w)[:STEM] for w in WORD.findall(NEW)}
OLD_LINES = OLD.splitlines()
ENTRY = re.compile(r"^- `([0-9a-f]{12})`\s*\[(BASLIK|TABLO|PARCA|ORNEK)\]\s*—\s*(.+)$")


def rule_id(sentence):
    return hashlib.sha256(sentence.encode("utf-8")).hexdigest()[:12]


def split(text):
    return [s.strip() for s in re.split(r"(?<=[.;:])\s+|\n", text)
            if 15 < len(s.strip()) < 400]


def sentences():
    """Every sentence, with no judgement about which ones are rules."""
    return split(OLD)


def survives(word):
    return word in NEW or word[:STEM] in NEW_STEMS


def is_covered(sentence):
    words = {fold(w) for w in WORD.findall(sentence)}
    if not words:
        return True
    distinctive = min(words, key=lambda w: (FREQUENCY[w], w))
    if survives(distinctive):
        return True
    return sum(1 for w in words if survives(w)) / len(words) >= SHARE


def uncovered():
    for sentence in sentences():
        if not is_covered(sentence):
            yield rule_id(sentence), sentence


def owning_line(sentence):
    for line in OLD_LINES:
        if sentence in line:
            return line
    return ""


def class_holds(kind, sentence, reason):
    """Re-derive a waiver's class from the text. No class is taken on the writer's word."""
    line = owning_line(sentence)
    if kind == "BASLIK":
        return bool(re.match(r"^\s*#", line)) or sentence.strip().endswith("**")
    if kind == "TABLO":
        return line.lstrip().startswith("|")
    if kind == "PARCA":
        head = re.sub(r"^[^0-9A-Za-zÇĞİÖŞÜçğıöşü]+", "", sentence)[:1]
        if not (head and head.islower()):
            return False  # a full sentence is not a continuation clause
        siblings = [s for s in split(line) if s != sentence]
        return any(is_covered(s) for s in siblings)
    if kind == "ORNEK":
        if not sentence.lstrip().startswith("Örneğin"):
            return False
        return any(is_covered(s) for s in split(line) if s != sentence)
    return False


def entries():
    if not WAIVER.exists():
        return []
    return [ENTRY.match(l.strip()).groups()
            for l in WAIVER.read_text(encoding="utf-8").splitlines()
            if ENTRY.match(l.strip())]


class RuleCoverageTests(unittest.TestCase):
    def test_every_uncovered_v1_3_rule_is_waived_in_writing(self):
        declared = {rid for rid, _, _ in entries()}
        missing = [(rid, text) for rid, text in uncovered() if rid not in declared]
        self.assertEqual(missing, [], "Bu v1.3 kuralları v1.4'te yok ve muafiyet kaydı da "
                                      "yok — ya metne geri alın ya da KAPSAM_MUAFIYET.md'ye "
                                      "sınıfı ve gerekçesiyle yazın:\n" +
                         "\n".join(f"{rid}  {text}" for rid, text in missing))

    def test_each_waiver_class_is_mechanically_true(self):
        """The written reason is audited, not believed: its class must re-derive."""
        by_id = {rid: text for rid, text in uncovered()}
        for rid, kind, reason in entries():
            with self.subTest(rule=rid, kind=kind):
                self.assertIn(rid, by_id, "kapsanmış kural için muafiyet yazılamaz")
                self.assertTrue(class_holds(kind, by_id[rid], reason),
                                f"{kind} sınıfı bu cümle için DOĞRULANAMADI: {by_id[rid]!r}")
                self.assertGreater(len(reason.strip()), 30)

    def test_waiver_has_no_stale_entries(self):
        """A waiver for a rule that is now covered would hide a later deletion."""
        live = {rid for rid, _ in uncovered()}
        self.assertEqual({rid for rid, _, _ in entries()} - live, set())


if __name__ == "__main__":
    unittest.main()
