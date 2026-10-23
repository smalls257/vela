"""Which capability depends on which, read from the flows alone.

The Violation this exists to prevent is a Paper Tiger: a dependency picture that is green on the data it was handed
and wrong about the plan. Dependencies drawn from apps or from requirement allocation say "A leans on B" when no
journey anyone wrote needs B in place for A. A flow is a journey someone wrote down, so it is the one honest source.
It is also one pure function over the explorer's flow records, so the rule lives in one place (the Distributed
Monolith risk is a second copy in the page's script) and a test can pin it without a vault.

The rule, as CONVENTIONS states it:

- A flow's primary capability (the first in its `capabilities:` list) depends on every other capability the same flow
  lists. The reason is the flow, and the contracts are the ones that flow's steps cross.
- A step that links another flow makes the primary depend on that flow's primary capability, through the flow that
  repeats it. The contracts are the ones the repeated flow's steps cross, with the repeating step's own.
- Nothing else makes a dependency. A flow whose capabilities are only guessed from its steps, or that lists none,
  makes none, and is counted in `noCapabilities` so the page can say how many flows the picture leaves out.
"""


def crossed(flow):
    """The contracts a flow's steps cross, in first-seen order."""
    seen = []
    for step in flow.get("steps", []):
        for cid in [*step.get("contracts", []), *(m.get("contract", "") for m in step.get("messages", []))]:
            if cid and cid not in seen:
                seen.append(cid)
    return seen


def recorded(flow):
    """The capabilities the flow's own page lists, primary first; none when they were only guessed from its steps."""
    return list(flow.get("capabilities", [])) if flow.get("capabilitiesFrom") == "frontmatter" else []


def reasons(flows):
    """[(from, to, flow key, repeated flow key or "", contracts)] for every reason one capability needs another."""
    by_key = {f["key"]: f for f in flows}
    out = []
    for flow in flows:
        caps = recorded(flow)
        if not caps:
            continue
        primary, own = caps[0], crossed(flow)
        out += [(primary, other, flow["key"], "", own) for other in caps[1:]]
        for step in flow.get("steps", []):
            target = by_key.get(step.get("ref") or "")
            theirs = recorded(target) if target else []
            if theirs and theirs[0] != primary:
                through = [*step.get("contracts", []), *crossed(target)]
                out.append((primary, theirs[0], flow["key"], target["key"], list(dict.fromkeys(through))))
    return out


def derive(flows):
    """{"edges": [...], "noCapabilities": [flow keys]} from the explorer's flow records.

    Each edge says `from` depends on `to`, with `flows` (one entry per flow: whether it lists the capability, which
    flows it repeats, and the contracts it crosses), the contracts across all of them, `nFlows`, `nContracts`, and
    `both` when the reverse edge exists too. Edges and flows come out in sorted order, so a rebuild never reshuffles."""
    edges = {}
    for a, b, flow, repeated, contracts in reasons(flows):
        edge = edges.setdefault((a, b), {"from": a, "to": b, "flows": {}})
        entry = edge["flows"].setdefault(flow, {"flow": flow, "lists": False, "repeats": [], "contracts": []})
        if repeated:
            entry["repeats"] = sorted({*entry["repeats"], repeated})
        else:
            entry["lists"] = True
        entry["contracts"] = list(dict.fromkeys([*entry["contracts"], *contracts]))
    out = []
    for (a, b), edge in sorted(edges.items()):
        listed = [edge["flows"][k] for k in sorted(edge["flows"])]
        contracts = sorted({c for f in listed for c in f["contracts"]})
        out.append({"from": a, "to": b, "flows": listed, "contracts": contracts, "nFlows": len(listed),
                    "nContracts": len(contracts), "both": (b, a) in edges})
    return {"edges": out, "noCapabilities": sorted(f["key"] for f in flows if not recorded(f))}
