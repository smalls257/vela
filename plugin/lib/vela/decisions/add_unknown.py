"""`add unknown`: a question nobody present can answer, as `### UNK-nnn <name>` on `11-unknowns-and-risks.md`
(CONVENTIONS "Fact bullets", MODES "Unknowns", close section 2, grill section 5).

The rules, each with the reason the skills gave:

- **Numbered past every open branch** (`textedit.next_id`), because an open session branch may already hold the number
  you would guess, and two headings with one ID fail the check (E208).
- **Owner is a handle**, the lead chasing it, because the unknown's owner and ask-by date are the record of who is asked
  and by when. The person who would actually know goes on `**Ask:**`, a handle or a role in words.
- **Ask by**, when not given, is the fixed rule (`markrules.ask_by`): the date the lead said, else the nearest hard date
  the vault holds (a constraint or a release target), else two weeks from today. Fixed so the lead is told the date
  chosen instead of being asked for bookkeeping.
- **Blocks** links each item it blocks by its heading (an open unknown that lists an item stops it being decided), or
  names an owed question's copy ID as written (an E805 deferral blocks the question), or says `nothing`.
- **The agenda follows** (grill section 5): every agenda item it blocks comes off the agenda, `off-agenda: UNK-nnn`,
  unless the lead overrode GATE-4 for it, and `now_blocks` says which so the CLI can tell the lead by name.
- **No second copy of an open question** (a Silent Fallback of the ledger: two owners chase one answer, and the page
  counts one question twice). A new question whose words overlap an open one's by `SAME_QUESTION` or more is
  refused with the existing question's name, and the fix is to add to it. `different_because` is the override: the
  reason it is a different question, written on the new one so the choice is on the page.
- With a `capture`, the record gets the `## Changes` row (`- -> open`) and the capture its keep mark, so the new
  question can be traced to the words it came from; a capture an earlier mode already marked keeps its mark.
"""
import re

from vela import markrules, schema as vault_schema
from vela.decisions import agenda, textedit
from vela.decisions.schema import Write

PAGE = "11-unknowns-and-risks"
SECTION = "Unknowns"
HANDLE = re.compile(rf"^{vault_schema.HANDLE}$")
COPY = re.compile(r"^(?:Q-[A-Z]{3}-\d{2}@[\w*.-]*[\w*]|R-[A-Z]{3}-\d{2,})$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SAME_QUESTION = 0.7  # share of the shorter question's content words found in the other
MIN_WORDS = 3        # a question with fewer content words is too short to call a copy
STOP = frozenset("a an and are as at be by can do does for from has have how if in is it its of on or our that the "
                 "their there this to us was we what when where which who whom why will with would".split())
OPEN_UNKNOWN = re.compile(r"^### (UNK-\d+) (.+?)\s*$")

FIELDS = {"name": "the short name for the heading: at most six words, none of # | ^ : % [ ]",
          "question": "the question, in the lead's words (leave null to take the capture's words)",
          "capture": "the capture the question came from (\"^c12\")",
          "owner": "the handle of the lead chasing it: run vela whoami",
          "ask": "who would actually know, when that isn't the owner: a handle or a role in words",
          "ask_by": "YYYY-MM-DD; leave null for the fixed rule (the lead's date, the nearest hard date, else +14 days)",
          "blocks": "the IDs it blocks (items, pages, or an owed question's copy ID); empty for nothing",
          "different_because": "only when vela names an open question that is nearly the same: why this one is "
                               "different, in the lead's words (it is written on the new question)",
          "id": "leave null: vela numbers it past every open branch"}
REQUIRED = ("name", "owner")
EXAMPLE = {"name": "Till rig owner", "capture": "^c12", "owner": "@priya", "ask": "the store manager",
           "blocks": ["CON-003"]}


def question_of(item, record):
    return item.get("question") or textedit.quote(record, item.get("capture"))


def ask_by(item, vault, record):
    if item.get("ask_by"):
        return item["ask_by"]
    words = item.get("question") or ""
    capture = record.capture(item["capture"]) if item.get("capture") else None
    if capture is not None:
        words = f"{capture.words} {words}"
    return markrules.ask_by(words, markrules.hard_dates(vault.model), textedit.today(vault))


def blocks_value(item, vault):
    """(the `**Blocks:**` value, [IDs it can't find])."""
    parts, missing = [], []
    for ident in item.get("blocks") or []:
        ident = str(ident).strip()
        if COPY.match(ident):
            parts.append(ident)
            continue
        found = textedit.link(vault, ident)
        if found is None:
            missing.append(ident)
        else:
            parts.append(found)
    return (", ".join(parts) if parts else "nothing"), missing


def content_words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.casefold()) if w not in STOP}


def open_questions(page):
    """[(ID, name, question)] for every open `### UNK-nnn` block on the unknowns page."""
    found, current = [], None
    for line in page.split("\n"):
        head = OPEN_UNKNOWN.match(line)
        if head:
            current = {"id": head[1], "name": head[2], "question": "", "open": False}
            found.append(current)
        elif line.startswith("#"):
            current = None  # a risk or another section's heading ends the block
        elif current and line.startswith("- **Question:**"):
            current["question"] = line.split(":**", 1)[1].strip()
        elif current and re.match(r"- \*\*State:\*\*\s*open\b", line):
            current["open"] = True
    return [(c["id"], c["name"], c["question"]) for c in found if c["open"]]


def same_question(words, other):
    """Whether two questions share `SAME_QUESTION` of the shorter one's content words."""
    a, b = content_words(words), content_words(other)
    if min(len(a), len(b)) < MIN_WORDS:
        return False
    return len(a & b) / min(len(a), len(b)) >= SAME_QUESTION


def duplicate_of(item, vault, record):
    """(ID, name) of an open question this one repeats, or None."""
    words = question_of(item, record) or ""
    path = textedit.page_path(vault, PAGE) or f"{PAGE}.md"
    for ident, name, question in open_questions(vault.text(path) or ""):
        if same_question(words, question):
            return ident, name
    return None


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    for refusal in (textedit.heading_refusal(item["name"]),
                    textedit.id_refusal(vault, item["id"], "UNK") if item.get("id") else None):
        if refusal is not None:
            found.append(refusal)
    if not HANDLE.match(str(item.get("owner") or "")):
        found.append(textedit.refusal("add-owner", "I need the handle of whoever chases this question.",
                                      f"owner {item.get('owner')!r} is not a handle; use the lead's (vela whoami).",
                                      override="none: an unknown's owner starts with a handle"))
    if not found and not question_of(item, record):
        found.append(textedit.refusal("add-question", "I need the question itself before I can write it down.",
                                      "Give question, or a capture holding the lead's words."))
    if item.get("ask_by") and not DATE.match(str(item["ask_by"])):
        found.append(textedit.refusal("add-ask-by", "That ask-by date isn't a date I can read.",
                                      "Give ask_by as YYYY-MM-DD, or leave it null for the fixed rule."))
    same = None if found or item.get("different_because") else duplicate_of(item, vault, record)
    if same:
        found.append(textedit.refusal(
            "add-duplicate-question", f"That's nearly the same question as \u201c{same[1]}\u201d, which is still open. "
                                      "Shall I add to that one instead?",
            f"{same[0]} is open with near-identical wording (at least {int(SAME_QUESTION * 100)}% of the shorter "
            "question's words). Add to it instead: put the new detail in its Question, its Ask or its Blocks. If the "
            "lead says this is a different question, run again with different_because (--different-because) set "
            "to their reason.",
            override="different_because: why it is a different question, in the lead's words"))
    missing = blocks_value(item, vault)[1]
    if missing:
        found.append(textedit.refusal("add-blocks", "I can't find something this question would hold up, so I filed "
                                                    "nothing.",
                                      f"blocks names {', '.join(missing)}, which the vault doesn't hold. Use an item "
                                      "or page ID, or an owed question's copy ID.",
                                      override="none: Blocks links what exists, or says nothing"))
    return found


def block_lines(ident, item, vault, record):
    lines = [f"### {ident} {item['name'].strip()}", "",
             f"- **Question:** {textedit.inline(question_of(item, record))}",
             f"- **Owner:** {item['owner']}"]
    if item.get("ask"):
        lines.append(f"- **Ask:** {textedit.inline(item['ask'])}")
    if item.get("different_because"):
        lines.append(f"- **Not the same as an open question because:** {textedit.inline(item['different_because'])}")
    lines += [f"- **Opened:** {textedit.today(vault)}", "- **State:** open",
              f"- **Ask by:** {ask_by(item, vault, record)}",
              f"- **Blocks:** {blocks_value(item, vault)[0]}"]
    return lines


def apply(item, vault, record):
    ident = textedit.new_id(item, vault, "UNK")
    path = textedit.page_path(vault, PAGE) or f"{PAGE}.md"
    page = vault.text(path) or ""
    page = textedit.insert_block(page, SECTION, block_lines(ident, item, vault, record), before=("Risks",
                                                                                                 "Question ledger"))
    text = textedit.record_text(record, vault)
    heading = f"{ident} {item['name'].strip()}"
    if item.get("capture"):
        text = textedit.add_change(text, ident, "-", "open", textedit.capture_link(record.id, item["capture"]))
        text = textedit.mark_if_unmarked(text, item["capture"], textedit.keep_mark(PAGE, heading, ident, "open"))
    for blocked in now_blocks(dict(item, id=ident), text):
        text = agenda.block(text, blocked, ident)
    return [Write(path, page)] + textedit.record_writes(record, vault, text)


def now_blocks(item, record_text):
    """The agenda items this unknown holds up: on the agenda, not decided, GATE-4 not overridden."""
    on = agenda.entries(record_text)
    return [ident for ident in (str(b).strip() for b in item.get("blocks") or [])
            if ident in on and agenda.now_blocked(on[ident])]
