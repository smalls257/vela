"""What a vault records of the things the explorer draws, as counts. Pure.

The explorer's domains, flow directions, releases, requirements, allocation rows and asks were fed only by demo data
until the skills learned to ask for them. These counts are the sensor for that: `vela capture` prints them, and
the session simulator reads them from the final vault, so a skill that stops asking shows up as a number, not as an
empty box someone finds on a live call.
"""
from vela import allocation, flows, links, releases


def linked(vault, pages):
    """How many of the pages carry at least one readable link. A link that failed to read counts for nothing."""
    return sum(1 for p in pages if links.of_page(p, vault.config)[0])


def counts(vault):
    """{name: number} plus the dates and asks found, read from the vault as it stands."""
    apps = vault.apps
    crossing = [s for s in flows.steps(vault) if s.contracts]
    unknowns = vault.unknowns
    found = releases.releases(vault)
    return {
        "apps": len(apps),
        "apps_with_domain": sum(1 for a in apps if isinstance(a.meta.get("domain"), str) and a.meta["domain"].strip()),
        "flow_steps_crossing": len(crossing),
        "flow_steps_with_sender": sum(1 for s in crossing if s.pair),
        "releases": len(found),
        "release_targets": [r.target for r in found if r.target],
        "requirements": len(allocation.requirements(vault)),
        "allocation_rows": len(allocation.rows(vault)),
        "apps_with_link": linked(vault, apps),
        "epics": len(vault.of_type("epic")),
        "epics_with_link": linked(vault, vault.of_type("epic")),
        "unknowns": len(unknowns),
        "unknowns_with_ask": sum(1 for u in unknowns if u.fact("Ask")),
        "asks": [u.fact("Ask") for u in unknowns if u.fact("Ask")],
    }


def verdict(found, release_date="", ask_phrase=""):
    """[(check, passed, detail)]: every app has a domain; at least 80% of crossing steps name a sender; the persona's
    dated release is present; an Ask appears where the persona planted one. The last two run only when asked for."""
    out = [("every app has a domain", found["apps"] > 0 and found["apps_with_domain"] == found["apps"],
            f"{found['apps_with_domain']} of {found['apps']}"),
           ("at least 80% of flow steps between apps say who sends",
            found["flow_steps_crossing"] > 0 and found["flow_steps_with_sender"] * 5 >= found["flow_steps_crossing"] * 4,
            f"{found['flow_steps_with_sender']} of {found['flow_steps_crossing']} do")]
    if release_date:
        out.append((f"a release is dated {release_date}", release_date in found["release_targets"],
                    ", ".join(found["release_targets"]) or "no release"))
    if ask_phrase:
        hit = [a for a in found["asks"] if ask_phrase.lower() in a.lower()]
        out.append((f"an Ask names '{ask_phrase}'", bool(hit), f"{found['unknowns_with_ask']} asks written"))
    return out
