"""`vela releases brief` and `vela releases tracer-candidates`: what a releases session starts from, and the tracer
ranking it offers (CLI/skill overhaul, Task 21f). The rules and their reasons are in `vela/releasebrief.py`.

The Violation this shape prevents is the Leaky Narrative at the skill's seam: the skill used to read the pages and
count by hand, then pasted what it counted with (IDs, codes) to the lead. Here each line is built twice, once with
IDs for the default mode and once in names for `--for-lead`, and the lead's line still goes through say's leak check.

- `brief`: the releases (target, state, slices, what each delivers), the slices in After order with the tracer
  marked, the requirements (how many, which are not allocated, which no release delivers), the first thin path a
  boundary session recorded, and each missing prerequisite with the skill to offer. A missing prerequisite is a fact
  the session acts on, not a refusal, so the exit stays 0.
- `tracer-candidates`: every drawn flow, most apps crossed first, then most new contracts; a tie at the top is
  reported as the lead's call, broken by what the first release's audience sees first.

Exit 0 done; 2 the vault would not load. Both read only: no git runs, so a reader copy answers the same.
"""
import pathlib

from vela import releasebrief, say
from vela.commands import emit


def register(sub):
    group = sub.add_parser("releases", help="what a releases session starts from, and the tracer candidates")
    verbs = group.add_subparsers(dest="releases_command", metavar="{brief,tracer-candidates}")
    verbs.required = True
    brief = verbs.add_parser("brief", help="releases, slices in order, requirements, allocation, the recorded first "
                                           "thin path, and what is missing")
    candidates = verbs.add_parser("tracer-candidates", help="flows ranked by apps crossed, then new contracts crossed")
    for parser, func in ((brief, cmd_brief), (candidates, cmd_candidates)):
        parser.add_argument("--vault", default=".", help="vault root or reader copy (default: current directory)")
        say.add_output_flags(parser)
        parser.set_defaults(func=func)


def load(args):
    from vela import cli  # cli builds the parser, so it is loaded by the time a command runs
    root = pathlib.Path(args.vault)
    if not root.is_dir():
        raise cli.ToolError(f"{root} is not a folder; pass --vault the vault root.")
    vault = cli.load_vault(root)
    return vault, say.Resolver(vault)


class Words:
    """One subject said two ways: with its ID for files and CI, by name alone for the lead."""

    def __init__(self, vault, resolver):
        self.vault, self.plain = vault, resolver.plain

    def tagged(self, ident):
        name = self.vault.name_of(ident)
        return ident if name == ident else f"{ident} {name}"

    def named(self, ident):
        return self.plain(self.vault.name_of(ident))

    def line(self, text, plain):
        return say.Line(text, self.plain(plain))

    def both(self, ids):
        return ", ".join(self.tagged(i) for i in ids) or "none", ", ".join(self.named(i) for i in ids) or "none"


def count(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def cmd_brief(args, out):
    vault, resolver = load(args)
    found = releasebrief.brief(vault)
    result = say.Result("releases brief", data=brief_data(found))
    result.lines = brief_lines(found, Words(vault, resolver))
    return emit(result, args, out, resolver)


def brief_data(b):
    return {
        "releases": [{"name": r.name, "target": r.target, "state": r.state, "slices": list(r.slices),
                      "delivers": [{"requirement": row.requirement, "criteria": row.raw_criteria or "all"}
                                   for row in r.rows]} for r in b.releases],
        "slices": [{"id": s.id, "name": s.name, "order": s.order, "after": list(s.after), "flows": list(s.flows),
                    "status": s.status, "tracer": b.tracer is not None and s.key == b.tracer.key} for s in b.slices],
        "requirements": {"count": len(b.requirements), "due": [r.id for r in b.due],
                         "unallocated": [r.id for r in b.unallocated], "undated": [r.id for r in b.undated]},
        "first_path": [{"flow": fp.flow, "words": fp.words} for fp in b.first_path],
        "flows": b.flow_count,
        "missing": [{"key": m.key, "says": m.says, "offer": m.offer} for m in b.missing],
    }


def brief_lines(b, w):
    lines = [w.line(f"Releases: {len(b.releases)}.", f"Releases: {len(b.releases)}.")]
    for r in b.releases:
        when = f"target {r.target or 'not given'}, {r.state or 'no state'}"
        delivers = [row.requirement + ("" if row.raw_criteria.lower() in ("", "all") else f" ({row.raw_criteria})")
                    for row in r.rows if row.requirement]
        said = [w.named(row.requirement) + ("" if row.raw_criteria.lower() in ("", "all") else
                                            f" (only checks {row.raw_criteria})") for row in r.rows if row.requirement]
        text_slices, plain_slices = w.both(r.slices)
        lines.append(w.line(f"- {r.name}: {when}; slices {text_slices}; delivers {', '.join(delivers) or 'nothing yet'}",
                            f"- {r.name}: {when}; slices on by then: {plain_slices}; delivers "
                            f"{', '.join(said) or 'nothing yet'}"))
    lines.append(w.line(f"Slices, in order: {len(b.slices)}.", f"Slices, in the order they come: {len(b.slices)}."))
    for s in b.slices:
        tracer = " (the tracer)" if b.tracer is not None and s.key == b.tracer.key else ""
        status = s.status or "not planned yet"
        text_after, plain_after = w.both(s.after)
        text_flows, plain_flows = w.both(s.flows)
        after = f"comes after {plain_after}; " if s.after else ""
        lines.append(w.line(f"{s.order + 1}. {s.label}{tracer}: {status}; after {text_after}; flows {text_flows}",
                            f"{s.order + 1}. {s.name}{tracer}: {status}; {after}flows {plain_flows}"))
    lines += requirement_lines(b, w)
    if b.first_path:
        for fp in b.first_path:
            lines.append(w.line(f"First thin path recorded on {w.tagged(fp.flow)}: {fp.words}",
                                f"The first thin path the boundary session recorded, on the flow {w.named(fp.flow)}: {fp.words}"))
    else:
        lines.append(w.line("First thin path recorded: none.", "No first thin path was recorded; ask the lead for one."))
    for m in b.missing:
        lines.append(w.line(f"Missing {m.key}: {m.says} Offer {m.offer}.", f"{m.says} Offer {m.offer}."))
    return lines


def requirement_lines(b, w):
    text_un, plain_un = w.both([r.id for r in b.unallocated])
    text_nd, plain_nd = w.both([r.id for r in b.undated])
    return [
        w.line(f"Requirements: {len(b.requirements)}, {len(b.due)} at assumption or later.",
               f"Requirements: {len(b.requirements)}, {len(b.due)} of them agreed far enough to place."),
        w.line(f"Not allocated: {text_un}.", f"Not allocated to an app yet: {plain_un}."),
        w.line(f"On no release: {text_nd}.", f"On no release yet: {plain_nd}."),
    ]


def cmd_candidates(args, out):
    vault, resolver = load(args)
    ranked = releasebrief.candidates(vault)
    tie = releasebrief.tied(ranked)
    result = say.Result("releases tracer-candidates", data={
        "candidates": [{"flow": c.flow, "name": vault.name_of(c.flow), "apps": list(c.apps),
                        "new_contracts": list(c.new_contracts), "recorded_first_path": c.recorded_first_path,
                        "in_slices": list(c.in_slices), "countable": c.countable} for c in ranked],
        "recommended": ranked[0].flow if ranked and ranked[0].countable and not tie else "", "tied": tie})
    result.lines = candidate_lines(ranked, tie, Words(vault, resolver))
    return emit(result, args, out, resolver)


def candidate_lines(ranked, tie, w):
    if not ranked:
        return [w.line("No flow is drawn yet.", "No flow is drawn yet, so take the tracer in plain words; a boundary "
                                                "session can draw it.")]
    lines = [w.line("Flows, most apps crossed first, then most new contracts:",
                    "Flows, the one crossing the most apps first, then the most new contracts:")]
    for n, c in enumerate(ranked, 1):
        recorded = " (the first thin path the boundary session recorded)" if c.recorded_first_path else ""
        if not c.countable:
            lines.append(w.line(f"{n}. {w.tagged(c.flow)}{recorded}: not counted, no step names a sender and receiver",
                                f"{n}. {w.named(c.flow)}{recorded}: not counted, because no step says who sends to "
                                "whom; a boundary session can redraw it"))
            continue
        text_apps, plain_apps = w.both(c.apps)
        text_new, plain_new = w.both(c.new_contracts)
        apps, new = count(len(c.apps), "app"), count(len(c.new_contracts), "new contract")
        lines.append(w.line(f"{n}. {w.tagged(c.flow)}{recorded}: {apps} ({text_apps}); {new} ({text_new})",
                            f"{n}. {w.named(c.flow)}{recorded}: crosses {apps} ({plain_apps}) and {new} ({plain_new})"))
    if tie:
        text_tie, plain_tie = w.both(tie)
        lines.append(w.line(f"Tied at the top: {text_tie}. The lead breaks it by what the first release's audience "
                            "sees first.",
                            f"{plain_tie} tie at the top; break it by what the first release's audience sees first."))
    elif not ranked[0].countable:
        lines.append(w.line("Nothing to recommend: no flow could be counted.",
                            "Nothing to recommend yet, because no flow says who sends to whom."))
    else:
        lines.append(w.line(f"Recommended: {w.tagged(ranked[0].flow)}.",
                            f"Recommended: {w.named(ranked[0].flow)}, because it proves the most of the system."))
    return lines
