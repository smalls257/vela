"""`vela close readback [--reword ITEM --line L --words W [--approved ^cNN]] [--cut ITEM --line L] [--pick ^cNN]
[--done] [--json|--for-lead]`: the lead reads back every sentence that goes on record in their name.

The Violation this command's shape prevents is a Silent Fallback in the record: a receipt's words, a Why line or a
quote reads as something the lead said, and nobody showed them the final wording. `closereadback.py` says what is
listed and why. Close order (controller ruling C7): "Still yes?" reconfirm first, then this read-back, so the digest
`--done` stores covers the final words; editing any listed sentence afterward changes the digest and the gate asks again.

- no flag: list the sentences (exit 0).
- `--reword ITEM --line decision|why|quote --words "..."`: the new words must be an excerpt of the capture the line
  cites, or the words of a lead capture that approves them (`--approved ^cNN`, which re-points a decision receipt to it).
- `--cut ITEM --line why|quote`: drop the line. A decision's words can be reworded, never cut.
- `--pick ^cNN`: add a quote of the lead's own words (or of someone with their own quote-yes) to
  `.vela/close/<id>.quotes.json`. The PR body no longer prints picked quotes; the pick is still read back and gated.
- `--done`: store the digest of what stands now in `.vela/close/<id>.readback.json`.

Exit codes: 0 done; 1 refused (said in plain words); 2 the tool failed; 3 several sessions are open.
"""
import json
import pathlib
from types import SimpleNamespace

from vela import closegate, closereadback, closestate, say
from vela.decisions import consent, textedit
from vela.edge import sessiongit

NAME = "close readback"
DECISION_STAYS = "Your decision needs your words on record, so I can reword it but not cut it."
NOT_THEIRS = "Those are someone else's words, and they go out only with their own yes, so I won't use them."


def register_close(steps):
    p = steps.add_parser("readback", help="read back every sentence that goes on record in the lead's name: keep, "
                                          "reword or cut each one, pick quotes, then record the yes")
    p.add_argument("--vault", default=".", help="vault root (default: current directory)")
    p.add_argument("--reword", metavar="ITEM", help="the item whose sentence to reword")
    p.add_argument("--cut", metavar="ITEM", help="the item whose Why line or quote to cut")
    p.add_argument("--line", choices=closereadback.LINES, help="which sentence: decision, why or quote")
    p.add_argument("--words", help="with --reword: the new words")
    p.add_argument("--number", metavar="^cNN", help="with --reword or --cut: which one, when an item has several "
                                                    "sentences of that line")
    p.add_argument("--approved", metavar="^cNN", help="with --reword: the lead's capture that approves the new words")
    p.add_argument("--pick", metavar="^cNN", help="add the lead's words in this capture as a quote")
    p.add_argument("--done", action="store_true", help="record that the lead has read back what stands now")
    say.add_output_flags(p)
    p.set_defaults(func=run)


def _file(root, record_id, kind):
    return f"{closestate.FOLDER}/{record_id}.{kind}.json"


def _picked(root, record_id):
    held = sessiongit.read_json(root, _file(root, record_id, "quotes"))
    return list(held.get("quotes", [])) if held else []


def _refused(text, plain=None):
    return say.Result(NAME, exit=say.REFUSED, lines=[say.Line(text, plain=plain or text)])


def _done(wrote, text, plain=None):
    return say.Result(NAME, exit=say.DONE, wrote=list(wrote), lines=[say.Line(text, plain=plain or text)])


NO_LEAD = ("I can't tell whose words these are, because I don't know your GitHub handle yet. "
           "Run vela whoami --set <handle> first.")
NO_LEAD_PLAIN = "I can't tell whose words these are, because I don't know your GitHub handle yet. What is it?"
UNTRACEABLE = "not traceable to your words"


def _find(found, item, line, number):
    """(the sentence, None), or (None, the refusal Result): the item's one sentence of that line, or the one `--number`
    names when there are several."""
    several = [s for s in found if s.item == item and s.line == line]
    if number:
        wanted = record_number(number)
        several = [s for s in several if s.number == wanted]
    if len(several) == 1:
        return several[0], None
    if not several:
        return None, _refused(f"No {line} sentence is listed for {item}.", f"I don't have a {line} line like that.")
    return None, _refused(f"{len(several)} {line} sentences are listed for {item}; say which with --number ^cNN.",
                          "There's more than one of those. Which one do you mean?")


def record_number(ref):
    from vela.decisions import record
    return record.number_of(ref)


def run(args, out):
    from vela import cli, commands
    from vela.commands import apply
    root = pathlib.Path(args.vault).resolve()
    try:
        record, early = apply.find_record(root)
        if early is not None:
            return commands.emit(early, args, out)
        vault = cli.load_vault(root)
        result = judge(args, root, vault, record, apply.lead_of(root))
    except (ValueError, OSError, cli.ToolError) as exc:
        return commands.emit(say.Result(NAME, exit=say.FAILED, lines=[say.Line(
            f"vela close readback: {exc}", plain="I couldn't do the read-back; something on disk didn't answer.")]),
            args, out)
    return commands.emit(result, args, out, say.Resolver(vault))


def judge(args, root, vault, record, lead):
    picked = _picked(root, record.id)
    listing = closereadback.sentences(vault, record.id, record.part, record.text, lead, picked)
    if args.pick:
        return pick(args.pick, root, record, lead, picked, vault)
    if (args.reword or args.cut) and lead is None and listing:
        return _refused(NO_LEAD, NO_LEAD_PLAIN)
    if args.reword:
        return reword(args, root, vault, record, listing, picked, lead)
    if args.cut:
        return cut(args, root, vault, record, listing, picked)
    if args.done:
        digest = closereadback.digest(listing)
        wrote = sessiongit.write_text(root, _file(root, record.id, "readback"), json.dumps({"digest": digest}) + "\n")
        return _done([wrote], f"close readback: {len(listing)} sentence(s) read back ({digest[:12]}).",
                     "Thank you. That wording is on record as you read it.")
    return show(listing, vault, lead)


def show(listing, vault, lead):
    many = len(listing)
    lines = [say.Line(f"close readback: {many} sentence(s) to read back.",
                      plain=f"{say.count_words(many, capital=True)} sentence{'s' if many != 1 else ''} to read back.")]
    if lead is None and listing:
        lines.append(say.Line(NO_LEAD, plain=NO_LEAD_PLAIN))
    for s in listing:
        cite = f"^c{s.number:02d}" if s.number else UNTRACEABLE
        text = f'{s.item} {s.line} ({cite}): "{s.words}"'
        label = _lead_label(s, vault)
        note = "" if s.number else f" ({UNTRACEABLE})"
        lines.append(say.Line(text, plain=f'{label}: "{s.words}"{note}'))
    if not listing:
        lines[0] = say.Line("close readback: nothing goes on record in the lead's name.",
                            plain="Nothing goes on record in your name, so there's nothing to read back.")
    data = {"sentences": [s.__dict__ for s in listing]}
    return say.Result(NAME, exit=say.DONE, lines=lines, data=data)


def _lead_label(sentence, vault):
    what = {"decision": "your decision", "why": "your reason", "quote": "a quote from you"}[sentence.line]
    named = "" if sentence.item.startswith("^") else vault.name_of(sentence.item)
    return f"On {named}, {what}" if named and named != sentence.item else what.capitalize()


def reword(args, root, vault, record, listing, picked, lead):
    if not (args.line and args.words is not None):
        return _refused("--reword needs --line and --words.", "Which sentence, and what should it say?")
    sentence, refusal = _find(listing, args.reword, args.line, args.number)
    if refusal is not None:
        return refusal
    approved = record.capture(args.approved) if args.approved else None
    if args.approved and not _may_approve(approved, record, lead):
        return _refused(f"{args.approved} is not the lead's own yes to the new words.",
                        "That isn't a yes from you to the new wording. Could you say it?")
    cited = record.captures.get(sentence.number)
    try:
        if sentence.line == closereadback.QUOTE:
            closereadback.check_words(args.words, approved, cited)
            return _write_quote(root, record, picked, sentence, args.words)
        page = pathlib.Path(root) / sentence.page
        new = closereadback.reword(page.read_text(encoding="utf-8"), sentence, args.words, approved, cited)
    except ValueError as exc:
        return _refused(f"{exc}", "Those words aren't ones you said, and you haven't said yes to them. What should it say?")
    wrote = sessiongit.write_text(root, sentence.page, new)
    return _done([wrote], f"close readback: reworded the {sentence.line} line for {sentence.item}.",
                 "Changed. I'll read it back to you again.")


def _may_approve(capture, record, lead):
    if capture is None or lead is None:
        return False
    handle, names = lead
    return (capture.is_person and not capture.unverified and not capture.is_bare_non_yes
            and consent.from_the_lead(capture, handle, names) is None)


def _write_quote(root, record, picked, sentence, words):
    kept = [dict(p, words=textedit.unescape(words)) if _is(p, sentence) else p for p in picked]
    wrote = sessiongit.write_text(root, _file(root, record.id, "quotes"), json.dumps({"quotes": kept}, indent=2) + "\n")
    return _done([wrote], f"close readback: reworded the quote {sentence.item}.", "Changed. I'll read it back to you again.")


def _is(pick, sentence):
    return int(pick["number"]) == sentence.number and (pick.get("item") or f"^c{sentence.number:02d}") == sentence.item


def cut(args, root, vault, record, listing, picked):
    if args.line == closereadback.DECISION:
        return _refused(DECISION_STAYS)
    if args.line not in closereadback.CUTTABLE:
        return _refused("--cut needs --line why or quote.", "Which sentence should I cut, a reason or a quote?")
    sentence, refusal = _find(listing, args.cut, args.line, args.number)
    if refusal is not None:
        return refusal
    if sentence.line == closereadback.QUOTE:
        kept = [p for p in picked if not _is(p, sentence)]
        wrote = sessiongit.write_text(root, _file(root, record.id, "quotes"), json.dumps({"quotes": kept}, indent=2) + "\n")
    else:
        page = pathlib.Path(root) / sentence.page
        wrote = sessiongit.write_text(root, sentence.page, closereadback.cut(page.read_text(encoding="utf-8"), sentence))
    return _done([wrote], f"close readback: cut the {sentence.line} line for {sentence.item}.", "Cut. It won't go on record.")


def pick(ref, root, record, lead, picked, vault):
    capture = record.capture(ref)
    if capture is None:
        return _refused(f"{ref} is not in this session's notes.", "I can't find that in what you said.")
    session = SimpleNamespace(captures=record.captures)
    if not consent.may_quote(capture, session, lead):
        if consent.agreed_but_unconfirmed(capture, session):
            return _refused(f"{ref} is {capture.origin}'s and unverified: {consent.NOT_CONFIRMED}{consent.NOT_CONFIRMED_FIX}",
                            consent.NOT_CONFIRMED)
        return _refused(f"{ref} is {capture.origin}'s, with no quote-yes from them.", NOT_THEIRS)
    number = int(capture.n)
    row = next((r for r in closegate.change_rows(record.text) if r.capture_number and int(r.capture_number) == number), None)
    entry = {"number": number, "words": capture.quote, "item": row.item if row else ""}
    kept = [p for p in picked if int(p["number"]) != number] + [entry]
    wrote = sessiongit.write_text(root, _file(root, record.id, "quotes"), json.dumps({"quotes": kept}, indent=2) + "\n")
    whose = "your" if _is_the_lead(capture, lead) else "their"
    return _done([wrote], f"close readback: picked ^c{number:02d} as a quote.",
                 f"Picked. It goes in the pull request in {whose} words.")


def _is_the_lead(capture, lead):
    handle, names = lead
    return consent.from_the_lead(capture, handle, names) is None
