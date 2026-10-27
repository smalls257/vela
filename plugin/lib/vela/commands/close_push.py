"""`vela close push` and `vela close pr [--prose FILE]`: send the session, then open its pull request (overhaul
Task 12, plan 4.3 and 7.3).

The lead's word to close is the yes for the push and the pull request: nothing asks a second time. What still stops a
send is the gate (a session that isn't ready isn't sent), a reader copy, a host that can't send, and the hard stop on
company material, which `guard` and the pre-commit hook hold whatever the host (Silent Fallback "no hook ran, so
nothing stopped it" is ruled out: the CLI checks first).

`close push`, in order:

1. A reader copy sends nothing (no git, no push, no PR) and says so. A host whose probe (`.vela/host.json`) says it
   can't send gets 7.3's sentence ("I can file the session here, but I can't send it...") before anything is tried:
   promising a send the next step breaks would be worse than saying so.
2. A session sitting on the default branch is moved onto its own `session/...` branch first
   (`move_off_default_branch`, the same move `vela session branch` makes): a pull request can't be opened from the
   branch it goes into, and the default branch is never pushed. Said as one line; nothing is asked.
3. The gate (`close_gate.observe` then `closegate.ready`, the same pair `close finish` composes): a session that isn't
   ready isn't sent.
4. Everything the session changed must be committed: a push sends commits.
5. The push, to the branch the session sits on: with `-u`, or, for an answer session, its challenge's
   branch as it is (the answer lands in the challenge's PR; `gh pr comment`). It leaves `.vela/close/<id>.push.json` (the branch and the head) for
   `close pr`.

`close pr`: when the branch already has an open pull request (`gh pr view` on the branch), the session's body is added to
it as a comment and no second one is opened; the lead is told so. Reviewers from `owner:` fields (the lead's own handle dropped, `vela whoami`; team handles kept as
`org/team`), the body `prbody.body` builds (the sentences and one plain line per item that changed; no capture's words are in it), and
`gh pr create`; for an answer session, `gh pr comment` on the challenge's open PR instead. When `gh` fails, or prints
no URL, the body is saved to `.vela/pr-body.md` and the lead hears one sentence; a PR is never said to exist unless
`gh` printed its URL. When a PR was created and the session wrote `handed_off_pr: pending`, the number replaces
`pending`, committed as `Handoff PR number for <APP-id>` and pushed; if `gh` failed, `pending` stays and W325 says so.

Exit codes. push: 0 pushed; 1 refused (a reader copy, a host that can't send, something uncommitted, the gate); 2 the
push failed (the branch and the retry command printed). pr: 0 the URL printed; 1 refused (not pushed yet) or `gh` failed (the body saved, one sentence); 2 the tool
failed (git, the disk, or the handoff number's push); 3 the lead's handle is unknown (ask once, `vela whoami --set`).
"""
import json
import pathlib
import re
import tempfile
from dataclasses import replace

from vela import closegate, commands, parse, planscope, prbody, privaterecord, say, sessions
from vela.commands import close_gate, whoami
from vela.decisions import settled
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
    push = steps.add_parser("push", help="send the session's branch (a session on the default branch moves to its own "
                                         "branch first); the lead's word to close is the yes")
    push.add_argument("--vault", default=".", help="vault root (default: current directory)")
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


def move_off_default_branch(root, session, lines):
    """A pull request goes from a branch into the default branch, so a session sitting on the default branch is moved
    onto its own `session/...` branch before anything is sent (`commands.session.move_to_own_branch`, the same move
    `vela session branch` makes); the default branch goes back to how it was and is never pushed. An answer session
    sits on its challenge's branch and stays. `lines` takes what the move said. Returns the session on its branch."""
    if session.branch != sessiongit.default_branch(root) or session.answer:
        return session
    from vela.commands import session as sessioncmd
    moved = sessioncmd.move_to_own_branch(root)
    lines += moved.lines
    return find_session(root, PUSH)


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
    from vela.commands import session as sessioncmd  # late: session loads the size reader, which push never needs
    root = pathlib.Path(args.vault).resolve()
    vault, said = None, []
    try:
        can_send(root, PUSH)
        session = move_off_default_branch(root, find_session(root, PUSH), said)
        vault = cli.load_vault(root)
        result = unready(root, vault, session, args) or send(root, vault, session, args)
    except Stop as stop:
        result = stop.result
    except sessioncmd.Stop as stop:
        result = replace(stop.result, command=PUSH)
    except (vaultgit.GitUnavailable, cli.ToolError, OSError) as exc:
        result = say.Result(PUSH, exit=say.FAILED, lines=[say.Line(f"vela close push: {exc}",
                                                                   plain="I couldn't send the session; git didn't "
                                                                         "answer.")])
    result.lines = said + result.lines
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


def send(root, vault, session, args):
    left = uncommitted(root)
    if left:
        what = "Some of this session's changes aren't committed yet"
        # The default mode names the paths for the model; the lead hears what it means for the send.
        raise refused(PUSH, f"vela close push: {what.lower()}: {', '.join(left)}. Commit them (vela close stage --close, "
                            "or vela close finish) and run this again.",
                      "A few of today's changes aren't saved yet, so they wouldn't go. I'll save them, then send.")
    sent = ghcli.push(root, session.branch, track=not session.answer)
    if not sent.ok:
        return say.Result(PUSH, exit=say.FAILED, data={"branch": session.branch, "retry": sent.command}, lines=[
            say.Line(f"vela close push: {sent.command} failed: {sent.why}. Branch: {session.branch}. Retry: "
                     f"{sent.command}",
                     plain=f"I couldn't send it: {trouble(sent.why)}. Shall I try again?")])
    head = vaultgit.git_out(root, "rev-parse", "HEAD")
    from vela import cli
    today, _ = cli.parse_today(args.today)
    pushed = {"version": VERSION, "branch": session.branch, "head": head, "date": today, "answer": session.answer}
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
                      "This session isn't sent yet. I'll send it first.")
    if marker.get("head") != vaultgit.git_out(root, "rev-parse", "HEAD"):
        raise refused(PR, f"vela close pr: {session.branch} has commits since close push; run vela close push "
                          "again so the remote has them.",
                      "Something changed after I sent the session. I'll send it again.")
    return marker


def body_facts(root, vault, session, args):
    """The sentences the lead's model wrote (or the session's summary) and what changed. Nothing else is gathered:
    the checks live in `vela check` and CI."""
    prose = pathlib.Path(args.prose).read_text(encoding="utf-8") if args.prose else ""
    summary = str(parse.split_frontmatter(session.text)[0].get("summary") or "")
    return prbody.Facts(summary=summary, prose=prose,
                        changed=prbody.what_changed(closegate.change_rows(session.text), vault))


def open_pr(root, vault, session, args):
    pushed_marker(root, session)
    before_texts = changes(root)
    found, before = reviewer_handles(root, vault, before_texts, PR)
    text = prbody.body(body_facts(root, vault, session, args))
    with tempfile.TemporaryDirectory(prefix="vela-pr-") as folder:
        body_file = pathlib.Path(folder) / "body.md"
        body_file.write_text(text, encoding="utf-8")
        if session.answer:
            sent = comment_on_challenge(root, session, body_file)
            title = ""
        else:
            title = planscope.titled(vaultgit.plan_scope(root), prbody.title(
                session.record.date, list(session.record.modes), session.record.title,
                decided=len(settled.settled_ids(session.text, vault, session.record.id))))
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

