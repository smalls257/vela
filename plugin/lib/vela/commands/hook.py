"""`vela hook session-start`: what the plugin's SessionStart hook (`plugin/hooks/hooks.json`) runs.

It writes `.vela/hooks-active` with the session id and the time, so `vela where --probe` (and later `close gate`) can
tell a host where plugin hooks run from one where they silently don't. Plugin hooks are documented for Cowork but
reported not to fire there (#27398, #63360), and a hook that didn't run looks exactly like one that passed: a Silent
Fallback for anything that relied on it. The marker turns "didn't run" into something the probe can see. No rule
depends on this hook; the CLI and CI hold every rule either way.

Hook protocol: it reads the hook's JSON on stdin, always exits 0 (a hook failure must never block a session), and
prints nothing on stdout, because SessionStart stdout is added to the model's context and a model would relay it.
Problems go to stderr, which `claude --debug` shows. It writes only in a vault or a published copy (a folder with
`.vela.yaml` or `.vela/`), so a plugin enabled for a whole account never litters other projects.
"""
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

MARKER = ".vela/hooks-active"


def register(sub):
    top = sub.add_parser("hook", help="what the plugin's hooks run; not for typing by hand")
    each = top.add_subparsers(dest="which", required=True)
    start = each.add_parser("session-start", help="leave .vela/hooks-active (session id and time) so the host probe "
                                                  "can see that hooks run here; reads the hook JSON on stdin")
    start.set_defaults(func=cmd_session_start)


def warn(text):
    print(f"vela hook session-start: {text}", file=sys.stderr)


def read_payload(stream):
    try:
        data = json.loads(stream.read() or "{}")
    except ValueError as exc:
        warn(f"the hook input wasn't JSON ({exc}); the marker is written without a session id")
        return {}
    return data if isinstance(data, dict) else {}


def marker_folder(payload):
    return pathlib.Path(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def cmd_session_start(args, out):
    from vela.edge import atomic
    payload = read_payload(sys.stdin)
    root = marker_folder(payload)
    if not ((root / ".vela.yaml").is_file() or (root / ".vela").is_dir()):
        warn(f"{root} is not a vault or a published copy, so no marker was left")
        return 0
    marker = {"session_id": str(payload.get("session_id") or ""), "source": str(payload.get("source") or ""),
              "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        (root / ".vela").mkdir(exist_ok=True)
        atomic.write_atomic(root / MARKER, json.dumps(marker) + "\n")
    except OSError as exc:
        warn(f"couldn't write {root / MARKER}: {exc}; the host probe will report hooks as not running")
    return 0
