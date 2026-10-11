"""How complete a vault's design is, as five shares a reader can check, and their mean. Pure: reads the vault.

"Done" is never claimed: a vault with every share at 100% has settled what it has written down, and the catalogue
and the reviewers find only what is written. Each share says what it counts, so a reader can see what moves it.
"""
from dataclasses import dataclass

from planner import progress, questions, reading, schema

SETTLED = ("decided", "fact")


@dataclass(frozen=True)
class Share:
    name: str
    done: int
    total: int

    @property
    def ratio(self):
        return self.done / self.total if self.total else 1.0

    def text(self):
        return f"{self.name} {self.done} of {self.total}"


def items(vault):
    """Every app page, runtime page and contract on the ladder, and every initiative section, settled or not."""
    units = [u for app in vault.apps if app.meta.get("change") in schema.LADDERED_CHANGES for u in progress.units(vault, app)]
    sections = [p for p in vault.of_type("initiative-section")
                if not reading.not_started(model_body(p), p.type, str(p.meta.get("state", "")))]
    done = sum(1 for u in units if u.state in SETTLED) + sum(1 for p in sections if p.meta.get("state") in SETTLED)
    return Share("items settled", done, len(units) + len(sections))


def model_body(page):
    lines = page.text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:])
    return page.text


def unknowns(vault):
    found = vault.unknowns
    return Share("unknowns resolved", sum(1 for u in found if u.fact("State") == "resolved"), len(found))


def cells(vault):
    """One cell per laddered app per concern page; a missing row counts as unexamined, as CONVENTIONS says."""
    apps = [a for a in vault.apps if a.meta.get("change") in schema.LADDERED_CHANGES]
    concerns = vault.of_type("concern")
    seen = {(c.concern.id, c.app): c.state for c in vault.cells}
    total = len(apps) * len(concerns)
    done = sum(1 for p in concerns for a in apps if seen.get((p.id, a.name), "unexamined") != "unexamined")
    return Share("concern cells examined", done, total)


def owed_questions(vault):
    kept = questions.dispositions(vault)
    rows = questions.reviewer_rows(vault)
    done = sum(1 for d in kept if not d.pending) + sum(1 for r in rows if r.state not in ("open", "asked"))
    return Share("questions disposed", done, len(kept) + len(rows))


def pages(vault):
    made = [p for p in vault.pages if p.type in reading.TEMPLATE_TYPES]
    written = sum(1 for p in made if not reading.not_started(model_body(p), p.type, str(p.meta.get("state", ""))))
    return Share("pages written", written, len(made))


def measure(vault):
    """(the mean share as a whole percent, the five shares)."""
    shares = [items(vault), unknowns(vault), cells(vault), owed_questions(vault), pages(vault)]
    return round(100 * sum(s.ratio for s in shares) / len(shares)), shares


def line(vault):
    percent, shares = measure(vault)
    return f"Completeness: {percent}% ({', '.join(s.text() for s in shares)})."
