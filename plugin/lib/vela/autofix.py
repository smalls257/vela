"""Which findings close fixes by itself. Pure.

A finding weighted `auto` (schema.WEIGHT) is one close can fix, so it is counted ("I'll fix 26 more myself when we
close") instead of said. The Violation this prevents is a Silent Fallback: a promise that close fixes something it
cannot. So `fixable` answers per finding, from the same code that would make the fix: W402 always (close renders),
W326 when `w326fix` can plan it, W358 when the plan has exactly one capability page, W408 when the
line can be found (it is simply removed). One that cannot is said.
"""
from vela import stagefix, w326fix, w358fix


def fixable(vault, finding):
    if finding.code == "W402":
        return True
    if finding.code == "W326":
        try:
            return bool(w326fix.plan([finding], {p.path: (p.id, p.text) for p in vault.pages}))
        except (w326fix.FixDrift, w326fix.NoStateLine):
            return False
    if finding.code == "W358":
        return any(c.path == finding.path for c in w358fix.plan(vault))
    if finding.code == "W408":
        return any(c.path == finding.path for c in stagefix.plan(vault))
    return False
