"""What `vela check --fix W326` changes: each flagged page's frontmatter `state`, set to what W326 says.

Why this is code and not prose (close section 6, overhaul Task 21b): a goals page whose every goal is decided, or a
constraints page whose every row cites its source, still reads unsettled to every reader and to `vela status` until its
own `state` follows. There is one right answer, so the model never hand-edits a state line (Shield: the rule and its
fix live in one place, and Task 24's hook can deny a typed state line without blocking the close).

The Violation this module's shape prevents is a Distributed Monolith between the rule and its fix: W326 is decided in
`rules.page_state_rules`, and a second copy of "which state is right" here would drift from it silently. So the target
is read from the finding the rule wrote, by one strict pattern, and a finding that no longer reads `Set state: <state>`
raises FixDrift (a vela bug, loudly) rather than guessing (Silent Fallback). A state line that is missing raises too.

Pure: text in, text out. The shell (`commands/check.py`) reads the vault, runs the check, writes through
`edge/atomic.py`, and checks the pages again so the new state's own duties (a fact lists its sources, E304) are said.
"""
import re
from dataclasses import dataclass

FIXABLE = ("W326",)
STATES = ("inkling", "assumption", "fact", "decided")
_TARGET = re.compile(r"^Set state: (?P<state>" + "|".join(STATES) + r")\b")
_STATE_LINE = re.compile(r"^state:[ \t]*(?P<value>.*?)[ \t]*$")


class FixDrift(Exception):
    """A W326 finding no longer says which state to set: the rule's Fix line changed and this module did not."""


class NoStateLine(Exception):
    """The page's frontmatter has no `state:` line to set."""


@dataclass(frozen=True)
class Change:
    path: str
    page: str  # the page's id
    line: int
    before: str
    after: str
    why: str  # the finding's message, which says what the rows already are

    def as_json(self):
        return {"path": self.path, "page": self.page, "from": self.before, "to": self.after, "line": self.line}


def target(finding):
    """The state a W326 finding says to set."""
    found = _TARGET.match(finding.fix or "")
    if not found:
        raise FixDrift(f"vela bug: W326 on {finding.path} no longer says 'Set state: <state>' (its Fix line is "
                       f"{finding.fix!r}), so --fix cannot tell which state to set.")
    return found.group("state")


def frontmatter_state(text):
    """(index of the `state:` line, its value) in the frontmatter, or NoStateLine."""
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for n, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                break
            found = _STATE_LINE.match(line)
            if found:
                return n, found.group("value")
    raise NoStateLine("the page has no state line in its frontmatter")


def set_state(text, state):
    """`text` with its frontmatter `state:` line set to `state`; every other byte unchanged."""
    index, _ = frontmatter_state(text)
    lines = text.split("\n")
    ending = "\r" if lines[index].endswith("\r") else ""  # a page saved with Windows line endings keeps them
    lines[index] = f"state: {state}{ending}"
    return "\n".join(lines)


def plan(findings, pages):
    """The changes the W326 findings ask for. `pages` maps a finding's path to (page id, page text). One change a page:
    a page flagged twice (two tables) takes the least settled target, so the fix never claims more than every row
    shows."""
    wanted = {}
    for finding in findings:
        if finding.code not in FIXABLE:
            continue
        state = target(finding)
        held = wanted.get(finding.path)
        if held is None or STATES.index(state) < STATES.index(held[0]):
            wanted[finding.path] = (state, finding)
    changes = []
    for path in sorted(wanted):
        state, finding = wanted[path]
        page_id, text = pages[path]
        _, before = frontmatter_state(text)
        if before != state:
            changes.append(Change(path, page_id, finding.line, before, state, finding.message))
    return changes


def rewrite(changes, texts):
    """{path: new text} for each change, from {path: current text}."""
    return {c.path: set_state(texts[c.path], c.after) for c in changes}
