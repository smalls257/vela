#!/usr/bin/env python3
"""Write a synthetic vault at the size of a large initiative, to see how the explorer copes with scale.

    python3 tests/fixtures/explorer/make_stress_vault.py <dir>

SYNTHETIC: 24 apps in 5 domains, 60 contracts, 250 unknowns, 50 epics, 20 capabilities, 12 of them with functional
requirements (each with acceptance criteria) and allocation rows, 3 releases on 04b-releases.md, and 14 flows (more than the explorer's flow picker lists flat), with
links out of the vault on every app, epic, party and party contract (example.com hosts). The content is filler; only
the shape matters. Links draw no random numbers, so adding them moved nothing else. It is not a vela-check-clean vault and is never meant to be one.
Seeded, so every run writes the same files.
"""
import pathlib
import random
import sys

SEED = 7
R = random.Random(SEED)
APPS = ["Booking", "Pricing", "Inventory", "Payments", "Ledger", "Notifications", "Identity", "Website", "Mobile app",
        "Call center", "Kiosks", "Reporting", "Loyalty", "Partner gateway", "Search", "Refunds", "Vouchers", "Fraud check",
        "Schedule", "Agent portal", "Data warehouse", "Consent", "Messaging hub", "Audit log"]
CHANGES = ["new", "new", "changed", "changed", "changed", "changed", "unchanged", "changed", "changed", "changed",
           "changed", "integrated", "changed", "new", "unchanged", "new", "changed", "new", "unchanged", "changed",
           "integrated", "new", "changed", "unchanged"]
DOMAINS = {"Channels": ["Website", "Mobile app", "Call center", "Kiosks", "Agent portal"],
           "Booking core": ["Booking", "Pricing", "Inventory", "Schedule", "Search"],
           "Payments": ["Payments", "Ledger", "Refunds", "Vouchers", "Fraud check"],
           "Platform": ["Identity", "Notifications", "Consent", "Messaging hub", "Audit log"],
           "Data and partners": ["Reporting", "Loyalty", "Partner gateway", "Data warehouse"]}
DOMAIN_OF = {app: d for d, apps in DOMAINS.items() for app in apps}
STAGES = ["baseline", "target", "boundaries", "contracts", "handoff", "epics"]
STATES = ["decided", "decided", "fact", "assumption", "assumption", "inkling"]
OWNERS = ["@sol-lead", "@booking-senior", "@pay-lead", "@platform-lead", "@qa-lead", "@data-lead", "@legal", "@ops-lead",
          "@product-lead", "@partner-manager"]
PARTIES = ["Cardco", "Mapline", "Taxbase"]
WORDS = ["hold", "seat", "fare", "refund", "event", "ledger", "customer", "voucher", "receipt", "schedule", "capacity",
         "points", "token", "audit", "report", "partner", "search", "price", "basket", "notice"]


def slug(name):
    return name.lower().replace(" ", "-")


def phrase(n=6):
    return " ".join(R.choice(WORDS) for _ in range(n))


def write_flows(out, apps, contracts, caps):
    """14 flows. The first 8 draw from R exactly as the older 8-flow vault did, so nothing after them moved; the other
    6 use their own generator. Capabilities are handed out by position, with no random draw, so the picker's groups
    never shuffle between runs: flows 1-8 name one capability in `capabilities:`, 12 names two, 9 and 10 only cite one
    in a step ("Uses [[CAP-...]]", which the picker marks as a guess), and 11, 13 and 14 name none, which leaves them
    to the domain of the apps they cross."""
    late = random.Random(11)
    cap_ids = [c for c, _ in caps[:12]]
    declared = {n: [cap_ids[(n * 5) % 4]] for n in range(1, 9)}
    declared[12] = [cap_ids[6], cap_ids[7]]
    cited = {9: cap_ids[2], 10: cap_ids[5]}
    for n in range(1, 15):
        rng = R if n <= 8 else late
        words = lambda k: " ".join(rng.choice(WORDS) for _ in range(k))  # noqa: E731
        chosen = rng.sample([c for c in contracts if not isinstance(c[2], str)], 4)
        steps = []
        for s, c in enumerate(chosen, start=1):
            provider = apps[c[2]]
            line = f"{s}. {provider[1]} answers over [[{provider[2]}#{c[0]} {c[1]}|{c[1]}]] with the {words(3)}."
            if s == 1 and n in cited:
                cid = cited[n]
                line += f" Uses [[{cid}-{slug(dict(caps)[cid])}|{dict(caps)[cid]}]]."
            steps.append(line)
        cap_line = f"capabilities: [{', '.join(declared[n])}]\n" if n in declared else ""
        (out / "06-runtime" / "flows" / f"FLO-{n:03d}.md").write_text(
            f"---\nid: FLO-{n:03d}\ntype: flow\ntitle: A customer {words(2)}\nstate: assumption\n{cap_line}---\n\n# A customer {words(2)}\n\n"
            f"The customer {words(6)}.\n\n## Steps\n\n" + "\n".join(steps) + "\n", encoding="utf-8")


def main(out):
    out = pathlib.Path(out)
    R.seed(SEED)  # R is module-wide: without this a second call in one process continues the sequence and writes a different vault
    for sub in ("05-building-blocks", "13-epics", "capabilities", "06-runtime/flows"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    (out / ".vela.yaml").write_text("initiative: INI-099\ntitle: Stress test (synthetic)\nstale_after_days: 365\n"
                                       'link_templates: {Jira: "https://jira.example.com/browse/{key}"}\n', encoding="utf-8")
    apps = [(f"APP-{slug(a)}", a, f"{slug(a)}-building-blocks", c) for a, c in zip(APPS, CHANGES)]
    contracts = []  # (id, title, provider index or party name, consumer indexes, state)
    for n in range(1, 61):
        provider = R.randrange(len(apps)) if n > 3 else PARTIES[n - 1]
        consumers = R.sample([i for i in range(len(apps)) if i != provider], R.choice([1, 1, 1, 2, 3]))
        contracts.append((f"CON-{n:03d}", f"{R.choice(WORDS).title()} {R.choice(WORDS)}", provider, consumers, R.choice(STATES)))
    caps = [(f"CAP-{n:03d}", f"{R.choice(WORDS).title()} the {R.choice(WORDS)}") for n in range(101, 121)]
    frs = {c: [f"{c}.FR{i}" for i in range(1, R.choice([1, 2, 3]) + 1)] for c, _ in caps[:12]}
    ac_count = {fr: R.choice([2, 3, 4]) for ids in frs.values() for fr in ids}
    epics = []
    for n in range(1, 51):
        app_ix = R.sample(range(len(apps)), R.choice([1, 2]))
        delivers = R.sample([c for c, _ in caps], 1) + R.sample([c[0] for c in contracts], R.choice([0, 1]))
        epics.append((f"EPC-{n:03d}", phrase(4).capitalize(), [apps[i][0] for i in app_ix], delivers,
                      R.sample([c[0] for c in contracts], R.choice([0, 1, 2]))))

    # the outside parties live on a context page
    (out / "03-context-and-scope.md").write_text(
        "---\nid: context-and-scope\ntype: initiative-section\ntitle: Context and scope\nstate: assumption\n---\n\n# Context and scope\n\n"
        "Synthetic context.\n\n## Outside parties\n\n" + "".join(f"### PTY-0{i + 1} {p}\n\n{p} is an outside party.\n\n"
                                                         f"- **Links:** [API spec](https://developer.{slug(p)}.example.com/openapi.yaml), "
                                                         f"[Docs](https://developer.{slug(p)}.example.com/docs)\n\n" for i, p in enumerate(PARTIES)),
        encoding="utf-8")

    for i, (app_id, name, page, change) in enumerate(apps):
        lines = ["---", f"id: {app_id}", "type: app-building-blocks", f"title: {name}", f"state: {R.choice(STATES[:4])}",
                 f"change: {change}", f"domain: {DOMAIN_OF[name]}",
                 f'links: {{Confluence: "https://confluence.example.com/display/STRESS/{name.replace(" ", "+")}", '
                 f'GitHub: "https://github.example.com/stress/{slug(name)}"}}']
        if change in ("new", "changed"):
            lines.append(f"stage: {R.choice(STAGES)}")
        lines += [f"owner: \"{R.choice(OWNERS)}\"", "sources: [SRC-01]", "---", "", f"# {name}", "",
                  f"{name} handles the {phrase(3)} for every channel. It keeps the {phrase(2)} and answers {phrase(3)}.", ""]
        mine = [c for c in contracts if c[2] == i or (isinstance(c[2], str) and i == 0)]
        if mine:
            lines += ["## Contracts this app provides", ""]
        for cid, title, provider, consumers, state in mine:
            lines += [f"### {cid} {title}", ""]
            if isinstance(provider, str):
                pty = PARTIES.index(provider) + 1
                lines.append(f"- **Provider:** [[03-context-and-scope#PTY-0{pty} {provider}|{provider}]]")
                lines.append(f"- **Links:** [API spec](https://developer.{slug(provider)}.example.com/{cid.lower()}.yaml)")
            lines += [f"- **Crosses the boundary:** {phrase(8)}.",
                      "- **Consumers:** " + ", ".join(f"[[{apps[k][2]}|{apps[k][1]}]]" for k in consumers),
                      "- **Change policy:** versioned.", f"- **Change:** {R.choice(['new', 'changed', 'new consumers'])}",
                      f"- **State:** {state}", ""]
        rows = [(fr, c) for c, ids in frs.items() for fr in ids if R.random() < 0.09]
        if rows:
            lines += ["## Requirements allocated", "", "| Requirement | Share | Through | State |", "|---|---|---|---|"]
            for fr, cap in rows:
                through = R.choice([c[0] for c in contracts])
                lines.append(f"| [[{cap}#{fr} Requirement\\|{fr}]] | {phrase(4)} | {through} | {R.choice(['assumption', 'decided', 'inkling'])} |")
            lines.append("")
        (out / "05-building-blocks" / f"{page}.md").write_text("\n".join(lines), encoding="utf-8")

    for cid, title in caps:
        body = [f"---\nid: {cid}\ntype: capability\ntitle: {title}\nchange: {R.choice(['new', 'extend', 'replace'])}\n"
                f"state: assumption\n---\n\n# {cid} {title}\n\nLets a customer {phrase(5)}.\n"]
        if cid in frs:
            body.append("\n## Functional requirements\n")
            for fr in frs[cid]:
                body.append(f"\n### {fr} Requirement\n\nThe customer can {phrase(5)}.\n\n- **State:** {R.choice(['assumption', 'decided'])}\n"
                            + "".join(f"- The customer sees the {phrase(3)}.\n" for _ in range(ac_count[fr])))
        (out / "capabilities" / f"{cid}-{slug(title)}.md").write_text("".join(body), encoding="utf-8")

    for eid, title, eapps, delivers, consumes in epics:
        (out / "13-epics" / f"{eid}.md").write_text(
            f"---\nid: {eid}\ntype: epic\ntitle: {title}\nstate: {R.choice(['draft', 'assumption', 'decided'])}\n"
            f"owner: \"{R.choice(OWNERS)}\"\napps: [{', '.join(eapps)}]\ndelivers: [{', '.join(delivers)}]\n"
            f"consumes: [{', '.join(consumes)}]\nlinks: {{Jira: STRESS-{int(eid[4:])}}}\n---\n\n# {eid} {title}\n\nThis epic builds the {phrase(5)}.\n", encoding="utf-8")

    unk = ["---", "id: unknowns-and-risks", "type: index", "title: Unknowns and risks", "---", "", "# Unknowns and risks", "", "## Unknowns", ""]
    for n in range(1, 251):
        state = "open" if R.random() < 0.6 else "resolved"
        due = f"2026-{R.choice([10, 10, 10, 11, 11, 12])}-{R.randrange(1, 29):02d}"
        roll = R.random()
        if roll < 0.55:
            blocks = "nothing yet, since no plan item exists to block"
        elif roll < 0.75:
            k = R.randrange(len(apps))
            blocks = f"[[{apps[k][2]}|{apps[k][1]}]]"
        elif roll < 0.9:
            c = R.choice([c for c in contracts if not isinstance(c[2], str)])
            blocks = f"[[{apps[c[2]][2]}#{c[0]} {c[1]}|{c[0]}]]"
        else:
            blocks = f"[[{R.choice(epics)[0]}]]"
        unk += [f"### UNK-{n:03d} {phrase(4).capitalize()}", "", f"- **Question:** Will the {phrase(5)}?",
                f"- **Owner:** {R.choice(OWNERS)}", f"- **Opened:** 2026-09-{R.randrange(1, 29):02d}", f"- **State:** {state}",
                f"- **Blocks:** {blocks}"]
        unk += [f"- **Ask by:** {due}"] if state == "open" else ["- **Outcome:** answered.", "- **Resolved in:** a session"]
        unk.append("")
    (out / "11-unknowns-and-risks.md").write_text("\n".join(unk), encoding="utf-8")

    write_flows(out, apps, contracts, caps)
    # three releases, each delivering some requirements; a few are split across two releases by acceptance criteria
    all_frs = [fr for ids in frs.values() for fr in ids]
    R.shuffle(all_frs)
    thirds = [all_frs[:4], all_frs[4:12], all_frs[12:]]
    rel = ["---", "id: releases", "type: initiative-section", "title: Releases", "state: assumption", "owner: \"@sol-lead\"",
           "authored: mixed", "---", "", "# Releases", "", "Synthetic releases, filler for scale.", ""]
    for n, (name, target) in enumerate([("Release one: first channel", "2027-01-15"), ("Release two: every channel", "2027-04-01"),
                                        ("Release three: the rest", "2027-07-01")]):
        rel += [f"## {name}", "", f"- **Target:** {target}", f"- **State:** {['assumption', 'assumption', 'inkling'][n]}", "",
                "| Delivers | Criteria | Note |", "|---|---|---|"]
        for fr in thirds[n]:
            cap = fr.split(".")[0]
            split = n < 2 and R.random() < 0.25 and ac_count[fr] > 2
            rel.append(f"| [[{cap}-{slug(dict(caps)[cap])}#{fr} Requirement\\|{fr}]] | {'AC1, AC2' if split else 'all'} | {'the rest next release' if split else ''} |")
            if split:
                thirds[n + 1].append(fr)
        rel.append("")
    (out / "04b-releases.md").write_text("\n".join(rel), encoding="utf-8")
    print(f"make_stress_vault.py: wrote a SYNTHETIC vault at {out}: {len(apps)} apps in {len(DOMAINS)} domains, "
          f"{len(contracts)} contracts, {len(all_frs)} requirements, 3 releases")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
