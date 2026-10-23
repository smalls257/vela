"""What `vela check` says about each slice from the flow checker's result. Pure: a Catalog and a date in.

W391 for a slice with a drawn flow whose check does not pass, while it is not yet building. W395 once a slice is at
building or later: by then its findings must each be fixed or covered by an override with an end date, and a slice
with nothing drawn is not fully checked, never a pass (R0). E398 for an override past its end date, wherever it sits:
it covers nothing any more, so the finding it named blocks the slice again, and a red line says so instead of a
quiet uncovering. Every slice comes from `slices.read_slices` through the catalog, and every override through
`readers.flow_overrides`: one reader each.
"""
from vela import flowcheck
from vela.model import Finding


def checked(catalog, found, today, max_states):
    """The flow checker's result for one slice, or None when check leaves it to check-slice: a slice that names no flow,
    or one with nothing drawn that is not building yet. The one place that decides which slices check runs, so the
    dashboard's flow-check state and check's W391 and W395 can never judge different slices."""
    drawn = any(catalog.flows[f].has_diagram for f in found.flows if f in catalog.flows)
    if not found.flows or not (drawn or found.at_least("building")):
        return None
    return flowcheck.check_catalog(catalog, found.key, today, max_states)


def state(catalog, found, today, max_states):
    """Where one slice's flow check stands, for a reader: its status ("passes", "fails", "not fully checked", "fails,
    and is not fully checked", or "not run" when check leaves it to check-slice), the open findings by name, how many an
    override covers, and every override that could cover a finding of the slice, with its end date and whether it has
    ended (an ended override covers nothing: E398)."""
    result = checked(catalog, found, today, max_states)
    rules = [o for f in found.flows if f in catalog.flows for o in catalog.flows[f].overrides]
    rules += list(catalog.slice_overrides.get(found.key, ()))
    overrides = [{"code": o.code, "item": o.item, "case": o.case, "until": o.until, "ended": o.until < today, "text": o.text,
                  "where": o.where} for o in sorted(set(rules), key=lambda o: o.where)]
    if result is None:
        return {"status": "not run", "open": [], "covered": 0, "overrides": overrides}
    open_ = [f for f in result.findings if f.severity == "error"]
    return {"status": result.status, "open": sorted({flowcheck.TITLES.get(f.code, f.code).lower() for f in open_}),
            "covered": sum(1 for f in result.findings if f.severity == "covered"), "overrides": overrides}


def findings(catalog, today, max_states):
    out = []
    for found in catalog.slices:
        result = checked(catalog, found, today, max_states)
        if result is None or result.status == "passes":
            continue
        building = found.at_least("building")
        open_ = [f for f in result.findings if f.severity == "error"]
        names = sorted({flowcheck.TITLES.get(f.code, f.code).lower() for f in open_})
        what = f"{len(open_)} open finding{'' if len(open_) == 1 else 's'} ({', '.join(names)})"
        target = found.id or found.name
        if building:
            out.append(Finding(found.path, found.lines.get("Status", found.line), "W395",
                               f"{found.label} is {found.status}, but its flow check {_verb(result.status)}: {what}, "
                               "and no override with an end date covers them.",
                               f"Run vela check-slice {target} for the traces and owners; fix each, or add an override "
                               "with an end date under the slice page's ## Overrides."))
        else:
            said = f"{found.label}: its flow check {_verb(result.status)}" if found.id else f"{found.name} {result.status}"
            out.append(Finding(found.path, found.line, "W391", f"{said}: {what}.",
                               f"Run vela check-slice \"{target}\" for the traces and owners, and fix or override each."))
    out += expired(catalog, today)
    return out


def _verb(status):
    """"fails" and "fails, and is not fully checked" read after "its flow check"; "not fully checked" needs an "is"."""
    return status if status.startswith("fails") else f"is {status}"


def expired(catalog, today):
    """E398 for each flow-check override whose end date has passed, on a flow page or a slice page."""
    rules = [o for flow in catalog.flows.values() for o in flow.overrides]
    rules += [o for found in catalog.slice_overrides.values() for o in found]
    out = []
    for o in sorted(set(rules), key=lambda o: o.where):
        if o.until >= today:
            continue
        path, _, line = o.where.rpartition(":")
        out.append(Finding(path, int(line) if line.isdigit() else 1, "E398",
                           f"The override for {o.code} on {o.item} ({o.case}) ended on {o.until}, so the finding it covered "
                           "blocks its slice again.",
                           "Fix the finding and delete the override, or write a new end date and why it moved."))
    return out
