"""`vela epics frontier` and `vela epics lint [--fix-shape]` (CLI/skill overhaul, Task 21e).

- `vela epics frontier --team @x [--json|--for-lead]`: that team's traceability gaps (T1, T2, T4, T6), the counts the
  skill paces by (epics, criteria, gaps by kind), and whether the team's first epic is on the tracer. Exit 0 no gaps;
  1 gaps (or no such team, with the teams there are); 2 the tool failed.
- `vela epics lint [EPC-n ...] [--json|--for-lead]`: the boundary test on every criterion (a contract or flow on its
  Trace line; no component, technology or generic store word; no ID in the sentence) and more than about seven
  criteria on one epic. Every epic when none is named. Exit 0 clean; 1 findings; 2 the tool failed.
- `vela epics lint --fix-shape EPC-n`: rewrite a first-shape epic to the template, every AC number kept (other pages
  cite `EPC-n.ACn`). Exit 0 rewritten or already in shape; 1 refused (plain reason); 2 the tool failed, nothing written.

The Violation this module's shape prevents is a Leaky Narrative: the pure modules (`epicsfrontier`, `epicslint`) return
gaps and findings with their IDs, and only here are they said, with codes and IDs by default and by name under
`--for-lead`, through `say`'s formatter, which refuses a line that still holds an ID. Why each rule holds is in the
pure modules' docstrings, with the rule.

`--fix-shape` writes one page through `edge/atomic.py` and runs no git anywhere; in a reader copy it says the change
reaches the owner through a proposal.
"""
import pathlib

from vela import epicsfrontier, epicslint, roles, say
from vela.commands import emit
from vela.edge import atomic


def register(sub):
    parser = sub.add_parser("epics", help="one team's epics frontier, and the boundary test on epic criteria")
    steps = parser.add_subparsers(dest="epics_step", metavar="STEP", required=True)

    frontier = steps.add_parser("frontier", help="a team's traceability gaps, counts for pacing, and whether its "
                                                 "first epic is on the tracer")
    frontier.add_argument("--team", required=True, help="the owning team's handle, like @agent-lead")
    frontier.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(frontier)
    frontier.set_defaults(func=cmd_frontier)

    lint = steps.add_parser("lint", help="the boundary test on each criterion, and more than about seven on one epic; "
                                         "--fix-shape rewrites a first-shape epic to the template, keeping its AC "
                                         "numbers")
    lint.add_argument("epics", nargs="*", metavar="EPC-n", help="the epics to test (default: every epic)")
    lint.add_argument("--fix-shape", metavar="EPC-n", default="",
                      help="rewrite this first-shape epic to the template; each criterion keeps its number as AC<n>")
    lint.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(lint)
    lint.set_defaults(func=cmd_lint)


def load(root):
    from vela import cli  # cli is the shell that reads the disk; loaded by the time a command runs
    vault = cli.load_vault(root)
    return vault, say.Resolver(vault)


# ------------------------------------------------------------------------------------------------ frontier

def cmd_frontier(args, out):
    vault, resolver = load(pathlib.Path(args.vault))
    try:
        found = epicsfrontier.frontier(vault, args.team)
    except epicsfrontier.UnknownTeam as exc:
        known = ", ".join(exc.known) or "none"
        result = say.Result("epics frontier", exit=say.REFUSED, data={"teams": list(exc.known)})
        result.refusals.append(say.Refusal("team", f"Nothing in the vault is owned by {exc.team}. The teams here are "
                                                   f"{known}.", "Run again with --team set to one of them."))
        return emit(result, args, out, resolver)
    result = say.Result("epics frontier", exit=say.REFUSED if found.gaps else say.DONE, data=frontier_json(found))
    result.lines = (summary_lines(found) + [gap_line(g, resolver) for g in found.gaps] + unowned_lines(found, resolver)
                    + [tracer_line(found, resolver)])
    return emit(result, args, out, resolver)


def unowned_lines(found, resolver):
    """Gaps no team's share holds, said on every team's frontier so narrowing to one team never hides them."""
    if not found.unowned:
        return []
    count = len(found.unowned)
    head = say.Line(f"{count} more gap(s) belong to no team yet (no app carries them):",
                    f"{count} more {'gap belongs' if count == 1 else 'gaps belong'} to no team yet, because no app "
                    f"carries {'it' if count == 1 else 'them'}:")
    return [head] + [say.Line(f"  {gap_line(g, resolver).text}", f"- {resolver.plain(g.message)}")
                     for g in found.unowned]


def frontier_json(found):
    t = found.tracer
    return {"team": found.team, "apps": [{"id": i, "title": n} for i, n in found.apps],
            "epics": [{"id": i, "title": n} for i, n in found.epics],
            "counts": {"epics": len(found.epics), "criteria": found.criteria,
                       "gaps": {rule: found.count(rule) for rule in epicsfrontier.FRONTIER_RULES}},
            "gaps": [{"rule": g.rule, "subject": g.subject, "label": g.label, "path": g.page.path,
                      "message": g.message, "fix": g.fix} for g in found.gaps],
            "unowned": [{"rule": g.rule, "subject": g.subject, "label": g.label, "path": g.page.path,
                         "message": g.message, "fix": g.fix} for g in found.unowned],
            "tracer": {"state": t.state, "epic": t.epic, "epic_title": t.epic_title, "epic_flows": list(t.epic_flows),
                       "tracer": t.tracer_name, "tracer_flows": list(t.tracer_flows),
                       "on_tracer": list(t.on_tracer)}}


def summary_lines(found):
    names = [n for _, n in found.apps]
    apps = ", ".join(names) or "no app pages"
    said_apps = (", ".join(names[:-1]) + " and " + names[-1]) if len(names) > 1 else apps
    counted = [f"{found.count(r)} {epicsfrontier.RULE_WORDS[r]}" for r in epicsfrontier.FRONTIER_RULES if found.count(r)]
    epics = f"{len(found.epics)} epic{'' if len(found.epics) == 1 else 's'} with {found.criteria} criteria"
    said_epics = f"{epics} so far" if found.epics else "no epics yet"
    gaps = "; ".join(counted) if counted else "no gaps"
    return [say.Line(f"{found.team}: {apps}. {epics}. Gaps: {gaps}.",
                     f"{found.team} owns {said_apps}, with {said_epics}. Still to cover: "
                     f"{gaps if counted else 'nothing'}.")]


def gap_line(gap, resolver):
    return say.Line(f"{gap.page.path}: {gap.rule} {gap.subject}: {gap.message}", resolver.plain(gap.message))


def tracer_line(found, resolver):
    t = found.tracer
    flows = ", ".join(t.tracer_flows)
    flow_names = ", ".join(resolver.name(f) for f in t.tracer_flows)
    if t.state == "no-epic":
        where = f" The tracer runs {flows}." if flows else ""
        return say.Line(f"No epic for {found.team} yet, so no first epic to place on the tracer.{where}",
                        "This team has no epic yet, so there's no first epic to check against the first thin path.")
    if t.state == "no-tracer":
        return say.Line(f"The vault names no tracer flows yet, so whether {t.epic} is on the tracer can't be said.",
                        f"The first thin path isn't named yet, so I can't say whether {t.epic_title} is on it.")
    if t.state == "on":
        names = ", ".join(resolver.name(f) for f in t.on_tracer)
        return say.Line(f"First epic {t.epic} ({t.epic_title}) is on the tracer ({t.tracer_name}: {flows}).",
                        f"{t.epic_title}, this team's first epic, is on the first thin path: it covers {names}.")
    return say.Line(f"First epic {t.epic} ({t.epic_title}) is not on the tracer ({t.tracer_name}: {flows}); "
                    f"its flows are {', '.join(t.epic_flows) or 'none'}. Say what comes first instead; it is not a fault.",
                    f"{t.epic_title}, this team's first epic, isn't on the first thin path ({flow_names}). That's "
                    "fine, but let's say which epic comes first instead.")


# ------------------------------------------------------------------------------------------------ lint

LINT_SAYS = {
    "no-boundary": ("its Trace line names no contract or flow, so a tester has nowhere to check it from",
                    "it isn't tied to a contract or a flow, so a tester has nowhere to check it from"),
    "component": ("it names {words}, inside the app; say what a tester sees at the contract or flow instead",
                  "it names {words}, which is inside the app; let's say what a tester sees at the boundary instead"),
    "technology": ("it names {words}, how the team builds it; say what a tester sees instead",
                   "it names {words}, which is how the team builds it; let's say what a tester sees instead"),
    "id-in-sentence": ("its sentence holds {words}; say the name and put the ID on the Trace line",
                       "its sentence uses a code where the name should be ({words})"),
}


def cmd_lint(args, out):
    root = pathlib.Path(args.vault)
    vault, resolver = load(root)
    if args.fix_shape:
        return fix_shape(root, vault, args, out, resolver)
    epics, missing = chosen(vault, args.epics)
    if missing:
        return emit(no_such_epic("epics lint", missing), args, out, resolver)
    findings = epicslint.lint(vault, epics)
    result = say.Result("epics lint", exit=say.REFUSED if findings else say.DONE,
                        data={"epics": [e.id for e in epics], "findings": [f.as_json() for f in findings]})
    result.lines = [finding_line(f, resolver) for f in findings]
    if not findings:
        result.lines = [say.Line(f"{len(epics)} epics: every criterion passes the boundary test.",
                                 f"All {len(epics)} epics pass the boundary test: every criterion sits at a contract "
                                 "or a flow.")]
    return emit(result, args, out, resolver)


def chosen(vault, ids):
    from vela import trace
    every = trace.epics(vault)
    if not ids:
        return every, []
    by_id = {e.id: e for e in every}
    return [by_id[i] for i in ids if i in by_id], [i for i in ids if i not in by_id]


def no_such_epic(command, missing):
    result = say.Result(command, exit=say.REFUSED, data={"missing": missing})
    result.refusals.append(say.Refusal("epic", f"I couldn't find {len(missing)} of the epics asked for.",
                                       f"No epic page has the id {', '.join(missing)}; run vela epics lint with "
                                       "no id to test every epic."))
    return result


def finding_line(f, resolver):
    where = f"{f.path}:{f.line}"
    if f.kind == "too-many":
        return say.Line(f"{where}: {f.epic} has {f.count} criteria, more than about {epicslint.MAX_CRITERIA}; offer a "
                        "split, or group them if the lead keeps it whole.",
                        f"{f.epic_title} has {f.count} criteria, more than about seven. Let's look at splitting it, "
                        "or group them if you'd rather keep it whole.")
    text, plain = LINT_SAYS[f.kind]
    words = ", ".join(f.words)
    plain_words = ", ".join(resolver.name(w) if f.kind == "id-in-sentence" else w for w in f.words)
    return say.Line(f"{where}: {f.epic}.AC{f.ac} ({f.criterion}): {text.format(words=words)}.",
                    resolver.plain(f'On {f.epic_title}, "{f.criterion}": {plain.format(words=plain_words)}.'))


def is_reader_copy(root):
    """The rule `roles` applies, from the disk alone: a reader copy has a workspace file and no git."""
    facts = roles.Facts(git_here=(root / ".git").exists(), has_workspace=(root / ".vela" / "workspace.json").is_file())
    return facts.has_workspace and not facts.git_here and roles.decide(facts).role == roles.READER


def fix_shape(root, vault, args, out, resolver):
    if args.epics:
        raise ValueError("--fix-shape takes one epic of its own; name no other epics with it")
    epics, missing = chosen(vault, [args.fix_shape])
    if missing:
        return emit(no_such_epic("epics lint", missing), args, out, resolver)
    page = epics[0]
    title = str(page.meta.get("title") or page.id)
    path = root / page.path
    text = path.read_text(encoding="utf-8")
    result = say.Result("epics lint", data={"epic": page.id, "path": page.path})
    try:
        rewrite = epicslint.fix_shape(page.path, text)
    except epicslint.ShapeRefused as exc:
        result.exit = say.REFUSED
        result.refusals.append(say.Refusal("one criteria section", exc.plain,
                                           f"Put {page.id}'s criteria under one heading in {page.path}, then run "
                                           "--fix-shape again."))
        return emit(result, args, out, resolver)
    except epicslint.ShapeLost as exc:
        print(str(exc), file=out)
        return say.FAILED
    result.data.update(changed=rewrite.changed, numbers=rewrite.numbers,
                       headings=[{"ac": n, "heading": h} for n, h in rewrite.headings])
    if not rewrite.changed:
        result.lines = [say.Line(f"{page.id} is already in the template shape; nothing changed.",
                                 f"{title} already uses the new layout, so I haven't changed anything.")]
        return emit(result, args, out, resolver)
    try:
        atomic.write_atomic(path, rewrite.text)
    except atomic.WriteFailed as exc:
        print(f"vela epics lint: could not write {page.path}: {exc}", file=out)
        return say.FAILED
    result.wrote = [page.path]
    numbers = ", ".join(f"AC{n}" for n in rewrite.numbers)
    result.lines = [say.Line(f"Rewrote {page.path} to the template; AC numbers kept: {numbers}. The headings are "
                             "drafted from each criterion's first words; reword them with the lead.",
                             f"I moved {title} to the new layout and kept every criterion's number, so nothing that "
                             "points at one breaks. The headings are drafted from each criterion's first words, so "
                             "let's reword them together.")]
    result.lines += [say.Line(f"  AC{n}: {h}", f"- {resolver.plain(h)}") for n, h in rewrite.headings]
    if is_reader_copy(root):
        result.lines.append(say.Line("This is a reader copy: no git runs here; the change reaches the owner through a "
                                     "proposal.", "This is your reading copy, so the change reaches the owner "
                                                  "through a proposal."))
    return emit(result, args, out, resolver)

