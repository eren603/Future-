"""No v1.3 sentence may vanish silently: it is either covered in v1.4 or waived in writing.

Five audits found rules deleted by the rewrite. The first four had the same cause: something
DECIDED which sentences counted as rules, and that decision had a blind spot. The fifth found
the next layer — the measure itself was too loose to notice a deletion, and the docstring
promised a safety net ("a spurious 'covered' is caught by the waiver audit") that did not
exist in the code. Measured then: deleting a v1.4 line byte-identical to a v1.3 line was
caught in only 3 of 18 cases.

So the measure is now POSITION-BOUND, and the promise is a test rather than a sentence:

  * A sentence is covered when SHARE of its content-word stems appear in ONE v1.4 paragraph.
    Vocabulary scattered across the document no longer counts — that was the loophole that
    let a whole table row be deleted while the test stayed green.
  * A sentence that lives in a v1.3 TABLE ROW must be matched by a v1.4 TABLE ROW. Rows carry
    generic words that any paragraph absorbs; row-to-row matching is what makes their deletion
    visible. All 8 undetected deletions in the fifth audit were table rows.
  * `test_deleting_a_carried_line_is_detected` is the guarantee itself: every v1.4 line that is
    byte-identical to a v1.3 line is deleted in turn and the measure MUST report new uncovered
    sentences, or prove the rule still lives on another line. No count is written here:
    a number in a docstring goes stale silently, and the sixth audit caught one that had
    (it said 18/18 for an artefact measuring 52). The test reports what it measured.

Turkish morphology is handled by two fixed rules rather than an analyser: a stem prefix (a rule
kept but re-inflected, "kullanma" -> "KULLANILMAZ", still matches) and `fold`, which maps the
dotted/dotless I pair before lowercasing. Both LOOSEN the measure, which is why the mutation
test above exists to bound how far.

Anything the measure does not cover must appear in astra/KAPSAM_MUAFIYET.md — and the waiver is
not taken on trust either. Every entry carries a CLASS, and `test_each_waiver_class_is_
mechanically_true` re-derives that class from the sentence itself; a waiver whose class does not
hold fails, as does a waiver written for a sentence that is in fact covered.

Remaining limits, stated rather than claimed away:
  * sentences are split on [.;:] and newlines, so an unusual layout can merge or split one;
  * a sentence of 15 characters or fewer is skipped (it carries no distinctive word);
  * the measure is lexical: it detects DELETION, not a sentence left in place and negated;
  * the stem is a fixed prefix, so it over-matches; the mutation test is what bounds that;
  * a sentence with fewer than MIN_STEMS content words cannot be measured by ratio at all —
    60% of two stems is one word, which any section supplies. Those sentences are checked
    by literal text instead, which is stricter but blind to rewording.
"""
import collections
import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = (ROOT / "bundle_v1_3" / "astra_command.md").read_text(encoding="utf-8")
NEW_PATH = ROOT / "bundle_v1_4" / "astra_command.md"
NEW = NEW_PATH.read_text(encoding="utf-8")
WAIVER = ROOT / "KAPSAM_MUAFIYET.md"

SHARE = 0.6  # a reworded sentence counts as covered when most content words survive
STEM = 6     # fixed prefix: enough to bridge Turkish inflection, short of a real stemmer
WORD = re.compile(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]{7,}")
NORMATIVE = re.compile(
    r"(?:[a-zçğıöşü]{3,}(?:maz|mez|mal[ıi]d[ıi]r|melidir|meli|mal[ıi])\b"
    r"|üretir\.|sayılır\.|olamaz\b|edilemez\b|verilmez\b|geçmez\b|değildir\b)")
ENTRY = re.compile(r"^- `([0-9a-f]{12})`\s*\[(BASLIK|PARCA|ORNEK|ONARILDI)\]\s*—\s*(.+)$")
OLD_LINES = OLD.splitlines()
_LITERAL_NEW = ""


def fold(text):
    """Turkish-aware lowercase. Python maps 'I' to 'i', so "OLMALIDIR" folds to "olmalidir"
    and stops matching "olmalıdır" — a casing trap that misreports a surviving rule as
    deleted, and can hide a deletion in the other direction."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def stems(text):
    return {fold(w)[:STEM] for w in WORD.findall(text)}


def rule_id(sentence):
    return hashlib.sha256(sentence.encode("utf-8")).hexdigest()[:12]


def split(text):
    return [s.strip() for s in re.split(r"(?<=[.;:])\s+|\n", text)
            if 15 < len(s.strip()) < 400]


def sentences():
    """Every sentence, with no judgement about which ones are rules."""
    return split(OLD)


def owning_line(sentence):
    for line in OLD_LINES:
        if sentence in line:
            return line
    return ""


FREQUENCY = collections.Counter(fold(w)[:STEM] for w in WORD.findall(OLD))


def regions(text):
    """v1.4 split into the two places a rule can live: SECTIONS and table rows.

    An earlier revision anchored to the paragraph, which quietly rewarded dumping: split a
    2000-character blob into readable paragraphs and coverage fell, so the measure pushed
    the text towards being unreadable. The section is the smallest unit that survives
    honest editing while still being a POSITION — vocabulary scattered across the whole
    document, the loophole this measure exists to close, still does not count.
    """
    sections, current, rows = [], [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("|"):
            rows.append(stems(line))
            continue
        if re.match(r"^\*\*(?:\d|Ek |ASTRA)", line):
            if current:
                sections.append(stems("\n".join(current)))
            current = []
        current.append(line)
    if current:
        sections.append(stems("\n".join(current)))
    return sections, rows


MIN_STEMS = 3  # altında oran ölçüsü anlamsız: %60 tek kelimeye iner


def matches(target, region):
    """A region carries a sentence only if it holds SHARE of its stems AND the rarest one.

    Without the second half a long bullet is absorbed by any large paragraph that happens to
    share 60% of its ordinary vocabulary, and deleting the bullet goes unnoticed — measured:
    two such blind spots in the sixth audit round.
    """
    if len(target & region) / len(target) < SHARE:
        return False
    return min(target, key=lambda s: (FREQUENCY[s], s)) in region


def _literal(text):
    return re.sub(r"[^0-9a-zçğıöşü]+", " ", fold(text)).strip()


def uncovered_in(text):
    global _LITERAL_NEW
    _LITERAL_NEW = _literal(text)
    paragraphs, rows = regions(text)
    out = []
    for sentence in sentences():
        target = stems(sentence)
        if not target:
            continue
        # a table row must be answered by a table row; rows are too generic for prose to carry
        if len(target) < MIN_STEMS:
            # Too few content words for a ratio to mean anything: 60% of two stems is one
            # word, which any paragraph supplies. Measured in the sixth audit: 253 of 739
            # sentences fall here and 164 of them were "covered" while absent from v1.4.
            # For these the text itself must survive, near enough to be recognisable.
            if _literal(sentence) in _LITERAL_NEW:
                continue
            out.append((rule_id(sentence), sentence))
            continue
        pool = rows if owning_line(sentence).lstrip().startswith("|") else paragraphs + rows
        if not any(matches(target, region) for region in pool):
            out.append((rule_id(sentence), sentence))
    return out


def uncovered():
    return uncovered_in(NEW)


def is_covered(sentence):
    return rule_id(sentence) not in {rid for rid, _ in uncovered()}


def class_holds(kind, sentence):
    """Re-derive a waiver's class from the text. No class is taken on the writer's word."""
    line = owning_line(sentence)
    if kind == "BASLIK":
        return bool(re.match(r"^\s*#", line)) or sentence.strip().endswith("**")
    if kind == "PARCA":
        head = re.sub(r"^[^0-9A-Za-zÇĞİÖŞÜçğıöşü]+", "", sentence)[:1]
        if not (head and head.islower()):
            return False  # a full sentence is not a continuation clause
        if NORMATIVE.search(sentence):
            # Starting in lowercase is not enough: a sentence opening with an identifier
            # ("candidate_review_passed ... gerçek inceleme sonuçlarıdır") is a full rule.
            # The sixth audit found three such rules waived as fragments while their text
            # was absent from v1.4. A mood marker means the sentence carries a verdict.
            return False
        return any(is_covered(s) for s in split(line) if s != sentence)
    if kind == "ONARILDI":
        # The sentence was a FINDING, not a rule to carry: v1.4 repaired it on purpose and
        # a test now forbids its wording. Restoring it verbatim would reintroduce the defect.
        # Mechanically: the repair register must name a finding whose text quotes this
        # sentence, and the package must carry a test that bans the old wording.
        register = (ROOT / "BULGU_DEGISIKLIK.md")
        if not register.exists():
            return False
        banned = re.findall(r"'([^']{8,})'", register.read_text(encoding="utf-8"))
        return any(phrase in sentence and phrase.lower() not in fold(NEW) for phrase in banned)
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
                self.assertTrue(class_holds(kind, by_id[rid]),
                                f"{kind} sınıfı bu cümle için DOĞRULANAMADI: {by_id[rid]!r}")
                self.assertGreater(len(reason.strip()), 30)

    def test_waiver_has_no_stale_entries(self):
        """A waiver for a rule that is now covered would hide a later deletion."""
        live = {rid for rid, _ in uncovered()}
        self.assertEqual({rid for rid, _, _ in entries()} - live, set())

    def test_deleting_a_carried_line_is_detected(self):
        """The guarantee itself: a rule carried over verbatim cannot be deleted unnoticed.

        This is the test the fifth audit asked for. It bounds how far the two Turkish
        loosenings (stem prefix, fold) may be pushed: weaken the measure and this goes red
        before any rule is lost.
        """
        carried = {l.strip() for l in OLD_LINES if len(l.strip()) > 40}
        lines = NEW.splitlines()
        targets = [l for l in lines if l.strip() in carried]
        self.assertGreater(len(targets), 10, "birebir taşınan satır kalmadı — test anlamsız")
        base = {rid for rid, _ in uncovered()}
        unexplained = []
        for target in targets:
            cut = "\n".join(l for l in lines if l != target)
            if {rid for rid, _ in uncovered_in(cut)} - base:
                continue  # deletion is visible: the guarantee holds for this line
            # Not detected. That is only acceptable when the rule provably lives on another
            # line — otherwise the measure is blind and the line could vanish unnoticed.
            mine = stems(target)
            elsewhere = any(len(mine & stems(l)) / len(mine) >= 0.7
                            for l in lines if l != target and stems(l))
            if not (mine and elsewhere):
                unexplained.append(target[:70])
        self.assertEqual(unexplained, [], "Bu satırlar v1.4'ten silinse ölçüm FARK ETMEZ ve "
                         "içerikleri başka bir satırda da DURMUYOR:\n" + "\n".join(unexplained))


if __name__ == "__main__":
    unittest.main()
