"""The only part of planner that touches the disk, the clock or git.

Exit codes: 0 clean, 1 findings, 2 the tool itself failed.
"""
import argparse
import codecs
import datetime
import json
import pathlib
import subprocess
import sys
import time
import traceback

import yaml

from planner import handoff, health, model, parse, progress, query, render, rules, schema, viewer

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"


class ToolError(Exception):
    """The tool cannot run: bad arguments, no vault config, unreadable files."""


def load_config(root):
    path = root / ".planner.yaml"
    if not path.is_file():
        raise ToolError(f"{root} has no .planner.yaml, so it is not a vault. Run planner from the vault root or pass --vault.")
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ToolError(f".planner.yaml is not valid YAML: {exc}") from exc
    if not isinstance(config, dict) or not schema.INITIATIVE_RE.match(str(config.get("initiative", ""))):
        raise ToolError(".planner.yaml needs 'initiative: INI-nnn' and 'title: ...'.")
    if not config.get("title"):
        raise ToolError(".planner.yaml needs 'title: ...'.")
    days = config.get("stale_after_days", schema.STALE_AFTER_DAYS)
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ToolError(f".planner.yaml has stale_after_days: {days!r}. Write a whole number of days, such as 60.")
    return config


def vault_files(root):
    """(pages to parse, basenames of other Markdown files) under the vault root."""
    pages, others = [], []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        parts = rel.parts
        if any(p.startswith(".") for p in parts[:-1]):
            continue
        if (len(parts) == 1 and parts[0] in schema.SKIP_FILES) or parts[0] in schema.SKIP_DIRS:
            others.append(path.stem)
            continue
        pages.append(path)
    return pages, others


def load_vault(root):
    config = load_config(root)
    paths, others = vault_files(root)
    pages = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ToolError(f"Cannot read {path}: {exc}") from exc
        pages.append(parse.parse_page(path.relative_to(root).as_posix(), text))
    return model.build(pages, config, others)


def parse_today(value):
    if value is None:
        return datetime.date.today().isoformat(), "system date"
    if not rules.is_date(value):
        raise ToolError(f"--today '{value}' is not a YYYY-MM-DD date.")
    return value, "--today"


def cmd_check(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, origin = parse_today(args.today)
    started = time.perf_counter()
    vault = load_vault(root)
    findings = rules.check(vault, today, gate=args.gate)
    errors = sum(1 for f in findings if f.is_error)
    warnings = len(findings) - errors
    elapsed = time.perf_counter() - started
    print(f"planner check: {errors} errors, {warnings} warnings in {len(vault.pages)} pages. "
          f"Today is {today} ({origin}). Took {elapsed:.2f} s." + (f" Gate: {args.gate}." if args.gate else ""), file=out)
    for finding in findings:
        print(finding.format(), file=out)
    return 1 if errors else 0


def cmd_render(args, out):
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    texts, changed, discarded, refusals = render.render_vault(vault, args.discard_edits)
    if refusals:
        print(f"planner render: wrote nothing, {len(refusals)} problems.", file=out)
        for finding in refusals:
            print(finding.format(), file=out)
        return 1
    for path, text in sorted(texts.items()):
        target = root / path
        original = target.read_bytes()
        if b"\r\n" in original:
            text = text.replace("\n", "\r\n")  # keep the file's own line endings
        data = text.encode("utf-8")
        if original.startswith(codecs.BOM_UTF8):
            data = codecs.BOM_UTF8 + data
        target.write_bytes(data)
    for path, name, old in discarded:
        print(f"{path}: discarded a hand edit in '{name}':", file=out)
        for line in old.split("\n"):
            print(f"  - {line}", file=out)
    print(f"planner render: {len(changed)} blocks changed.", file=out)
    for path, name in changed:
        print(f"  {path}: {name}", file=out)
    return 0


def git(root, *args):
    """Output of a git command in the vault, or "" when git cannot answer."""
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def read_asset(name):
    path = ASSETS / name
    if not path.is_file():
        raise ToolError(f"{path} is missing, so the viewer cannot work offline. Restore it from the toolkit repo.")
    return path.read_text(encoding="utf-8")


def cmd_view(args, out):
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    today, _ = parse_today(args.date)
    commit = args.commit or git(root, "rev-parse", "--short", "HEAD") or "an uncommitted copy"
    if git(root, "status", "--porcelain", "--", "."):
        commit += " with uncommitted changes"
    findings = rules.check(vault, today)
    errors = sum(1 for f in findings if f.is_error)
    stamp = {
        "commit": commit,
        "date": today,
        "repo": args.repo_url or git(root, "remote", "get-url", "origin") or "no repository URL recorded",
        "errors": errors,
        "warnings": len(findings) - errors,
    }
    html, problems = viewer.build(vault, read_asset("marked.min.js"), read_asset("mermaid.min.js"), stamp)
    if problems:
        print(f"planner view: wrote nothing, {len(problems)} links would break in the viewer.", file=out)
        for problem in problems:
            print(f"  {problem}", file=out)
        return 1
    target = pathlib.Path(args.out)
    target.write_text(html, encoding="utf-8")
    print(f"planner view: wrote {target} ({len(viewer.bundled(vault))} pages). "
          f"Built from {stamp['commit']} on {stamp['date']}. "
          f"Check at build time: {errors} errors, {stamp['warnings']} warnings.", file=out)
    return 0


def cmd_health(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, _ = parse_today(args.today)
    vault = load_vault(root)
    commit = git(root, "rev-parse", "--short", "HEAD") or "an uncommitted copy"
    findings = rules.check(vault, today)
    print(health.report(vault, findings, today, commit), end="", file=out)
    return 0


def print_answer(answer, as_json, out):
    """JSON, or one "key: value" line per field with lists joined by commas."""
    if as_json:
        print(json.dumps(answer, indent=2, ensure_ascii=False), file=out)
        return
    for key, value in answer.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            print(f"{key}:", file=out)
            for entry in value:
                print("  " + " · ".join(f"{k}: {v}" for k, v in entry.items()), file=out)
        elif isinstance(value, list):
            print(f"{key}: {', '.join(map(str, value)) or 'none'}", file=out)
        elif isinstance(value, bool):
            print(f"{key}: {'true' if value else 'false'}", file=out)
        else:
            print(f"{key}: {value if value not in (None, '') else 'none'}", file=out)


def cmd_query(args, out):
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    if args.what == "get":
        answer = query.get(vault, args.id)
    elif args.what == "refs":
        answer = query.refs(vault, args.id)
    elif args.what == "find":
        if not any(w.strip() for w in args.words):
            raise ToolError("planner query find needs at least one word that is not blank.")
        answer = query.find(vault, args.words)
    else:
        today, _ = parse_today(args.today)
        answer = query.status(vault, today)
    print_answer(answer, args.json, out)
    return 1 if answer.get("not_found") else 0


def handoff_app(vault, app_id):
    pages = vault.by_id.get(app_id)
    if not pages or pages[0].type != "app-building-blocks":
        raise ToolError(f"{app_id} is not the id of an app's building-blocks page, for example APP-booking.")
    return pages[0]


def stamp_commit(root, override):
    commit = override or git(root, "rev-parse", "--short", "HEAD") or "an uncommitted copy"
    if not override and git(root, "status", "--porcelain", "--", "."):
        commit += " with uncommitted changes"
    return commit


def cmd_handoff(args, out):
    root = pathlib.Path(args.vault).resolve()
    if len(args.words) == 2 and args.words[0] == "verify":
        return handoff_verify(root, args.words[1], out)
    if len(args.words) != 1 or args.words[0] == "verify":
        raise ToolError("Write planner handoff <APP-id>, or planner handoff verify <APP-id>.")
    app_id = args.words[0]
    today, _ = parse_today(args.today)
    vault = load_vault(root)
    app = handoff_app(vault, app_id)
    errors = [f for f in rules.check(vault, today) if f.is_error]
    if errors:
        print(f"planner handoff: wrote nothing, planner check has {len(errors)} errors. Fix them first.", file=out)
        for finding in errors:
            print(finding.format(), file=out)
        return 1
    target = root / schema.HANDOFF_DIR / f"{app_id}.md"
    if target.exists() and not args.replace:
        print(f"planner handoff: wrote nothing. {target.relative_to(root)} is what the senior accepted. "
              f"Run planner handoff verify {app_id}, or pass --replace once the senior accepts the changes.", file=out)
        return 1
    entries = handoff.slice_of(vault, app)
    commit = stamp_commit(root, args.commit)
    target.parent.mkdir(exist_ok=True)
    target.write_text(handoff.write(app_id, entries, commit, today), encoding="utf-8")
    print(f"planner handoff: wrote {target.relative_to(root).as_posix()}, {len(entries)} items, at {commit}.", file=out)
    return 0


def handoff_verify(root, app_id, out):
    vault = load_vault(root)
    app = handoff_app(vault, app_id)
    path = root / schema.HANDOFF_DIR / f"{app_id}.md"
    if not path.is_file():
        raise ToolError(f"{path.relative_to(root).as_posix()} does not exist. Run planner handoff {app_id} when the senior accepts the slice.")
    try:
        facts, accepted = handoff.read(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, handoff.ManifestError) as exc:
        raise ToolError(f"{path.relative_to(root).as_posix()} cannot be read as a manifest: {exc}") from exc
    diff = handoff.verify(accepted, handoff.slice_of(vault, app))
    print(f"planner handoff verify {app_id}: {len(diff.changed)} changed, {len(diff.added)} added, {len(diff.removed)} removed "
          f"since the handoff at {facts.get('Commit', 'an unrecorded commit')} on {facts.get('Written', 'an unrecorded date')}.",
          file=out)
    for old, new in diff.changed:
        print(handoff.describe(old, new), file=out)
    for entry in diff.added:
        print(f"added: {entry.id} ({entry.kind}, {entry.page}, {entry.state or 'no state'})", file=out)
    for entry in diff.removed:
        print(f"removed: {entry.id} ({entry.kind}, {entry.page}, was {entry.state or 'no state'})", file=out)
    return 1 if diff.breaks_acceptance else 0


def days_between(earlier, later):
    return (datetime.date.fromisoformat(later) - datetime.date.fromisoformat(earlier)).days


def oldest_text(row, today):
    if row.oldest is None:
        return "none"
    if not row.opened:
        return f"{row.oldest.id}, opened: not recorded"
    return f"{row.oldest.id}, open {days_between(row.opened, today)} days (opened {row.opened})"


def status_line(row, today):
    inkling, assumption, fact, decided = row.mix
    next_text = f"{row.mode} {row.subject}".strip() if row.mode != "none" else "none"
    return (f"{row.app.id} | stage {row.stage or '-'} | inkling {inkling}, assumption {assumption}, fact {fact}, "
            f"decided {decided} | oldest open unknown: {oldest_text(row, today)} | next: {next_text}. {row.reason}")


def cmd_status(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, origin = parse_today(args.today)
    vault = load_vault(root)
    rows = progress.grid(vault, today)
    print(f"planner status: {len(rows)} apps. Today is {today} ({origin}).", file=out)
    for row in rows:
        print(status_line(row, today), file=out)
    return 0


def cmd_next(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, origin = parse_today(args.today)
    vault = load_vault(root)
    when = f"Today is {today} ({origin})."
    if not vault.apps:
        print(f"planner next: initiative, dump. No app page exists yet, so start with a Dump & Diverge or a Discover. {when}",
              file=out)
        return 0
    row = progress.best(progress.grid(vault, today))
    if row is None:
        print(f"planner next: nothing to do. Every app's items are settled and its epics decided. {when}", file=out)
        return 0
    print(f"planner next: {row.app.id}, {row.mode} {row.subject}. {row.reason} {when}", file=out)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="planner", description="Check and render an initiative vault.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="read-only check of the vault")
    check.add_argument("--vault", default=".", help="vault root (default: current directory)")
    check.add_argument("--today", help="date to judge overdue unknowns by, YYYY-MM-DD (default: system date)")
    check.add_argument("--gate", choices=schema.GATES,
                       help="epics: trace gaps are errors; run it before calling an app's epics complete")
    check.set_defaults(func=cmd_check)
    rend = sub.add_parser("render", help="rewrite generated blocks")
    rend.add_argument("--vault", default=".", help="vault root (default: current directory)")
    rend.add_argument("--discard-edits", action="store_true", help="overwrite hand-edited blocks and print what was lost")
    rend.set_defaults(func=cmd_render)
    view = sub.add_parser("view", help="build one offline HTML file of the vault")
    view.add_argument("--vault", default=".", help="vault root (default: current directory)")
    view.add_argument("--out", required=True, help="HTML file to write")
    view.add_argument("--commit", help="commit to stamp (default: git rev-parse --short HEAD)")
    view.add_argument("--repo-url", help="where newer versions live (default: git remote get-url origin)")
    view.add_argument("--date", help="build date to stamp, YYYY-MM-DD (default: system date)")
    view.set_defaults(func=cmd_view)
    status = sub.add_parser("status", help="each app's stage, certainty mix, oldest open unknown and next mode")
    status.add_argument("--vault", default=".", help="vault root (default: current directory)")
    status.add_argument("--today", help="date to judge overdue unknowns and ages by, YYYY-MM-DD (default: system date)")
    status.set_defaults(func=cmd_status)
    nxt = sub.add_parser("next", help="the single best next step: an app and a mode, with the reason")
    nxt.add_argument("--vault", default=".", help="vault root (default: current directory)")
    nxt.add_argument("--today", help="date to judge overdue unknowns by, YYYY-MM-DD (default: system date)")
    nxt.set_defaults(func=cmd_next)
    report = sub.add_parser("health", help="stale pages and sources, overdue unknowns and session gaps, as Markdown")
    report.add_argument("--vault", default=".", help="vault root (default: current directory)")
    report.add_argument("--today", help="date to judge by, YYYY-MM-DD (default: system date)")
    report.set_defaults(func=cmd_health)
    ask = sub.add_parser("query", help="read-only answers about IDs, for /ask: get, refs, find, status")
    asks = ask.add_subparsers(dest="what", required=True)
    for name, helptext in (("get", "an ID's page, heading, state, owner, sources and decision"),
                           ("refs", "every page that links to an ID"), ("find", "page titles and item headings with these words"),
                           ("status", "the planner status grid")):
        one = asks.add_parser(name, help=helptext)
        if name in ("get", "refs"):
            one.add_argument("id", help="an ID, for example CON-001 or APP-booking")
        if name == "find":
            one.add_argument("words", nargs="+", help="words that must all appear, in any case; put -- before a word that starts with -")
        if name == "status":
            one.add_argument("--today", help="date to judge by, YYYY-MM-DD (default: system date)")
        one.add_argument("--vault", default=".", help="vault root (default: current directory)")
        one.add_argument("--json", action="store_true", help="print JSON instead of text")
        one.set_defaults(func=cmd_query)
    hand = sub.add_parser("handoff", help="write the senior's handoff manifest, or verify the vault against it")
    hand.add_argument("words", nargs="+", metavar="[verify] APP-id", help="APP-id to write handoffs/<APP-id>.md; verify APP-id to compare")
    hand.add_argument("--vault", default=".", help="vault root (default: current directory)")
    hand.add_argument("--today", help="date to record, YYYY-MM-DD (default: system date)")
    hand.add_argument("--commit", help="commit to record (default: git rev-parse --short HEAD)")
    hand.add_argument("--replace", action="store_true", help="overwrite an existing manifest once the senior accepts the changes")
    hand.set_defaults(func=cmd_handoff)
    return parser


def main(argv=None, out=None):
    out = out or sys.stdout
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        return args.func(args, out)
    except ToolError as exc:
        print(f"planner: {exc}", file=out)
        return 2
    except Exception as exc:  # the tool failed; never report this as a vault finding
        print(f"planner: internal error: {exc!r}. This is a bug in planner, not in the vault.", file=out)
        traceback.print_exc(file=out)
        return 2
