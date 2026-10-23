"""`vela close push [--consent ^cN]` and `vela close pr [--prose FILE]`: send the session after a recorded yes, then
open its pull request (overhaul Task 12, plan 4.3 and 7.3).

One confirmation stays before anything leaves the machine: the push and the pull request are the only steps that do,
and a hard stop forbids sending company material without consent. A yes only happens in conversation, so code can't
prove it; what code can do is refuse to send without one on record, numbered after the notice, and put the quoted words
in the PR. That makes this a Sensor, not a Shield, said plainly (plan 4.3). The CLI refuses first, so a hook that didn't
fire in Cowork can't let a push through: the Silent Fallback "no hook ran, so nothing asked" is ruled out here, where
it's checked whatever the host.

`close push`, in order:

1. A reader copy sends nothing (no git, no push, no PR) and says so. A host whose probe (`.vela/host.json`) says it
   can't send gets 7.3's sentence ("I can file the session here, but I can't send it...") before any notice: telling
   the lead what will be sent when it can't be sent would be a promise the next step breaks.
2. Without `--consent`: the send notice ("I'll push `session/<id>` and open a pull request for <reviewers>"; for the
   lead, "I'll send this for review to Ines and the payments team. OK?"), the record's capture count, exit 3.
   Nothing the lead owns changes. One machine-local marker is left, `.vela/close/<id>.push-notice.json`, holding that
   count and the branch, because "the yes comes after the notice" can't be checked later without it; `.vela/` is
   never committed.
3. With `--consent ^cN`: the capture exists, is the lead's own words (its origin their `vela whoami` handle; anyone
   else's, an email address included, is said as theirs), isn't a bare "ok", and is numbered
   above the notice's count (`decisions.consent`, the same checks `apply` uses). A yes with no notice printed for this
   session on this machine is refused the same way: the lead hasn't heard what is sent.
4. Everything the session changed is committed, the record with the yes included: a push sends commits, so an
   uncommitted yes would be quoted in the PR but missing from the branch.
5. The gate (`close_gate.observe` then `closegate.ready`, the same pair `close finish` composes): a session that isn't
   ready isn't sent.
6. The push, to the branch the session sits on (any branch but the default one: a pull request can't be opened from the
   branch it goes into, so a session on main is told so and offered `vela session branch`, after the lead's yes): with
   `-u`, or, for an answer session, its challenge's
   branch as it is (the answer lands in the challenge's PR). It leaves `.vela/close/<id>.push.json` (the branch, the
   head, the yes) for `close pr`.

`close pr`: when the branch already has an open pull request (`gh pr view` on the branch), the session's body is added to
it as a comment and no second one is opened; the lead is told so. Reviewers from `owner:` fields (the lead's own handle dropped, `vela whoami`; team handles kept as
`org/team`), the body `prbody.body` builds (its Decisions are the pages' receipts, its push line the day of the lead's yes; no capture's words are in it), and
`gh pr create`; for an answer session, `gh pr comment` on the challenge's open PR instead. When `gh` fails, or prints
no URL, the body is saved to `.vela/pr-body.md` and the lead hears one sentence; a PR is never said to exist unless
`gh` printed its URL. When a PR was created and the session wrote `handed_off_pr: pending`, the number replaces
`pending`, committed as `Handoff PR number for <APP-id>` and pushed; if `gh` failed, `pending` stays and W325 says so.

Exit codes. push: 0 pushed; 1 refused (a reader copy, a host that can't send, the yes doesn't qualify, something
uncommitted, the gate); 2 the push failed (the branch and the retry command printed); 3 the yes is needed (the notice
printed). pr: 0 the URL printed; 1 refused (not pushed yet) or `gh` failed (the body saved, one sentence); 2 the tool
failed (git, the disk, or the handoff number's push); 3 the lead's handle is unknown (ask once, `vela whoami --set`).
"""
import json
import pathlib
import re
import tempfile
from dataclasses import replace

from vela import closegate, commands, parse, planscope, prbody, privaterecord, say, sessions
from vela.commands import close_gate, whoami
from vela.decisions import consent as consents
from vela.decisions import record as records
from vela.edge import flowstore, ghcli, hostprobe, sessiongit, vaultgit

PUSH, PR = "close push", "close pr"
CLOSE_DIR = ".vela/close"
BODY_FILE = ".vela/pr-body.md"
VERSION = 1
HANDOFF_MESSAGE = "Handoff PR number for {app}"
READER_SENTENCE = "This is your copy, so close writes your session record and stops. Nothing is committed, pushed or sent."
PENDING = re.compile(r"^(handed_off_pr:[ \t]*)pending([ \t]*)$", re.M)


class Stop(Exception):
    def __init__(self, result):
        super().__init__(result.command)
        self.result = result


def register_close(steps):
    push = steps.add_parser("push", help="send the session's branch, after the lead's yes to the send notice: without "
                                         "--consent, print the notice and exit 3")
    push.add_argument("--vault", default=".", help="vault root (default: current directory)")
    push.add_argument("--consent", default="", metavar="^cN",
                      help="the capture holding the lead's yes, numbered after the notice this command printed")
    push.add_argument("--today", help="the date the gate judges by, YYYY-MM-DD (default: system date)")
    say.add_output_flags(push)
    push.set_defaults(func=cmd_push)
    pr = steps.add_parser("pr", help="open the pushed session's pull request (an answer session: comment on its "
                                     "challenge's PR); on a gh failure, save the body to .vela/pr-body.md")
    pr.add_argument("--vault", default=".", help="vault root (default: current directory)")
    pr.add_argument("--prose", metavar="FILE", help="the two or three sentences a reviewer reads first")
    pr.add_argument("--today", help="the date check is judged by, YYYY-MM-DD (default: system date)")
    say.add_output_flags(pr)
    pr.set_defaults(func=cmd_pr)


# ------------------------------------------------------------------ shared

def refused(command, text, plain):
    return Stop(say.Result(command, exit=say.REFUSED, lines=[say.Line(text, plain=plain)]))


def failed(command, text, plain):
    return Stop(say.Result(command, exit=say.FAILED, lines=[say.Line(text, plain=plain)]))


def close_file(record_id, suffix):
    return f"{CLOSE_DIR}/{record_id}.{suffix}.json"


class Session:
    """The session being sent: its record (open or already closed by `close finish`), branch and modes."""

    def __init__(self, record, text, branch):
        self.record, self.text, self.branch = record, text, branch

    @property
    def id(self):
        return self.record.id

    @property
    def part(self):
        """Which part of the session's notes this machine holds: the part a committed citation names."""
        return privaterecord.part_of(self.text)

    @property
    def answer(self):
        return "answer" in self.record.modes

    @property
    def challenged(self):
        found = re.match(r"^Answer: (\S+)$", self.record.title or "")
        return found.group(1) if found else ""


def find_session(root, command):
    """The session `.vela/session.json` names (its record may be closed by now), else the one open record here. The
    branch is the one the session sits on, and HEAD must be on it: pushing another branch would send the wrong work."""
    try:
        state = sessiongit.read_json(root, sessiongit.STATE_FILE) or {}
    except ValueError as exc:
        raise failed(command, f"vela {command}: {exc}", f"I couldn't read which session this is: {exc}") from exc
    record, text = None, ""
    if state.get("stub") and (root / str(state["stub"])).is_file():
        record, _ = sessions.read("", str(state["stub"]), (root / str(state["stub"])).read_text(encoding="utf-8"))
        text = sessiongit.private_text(root, record.id) if record is not None else ""
        if text is None:
            missing = str(sessiongit.PrivateMissing(record.id))
            raise failed(command, f"vela {command}: {missing}", missing)
    if record is None:
        found, text, early = close_gate.open_record(root)
        if early is not None:
            raise Stop(replace(early, command=command))
        record = found
    current = sessiongit.current_branch(root)
    branch = str(state.get("branch") or "") if state.get("id") == record.id else ""
    branch = branch or current or ""
    if not current or current != branch:
        raise refused(command, f"vela {command}: HEAD is on {current or 'no branch'}, but {record.id} is on {branch}; "
                               f"switch to {branch} first (vela session open --switch).",
                      "This folder has other work open, not this session, so I haven't sent anything. Shall I "
                      "switch back to it?")
    return Session(record, text, branch)


def refuse_default_branch(root, session, command):
    """A pull request goes from a branch into the default branch, so a session sitting on the default branch has nothing
    to open one from. Said in plain words with the way out, which is the lead's yes: moving the session's commits to a
    new branch changes where the work lives. Nothing is committed to main and nothing is pushed."""
    default = sessiongit.default_branch(root)
    if session.branch != default or session.answer:
        return
    question = (f"This session is on {default}, and a review needs its own branch, so I haven't sent anything. Want me "
                f"to move today's work onto a new branch for the review? {default.capitalize()} goes back to how it "
                "was before.")
    raise Stop(say.Result(command, exit=say.REFUSED, lines=[say.Line(
        f"vela {command}: {session.id} is on {default}, and a pull request can't be opened from {default} into itself; "
        f"nothing was pushed. With the lead's yes, run vela session branch to move the session's commits onto "
        f"session/{session.id}, then run close push again.", plain=question)],
        needs_lead=[{"ask": "move to a branch", "question": question, "answer_with": "vela session branch"}]))


def can_send(root, command):
    """Refuse first in a reader copy, or on a host whose probe says sending fails (plan 7.3)."""
    if sessiongit.is_read_copy(root):
        raise refused(command, f"vela {command}: a reader copy: no git runs here, nothing is pushed or sent.",
                      READER_SENTENCE)
    host = hostprobe.read_json(root / hostprobe.HOST_FILE)
    if host:
        row, sentence = hostprobe.stance(host)
        if row != "everything":
            raise refused(command, f"vela {command}: this host can't send ({row}, from {hostprobe.HOST_FILE}). "
                                   f"{sentence}", sentence)


def own_handle(root, command):
    found = whoami.find_handle(root)
    if found.exit == say.NEEDS_LEAD:
        raise Stop(replace(found, command=command))
    return found.data["handle"]


def changes(root):
    """({path: text at the branch point}, the vault at the branch point)."""
    return flowstore.changed_files(root, since=close_gate.branch_point(root))


def reviewer_handles(root, vault, before_texts, command):
    before = close_gate.vault_before(vault, before_texts)
    return prbody.reviewers(prbody.owner_fields(vault, before, set(before_texts)), own_handle(root, command)), before


def read_marker(root, rel):
    try:
        return sessiongit.read_json(root, rel)
    except ValueError:
        return None


def uncommitted(root):
    """Tracked files with changes not committed, staged or not, vault-relative (`.vela/` is never committed)."""
    out = vaultgit.git_out(root, "diff", "--name-only", "--relative", "HEAD")
    return [line for line in out.splitlines() if line.strip()]


def emit(result, args, out, vault=None):
    resolver = say.Resolver(vault) if say.mode_of(args) == "for-lead" else None
    return commands.emit(result, args, out, resolver)


# ------------------------------------------------------------------ close push

def cmd_push(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    vault = None
    try:
        can_send(root, PUSH)
        session = find_session(root, PUSH)
        refuse_default_branch(root, session, PUSH)
        vault = cli.load_vault(root)
        if not args.consent:
            # Readiness first: asking "OK?" for a session that can't go yet asks the lead for a yes that is then
            # refused (the October 14 voice audit, row 133).
            result = unready(root, vault, session, args) or notice(root, vault, session)
        else:
            result = send(root, vault, session, args)
    except Stop as stop:
        result = stop.result
    except (vaultgit.GitUnavailable, cli.ToolError, OSError) as exc:
        result = say.Result(PUSH, exit=say.FAILED, lines=[say.Line(f"vela close push: {exc}",
                                                                   plain="I couldn't send the session; git didn't "
                                                                         "answer.")])
    return emit(result, args, out, vault)


def unready(root, vault, session, args):
    """The refusal when the gate says the session can't be sent yet, or None. Said in the gate's own grouped words."""
    from vela import cli
    today, _ = cli.parse_today(args.today)
    readiness = closegate.ready(vault, session.text, session.id,
                                close_gate.observe(root, vault, session.record, session.text, today),
                                session.part)
    if readiness.ready:
        return None
    lines = close_gate.problem_lines(readiness, say.Resolver(vault))
    return say.Result(PUSH, exit=say.REFUSED, answer=f"I haven't sent anything. {close_gate.answer_words(readiness)}",
                      lines=[say.Line(f"close push: {session.id} isn't ready to send; nothing was pushed.",
                                      plain="")] + lines)


def trouble(why):
    """What a failed push or gh call means, in words the lead can act on; git's own words stay in the default line."""
    said = (why or "").lower()
    if any(w in said for w in ("could not resolve host", "unable to access", "timed out", "no answer", "network")):
        return "the network didn't answer"
    if any(w in said for w in ("rejected", "non-fast-forward", "fetch first")):
        return "the shared copy has changes this one doesn't have yet"
    if any(w in said for w in ("permission denied", "authentication", "auth login", "403", "401")):
        return "GitHub didn't accept my sign-in"
    if "isn't installed" in said:
        return "GitHub's tool isn't installed on this machine"
    return "git didn't take it"


def notice(root, vault, session):
    """The send notice and exit 3. The marker holds the capture count the yes must be numbered above."""
    count = records.from_text(session.id, privaterecord.private_path(session.id), session.text).count
    found, _ = reviewer_handles(root, vault, changes(root), PUSH)
    if session.answer:
        said = (f"I'll push `{session.branch}` and add a comment on the challenge's pull request.",
                "I'll send this answer to the challenge's pull request. OK?")
    else:
        names = prbody.reviewer_words(found)
        said = (f"I'll push `{session.branch}` and open a pull request for "
                f"{', '.join('@' + h for h in found) or 'no reviewer (nobody but you owns what changed)'}.",
                f"I'll send this for review to {names}. OK?" if names else "I'll send this for review. OK?")
    marker = {"version": VERSION, "branch": session.branch, "captures": count, "reviewers": found}
    sessiongit.write_text(root, close_file(session.id, "push-notice"), json.dumps(marker, indent=2) + "\n")
    s = "" if count == 1 else "s"
    lines = [say.Line(f"{said[0]}\nThe record holds {count} capture{s} at this notice; capture the lead's yes after "
                      "it (vela record add), then run vela close push --consent ^cNN.", plain=said[1])]
    result = say.Result(PUSH, exit=say.NEEDS_LEAD, lines=lines, data={"branch": session.branch, "reviewers": found},
                        needs_lead=[{"ask": "push", "question": said[1], "captures_at_notice": count,
                                     "answer_with": "--consent ^cNN"}])
    return result


def consent_refusal(root, session, ref):
    """The first reason the yes doesn't qualify, or None; and the yes itself."""
    record = records.from_text(session.id, privaterecord.private_path(session.id), session.text)
    first = consents.a_yes(ref, record)
    if first is not None:
        return first, None
    yes = record.capture(ref)
    not_theirs = consents.from_the_lead(yes, own_handle(root, PUSH), sessiongit.lead_names(root))
    if not_theirs is not None:
        return not_theirs, yes
    marker = read_marker(root, close_file(session.id, "push-notice"))
    if not marker or marker.get("branch") != session.branch or not isinstance(marker.get("captures"), int):
        late = consents.after_send_notice(yes, int(yes.n))
        return replace(late, fix="Run vela close push without --consent first: no send notice was printed for this "
                                 "session's branch on this machine. Then capture the lead's yes after it."), yes
    return consents.after_send_notice(yes, marker["captures"]), yes


def send(root, vault, session, args):
    refusal, yes = consent_refusal(root, session, args.consent)
    if refusal is not None:
        return say.Result(PUSH, exit=say.REFUSED, refusals=[refusal])
    left = uncommitted(root)
    if left:
        what = ("The record with your yes isn't committed yet" if session.record.path in left
                else "Some of this session's changes aren't committed yet")
        # The default mode names the paths for the model; the lead hears what it means for the send.
        raise refused(PUSH, f"vela close push: {what.lower()}: {', '.join(left)}. Commit them (vela close stage --close, "
                            "or vela close finish) and run this again.",
                      "A few of today's changes aren't saved yet, so they wouldn't go. I'll save them, then send.")
    stopped = unready(root, vault, session, args)
    if stopped is not None:
        return stopped
    sent = ghcli.push(root, session.branch, track=not session.answer)
    if not sent.ok:
        return say.Result(PUSH, exit=say.FAILED, data={"branch": session.branch, "retry": sent.command}, lines=[
            say.Line(f"vela close push: {sent.command} failed: {sent.why}. Branch: {session.branch}. Retry: "
                     f"{sent.command}",
                     plain=f"I couldn't send it: {trouble(sent.why)}. Shall I try again?")])
    head = vaultgit.git_out(root, "rev-parse", "HEAD")
    from vela import cli
    today, _ = cli.parse_today(args.today)
    pushed = {"version": VERSION, "branch": session.branch, "head": head, "consent": f"c{yes.n}",
              "date": today, "answer": session.answer,
              "link": privaterecord.citation(session.id, session.part, int(yes.n))}
    wrote = [sessiongit.write_text(root, close_file(session.id, "push"), json.dumps(pushed, indent=2) + "\n")]
    plain = ("Sent. Now I'll add your answer to the challenge." if session.answer
             else "Sent. Now I'll open the review.")
    return say.Result(PUSH, wrote=wrote, data={"branch": session.branch, "head": head},
                      lines=[say.Line(f"pushed {session.branch} ({head[:7]}) with {sent.command}", plain=plain)])


# ------------------------------------------------------------------ close pr

def cmd_pr(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    vault = None
    try:
        if sessiongit.is_read_copy(root):
            raise refused(PR, "vela close pr: a reader copy: no pull request is opened from here.", READER_SENTENCE)
        session = find_session(root, PR)
        refuse_default_branch(root, session, PR)
        vault = cli.load_vault(root)
        result = open_pr(root, vault, session, args)
    except Stop as stop:
        result = stop.result
    except (vaultgit.GitUnavailable, cli.ToolError, OSError, ValueError) as exc:
        result = say.Result(PR, exit=say.FAILED, lines=[say.Line(f"vela close pr: {exc}",
                                                                 plain="I couldn't open the review; GitHub didn't "
                                                                       "answer.")])
    return emit(result, args, out, vault)


def pushed_marker(root, session):
    marker = read_marker(root, close_file(session.id, "push"))
    if not marker or marker.get("branch") != session.branch:
        raise refused(PR, f"vela close pr: {session.branch} isn't pushed by close push yet; run vela close push first.",
                      # Sending needs the lead's own yes (close push's notice), so this asks; it never promises.
                      "This session isn't sent yet. Shall I send it for review?")
    if marker.get("head") != vaultgit.git_out(root, "rev-parse", "HEAD"):
        raise refused(PR, f"vela close pr: {session.branch} has commits since close push; run vela close push "
                          f"--consent ^{marker.get('consent')} again so the remote has them.",
                      "Something changed after I sent the session. Shall I send it again?")
    return marker


def stub_meta(root, session):
    """The committed header of the session: where each part's fingerprint is kept."""
    return privaterecord.stub_meta((root / privaterecord.stub_path(session.id)).read_text(encoding="utf-8"))


def body_facts(root, vault, session, marker, before_texts, before, args):
    from vela import cli, ladder, questions, rules
    today, _ = cli.parse_today(args.today)
    findings = list(rules.check(vault, today))
    changed = set(before_texts)
    titles = {p.path: str(p.meta.get("title") or p.name) for p in vault.pages}
    rows = closegate.change_rows(session.text)
    decided = [r.item for r in rows if r.after == closegate.CONSENT_STATE]
    owed = [(d.copy.entry.question, d.copy.subject.title) for d in questions.dispositions(vault)
            if d.pending and d.copy.subject.page is not None and d.copy.subject.page.path in changed]
    entries = {e.id: e.question for e in vault.catalog.entries}
    added = [(name, o) for key, (name, o) in sorted(closegate.override_scopes(vault).items(), key=lambda p: str(p[0]))
             if key not in closegate.override_scopes(before)]
    stage = [prbody.stage_line(str(app.meta.get("title") or app.name), reached, app.meta.get("stage"))
             for app in vault.apps for reached in [ladder.ahead_of_stage(vault, app)] if reached]
    check = [prbody.check_line(findings, len(vault.pages))]
    red = ""
    if session.answer and session.challenged:
        still = any(f.code == "E316" and session.challenged in f.message for f in findings)
        check.append(prbody.answer_check(session.challenged, still))
    if "challenge" in session.record.modes:
        ident = prbody.topic_of(session.record.title)
        state = closegate.states(vault).get(ident, "")
        red = prbody.red_check(ident, vault.name_of(ident), state)
    texts = {p.path: p.text for p in vault.pages}
    voice = read_marker(root, close_file(session.id, "voice"))
    prose = pathlib.Path(args.prose).read_text(encoding="utf-8") if args.prose else ""
    summary = str(parse.split_frontmatter(session.text)[0].get("summary") or "")
    return prbody.Facts(
        summary=summary, prose=prose,
        decisions=prbody.decision_lines(vault, session.id), push_line=prbody.push_words(marker.get("date", "")),
        in_their_words=prbody.in_their_words(close_gate.read_picked(root, session.id), vault),
        fingerprint_note=prbody.fingerprint_notes(stub_meta(root, session), session.part),
        changed=prbody.what_changed(rows, vault, session.id, session.part), voice=prbody.voice_lines(voice, lambda p: titles.get(p, p)),
        kept_on_claude=prbody.kept_on_claude(session.text, vault),
        not_read_back=prbody.not_read_back(decided, vault, prbody.present_people(session.text)),
        overrides=prbody.override_lines(added, vault),
        old_values=prbody.old_value_hits(prbody.old_values(before, vault), texts),
        overdue=prbody.overdue_lines(prbody.overdue_rows(vault, findings)),
        open_questions=prbody.open_question_lines(owed),
        catalog_gaps=prbody.catalog_gap_lines(questions.stats(vault), entries),
        red_check=red, check=check, stage=stage)


def open_pr(root, vault, session, args):
    marker = pushed_marker(root, session)
    before_texts = changes(root)
    found, before = reviewer_handles(root, vault, before_texts, PR)
    text = prbody.body(body_facts(root, vault, session, marker, before_texts, before, args))
    with tempfile.TemporaryDirectory(prefix="vela-pr-") as folder:
        body_file = pathlib.Path(folder) / "body.md"
        body_file.write_text(text, encoding="utf-8")
        if session.answer:
            sent = comment_on_challenge(root, session, body_file)
            title = ""
        else:
            title = planscope.titled(vaultgit.plan_scope(root), prbody.title(
                session.record.date, list(session.record.modes), session.record.title))
            sent = add_to_open_pr(root, session, body_file)
            if sent is None:
                sent = ghcli.pr_create(root, session.branch, title, body_file, found,
                                       base=sessiongit.default_branch(root))
    added = sent.added
    data = {"url": sent.url, "number": sent.number, "reviewers": found, "title": title, "command": sent.command,
            "added_to_open": added}
    if not sent.ok:
        wrote = [sessiongit.write_text(root, BODY_FILE, text)]
        sentence = prbody.SAVED_COMMENT_SENTENCE if session.answer else prbody.SAVED_SENTENCE
        return say.Result(PR, exit=say.REFUSED, wrote=wrote, data={**data, "body_file": BODY_FILE}, lines=[
            say.Line(f"vela close pr: {sent.command} failed: {sent.why}. The body is in {BODY_FILE}; nothing says a "
                     "pull request exists.", plain=sentence)])
    lines = [pr_line(session, sent, data["added_to_open"])]
    if session.answer:
        return say.Result(PR, data=data, lines=lines)
    return write_pr_number(root, vault, session, sent, before_texts, data, lines)


def pr_line(session, sent, added):
    if session.answer:
        return say.Line(f"commented on {sent.url}", plain=f"I added the answer to the challenge's pull request: {sent.url}")
    if added:
        return say.Line(f"{session.branch} already has an open pull request; added this session to it: {sent.url}",
                        plain=f"This branch already has a review open, so I added today's session to it instead of "
                              f"opening another: {sent.url}")
    return say.Line(f"opened {sent.url}", plain=f"The pull request is open: {sent.url}")


def add_to_open_pr(root, session, body_file):
    """None when the branch has no open pull request. Otherwise the session's body goes on it as a comment, and the
    result is a `ghcli.Sent` for that pull request (its own URL and number), or the failure of the lookup or the comment.
    A second pull request for the same branch is never opened."""
    found, why = ghcli.open_pr_on(root, session.branch)
    command = f"gh pr view {session.branch} --json number,url,state"
    if why:
        return ghcli.Sent(False, command, why)
    if found is None:
        return None
    said = ghcli.pr_comment(root, found["number"], body_file)
    if not said.ok:
        return said
    return ghcli.Sent(True, said.command, url=found.get("url") or said.url, number=int(found["number"]), added=True)


def comment_on_challenge(root, session, body_file):
    found, why = ghcli.open_prs_for(root, session.branch)
    command = f"gh pr list --head {session.branch} --state open"
    if found is None:
        return ghcli.Sent(False, command, why)
    if len(found) != 1:
        return ghcli.Sent(False, command, f"{len(found)} open pull requests have {session.branch} as their head, "
                                          "not one; an answer is never sent to a guessed PR")
    return ghcli.pr_comment(root, found[0].get("number"), body_file)


def write_pr_number(root, vault, session, sent, before_texts, data, lines):
    """`handed_off_pr: pending` on an app page this session changed -> the number, committed and pushed."""
    wrote = []
    for app in vault.apps:
        if app.path not in before_texts or str(app.meta.get("handed_off_pr")) != "pending":
            continue
        page = root / app.path
        new = PENDING.sub(lambda m: f"{m.group(1)}{sent.number}{m.group(2)}", page.read_text(encoding="utf-8"), 1)
        wrote.append(sessiongit.write_text(root, app.path, new))
        sessiongit.commit(root, HANDOFF_MESSAGE.format(app=app.id), [app.path])
        lines.append(say.Line(f"wrote PR #{sent.number} into {app.path} handed_off_pr and committed it",
                              plain=f"{app.meta.get('title') or app.name}'s handoff now names this pull request."))
    if not wrote:
        return say.Result(PR, data=data, lines=lines)
    again = ghcli.push(root, session.branch, track=True)
    if not again.ok:
        lines.append(say.Line(f"vela close pr: {again.command} failed: {again.why}. Retry: {again.command}",
                              plain=f"The review is open, but I couldn't link it from the handoff: "
                                    f"{trouble(again.why)}. Shall I try again?"))
        return say.Result(PR, exit=say.FAILED, data=data, wrote=wrote, lines=lines)
    head = vaultgit.git_out(root, "rev-parse", "HEAD")
    marker = read_marker(root, close_file(session.id, "push")) or {}
    wrote.append(sessiongit.write_text(root, close_file(session.id, "push"),
                                       json.dumps({**marker, "head": head}, indent=2) + "\n"))
    return say.Result(PR, data=data, wrote=wrote, lines=lines)

