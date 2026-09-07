"""No v1.3 sentence may vanish silently: it is either covered in v1.4 or waived in writing.

Five audits found rules deleted by the rewrite. The first four had the same cause: something
DECIDED which sentences counted as rules, and that decision had a blind spot. The fifth found
the next layer — the measure itself was too loose to notice a deletion, and the docstring
promised a safety net ("a spurious 'covered' is caught by the waiver audit") that did not
exist in the code. Measured then: deleting a v1.4 line byte-identical to a v1.3 line was
caught in only 3 of 18 cases.

So the measure is now POSITION-BOUND, and the promise is a test rather than a sentence:

  * A sentence is covered when SHARE of its content-word stems appear in ONE v1.4 SECTION.
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
  * a lead-in ending in ":" cannot be told from its own list by a bag-of-words measure, so
    its deletion alone is not detected — measured: 1 of 65 carried lines; the list itself is;
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
# A mood marker means the sentence delivers a verdict, so it is a rule and not a fragment.
# The negative imperative and the copula are matched only at the END of the sentence: mid-
# sentence they are almost always deverbal NOUNS ("inceleme", "sözleşme", "karşılaştırma"),
# and an earlier revision that ignored position pasted meaningless fragments into the text
# because it read those nouns as commands.
NORMATIVE = re.compile(
    r"(?:[a-zçğıöşü]{3,}(?:maz|mez|mal[ıi]d[ıi]r|melidir|meli|mal[ıi])\b"
    r"|olamaz\b|edilemez\b|verilmez\b|geçmez\b|değildir\b"
    r"|[a-zçğıöşü]{2,}(?:ma|me)\s*[.;:]?\s*$"      # sunma. / sayma. / yazma; (cümle sonu)
    r"|[a-zçğıöşü]{2,}(?:d[ıiuü]r|tur|tür)\s*[.;:]?\s*$"   # …sonuçlarıdır. / …zorunludur.
    r"|üretir\.|sayılır\.)")

ENTRY = re.compile(r"^- `([0-9a-f]{12})`\s*\[(BASLIK|PARCA|ORNEK|YASAK_IFADE|V13_TEKRAR)\]\s*—\s*(.+)$")
OLD_LINES = OLD.splitlines()
_LITERAL_NEW = ""
_LINES_NEW = []


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


STRONG = 0.85  # the repetition gate's own threshold; the two must agree
MIN_STEMS = 4  # altında oran ölçüsü anlamsız: %60 tek kelimeye iner


def matches(target, region):
    """A region carries a sentence only if it holds SHARE of its stems AND the rarest one.

    Without the second half a long bullet is absorbed by any large paragraph that happens to
    share 60% of its ordinary vocabulary, and deleting the bullet goes unnoticed — measured:
    two such blind spots in the sixth audit round.
    """
    overlap = len(target & region) / len(target)
    if overlap >= STRONG:
        # Vocabulary this close in ONE place is the sentence, reworded. Requiring the rarest
        # stem on top of it made the coverage gate and the repetition gate contradict each
        # other: coverage said "not carried", repetition said "that is a duplicate", and a
        # restore loop oscillated between them. 85% in one region settles it.
        return True
    if overlap < SHARE:
        return False
    return min(target, key=lambda s: (FREQUENCY[s], s)) in region


def _literal(text):
    return re.sub(r"[^0-9a-zçğıöşü]+", " ", fold(text)).strip()


LITERAL_SHARE = 0.8  # bounded by test_deleting_a_carried_line_is_detected, which must stay 58/58


def _reworded(sentence):
    """Low-stem sentences are matched on words in order, not on an exact string.

    A sentence with two content words cannot be measured by ratio, so an earlier revision
    demanded its literal text. That made any REWORDING look like a deletion, and the waiver
    class invented to cover the one real case (a phrase v1.4 repaired on purpose) turned out
    to be forgeable twice over — a register line, then a test file with no assertions. The
    class is gone. Instead the sentence's own words are looked for IN ORDER inside one v1.4
    line: a repair that changes a word or two still matches, while a deleted sentence does not.
    """
    want = _literal(sentence).split()
    if not want:
        return True
    for line in _LINES_NEW:
        have = _literal(line).split()
        i = 0
        for word in have:
            if i < len(want) and word == want[i]:
                i += 1
        if i / len(want) >= LITERAL_SHARE:
            return True
    return False


def uncovered_in(text):
    global _LITERAL_NEW, _LINES_NEW
    _LITERAL_NEW = _literal(text)
    _LINES_NEW = [l for l in text.splitlines() if l.strip()]
    paragraphs, rows = regions(text)
    out = []
    for sentence in sentences():
        target = stems(sentence)
        # a table row must be answered by a table row; rows are too generic for prose to carry
        if len(target) < MIN_STEMS:
            # Includes sentences with NO content word at all. An earlier revision skipped
            # those outright, so a line built from short words ("- Sonuç ve somut eylem;")
            # could be deleted and the measure never noticed — found by the mutation test.
            # Too few content words for a ratio to mean anything: 60% of two stems is one
            # word, which any paragraph supplies. Measured in the sixth audit: 253 of 739
            # sentences fall here. How many of those were wrongly "covered" depends on how
            # "absent" is defined, so no count is quoted: the rule is the fix, not a number.
            # For these the text itself must survive, near enough to be recognisable.
            if _literal(sentence) in _LITERAL_NEW or _reworded(sentence):
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
    if kind == "V13_TEKRAR":
        # v1.3 states this rule TWICE, in two places and two wordings. v1.4 carries it once,
        # which is correct — and then the repetition gate forbids adding the second copy while
        # the coverage gate reports it missing. The waiver is verified against v1.3 alone: an
        # equivalent sentence must exist there AND be covered here. Nothing outside the two
        # command texts is consulted, so there is no document to forge.
        target = stems(sentence)
        if len(target) < 2:
            return False
        for other in sentences():
            if other == sentence:
                continue
            twin = stems(other)
            if twin and len(target & twin) / max(len(target), len(twin)) >= STRONG:
                if is_covered(other):
                    return True
        return False
    if kind == "YASAK_IFADE":
        # v1.4 forbids this sentence's wording, so carrying it verbatim would break the very
        # repair the ban records. This is a real conflict between two rules of the repo, not a
        # loophole, and it is verified from the BAN LISTS the package's own tests enforce —
        # not from a document. The seventh and eighth audits broke two earlier attempts, both
        # of which trusted a file someone could simply write: a repair register, then a test
        # with no assertions. A ban list is different in kind: forging an entry FORBIDS that
        # wording everywhere in the command text, so the forgery destroys what it was meant
        # to smuggle in. The residual limit, stated: a check that reads repository files can
        # never be unforgeable — it can only be made self-defeating to forge.
        for phrase in banned_phrases():
            if phrase in sentence and phrase.lower() not in fold(NEW):
                return True
        return False
    if kind == "ORNEK":
        if not sentence.lstrip().startswith("Örneğin"):
            return False
        return any(is_covered(s) for s in split(line) if s != sentence)
    return False


def banned_phrases():
    """The wordings the package's own tests keep out of the command text."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_ct", ROOT / "bundle_v1_4" / "tests" / "test_command_text.py")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return []
    out = list(getattr(module, "DISCRETION", [])) + list(getattr(module, "SLOP", []))
    source = (ROOT / "bundle_v1_4" / "tests" / "test_command_text.py").read_text(encoding="utf-8")
    out += re.findall(r'for phrase in \(([^)]*)\):', source) and re.findall(
        r'"([^"]+)"', re.search(r'for phrase in \(([^)]*)\):', source).group(1)) or []
    return [p for p in out if len(p) > 6]


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
            elsewhere = mine and any(len(mine & stems(l)) / len(mine) >= 0.7
                                     for l in lines if l != target and stems(l))
            # A lead-in and the list under it carry one rule between them: deleting only the
            # lead-in leaves the list, which a reader still sees and a bag-of-words measure
            # cannot tell apart. That is a structural property, not an exception list — the
            # shape is checked here, and the LIST's own deletion is still detected.
            after = next((l for l in lines[lines.index(target) + 1:] if l.strip()), "")
            lead_in = target.rstrip().endswith(":") and after.lstrip().startswith(("-", "|"))
            if not (elsewhere or lead_in):
                unexplained.append(target[:70])
        self.assertEqual(unexplained, [], "Bu satırlar v1.4'ten silinse ölçüm FARK ETMEZ ve "
                         "içerikleri başka bir satırda da DURMUYOR:\n" + "\n".join(unexplained))


if __name__ == "__main__":
    unittest.main()
