"""`vela decide ID --yes ^cM [...]` and `vela decide --reopen ID --why ^cN` (overhaul Task 16, plan 3.3).

Grill section 4 was nine bullets of writes per decision, every one mechanical: the state, the Decision bullet, the Why
copied word for word, the Dissent, the Override and Decided by bullets, the Pending approval marker in a reader copy, the
`## Changes` row, the mark on the deciding capture and the commit. Each was a place for a model to tidy the lead's words
or skip a row, and `close gate` then refused the session over a decision with nothing on record. Here the flags name
captures, never words; `vela.decisions.decide` dispatches to the target kind's module and writes all of it in one step,
through the same `decisions.plan` as `vela apply`, so `close gate` and `decide` agree by construction. The skill
captures a reason only when the lead gives one; code copies it.

    vela decide ID --yes ^cM [--why ^cK] [--dissent ^cJ]
                   [--override RULE ... --reason-from ^cR [--until YYYY-MM-DD]]
                   [--provider ^cP] [--picked "OPTION=^cP" --rejected "OPTION=^cR|declined" ...]
                   [--group CRITERIA YES ...] [--vault V] [--today D] [--json|--for-lead]
    vela decide ID --later --yes ^cM [--vault V] [--today D] [--json|--for-lead]
    vela decide --reopen ID --why ^cN [--vault V] [--today D] [--json|--for-lead]

ID is a page's or item's ID, an allocation row as `CAP-nnn.FRn@APP-<slug>`, or a release's heading. `--provider` is a
contract's (where the provider stands), `--group` an epic's (one per criterion group); each kind's module
says why. `--override` may repeat; its rules share one reason, and `--until` goes on the standing ones only (an event
rule, GATE-1, 2 or 3, has nothing to end).

The lead's yes settles any item. When the item is someone else's, `Decided by: @lead, on behalf of @owner` is written
for them and the answer says so once; nothing is refused or overridden.

Any session can decide: the rule is that `vela decide` filed it, with the lead's yes, and nothing here
reads the session's modes. `--later --yes ^cM` is the other answer to an offer to settle: it keeps the lead's yes under
`## Ready to decide` and decides nothing; with `--picked` and `--rejected` it also writes the pick's options on the
page, so the reasons the lead gave are kept.

The gate (`gates.verdict`) runs first, with the flow check's recorded standings for a slice or a flow: a reason
the lead didn't set aside refuses the decision, with the override line that would decide it anyway.

Exit codes (plan 3.1):
0  decided (or planned, or reopened): what was written and the commit are printed (`--json`: `id`, `state`, `wrote`,
   `commit`, `reader`);
1  refused: every reason, plainly, and nothing written. The gate failed and nothing set it aside; the yes isn't a yes;
   what the target kind needs is missing; or no session is open;
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
from vela.decisions import consent, decide, decide_writes, ready, schema, textedit
from vela.edge import apply as disk
from vela.edge import atomic, sessiongit, stagegit
from vela.edge.vaultgit import GitUnavailable

NAME = "decide"
MESSAGES = {"decided": "{mode}: {id} decided", "planned": "{mode}: {id} planned", "reopened": "{mode}: {id} reopened"}
OPTIONS_KEPT = "{mode}: {id} options kept"
NO_MODE = "decide"
STATED_MESSAGE = "import: {id} decided, as {source} states"


def register(sub):
    parser = sub.add_parser("decide", help="write one decision the lead gave: state, Decision, Why in their words, "
                                           "Changes row, mark and commit, after the gate")
    parser.add_argument("--later", action="store_true",
                        help="the lead said yes but isn't settling it now: keep it on the list (needs --yes; --picked and --rejected also write the options)")
    parser.add_argument("id", nargs="?", help="the item: an ID, CAP-nnn.FRn@APP-<slug> for an allocation row, or a "
                                              "release's heading")
    parser.add_argument("--reopen", metavar="ID", help="reopen a decided item (a change of mind), with --why")
    parser.add_argument("--yes", metavar="^cM", help="the capture holding the lead's yes")
    parser.add_argument("--why", metavar="^cK", help="the capture holding the lead's reason, copied verbatim")
    parser.add_argument("--dissent", metavar="^cJ", help="the capture holding a disagreement, in the dissenter's words")
    parser.add_argument("--override", metavar="RULE", action="append",
                        help="a rule the lead sets aside (GATE-4, E318, \"case table\", ...); repeat for each")
    parser.add_argument("--reason-from", metavar="^cR", help="the capture holding the lead's reason for the overrides")
    parser.add_argument("--until", metavar="YYYY-MM-DD", help="the last day a standing override covers")
    parser.add_argument("--options-none", metavar="^cN",
                        help="the capture holding the lead's answer that this was the only option: recorded as the options considered, so no Shape session is needed (the grill gate below medium asks that one question)")
    parser.add_argument("--provider", metavar="^cP", help="contract: the capture saying where the provider stands")
    parser.add_argument("--group", nargs=2, action="append", metavar=("CRITERIA", "YES"),
                        help="epic: a criterion group (AC1-AC5) and the lead's yes to it; repeat")
    parser.add_argument("--picked", metavar="OPTION=^cP",
                        help="settling a pick: the option the lead picked and the capture where they picked it")
    parser.add_argument("--rejected", metavar="OPTION=^cR", action="append",
                        help="settling a pick: an option set aside and the capture holding the lead's reason "
                             "(OPTION=declined when they gave none); repeat for each")
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
    item = {"id": ident, "yes": args.yes, "why": args.why, "dissent": args.dissent,
            "overrides": override_groups(args), "by": by, "reader": reader}
    if args.provider:
        item["provider"] = args.provider
    if getattr(args, "stated_in", None):
        item["stated_in"] = args.stated_in
    if args.picked:
        item["picked"] = args.picked
    if args.rejected:
        item["rejected"] = list(args.rejected)
    if getattr(args, "options_none", None):
        item["options_none"] = args.options_none
    if args.group:
        item["groups"] = [{"criteria": c, "yes": y} for c, y in args.group]
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
        return commands.emit(keep_for_later(root, record, staged, args), args, out, resolver)
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


def keep_for_later(root, record, staged, args):
    """`--later --yes ^cM`: the lead's yes is kept under Ready to decide and nothing is decided. A declined offer to
    settle is still on record (a Silent Fallback of consent otherwise). No gate, no page, no commit: the notes and the
    stub only. What it cannot write is refused, never dropped: a Silent Fallback of the lead's reasons otherwise."""
    ident = args.reopen or args.id
    early = later_refusals(args, record, staged, ident)
    if early is not None:
        return early
    if args.picked or args.rejected:
        return keep_pick_for_later(root, record, staged, args, ident)
    marked = ready.mark(record.text, ident, record.id, args.yes.strip())
    wrote = sessiongit.write_notes(root, record, marked)
    return say.Result(NAME, wrote=wrote, data={"id": ident, "ready_to_decide": True},
                      lines=[say.Line(f"{ident} kept as ready to decide in {record.id}",
                                      plain="I've kept it as not decided yet. It's on the list of things you said yes "
                                            "to, for when you're sure.")])


def keep_pick_for_later(root, record, staged, args, ident):
    """`--later` with `--picked` and `--rejected`: the lead picked and then kept the item open, so the pick's options
    go on the page at the item's own state, with their captures kept on it, and the yes is listed as for any `--later`.
    Without this the answer to "Why not <option>?" would be lost on the way to a settle (a Silent Fallback)."""
    pick = {"picked": args.picked, "rejected": list(args.rejected or [])}
    _, target = decide.locate(staged, ident)
    found = decide_writes.options_refusals(pick, staged, record, target)
    if found:
        return refused(found)
    page = decide_writes.add_history(staged.text(target.path), [decide_writes.options_bullet(pick, staged, record)], target)
    mark = textedit.keep_mark(textedit.basename(target.path), target.anchor, target.id, target.state)
    notes = textedit.record_text(record, staged)
    for ref in decide_writes.consumed(pick):
        notes = textedit.mark_if_unmarked(notes, ref, mark)
    notes = ready.mark(notes, ident, record.id, args.yes.strip())
    writes = [schema.Write(target.path, page)] + textedit.record_writes(record, staged, notes)
    try:
        written = disk.write_all(root, writes, {})
        commit = None if sessiongit.is_read_copy(root) else stagegit.commit(
            root, OPTIONS_KEPT.format(id=ident, mode=commit_mode(staged.text(record.stub))),
            [p for p in written if not privaterecord.is_private(p)])
    except (disk.OutsideVault, atomic.WriteFailed, GitUnavailable) as exc:
        return failed(f"the options were not kept ({exc})", "The disk refused that, so I kept nothing.")
    return say.Result(NAME, wrote=written, data={"id": ident, "ready_to_decide": True},
                      lines=[say.Line(f"{ident} options written and kept as ready to decide in {record.id}"
                                      + (f"; commit {commit}" if commit else ""),
                                      plain=f"I've written down what you picked and what it beat, and kept {target.name} "
                                            "as not decided yet.")])


def later_refusals(args, record, staged, ident):
    """The Result refusing `--later`, or None when the item exists, is open, and the yes is the lead's own."""
    if not (args.yes or "").strip():
        return refused([textedit.refusal(
            "decide-later-needs-yes", "I need the lead's yes before I can keep this for later.",
            "give --yes: the capture holding the lead's yes to the pick", audience=say.MODEL,
            override="none: without the lead's yes there is nothing to keep")])
    unwritten = [flag for flag, given in (("--why", args.why), ("--dissent", args.dissent), ("--reopen", args.reopen))
                 if given]
    if unwritten:
        return refused([textedit.refusal(
            "decide-later-writes-nothing", "Keeping this for later writes down only your yes, not the reasons or the "
                                           "options, so I haven't kept anything.",
            f"--later writes none of {', '.join(unwritten)}; settle it to file them, or drop those flags and keep "
            "only the yes (--picked and --rejected it does write)", audience=say.MODEL,
            override="none: drop the flags, or settle it")])
    module, target = decide.locate(staged, ident)
    if target is None:
        return refused([decide.missing(ident)])
    done = decide.already(staged, ident)
    if done is not None:
        return already_result(done)
    return yes_refusal_for_later(args.yes, record, staged.lead)


def yes_refusal_for_later(ref, record, lead):
    """The refusal when `ref` isn't the lead's own plain yes (the test the Ready-to-decide listing applies), else None."""
    found = consent.a_yes(ref, record)
    if found is not None:
        return refused([found])
    if ready.leads_own_yes(record.capture(ref), lead):
        return None
    return refused([textedit.refusal(
        "decide-later-not-the-leads-yes", "That isn't a plain yes from you, so I haven't kept it as one.",
        f"{ref} is not the lead's own plain yes (a bare \"ok\", Claude's words, or someone else's does not list an "
        "item as ready to decide)", audience=say.MODEL, override="none: ask the lead for a plain yes")])


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
    owners = decide_writes.stand_in_owners(item, staged, record, target)
    return report(item, target, state, written, commit, reader, owners)


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


def report(item, target, state, written, commit, reader, owners=()):
    said = "reopened" if item.get("reopen") else state
    lines = [say.Line(f"{said} {target.id}: wrote {', '.join(written)}" + (f"; commit {commit}" if commit else ""),
                      plain=f"{target.name} is {said}." + set_aside_words(item))]
    if owners:
        lines.append(say.Line(f"decided on behalf of {' '.join(owners)}",
                              plain=f"{target.name} is {' and '.join(owners)}'s; I noted you settled it for them. "
                                    "They can confirm it or challenge it."))
    if reader:
        lines.append(say.Line("read copy: nothing committed (no git runs here); the decision is pending the owner's "
                              "approval.", plain="This is your copy, so nothing was committed, and the owner sees "
                                                 "the decision before it counts."))
    return say.Result(NAME, lines=lines, wrote=written,
                      data={"id": target.id, "kind": target.kind, "state": state, "commit": commit, "reader": reader})
