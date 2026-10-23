"""The read-back at close: every sentence that goes on record in the lead's name, listed so the lead can keep, reword
or cut it. Pure.

The Violation this exists to prevent is a Silent Fallback in the record: a receipt's words, a Why line or a picked
quote reads as something the lead said, and nobody asked them to look at the final wording. The lead's one read-back
is their yes to all of their own lines at once, so the list has to be exactly the lines that leave the machine in their
name, and a line changed after the yes has to reopen it (`digest`).

What counts: a receipt that cites this record and part and carries the lead's words; the Why lines on the same
item; and the quotes the lead picked (`.vela/close/<id>.quotes.json`, `{"quotes": [{"number", "words", "item"}]}`;
`item` is the item the capture's Changes row names, else ""). A receipt that quotes someone else's words is theirs,
under their own yes to being quoted, and is not the lead's to reword here.

A reworded line stays honest by one rule: its words are an excerpt of the capture it cites, or the words of (or an
excerpt of) a lead capture that approves the new wording, in which case a receipt is re-pointed to that capture.
Cutting a decision's words would break E315, so only Why lines and quotes can be cut.
"""
import hashlib
import re
from dataclasses import dataclass

from vela import closegate, privaterecord, questions, receipts
from vela.decisions import consent, textedit

DECISION, WHY, QUOTE = "decision", "why", "quote"
LINES = (DECISION, WHY, QUOTE)
CUTTABLE = (WHY, QUOTE)
_BULLET_FOR = {DECISION: "Decision", WHY: "Why"}


@dataclass(frozen=True)
class Sentence:
    """One line the lead reads back. `item` is the item ID (the page's ID for a page-level line, `^cNN` for a picked
    quote with no item), `page` the page path ("" for a quote), `number` the capture it cites (0 when none is found),
    `words` the words unescaped, and `at` the 1-based line of the bullet on its page (0 for a quote)."""
    item: str
    line: str
    page: str
    number: int
    words: str
    at: int = 0


def sentences(vault, record_id, part, record_text, lead, picked):
    """Every sentence to read back for this record and part, in page order, then the picked quotes. With no known lead
    (`lead` None) every receipt with words is listed: reading back too much is the safe side."""
    said = closegate.captures(record_text)
    found = []
    for page in vault.pages:
        found += _page_sentences(page, record_id, part, said, lead)
    for pick in picked:
        number = int(pick["number"])
        found.append(Sentence(pick.get("item") or f"^c{number:02d}", QUOTE, "", number, str(pick["words"])))
    return found


def _page_sentences(page, record_id, part, said, lead):
    scopes, seen = {}, set()
    for bullet in page.bullets:
        if bullet.generated or bullet.line in seen or bullet.label not in ("Decision", "Why"):
            continue
        seen.add(bullet.line)
        scopes.setdefault(bullet.item, []).append(bullet)
    out = []
    for item, bullets in scopes.items():
        cited = [(b, r) for b in bullets if b.label == "Decision" and (r := _receipt_for(b, record_id, part))]
        if not cited:
            continue
        name = item or str(page.meta.get("id") or page.name)
        for bullet, receipt in cited:
            if receipt.words and _is_lead(receipt.who, lead):
                out.append(Sentence(name, DECISION, page.path, receipt.ref.n, textedit.unescape(receipt.words), bullet.line))
        for bullet in bullets:
            if bullet.label == "Why":
                words = textedit.unescape(bullet.value)
                out.append(Sentence(name, WHY, page.path, _capture_of(words, said), words, bullet.line))
    return out


def _receipt_for(bullet, record_id, part):
    receipt = receipts.parse_decision(bullet.value)
    if receipt is None or receipt.record != record_id or receipt.ref is None or receipt.ref.part != part:
        return None
    return receipt


def _is_lead(who, lead):
    if lead is None:
        return True
    handle, names = lead
    return consent.same_handle(who, handle) or who.strip().casefold() in {n.casefold() for n in names}


def _capture_of(words, said):
    """The number of the first capture whose words contain `words`, else 0."""
    wanted = questions.normal_text(words)
    for capture in said.values():
        if wanted and wanted in questions.normal_text(capture.quote):
            return int(capture.n)
    return 0


def digest(found):
    """A fingerprint of the sentences as they stand. A line changed, added or cut after the lead's yes changes it."""
    body = "\n".join(sorted(f"{s.item}\t{s.line}\t{s.number}\t{s.words}" for s in found))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def is_excerpt(words, quote):
    """Whether `words` are a piece of `quote`, compared the way quotes are everywhere (`questions.normal_text`)."""
    wanted = questions.normal_text(words)
    return bool(wanted) and wanted in questions.normal_text(quote)


def reword(page_text, sentence, words, approved, cited):
    """`page_text` with the sentence's line carrying `words`. Raises ValueError when the words are neither an excerpt
    of `cited.quote` nor the words (or an excerpt) of `approved`, the lead capture that approves the new wording. With
    `approved`, a decision receipt is re-pointed to it. A quote has no page line: the text comes back as it was."""
    ok_cited = cited is not None and is_excerpt(words, cited.quote)
    ok_approved = approved is not None and is_excerpt(words, approved.quote)
    if not (ok_cited or ok_approved):
        raise ValueError("those words are not in what you said, and you haven't said yes to them")
    if sentence.line == QUOTE:
        return page_text
    lines = page_text.split("\n")
    index = _line_index(lines, sentence)
    prefix = f"- **{_BULLET_FOR[sentence.line]}:** "
    if sentence.line == WHY:
        lines[index] = prefix + textedit.inline(words)
    else:
        lines[index] = prefix + _repointed(lines[index][len(prefix):], words, approved if not ok_cited else None)
    return "\n".join(lines)


def _repointed(value, words, approved):
    old = receipts.parse_decision(value)
    ref = old.ref if approved is None else privaterecord.Ref(old.ref.part, int(approved.n))
    return receipts.decision_value(old.record, ref, old.who, words, old.stated_in)


def cut(page_text, sentence):
    """`page_text` without the sentence's line. A decision's words can't be cut: ValueError."""
    if sentence.line not in CUTTABLE:
        raise ValueError("a decision needs the lead's words on record")
    if sentence.line == QUOTE:
        return page_text
    lines = page_text.split("\n")
    del lines[_line_index(lines, sentence)]
    return "\n".join(lines)


def _line_index(lines, sentence):
    """The bullet's index: its recorded line when that line still holds the sentence, else the first line that does."""
    label = _BULLET_FOR[sentence.line]
    holds = re.compile(rf"^- \*\*{label}:\*\* ")

    def matches(i):
        if not 0 <= i < len(lines) or not holds.match(lines[i]):
            return False
        value = lines[i][holds.match(lines[i]).end():]
        if sentence.line == WHY:
            return textedit.unescape(value) == sentence.words
        receipt = receipts.parse_decision(value)
        return receipt is not None and receipt.ref is not None and receipt.ref.n == sentence.number \
            and textedit.unescape(receipt.words or "") == sentence.words

    if sentence.at and matches(sentence.at - 1):
        return sentence.at - 1
    for i in range(len(lines)):
        if matches(i):
            return i
    raise ValueError(f"the {sentence.line} line for {sentence.item} is not on {sentence.page}")
