"""What `vela check --fix W358` (and `--fix auto`) changes: a flow with no `capabilities:` field gets the plan's only
capability, written onto the flow's own page.

The Violation this exists to prevent is Forensic Coding. W358 asks which capability each journey serves. When the plan
has exactly one capability page there is one right answer, and the fact belongs on the flow (Anchor), not in a guess the
dashboard makes from the steps, so a second capability later changes nothing already written. With two or more there
is no one answer, so this plans nothing and the finding stays the lead's.

Pure: the vault in, changes out; `rewrite` is text in, text out. The shell writes through `edge/atomic.py`.
"""
import re
from dataclasses import dataclass

FIXABLE = ("W358",)
_FIELD = re.compile(r"^capabilities:[ \t]*(?P<value>.*?)[ \t]*$")


@dataclass(frozen=True)
class Change:
    path: str
    line: int
    page: str    # the flow's id
    before: str  # "" when the flow had no capabilities line
    after: str   # "capabilities: [CAP-001]"
    why: str

    def as_json(self):
        return {"path": self.path, "page": self.page, "line": self.line, "from": self.before, "to": self.after}


def plan(vault):
    """One change for each flow with no capabilities, when exactly one capability page exists; else ()."""
    caps = vault.of_type("capability")
    if len(caps) != 1:
        return ()
    after = f"capabilities: [{caps[0].id}]"
    return tuple(Change(flow.path, 1, flow.id, "", after, f"{flow.id} serves the plan's one capability, {caps[0].id}")
                 for flow in sorted(vault.of_type("flow"), key=lambda p: p.path) if not flow.meta.get("capabilities"))


def set_capabilities(text, line):
    """`text` with its frontmatter `capabilities:` line set to `line`, added before the closing `---` when absent."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("the page has no frontmatter to write the capability into")
    for n in range(1, len(lines)):
        if lines[n].strip() == "---":
            lines.insert(n, line)
            return "\n".join(lines)
        if _FIELD.match(lines[n]):
            ending = "\r" if lines[n].endswith("\r") else ""
            lines[n] = line + ending
            return "\n".join(lines)
    raise ValueError("the page's frontmatter never closes")


def rewrite(changes, texts):
    """{path: new text} for each change, from {path: current text}."""
    return {c.path: set_capabilities(texts[c.path], c.after) for c in changes}
