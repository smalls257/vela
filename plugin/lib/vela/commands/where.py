"""`vela where` and `vela where --probe`.

Plain `where` is `cli.cmd_where`: which vela program a skill would run, and why other places were passed over.

`where --probe` (plan 7.1-7.3) asks what this host gives a session, one row per assumption the skills make, each
`yes`, `no` or `couldn't tell` with what it means, and writes `.vela/host.json` for `session start`, `close gate` and
`close push` to read. It exists because a host's gaps used to show up only when a step failed at push (a Black Box):
the probe is the sensor, so the session can say at the start "close this in Claude Code" instead of failing at the end.
The skill passes what the host expanded (`--plugin-root`, `--skill-dir`) and whether its one `!` line ran
(`--injection`), because only the skill can see those.

Exit codes: 0 everything a session needs works; 1 something it needs is missing or couldn't be told, each named;
2 the probe itself failed (its record couldn't be written).
"""
import os
import pathlib
import time
from datetime import datetime, timezone


def register(sub):
    from vela import cli, say  # cli builds the parser, so it is loaded by the time this runs
    where = sub.add_parser("where", help="which vela program a skill would run, and why other places were passed "
                                         "over; with --probe, what this host gives a session")
    where.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    where.add_argument("--plugin-root", default=None, help="the value ${CLAUDE_PLUGIN_ROOT} had when the skill loaded")
    where.add_argument("--skill-dir", default=None, help="the value ${CLAUDE_SKILL_DIR} had when the skill loaded")
    where.add_argument("--probe", action="store_true",
                       help="check git, network, gh, Python, hooks and injection here, and write .vela/host.json")
    where.add_argument("--injection", choices=("yes", "no"), default=None,
                       help="with --probe: whether the skill's ! line ran before the skill started")
    where.add_argument("--timeout", type=float, default=None,
                       help="with --probe: seconds the network and gh checks wait (default 10)")
    say.add_output_flags(where)  # --json and --for-lead apply to --probe
    where.set_defaults(func=cmd_where, plain_where=cli.cmd_where)


def cmd_where(args, out):
    if not args.probe:
        args.plugin_root, args.skill_dir = args.plugin_root or "", args.skill_dir or ""
        return args.plain_where(args, out)
    return cmd_probe(args, out)


def cmd_probe(args, out):
    from vela import cli, commands, say
    from vela.edge import hostprobe
    root = pathlib.Path(args.vault).resolve()
    timeout = args.timeout if args.timeout is not None else hostprobe.TIMEOUT
    checked = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # The skill passing any of these means a Claude session ran the probe, so a hook that left no marker is a "no".
    in_session = bool(os.environ.get("CLAUDECODE")) or any(
        value is not None for value in (args.plugin_root, args.skill_dir, args.injection))
    try:
        rows, host = hostprobe.gather(root, args.plugin_root, args.skill_dir, args.injection, timeout, time.time(),
                                      checked, pathlib.Path.home(), in_session)
        wrote = hostprobe.write_host(root, host)
    except hostprobe.ProbeFailed as exc:
        raise cli.ToolError(f"where --probe: {exc}. Nothing was recorded about this host.") from exc
    gaps = hostprobe.missing(rows, host["reader"])
    row_name, said = hostprobe.stance(host)
    # The stance is the answer; the lead hears only the rows that don't work (the 14 October voice audit, row 213),
    # and only where the stance leaves the reason open: with no git, or in a reader's copy, the stance already says
    # why, and the git, network and gh rows under it would only repeat it (row 216). The skill's folder, the
    # plugin's folder and the ! line are the skill's plumbing, never needed, so never heard (row 217).
    heard = set(gaps) if row_name in ("everything", "no-send") else set()
    result = say.Result("where --probe", exit=say.REFUSED if gaps else say.DONE, wrote=[wrote], answer=said)
    for row in rows:
        result.lines.append(say.Line(f"{row.key}: {row.answer}: {row.meaning}" + (f" ({row.detail})" if row.detail else ""),
                                     row.meaning if row.key in heard and row.answer != hostprobe.YES else ""))
    if gaps:
        result.lines.append(say.Line(f"missing for a full session: {', '.join(gaps)}", ""))
    result.lines.append(say.Line(f"stance: {row_name}: {said}", ""))
    result.data = {"rows": [row.as_json() for row in rows], "host": host, "missing": gaps,
                   "stance": {"row": row_name, "said": said}}
    return commands.emit(result, args, out)
