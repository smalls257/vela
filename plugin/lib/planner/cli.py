"""The only part of planner that touches the disk, the clock, git or the network.
The network is touched by one command alone, `planner voicescore setup`.

Exit codes: 0 clean, 1 findings, 2 the tool itself failed.
"""
import argparse
import codecs
import datetime
import difflib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback

import yaml

from planner import catalog, export, handoff, health, ladder, model, reading, parse, progress, query, questions, render, reviews, rules, schema, viewer, voicecheck, voicescore

ASSETS = pathlib.Path(__file__).resolve().parent / "assets"
CATALOGUE = pathlib.Path(__file__).resolve().parent.parent.parent / "catalog" / "questions.yaml"


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
    return model.build(pages, config, others, load_catalogue())


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


def git_strict(root, *args):
    """Output of a git command, or ToolError with git's own message. For commands whose
    failure must never read as "nothing changed". Output that is not UTF-8 is a failure too."""
    try:
        result = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=false", *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ToolError(f"git {' '.join(args)} could not run: {exc}") from exc
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
    try:
        target.parent.mkdir(exist_ok=True)
        target.write_text(handoff.write(app_id, entries, commit, today), encoding="utf-8")
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
    remote = args.repo_url or git(root, "remote", "get-url", "origin")
    base = export.web_url(remote)
    commit = args.commit or git(root, "rev-parse", "HEAD")
    prefix = git(root, "rev-parse", "--show-prefix")
    if base and commit:
        def link_for(path):
            return f"{base}/blob/{commit}/{export.link_path(prefix + path)}"
    else:
        def link_for(path):
            return path
    table = export.rows(vault, link_for)
    target = pathlib.Path(args.out)
    try:
        target.write_text(export.to_csv(table), encoding="utf-8", newline="")
    except (OSError, ValueError) as exc:
        raise ToolError(f"Cannot write {target}: {exc}") from exc
    print(f"planner export: wrote {len(table)} epics to {target}.", file=out)
    if remote and not base:
        print("  The repository remote is not one planner can turn into a web link.", file=out)
    if not (base and commit):
        print("  No repository URL or commit was found, so Vault link holds each epic's path in the vault. "
              "Pass --repo-url and --commit to link to the repository.", file=out)
    elif not args.commit and git(root, "status", "--porcelain", "--", "."):
        print("  The vault has uncommitted changes, so Vault links point at HEAD and may not show them.", file=out)
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
        result = voicecheck.compare(before, after)
        if not result.same:
            failed.append((path, result))
    print(f"planner voicecheck: {len(pairs)} files compared, {len(failed)} with protected tokens changed.", file=out)
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
            try:
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
    git_dir = git(root, "rev-parse", "--absolute-git-dir")
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


def cmd_style(args, out):
    """Where the named pages read as a log rather than a document: history above ## History, IDs and bare source
    IDs in prose, no opening prose. Close runs it on the pages a session changed."""
    root = pathlib.Path(args.vault).resolve()
    vault = load_vault(root)
    pages = [reviews.find_page(vault, ref) for ref in args.pages] if args.pages else list(vault.pages)
    missing = [ref for ref, page in zip(args.pages or [], pages) if page is None]
    if missing:
        raise ToolError(f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not a page in this vault.")
    found = [(page, n, why) for page in pages if page.type != "session"
             for n, why in reading.style_problems(viewer.body_of(page), page.type)]
    offset = {page.path: page.text.split("\n").index(viewer.body_of(page).split("\n")[0]) if viewer.body_of(page) else 0
              for page in pages}
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
    return 0


def first_step(vault):
    """What to do while no app page exists. Once a Grill has decided the solution strategy, the direction is set
    and only a Boundary session turns it into apps; before that, the work is still finding out and shaping."""
    strategy = vault.page("04-solution-strategy")
    if strategy is not None and strategy.meta.get("state") == "decided":
        return ("initiative, boundary. The solution strategy is decided and no app page exists yet, so run a Boundary "
                "session to turn it into apps.")
    return "initiative, dump. No app page exists yet, so start with a Dump & Diverge or a Discover."


def cmd_next(args, out):
    root = pathlib.Path(args.vault).resolve()
    today, origin = parse_today(args.today)
    vault = load_vault(root)
    when = f"Today is {today} ({origin})."
    if not vault.apps:
        print(f"planner next: {first_step(vault)} {when}", file=out)
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
    status = sub.add_parser("status", help="each app's stage, certainty mix, oldest open unknown and next mode")
    status.add_argument("--vault", default=".", help="vault root (default: current directory)")
    status.add_argument("--today", help="date to judge overdue unknowns and ages by, YYYY-MM-DD (default: system date)")
    status.set_defaults(func=cmd_status)
    nxt = sub.add_parser("next", help="the single best next step: an app and a mode, with the reason")
    nxt.add_argument("--vault", default=".", help="vault root (default: current directory)")
    nxt.add_argument("--today", help="date to judge overdue unknowns by, YYYY-MM-DD (default: system date)")
    nxt.set_defaults(func=cmd_next)
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
