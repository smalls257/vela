"""`check-slice --changed` and `--all`: check the slices a change can touch, reuse the rest. Pure.

The impact walk (`impact.walk`) says which slices a change reaches and why; the record (`record`) says whether a
slice's model is the one last explored. Every slice of the vault is built (milliseconds) and fingerprinted, and then:

- reached by the walk, or never recorded, or recorded under another fingerprint: explored, and the reason said;
- not reached and recorded under the same fingerprint: reused, "unchanged since <date>";
- reached, but its model is the recorded one (a contract's prose changed, say): reused, and the line says so.

A slice the walk did not reach whose fingerprint moved anyway is explored, and its line says the walk missed it: the
record is a sensor on the walk, so a gap in the walk shows instead of serving a stale result. The exit status counts
every slice in the report, reused ones included: a failing slice that nobody touched is still failing (R0).
"""
from dataclasses import dataclass, field

from vela import flowcheck
from vela.flowcheck import record


@dataclass
class Line:
    key: str
    label: str
    result: object  # SliceResult
    reused: str = ""  # the date of the record reused, or ""
    why: str = ""  # why it was explored, or the note on a reused one

    @property
    def passes(self):
        return self.result.status == "passes"

    def words(self):
        status = self.result.status
        opened = self.result.open
        if opened and status.startswith("fails"):
            titles = sorted({flowcheck.TITLES.get(f.code, f.code).lower() for f in opened if f.code not in ("F10", "F11")})
            n = sum(1 for f in opened if f.code not in ("F10", "F11"))
            status += f", {n} open finding{'' if n == 1 else 's'} ({', '.join(titles)})" if n else ""
        if "not fully checked" in status:
            status += f" ({_unchecked_why(self.result)})"
        head = f"{self.label}: unchanged since {self.reused}, {status}" if self.reused else f"{self.label}: {status}"
        return f"{head}. {self.why}" if self.why else f"{head}."


def _unchecked_why(result):
    codes = {f.code for f in result.open}
    if "F11" in codes:
        return "the budget ran out"
    return "a line or property the check cannot read"


@dataclass
class Report:
    lines: list = field(default_factory=list)
    store: dict = field(default_factory=dict)  # the store to write back
    everything: str = ""  # why every slice was checked
    untouched: list = field(default_factory=list)
    unread: list = field(default_factory=list)  # changed files the check does not read
    warnings: list = field(default_factory=list)

    @property
    def checked(self):
        return [line for line in self.lines if not line.reused]

    @property
    def exit_code(self):
        return 0 if all(line.passes for line in self.lines) else 1

    def format(self, mode="--changed"):
        n, k = len(self.lines), len(self.checked)
        head = f"vela check-slice {mode}: checked {k} of {n} slice{'' if n == 1 else 's'}"
        if self.everything:
            head += f", every one, because {self.everything}"
        if n - k:
            head += f". The other {n - k} {'is' if n - k == 1 else 'are'} unchanged since {'its' if n - k == 1 else 'their'} last check"
        out = [head + "."]
        out += [f"Warning: {w}" for w in self.warnings]
        if self.untouched:
            out.append(f"Changed, and in no slice: {', '.join(self.untouched)}.")
        if self.unread:
            shown = ", ".join(self.unread[:5]) + (f" and {len(self.unread) - 5} more" if len(self.unread) > 5 else "")
            out.append(f"Changed, and not read by the check: {shown}.")
        out += [line.words() for line in self.lines]
        for line in self.checked:
            if not line.passes:
                out += ["", line.result.format()]
        return "\n".join(out)


def check_slices(catalog, today, store, walk=None, everything=False, max_states=flowcheck.DEFAULT_MAX_STATES,
                 max_seconds=flowcheck.DEFAULT_MAX_SECONDS, clock=flowcheck.frozen_clock, journeys=None, version="",
                 unread=()):
    """A Report over every slice of `catalog`. `walk` is impact.walk's answer (None with `everything`, for --all, which
    explores every slice and reuses nothing). `store` is the record as read; the report's store is the one to write."""
    report = Report(store={"format": record.FORMAT, "slices": dict(store.get("slices") or {})})
    if everything:
        report.everything = "--all asks for every one"
    elif walk is not None and walk.everything:
        report.everything = f"the walk cannot tell what changed: {walk.everything}"
    if walk is not None:
        report.untouched = list(walk.untouched)
    report.unread = list(unread)
    for found in catalog.slices:
        prepared = flowcheck.prepare(catalog, found.key, today, journeys)
        fp = record.fingerprint(prepared, max_states, max_seconds, version)
        kept = report.store["slices"].get(found.key)
        chains = (walk.affected.get(found.key) if walk is not None else None) or []
        reuse, why = _decide(kept, fp, chains, everything or bool(walk is not None and walk.everything))
        explored = None
        if reuse:
            try:
                explored = record.explored_of(kept)
            except ValueError as exc:
                report.warnings.append(f"the record of {found.label} does not read ({exc}), so it was checked afresh.")
                reuse, why = False, "Its record did not read."
        if explored is None:
            explored = flowcheck.explore_prepared(prepared, max_states, max_seconds, clock)
        result = flowcheck.finish(catalog, prepared, explored, today)
        if reuse:
            report.lines.append(Line(found.key, found.label, result, kept.get("checked", "an earlier check"), why))
        else:
            report.store["slices"][found.key] = record.to_record(result, explored, fp, today, (max_states, max_seconds))
            report.lines.append(Line(found.key, found.label, result, "", why))
    return report


def _decide(kept, fp, chains, everything):
    """(reuse?, why): the rules in the module doc."""
    same = isinstance(kept, dict) and kept.get("fingerprint") == fp
    because = "; ".join(chains)
    if everything:
        return False, ""
    if chains and same:
        return True, f"{because}, but the model it checks is the one last explored, so that exploration is reused."
    if chains:
        return False, f"Checked because {because}."
    if kept is None:
        return False, "Checked because it has no recorded result yet."
    if not same:
        return False, "Checked because what it reads changed in a way the impact walk did not trace."
    return True, ""

