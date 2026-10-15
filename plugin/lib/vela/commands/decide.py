"""`vela decide ID --readback ^cN --yes ^cM [...]` and `vela decide --reopen ID --why ^cN` (overhaul Task 16, plan 3.3).

Grill section 4 was nine bullets of writes per decision, every one mechanical: the state, the Decision bullet, the Why
copied word for word, the Dissent, the Override and Decided by bullets, the Pending approval marker in a reader copy, the
`## Changes` row, the mark on the deciding capture and the commit. Each was a place for a model to tidy the lead's words
or skip a row, and `close gate` then refused the session over a decision with nothing on record. Here the flags name
captures, never words; `vela.decisions.decide` dispatches to the target kind's module and writes all of it in one step,
through the same `decisions.plan` as `vela apply`, so `close gate` and `decide` agree by construction. The skill still
asks "Why this one, in your words?" and captures the answer; code copies it.

    vela decide ID --readback ^cN --yes ^cM [--why ^cK] [--dissent ^cJ]
                   [--override RULE ... --reason-from ^cR [--until YYYY-MM-DD]] [--on-behalf @owner]
                   [--provider ^cP] [--group CRITERIA READBACK YES ...] [--vault V] [--today D] [--json|--for-lead]
    vela decide --reopen ID --why ^cN [--vault V] [--today D] [--json|--for-lead]

ID is a page's or item's ID, an allocation row as `CAP-nnn.FRn@APP-<slug>`, or a release's heading. `--provider` is a
contract's (where the provider stands), `--group` an epic's (one per criterion group read back); each kind's module
says why. `--override` may repeat; its rules share one reason, and `--until` goes on the standing ones only (an event
rule, GATE-1, 2, 3 or 5, has nothing to end).

The grill gate (`gates.verdict`) runs first, with the flow check's recorded standings for a slice or a flow: a reason
the lead didn't set aside refuses the decision, with the override line that would decide it anyway.

Exit codes (plan 3.1):
0  decided (or planned, or reopened): what was written and the commit are printed (`--json`: `id`, `state`, `wrote`,
   `commit`, `reader`);
1  refused: every reason, plainly, and nothing written. The gate failed and nothing set it aside; the yes isn't a yes
   or comes before the read-back; what the target kind needs is missing; or no session is open;
2  the tool failed: the vault or git can't be read, the disk refused a write, or the commit failed (what was written
   is named, so nothing is lost);
3  the item is already decided: nothing written; the choices are reopening it (`--reopen`, recording the change of
   mind) or leaving it (`needs_lead`). Also: several sessions are open.

Commits `grill: <ID> decided` (`planned` for a slice, `reopened` for a change of mind) with only the changed pages and
the record, by exact path. In a reader copy no git runs at all, and the marker says the owner sees it before it counts.
"""
import pathlib

from vela import commands, decisions, gates, say
from vela import override as overrides
from vela.commands import apply as apply_command
from vela.decisions import decide, schema, textedit
from vela.edge import apply as disk
from vela.edge import atomic, sessiongit, stagegit
from vela.edge.vaultgit import GitUnavailable

NAME = "decide"
MESSAGES = {"decided": "grill: {id} decided", "planned": "grill: {id} planned", "reopened": "grill: {id} reopened"}


def register(sub):
    parser = sub.add_parser("decide", help="write one decision the lead gave: state, Decision, Why in their words, "
                                           "Changes row, mark and commit, after the grill gate")
    parser.add_argument("id", nargs="?", help="the item: an ID, CAP-nnn.FRn@APP-<slug> for an allocation row, or a "
                                              "release's heading")
    parser.add_argument("--reopen", metavar="ID", help="reopen a decided item (a change of mind), with --why")
    parser.add_argument("--readback", metavar="^cN", help="the capture where the final wording was read back")
    parser.add_argument("--yes", metavar="^cM", help="the capture holding the lead's yes, after the read-back")
    parser.add_argument("--why", metavar="^cK", help="the capture holding the lead's reason, copied verbatim")
    parser.add_argument("--dissent", metavar="^cJ", help="the capture holding a disagreement, in the dissenter's words")
    parser.add_argument("--override", metavar="RULE", action="append",
                        help="a rule the lead sets aside (GATE-4, E318, \"case table\", ...); repeat for each")
    parser.add_argument("--reason-from", metavar="^cR", help="the capture holding the lead's reason for the overrides")
    parser.add_argument("--until", metavar="YYYY-MM-DD", help="the last day a standing override covers")
    parser.add_argument("--on-behalf", metavar="@owner", help="the owner the lead decides for (goes with GATE-5)")
    parser.add_argument("--provider", metavar="^cP", help="contract: the capture saying where the provider stands")
    parser.add_argument("--group", nargs=3, action="append", metavar=("CRITERIA", "READBACK", "YES"),
                        help="epic: a criterion group read back (AC1-AC5), its read-back and the lead's yes; repeat")
    parser.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    parser.add_argument("--today", help="the date written (Dissent, Override, Pending approval), YYYY-MM-DD")
    say.add_output_flags(parser)
    parser.set_defaults(func=run)


def failed(text, plain):
    return say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"vela decide: {text}", plain=plain)])


def refused(refusals):
    return say.Result(NAME, exit=say.REFUSED, refusals=list(refusals))


def override_groups(args):
    """The --override rules as the item's groups: the standing ones with --until, the event ones without."""
    rules = list(args.override or [])
    if not rules:
        return []
    standing = [r for r in rules if overrides.is_standing(r)]
    event = [r for r in rules if not overrides.is_standing(r)]
    groups = []
    if standing:
        groups.append({"rules": standing, "reason": args.reason_from, "until": args.until})
    if event:
        groups.append({"rules": event, "reason": args.reason_from})
    return groups


def item_from(args, ident, by, reader):
    if args.reopen:
        return {"id": ident, "reopen": True, "why": args.why, "by": by, "reader": reader}
    item = {"id": ident, "readback": args.readback, "yes": args.yes, "why": args.why, "dissent": args.dissent,
            "overrides": override_groups(args), "on_behalf_of": args.on_behalf, "by": by, "reader": reader}
    if args.provider:
        item["provider"] = args.provider
    if args.group:
        item["groups"] = [{"criteria": c, "readback": r, "yes": y} for c, r, y in args.group]
    return {k: v for k, v in item.items() if v not in (None, [])}


def lead_handle(root, record, args):
    """`.vela/handle` (what `vela whoami` keeps); else the yes capture's origin when it is a handle."""
    handle = sessiongit.read_handle(root)
    if handle:
        return "@" + handle.lstrip("@")
    capture = record.capture(args.yes or args.why) if (args.yes or args.why) else None
    origin = capture.origin.strip() if capture is not None else ""
    return origin if origin.startswith("@") else ""


def run(args, out):
    from vela import cli  # the shell loads the vault, parses the date and reads the flow record; this module wires it
    root = pathlib.Path(args.vault).resolve()
    ident = args.reopen or args.id
    if not ident or (args.reopen and args.id):
        return commands.emit(failed("give one ID, or --reopen ID", "I wasn't told which item to decide."), args, out)
    try:
        today = cli.parse_today(args.today)[0]
        vault = cli.load_vault(root)
    except cli.ToolError as exc:
        return commands.emit(failed(str(exc), "I couldn't read the vault, so I decided nothing."), args, out)
    resolver = say.Resolver(vault)
    record, early = apply_command.find_record(root)
    if early is not None:
        return commands.emit(early, args, out, resolver)
    reader = sessiongit.is_read_copy(root)
    # A decision numbers nothing, so no branch is read for IDs; the view still carries the (empty) list `attach` gives.
    staged = textedit.attach(decisions.Staged(vault, disk.reader(root)), today, [])
    _, target = decide.locate(staged, ident)
    if target is not None and target.gate:
        keys = gates.flow_keys(vault, target.gate)
        staged.flows = cli.recorded_standings(root, vault, keys, today)[0] if keys else {}
    if not args.reopen:
        done = decide.already(staged, ident)
        if done is not None:
            return commands.emit(already_result(done), args, out, resolver)
    item = item_from(args, ident, lead_handle(root, record, args), reader)
    result = file_item(item, root, staged, record, reader)
    return commands.emit(result, args, out, resolver)


def already_result(target):
    choices = [{"choice": "reopen", "command": f"vela decide --reopen {target.id} --why <the lead's reason>",
                "plain": "reopen it, which records the change of mind"},
               {"choice": "leave", "command": "", "plain": "leave it as it is"}]
    return say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=choices, data={"id": target.id, "state": target.state},
                      lines=[say.Line(f"{target.id} is already {target.state}; nothing written. Reopen it? "
                                      f"vela decide --reopen {target.id} --why ^cN",
                                      plain=f"{target.name} is already {target.state}. Shall I reopen it? Reopening "
                                            "records the change of mind.")])


def file_item(item, root, staged, record, reader):
    raw = {"version": schema.VERSION, "kind": "decide", "session": record.id, "items": [item]}
    decision = decisions.Decision("decide", record.id, [item], raw)
    folder = root / schema.FOLDER / record.id
    existing = sorted(p.name for p in folder.glob("*.json")) if folder.is_dir() else []
    path = root / schema.draft_path(record.id, existing, "decide")
    _, target = decide.locate(staged, item["id"])
    try:
        writes, refusals = decisions.plan(decision, staged, record)
        if refusals:
            return refused(refusals)
        state = decide.new_state(item, staged)
        filed = decisions.applied_text(decision, writes, decisions.record_after(record, staged))
        path.parent.mkdir(parents=True, exist_ok=True)
        written = disk.write_all(root, writes, {path: filed})
    except disk.OutsideVault as exc:
        return refused([say.Refusal("apply-outside-vault", "That would have changed a file outside the vault, so I "
                                                           "decided nothing.", f"{exc}.",
                                    override="none: vela only writes inside the vault")])
    except atomic.WriteFailed as exc:
        landed = ", ".join(str(p) for p in exc.written) or "nothing"
        return failed(f"the disk refused a write ({exc}); written: {landed}",
                      "The disk refused part of that; I've listed which files changed.")
    commit = None
    if not reader:
        message = MESSAGES[state if not item.get("reopen") else "reopened"].format(id=item["id"])
        try:
            commit = stagegit.commit(root, message, written)
        except GitUnavailable as exc:
            return failed(f"wrote {', '.join(written)} but the commit failed: {exc}",
                          "I wrote it down, but couldn't commit it; the changes are on disk.")
    return report(item, target, state, written, commit, reader)


def report(item, target, state, written, commit, reader):
    said = "reopened" if item.get("reopen") else state
    lines = [say.Line(f"{said} {target.id}: wrote {', '.join(written)}" + (f"; commit {commit}" if commit else ""),
                      plain=f"I've written {target.name} down as {said}" + (" and committed it." if commit else "."))]
    if reader:
        lines.append(say.Line("read copy: nothing committed (no git runs here); the decision is pending the owner's "
                              "approval.", plain="This is a read copy, so nothing was committed, and the owner sees "
                                                 "the decision before it counts."))
    return say.Result(NAME, lines=lines, wrote=written,
                      data={"id": target.id, "kind": target.kind, "state": state, "commit": commit, "reader": reader})
