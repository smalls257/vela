"""The lead's tuning page (ONBOARDING.md): which role specifics to stress, play down or hide, and a note per role.

The Violation this module exists to prevent is the Silent Fallback: a typo in "Hide: Contrcts" that quietly hides
nothing, so the lead believes the page works. So every name is checked against the fixed vocabulary
(`onboarding.NAMES`) and every mistake comes back as a Problem with the fix, never as a dropped line. A page with no
file is the standard path; a page with problems still applies everything that was understood.

Format (CONVENTIONS, "Onboarding"):

    ## Engineering
    - Stress: Contracts, Journeys
    - Play down: Open questions
    - Hide: Failure behavior
    - Note: Read the contract for the pilot first.

Pure: text in, `Tuning` out.
"""
import difflib
import re
from collections import namedtuple
from dataclasses import dataclass

from vela import onboarding, say

FILE = "ONBOARDING.md"
LABELS = {"stress": "stress", "play down": "play_down", "hide": "hide", "note": "note"}
HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*#*[ \t]*$")
BULLET = re.compile(r"^[ \t]*[-*][ \t]+([A-Za-z ]+?)[ \t]*:[ \t]*(.*?)[ \t]*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
Problem = namedtuple("Problem", "line text fix")


@dataclass(frozen=True)
class RoleTuning:
    stress: tuple = ()
    play_down: tuple = ()
    hide: tuple = ()
    note: str = ""


@dataclass(frozen=True)
class Tuning:
    roles: dict  # audience -> RoleTuning
    problems: tuple  # Problems, in file order

    def for_audience(self, audience):
        return self.roles.get(audience)


EMPTY = Tuning({}, ())
BY_LABEL = {onboarding.AUDIENCE_LABELS[a].casefold(): a for a in onboarding.AUDIENCES}


def parse(text):
    """The lead's page as a Tuning. Lines outside a `## <Role>` section and bullets with other labels are the lead's
    own prose and are left alone; a heading that names no role, or a name that is no module, is a Problem."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")  # an editor on Windows adds a BOM and CRLF; neither is the lead's
    roles, problems = {}, []
    audience, fields, fence = None, {}, None
    seen = set()  # roles already given a section; a later one for the same role is reported and ignored, the first stands

    def close():
        if audience is not None:
            roles[audience] = RoleTuning(tuple(fields.get("stress", ())), tuple(fields.get("play_down", ())),
                                         tuple(fields.get("hide", ())), fields.get("note", ""))

    for number, line in enumerate(text.split("\n"), start=1):
        opened = FENCE.match(line)
        if fence:
            if opened and opened.group(1)[0] == fence[0]:
                fence = None
            continue
        if opened:
            fence = opened.group(1)
            continue
        head = HEADING.match(line)
        if head:
            close()
            audience, fields = BY_LABEL.get(head.group(1).casefold()), {}
            if audience in seen:
                problems.append(Problem(number, f"{onboarding.AUDIENCE_LABELS[audience]} is listed twice", "Keep one section per role."))
                audience = None
            elif audience is not None:
                seen.add(audience)
            else:
                problems.append(Problem(number, f"'{head.group(1)}' is not a role",
                                        "Use one of: " + ", ".join(onboarding.AUDIENCE_LABELS[a] for a in onboarding.AUDIENCES)))
            continue
        bullet = BULLET.match(line)
        if bullet and audience is not None and bullet.group(1).casefold() in LABELS:
            _read_bullet(audience, LABELS[bullet.group(1).casefold()], bullet.group(2), number, fields, problems)
    close()
    return Tuning(roles, tuple(problems))


def _read_bullet(audience, field, value, number, fields, problems):
    label = onboarding.AUDIENCE_LABELS[audience]
    if field == "note":
        if "note" in fields:
            problems.append(Problem(number, f"{label} has a second note", "Keep one note per role; the first is used."))
            return
        leak = next((kind for kind in say.ID_KINDS if say.LEAD_PATTERNS[kind].search(value)), "")
        if leak:
            problems.append(Problem(number, f"the {label} note holds a code ({leak})", "Name the thing in words; the note is shown as you wrote it."))
        fields["note"] = value
        return
    found = fields.setdefault(field, [])
    names = [n.strip() for n in re.split(r"[,;]", value) if n.strip()]
    if not names:
        problems.append(Problem(number, f"the {label} '{field.replace('_', ' ').capitalize()}' line names no module", "Name at least one module, or delete the line."))
    for name in names:
        module = onboarding.BY_NAME.get(name.casefold())
        if module is None:
            near = difflib.get_close_matches(name.casefold(), list(onboarding.BY_NAME), n=1, cutoff=0.6)
            fix = f"Did you mean '{onboarding.NAMES[onboarding.BY_NAME[near[0]]]}'?" if near else "Use a module's name as the dashboard shows it."
            problems.append(Problem(number, f"'{name}' is not a module", fix))
        elif module in onboarding.CORE:
            problems.append(Problem(number, f"'{name}' is one of the five parts everyone gets, so it can't be moved or hidden", "Leave it out; the five parts always come first."))
        elif not any(module in ids for ids in onboarding.SPECIFICS[audience].values()):
            problems.append(Problem(number, f"'{name}' is not one of the {label} modules", "Pick one of the modules the dashboard shows for that role."))
        elif module in found or any(module in fields.get(other, ()) for other in ("stress", "play_down", "hide")):
            problems.append(Problem(number, f"'{name}' is listed twice for {label}", "Name each module once."))
        else:
            found.append(module)


def problems_text(tuning):
    """One plain line per problem, for `vela onboard check` and the build report."""
    return [f"The onboarding page, line {p.line}: {p.text}. {p.fix}" for p in tuning.problems]
