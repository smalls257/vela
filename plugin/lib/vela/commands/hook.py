"""`vela hook session-start|said|bash|edit|post-edit`: what the plugin's hooks (`plugin/hooks/hooks.json`) run.

`bash` and `edit` are PreToolUse hooks: they print a `permissionDecision` (deny, or ask before a push or a pull
request) with the reason in plain words. The verdicts come from `hookverdict.py`, which judges paths by `guard.py`, so
a hook holds no rule of its own (Distributed Monolith ruled out). `post-edit` is the PostToolUse quick check: it
parses the one page just edited and hands the model what's broken on it, so a stray marker or a broken table is fixed
now instead of at close. A full `vela check` per edit would cost seconds on every edit of a session (Computational
Friction); the close runs it once. None of them is a gate: each rule is already refused by the CLI, which holds where
hooks don't fire (Cowork).

`session-start` writes `.vela/hooks-active` with the session id and the time, so `vela where --probe` (and later
`close gate`) can tell a host where plugin hooks run from one where they silently don't. Plugin hooks are documented
for Cowork but reported not to fire there (#27398, #63360), and a hook that didn't run looks exactly like one that
passed: a Silent Fallback for anything that relied on it. The marker turns "didn't run" into something the probe can
see. No rule depends on this hook; the CLI and CI hold every rule either way.

Hook protocol: each reads the hook's JSON on stdin and always exits 0 (a hook failure must never block a session).
`session-start` prints nothing on stdout, because SessionStart stdout is added to the model's context and a model
would relay it; the others print their decision JSON, or nothing for no opinion. Problems go to stderr, which
`claude --debug` shows. They speak only in a vault or a published copy (a folder with `.vela.yaml` or `.vela/`), so a
plugin enabled for a whole account never litters, or denies `git add` in, the user's other projects.

The vault is found by walking up from the edited file or the command's working folder to the nearest `.vela.yaml`,
stopping at the repo's root (`edge/plans.py`). One docs repo may hold several plans, each in its own folder: Claude
opened at the repo's root and editing a page in `projects/heron/` is guarded by heron's rules, and a folder with no
plan above it stays unguarded.
"""
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

from vela.edge import plans

MARKER = ".vela/hooks-active"


def register(sub):
    top = sub.add_parser("hook", help="what the plugin's hooks run; not for typing by hand")
    each = top.add_subparsers(dest="which", required=True)
    start = each.add_parser("session-start", help="leave .vela/hooks-active (session id and time) so the host probe "
                                                  "can see that hooks run here; reads the hook JSON on stdin")
    start.set_defaults(func=cmd_session_start)
    said_hook = each.add_parser("said", help="UserPromptSubmit: append the person's message to .vela/said/ so `vela record "
                                             "add` can check a capture is words they typed; reads the hook JSON on stdin")
    said_hook.set_defaults(func=cmd_said)
    for name, func, said in (("bash", cmd_bash, "PreToolUse on Bash: deny staging by hand, ask before a push or a PR"),
                             ("edit", cmd_edit, "PreToolUse on Edit/Write: deny a hand-moved state or an edit inside "
                                                "a generated block"),
                             ("post-edit", cmd_post_edit, "PostToolUse on Edit/Write: the edited page's parse "
                                                          "problems, for the model")):
        one = each.add_parser(name, help=said + "; reads the hook JSON on stdin")
        one.set_defaults(func=func)


def warn(text, which="session-start"):
    print(f"vela hook {which}: {text}", file=sys.stderr)


def read_payload(stream, which="session-start"):
    try:
        data = json.loads(stream.read() or "{}")
    except ValueError as exc:
        warn(f"the hook input wasn't JSON ({exc}); " + ("the marker is written without a session id"
                                                        if which == "session-start" else "no opinion given"), which)
        return {}
    return data if isinstance(data, dict) else {}


def marker_folder(payload):
    return pathlib.Path(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def vault_for(folder):
    """The vault or published copy that holds `folder` (the nearest above it, never past the repo's root), or None."""
    return plans.plan_above(folder)


def vaults_started_from(folder):
    """Where session-start leaves its marker: the vault above `folder`; or, when Claude was opened at the root of a repo
    that holds several plans, each of them, so the host probe finds the marker whichever plan the lead then names."""
    above = vault_for(folder)
    if above is not None:
        return [above]
    return plans.plans_in(folder) if plans.repo_root(folder) == folder.resolve() else []


def cmd_session_start(args, out):
    from vela.edge import atomic
    payload = read_payload(sys.stdin)
    folder = marker_folder(payload)
    found = vaults_started_from(folder)
    if not found:
        warn(f"{folder} is not in a vault or a published copy, so no marker was left")
        return 0
    marker = {"session_id": str(payload.get("session_id") or ""), "source": str(payload.get("source") or ""),
              "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    for root in found:
        try:
            (root / ".vela").mkdir(exist_ok=True)
            atomic.write_atomic(root / MARKER, json.dumps(marker) + "\n")
        except OSError as exc:
            warn(f"couldn't write {root / MARKER}: {exc}; the host probe will report hooks as not running")
    return 0


def cmd_said(args, out):
    """UserPromptSubmit: log what the person typed. Prints nothing (UserPromptSubmit stdout reaches the model's
    context), always exits 0, and leaves the log in `.vela/`, which is never staged."""
    from vela import said
    from vela.edge import saidlog, vaultgit
    payload = read_payload(sys.stdin, "said")
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip() or said.harness_injected(prompt):
        return 0
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for root in vaults_started_from(marker_folder(payload)):  # opened at a repo's root, every plan below hears it
        name = str(payload.get("session_id") or "") or vaultgit.current_branch(root) or "session"
        try:
            saidlog.append(root, name, when, prompt)
        except OSError as exc:
            warn(f"couldn't log the message under {root / saidlog.FOLDER}: {exc}; `vela record add` will mark yeses unverified", "said")
    return 0


# --------------------------------------------------------------------------- PreToolUse and PostToolUse


def vault_of(path):
    """The plan folder holding `path` (the nearest parent with `.vela.yaml`, never past the repo's root), or None."""
    start = path.parent
    top = plans.repo_root(start)
    for folder in [start, *start.parents]:
        if (folder / ".vela.yaml").is_file():
            return folder
        if top is not None and folder == top:
            return None
    return None


def answer(out, verdict, payload=None):
    """Print a PreToolUse decision. No verdict prints nothing, which leaves the call to the normal permission flow.
    An "ask" is dropped when the person runs with bypassed permissions: they chose not to be prompted, so the hook
    doesn't prompt either. A deny still denies: it guards the plan, not the person's attention."""
    if verdict is not None and verdict.decision == "ask" and (payload or {}).get("permission_mode") == "bypassPermissions":
        return 0
    if verdict is not None:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": verdict.decision,
                                                 "permissionDecisionReason": verdict.reason},
                          "vela": {"forbidden": verdict.forbidden}}), file=out)
    return 0


def cmd_bash(args, out):
    from vela import hookverdict
    payload = read_payload(sys.stdin, "bash")
    command = (payload.get("tool_input") or {}).get("command") if payload else None
    if not isinstance(command, str):
        return 0
    folder = marker_folder(payload)
    if vault_for(folder) is not None:
        return answer(out, hookverdict.bash_verdict(command), payload)
    roots = plan_roots_around(folder) if "git" in command else []
    if not roots:
        return 0
    return answer(out, hookverdict.bash_verdict(command, str(folder.resolve()), roots, staged_in(folder, command)), payload)


def staged_in(folder, command):
    """Absolute paths the index holds, read only for a command that might commit; None when git cannot say (the verdict
    then treats the index as holding a plan's files: a hook that cannot look does not wave a commit through)."""
    from vela.edge import stagegit, vaultgit
    if "commit" not in command:
        return ()
    top = plans.repo_root(folder)
    try:
        return [str(top / path) for path in stagegit.staged_paths_in_repo(top) + stagegit.staged_deletions_in_repo(top)]
    except vaultgit.GitUnavailable as exc:
        warn(f"couldn't read the index ({exc}); a commit here is treated as holding a plan's files", "bash")
        return None


def plan_roots_around(folder):
    """Absolute folders of the plans in the repo `folder` sits in, when no plan is above it: a `git add` here can reach
    them, but the owner's files outside every plan are the owner's own business. [] outside a repo or with no plans."""
    top = plans.repo_root(folder)
    return [str(p) for p in plans.plans_in(top)] if top is not None else []


def edited_file(payload):
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(raw, str) or not raw:
        return None
    path = pathlib.Path(raw)
    return path if path.is_absolute() else marker_folder(payload) / path


def read_text(path, which):
    """The file's text; None when it doesn't exist yet, or (said on stderr) can't be read."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        warn(f"couldn't read {path}: {exc}; no opinion given", which)
        return None


def text_after(tool, tool_input, before):
    from vela import hookverdict
    if tool == "Write":
        content = tool_input.get("content")
        return content if isinstance(content, str) else None
    if before is None:
        return None
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    return hookverdict.apply_edits(before, [e for e in edits if isinstance(e, dict)] if isinstance(edits, list) else [])


def cmd_edit(args, out):
    from vela import hookverdict
    payload = read_payload(sys.stdin, "edit")
    path = edited_file(payload) if payload else None
    if path is None or path.suffix != ".md" or vault_of(path) is None:
        return 0
    before = read_text(path, "edit")
    after = text_after(str(payload.get("tool_name") or ""), payload.get("tool_input") or {}, before)
    return answer(out, hookverdict.edit_verdict(before, after))


def cmd_post_edit(args, out):
    from vela import parse
    payload = read_payload(sys.stdin, "post-edit")
    path = edited_file(payload) if payload else None
    root = vault_of(path) if path is not None and path.suffix == ".md" else None
    text = read_text(path, "post-edit") if root is not None else None
    if text is None:
        return 0
    page = parse.parse_page(path.relative_to(root).as_posix(), text)
    if not page.errors:
        return 0
    title = str(page.meta.get("title") or page.path) if isinstance(page.meta, dict) else page.path
    problems = "; ".join(f"{e.code} line {e.line}: {e.message} {e.fix}".strip() for e in page.errors)
    said = (f"vela quick check of {title} ({page.path}): {len(page.errors)} problem"
            f"{'s' if len(page.errors) != 1 else ''} to fix before going on: {problems}")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": said}}), file=out)
    return 0
