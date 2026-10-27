"""The pull request `vela close pr` opens: its title, its reviewers and its body (overhaul Task 12). Pure.

The Violation this exists to prevent is a God Method in prose: close's "The pull request, and what you tell the lead" and PR-BODY.md had the model work out
the reviewers, run greps, paste check lines and copy the consent block by hand, every close, and a
skipped step left a list out with nothing saying it was skipped. Everything here is computable, so it is computed:

- **Reviewers.** The `owner:` of each app page the session changed and of each consumer app of a contract it changed.
  A person's handle loses its `@`; a team handle `@org/team` is passed as `org/team` (gh's form); the lead's own
  handle is dropped, because GitHub refuses a PR author as its reviewer and the lead can't review their own session.
- **A challenge's reviewer** is also the solution lead, the `owner:` of `01-goals.md`: a challenge changes no app page,
  so no app owner would be asked otherwise.
- **The body**, short on purpose: it is for reading. The model's two or three sentences, then **What changed**: one
  line per item, its name and its new state in plain words ("now decided", "set back to not decided yet").
- **What the body does not carry.** Overrides, open questions, stale pages, the check result and the stage still
  run in `vela check` and in CI, which reviewers see on the PR, so the body does not repeat them, and an empty list
  does not need to say "none". The Violation this prevents is a Leaky Narrative of the record: receipts, record
  links, capture numbers, quotes and the push line made the description a transcript. Nothing here reads a capture's
  text; a reviewer who wants a line asks the lead, who can paste their own with `vela records show`. The notes are a
  Sensor for the lead, not a proof for the reviewer (plan 4.3).

What stays the model's is the two or three sentences a reviewer reads first; `close pr --prose FILE` passes them in.

PR titles use plain mode names ("2026-10-12 Brainstorm: desks", "Decisions: consent"): a reviewer scanning a PR list
reads what the session did, not the mode's internal display name ("Dump & Diverge").
"""
import re
from dataclasses import dataclass, field

from vela import say, schema, sessions

# Plain names for PR titles. A mode not listed keeps its own name, capitalized.
MODE_TITLES = {"dump": "Brainstorm", "discover": "Discovery", "shape": "Options", "boundary": "App boundaries",
               "allocate": "Allocation", "releases": "Releases", "grill": "Decisions", "requirements": "Requirements",
               "epics": "Epics", "challenge": "Challenge", "answer": "Answer"}

SAVED_SENTENCE = ("It's sent, but I couldn't open the review from here. I've kept its text; open Claude Code in "
                  "this folder and I'll try again.")
SAVED_COMMENT_SENTENCE = ("It's sent, but I couldn't add your answer to the challenge from here. I've kept its text; "
                          "open Claude Code in this folder and I'll try again.")

_HANDLE = re.compile(schema.HANDLE)


# ------------------------------------------------------------------ title and reviewers

def topic_of(record_title):
    """The record's topic: its title without the `<Mode>: ` prefix `session start` writes."""
    text = str(record_title or "").strip()
    for name in list(sessions.MODE_NAMES.values()) + list(MODE_TITLES.values()):
        if text.startswith(f"{name}: "):
            return text[len(name) + 2:].strip()
    return text


def title(date, modes, record_title, decided=0):
    """'2026-10-26 Options and one decision: booking jobs'. A session that settled something outside a grill says so,
    so a reviewer scanning the list sees a decision was made; a grill's title ("Decisions") already says it."""
    mode = modes[0] if modes else ""
    name = MODE_TITLES.get(mode, mode.capitalize())
    if decided and mode != "grill":
        name += f" and {say.count_words(decided)} decision{'' if decided == 1 else 's'}"
    return f"{date} {name}: {topic_of(record_title)}"


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


def solution_lead(vault):
    """The `owner:` of `01-goals.md`: the solution lead, who answers a challenge. A list of one, or none."""
    goals = vault.page("01-goals")
    owner = goals.meta.get("owner") if goals is not None else None
    return [str(owner)] if owner else []


def _facts(item):
    return tuple(sorted((label, bullet.value) for label, bullet in item.facts.items()))


# ------------------------------------------------------------------ the lists

STATE_WORDS = {"resolved": "answered"}


def state_move(before, after):
    """A state move in plain words: 'now decided', 'set back to not decided yet', 'answered'."""
    if after in STATE_WORDS:
        return STATE_WORDS[after]
    if before == "decided":
        return "set back to not decided yet"
    return f"now {after}"


def what_changed(rows, vault):
    """One line per `## Changes` row: the item's name and its new state. No record link and no capture number."""
    return [f"- {vault.name_of(r.item)}: {state_move(r.before, r.after)}" for r in rows if r.after]


# ------------------------------------------------------------------ the body

@dataclass
class Facts:
    """Everything the body says, gathered by the command. Lists are lines already in words."""
    summary: str
    changed: list = field(default_factory=list)
    prose: str = ""


def body(f):
    """The PR body's Markdown: the sentences and What changed, nothing else."""
    lines = [(f.prose or f.summary).strip()]
    lines += ["", "**What changed**", ""] + (list(f.changed) or ["- nothing promoted"])
    return "\n".join(lines).strip() + "\n"
