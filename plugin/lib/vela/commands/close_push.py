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
   lead, "I'll send this for review to Priya and the identity team. OK?"), the record's capture count, exit 3.
   Nothing the lead owns changes. One machine-local marker is left, `.vela/close/<id>.push-notice.json`, holding that
   count and the branch, because "the yes comes after the notice" can't be checked later without it; `.vela/` is
   never committed.
3. With `--consent ^cN`: the capture exists, is a person's words (not `claude...`), isn't a bare "ok", and is numbered
   above the notice's count (`decisions.consent`, the same checks `apply` uses). A yes with no notice printed for this
   session on this machine is refused the same way: the lead hasn't heard what is sent.
4. Everything the session changed is committed, the record with the yes included: a push sends commits, so an
   uncommitted yes would be quoted in the PR but missing from the branch.
5. The gate (`close_gate.observe` then `closegate.ready`, the same pair `close finish` composes): a session that isn't
   ready isn't sent.
6. The push, to the branch the session sits on: `session/<id>` with `-u`, or, for an answer session, its challenge's
   branch as it is (the answer lands in the challenge's PR). It leaves `.vela/close/<id>.push.json` (the branch, the
   head, the yes) for `close pr`.

`close pr`: reviewers from `owner:` fields (the lead's own handle dropped, `vela whoami`; team handles kept as
`org/team`), the body `prbody.body` builds (the Consent list now lives there, with the push yes added), and
`gh pr create`; for an answer session, `gh pr comment` on the challenge's open PR instead. When `gh` fails, or prints
no URL, the body is saved to `.vela/pr-body.md` and the lead hears one sentence; a PR is never said to exist unless
`gh` printed its URL. When a PR was created and the session wrote `handed_off: "..., PR pending"`, the number replaces
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

from vela import closegate, commands, parse, prbody, say, sessions
from vela.commands import close_gate, whoami
from vela.decisions import consent as consents
from vela.decisions import record as records
from vela.edge import flowstore, ghcli, hostprobe, sessiongit, vaultgit

PUSH, PR = "close push", "close pr"
CLOSE_DIR = ".vela/close"
BODY_FILE = ".vela/pr-body.md"
VERSION = 1
HANDOFF_MESSAGE = "Handoff PR number for {app}"
READER_SENTENCE = "This is a read copy, so close writes your session record and stops. Nothing is committed, pushed or sent."
PENDING = re.compile(r"^(handed_off:.*\bPR )pending(\"?\s*)$", re.M)


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
    if state.get("path") and (root / str(state["path"])).is_file():
        text = (root / str(state["path"])).read_text(encoding="utf-8")
        record, _ = sessions.read("", str(state["path"]), text)
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
                      "This folder is on another branch than the session's, so I haven't sent anything.")
    return Session(record, text, branch)


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
        vault = cli.load_vault(root)
        result = notice(root, vault, session) if not args.consent else send(root, vault, session, args)
    except Stop as stop:
        result = stop.result
    except (vaultgit.GitUnavailable, cli.ToolError, OSError) as exc:
        result = say.Result(PUSH, exit=say.FAILED, lines=[say.Line(f"vela close push: {exc}",
                                                                   plain=f"I couldn't send the session: {exc}")])
    return emit(result, args, out, vault)


def notice(root, vault, session):
    """The send notice and exit 3. The marker holds the capture count the yes must be numbered above."""
    count = records.from_text(session.id, session.record.path, session.text).count
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
                      "it (vela record add), commit it, then run vela close push --consent ^cNN.", plain=said[1])]
    result = say.Result(PUSH, exit=say.NEEDS_LEAD, lines=lines, data={"branch": session.branch, "reviewers": found},
                        needs_lead=[{"ask": "push", "question": said[1], "captures_at_notice": count,
                                     "answer_with": "--consent ^cNN"}])
    return result


def consent_refusal(root, session, ref):
    """The first reason the yes doesn't qualify, or None; and the yes itself."""
    record = records.from_text(session.id, session.record.path, session.text)
    first = consents.a_yes(ref, record)
    if first is not None:
        return first, None
    yes = record.capture(ref)
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
                      f"{what}, so they wouldn't be sent. I'll commit them first.")
    from vela import cli
    today, _ = cli.parse_today(args.today)
    readiness = closegate.ready(vault, session.text, session.id,
                                close_gate.observe(root, vault, session.record, session.text, today))
    if not readiness.ready:
        lines = close_gate.problem_lines(readiness, say.Resolver(vault))
        return say.Result(PUSH, exit=say.REFUSED, lines=[say.Line(
            f"close push: {session.id} isn't ready to send; nothing was pushed.",
            plain="I haven't sent anything: the session isn't ready yet.")] + lines)
    sent = ghcli.push(root, session.branch, track=not session.answer)
    if not sent.ok:
        return say.Result(PUSH, exit=say.FAILED, data={"branch": session.branch, "retry": sent.command}, lines=[
            say.Line(f"vela close push: {sent.command} failed: {sent.why}. Branch: {session.branch}. Retry: "
                     f"{sent.command}",
                     plain=f"I couldn't send the branch {session.branch}. To try again: {sent.command}")])
    head = vaultgit.git_out(root, "rev-parse", "HEAD")
    pushed = {"version": VERSION, "branch": session.branch, "head": head, "consent": f"c{yes.n}",
              "words": yes.quote, "link": f"[[{session.id}#^c{yes.n}]]", "answer": session.answer}
    wrote = [sessiongit.write_text(root, close_file(session.id, "push"), json.dumps(pushed, indent=2) + "\n")]
    plain = ("Sent to the challenge's branch; next, the comment on its pull request." if session.answer
             else "Sent; next, the pull request.")
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
        vault = cli.load_vault(root)
        result = open_pr(root, vault, session, args)
    except Stop as stop:
        result = stop.result
    except (vaultgit.GitUnavailable, cli.ToolError, OSError, ValueError) as exc:
        result = say.Result(PR, exit=say.FAILED, lines=[say.Line(f"vela close pr: {exc}",
                                                                 plain=f"I couldn't open the pull request: {exc}")])
    return emit(result, args, out, vault)


def pushed_marker(root, session):
    marker = read_marker(root, close_file(session.id, "push"))
    if not marker or marker.get("branch") != session.branch:
        raise refused(PR, f"vela close pr: {session.branch} isn't pushed by close push yet; run vela close push first.",
                      "This session isn't sent yet, so there's no pull request to open. I'll send it first.")
    if marker.get("head") != vaultgit.git_out(root, "rev-parse", "HEAD"):
        raise refused(PR, f"vela close pr: {session.branch} has commits since close push; run vela close push "
                          f"--consent ^{marker.get('consent')} again so the remote has them.",
                      "Something was committed after the branch was sent, so I'll send it again first.")
    return marker


def commit_times(root):
    out = vaultgit.git_out(root, "log", "--format=%ct", f"{close_gate.branch_point(root)}..HEAD")
    return [int(t) for t in out.split()]


def body_facts(root, vault, session, marker, before_texts, before, args):
    from vela import cli, ladder, questions, rules
    today, _ = cli.parse_today(args.today)
    readiness = closegate.ready(vault, session.text, session.id,
                                close_gate.observe(root, vault, session.record, session.text, today))
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
        consent=prbody.consent_list(readiness.consent, prbody.push_consent(session.branch, marker.get("words", ""),
                                                                           marker.get("link", ""))),
        changed=prbody.what_changed(rows, vault), voice=prbody.voice_lines(voice, lambda p: titles.get(p, p)),
        kept_on_claude=prbody.kept_on_claude(session.text, vault),
        not_read_back=prbody.not_read_back(decided, vault, prbody.present_people(session.text)),
        overrides=prbody.override_lines(added, vault),
        old_values=prbody.old_value_hits(prbody.old_values(before, vault), texts),
        overdue=prbody.overdue_lines(prbody.overdue_rows(vault, findings)),
        open_questions=prbody.open_question_lines(owed),
        catalog_gaps=prbody.catalog_gap_lines(questions.stats(vault), entries),
        red_check=red, check=check, stage=stage, minutes=prbody.minutes(commit_times(root)))


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
            title = prbody.title(session.record.date, list(session.record.modes), session.record.title)
            sent = ghcli.pr_create(root, session.branch, title, body_file, found)
    data = {"url": sent.url, "number": sent.number, "reviewers": found, "title": title, "command": sent.command}
    if not sent.ok:
        wrote = [sessiongit.write_text(root, BODY_FILE, text)]
        sentence = prbody.SAVED_COMMENT_SENTENCE if session.answer else prbody.SAVED_SENTENCE
        return say.Result(PR, exit=say.REFUSED, wrote=wrote, data={**data, "body_file": BODY_FILE}, lines=[
            say.Line(f"vela close pr: {sent.command} failed: {sent.why}. The body is in {BODY_FILE}; nothing says a "
                     "pull request exists.", plain=sentence)])
    lines = [say.Line(f"{'commented on' if session.answer else 'opened'} {sent.url}",
                      plain=(f"I added the answer to the challenge's pull request: {sent.url}" if session.answer
                             else f"The pull request is open: {sent.url}"))]
    if session.answer:
        return say.Result(PR, data=data, lines=lines)
    return write_pr_number(root, vault, session, sent, before_texts, data, lines)


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
    """`handed_off: "..., PR pending"` on an app page this session changed -> `PR #<n>`, committed and pushed."""
    wrote = []
    for app in vault.apps:
        value = str(app.meta.get("handed_off") or "")
        if app.path not in before_texts or not value.endswith("PR pending"):
            continue
        page = root / app.path
        new = PENDING.sub(lambda m: f"{m.group(1)}#{sent.number}{m.group(2)}", page.read_text(encoding="utf-8"), 1)
        wrote.append(sessiongit.write_text(root, app.path, new))
        sessiongit.commit(root, HANDOFF_MESSAGE.format(app=app.id), [app.path])
        lines.append(say.Line(f"wrote PR #{sent.number} into {app.path} handed_off and committed it",
                              plain=f"{app.meta.get('title') or app.name}'s handoff now names this pull request."))
    if not wrote:
        return say.Result(PR, data=data, lines=lines)
    again = ghcli.push(root, session.branch, track=True)
    if not again.ok:
        lines.append(say.Line(f"vela close pr: {again.command} failed: {again.why}. Retry: {again.command}",
                              plain=f"The pull request is open, but I couldn't send the handoff's number. To try "
                                    f"again: {again.command}"))
        return say.Result(PR, exit=say.FAILED, data=data, wrote=wrote, lines=lines)
    head = vaultgit.git_out(root, "rev-parse", "HEAD")
    marker = read_marker(root, close_file(session.id, "push")) or {}
    wrote.append(sessiongit.write_text(root, close_file(session.id, "push"),
                                       json.dumps({**marker, "head": head}, indent=2) + "\n"))
    return say.Result(PR, data=data, wrote=wrote, lines=lines)

