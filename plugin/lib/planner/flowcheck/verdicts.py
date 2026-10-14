"""What `planner check` says about each slice from the flow checker's result. Pure: a Catalog and a date in.

W391 for a slice with a drawn flow whose check does not pass, while it is not yet building. W395 once a slice is at
building or later: by then its findings must each be fixed or covered by an override with an end date, and a slice
with nothing drawn is not fully checked, never a pass (R0). E398 for an override past its end date, wherever it sits:
it covers nothing any more, so the finding it named blocks the slice again, and a red line says so instead of a
quiet uncovering. Every slice comes from `slices.read_slices` through the catalog, and every override through
`readers.flow_overrides`: one reader each.
"""
from planner import flowcheck
from planner.model import Finding


def findings(catalog, today, max_states):
    out = []
    for found in catalog.slices:
        drawn = any(catalog.flows[f].has_diagram for f in found.flows if f in catalog.flows)
        building = found.at_least("building")
        if not found.flows or not (drawn or building):
            continue
        result = flowcheck.check_catalog(catalog, found.key, today, max_states)
        if result.status == "passes":
            continue
        open_ = [f for f in result.findings if f.severity == "error"]
        names = sorted({flowcheck.TITLES.get(f.code, f.code).lower() for f in open_})
        what = f"{len(open_)} open finding{'' if len(open_) == 1 else 's'} ({', '.join(names)})"
        target = found.id or found.name
        if building:
            out.append(Finding(found.path, found.lines.get("Status", found.line), "W395",
                               f"{found.label} is {found.status}, but its flow check {_verb(result.status)}: {what}, "
                               "and no override with an end date covers them.",
                               f"Run planner check-slice {target} for the traces and owners; fix each, or add an override "
                               "with an end date under the slice page's ## Overrides."))
        else:
            said = f"{found.label}: its flow check {_verb(result.status)}" if found.id else f"{found.name} {result.status}"
            out.append(Finding(found.path, found.line, "W391", f"{said}: {what}.",
                               f"Run planner check-slice \"{target}\" for the traces and owners, and fix or override each."))
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
