"""The only part of planner that touches the disk, the clock or git.

Exit codes: 0 clean, 1 findings, 2 the tool itself failed.
"""
import argparse
import codecs
import datetime
import pathlib
import subprocess
import sys
import time
import traceback

import yaml

from planner import model, parse, progress, render, rules, schema, viewer

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
