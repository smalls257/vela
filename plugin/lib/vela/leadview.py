"""What the lead hears of a check, by weight. Pure.

Every finding code carries one weight (schema.WEIGHT). `decision` and `scale:*` findings are said at every size; `polish`
(reading load) is kept quiet below the size that shows it; `auto` is counted when close fixes it, else said. The
Violation this exists to prevent is a Black Box by noise: 119 lines in arrival order hid the 21 that matter. It must not
become a Silent Fallback, so the split is total (said + wording + fixed is every finding), the quiet ones are counted in
one line each, and plain `vela check` and CI never call this: they list everything.
"""
from dataclasses import dataclass

from vela import autofix, schema
from vela.sizing import Need


@dataclass(frozen=True)
class LeadView:
    said: tuple      # findings the lead hears, errors first
    wording: tuple   # polish findings kept quiet at this size
    fixed: tuple     # auto findings close fixes itself


def split(vault, findings, sized):
    said, wording, fixed = [], [], []
    for finding in findings:
        weight = schema.WEIGHT.get(finding.code, "decision")  # a code with no weight is a decision: said, never quiet
        if weight == "polish" and not sized.needs(Need.READING_LOAD_SHOWN):
            wording.append(finding)
        elif weight == "auto" and autofix.fixable(vault, finding):
            fixed.append(finding)
        else:
            said.append(finding)
    return LeadView(tuple(sorted(said, key=lambda f: not f.is_error)), tuple(wording), tuple(fixed))
