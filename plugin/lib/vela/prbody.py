"""The pull request `vela close pr` opens: its title, its reviewers and its body (overhaul Task 12). Pure.

The Violation this exists to prevent is a God Method in prose: close section 8 and PR-BODY.md had the model work out
the reviewers, run greps, paste check lines and copy the consent block by hand, every close, and a
skipped step left a list out with nothing saying it was skipped. Everything here is computable, so it is computed:

- **Reviewers.** The `owner:` of each app page the session changed and of each consumer app of a contract it changed.
  A person's handle loses its `@`; a team handle `@org/team` is passed as `org/team` (gh's form); the lead's own
  handle is dropped, because GitHub refuses a PR author as its reviewer and the lead can't review their own session.
- **The body's lists**, under the headings the audit of PR-BODY.md settled on, each said in words a reviewer reads,
  never as check lines: **Overdue open questions** (the question, its owner and its due date, the way `vela health`
  titles it, not W705 lines), **Questions still open** (by the question's text, not W806 lines), **Kept on Claude's
  suggestion (check these)**, **Decisions the owner hasn't heard read back**, **Other pages that may still say the old
  value**, and the stage line "Ready to move on: ...".
- **Decisions, What changed, the push line and In their words.** The Violation these exist to prevent is a Leaky
  Narrative of the record: the old Consent list pasted every capture's words where the whole team reads. Now
  **Decisions** is each receipt as the pages hold it (wordless where the words rule says so), **What changed** is
  each state move with the citation of the capture behind it, the push line is the day the lead said yes to
  sending, and **In their words** is only the lines the lead kept at the read-back (`.vela/close/<id>.quotes.json`).
  Nothing here reads a capture's text; a reviewer who wants a line asks the lead, who can paste their own with
  `vela records show`. The notes are a Sensor for the lead, not a proof for the reviewer (plan 4.3).

What stays the model's is the two or three sentences a reviewer reads first; `close pr --prose FILE` passes them in.
A list that is empty is left out, except the ones a reviewer must see even when empty (Overrides, Questions still
open, Check, Voice review), which say "none" or "not run: <why>": a missing list must never read as "checked, none"
(Silent Fallback).

PR titles use plain mode names ("2026-10-12 Brainstorm: desks", "Decisions: consent"): a reviewer scanning a PR list
reads what the session did, not the mode's internal display name ("Dump & Diverge").
"""
import re
from dataclasses import dataclass, field

from vela import closegate, privaterecord, receipts, say, schema, sessions

# Plain names for PR titles. A mode not listed keeps its own name, capitalized.
MODE_TITLES = {"dump": "Brainstorm", "discover": "Discovery", "shape": "Options", "boundary": "App boundaries",
               "allocate": "Allocation", "releases": "Releases", "grill": "Decisions", "requirements": "Requirements",
               "epics": "Epics", "challenge": "Challenge", "answer": "Answer"}

# A catalog entry is named as one to prune or tighten when it was ruled out this often, over enough copies to mean
# something: one copy ruled out once says nothing about the entry, and pruning stays the lead's call.
GAP_SHARE = 0.8
GAP_MIN_OWED = 3
# An old value shorter than this ("yes", "12") matches everywhere, so a grep for it lists noise, not stale pages.
OLD_VALUE_MIN = 12
# Bullets whose old text is bookkeeping, not a value another page would repeat.
NOT_VALUES = ("State", "Decision", "Source", "Sources", "Change", "Override", "Dissent", "Resolved in", "Opened")

SAVED_SENTENCE = ("It's sent, but I couldn't open the review from here. I've kept its text; open Claude Code in "
                  "this folder and I'll try again.")
SAVED_COMMENT_SENTENCE = ("It's sent, but I couldn't add your answer to the challenge from here. I've kept its text; "
                          "open Claude Code in this folder and I'll try again.")
REVIEWER_FILLS = "Filled in by the reviewer."

_HANDLE = re.compile(schema.HANDLE)


# ------------------------------------------------------------------ title and reviewers

def topic_of(record_title):
    """The record's topic: its title without the `<Mode>: ` prefix `session start` writes."""
    text = str(record_title or "").strip()
    for name in list(sessions.MODE_NAMES.values()) + list(MODE_TITLES.values()):
        if text.startswith(f"{name}: "):
            return text[len(name) + 2:].strip()
    return text


def title(date, modes, record_title):
    mode = modes[0] if modes else ""
    return f"{date} {MODE_TITLES.get(mode, mode.capitalize())}: {topic_of(record_title)}"


def handles(owner):
    """Every handle in an `owner:` value, without its `@`."""
    return [h[1:] for h in _HANDLE.findall(str(owner or ""))]


def reviewers(owners, own):
    """gh's `--reviewer` values for these `owner:` values, in first-seen order, the lead's own handle dropped."""
    out = []
    for owner in owners:
        for handle in handles(owner):
            if handle.lower() != str(own or "").lstrip("@").lower() and handle not in out:
                out.append(handle)
    return out


def _person(handle):
    return " ".join(part.capitalize() for part in handle.split("-") if part)


def _team(handle):
    words = handle.split("/", 1)[1].replace("_", "-").split("-")
    if words and words[-1].lower() == "team":
        words = words[:-1]
    return f"the {' '.join(w for w in words if w) or handle.split('/', 1)[1]} team"


def reviewer_words(found):
    """'Ines and the payments team': people first, then teams, as a lead would say them."""
    names = [_person(h) for h in found if "/" not in h] + [_team(h) for h in found if "/" in h]
    if len(names) < 2:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def owner_fields(vault, before, changed):
    """The `owner:` values whose holders review: each changed app page, and each consumer app of a changed contract.
    `before` is the vault at the branch point; `changed` the vault-relative paths changed since then."""
    out = []
    for app in vault.apps:
        if app.path in changed and app.meta.get("owner"):
            out.append(str(app.meta["owner"]))
    for contract in vault.contracts:
        if contract.page.path not in changed:
            continue
        old = before.item(contract.id) if before is not None else None
        if old is not None and _facts(old) == _facts(contract):
            continue
        out += [str(app.meta["owner"]) for app in vault.consumers(contract) if app.meta.get("owner")]
    return out


def _facts(item):
    return tuple(sorted((label, bullet.value) for label, bullet in item.facts.items()))


# ------------------------------------------------------------------ the lists

def section(heading, lines, empty=None):
    """`**heading**` and its lines; nothing when there are none, unless `empty` says what to write instead."""
    if not lines and empty is None:
        return []
    return [f"**{heading}**", ""] + (list(lines) or [f"- {empty}"])


def _sentence(text):
    text = str(text).strip()
    return text if text[-1:] in ".?!" else text + "."


FINGERPRINT_PENDING = "Part {n}'s notes are on the other machine and aren't fingerprinted yet."


def decision_lines(vault, record_id):
    """Each receipt that cites this record, as the page holds it, by the item's name."""
    out = []
    for ident, items in sorted(vault.items.items()):
        bullet = items[0].facts.get("Decision")
        found = receipts.parse_decision(bullet.value) if bullet is not None else None
        if found is not None and found.record == record_id:
            out.append(f"- {vault.name_of(ident)}: {bullet.value.strip()}")
    return out


def what_changed(rows, vault, record_id, part):
    """One line per `## Changes` row: the item's name, the move, and the citation of the capture behind it."""
    out = []
    for r in rows:
        if not r.after:
            continue
        line = f"- {vault.name_of(r.item)}: {r.before if r.before not in ('', '-') else 'new'} to {r.after}"
        number = r.capture_number
        out.append(f"{line}, {privaterecord.citation(record_id, part, int(number))}" if number else line)
    return out


def push_words(date):
    return f"Sent with your yes on {say.date_words(date)}."


def fingerprint_notes(stub_meta, part):
    """One line for each other part of the notes that no machine has fingerprinted yet. This machine's own part is
    fingerprinted by the close before it gets here."""
    return [FINGERPRINT_PENDING.format(n=n) for n, held in sorted(privaterecord.parts(stub_meta).items())
            if held == privaterecord.PENDING and n != part]


def in_their_words(picked, vault):
    """The lines the lead kept at the read-back, each by the item it concerns."""
    out = []
    for quote in picked:
        item = str(quote.get("item") or "")
        label = vault.name_of(item) if item else "Said in the session"
        out.append(f'- {label}: "{quote["words"]}"')
    return out


def kept_on_claude(record_text, vault):
    """Items kept or promoted on Claude's own words (origin `claude...`), by name only: a reviewer checks these
    first, and what Claude said stays in the notes."""
    out = []
    for c in closegate.captures(record_text).values():
        if c.is_person or not c.mark.startswith("keep"):
            continue
        found = re.search(r"\|([^\]]+)\]\]", c.mark)
        out.append(f"- {vault.name_of(found.group(1)) if found else 'an item'}")
    return out


def present_people(record_text):
    """The handles and names of everyone whose own words the record holds, lower-case, without `@`."""
    return {c.origin.strip().lstrip("@").lower() for c in closegate.captures(record_text).values() if c.is_person}


def not_read_back(decided, vault, present):
    """Items decided this session whose owner's words aren't in the record, so the owner hasn't heard the wording."""
    out = []
    for ident in decided:
        item = vault.item(ident)
        owner = (item.fact("Owner") if item is not None else "") or ""
        if not owner and item is not None:
            owner = str(item.page.meta.get("owner") or "")
        if not owner:
            pages = vault.by_id.get(ident)
            owner = str(pages[0].meta.get("owner") or "") if pages else ""
        owned = handles(owner)
        if owned and not any(h.lower() in present for h in owned):
            out.append(f"- {vault.name_of(ident)}: its owner hasn't heard the wording read back.")
    return out


def old_values(before, vault, decided_or_fact=("decided", "fact")):
    """[(item name, old wording)] for each value of a decided or fact item this session reworded."""
    if before is None:
        return []
    out = []
    for ident, items in sorted(vault.items.items()):
        now, old = items[0], before.item(ident)
        state = (now.fact("State") or "").split()[:1]
        if old is None or not state or state[0].strip(".,;").lower() not in decided_or_fact:
            continue
        for label, bullet in old.facts.items():
            was = bullet.value.strip()
            if label in NOT_VALUES or len(was) < OLD_VALUE_MIN:
                continue
            new = now.facts.get(label)
            if new is None or new.value.strip() != was:
                out.append((now.name or ident, was))
    return out


def old_value_hits(olds, texts):
    """'- <page> still says "<old>" (line n)' for every page (sessions excluded) that still holds an old wording."""
    out = []
    for name, was in olds:
        for path, text in sorted(texts.items()):
            if path.startswith("sessions/"):
                continue
            for number, line in enumerate(text.split("\n"), 1):
                if was in line:
                    out.append(f'- {path}, line {number}, may still say the old value of {name}: "{was}"')
    return out


def overdue_rows(vault, findings):
    """(question, owner, due) for each W705 finding, the open question's own words rather than the check line."""
    rows = []
    for finding in findings:
        if finding.code != "W705":
            continue
        for unknown in vault.unknowns:
            bullet = unknown.facts.get("Ask by")
            if unknown.page.path == finding.path and bullet is not None and bullet.line == finding.line:
                question = unknown.fact("Question") or unknown.name
                owner = " ".join("@" + h for h in handles(unknown.fact("Owner"))) or "no owner recorded"
                rows.append((question, owner, unknown.fact("Ask by")))
    return rows


def overdue_lines(rows):
    return [f"- {_sentence(q)} Owner {owner}, due {due}." for q, owner, due in rows]


def open_question_lines(pending):
    """(question, subject title) for each standard question still owed on what this session changed."""
    return [f'- "{q.rstrip("?")}?" for {subject}' for q, subject in pending]


def catalog_gap_lines(stats, questions):
    """Entries `questions --stats` shows as nearly always ruled out: candidates to prune or tighten, the lead's call."""
    out = []
    for entry in stats.get("entries", ()):
        if entry["owed"] >= GAP_MIN_OWED and entry["not_applicable_share"] >= GAP_SHARE:
            words = questions.get(entry["entry"], "a standard question")
            out.append(f'- "{words.rstrip("?")}?" was ruled out {entry["not_applicable"]} of {entry["owed"]} times: '
                       "one to prune or tighten.")
    return out


def override_lines(added, vault):
    """Each override this session wrote: its item, the rules it sets aside, by whom, and the reason."""
    return [f"- {name}: {', '.join(o.rules)}, by {o.by} on {o.date}: {o.reason}" for name, o in added]


def voice_lines(voice, title_of):
    """The voice review from `.vela/close/<id>.voice.json`, or why there is none."""
    if voice is None:
        return ["- not run: no voice review was recorded for this session", "- voicescore: not run (no voice review)"]
    out = [f'- Dropped as redundant on {title_of(r.get("page", ""))}: "{r.get("sentence", "")}" (the reviewer asked)'
           for r in voice.get("redundant") or ()]
    out += [f"- Kept the earlier draft of {title_of(r.get('page', ''))}: {r.get('why', '')}"
            for r in voice.get("restored") or ()]
    out += [f"- Rewritten and kept: {title_of(page)}" for page in voice.get("kept") or ()]
    if not out:
        out.append("- The reviewer flagged nothing.")
    out.append(f"- {voice['voicescore']}" if voice.get("voicescore") else "- voicescore: not run (not asked for)")
    return out


def stage_line(app, reached, typed):
    return f"Ready to move on: {app}'s pages are ready for {reached}; its stage still says '{typed}'."


def red_check(ident, name, state):
    """The challenge PR's paragraph on the red check, which depends on one fact: is the item decided?"""
    if state != "decided":
        return (f"Nothing blocks this merge: {name} ({ident}) is {state or 'not decided'}, not decided, so the "
                "dispute lives in the open question and the Dissent line, and the item can't be decided while that "
                "question is open.")
    back = "reopened" if ident.startswith("EPC-") else "assumption"
    return (f"E316 is deliberate. `vela check` fails on it until it is answered, so this PR shouldn't merge "
            f"while main reads {name} ({ident}) as decided with an open blocker. The solution lead answers on this "
            f"branch, either by resolving the open question in a Grill or by setting the item back to {back}. After "
            "that the check turns green and the PR can merge. To answer, run /vela:grill and name this PR or "
            f"{ident}.")


def answer_check(ident, still_reported):
    if still_reported:
        return f"E316 for {ident} is still reported: this answer hasn't cleared it yet."
    return f"E316 for {ident} should now be gone."


def check_line(findings, page_count):
    errors = sum(1 for f in findings if f.is_error)
    return f"vela check: {errors} errors, {len(findings) - errors} warnings in {page_count} pages"


# ------------------------------------------------------------------ the body

@dataclass
class Facts:
    """Everything the body says, gathered by the command. Lists are lines already in words."""
    summary: str
    decisions: list = field(default_factory=list)
    push_line: str = ""
    in_their_words: list = field(default_factory=list)
    fingerprint_note: list = field(default_factory=list)
    changed: list = field(default_factory=list)
    voice: list = field(default_factory=list)
    kept_on_claude: list = field(default_factory=list)
    not_read_back: list = field(default_factory=list)
    overrides: list = field(default_factory=list)
    old_values: list = field(default_factory=list)
    overdue: list = field(default_factory=list)
    open_questions: list = field(default_factory=list)
    catalog_gaps: list = field(default_factory=list)
    red_check: str = ""
    check: list = field(default_factory=list)
    stage: list = field(default_factory=list)
    prose: str = ""


def body(f):
    """The PR body's Markdown."""
    lines = [(f.prose or f.summary).strip(), ""]
    lines += section("Decisions", f.decisions, empty="none")
    lines += [""] + section("What changed", f.changed, empty="nothing promoted")
    lines += [""] + ([f.push_line] if f.push_line else []) + f.fingerprint_note
    block = section("In their words", f.in_their_words)
    lines += [""] + block if block else []
    for heading, items, empty in (("Voice review", f.voice, "not run"),
                                  ("Kept on Claude's suggestion (check these)", f.kept_on_claude, None),
                                  ("Decisions the owner hasn't heard read back", f.not_read_back, None),
                                  ("Overrides", f.overrides, "none"),
                                  ("Other pages that may still say the old value", f.old_values, None),
                                  ("Overdue open questions", f.overdue, None),
                                  ("Questions still open", f.open_questions, "none"),
                                  ("Catalog entries to prune or tighten", f.catalog_gaps, None)):
        block = section(heading, items, empty)
        lines += [""] + block if block else []
    if f.red_check:
        lines += ["", "**The red check**", "", f.red_check]
    lines += [""] + section("Check", [f"- {line}" for line in f.check], empty="not run")
    if f.stage:
        lines += ["", "**Stage**", ""] + [f"- {line}" for line in f.stage]
    lines += ["", f"**Structural fixes:** {REVIEWER_FILLS}",
              f"**Prose edits:** {REVIEWER_FILLS}"]
    return "\n".join(lines).strip() + "\n"
