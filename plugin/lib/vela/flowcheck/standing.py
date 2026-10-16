"""Where each slice's recorded flow check stands now, in a reader's words. Pure: the catalog, the record as read
(`record.read_store`, the one reader of .vela/flowcheck-cache.json), the date and the checker's version in.

What it exists to prevent: a Silent Fallback, where a slice with no record, or a record of a slice that has changed
since, reads as passed because nothing said otherwise (R0: never a pass by default); and a second reader of the
record (the handoff and the dashboard each parsing the file their own way, drifting from the checker that writes it).

A record holds for the slice as it is now only when its fingerprint matches the slice prepared today with the budget
and the journeys it was explored with; otherwise it is "not checked since" the day it was recorded, and its result
is not shown as the slice's. A record that holds is judged afresh with today's overrides, the way `check-slice
--changed` reuses one (`flowcheck.finish`): an override that ended since stops covering its finding here too.
Nothing is explored here, so a reader pays milliseconds.
"""
from dataclasses import dataclass

from vela import flowcheck, say
from vela.flowcheck import record
from vela.flowcheck.findings import NOT_CHECKED, TITLES

PASSED, FINDINGS, NOT_FULLY, STALE, MISSING = "passed", "findings", "not fully checked", "stale", "not checked"


@dataclass(frozen=True)
class Standing:
    state: str  # one of PASSED, FINDINGS, NOT_FULLY, STALE, MISSING
    words: str  # "passed", "2 findings", "1 finding, not fully checked", "not fully checked", "not checked since 2026-10-12", "not checked"
    checked: str = ""  # the day the record was written, "" when there is none
    open: tuple = ()  # the open findings by name, when the record holds
    why: str = ""  # for a stale or missing record, what a reader should know

    @property
    def passed(self):
        return self.state == PASSED

    def line(self):
        """The standing in one line a reader hears: "passed on 14 Oct", "2 findings (an answer nobody handles), checked
        on 14 Oct", "Last checked 12 Oct; the flow or the checker has changed since, so run the flow check again.",
        "Nobody has run the flow check on it yet." No ISO date: this line reaches the handoff and the dashboard."""
        said = self.words + (f" ({', '.join(self.open)})" if self.open else "")
        if self.state in (PASSED, FINDINGS, NOT_FULLY):
            if not self.checked:
                return said
            return f"{said} on {short_day(self.checked)}" if self.state == PASSED else f"{said}, checked on {short_day(self.checked)}"
        if self.state == STALE and self.checked:
            return f"Last checked {short_day(self.checked)}; {self.why[:1].lower()}{self.why[1:]}" if self.why else f"Last checked {short_day(self.checked)}."
        return self.why or said


def short_day(iso):
    """'2026-10-14' -> '14 Oct'; anything that isn't a date as written."""
    words = say.date_words(iso)
    parts = words.split()
    return f"{parts[0]} {parts[1][:3]}" if len(parts) >= 2 and parts[0].isdigit() else words


def standing(catalog, store, key, today, version):
    """The Standing of the slice recorded under `key` (a slice's ID or release heading, or a flow ID checked alone)."""
    kept = (store.get("slices") or {}).get(key)
    if not isinstance(kept, dict) or "fingerprint" not in kept:
        return Standing(MISSING, "not checked", why="Nobody has run the flow check on it yet.")
    checked = str(kept.get("checked") or "")
    states, seconds = budget_of(kept)
    try:
        prepared = flowcheck.prepare(catalog, key, today, kept.get("journeys"))
    except (flowcheck.SliceNotFound, ValueError):
        return stale(checked, "The slice it was checked for isn't in the plan anymore.")
    if record.fingerprint(prepared, states, seconds, version) != kept["fingerprint"]:
        return stale(checked, "The flow or the checker has changed since, so run the flow check again.")
    try:
        explored = record.explored_of(kept)
    except ValueError:
        return stale(checked, "Its saved result can't be read, so run the flow check again.")
    result = flowcheck.finish(catalog, prepared, explored, today)
    errors = [f for f in result.open if f.code not in NOT_CHECKED]
    names = tuple(sorted({TITLES.get(f.code, f.code).lower() for f in errors}))
    partial = any(f.code in NOT_CHECKED for f in result.open)
    if errors:
        said = f"{len(errors)} finding{'' if len(errors) == 1 else 's'}" + (", not fully checked" if partial else "")
        return Standing(FINDINGS, said, checked, names)
    if partial:
        return Standing(NOT_FULLY, "not fully checked", checked)
    return Standing(PASSED, "passed", checked)


def standings(catalog, store, keys, today, version):
    """{key: Standing} for each of `keys`, from one record."""
    return {key: standing(catalog, store, key, today, version) for key in keys}


def stale(checked, why):
    return Standing(STALE, f"not checked since {checked}" if checked else "not checked", checked, why=why)


def budget_of(kept):
    """The budget a record was explored with: its own when it says so, else the check-slice defaults, so an old
    record from a run with another budget reads as stale rather than as holding."""
    budget = kept.get("budget")
    if isinstance(budget, list) and len(budget) == 2:
        return budget[0], budget[1]
    return flowcheck.DEFAULT_MAX_STATES, flowcheck.DEFAULT_MAX_SECONDS
