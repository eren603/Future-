"""No v1.3 rule may vanish silently — and there is NO WAIVER MECHANISM to abuse.

Eleven audits. Six of them FAILED, and the last four each broke a waiver mechanism the round
before had added: a repair register, a ban-list lookup, a v1.3-twin match, then the class set
itself. The eleventh audit deleted six real rules — including "salt okunur verinin emir
yetkisinden ayrılması" and the worker-isolation rule — waived each as PARCA, and every test
stayed green; it measured 85 covered sentences with the same exploitable shape. It also showed
the two-entry IRREDUCIBLE cap was not binding, because a slot could be freed and reused.

The lesson is not "harden the waiver". It is that a waiver is a hole by construction: whoever
repairs the text also writes whatever the waiver consults. So the mechanism is GONE — no
classes, no list, no register, no KAPSAM_MUAFIYET.md.

What replaced it is a smaller inventory that needs no exceptions. The unit is the v1.3 LINE,
not the sub-clause. Splitting on ";" and ":" was what created fragments that looked like
"not really rules" and therefore needed a class to excuse them; a line never does. Every v1.3
line over 15 characters must be covered, and 100% are. Headings and table rows are lines too
and are held to the same bar.

Coverage is position-bound: SHARE of a line's content-word stems must appear in ONE v1.4
section, and that section must also carry the line's rarest stem; STRONG overlap alone
suffices. A v1.3 table row must be answered by a v1.4 table row.

test_deleting_a_carried_line_is_detected is the guarantee: every v1.4 line carried verbatim
from v1.3 is deleted in turn and the measure must notice, or the content must provably live on
another line, or the line is a lead-in whose list remains.

Limits, stated rather than claimed away:
  * lexical — it detects DELETION, not a rule left in place and negated;
  * the stem is a fixed prefix, so it over-matches; the mutation test bounds that;
  * a lead-in ending in ":" cannot be told from its own list by a bag-of-words measure.
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

SHARE = 0.6    # a reworded line counts as covered when most content words survive
STRONG = 0.85  # vocabulary this close in one place IS the line, reworded
STEM = 6       # fixed prefix: enough to bridge Turkish inflection, short of a real stemmer
MIN_LEN = 15   # below this a line carries no measurable vocabulary
WORD = re.compile(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]{7,}")


def fold(text):
    """Turkish-aware lowercase. Python maps 'I' to 'i', so "OLMALIDIR" folds to "olmalidir"
    and stops matching "olmalıdır" — a casing trap that misreports a surviving rule as
    deleted, and can hide a deletion in the other direction."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def stems(text):
    return {fold(w)[:STEM] for w in WORD.findall(text)}


FREQUENCY = collections.Counter(s for line in OLD.splitlines() for s in stems(line))


def rule_id(line):
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:12]


def lines_of(text):
    return [l.strip() for l in text.splitlines() if len(l.strip()) > MIN_LEN]


def sentences():
    """The inventory: every v1.3 LINE. Nothing decides which ones are rules."""
    return lines_of(OLD)


def regions(text):
    """v1.4 split into the three places a rule can live: sections, table rows, list items.

    Rows and items are matched one-for-one. Both are short and share vocabulary with their
    neighbours, so a section will happily "carry" a bullet that was deleted — measured: five
    bullets could be removed without the measure noticing until items were separated out.

    Anchoring to the paragraph rewarded dumping — splitting a blob into readable paragraphs
    lowered coverage, so the measure pushed the text towards being unreadable. The section is
    the smallest unit that survives honest editing while still being a POSITION.
    """
    sections, current, rows, items = [], [], [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("|"):
            rows.append(stems(line))
            continue
        if line.lstrip().startswith("- "):
            items.append(stems(line))
        if re.match(r"^\*\*(?:\d|Ek |ASTRA)", line):
            if current:
                sections.append(stems("\n".join(current)))
            current = []
        current.append(line)
    if current:
        sections.append(stems("\n".join(current)))
    return sections, rows, items


def matches(target, region):
    """A region carries a line only if it holds SHARE of its stems AND the rarest one.

    Without the second half a long line is absorbed by any large section that happens to share
    60% of its ordinary vocabulary, and deleting the line goes unnoticed. STRONG overlap alone
    is accepted so this gate and the repetition gate cannot contradict each other.
    """
    overlap = len(target & region) / len(target)
    if overlap >= STRONG:
        return True
    if overlap < SHARE:
        return False
    return min(target, key=lambda s: (FREQUENCY[s], s)) in region


def _literal(text):
    return re.sub(r"[^0-9a-zçğıöşü]+", " ", fold(text)).strip()


def uncovered_in(text):
    sections, rows, items = regions(text)
    out = []
    for line in sentences():
        target = stems(line)
        if not target:
            # No word long enough to stem ("- Sonuç ve somut eylem; veya engel ve gerçek
            # nedeni."). A ratio is meaningless here, so the text itself must survive —
            # otherwise such a line could be deleted and the measure would never notice.
            if _literal(line) not in _literal(text):
                out.append((rule_id(line), line))
            continue
        # a row is answered by a row and a bullet by a bullet: prose absorbs both too easily
        if line.lstrip().startswith("|"):
            pool = rows
        elif line.lstrip().startswith("- "):
            pool = items
        else:
            pool = sections + rows + items
        if not any(matches(target, region) for region in pool):
            out.append((rule_id(line), line))
    return out


def uncovered():
    return uncovered_in(NEW)


class RuleCoverageTests(unittest.TestCase):
    def test_every_v1_3_line_is_carried(self):
        """No exceptions, no waivers: every v1.3 line must be covered in v1.4."""
        missing = uncovered()
        self.assertEqual(missing, [], "Bu v1.3 satırları v1.4'te YOK. Muafiyet mekanizması "
                                      "KALDIRILDI (on birinci denetim onu genel bir kaçış "
                                      "yoluna çevirdi) — tek çare metne geri almaktır:\n" +
                         "\n".join(f"{rid}  {text[:100]}" for rid, text in missing))

    def test_deleting_a_carried_line_is_detected(self):
        """The guarantee: a rule carried over verbatim cannot be deleted unnoticed.

        Deletion must be visible, or the content must provably live on another line, or the
        line must be a lead-in whose list stays behind (a bag-of-words measure cannot tell a
        lead-in from its own list; the list's own deletion is still detected).
        """
        carried = {l.strip() for l in OLD.splitlines() if len(l.strip()) > 40}
        lines = NEW.splitlines()
        targets = [l for l in lines if l.strip() in carried]
        self.assertGreater(len(targets), 10, "birebir taşınan satır kalmadı — test anlamsız")
        base = {rid for rid, _ in uncovered()}
        unexplained = []
        for target in targets:
            cut = "\n".join(l for l in lines if l != target)
            if {rid for rid, _ in uncovered_in(cut)} - base:
                continue
            mine = stems(target)
            elsewhere = mine and any(len(mine & stems(l)) / len(mine) >= 0.7
                                     for l in lines if l != target and stems(l))
            after = next((l for l in lines[lines.index(target) + 1:] if l.strip()), "")
            lead_in = target.rstrip().endswith(":") and after.lstrip().startswith(("-", "|"))
            if not (elsewhere or lead_in):
                unexplained.append(target[:70])
        self.assertEqual(unexplained, [], "Bu satırlar v1.4'ten silinse ölçüm FARK ETMEZ ve "
                         "içerikleri başka bir satırda da DURMUYOR:\n" + "\n".join(unexplained))

    def test_no_waiver_mechanism_exists(self):
        """The mechanism that failed four audits in a row must stay gone.

        Every waiver this test ever had was verified against a file the repairer also writes:
        a repair register, the package's ban lists, a v1.3 twin, a bounded list. Each was
        broken within one round — the eleventh audit deleted six real rules through the last
        of them. This checks the ARTEFACTS rather than this file's own words: no waiver
        register on disk, and no waiver symbol in the module namespace.
        """
        self.assertFalse((ROOT / "KAPSAM_MUAFIYET.md").exists(),
                         "muafiyet defteri geri gelmiş")
        import sys
        module = sys.modules[__name__]
        for symbol in ("IRREDUCIBLE", "class_holds", "entries", "banned_phrases", "WAIVER"):
            self.assertFalse(hasattr(module, symbol),
                             f"muafiyet mekanizması geri gelmiş: {symbol}")


if __name__ == "__main__":
    unittest.main()
