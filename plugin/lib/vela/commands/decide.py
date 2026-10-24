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
    vela decide ID --later --yes ^cM [--vault V] [--today D] [--json|--for-lead]
    vela decide --reopen ID --why ^cN [--vault V] [--today D] [--json|--for-lead]

ID is a page's or item's ID, an allocation row as `CAP-nnn.FRn@APP-<slug>`, or a release's heading. `--provider` is a
contract's (where the provider stands), `--group` an epic's (one per criterion group read back); each kind's module
says why. `--override` may repeat; its rules share one reason, and `--until` goes on the standing ones only (an event
rule, GATE-1, 2, 3 or 5, has nothing to end).

Any session can decide: the rule is that `vela decide` filed it, with the lead's yes to a read-back, and nothing here
reads the session's modes. `--later --yes ^cM` is the other answer to an offer to settle: it keeps the lead's yes under
`## Ready to decide` and decides nothing.

The gate (`gates.verdict`) runs first, with the flow check's recorded standings for a slice or a flow: a reason
the lead didn't set aside refuses the decision, with the override line that would decide it anyway.

Exit codes (plan 3.1):
0  decided (or planned, or reopened): what was written and the commit are printed (`--json`: `id`, `state`, `wrote`,
   `commit`, `reader`);
1  refused: every reason, plainly, and nothing written. The gate failed and nothing set it aside; the yes isn't a yes
   or comes before the read-back; what the target kind needs is missing; or no session is open;
2  the tool failed: the vault or git can't be read, the disk refused a write, or the commit failed (what was written
   is named, so nothing is lost);
3  the item is already decided: nothing written; the choices are reopening it (`--reopen`, recording the change of
   mind) or leaving it (`needs_lead`). Also: several sessions are open, or the lead's GitHub handle is unknown
   (`vela whoami` asks for it once; a decision puts the lead's name on record, so it is never guessed).

Commits `<mode>: <ID> decided` (`planned` for a slice, `reopened` for a change of mind), `<mode>` being the session's
first mode (`commit_mode`) with only the changed pages and
the record, by exact path. In a reader copy no git runs at all, and the marker says the owner sees it before it counts.
"""
import datetime
import pathlib

from vela import commands, decisions, gates, privaterecord, receipts, say, sessions
from vela import override as overrides
from vela.commands import apply as apply_command, whoami
from vela.decisions import decide, ready, schema, textedit
from vela.edge import apply as disk
from vela.edge import atomic, sessiongit, stagegit
from vela.edge.vaultgit import GitUnavailable

NAME = "decide"
MESSAGES = {"decided": "{mode}: {id} decided", "planned": "{mode}: {id} planned", "reopened": "{mode}: {id} reopened"}
NO_MODE = "decide"
STATED_MESSAGE = "import: {id} decided, as {source} states"


def register(sub):
    parser = sub.add_parser("decide", help="write one decision the lead gave: state, Decision, Why in their words, "
                                           "Changes row, mark and commit, after the gate")
    parser.add_argument("--later", action="store_true",
                        help="the lead said yes but isn't settling it now: keep it on the list (needs --yes)")
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
    parser.add_argument("--stated-in", metavar="SRC-nn",
                        help="import: the source that states the decision; the lead's yes confirms it, no options "
                             "needed")
    parser.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    parser.add_argument("--today", help="the date written (Dissent, Override, Pending approval), YYYY-MM-DD")
    say.add_output_flags(parser)
    parser.set_defaults(func=run)


def failed(text, plain):
    return say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"vela decide: {text}", plain=plain)])


def refused(refusals, name=""):
    """The refusal Result: when more than one thing stands in the lead's way, the answer counts them first."""
    theirs = [r for r in refusals if r.audience == say.LEAD]
    answer = (f"I can't decide {name} yet: {say.count_words(len(theirs))} things stand in the way."
              if name and len(theirs) > 1 else "")
    return say.Result(NAME, exit=say.REFUSED, refusals=list(refusals), answer=answer)


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
    if getattr(args, "stated_in", None):
        item["stated_in"] = args.stated_in
    if args.group:
        item["groups"] = [{"criteria": c, "readback": r, "yes": y} for c, r, y in args.group]
    return {k: v for k, v in item.items() if v not in (None, [])}


def lead_handle(root):
    """(the lead's `@handle`, None), or (None, the Result to print instead): `vela whoami`'s answer, which asks the
    lead once when it doesn't know. A yes capture's origin is never taken for the lead: the model writes it."""
    found = whoami.find_handle(root)
    if found.exit != say.DONE:
        return None, found
    return receipts.handle_ref(found.data["handle"]), None


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
    resolver = say.Resolver(vault, today=datetime.date.fromisoformat(today))
    record, early = apply_command.find_record(root)
    if early is not None:
        return commands.emit(early, args, out, resolver)
    reader = sessiongit.is_read_copy(root)
    by, early = lead_handle(root)
    if early is not None:
        return commands.emit(early, args, out, resolver)
    # A decision numbers nothing, so no branch is read for IDs; the view still carries the (empty) list `attach` gives.
    staged = textedit.attach(decisions.Staged(vault, disk.reader(root)), today, [], lead=apply_command.lead_of(root))
    _, target = decide.locate(staged, ident)
    if args.later:
        return commands.emit(keep_for_later(root, record, ident, args.yes, args.readback), args, out, resolver)
    if target is not None and target.gate:
        keys = gates.flow_keys(vault, target.gate)
        staged.flows = cli.recorded_standings(root, vault, keys, today)[0] if keys else {}
    if not args.reopen:
        done = decide.already(staged, ident)
        if done is not None:
            return commands.emit(already_result(done), args, out, resolver)
    item = item_from(args, ident, by, reader)
    result = file_item(item, root, staged, record, reader)
    return commands.emit(result, args, out, resolver)


def keep_for_later(root, record, ident, yes, readback=None):
    """`--later --yes ^cM`: the lead's yes is kept under Ready to decide and nothing is decided. A declined offer to
    settle is still on record (a Silent Fallback of consent otherwise). No gate, no page, no commit: the notes and the
    stub only."""
    if not (yes or "").strip():
        return refused([textedit.refusal(
            "decide-later-needs-yes", "I need the lead's yes before I can keep this for later.",
            "give --yes: the capture holding the lead's yes to the pick", audience=say.MODEL,
            override="none: without the lead's yes there is nothing to keep")])
    if readback:
        return refused([textedit.refusal(
            "decide-later-with-readback", "I can't both keep this for later and settle it.",
            "a read-back means the lead is settling, so drop --later", audience=say.MODEL,
            override="none: drop --later to settle, or --readback to keep it for later")])
    marked = ready.mark(record.text, ident, record.id, yes.strip())
    wrote = sessiongit.write_notes(root, record, marked)
    return say.Result(NAME, wrote=wrote, data={"id": ident, "ready_to_decide": True},
                      lines=[say.Line(f"{ident} kept as ready to decide in {record.id}",
                                      plain="I've kept it as not decided yet. It's on the list of things you said yes "
                                            "to, for when you're sure.")])


def commit_mode(stub_text):
    """The session's first mode, the label before the colon in the commit message. A header that names no mode gets
    `decide`. Nothing reads the label back, so the default hides no failure."""
    modes = sessions.modes_of(privaterecord.stub_meta(stub_text or ""))
    return modes[0] if modes else NO_MODE


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
            return refused(refusals, target.name if target is not None else "")
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
        message = MESSAGES[state if not item.get("reopen") else "reopened"].format(
            id=item["id"], mode=commit_mode(staged.text(record.stub)))
        if item.get("stated_in") and not item.get("reopen"):
            message = STATED_MESSAGE.format(id=item["id"], source=item["stated_in"])
        try:
            commit = stagegit.commit(root, message, [p for p in written if not privaterecord.is_private(p)])
        except GitUnavailable as exc:
            return failed(f"wrote {', '.join(written)} but the commit failed: {exc}",
                          "I wrote it down, but couldn't commit it; the changes are on disk.")
    return report(item, target, state, written, commit, reader)


def set_aside_words(item):
    """' I've noted that you set aside the open-question check until December 1.': the true state when a decision
    went through on an exception (conversation voice rules 4 and 6), or ""."""
    said = []
    for group in item.get("overrides") or ():
        rules = say.names_said([say.GATE_WORDS.get(r) or say.RULE_WORDS.get(r) or rule_words(r)
                                for r in group.get("rules") or ()])
        until = f" until {say.date_words(group['until'])}" if group.get("until") else ""
        said.append(f"{rules}{until}")
    return f" I've noted that you set aside {say.names_said(said)}." if said else ""


def rule_words(rule):
    from vela import schema as vault_schema
    meaning = vault_schema.CODES.get(rule)
    return f'the "{meaning}" check' if meaning else "a check"


def report(item, target, state, written, commit, reader):
    said = "reopened" if item.get("reopen") else state
    lines = [say.Line(f"{said} {target.id}: wrote {', '.join(written)}" + (f"; commit {commit}" if commit else ""),
                      plain=f"{target.name} is {said}." + set_aside_words(item))]
    if reader:
        lines.append(say.Line("read copy: nothing committed (no git runs here); the decision is pending the owner's "
                              "approval.", plain="This is your copy, so nothing was committed, and the owner sees "
                                                 "the decision before it counts."))
    return say.Result(NAME, lines=lines, wrote=written,
                      data={"id": target.id, "kind": target.kind, "state": state, "commit": commit, "reader": reader})
