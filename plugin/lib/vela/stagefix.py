"""What `vela check --fix W408` (and `--fix auto`) changes: a page's old `stage:` frontmatter line is removed.

The Violation this exists to prevent is a Fossil Comment. Nobody types a stage any more: vela works it out from the
pages an app reaches (`ladder.stage`), so a `stage: target` line left on a page says one thing while the plan says
another. There is one right answer, delete the line, so no lead has to decide it. No shim reads the old line first
(the plan has no users to keep it for).

Pure: the vault in, changes out; `rewrite` is text in, text out. The shell writes through `edge/atomic.py`.
"""
from dataclasses import dataclass

FIXABLE = ("W408",)


@dataclass(frozen=True)
class Change:
    path: str
    line: int
    page: str    # the page's id
    before: str  # "stage: target"
    after: str   # "" (the line is gone)
    why: str

    def as_json(self):
        return {"path": self.path, "page": self.page, "line": self.line, "from": self.before, "to": self.after}


def _stage_span(lines):
    """(first index, end index) of the frontmatter `stage:` entry, with any indented continuation, else None."""
    if not lines or lines[0].strip() != "---":
        return None
    for n in range(1, len(lines)):
        if lines[n].strip() == "---":
            return None
        if lines[n].startswith("stage:"):
            end = n + 1
            while end < len(lines) and lines[end].strip() != "---" and lines[end][:1] in (" ", "\t", "-"):
                end += 1
            return n, end
    return None


def plan(vault):
    """One change for each page whose frontmatter still has a `stage:` line."""
    out = []
    for page in sorted(vault.pages, key=lambda p: p.path):
        span = _stage_span(page.text.split("\n"))
        if span is not None:
            out.append(Change(page.path, span[0] + 1, page.id or page.name, page.text.split("\n")[span[0]].rstrip("\r"),
                              "", "vela works the stage out from the pages now"))
    return tuple(out)


def remove_stage(text):
    lines = text.split("\n")
    span = _stage_span(lines)
    if span is None:
        raise ValueError("the page has no frontmatter stage line to remove")
    return "\n".join(lines[:span[0]] + lines[span[1]:])


def rewrite(changes, texts):
    """{path: new text} for each change, from {path: current text}."""
    return {c.path: remove_stage(texts[c.path]) for c in changes}
