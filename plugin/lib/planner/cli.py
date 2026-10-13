"""The only part of planner that touches the disk, the clock, git or the network.
The network is touched by one command alone, `planner voicescore setup`.

Exit codes: 0 clean, 1 findings, 2 the tool itself failed.
"""
import argparse
import codecs
import datetime
import difflib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

import yaml

from planner import allocation, capture, catalog, completeness, drafts, search, export, freshness, handoff, health, ids, ladder, model, opening, pending, pluginroot, proposal, reading, parse, progress, publish, query, questions, releases, render, replay, review, reviews, roles, rules, schema, secretscan, untrusted, viewer, voicecheck, voicescore
from planner.edge import atomic, copies, replays, reviewgit, vaultgit
from planner.edge import proposals as proposal_files

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"
CATALOGUE = pathlib.Path(__file__).resolve().parent.parent.parent / "catalog" / "questions.yaml"
LINT_WORDS = pathlib.Path(__file__).resolve().parent.parent.parent / "references" / "lint-words.txt"
TEMPLATE_LINES = pathlib.Path(__file__).resolve().parent.parent.parent / "catalog" / "template-lines.txt"


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


def load_catalogue(path=None):
    """The question catalogue the plugin ships. Missing or unreadable is a tool failure, never an empty
    catalogue: an empty one would make every vault look as if it owed no questions."""
    path = pathlib.Path(path or CATALOGUE)
    if not path.is_file():
        raise ToolError(f"{path} is missing, so planner cannot work out which questions are owed. "
                        "Restore it from the toolkit repo.")
    try:
        data = catalog.load_yaml(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ToolError(f"{path} cannot be read as YAML: {exc}") from exc
    try:
        return catalog.parse_catalogue(data)
    except catalog.CatalogueError as exc:
        raise ToolError(f"{path} is not a valid question catalogue: {exc}") from exc


def load_template_lines(path=None):
    """The prose lines the template pages write, one per line, for W368. Missing is a tool failure: an empty list
    would make every page look as if it had replaced its template opening."""
    path = pathlib.Path(path or TEMPLATE_LINES)
    try:
        return [line for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]
    except (OSError, UnicodeDecodeError) as exc:
        raise ToolError(f"{path} cannot be read ({exc}), so planner cannot tell a template opening from a written one. "
                        "Restore it from the toolkit repo.") from exc


def vault_files(root):
    """(pages to parse, basenames of other Markdown files) under the vault root."""
    pages, others = [], []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        parts = rel.parts
        if any(p.startswith(".") for p in parts[:-1]) or replay.is_mine_file(rel.as_posix()):
            continue
        if path.is_symlink():
            raise ToolError(str(untrusted.link_refusal(rel.as_posix())))
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
    return model.build(pages, config, others, load_catalogue(), load_template_lines())


def parse_today(value):
    if value is None:
        return datetime.date.today().isoformat(), "system date"
    if not rules.is_date(value):
        raise ToolError(f"--today '{value}' is not a YYYY-MM-DD date.")
    return value, "--today"


# The format the installed skills follow. A vault keeps its own copy, from the day it was made, so a plugin update
# that changes the format would leave the vault's copy saying rules the skills no longer follow.
PLUGIN_CONVENTIONS = pathlib.Path(__file__).resolve().parents[2] / "vault" / "CONVENTIONS.md"


def same_text(one, other):
    """Equal once line endings are read alike, so a Windows checkout's CRLF is not a different copy."""
    return one.read_bytes().replace(b"\r\n", b"\n") == other.read_bytes().replace(b"\r\n", b"\n")


def conventions_findings(root):
    """W717 when the vault's CONVENTIONS.md is not the plugin's. A missing copy on either side is not judged."""
    mine = root / "CONVENTIONS.md"
    if not (mine.is_file() and PLUGIN_CONVENTIONS.is_file()) or same_text(mine, PLUGIN_CONVENTIONS):
        return []
    return [model.Finding("CONVENTIONS.md", 1, "W717",
                          "CONVENTIONS.md is not the copy the installed plugin ships, so the skills may follow rules "
                          "it does not state.",
                          "Run planner upgrade, review the change with git diff CONVENTIONS.md, and commit it.")]


def cmd_upgrade(args, out):
    root = pathlib.Path(args.vault).resolve()
    refuse_if_reader(root, "Upgrading CONVENTIONS.md")
    if not PLUGIN_CONVENTIONS.is_file():
        raise ToolError(f"the plugin's CONVENTIONS.md is missing at {PLUGIN_CONVENTIONS}; reinstall the plugin.")
    mine = root / "CONVENTIONS.md"
    new = PLUGIN_CONVENTIONS.read_bytes()
    if mine.is_file() and same_text(mine, PLUGIN_CONVENTIONS):
        print("planner upgrade: CONVENTIONS.md is already the plugin's copy. Nothing changed.", file=out)
        return 0
    old_lines = mine.read_text(encoding="utf-8").splitlines() if mine.is_file() else []
    mine.write_bytes(new)
    changed = sum(1 for line in difflib.unified_diff(old_lines, new.decode("utf-8").splitlines(), lineterm="")
                  if line[:1] in "+-" and not line.startswith(("+++", "---")))
    print(f"planner upgrade: CONVENTIONS.md replaced with the plugin's copy, {changed} lines changed. "
          "Review it with git diff CONVENTIONS.md, then commit it.", file=out)
    return 0


def detect_role(root):
    """The roles.Role for a folder. A git that cannot run is a tool failure only when nothing else decides the role."""
    return roles.decide(vaultgit.role_facts(root))


def print_role(found, out):
    print(f"planner role: {found.role}. {found.reason[0].upper()}{found.reason[1:]}.", file=out)
    for note in found.notes:
        print(f"  Note: {note}.", file=out)
    for warning in found.warnings:
        print(f"  Warning: {warning}.", file=out)


def cmd_role(args, out):
    found = detect_role(pathlib.Path(args.vault).resolve())
    if args.json:
        print(json.dumps(found.as_dict(), indent=2), file=out)
    else:
        print_role(found, out)
    return 0 if found.role != roles.NONE else 1


def refuse_reader(root, action):
    """Stop a reader from doing an owner's job, naming whom to write to (a bare 'not allowed' is a Silent Fallback)."""
    try:
        stamp = copies.read_own_stamp(root)
    except copies.SourceUnreadable:
        stamp = None  # the refusal still stands; only the name of the owner is lost
    who = (stamp or {}).get("owner", {})
    contact = who.get("name") or who.get("contact")
    return ToolError(f"{action} is the owner's job, and this is a published copy. "
                     + (f"That is {contact}'s call. Send a proposal and they decide." if contact
                        else "Send the owner a proposal and they decide."))


def refuse_if_reader(root, action):
    """Owner-only commands stop in a published copy. A folder that decides no role is left alone: tests and fresh vaults have no git."""
    if detect_role(root).role == roles.READER:
        raise refuse_reader(root, action)


def check_counts(files, today):
    """(errors, warnings) of planner check on exactly these committed files."""
    with tempfile.TemporaryDirectory() as folder:
        copies.write_folder(files, folder + "/vault")
        root = pathlib.Path(folder) / "vault"
        vault = load_vault(root)
        found = rules.check(vault, today) + conventions_findings(root)
    errors = sum(1 for f in found if f.is_error)
    return errors, len(found) - errors


def publish_dashboard(files, built, today):
    """dashboard.html bytes built from exactly the files a read copy will hold, so the page and the pages never disagree.
    Built in a scratch folder with no git and no stamp, so it carries no freshness line: a reader's own build adds that."""
    from planner.explorer import build as explorer, pins as explorer_pins  # lazy: the explorer imports this module
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        copies.write_folder(files, folder)
        page = folder / publish.DASHBOARD_PATH
        try:
            explorer.generate(folder, page, today, pins_path=folder / explorer_pins.PINS_FILE, assets_config=None,
                              design_args=[], theme="console", freshness=None, built=built)
        except explorer.ExplorerError as exc:
            raise ToolError(f"cannot publish: the dashboard could not be built from the committed pages: {exc}") from exc
        return page.read_bytes()


def cmd_publish(args, out):
    root = pathlib.Path(args.vault).resolve()
    found = detect_role(root)
    if found.role == roles.READER:
        raise refuse_reader(root, "Publishing")
    if found.role != roles.OWNER:
        raise ToolError(f"cannot publish: {found.reason}.")
    target = pathlib.Path(args.out).expanduser().resolve()
    if target == root or root in target.parents:
        raise ToolError(f"--out {target} is inside the vault; publish to a folder outside it.")
    today, _ = parse_today(args.today)
    try:
        files, skipped, executable = vaultgit.committed_files(root)
        commit, short = vaultgit.head(root)
        dirty_files = vaultgit.uncommitted(root)
        git_name, git_email = vaultgit.user_identity(root)
        files = publish.selected(files)
        secret_notes = check_secrets(files, args.allow_secrets)
        if ".planner.yaml" not in files:
            raise ToolError("HEAD has no .planner.yaml, so there is no initiative to publish. Commit it first.")
        files[publish.DASHBOARD_PATH] = publish_dashboard(files, {"date": vaultgit.commit_date(root, "HEAD") or today, "commit": short}, today)
        config = load_config_text(files[".planner.yaml"])
        owner = publish.owner_contact(config, git_name, git_email, args.owner_name or "", args.owner_contact or "")
        counts = check_counts(files, today)
        stamp = publish.build_stamp(config, commit, short, today, bool(dirty_files), owner, counts, files)
        stamped = publish.with_stamp(files, stamp)
        if target.suffix.lower() == ".zip":
            copies.write_zip(publish.zip_bytes(stamped, publish.copy_name(config["title"], short),
                                               {p for p in executable if executable[p] and p in stamped}), target)
        else:
            copies.write_folder(stamped, target, {p for p in executable if executable[p] and p in stamped})
    except vaultgit.GitUnavailable as exc:
        raise ToolError(f"cannot read the vault's commit: {exc}. Is there at least one commit?") from exc
    except publish.PublishError as exc:
        raise ToolError(str(exc)) from exc
    except OSError as exc:
        raise ToolError(f"cannot write {target}: {exc.strerror or exc}") from exc
    print(f"planner publish: wrote {target.name} ({len(stamped)} files) at {short}, {counts[0]} errors and {counts[1]} warnings "
          f"at publish. Contact: {owner['name']} <{owner['contact']}>.", file=out)
    for line in secret_notes:
        print(f"  {line}", file=out)
    note = publish.dirty_message(short, len(dirty_files))
    if note:
        print(f"  {note[0].upper()}{note[1:]} The stamp says dirty: true.", file=out)
    if skipped:
        print(f"  Not copied (links or submodules a read copy cannot carry): {', '.join(skipped[:5])}.", file=out)
    return 0


def check_secrets(files, allowed):
    """Refuse a publish whose pages look like they hold a credential; with --allow-secrets, go on and say what was let through."""
    texts = {path: data.decode("utf-8", "replace") for path, data in files.items() if path != publish.DASHBOARD_PATH and not drafts.is_binary(data)}
    hits = secretscan.find_secrets(texts)
    if not hits:
        return []
    if not allowed:
        raise ToolError(secretscan.refusal(hits))
    return [f"--allow-secrets: published with {len(hits)} possible secret(s) in it ({hits[0].path} line {hits[0].line} and others); the copy carries them to every reader."]


def load_config_text(data):
    """.planner.yaml read from committed bytes, with the same rules as load_config."""
    with tempfile.TemporaryDirectory() as folder:
        (pathlib.Path(folder) / ".planner.yaml").write_bytes(data)
        return load_config(pathlib.Path(folder))


def owner_freshness(root, timeout, checked_at):
    """freshness.Report for a git owner: fetch with a timeout, then count behind, ahead and uncommitted. Never pulls."""
    try:
        full, short = vaultgit.head(root)
    except vaultgit.GitUnavailable as exc:
        return freshness.Report("owner", freshness.UNKNOWN, checked_at, f"I cannot read this clone's commits yet: {exc}.")
    local = {"commit": short, "date": vaultgit.commit_date(root, "HEAD")}
    uncommitted = len(vaultgit.uncommitted(root))
    upstream_name = vaultgit.upstream(root)
    if not vaultgit.has_origin(root):
        return freshness.owner_report(local, None, 0, 0, uncommitted, "", "this vault has no remote called origin, so there is nothing to compare with", checked_at)
    fetch_error = vaultgit.fetch(root, timeout)
    if not upstream_name:
        return freshness.owner_report(local, None, 0, 0, uncommitted, "", "this branch has no upstream, so there is nothing to compare with", checked_at)
    behind, ahead = vaultgit.behind_ahead(root, upstream_name)
    latest = {"commit": vaultgit.head_short(root, upstream_name), "date": vaultgit.commit_date(root, upstream_name)}
    return freshness.owner_report(local, latest, behind, ahead, uncommitted, fetch_error, "", checked_at)


def reader_freshness(root, checked_at):
    """freshness.Report for a reader's workspace: baseline stamp against the stamp at the remembered source."""
    try:
        workspace = copies.read_workspace(root)
    except copies.SourceUnreadable as exc:
        return freshness.Report("reader", freshness.UNKNOWN, checked_at, f"{exc}")
    stamp, unreachable, unreadable = None, "", ""
    try:
        stamp = copies.read_source_stamp(workspace.get("source_path") or "")
    except copies.SourceUnreachable as exc:
        unreachable = str(exc)
    except copies.SourceUnreadable as exc:
        unreadable = str(exc)
    return freshness.reader_report(workspace, stamp, unreachable, unreadable, checked_at)


def freshness_report(root, found, timeout, today, checked_at=None):
    """The freshness.Report for a folder whose role is `found`. `planner freshness`, `explore` and the helper's
    /freshness all ask here, so the three can never disagree."""
    checked_at = checked_at or f"{today}T{time.strftime('%H:%M:%S')}"
    if found.role == roles.OWNER:
        return owner_freshness(root, timeout, checked_at)
    if found.role == roles.READER:
        return reader_freshness(root, checked_at)
    raise ToolError(f"cannot check freshness: {found.reason}.")


def page_freshness(root, found, today):
    """What the explorer page is stamped with at build time: the report as a dict, or None when no role decides one.
    It is checked "at" the day, not the second, so building twice from one state writes the same page."""
    if found.role == roles.NONE:
        return None
    return freshness_report(root, found, vaultgit.FETCH_TIMEOUT, today, checked_at=today).as_dict()


def page_built(root, found, today):
    """{"date", "commit"} the dashboard says it was built from, so someone opening an old copy knows how old it is.
    The date is the commit's own (never the clock), so an unchanged vault rebuilds to the same file; with no commit to
    name, the build day and no commit. An owner's is HEAD; a reader's is the publish their workspace was opened from."""
    if found.role == roles.OWNER:
        try:
            return {"date": vaultgit.commit_date(root, "HEAD") or today, "commit": vaultgit.head(root)[1]}
        except vaultgit.GitUnavailable:
            return {"date": today, "commit": ""}  # a clone with no commit yet; the page then names no commit
    if found.role == roles.READER:
        try:
            workspace = copies.read_workspace(root)
        except copies.SourceUnreadable:
            return {"date": today, "commit": ""}  # page_freshness reports the unreadable record on the same build
        return {"date": workspace.get("base_date") or today, "commit": (workspace.get("base_commit") or "")[:7]}
    return {"date": today, "commit": ""}


def cmd_freshness(args, out):
    root = pathlib.Path(args.vault).resolve()
    found = detect_role(root)
    today, _ = parse_today(args.today)
    report = freshness_report(root, found, args.timeout, today)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2), file=out)
    else:
        print(f"planner freshness: {report.message}", file=out)
    return 0


PLANNER_PROGRAM = pathlib.Path(__file__).resolve().parent.parent.parent / "scripts" / "planner"


def reader_author(flag, root):
    """Who the drafts are by: --author, else git's user.name. Never the OS username (it would leak into proposals)."""
    if flag:
        return flag
    try:
        name = vaultgit.user_identity(root)[0]
    except vaultgit.GitUnavailable:
        name = ""
    if not name:
        raise ToolError("I do not know your name for the drafts. Pass --author \"Your Name\".")
    return name


def environment_notes(env):
    """What this machine lacks for the optional parts, said once at open (never a failure)."""
    notes = []
    if not shutil.which("claude"):
        notes.append("`claude` is not on PATH, so --serve and the Ask Claude helper will not work here; the page still opens as a file.")
    if not env.get("PLANNER_WORKSPACES") and not pathlib.Path.home().exists():
        notes.append("there is no home folder to keep the workspace in; pass --into.")
    return notes


def workspace_folder(slug, into, env, in_cowork):
    """The absolute workspace folder by the rule opening.location_rule picks; a synced location is refused."""
    rule = opening.location_rule(into, env.get("PLANNER_WORKSPACES"), in_cowork)
    base = {"into": lambda: pathlib.Path(into or ""), "env": lambda: pathlib.Path(env.get("PLANNER_WORKSPACES", "")) / slug,
            "cowork": lambda: pathlib.Path.cwd() / opening.COWORK_FOLDER / slug,
            "home": lambda: pathlib.Path.home() / opening.DEFAULT_FOLDER / slug}[rule]()
    folder = pathlib.Path(os.path.abspath(base.expanduser()))
    opening.refuse_synced(folder.parts, folder)
    return folder


def cmd_open(args, out):
    env = os.environ
    try:
        files, stamp = copies.read_published(args.source)
        opening.verify_tree(files, stamp)
        admitted, left_out = opening.admit(files)
        in_cowork = bool(env.get("PLANNER_COWORK") or env.get("CLAUDE_COWORK"))
        folder = workspace_folder(publish.slug(stamp["title"]), args.into, env, in_cowork)
        existing = copies.read_existing_workspace(folder)
        today, _ = parse_today(args.today)
        source_path = os.path.abspath(os.path.expanduser(args.source))
        if existing is not None:
            return reopen_workspace(folder, existing, (admitted, stamp), (pathlib.Path(args.source).name, source_path), (args.author, args.newer), today, out)
        record = opening.workspace_record(stamp, pathlib.Path(args.source).name, source_path,
                                          today, reader_author(args.author, pathlib.Path.cwd()),
                                          str(PLANNER_PROGRAM))
        copies.write_workspace(folder, admitted, record)
    except opening.OpenError as exc:
        raise ToolError(str(exc)) from exc
    for line in opening.opened_message(stamp, folder):
        print(line, file=out)
    if left_out:
        print(f"  {untrusted.left_out_line(left_out)}", file=out)
    explore_workspace(folder, today, out)
    checked_at = f"{today}T{time.strftime('%H:%M:%S')}"
    print(f"planner open: {reader_freshness(folder, checked_at).message}", file=out)
    for note in environment_notes(env):
        print(f"  Note: {note}", file=out)
    print(f"  Work from that folder: cd {folder}", file=out)
    return 0


def reopen_workspace(folder, existing, published, source, flags, today, out):
    """`planner open <newer copy> --into <workspace>`: the reader's drafts replayed onto the newer copy (design session 15
    section 8). Pure planning in replay.py; edge/replays.py writes it in an order that leaves the old baseline until the end."""
    files, stamp = published
    author_flag, confirmed_newer = flags
    verdict = opening.reopen_verdict(existing, stamp, confirmed_newer)
    refusal = opening.reopen_refusal(existing, stamp, verdict)
    if refusal:
        raise opening.OpenError(refusal)
    if verdict == opening.SAME:
        print(f"planner open: this workspace is already on {stamp['short']} (published {stamp['date']}); there is nothing to replay and nothing was changed.", file=out)
        return 0
    baseline_dir = folder / copies.BASELINE
    if not baseline_dir.is_dir():
        raise opening.OpenError(f"{baseline_dir} is missing, so I cannot tell what you changed and would risk overwriting it. "
                                "Open the newer copy into a new folder with --into instead.")
    new_files = {path: data for path, data in files.items() if path != publish.STAMP_PATH and not publish.is_excluded(path)}
    carried = replays.open_conflicts(folder)
    result = replay.plan(copies.read_tree(baseline_dir, skip_published=True), copies.read_tree(folder, skip_published=True), new_files,
                         replays.existing_mine(folder))
    old, new = (existing.get("base_commit", "")[:7], existing.get("base_date", "")), (stamp["short"], stamp["date"])
    stale, unreadable = proposal_files.written_against(folder.parent / "proposals", existing.get("base_commit", ""))
    record = opening.workspace_record_after_replay(existing, stamp, source[0], source[1], today, author_flag or "")
    journal = replays.record_json({"commit": old[0], "date": old[1]}, {"commit": new[0], "date": new[1]}, result, carried, today)
    replays.apply(folder, result, new_files | {publish.STAMP_PATH: files[publish.STAMP_PATH]}, journal, record, f"{today}-{stamp['short']}")
    print(f"planner open: {folder}", file=out)
    for line in replay.report(result, old, new, replay.stale_lines(stale, old[0])):
        print(line, file=out)
    for name, why in unreadable:
        print(f"  Could not read the proposal {name}, so I do not know whether it is stale: {why}", file=out)
    explore_workspace(folder, today, out)
    checked_at = f"{today}T{time.strftime('%H:%M:%S')}"
    print(f"planner open: {reader_freshness(folder, checked_at).message}", file=out)
    return 0


def explore_workspace(folder, today, out):
    """Build dashboard.html in the workspace root so a reader has something to open."""
    from planner.explorer import build as explorer, pins as explorer_pins  # lazy: the explorer imports this module
    found = detect_role(folder)
    try:
        lines = explorer.generate(folder, folder / publish.DASHBOARD_PATH, today, pins_path=folder / explorer_pins.PINS_FILE,
                                  assets_config=None, design_args=[], theme="console",
                                  freshness=page_freshness(folder, found, today), built=page_built(folder, found, today))
    except explorer.ExplorerError as exc:
        raise ToolError(f"the workspace was written at {folder}, but the explorer page could not be built: {exc}") from exc
    for line in lines:
        print(f"planner explore: {line}", file=out)


# ------------------------------------------------------------------ propose (a reader) and proposals (an owner)

def vault_findings(root, today):
    """Every finding `planner check` would print for the vault at `root`."""
    return rules.check(load_vault(root), today) + conventions_findings(root)


def check_summary(root, baseline_dir, today):
    """What the proposal says about its own copy: counts, the errors in full (they print first), and what is new."""
    found = vault_findings(root, today)
    before = {(f.code, f.path, f.message) for f in vault_findings(baseline_dir, today)}
    errors = [f for f in found if f.is_error]
    fresh = [f for f in found if (f.code, f.path, f.message) not in before and f.code != pending.WARNING]
    shown = [f"{f.code} in {f.path}" for f in fresh[:5]] + ([f"and {len(fresh) - 5} more"] if len(fresh) > 5 else [])
    return {"errors": len(errors), "warnings": len(found) - len(errors), "new": shown,
            "error_lines": [f.format() for f in errors[:10]] + ([f"and {len(errors) - 10} more errors; run planner check"] if len(errors) > 10 else [])}


def heading_for(page, item_id):
    """The text of the heading that names an item ("CON-004 Refund contract"), else the ID alone."""
    for heading in page.headings:
        if heading.text.split()[:1] == [item_id]:
            return heading.text.strip()
    return item_id


def new_pending(root, baseline_dir, changed):
    """{item ID: {heading, by, date, session}} for the pending-approval markers the reader added since the baseline."""
    now, was = load_vault(root), load_vault(baseline_dir)
    had = {(p.path, p.item, p.by, p.date) for p in pending.items(was)}
    pages = {p.path: p for p in now.pages}
    found = {}
    for entry in pending.items(now):
        if (entry.path, entry.item, entry.by, entry.date) in had:
            continue
        key = entry.item or entry.subject
        session = next((pathlib.PurePosixPath(path).stem for path in sorted(changed) if path.startswith("sessions/")
                        and key in changed[path]), "")
        found[key] = {"heading": heading_for(pages[entry.path], key) if entry.item else key, "by": entry.by,
                      "date": entry.date, "session": session}
    return found


def read_json_argument(flag, path):
    """JSON from a file, or from standard input when the path is '-' (so a skill can pass free text without quoting it)."""
    try:
        text = sys.stdin.read() if path == "-" else pathlib.Path(path).read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolError(f"{flag} {path} cannot be read as JSON: {exc}") from exc


def read_whys(path, keys):
    """{group key: the reader's reason} from JSON; a key that names no group is an error, not a lost reason."""
    if not path:
        return {}
    data = read_json_argument("--whys", path)
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise ToolError("--whys must be a JSON object of group -> reason text.")
    unknown = sorted(set(data) - set(keys))
    if unknown:
        raise ToolError(f"--whys names {', '.join(unknown)}, which is not a group of this proposal. The groups are: {', '.join(keys)}.")
    return {k: v.strip() for k, v in data.items() if v.strip()}


def private_strings(root, workspace):
    """Exact strings no proposal may carry: where this person's files live and where the copy came from."""
    home = str(pathlib.Path.home())
    return [home, os.path.expanduser("~"), str(root), os.path.abspath(str(root)), str(workspace.get("source_path") or ""),
            str(workspace.get("planner_path") or ""), str(PLANNER_PROGRAM)]


def text_with_home_hidden(files, home):
    """The text files with this person's home folder written as <home>; binary files are left as they are."""
    return {path: (proposal.hide_home(data.decode("utf-8"), home).encode("utf-8") if not drafts.is_binary(data) else data)
            for path, data in files.items()}


def print_groups(groups, as_json, out):
    if as_json:
        print(json.dumps([{"group": g.key, "pending": g.pending, "changes": [{"path": p, "hunk": h, "also": list(a)} for p, h, a in g.hunks]}
                          for g in groups], indent=2), file=out)
        return
    for g in groups:
        files = sorted({p for p, _, _ in g.hunks})
        print(f"  {g.key}{' (pending decision)' if g.pending else ''}: {len(g.hunks)} change(s) in {', '.join(files)}", file=out)


def refuse_while_conflicted(root):
    """A proposal built while a replay conflict is open would carry the owner's page as if it were the reader's choice."""
    try:
        open_conflicts = replays.open_conflicts(root)
    except opening.OpenError as exc:
        raise ToolError(str(exc)) from exc
    if not open_conflicts:
        return
    listing = "; ".join(f"{c['path']} (your version: {c['mine']})" for c in open_conflicts[:5])
    raise ToolError(f"{len(open_conflicts)} page(s) still conflict with the owner's newer copy: {listing}. Open each pair, copy over what you want to keep, "
                    "then delete the .mine file. Then run propose again. Nothing was written.")


def cmd_propose(args, out):
    root = pathlib.Path(args.vault).resolve()
    found = detect_role(root)
    if found.role == roles.OWNER:
        raise ToolError("You work in this vault's git repo, so you are an owner and decide directly: change it on a session branch and open a PR. "
                        "A proposal is how a reader, who has no git, sends changes to an owner. Nothing was written.")
    if found.role != roles.READER:
        raise ToolError(f"cannot propose: {found.reason}.")
    today, _ = parse_today(args.today)
    refuse_while_conflicted(root)
    baseline_dir = root / copies.BASELINE
    if not baseline_dir.is_dir():
        raise ToolError(f"{baseline_dir} is missing, so I have nothing to compare your pages with. Open the published copy again into a new folder.")
    try:
        workspace = copies.read_workspace(root)
        stamp = copies.read_own_stamp(root) or {}
        baseline, working = copies.read_tree(baseline_dir, skip_published=True), copies.read_tree(root, skip_published=True)
        if args.rewrite_home:
            working = text_with_home_hidden(working, str(pathlib.Path.home()))
        built = proposal.build(baseline, working, workspace.get("base_commit", ""), workspace.get("initiative") or stamp.get("initiative", ""))
    except (copies.SourceUnreadable, opening.OpenError, proposal.ProposalError) as exc:
        raise ToolError(str(exc)) from exc
    if not built.files and not built.binaries:
        raise ToolError("You have not changed anything since you opened this copy, so there is nothing to propose.")
    changed = {path: working[path].decode("utf-8") for path, *_ in drafts.changed_files(baseline, working) if path in working and not drafts.is_binary(working[path])}
    waiting = new_pending(root, baseline_dir, changed)
    groups = proposal.groups(built.files, set(waiting))
    if args.groups:
        if not args.json:
            print(f"planner propose: {len(groups)} group(s) of change; each needs a reason from you.", file=out)
        print_groups(groups, args.json, out)
        return 0
    if not args.title:
        raise ToolError("--title is needed: a few words naming what this proposal changes. Run with --groups first to see what it holds.")
    whys = read_whys(args.whys, [g.key for g in groups])
    note = {"title": args.title, "author": workspace.get("author") or "", "written": today, "groups": groups, "whys": whys, "pending": waiting,
            "files": built.files, "binaries": built.binaries, "check": check_summary(root, baseline_dir, today),
            "base": {"initiative": workspace.get("initiative") or stamp.get("initiative", ""), "short": workspace.get("base_commit", "")[:7],
                     "date": workspace.get("base_date", ""), "owner": (stamp.get("owner") or {}).get("name") or "the owner"}}
    if not note["author"]:
        raise ToolError("this workspace records no author name; re-open the copy with --author \"Your Name\".")
    forbidden = private_strings(root, workspace)
    parent = pathlib.Path(args.out_dir).expanduser().resolve() if args.out_dir else root.parent / "proposals"
    name = proposal_files.folder_name(today, args.title, parent)
    try:
        target = proposal_files.write(parent, name, {proposal_files.NOTE: proposal.render_markdown(note), proposal_files.PATCH: built.patch},
                                      args.zip, lambda texts: proposal.privacy_hits(texts, forbidden))
    except proposal_files.ProposalIOError as exc:
        raise ToolError(str(exc)) from exc
    contact = (stamp.get("owner") or {}).get("contact") or "the owner"
    print(f"planner propose: wrote {target} ({len(built.files)} text files patched, {len(built.binaries)} binary listed, {len(waiting)} pending decision(s) first).", file=out)
    print(f"  Check on this copy: {proposal.check_phrase(note['check'])}." + (" The errors are listed first in the proposal; they did not stop it." if note["check"]["errors"] else ""), file=out)
    print(f"  Send {'that file' if args.zip else 'that folder'} to {note['base']['owner']} ({contact}). Nothing was sent from here.", file=out)
    return 0


def worktree_vault(args):
    """(worktree top, vault folder in it, branch) for a command that works inside a proposal's worktree."""
    vault = pathlib.Path(args.vault).resolve()
    try:
        top, branch = reviewgit.toplevel(vault), reviewgit.branch_name(vault)
    except vaultgit.GitUnavailable as exc:
        raise ToolError(f"{vault} is not a git work tree ({exc}). Run this inside the proposal's worktree, the folder `planner proposals review` printed.") from exc
    if not branch.startswith("proposal/"):
        raise ToolError(f"{vault} is on branch '{branch}', not a proposal/ branch. This changes files and commits, so it only runs in the worktree `planner proposals review` made.")
    return top, vault, branch


def load_proposal(source):
    try:
        loaded = proposal_files.read(source)
        parsed = review.parse_patch(loaded.patch)
    except (proposal_files.ProposalIOError, review.ReviewError) as exc:
        raise ToolError(str(exc)) from exc
    note = review.parse_note(loaded.note) if loaded.note else None
    refs, problems = review.groups_for(parsed, note)
    return loaded, parsed, note, refs, problems


def review_refusals(root, parsed, slug, branch, folder):
    """Why a review cannot start, in plain words, or nothing."""
    if not reviewgit.commit_exists(root, parsed.base):
        raise ToolError(f"This proposal was written against commit {parsed.base[:7]}, which is not in this clone. It is the commit the reader's copy was "
                        "published from: fetch the clone it came from (git fetch origin) and review again.")
    dirty = vaultgit.uncommitted(root)
    if dirty:
        raise ToolError(f"Your checkout has {len(dirty)} uncommitted file(s) ({dirty[0].strip()}...), so I did not start. Commit or stash them: "
                        "a review starts from a known state, and its branch is made from committed work.")
    if reviewgit.branch_exists(root, branch):
        raise ToolError(f"Branch {branch} already exists. Finish or delete it, or pass --slug with another name.")
    if folder.exists():
        raise ToolError(f"{folder} already exists. Remove it (git worktree remove) or pass --worktree with another folder.")


def review_state(parsed, note, refs, problems, facts):
    return {"title": note.title if note else "", "author": note.author if note else "", "base": parsed.base, "behind": facts["behind"],
            "branch": facts["branch"], "worktree": str(facts["worktree"]), "applied": facts["applied"], "commit": facts["commit"],
            "conflicts": facts["conflicts"], "check": facts["check"], "claim": list(note.claim) if note and note.claim else None,
            "pending": facts["pending"], "problems": problems,
            "groups": [{"group": g.key, "pending": g.pending, "changes": [{"path": p, "hunk": h} for p, h in g.hunks]} for g in refs]}


def run_render_and_check(vault_dir, worktree, today):
    """(note on render, check counts) after a clean apply. Render churn is committed on its own."""
    buffer = io.StringIO()
    render_code = cmd_render(argparse.Namespace(vault=str(vault_dir), discard_edits=False), buffer)
    rendered = ""
    if render_code != 0:
        rendered = "render refused: " + (buffer.getvalue().strip().splitlines() or ["no reason given"])[0]
    elif reviewgit.has_changes(worktree):
        rendered = f"render changed generated blocks; committed {reviewgit.commit_all(worktree, 'Render generated blocks after the proposal')}"
    found = vault_findings(vault_dir, today)
    errors = [f for f in found if f.is_error]
    return rendered, {"errors": len(errors), "warnings": len(found) - len(errors), "error_lines": [f.format() for f in errors[:10]]}


def print_review(state, out):
    who = f" from {state['author']}" if state["author"] else ""
    print(f"planner proposals review: \"{state['title'] or 'changes.patch'}\"{who}", file=out)
    moved = f"; the vault has moved {state['behind']} commit(s) since" if state["behind"] else ""
    print(f"  Base {state['base'][:7]}{moved}. Branch {state['branch']} in {state['worktree']}.", file=out)
    if state["applied"]:
        print(f"  Applied cleanly and committed {state['commit']}.", file=out)
    else:
        print(f"  CONFLICTS in {', '.join(state['conflicts'])}. The files hold conflict markers; resolve them in the worktree, then commit.", file=out)
    if state["check"]:
        claim = state["claim"]
        said = f"the proposal said {claim[0]} errors, {claim[1]} warnings" if claim else "the proposal made no claim"
        print(f"  Check: {state['check']['errors']} errors, {state['check']['warnings']} warnings ({said}).", file=out)
        for line in state["check"]["error_lines"]:
            print(f"    {line}", file=out)
    for line in state.get("notes", []):
        print(f"  {line}", file=out)
    for problem in state["problems"]:
        print(f"  Note: {problem}", file=out)
    print("  Groups, pending decisions first:", file=out)
    for g in state["groups"]:
        print(f"    {g['group']}{' (pending decision)' if g['pending'] else ''}: {len(g['changes'])} change(s)", file=out)


def cmd_proposals_review(args, out):
    root = pathlib.Path(args.vault).resolve()
    found = detect_role(root)
    if found.role != roles.OWNER:
        raise ToolError("Reviewing a proposal is the owner's job and needs the vault's git repo; "
                        + ("this is a published copy." if found.role == roles.READER else f"{found.reason}."))
    today, _ = parse_today(args.today)
    loaded, parsed, note, refs, problems = load_proposal(args.source)
    slug = args.slug or publish.slug(note.title if note and note.title else "proposal")
    branch = f"proposal/{slug}"
    try:
        top = reviewgit.toplevel(root)
    except vaultgit.GitUnavailable as exc:
        raise ToolError(f"git stopped the review: {exc}") from exc
    folder = pathlib.Path(args.worktree).expanduser().resolve() if args.worktree else top.parent / f"{top.name}-proposal-{slug}"
    try:
        review_refusals(root, parsed, slug, branch, folder)
        start = reviewgit.start_ref(root)
        behind = reviewgit.commits_between(root, parsed.base, start)
        prefix = reviewgit.prefix(root)
        reviewgit.add_worktree(root, folder, branch, start)
        clean, conflicts, words = reviewgit.apply_three_way(folder, loaded.patch.decode("utf-8"), prefix)
        if not clean and not conflicts:
            reviewgit.discard_worktree(root, folder, branch)
            raise ToolError(f"git could not apply this proposal, and nothing was changed: {words}")
        try:
            untrusted.check_applied(reviewgit.changed_entries(folder), prefix)
        except untrusted.Refused as exc:
            reviewgit.discard_worktree(root, folder, branch)
            raise ToolError(f"I stopped before committing anything: {exc} Nothing was changed.") from exc
        title = note.title if note and note.title else "changes.patch"
        author = note.author if note and note.author else "a reader"
        commit, check, notes = "", None, []
        vault_dir = folder / prefix if prefix else folder
        if clean:
            commit = reviewgit.commit_all(folder, f"Proposal: {title} (from {author})")
            rendered, check = run_render_and_check(vault_dir, folder, today)
            if rendered:
                notes.append(rendered)
            pending_now = [{"item": p.item or p.subject, "by": p.by, "date": p.date, "path": p.path} for p in pending.items(load_vault(vault_dir))]
        else:
            pending_now = []
            notes.append("check and render wait until the conflicts are resolved.")
    except vaultgit.GitUnavailable as exc:
        raise ToolError(f"git stopped the review: {exc}") from exc
    state = review_state(parsed, note, refs, problems, {"behind": behind, "branch": branch, "worktree": folder, "applied": clean, "commit": commit,
                                                       "conflicts": conflicts, "check": check, "pending": pending_now})
    state["notes"] = notes
    if args.json:
        print(json.dumps(state, indent=2), file=out)
    else:
        print_review(state, out)
    return 0 if clean else 1


def cmd_proposals_accept(args, out):
    top, vault_dir, branch = worktree_vault(args)
    item = args.item
    try:
        vault = load_vault(vault_dir)
        entry = next((p for p in pending.items(vault) if item in (p.item, p.subject)), None)
        if entry is None:
            raise ToolError(f"{item} carries no well-formed **Pending approval:** marker in this worktree, so there is nothing to accept.")
        target = vault_dir / entry.path
        text, by, date = review.accept_pending(entry.path, target.read_text(encoding="utf-8"), entry.item, args.by)
        target.write_bytes(text.encode("utf-8"))
        commit = reviewgit.commit_all(top, f"Accept {item} proposed by {by} on {date}: decided by {args.by}")
    except (review.ReviewError, OSError, UnicodeDecodeError) as exc:
        raise ToolError(str(exc)) from exc
    except vaultgit.GitUnavailable as exc:
        raise ToolError(f"git stopped the accept: {exc}") from exc
    print(f"planner proposals accept: {item} is now {args.by}'s decision, crediting {by} ({date}); committed {commit} on {branch}.", file=out)
    return 0


def cmd_proposals_reject(args, out):
    top, vault_dir, branch = worktree_vault(args)
    loaded, parsed, note, refs, problems = load_proposal(args.proposal)
    group = next((g for g in refs if g.key == args.group), None)
    if group is None:
        raise ToolError(f"'{args.group}' is not a group of this proposal. The groups are: {', '.join(g.key for g in refs)}.")
    if not args.reason.strip():
        raise ToolError("--reason is needed: the reader will read why their change was turned down.")
    try:
        if reviewgit.unmerged(top) or reviewgit.has_changes(top):
            raise ToolError("This worktree has uncommitted or conflicted files. Resolve and commit them first, so the rejection is a clean step of its own.")
        ok, words = reviewgit.revert(top, review.subpatch(parsed, group), reviewgit.prefix(vault_dir))
        if not ok:
            raise ToolError(f"I could not take '{group.key}' back out automatically (the pages have changed since): {words} Edit the files yourself, then record it as edited.")
        commit = reviewgit.commit_all(top, f"Reject {group.key} from the proposal: {' '.join(args.reason.split())}")
    except review.ReviewError as exc:
        raise ToolError(str(exc)) from exc
    except vaultgit.GitUnavailable as exc:
        raise ToolError(f"git stopped the reject: {exc}") from exc
    print(f"planner proposals reject: took {group.key} back out ({len(group.hunks)} change(s)); committed {commit} on {branch}.", file=out)
    return 0


def cmd_proposals_answer(args, out):
    top, vault_dir, branch = worktree_vault(args)
    loaded, parsed, note, refs, problems = load_proposal(args.proposal)
    decisions = read_json_argument("--decisions", args.decisions)
    if not isinstance(decisions, list) or not all(isinstance(d, dict) for d in decisions):
        raise ToolError("--decisions must be a JSON list of {group, outcome, reason} objects.")
    today, _ = parse_today(args.today)
    try:
        reviewer = vaultgit.user_identity(vault_dir)[0]
        if not reviewer:
            raise ToolError("git user.name is not set, so the answer cannot say who reviewed it.")
        text = review.answer_markdown(note or review.Note("changes.patch", "", None, ()), refs, decisions, reviewer, today, branch,
                                      reviewgit.head_short(top), parsed.base[:7])
    except review.ReviewError as exc:
        raise ToolError(str(exc)) from exc
    except vaultgit.GitUnavailable as exc:
        raise ToolError(f"git stopped the answer: {exc}") from exc
    forbidden = [str(top), str(vault_dir), str(pathlib.Path.home()), os.path.expanduser("~"), str(pathlib.Path(args.proposal).expanduser().resolve())]
    hits = proposal.privacy_hits({"answer.md": text}, forbidden)
    if hits:
        raise ToolError(f"answer.md line {hits[0][1]} holds a private path or name: '{hits[0][2]}'. Reword that reason and answer again. Nothing was written.")
    try:
        target = proposal_files.write_answer(loaded.answer_to, text)
    except proposal_files.ProposalIOError as exc:
        raise ToolError(str(exc)) from exc
    print(f"planner proposals answer: wrote {target} ({len(refs)} group(s) answered). Send it to {note.author if note and note.author else 'the reader'}. Merging {branch} is your normal git step; nothing was pushed.", file=out)
    return 0


def cmd_where(args, out):
    """Which program a skill would run, and why each earlier rule was passed over. For /planner:where and for bug reports."""
    vault = pathlib.Path(args.vault)
    recorded = ""
    if (vault / copies.WORKSPACE).is_file():  # an owner's vault has none, and the rule is simply not applicable
        try:
            recorded = copies.read_workspace(vault).get("planner_path") or ""
        except copies.SourceUnreadable as exc:
            raise ToolError(str(exc)) from exc
    chosen, tried = pluginroot.resolve(args.plugin_root, args.skill_dir, str(vault), recorded, lambda path: pathlib.Path(path).is_file())
    for found in tried:
        print(f"{found.source}: {found.path or '(none)'}{' -> ' + found.skipped if found.skipped else ' -> found'}", file=out)
    if chosen is None:
        print(pluginroot.NOT_FOUND, file=out)
        return 1
    print(f"planner where: run python3 {chosen.path}", file=out)
    return 0


def cmd_check(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, origin = parse_today(args.today)
    started = time.perf_counter()
    vault = load_vault(root)
    items = gate_items(vault, args.gate, args.item)
    findings = rules.check(vault, today, gate=args.gate, items=items) + conventions_findings(root)
    errors = sum(1 for f in findings if f.is_error)
    warnings = len(findings) - errors
    elapsed = time.perf_counter() - started
    print(f"planner check: {errors} errors, {warnings} warnings in {len(vault.pages)} pages. "
          f"Today is {today} ({origin}). Took {elapsed:.2f} s." + (f" Gate: {args.gate}." if args.gate else "")
          + (f" Items: {', '.join(items)}." if items else ""), file=out)
    for finding in findings:
        print(finding.format(), file=out)
    if args.gate == "epics" and not errors:
        resting = questions.load_bearing_assumptions(vault)
        if resting:
            print(f"Note: the epics gate passed, and it rests on {len(resting)} load-bearing "
                  f"assumption{'' if len(resting) == 1 else 's'} about high-severity questions: {', '.join(resting)}. "
                  "Each holds until its signpost shows.", file=out)
    return 1 if errors else 0


def gate_items(vault, gate, items):
    """The items a grill gate checks. A grill gate needs at least one, and only a grill gate takes any."""
    items = list(items or ())
    if gate == "grill" and not items:
        raise ToolError("--gate grill needs the agenda: one --item <ID> per item, for example --item CON-001.")
    if items and gate != "grill":
        raise ToolError("--item names a Grill's agenda, so it goes with --gate grill.")
    missing = [i for i in items if i not in vault.known_ids()]
    if missing:
        raise ToolError(f"--item {', '.join(missing)} is not an ID in this vault.")
    return sorted(set(items))


def cmd_render(args, out):
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    texts, changed, discarded, refusals = render.render_vault(vault, args.discard_edits)
    if refusals:
        print(f"planner render: wrote nothing, {len(refusals)} problems.", file=out)
        for finding in refusals:
            print(finding.format(), file=out)
        return 1
    pending_writes = {}
    for path, text in sorted(texts.items()):
        target = root / path
        original = target.read_bytes()
        if b"\r\n" in original:
            text = text.replace("\n", "\r\n")  # keep the file's own line endings
        data = text.encode("utf-8")
        if original.startswith(codecs.BOM_UTF8):
            data = codecs.BOM_UTF8 + data
        pending_writes[target] = data
    try:
        atomic.write_all_atomic(pending_writes)
    except atomic.WriteFailed as exc:
        def names(paths):
            return ", ".join(p.relative_to(root).as_posix() for p in paths) or "none"
        raise ToolError(f"render could not finish: {exc}. Written: {names(exc.written)}. Not written: {names(exc.unwritten)}. "
                        "Fix the cause and run planner render again; it only rewrites blocks that are out of date.") from exc
    for path, name, old in discarded:
        print(f"{path}: discarded a hand edit in '{name}':", file=out)
        for line in old.split("\n"):
            print(f"  - {line}", file=out)
    print(f"planner render: {len(changed)} blocks changed.", file=out)
    for path, name in changed:
        print(f"  {path}: {name}", file=out)
    return 0


# What git says when it ran fine and the answer is "no": not a repository, no commit yet, no such remote.
GIT_SAYS_NO = ("not a git repository", "unknown revision", "ambiguous argument", "bad revision", "no such remote",
               "does not have any commits", "needed a single revision")


def git(root, *args):
    """Output of a git command in the vault. "" means git ran and answered no (no repository, no commit, no remote).
    A git that is missing, times out or fails for any other reason raises GitUnavailable: it must never read as that
    answer, or a stamp would claim a clean copy it never checked."""
    code, out, err = vaultgit.run_git(root, *args, timeout=10)
    if code == 0:
        return out
    if any(phrase in err.lower() for phrase in GIT_SAYS_NO):
        return ""
    raise vaultgit.GitUnavailable(f"git {' '.join(args)} failed: {err or out or 'no message'}")


def remote_url(root):
    """The origin URL, "" when there is none, or words saying git did not answer."""
    try:
        return git(root, "remote", "get-url", "origin")
    except vaultgit.GitUnavailable as exc:
        return f"unknown, git did not answer ({exc})"


def changes_note(root):
    """" with uncommitted changes", "", or words saying git could not tell."""
    try:
        return " with uncommitted changes" if git(root, "status", "--porcelain", "--", ".") else ""
    except vaultgit.GitUnavailable as exc:
        return f" (could not tell whether it has uncommitted changes: {exc})"


def commit_stamp(root, override=""):
    """The commit a generated file is stamped with: the override, the short HEAD, or words that say what could not be
    learned. Never a clean-looking stamp from a git that did not answer."""
    if override:
        return override
    try:
        commit = git(root, "rev-parse", "--short", "HEAD") or "an uncommitted copy"
        dirty = bool(git(root, "status", "--porcelain", "--", "."))
    except vaultgit.GitUnavailable as exc:
        return f"unknown, git did not answer ({exc})"
    return commit + (" with uncommitted changes" if dirty else "")


# Where a number can live besides a session branch: the default branch, here and on origin. A session branch that merged
# and was deleted leaves its numbers only here.
MAIN_REFS = ("refs/heads/main", "refs/heads/master", "refs/remotes/origin/main", "refs/remotes/origin/master")


def cmd_next_id(args, out):
    """The next free ID for a prefix, counting this working tree, the default branch and every session branch, local and
    remote. It reads the remote refs this clone last fetched, so run `git fetch` first to see numbers pushed since."""
    root = pathlib.Path(args.vault).resolve()
    load_config(root)  # a folder that is not a vault has no IDs to count
    texts = [path.read_text(encoding="utf-8") for path in vault_files(root)[0]]
    if (root / ".git").exists() and ids.PREFIX_RE.match(args.prefix):
        refs = git_strict(root, "for-each-ref", "--format=%(refname)", "refs/heads/session/", "refs/remotes/origin/session/",
                          *MAIN_REFS)
        for ref in refs.split():
            texts.append(git_strict(root, "grep", "-h", "-E", "-o", rf"{args.prefix}-[0-9]+", ref, "--", "*.md",
                                    allow_no_match=True))
    try:
        print(ids.next_id(args.prefix, texts), file=out)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return 0


def git_strict(root, *args, allow_no_match=False):
    """Output of a git command, or ToolError with git's own message. For commands whose
    failure must never read as "nothing changed". Output that is not UTF-8 is a failure too."""
    try:
        result = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=false", *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ToolError(f"git {' '.join(args)} could not run: {exc}") from exc
    if result.returncode == 1 and allow_no_match and not result.stderr:
        return ""  # git grep exits 1 when nothing matched, which is an answer
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip() or result.stdout.decode("utf-8", "replace").strip()
        raise ToolError(f"git {' '.join(args)} failed: {message}")
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ToolError(f"git {' '.join(args)} gave output that is not UTF-8: {exc}") from exc


def read_asset(name):
    path = ASSETS / name
    if not path.is_file():
        raise ToolError(f"{path} is missing, so the viewer cannot work offline. Restore it from the toolkit repo.")
    return path.read_text(encoding="utf-8")


def cmd_view(args, out):
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    today, _ = parse_today(args.date)
    commit = commit_stamp(root, args.commit)
    if args.commit:
        commit += changes_note(root)  # a named commit still says when the files differ from it
    findings = rules.check(vault, today)
    errors = sum(1 for f in findings if f.is_error)
    stamp = {
        "commit": commit,
        "date": today,
        "repo": export.redact_remote(args.repo_url or remote_url(root)) or "no repository URL recorded",
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
    try:
        atomic.write_atomic(target, html)
    except atomic.WriteFailed as exc:
        raise ToolError(f"cannot write {target}: {exc}") from exc
    print(f"planner view: wrote {target} ({len(viewer.bundled(vault))} pages). "
          f"Built from {stamp['commit']} on {stamp['date']}. "
          f"Check at build time: {errors} errors, {stamp['warnings']} warnings.", file=out)
    return 0


# What a vault's .gitignore says when it keeps the tool's own files out of commits (the template's does).
# `.planner/*` is the template's form: it lets `!.planner/explorer-pins.json` keep the shared layout in git.
IGNORES_DASHBOARD = (publish.DASHBOARD_PATH, f"/{publish.DASHBOARD_PATH}", "*.html", "/*.html", "**/*.html")


def ignores_dashboard(root):
    """True when the vault's .gitignore keeps dashboard.html out of git, so the page would not travel with the vault."""
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return False
    return any(line.strip() in IGNORES_DASHBOARD for line in gitignore.read_text(encoding="utf-8").splitlines())


def live_freshness(root, found, today, unavailable):
    """The helper's answer to GET /freshness: the same report `planner freshness --json` prints, asked again now."""
    try:
        return freshness_report(root, found, vaultgit.FETCH_TIMEOUT, today).as_dict()
    except ToolError as exc:
        raise unavailable(str(exc)) from exc


def cmd_explore(args, out):
    """Build the explorer page: dashboard.html at the vault root unless --out says otherwise, so it travels with the vault
    in git or OneDrive. The pinned layout goes in .planner/; nothing is written beside the plugin."""
    from planner.explorer import build as explorer, pins as explorer_pins, serve as explorer_serve  # lazy: the explorer imports this module
    root = pathlib.Path(args.vault).resolve()
    today, _ = parse_today(args.today)
    target = pathlib.Path(args.out) if args.out else root / publish.DASHBOARD_PATH
    found = detect_role(root)
    try:
        lines = explorer.generate(root, target, today, pins_path=root / explorer_pins.PINS_FILE,
                                  assets_config=args.assets, design_args=args.design, theme=args.theme,
                                  freshness=page_freshness(root, found, today), breakdown_args=args.breakdown,
                                  built=page_built(root, found, today))
    except explorer.ExplorerError as exc:
        raise ToolError(str(exc)) from exc
    for line in lines:
        print(f"planner explore: {line}", file=out)
    if ignores_dashboard(root):
        print(f"planner explore: this vault's .gitignore lists {publish.DASHBOARD_PATH}, so colleagues who pull the repo will not get the page. "
              f"Remove that line from .gitignore, or build with --out somewhere else.", file=out)
    if args.serve:
        if not 0 <= args.port <= 65535:
            raise ToolError(f"--port {args.port} is not a port number (0 to 65535)")
        link = copies.first_symlink(root)
        if link:
            raise ToolError(f"I will not serve Ask Claude for this vault: {untrusted.link_refusal(link)}")
        try:
            explorer_serve.serve(root, target, args.port, args.model, not args.no_open, lambda line: print(f"planner explore: {line}", file=out, flush=True),
                                 freshness=lambda: live_freshness(root, found, today, explorer_serve.FreshnessUnavailable),
                                 pins=root / explorer_pins.PINS_FILE)
        except OSError as exc:
            raise ToolError(f"cannot serve the page on port {args.port}: {exc}") from exc
    return 0


def cmd_health(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, _ = parse_today(args.today)
    vault = load_vault(root)
    commit = commit_stamp(root)
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


def print_search(answer, out):
    """Hits as a reader scans them: where, the heading, one line of what it says, and the flows that cross it."""
    if answer.get("not_found"):
        meant = ", ".join(answer["terms"]) or "nothing but common words"
        print(f"planner query search: nothing holds enough of: {meant}. Try the vault's own words; 12-glossary.md has them.",
              file=out)
        return
    print(f"planner query search: {len(answer['hits'])} places for {', '.join(answer['terms'])}"
          + (f", {answer['more']} more with --limit" if answer["more"] else "") + ".", file=out)
    for n, hit in enumerate(answer["hits"], 1):
        where = hit["page"] + (f" › {hit['heading']}" if hit["heading"] else "")
        print(f"{n}. {hit['title']}: {where}", file=out)
        print(f"   {hit['snippet']}", file=out)
        if hit["flows"]:
            print(f"   Flows that cross it: {'; '.join(f['title'] + ' (' + f['page'] + ')' for f in hit['flows'])}", file=out)


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
    elif args.what == "search":
        answer = search.search(vault, args.words, limit=args.limit)
        if not args.json:
            print_search(answer, out)
            return 1 if answer.get("not_found") else 0
    else:
        today, _ = parse_today(args.today)
        answer = query.status(vault, today)
    print_answer(answer, args.json, out)
    return 1 if answer.get("not_found") else 0


def cmd_questions(args, out):
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    if args.area is not None and args.area not in vault.catalogue.area_codes:
        raise ToolError(f"--area {args.area} is not an area of catalogue v{vault.catalogue.version}. "
                        f"Use one of: {', '.join(vault.catalogue.area_codes)}.")
    if args.subject is not None and questions.subject(vault, args.subject) is None:
        answer = {"subject": args.subject, "not_found": True}
        print(json.dumps(answer, indent=2) if args.json else
              f"planner questions: {args.subject} is not a subject in this vault: an initiative, app, contract, "
              "capability, party or stored value ID.", file=out)
        return 1
    if args.all and not args.digest:
        raise ToolError("--all goes with --digest: it prints every line of the digest in full.")
    if args.stats:
        if args.open or args.subject:
            raise ToolError("--stats counts every copy the vault owes. Leave out --open and --subject.")
        answer = questions.stats(vault, args.area)
        if args.json:
            print(json.dumps(answer, indent=2, ensure_ascii=False), file=out)
        else:
            print_stats(answer, out)
        return 0
    if args.digest:
        answer = questions.digest(vault, args.area, args.subject)
        if args.json:
            print(json.dumps(answer, indent=2, ensure_ascii=False), file=out)
        else:
            print_digest(answer, out, vault.catalogue.area_codes, args)
        return 0
    answer = questions.listing(vault, args.area, args.open, args.subject)
    if args.json:
        print(json.dumps(answer, indent=2, ensure_ascii=False), file=out)
        return 0
    print(questions_header(answer, args), file=out)
    for copy in answer["copies"]:
        print(question_line(copy), file=out)
    for row in answer["reviewer"]:
        print(question_line(row), file=out)
    return 0


def questions_header(answer, args):
    kept = [f"area {args.area}" if args.area else "", f"subject {args.subject}" if args.subject else "",
            "open only" if args.open else ""]
    where = ", ".join(k for k in kept if k)
    line = f"planner questions: {answer['coverage']}." + (f" Showing {where}." if where else "")
    if answer["reviewer_questions"]:
        count = answer["reviewer_questions"]
        line += f" {count} reviewer question{'' if count == 1 else 's'}, {answer['reviewer_open']} open."
    return line


BLOCKS_SHOWN = 3


def blocks_text(units):
    """The units a question holds up. A long list is cut to a count and the first few: --json has them all."""
    if len(units) <= BLOCKS_SHOWN + 2:
        return ", ".join(units)
    return f"{len(units)} items: {', '.join(units[:BLOCKS_SHOWN])}, …"


def print_digest(answer, out, area_codes, args):
    """The consequential lines in full, then the rest as one count per area with the command that lists them,
    so a long digest stays readable and nothing leaves it. --all prints every line in full."""
    groups = answer["groups"]
    short = len(groups) <= questions.DIGEST_READS_WHOLE
    full = groups if args.all or short else [g for g in groups if questions.consequential(g)]
    rest = [g for g in groups if g not in full]
    lines = f"{len(groups)} line{'' if len(groups) == 1 else 's'} to take, most consequential first"
    if rest:
        lines += f": {len(full)} in full, {len(rest)} more counted by area"
    print(f"planner questions --digest: {answer['coverage']}. {lines}.", file=out)
    for n, group in enumerate(full, start=1):
        print_digest_line(n, group, out)
    if not rest:
        return
    narrow = (f" --area {args.area}" if args.area else "") + (f" --subject {args.subject}" if args.subject else "")
    for code in area_codes:
        count = sum(1 for g in rest if g["area"] == code)
        if count:
            print(f"{code}: {count} more (normal). List them: planner questions --open --digest --all"
                  f"{narrow if args.area else narrow + ' --area ' + code}", file=out)
    print(f"Every line in full: planner questions --open --digest --all{narrow}", file=out)


def print_digest_line(n, group, out):
    head = f"[{group['area']}] {group['severity']}"
    if group["blocks"]:
        head += f", blocks {blocks_text(group['blocks'])}"
    print(f"{n}. {head}: {group['question']}", file=out)
    why = ", ".join(f"{digest_label(k)} {v}" if len(group["why"]) > 1 else digest_label(k)
                    for k, v in group["why"].items())
    count = len(group["copies"])
    lead = f"{count} copies ({why}): " if count > 1 else f"({why}) "
    many = ": one answer for all?" if count > 1 else ""
    print(f"   {lead}{', '.join(group['copies'])}{many}", file=out)


def digest_label(label):
    """A state label as the digest prints it inside brackets: `invalid (open)` reads `invalid: open`."""
    return label.replace("invalid (", "invalid: ")[:-1] if label.startswith("invalid (") else label


def print_stats(answer, out):
    print(f"planner questions --stats: how each entry of catalogue v{answer['catalogue']} ended in this vault. "
          "An entry that nearly always ends not-applicable is one to prune or tighten; that is your call.", file=out)
    for entry in answer["entries"]:
        states = ", ".join(f"{k} {v}" for k, v in entry["states"].items()) or "nothing owed"
        share = f"{entry['not_applicable_share'] * 100:.0f}%"
        print(f"{entry['entry']} | {entry['area']} | owed {entry['owed']} | not-applicable {entry['not_applicable']} "
              f"of {entry['owed']} ({share}) | {states}", file=out)


def question_line(entry):
    state = (entry["state"] if entry["valid"] else f"invalid ({entry['state']})") + (f" via {entry['via']}" if entry["via"] else "")
    if not entry["pending"]:
        blocked = "settled"
    else:
        blocked = f"blocks {blocks_text(entry['blocks'])}" if entry["blocks"] else "blocks nothing"
    return " | ".join((entry["id"], entry["area"], entry["severity"], state, entry["subject"] or "reviewer", blocked,
                       entry["question"]))


def unfence(text):
    """A reply that is one fenced block, as models often send JSON, without its fence. Anything else as it is."""
    lines = text.strip().split("\n")
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return text


def read_findings(folder, codes):
    """({area: (data, problem)}, ignored file names) from a folder of <AREA>.json files. A file that
    cannot be read or parsed makes its area "did not run" with the reason; it never stops the merge."""
    outputs, ignored = {}, []
    for path in sorted(folder.iterdir()):
        if path.name.startswith("."):
            continue  # .DS_Store and friends are not reviewer output
        if path.suffix != ".json" or path.stem not in codes:
            ignored.append(path.name)
            continue
        try:
            outputs[path.stem] = (json.loads(unfence(path.read_text(encoding="utf-8-sig"))), "")
        except (OSError, UnicodeDecodeError) as exc:
            outputs[path.stem] = (None, f"cannot read {path.name}: {exc}")
        except json.JSONDecodeError as exc:
            outputs[path.stem] = (None, f"{path.name} is not JSON: {exc.msg} at line {exc.lineno}")
    return outputs, ignored


def changed_pages(vault, value):
    """What --changed names, comma-separated: each page's vault path mapped to None for the whole page, or to its
    (first, last) line ranges for `<page>:40-52+88-90`. None when --changed is not given."""
    if value is None:
        return None
    paths, missing = {}, []
    for ref in (r.strip() for r in value.split(",")):
        if not ref:
            continue
        name, _, spans = ref.partition(":")
        page = reviews.find_page(vault, name)
        if page is None:
            missing.append(name)
            continue
        if not spans:
            paths[page.path] = None
            continue
        ranges = []
        for span in spans.split("+"):
            first, _, last = span.partition("-")
            if not (first.isdigit() and (last or first).isdigit()) or int(last or first) < int(first):
                raise ToolError(f"--changed {ref}: write the lines as <first>-<last>, joined by +, such as {name}:40-52+88-90.")
            ranges.append((int(first), int(last or first)))
        if paths.get(page.path, ()) is not None:
            paths[page.path] = (paths.get(page.path) or []) + ranges
    if missing:
        raise ToolError(f"--changed names {', '.join(missing)}, which {'is' if len(missing) == 1 else 'are'} not a page "
                        "in this vault. List the pages this session changed, and its own record.")
    return paths


def cmd_findings(args, out):
    root = pathlib.Path(args.vault).resolve()
    folder = pathlib.Path(args.folder)
    if not folder.is_dir():
        raise ToolError(f"{folder} is not a folder. Write each reviewer's output to <folder>/<AREA>.json, such as FIN.json.")
    vault = load_vault(root)
    only = parse_areas(args.areas, vault.catalogue.area_codes)
    skipped = parse_areas(args.skipped, vault.catalogue.area_codes, "--skipped") or ()
    if skipped and only is None:
        raise ToolError("--skipped goes with --areas: name the areas whose reviewers ran with --areas, "
                        "and the areas left out as out of scope with --skipped.")
    both = [code for code in skipped if code in (only or ())]
    if both:
        raise ToolError(f"{', '.join(both)} {'is' if len(both) == 1 else 'are'} in both --areas and --skipped. "
                        "An area either ran or was skipped.")
    outputs, ignored = read_findings(folder, vault.catalogue.area_codes)
    if only is not None:
        ignored += [f"{code}.json" for code in sorted(outputs) if code not in only]
    result = reviews.merge(vault, outputs, ignored, only, skipped, changed_pages(vault, args.changed))
    if args.json:
        print(json.dumps(result.as_dict(vault.catalogue.version), indent=2, ensure_ascii=False), file=out)
        return 0 if result.clean else 1
    ran = sum(1 for a in result.areas if a.ran)
    print(f"planner findings merge: {len(result.kept)} kept, {len(result.duplicates)} "
          f"duplicate{'' if len(result.duplicates) == 1 else 's'}, "
          f"{len(result.dropped)} dropped, from {ran} of {len(result.areas)} areas.", file=out)
    print(result.coverage, file=out)
    for title, entries in (("kept", result.kept), ("duplicates", result.duplicates), ("dropped", result.dropped)):
        if entries:
            print(f"{title}:", file=out)
        for entry in entries:
            print(finding_line(entry), file=out)
            if isinstance(entry, reviews.Kept):
                print(f"   {entry.finding}", file=out)
    for name in result.ignored:
        if name[:-5] in skipped:
            print(f"ignored: {name} is for an area skipped with --skipped {','.join(skipped)}", file=out)
        elif only is not None and name[:-5] in vault.catalogue.area_codes:
            print(f"ignored: {name} is not one of the areas asked for with --areas {','.join(only)}", file=out)
        else:
            print(f"ignored: {name} is not <AREA>.json for an area of catalogue v{vault.catalogue.version}", file=out)
    return 0 if result.clean else 1


def parse_areas(text, codes, flag="--areas"):
    """The area codes of --areas FIN,REG, or None for every area. An unknown code is a tool error."""
    if text is None:
        return None
    wanted = [w.strip().upper() for w in text.split(",") if w.strip()]
    unknown = [w for w in wanted if w not in codes]
    if not wanted or unknown:
        raise ToolError(f"{flag} takes area codes of the catalogue ({', '.join(codes)}); "
                        f"{', '.join(unknown) or 'it was empty'} {'is' if len(unknown) < 2 else 'are'} not one.")
    return tuple(c for c in codes if c in wanted)


def finding_line(entry):
    if isinstance(entry, reviews.Kept):
        return f"{entry.n}. [{', '.join(entry.area_list)}] {entry.severity}, {entry.copy}: {entry.question} | \"{entry.quote}\" in {entry.page}"
    if isinstance(entry, reviews.Duplicate):
        return f"- [{entry.area}] same as {entry.same_as}: {entry.question}"
    return f"- [{entry.area}] {entry.reason}: {entry.question}"


def handoff_app(vault, app_id):
    pages = vault.by_id.get(app_id)
    if not pages or pages[0].type != "app-building-blocks":
        raise ToolError(f"{app_id} is not the id of an app's building-blocks page, for example APP-booking.")
    return pages[0]


def stamp_commit(root, override):
    """The commit a handoff manifest records. A manifest is provenance, so a git that did not answer stops the
    handoff instead of writing a stamp nobody can trust."""
    commit = commit_stamp(root, override)
    if commit.startswith("unknown"):
        raise ToolError(f"cannot record the commit: {commit[len('unknown, '):]}. Pass --commit <sha> to state it yourself.")
    return commit


def cmd_handoff(args, out):
    root = pathlib.Path(args.vault).resolve()
    if len(args.words) == 2 and args.words[0] == "verify":
        return handoff_verify(root, args.words[1], out)
    if len(args.words) != 1 or args.words[0] == "verify":
        raise ToolError("Write planner handoff <APP-id>, or planner handoff verify <APP-id>.")
    refuse_if_reader(root, "Handing off an app")
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
    try:
        target.parent.mkdir(exist_ok=True)
        atomic.write_atomic(target, handoff.write(app_id, entries, commit, today))
    except OSError as exc:
        raise ToolError(f"cannot write {target.relative_to(root).as_posix()}: {exc.strerror or exc}. "
                        f"{schema.HANDOFF_DIR}/ must be a folder and {app_id}.md a file.") from exc
    print(f"planner handoff: wrote {target.relative_to(root).as_posix()}, {len(entries)} items, at {commit}.", file=out)
    return 0


def handoff_verify(root, app_id, out):
    vault = load_vault(root)
    app = handoff_app(vault, app_id)
    path = root / schema.HANDOFF_DIR / f"{app_id}.md"
    if path.is_dir():
        raise ToolError(f"{path.relative_to(root).as_posix()} is a folder, not a manifest file.")
    if not path.is_file():
        raise ToolError(f"{path.relative_to(root).as_posix()} does not exist. Run planner handoff {app_id} when the senior accepts the slice.")
    try:
        facts, accepted = handoff.read(path.read_text(encoding="utf-8"))
        handoff.check_manifest(app_id, facts, accepted)
    except (OSError, UnicodeDecodeError, handoff.ManifestError) as exc:
        raise ToolError(f"{path.relative_to(root).as_posix()} cannot be read as a manifest: {exc}") from exc
    diff = handoff.verify(accepted, handoff.slice_of(vault, app), vault)
    print(f"planner handoff verify {app_id}: {len(diff.changed)} changed, {len(diff.added)} added, {len(diff.removed)} removed "
          f"since the handoff at {facts.get('Commit', 'an unrecorded commit')} on {facts.get('Written', 'an unrecorded date')}.",
          file=out)
    for old, new in diff.changed:
        print(handoff.describe(old, new, new.id in diff.left), file=out)
    for entry in diff.added:
        print(f"added: {entry.id} ({entry.kind}, {entry.page}, {entry.state or 'no state'})", file=out)
    for entry in diff.removed:
        print(f"removed: {entry.id} ({entry.kind}, {entry.page}, was {entry.state or 'no state'})", file=out)
    return 1 if diff.breaks_acceptance else 0


def cmd_export(args, out):
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    git_trouble, dirty = "", False
    try:
        dirty = not args.commit and bool(git(root, "status", "--porcelain", "--", "."))
        remote = args.repo_url or git(root, "remote", "get-url", "origin")
        commit = args.commit or git(root, "rev-parse", "HEAD")
        prefix = git(root, "rev-parse", "--show-prefix")
    except vaultgit.GitUnavailable as exc:
        remote, commit, prefix, git_trouble = args.repo_url or "", args.commit or "", "", str(exc)
    base = export.web_url(remote)
    if base and commit:
        def link_for(path):
            return f"{base}/blob/{commit}/{export.link_path(prefix + path)}"
    else:
        def link_for(path):
            return path
    table = export.rows(vault, link_for)
    target = pathlib.Path(args.out)
    try:
        atomic.write_atomic(target, export.to_csv(table))
    except (OSError, ValueError) as exc:
        raise ToolError(f"Cannot write {target}: {exc}") from exc
    print(f"planner export: wrote {len(table)} epics to {target}.", file=out)
    if remote and not base:
        print("  The repository remote is not one planner can turn into a web link.", file=out)
    if not (base and commit):
        print("  No repository URL or commit was found, so Vault link holds each epic's path in the vault. "
              "Pass --repo-url and --commit to link to the repository.", file=out)
    elif dirty:
        print("  The vault has uncommitted changes, so Vault links point at HEAD and may not show them.", file=out)
    if git_trouble:
        print(f"  Git did not answer ({git_trouble}), so Vault links hold paths, not repository links.", file=out)
    open_epics = [e for e in vault.of_type("epic") if e.meta.get("state") != "decided"]
    if open_epics:
        print("  Not decided yet: " + ", ".join(f"{e.id or e.path} ({e.meta.get('state', 'no state')})"
                                               for e in sorted(open_epics, key=lambda e: e.id or e.path)) + ".", file=out)
    skipped = export.unloaded(vault)
    for path in skipped:
        print(f"  Not exported (fix with planner check): {path}", file=out)
    return 1 if skipped else 0


def read_text_file(path):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ToolError(f"Cannot read {path}: {exc}") from exc


def range_pairs(root, spec):
    """[(path, before text, after text)] for each .md file a ref range changed. `A` compares
    A with the working tree; `A..B` compares two commits. A file that is new on one side
    is compared with nothing, so every token in it counts as added or missing. A renamed
    file compares the old path's before text with the new path's after text."""
    before_ref, _, after_ref = spec.partition("..")
    if not before_ref:
        raise ToolError(f"--range {spec!r} names no commit. Write --range HEAD or --range A..B.")
    for ref in (before_ref, after_ref):
        if ref.startswith("-"):
            raise ToolError(f"--range {spec!r} has {ref!r}, which reads as a git option. Name a commit.")
        if ref:
            git_strict(root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
    status = git_strict(root, "diff", "-z", "--name-status", "-M", "--relative", "--end-of-options", before_ref,
                        *([after_ref] if after_ref else []), "--", "*.md")
    fields = status.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    pairs, i = [], 0
    while i < len(fields):
        code = fields[i][:1]
        count = 2 if code in "RC" else 1
        names = fields[i + 1:i + 1 + count]
        if len(names) != count:
            raise ToolError(f"git diff gave a status line this tool cannot read: {fields[i:]!r}")
        old, new = names[0], names[-1]
        before = "" if code == "A" else show(root, before_ref, old)
        if code == "D":
            after = ""
        elif after_ref:
            after = show(root, after_ref, new)
        else:
            after = read_text_file(root / new)
        pairs.append((new, before, after))
        i += 1 + count
    return sorted(pairs, key=lambda pair: pair[0])


def show(root, ref, path):
    """A file's text at a commit, or "" when the commit has no such path. Any other git
    failure raises ToolError, so it cannot read as an empty file."""
    present = git_strict(root, "ls-tree", "-z", "--name-only", "--end-of-options", ref, "--", f"./{path}").split("\0")
    if path not in present:
        return ""
    return git_strict(root, "show", f"{ref}:./{path}")


def cmd_voicecheck(args, out):
    if bool(args.range) == bool(args.files):
        raise ToolError("Give two files, planner voicecheck <before> <after>, or a ref range, planner voicecheck --range A..B.")
    if args.files:
        if len(args.files) != 2:
            raise ToolError("Give exactly two files: the text before the rewrite and the text after.")
        pairs = [(args.files[1], read_text_file(args.files[0]), read_text_file(args.files[1]))]
    else:
        pairs = range_pairs(pathlib.Path(args.vault).resolve(), args.range)
    failed = []
    for path, before, after in pairs:
        try:
            result = voicecheck.compare(before, after, args.redundant or ())
        except voicecheck.NotRedundant as exc:
            raise ToolError(f"{path}: {exc}") from exc
        if not result.same:
            failed.append((path, result))
    print(f"planner voicecheck: {len(pairs)} files compared, {len(failed)} with protected tokens changed.", file=out)
    for sentence in args.redundant or ():
        print(f"removed as redundant, named by the reviewer: {sentence}", file=out)
    for path, result in failed:
        for line in voicecheck.describe(result):
            print(f"{path}: {line}", file=out)
    return 1 if failed else 0


# --- voicescore: optional, needs sentence-transformers and a one-off model download ----------

MODEL_MARKER = ".planner-complete"  # written last, so a half-finished download never reads as present


def voicescore_home():
    """Where the pinned model lives. Outside the vault, so a 0.5 GB model is never committed."""
    return pathlib.Path(os.environ.get("PLANNER_VOICESCORE_HOME") or pathlib.Path.home() / ".cache" / "planner-voicescore")


def model_dir():
    return voicescore_home() / voicescore.MODEL_ID.replace("/", "__") / voicescore.MODEL_REVISION


def missing_dependencies():
    """pip names of the optional packages this Python cannot import."""
    return [pip for module, pip in (("sentence_transformers", "sentence-transformers"), ("torch", "torch"))
            if importlib.util.find_spec(module) is None]


class VoiceScoreUnavailable(Exception):
    """voicescore cannot run on this machine or vault. Printed as "not run: <reason>", exit 2."""


def require_dependencies():
    missing = missing_dependencies()
    if missing:
        raise VoiceScoreUnavailable(f"{' and '.join(missing)} not installed. voicescore is optional. "
                                    f"To use it: {voicescore.INSTALL_HINT}, then run planner voicescore setup once.")


def require_model():
    if not (model_dir() / MODEL_MARKER).is_file():
        raise VoiceScoreUnavailable(f"the {voicescore.MODEL_ID} model is not downloaded yet ({model_dir()}). "
                                    f"Run planner voicescore setup once; it is the only step that uses the network.")


def load_styledistance(path):
    """An embed callable over the local model. Offline mode is set before the import, because the
    Hugging Face libraries read it at import time; scoring must never fetch anything."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(str(path), device="cpu")

    def embed(texts):
        return [list(map(float, v)) for v in model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)]
    return embed


def download_styledistance(target):
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=voicescore.MODEL_ID, revision=voicescore.MODEL_REVISION, local_dir=str(target))


def cached(embed, folder):
    """embed, reading and writing one JSON vector per text under `folder`. A cache file that
    cannot be read is embedded again and rewritten, never trusted."""
    def lookup(texts):
        keys = [voicescore.cache_key(t) for t in texts]
        found = {}
        for key in set(keys):
            try:  # nosemgrep: except-pass -- an unreadable cache entry is a miss: it is re-embedded and rewritten
                found[key] = json.loads((folder / f"{key}.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        todo = [t for t, k in dict(zip(texts, keys)).items() if k not in found]
        if todo:
            folder.mkdir(parents=True, exist_ok=True)
            for text, vector in zip(todo, embed(todo)):
                key = voicescore.cache_key(text)
                found[key] = list(vector)
                (folder / f"{key}.json").write_text(json.dumps(found[key]), encoding="utf-8")
        return [found[k] for k in keys]
    return lookup


def cache_folder(root):
    """.git/planner-voicescore/ of the vault's repo, so the cache is never staged, or None outside git."""
    try:
        git_dir = git(root, "rev-parse", "--absolute-git-dir")
    except vaultgit.GitUnavailable as exc:
        raise ToolError(f"cannot place the voice-score cache inside the repository: {exc}") from exc
    return pathlib.Path(git_dir) / "planner-voicescore" if git_dir else None


def voice_examples(root):
    """(examples, unreadable paths) from voice/examples/ and voice/local/."""
    examples, unreadable = [], []
    for folder in ("examples", "local"):
        for path in sorted((root / "voice" / folder).glob("*/*.md")):
            example = voicescore.read_example(folder, read_text_file(path))
            if example is None:
                unreadable.append(path.relative_to(root).as_posix())
            else:
                examples.append(example)
    return examples, unreadable


def voicescore_setup(args, out):
    require_dependencies()
    target = model_dir()
    if (target / MODEL_MARKER).is_file():
        return {"ran": True, "downloaded": False, "path": str(target),
                "message": f"{voicescore.MODEL_ID} at {voicescore.MODEL_REVISION[:12]} is already in {target}. Nothing downloaded."}
    if not args.json:
        print(f"planner voicescore setup: this downloads {voicescore.MODEL_ID} at revision {voicescore.MODEL_REVISION[:12]} "
              f"({voicescore.MODEL_SIZE}) from huggingface.co into {target}. It is the only planner command that uses "
              f"the network. Scoring runs offline afterwards, and your text never leaves this machine.", file=out, flush=True)
    try:
        download_styledistance(target)
    except Exception as exc:  # any download failure leaves no marker, so scoring keeps saying "not downloaded"
        raise VoiceScoreUnavailable(f"the download failed: {exc}") from exc
    (target / MODEL_MARKER).write_text(json.dumps({"model": voicescore.MODEL_ID, "revision": voicescore.MODEL_REVISION}),
                                       encoding="utf-8")
    return {"ran": True, "downloaded": True, "path": str(target),
            "message": f"downloaded {voicescore.MODEL_ID} at {voicescore.MODEL_REVISION[:12]} into {target}."}


def voicescore_embedder(root):
    """(embed, cache note). The cache note says where vectors are kept, or that they are not.
    The model loads on the first cache miss, so a fully cached run never pays for loading it."""
    model = []

    def embed(texts):
        if not model:
            model.append(load_styledistance(model_dir()))
        return model[0](texts)
    folder = cache_folder(root)
    if folder is None:
        return embed, "cache: off, the vault is not a git repository"
    return cached(embed, folder), f"cache: {folder}"


def voicescore_reference(root, against):
    examples, unreadable = voice_examples(root)
    if unreadable:
        raise VoiceScoreUnavailable(f"cannot read the frontmatter of {', '.join(unreadable)}. Fix it so every example counts.")
    return voicescore.reference(examples, against)


def voicescore_run(args, root):
    if args.rank:
        if len(args.words) < 2:
            raise ToolError("Give at least two candidate files: planner voicescore --rank <a> <b> [...].")
        candidates = [(name, read_text_file(name)) for name in args.words]
    elif len(args.words) != 1:
        raise ToolError("Give one file: planner voicescore <file>, or planner voicescore --rank <a> <b>, or planner voicescore setup.")
    else:
        text = read_text_file(args.words[0])
    require_dependencies()  # the machine's reasons come first: they hold for every vault
    require_model()
    ref = voicescore_reference(root, args.against)
    embed, cache_note = voicescore_embedder(root)
    answer = {"ran": True, "against": ref.against, "reference": ref.described, "examples": [e.id for e in ref.examples],
              "reliable": not ref.warning, "warning": ref.warning, "model": voicescore.MODEL_ID,
              "revision": voicescore.MODEL_REVISION, "cache": cache_note}
    if args.rank:
        answer["ranked"] = [{"file": name, "label": p.label, "inside": p.inside, "percentile": p.percentile,
                             "distance": round(p.distance, 6)} for name, p in voicescore.rank(candidates, ref, embed)]
        return answer
    scored = voicescore.score(text, ref, embed)
    answer["file"] = args.words[0]
    answer["summary"] = voicescore.summary(scored, ref.range_name)
    answer["paragraphs"] = [{"number": s.paragraph.number, "line": s.paragraph.line, "label": s.placement.label,
                             "inside": s.placement.inside, "percentile": s.placement.percentile,
                             "distance": round(s.placement.distance, 6), "starts": s.paragraph.text[:60]} for s in scored]
    return answer


def print_voicescore(answer, out):
    if "ranked" in answer:
        print(f"planner voicescore --rank: {len(answer['ranked'])} candidates against {answer['reference']}, closest first.", file=out)
    elif "paragraphs" in answer:
        print(f"planner voicescore: {len(answer['paragraphs'])} paragraphs in {answer['file']} against {answer['reference']}.",
              file=out)
    else:
        print(f"planner voicescore setup: {answer['message']}", file=out)
        return
    if answer["warning"]:
        print(answer["warning"], file=out)
    for n, entry in enumerate(answer.get("ranked", []), start=1):
        print(f"{n}. {entry['file']}: {entry['label']}", file=out)
    for entry in answer.get("paragraphs", []):
        print(f"¶{entry['number']} line {entry['line']}: {entry['label']}. \"{entry['starts']}...\"", file=out)
    if "summary" in answer:
        print(answer["summary"], file=out)
    print(f"The range is how far each of the {len(answer['examples'])} examples sits from the centroid of the others. "
          f"Inside means no farther than {voicescore.INSIDE_UP_TO}% of them. This is a hint, not a gate. "
          f"Model {answer['model']} at {answer['revision'][:12]}, offline; {answer['cache']}.", file=out)


def cmd_voicescore(args, out):
    root = pathlib.Path(args.vault).resolve()
    try:
        if args.words == ["setup"] and not args.rank:
            answer = voicescore_setup(args, out)
        else:
            answer = voicescore_run(args, root)
    except (VoiceScoreUnavailable, voicescore.NotScorable) as exc:
        if args.json:
            print(json.dumps({"ran": False, "reason": str(exc)}, indent=2, ensure_ascii=False), file=out)
        else:
            print(f"planner voicescore: not run: {exc}", file=out)
        return 2
    if args.json:
        print(json.dumps(answer, indent=2, ensure_ascii=False), file=out)
    else:
        print_voicescore(answer, out)
    return 0


def days_between(earlier, later):
    return (datetime.date.fromisoformat(later) - datetime.date.fromisoformat(earlier)).days


def oldest_text(row, today):
    if row.oldest is None:
        return "none"
    if not row.opened:
        return f"{row.oldest.id}, opened: not recorded"
    return f"{row.oldest.id}, open {days_between(row.opened, today)} days (opened {row.opened})"


def ladder_note(vault, app):
    """" | pages reach <stage>" when the app's pages meet a later stage's entry list than its typed stage, else "".
    Said once, here and in close's report, never asked: the lead types the stage, or leaves it."""
    reached = ladder.ahead_of_stage(vault, app)
    return f" | pages reach {reached}" if reached else ""


def status_line(row, today, vault=None):
    inkling, assumption, fact, decided = row.mix
    next_text = f"{row.mode} {row.subject}".strip() if row.mode != "none" else "none"
    note = ladder_note(vault, row.app) if vault is not None else ""
    return (f"{row.app.id} | stage {row.stage or '-'}{note} | inkling {inkling}, assumption {assumption}, fact {fact}, "
            f"decided {progress.decided_text(row)} | oldest open unknown: {oldest_text(row, today)} | next: {next_text}. {row.reason}")


def load_lint_words(path=None):
    """The word list `planner style` and the voice reviewer share. Missing is a tool failure: an empty list would make
    every page look as if it passed the lint."""
    path = pathlib.Path(path or LINT_WORDS)
    try:
        return reading.lint_words(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise ToolError(f"{path} cannot be read ({exc}), so planner style cannot lint words. Restore it from the toolkit repo.") from exc


def cmd_style(args, out):
    """Where the named pages read as a log rather than a document: history above ## History, IDs and bare source
    IDs in prose, no opening prose. Close runs it on the pages a session changed."""
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    pages = [reviews.find_page(vault, ref) for ref in args.pages] if args.pages else list(vault.pages)
    missing = [ref for ref, page in zip(args.pages or [], pages) if page is None]
    if missing:
        raise ToolError(f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not a page in this vault.")
    found, offset, lint = [], {}, load_lint_words()
    for page in pages:
        if page.type == "session":
            continue
        _, body_start, _ = parse.split_frontmatter(page.text)
        body = "\n".join(page.text.replace("\r\n", "\n").split("\n")[body_start - 1:])
        offset[page.path] = body_start - 1
        found += [(page, n, why) for n, why in reading.style_problems(body, page.type, parse.KNOWN_LABELS.values(), lint)]
    print(f"planner style: {len(found)} to fix in {len(pages)} pages.", file=out)
    for page, n, why in found:
        print(f"{page.path}:{n + offset[page.path]}: {why}", file=out)
    return 1 if found else 0


def cmd_ladder(args, out):
    """For each app on the ladder: its typed stage, the stage its pages reach, and what the next stage still needs."""
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    apps = [a for a in vault.apps if a.meta.get("change") in schema.LADDERED_CHANGES]
    print(f"planner ladder: {len(apps)} apps on the ladder.", file=out)
    for app in apps:
        reached, gaps = ladder.allows(vault, app)
        typed = app.meta.get("stage") or "-"
        head = f"{app.id} | stage {typed} | pages reach {reached}"
        if gaps:
            shown = "; ".join(gaps[:3]) + (f"; and {len(gaps) - 3} more" if len(gaps) > 3 else "")
            head += f" | next stage needs: {shown}"
        print(head, file=out)
    return 0


def cmd_status(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, origin = parse_today(args.today)
    vault = load_vault(root)
    rows = progress.grid(vault, today)
    print(f"planner status: {len(rows)} apps. Today is {today} ({origin}).", file=out)
    for row in rows:
        print(status_line(row, today, vault), file=out)
    print(completeness.line(vault), file=out)
    return 0


def initiative_step(vault, row):
    """A step for the whole initiative that comes before the per-app frontier, or None. Requirements cut across
    apps, so their gaps are not any one app's: an unallocated requirement is allocate's work before the Grill that
    decides the apps, a changing capability with no requirements is requirements' work, and dated releases come after allocation and before epics.
    An overdue unknown (rule 1) still comes first: it blocks a contract a team is waiting on, and asking costs one message.
    Every other probe (rule 6) ranks below these: an app exists, so Boundary has run, and a capability nobody wrote
    requirements for leaves allocate, releases and every epic's criteria with nothing to stand on. Once epics exist the
    step still fires when the vault holds no requirement at all, because a lead who cut epics without running the skill
    would otherwise never be told; one capability short in a vault that has some is W356's to name, not next's, so a
    partly filled vault is not nagged again and again."""
    if row is not None and row.rule <= 1:
        return None
    loose = allocation.unallocated(vault)
    if loose:
        return (f"initiative, allocate {loose[0].id.split('.')[0]}. {loose[0].id} is at {loose[0].fact('State')} and no "
                f"app's Requirements allocated table carries it, so no team owns it yet.")
    if allocation.due(vault) and not releases.releases(vault) and not vault.of_type("epic"):
        return ("initiative, releases. Every requirement is carried by an app and no release says when anyone gets any of "
                "it, so date the releases before epics are cut.")
    have = {r.id.split(".")[0] for r in allocation.requirements(vault)}
    bare = [c for c in sorted(vault.of_type("capability"), key=lambda p: p.id)
            if c.meta.get("change") in schema.ENUMS["change@capability"] and c.meta.get("change") != "unchanged"
            and c.id not in have]
    if bare and (not vault.of_type("epic") or not have):
        return (f"initiative, requirements {bare[0].id}. {bare[0].id} is {bare[0].meta['change']} and has no functional "
                "requirements, so allocate has nothing to divide among the apps for it.")
    return None


def first_step(vault):
    """What to do while no app page exists. Once a Grill has decided the solution strategy, the direction is set
    and only a Boundary session turns it into apps; before that, the work is still finding out and shaping."""
    strategy = vault.page("04-solution-strategy")
    if strategy is not None and strategy.meta.get("state") == "decided" and not allocation.requirements(vault):
        return ("initiative, requirements. The solution strategy is decided and no capability has functional "
                "requirements yet, so write them before Boundary cuts the apps against them.")
    if strategy is not None and strategy.meta.get("state") == "decided":
        return ("initiative, boundary. The solution strategy is decided and no app page exists yet, so run a Boundary "
                "session to turn it into apps.")
    return "initiative, dump. No app page exists yet, so start with a Dump & Diverge or a Discover."


def cmd_capture(args, out):
    """Counts of what the vault records for the explorer's domains, flow senders, releases, requirements and asks."""
    found = capture.counts(load_vault(pathlib.Path(args.vault).resolve()))
    checks = capture.verdict(found, args.expect_release or "", args.expect_ask or "")
    if args.json:
        print(json.dumps({"counts": found, "checks": [{"check": n, "passed": ok, "detail": d} for n, ok, d in checks]},
                         indent=2), file=out)
        return 0
    print(f"planner capture: {found['apps_with_domain']} of {found['apps']} apps have a domain; "
          f"{found['flow_steps_with_sender']} of {found['flow_steps_crossing']} flow steps that cross a contract name a sender; "
          f"{found['releases']} releases; {found['requirements']} requirements; {found['allocation_rows']} allocation rows; "
          f"{found['unknowns_with_ask']} of {found['unknowns']} unknowns name who to ask.", file=out)
    print(f"  info  {found['apps_with_link']} of {found['apps']} apps have a code or wiki link; "
          f"{found['epics_with_link']} of {found['epics']} epics have a tracker link.", file=out)
    for name, ok, detail in checks:
        print(f"  {'pass' if ok else 'gap '}  {name}: {detail}", file=out)
    return 0


def cmd_next(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, origin = parse_today(args.today)
    vault = load_vault(root)
    when = f"Today is {today} ({origin})."
    if not vault.apps:
        print(f"planner next: {first_step(vault)} {when}", file=out)
        return 0
    row = progress.best(progress.grid(vault, today))
    step = initiative_step(vault, row)
    if step:
        print(f"planner next: {step} {when}", file=out)
        return 0
    if row is None:
        print(f"planner next: nothing to do. Every app's items are settled and its epics decided. {when}", file=out)
        return 0
    print(f"planner next: {row.app.id}, {row.mode} {row.subject}. {row.reason} {when}", file=out)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="planner", description="Check and render an initiative vault.")
    parser.add_argument("--version", action="version", version="planner (run `planner --version` on its own)",
                        help="print the plugin version and exit")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="read-only check of the vault")
    check.add_argument("--vault", default=".", help="vault root (default: current directory)")
    check.add_argument("--today", help="date to judge overdue unknowns by, YYYY-MM-DD (default: system date)")
    check.add_argument("--gate", choices=schema.GATES,
                       help="epics: trace gaps and undisposed high-severity questions are errors; shape: assumed "
                            "questions warn; grill: open questions that block an --item warn")
    check.add_argument("--item", action="append", help="with --gate grill: an agenda item's ID; repeat for each")
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
    explore = sub.add_parser("explore", help="build the vault explorer, one offline HTML page of the whole initiative")
    explore.add_argument("vault", nargs="?", default=".", help="vault root (default: current directory)")
    explore.add_argument("-o", "--out", help="HTML file to write (default: <vault>/dashboard.html)")
    explore.add_argument("--today", help="the date due windows count from, YYYY-MM-DD (default: system date)")
    explore.add_argument("--theme", default="console", help="the theme the page opens in: console, graphite, daylight or vaporwave")
    explore.add_argument("--design", action="append", default=[], metavar="APP-x=PATH",
                         help="a team's tech design doc for an app, for Inside this app; repeat for each app")
    explore.add_argument("--breakdown", action="append", default=[], metavar="APP-x=PATH",
                         help="a team's work breakdown (docs/plan/<slug>-breakdown.md) for an app, for its Build plan; repeat for each app")
    explore.add_argument("--assets", help="an assets.config.json whose provider's art is inlined (default: the builtin art)")
    explore.add_argument("--serve", action="store_true",
                         help="then serve the page on this machine only, with Ask Claude on; opens the browser, Ctrl-C stops")
    explore.add_argument("--port", type=int, default=0, help="with --serve, the port (default: any free one)")
    explore.add_argument("--model", choices=["haiku", "sonnet"], default="haiku",
                         help="with --serve, the model that answers questions (default: haiku; the page's Think harder asks sonnet)")
    explore.add_argument("--no-open", action="store_true", help="with --serve, do not open the browser")
    explore.set_defaults(func=cmd_explore)
    role = sub.add_parser("role", help="owner or reader: decided by access to the vault's git repo, never by title or config")
    role.add_argument("--vault", default=".", help="vault root (default: current directory)")
    role.add_argument("--json", action="store_true", help="the answer as JSON")
    role.set_defaults(func=cmd_role)
    nid = sub.add_parser("next-id", help="the next free ID for a prefix, such as UNK, counting main and every session branch as last fetched (git fetch first); never fills a gap")
    nid.add_argument("prefix", help="1 to 4 capital letters, for example UNK, CON, R or ADR")
    nid.add_argument("--vault", default=".", help="vault root (default: current directory)")
    nid.set_defaults(func=cmd_next_id)
    pub = sub.add_parser("publish", help="write a read copy of the committed vault, as a folder or a .zip, for people without git")
    pub.add_argument("--vault", default=".", help="vault root (default: current directory)")
    pub.add_argument("--out", required=True, help="a new folder, or a path ending in .zip")
    pub.add_argument("--today", help="the date to stamp, YYYY-MM-DD (default: system date)")
    pub.add_argument("--owner-name", help="who readers write to (default: git user.name)")
    pub.add_argument("--owner-contact", help="how readers reach the owner (default: owner_contact in .planner.yaml, else git user.email)")
    pub.add_argument("--allow-secrets", action="store_true", help="publish although the scan found text that looks like a password, token or key (it is named, never printed)")
    pub.set_defaults(func=cmd_publish)
    fresh = sub.add_parser("freshness", help="whether anything changed since this clone or copy was made; reports, never updates")
    fresh.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    fresh.add_argument("--json", action="store_true", help="the answer as JSON")
    fresh.add_argument("--today", help="the date to stamp the check with, YYYY-MM-DD (default: system date)")
    fresh.add_argument("--timeout", type=int, default=vaultgit.FETCH_TIMEOUT, help="seconds an owner's git fetch may take (default 8)")
    fresh.set_defaults(func=cmd_freshness)
    opn = sub.add_parser("open", help="make a private reader workspace from a published folder or zip; the source is never written")
    opn.add_argument("source", help="the published folder or .zip")
    opn.add_argument("--into", help="the workspace folder (default: $PLANNER_WORKSPACES/<slug>, else ~/PlannerWorkspaces/<slug>); folders OneDrive, SharePoint, Dropbox, iCloud Drive, Google Drive or Box sync are refused")
    opn.add_argument("--author", help="your name for the drafts (default: git user.name)")
    opn.add_argument("--today", help="the date to record, YYYY-MM-DD (default: system date)")
    opn.add_argument("--newer", action="store_true", help="re-opening: say that this copy is the later of two published on the same day (a stamp holds a date, not a time)")
    opn.set_defaults(func=cmd_open)
    prop = sub.add_parser("propose", help="a reader's changes as a proposal folder (proposal.md and changes.patch) beside the workspace; sends nothing")
    prop.add_argument("--vault", default=".", help="the reader workspace (default: current directory)")
    prop.add_argument("--groups", action="store_true", help="list the groups of change that need a reason, and write nothing")
    prop.add_argument("--json", action="store_true", help="with --groups, print them as JSON")
    prop.add_argument("--title", help="a few words naming what the proposal changes")
    prop.add_argument("--whys", help="JSON of group -> the reader's reason, from a file or - for standard input; a group without one reads 'no reason given'")
    prop.add_argument("--zip", action="store_true", help="write one .zip instead of a folder")
    prop.add_argument("--out-dir", help="where proposals go (default: a proposals/ folder beside the workspace)")
    prop.add_argument("--rewrite-home", action="store_true", help="write this machine's home folder as <home> in the proposal (your own files are not changed)")
    prop.add_argument("--today", help="the date to record, YYYY-MM-DD (default: system date)")
    prop.set_defaults(func=cmd_propose)
    props = sub.add_parser("proposals", help="the owner's side: review a reader's proposal in a git worktree, accept or reject its parts, answer it")
    pshared = props.add_subparsers(dest="what", required=True)
    rev = pshared.add_parser("review", help="apply a proposal (folder, .zip or .patch) with git apply --3way on branch proposal/<slug> in a new worktree")
    rev.add_argument("source", help="the proposal folder, .zip or changes.patch")
    rev.add_argument("--vault", default=".", help="the vault's git checkout (default: current directory)")
    rev.add_argument("--slug", help="branch name after proposal/ (default: from the proposal's title)")
    rev.add_argument("--worktree", help="where to put the worktree (default: beside the vault)")
    rev.add_argument("--json", action="store_true", help="print the review state as JSON")
    rev.add_argument("--today", help="the date for planner check, YYYY-MM-DD (default: system date)")
    rev.set_defaults(func=cmd_proposals_review)
    acc = pshared.add_parser("accept", help="clear a pending decision in the proposal's worktree: the owner decides it, the reader is credited")
    acc.add_argument("--vault", default=".", help="the proposal's worktree (default: current directory)")
    acc.add_argument("--item", required=True, help="the item ID that carries the marker (the page ID for a page-level marker)")
    acc.add_argument("--by", required=True, help="the owner's handle, @name")
    acc.set_defaults(func=cmd_proposals_accept)
    rej = pshared.add_parser("reject", help="take one group of a proposal back out of the worktree and commit that")
    rej.add_argument("proposal", help="the proposal folder, .zip or changes.patch")
    rej.add_argument("--vault", default=".", help="the proposal's worktree (default: current directory)")
    rej.add_argument("--group", required=True, help="the group key, as `planner proposals review` listed it")
    rej.add_argument("--reason", required=True, help="why, in the owner's words; the reader reads it")
    rej.set_defaults(func=cmd_proposals_reject)
    ans = pshared.add_parser("answer", help="write answer.md for the reader from the owner's decision on each group")
    ans.add_argument("proposal", help="the proposal folder, .zip or changes.patch")
    ans.add_argument("--vault", default=".", help="the proposal's worktree (default: current directory)")
    ans.add_argument("--decisions", required=True, help="JSON list of {group, outcome: accepted|rejected|edited, reason, commit}, from a file or - for standard input")
    ans.add_argument("--today", help="the date to record, YYYY-MM-DD (default: system date)")
    ans.set_defaults(func=cmd_proposals_answer)
    where = sub.add_parser("where", help="which planner program a skill would run, and why other places were passed over")
    where.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    where.add_argument("--plugin-root", default="", help="the value ${CLAUDE_PLUGIN_ROOT} had when the skill loaded")
    where.add_argument("--skill-dir", default="", help="the value ${CLAUDE_SKILL_DIR} had when the skill loaded")
    where.set_defaults(func=cmd_where)
    status = sub.add_parser("status", help="each app's stage, certainty mix, oldest open unknown and next mode")
    status.add_argument("--vault", default=".", help="vault root (default: current directory)")
    status.add_argument("--today", help="date to judge overdue unknowns and ages by, YYYY-MM-DD (default: system date)")
    status.set_defaults(func=cmd_status)
    nxt = sub.add_parser("next", help="the single best next step: an app and a mode, with the reason")
    nxt.add_argument("--vault", default=".", help="vault root (default: current directory)")
    nxt.add_argument("--today", help="date to judge overdue unknowns by, YYYY-MM-DD (default: system date)")
    nxt.set_defaults(func=cmd_next)
    cap = sub.add_parser("capture", help="counts of what the vault records for domains, flow senders, releases, requirements and asks")
    cap.add_argument("--vault", default=".", help="vault root (default: current directory)")
    cap.add_argument("--json", action="store_true", help="print the counts and checks as JSON")
    cap.add_argument("--expect-release", help="a YYYY-MM-DD target a release should carry")
    cap.add_argument("--expect-ask", help="words an Ask line should contain, such as 'outside counsel'")
    cap.set_defaults(func=cmd_capture)
    sty = sub.add_parser("style", help="where pages read as a log rather than a document; close runs it on changed pages")
    sty.add_argument("pages", nargs="*", help="pages to read, by path or name (default: every page)")
    sty.add_argument("--vault", default=".", help="vault root (default: current directory)")
    sty.set_defaults(func=cmd_style)
    lad = sub.add_parser("ladder", help="each app's typed stage, the stage its pages reach, and what the next needs")
    lad.add_argument("--vault", default=".", help="vault root (default: current directory)")
    lad.set_defaults(func=cmd_ladder)
    upgrade = sub.add_parser("upgrade", help="replace the vault's CONVENTIONS.md with the installed plugin's copy")
    upgrade.add_argument("--vault", default=".", help="vault root (default: current directory)")
    upgrade.set_defaults(func=cmd_upgrade)
    report = sub.add_parser("health", help="stale pages and sources, overdue unknowns and session gaps, as Markdown")
    report.add_argument("--vault", default=".", help="vault root (default: current directory)")
    report.add_argument("--today", help="date to judge by, YYYY-MM-DD (default: system date)")
    report.set_defaults(func=cmd_health)
    ask = sub.add_parser("query", help="read-only answers about IDs, for /ask: get, refs, find, search, status")
    asks = ask.add_subparsers(dest="what", required=True)
    for name, helptext in (("get", "an ID's page, heading, state, owner, sources and decision"),
                           ("refs", "every page that links to an ID"), ("find", "page titles and item headings with these words"),
                           ("search", "plain-word search, ranked, with the flows that cross each place"),
                           ("status", "the planner status grid")):
        one = asks.add_parser(name, help=helptext)
        if name in ("get", "refs"):
            one.add_argument("id", help="an ID, for example CON-001 or APP-booking")
        if name == "find":
            one.add_argument("words", nargs="+", help="words that must all appear, in any case; put -- before a word that starts with -")
        if name == "search":
            one.add_argument("words", nargs="+", help="what you are looking for, in your own words")
            one.add_argument("--limit", type=int, default=8, help="how many places to show (default: 8)")
        if name == "status":
            one.add_argument("--today", help="date to judge by, YYYY-MM-DD (default: system date)")
        one.add_argument("--vault", default=".", help="vault root (default: current directory)")
        one.add_argument("--json", action="store_true", help="print JSON instead of text")
        one.set_defaults(func=cmd_query)
    ques = sub.add_parser("questions", help="the questions the catalogue says this vault owes, and where each stands")
    ques.add_argument("--vault", default=".", help="vault root (default: current directory)")
    ques.add_argument("--json", action="store_true", help="print JSON instead of text")
    ques.add_argument("--area", help="only this area of the catalogue, such as FIN")
    ques.add_argument("--open", action="store_true", help="list only copies with no row, an open row, an invalid row or an asked row")
    ques.add_argument("--subject", help="only copies about this subject, such as APP-booking")
    view_of = ques.add_mutually_exclusive_group()
    view_of.add_argument("--digest", action="store_true",
                         help="the undisposed and asked copies grouped by entry and ranked, high and blocking first")
    ques.add_argument("--all", action="store_true",
                      help="with --digest: every line in full, not only the high and blocking ones")
    view_of.add_argument("--stats", action="store_true", help="how often each entry ends not-applicable in this vault")
    ques.set_defaults(func=cmd_questions)
    found = sub.add_parser("findings", help="merge the focused reviewers' findings and check every quote")
    founds = found.add_subparsers(dest="what", required=True)
    merge = founds.add_parser("merge", help="union, remove duplicates, drop a finding whose quote is not on its page")
    merge.add_argument("folder", help="folder holding one <AREA>.json per reviewer, such as FIN.json")
    merge.add_argument("--vault", default=".", help="vault root (default: current directory)")
    merge.add_argument("--json", action="store_true", help="print JSON instead of text")
    merge.add_argument("--areas", help="only these areas, such as FIN,REG, for a re-run; the others are not read")
    merge.add_argument("--skipped", help="with --areas: areas left out because nothing in them was in scope, "
                                         "such as OPS; the coverage line says so")
    merge.add_argument("--changed", help="the pages this session changed, and its record, comma-separated: a new "
                                         "question quoting any other page is dropped")
    merge.set_defaults(func=cmd_findings)
    hand = sub.add_parser("handoff", help="write the senior's handoff manifest, or verify the vault against it")
    hand.add_argument("words", nargs="+", metavar="[verify] APP-id", help="APP-id to write handoffs/<APP-id>.md; verify APP-id to compare")
    hand.add_argument("--vault", default=".", help="vault root (default: current directory)")
    hand.add_argument("--today", help="date to record, YYYY-MM-DD (default: system date)")
    hand.add_argument("--commit", help="commit to record (default: git rev-parse --short HEAD)")
    hand.add_argument("--replace", action="store_true", help="overwrite an existing manifest once the senior accepts the changes")
    hand.set_defaults(func=cmd_handoff)
    exp = sub.add_parser("export", help="write the epics out for another tool; nothing is read back")
    exps = exp.add_subparsers(dest="format", required=True)
    jira = exps.add_parser("jira-csv", help="one row per epic: Summary, Description, Epic Name, Owner team, Vault link")
    jira.add_argument("--out", required=True, help="CSV file to write")
    jira.add_argument("--vault", default=".", help="vault root (default: current directory)")
    jira.add_argument("--repo-url", help="repository to link to (default: git remote get-url origin)")
    jira.add_argument("--commit", help="commit to link to (default: git rev-parse HEAD)")
    jira.set_defaults(func=cmd_export)
    voice = sub.add_parser("voicecheck", help="fail when a rewrite changed an ID, number, date, link, code span or table cell")
    voice.add_argument("files", nargs="*", metavar="before after", help="the text before the rewrite and after it")
    voice.add_argument("--range", help="a ref range instead of files: A (A against the working tree) or A..B")
    voice.add_argument("--redundant", action="append", metavar="SENTENCE",
                       help="a sentence the reviewer named as already said elsewhere; the rewrite may drop it and its negation. "
                            "Repeat for each. It must be in the text before and gone from the text after")
    voice.add_argument("--vault", default=".", help="vault root for --range (default: current directory)")
    voice.set_defaults(func=cmd_voicecheck)
    score = sub.add_parser("voicescore", help="optional: where each prose paragraph sits against your own voice's range")
    score.add_argument("words", nargs="+", metavar="setup | file | candidate",
                       help="setup to download the model once; a page to score its prose paragraphs; with --rank, two or more drafts")
    score.add_argument("--rank", action="store_true", help="rank drafts of the same paragraph, closest to the voice first")
    score.add_argument("--against", choices=voicescore.AGAINST, default="owner",
                       help="owner (default): your active owner and owner-edit examples; seed: the public seed, labelled as such")
    score.add_argument("--vault", default=".", help="vault root holding voice/ (default: current directory)")
    score.add_argument("--json", action="store_true", help="print JSON instead of text")
    score.set_defaults(func=cmd_voicescore)
    return parser


def unrecognized_message(args, extras):
    """Why an extra argument was refused. A folder is almost always a vault passed the way `explore` takes it, so say
    how check, render, view and the rest take it: with --vault."""
    command = getattr(args, "command", "")
    first = extras[0]
    if "vault" in args and pathlib.Path(first).is_dir():
        return (f"planner: {first} is not an argument of '{command}'. It takes the vault as an option: "
                f"planner {command} --vault {first}")
    return f"planner: unrecognized arguments: {' '.join(extras)}"


PLUGIN_JSON =pathlib.Path(__file__).resolve().parent.parent.parent / ".claude-plugin" / "plugin.json"


def plugin_version(path=PLUGIN_JSON):
    """The version plugin.json declares, or words saying why it cannot be read: an owner and a reader on different
    builds can only tell each other so if the tool can say which build it is (Sensor)."""
    try:
        return str(json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return f"unknown ({path.name if hasattr(path, 'name') else path} could not be read: {exc})"


def main(argv=None, out=None):
    out = out or sys.stdout
    if list(argv if argv is not None else sys.argv[1:]) == ["--version"]:
        print(f"planner {plugin_version()}", file=out)
        return 0
    try:
        args, extras = build_parser().parse_known_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if extras:
        print(unrecognized_message(args, extras), file=out)
        return 2
    try:
        return args.func(args, out)
    except ToolError as exc:
        print(f"planner: {exc}", file=out)
        return 2
    except Exception as exc:  # the tool failed; never report this as a vault finding
        print(f"planner: internal error: {exc!r}. This is a bug in planner, not in the vault.", file=out)
        traceback.print_exc(file=out)
        return 2
