#!/usr/bin/env python3
"""Run plugin-eval cases by hand in both arms, then grade every kept workspace with vela check.

This costs money: each run is a real Claude session on your account. Run it before a skill ships,
after a SKILL.md or reference change, and when the default model changes.

Usage:
  python3 tests/evals/run.py --model <model> --judge-model <model> [--runs 3] [--max-cost-usd 10] [CASE ...]

CASE is a case name such as e1-dump. With none, every case runs. Each case runs twice: the plugin arm
(tests/evals/plugin/<case>) and the conventions-only arm (tests/evals/stub/<case>). Results, one Markdown
file per case, go to tests/evals/.results/, which git ignores.

--max-cost-usd caps each plugin eval invocation, which is one arm of one case. The worst case for a
whole run is the ceiling times 2 arms times the number of cases.

Exit codes: 0 plugin eval exited 0 in every arm (every native grader passed at --threshold 1) and every
workspace grade passed; 1 plugin eval exited 1 or at least one grade FAILed; 2 a run could not be graded
(plugin eval exited other than 0 or 1, such as 2 for the cost ceiling, or the number of kept workspaces
differs from --runs).
"""
import argparse
import datetime
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
VELA = REPO / "plugin" / "scripts" / "vela"
RESULTS = HERE / ".results"
ARMS = ("plugin", "stub")
sys.path.insert(0, str(REPO / "plugin" / "lib"))
from vela import schema  # noqa: E402  (the ID patterns live there; a copy here would drift)

# Per case: the date check judges by, whether the epics gate applies, whether the workspace must stay
# git-clean ("readonly"), and file checks on the kept workspace. "expect" patterns must match in some file
# the glob names; "forbid" patterns must match in none. "may_decide" is how many pages the run may move to
# decided (default 0: a case that asks for no decision writes none). "check_codes" / "check_never" are finding codes that
# `vela check` must, and must not, report on the kept workspace. Checks read the files, never the transcript, because
# a transcript holds the skill's own text and would pass on the instructions alone.
OVERRIDE_BULLET = r"^- \*\*Override:\*\*"
CAP_021 = "capabilities/CAP-021-*.md"
DECIDED = r"^state: decided$|^- \*\*State:\*\* decided$"
CLOSE_RECORD = "sessions/2026-10-05-mainframe-breaks-booking.md"
CASES = {
    "e1-dump": {"today": "2026-10-05", "gate": False,
                "expect": [("sessions/*.md", r"^- \[unknown\] ")],
                "forbid": [("**/*.md", DECIDED)]},
    "e1-close": {"today": "2026-10-05", "gate": False,
                 "expect": [(CLOSE_RECORD, r"^status: closed$"),
                            (CLOSE_RECORD, r"^- \[unknown\] \(claude\)[^\n]*→ drop: \S[^\n]* \^c07$"),
                            ("11-unknowns-and-risks.md", r"\*\*Owner:\*\* @")],
                 "forbid": [("**/*.md", DECIDED),
                            (CLOSE_RECORD, r"^- \[unknown\][^\n]*→ park"),
                            ("11-unknowns-and-risks.md", r"host a booking service")]},
    "e2-discover": {"today": "2026-10-05", "gate": False,
                    "expect": [("sources.md", r"\| SRC-01 \|"),
                               ("sessions/*.md", r"→ keep: [^\n]*\(fact\)")],
                    "forbid": [("**/*.md", r"(?i)event bus[^\n]*(ready|Q4)[^\n]*\bfact\b")]},
    "e3-grill-refused": {"today": "2026-11-20", "gate": False,
                         "expect": [],
                         "forbid": [("capabilities/CAP-021-*.md", DECIDED), (CAP_021, OVERRIDE_BULLET)]},
    "e7-grill-override": {"today": "2026-11-20", "gate": False, "may_decide": 1,
                          "expect": [(CAP_021, DECIDED),
                                     (CAP_021, OVERRIDE_BULLET + r"[^\n]*\bGATE-4\b"),
                                     (CAP_021, r"^- \*\*Decided by:\*\* @[A-Za-z0-9_-]+, on behalf of @")],
                          "forbid": [], "check_codes": ["W316"], "check_never": ["E316"]},
    "e4-shape": {"today": "2026-11-20", "gate": False,
                 "expect": [("sessions/**/*.md", r"(?i)read.?back")],
                 "forbid": []},  # no page may reach decided: decided_growth fails any rise over the scaffold, on every page
    "e5-ask": {"today": "2026-11-20", "gate": False, "readonly": True, "expect": [], "forbid": []},
    "e6-epics": {"today": "2026-11-20", "gate": True,
                 "expect": [("13-epics/EPC-*.md", r"^type: epic$")],
                 "forbid": [("13-epics/EPC-*.md", DECIDED)]},
}

PATH = re.compile(r"(/[^\s'\"`,;)]+)")


class EvalError(Exception):
    """The wrapper cannot grade the run. It never guesses a result."""


def find_workspaces(log):
    """Kept workspaces the eval printed: a printed directory that itself holds .vela.yaml. No parent is searched."""
    found = []
    for raw in PATH.findall(log):
        path = pathlib.Path(raw.rstrip("."))
        if (path / ".vela.yaml").is_file() and path.resolve() not in found:
            found.append(path.resolve())
    return found


def file_checks(workspace, checks, want):
    """Each (glob, pattern) with the files it matched. want=True: a hit is required. want=False: a hit is a failure."""
    lines = []
    for glob, pattern in checks:
        regex = re.compile(pattern, re.M)
        hits = [p.relative_to(workspace).as_posix() for p in sorted(workspace.glob(glob))
                if p.is_file() and ".claude" not in p.parts and regex.search(p.read_text(encoding="utf-8", errors="replace"))]
        ok = bool(hits) if want else not hits
        lines.append(f"{'pass' if ok else 'FAIL'}: {'expect' if want else 'forbid'} /{pattern}/ in {glob}"
                     + (f" ({', '.join(hits)})" if hits else ""))
    return lines


# ------------------------------------------------------------ invented IDs

FRONT = re.compile(r"\A---\n(.*?)\n---", re.S)
ITEM_TOKEN = r"(?:[A-Z]{1,4}-\d+|G\d+)"
HEADING_ID = re.compile(rf"^#{{1,6}}\s+({ITEM_TOKEN})\b", re.M)
ROW_ID = re.compile(rf"^\|\s*({ITEM_TOKEN})\s*\|", re.M)
ID_PATTERNS = [*schema.PAGE_ID_RE.values(), schema.ITEM_ID_RE, schema.GOAL_ID_RE, schema.CONSTRAINT_ID_RE, schema.SOURCE_ID_RE]


def vault_pages(read, names):
    """The committed pages. sessions/private/ holds the lead's own notes, which are never committed or graded."""
    return [(n, read(n)) for n in names if n.endswith(".md") and not n.startswith((".", "voice/", "sessions/private/")) and "/.claude/" not in "/" + n]


def ids_in(name, text):
    """(id, kind) pairs a page declares: its frontmatter id, heading IDs, and table-row IDs outside sessions/."""
    found = set()
    front = FRONT.match(text)
    if front:
        page_id = re.search(r"^id:\s*(\S+)", front.group(1), re.M)
        page_type = re.search(r"^type:\s*(\S+)", front.group(1), re.M)
        if page_id:
            found.add((page_id.group(1).strip("'\""), "session" if page_type and page_type.group(1) == "session" else "page"))
    found |= {(m, "item") for m in HEADING_ID.findall(text)}
    if not name.startswith("sessions/"):
        found |= {(m, "item") for m in ROW_ID.findall(text)}
    return found


def changes_ids(pages):
    """IDs in the first column of every session's ## Changes table."""
    ids = set()
    for name, text in pages:
        if not name.startswith("sessions/"):
            continue
        section = text.split("## Changes", 1)[-1] if "## Changes" in text else ""
        ids |= set(re.findall(r"^\|\s*([^|\s]+)\s*\|", section, re.M))
    return ids


def scaffold_state(workspace):
    """(root commit, its .md pages) of the kept workspace's git history, or None when git cannot say."""
    root = subprocess.run(["git", "-C", str(workspace), "rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True, timeout=60)
    if root.returncode != 0 or not root.stdout.split():
        return None
    commit = root.stdout.split()[0]
    names = subprocess.run(["git", "-C", str(workspace), "ls-tree", "-r", "--name-only", commit], capture_output=True, text=True, timeout=60)
    if names.returncode != 0:
        return None
    def read(name):
        shown = subprocess.run(["git", "-C", str(workspace), "show", f"{commit}:{name}"], capture_output=True, text=True, timeout=60)
        return shown.stdout
    return vault_pages(read, names.stdout.splitlines())


def invented_ids(workspace):
    """Lines for the 'no invented ID' invariant: every ID absent from the scaffold must be a well-formed new ID
    that the session's Changes table records. Sessions need only a well-formed id equal to their file name."""
    before = scaffold_state(workspace)
    if before is None:
        return ["FAIL: cannot read the scaffold commit, so invented IDs cannot be checked"]
    names = [p.relative_to(workspace).as_posix() for p in sorted(workspace.rglob("*.md")) if ".git" not in p.parts]
    after = vault_pages(lambda n: (workspace / n).read_text(encoding="utf-8", errors="replace"), names)
    known = set().union(*(ids_in(n, t) for n, t in before)) if before else set()
    recorded = changes_ids(after)
    problems, new = [], 0
    for name, text in after:
        for item, kind in sorted(ids_in(name, text) - known):
            new += 1
            if not any(p.match(item) for p in ID_PATTERNS):
                problems.append(f"FAIL: invented ID {item} in {name}: not a vela ID pattern")
            elif schema.SOURCE_ID_RE.match(item):
                if name != "sources.md":
                    problems.append(f"FAIL: invented ID {item} in {name}: SRC IDs belong only in sources.md")
            elif kind == "session":
                if item != pathlib.PurePosixPath(name).stem:
                    problems.append(f"FAIL: invented ID {item} in {name}: a session id must equal its file name")
            elif item not in recorded:
                problems.append(f"FAIL: invented ID {item} in {name}: not in any session's Changes table")
    return problems or [f"pass: no invented IDs ({new} new, each recorded)"]


def decided_growth(workspace, allowed=0):
    """A case that asks for no decision writes none. A rise in decided states over the scaffold beyond `allowed` is a
    failure."""
    before = scaffold_state(workspace)
    if before is None:
        return ["FAIL: cannot read the scaffold commit, so decided states cannot be compared"]
    regex = re.compile(r"^state: decided$|^- \*\*State:\*\* decided$", re.M)
    count = lambda pages: sum(len(regex.findall(t)) for n, t in pages)  # noqa: E731
    names = [p.relative_to(workspace).as_posix() for p in sorted(workspace.rglob("*.md")) if ".git" not in p.parts]
    now = count(vault_pages(lambda n: (workspace / n).read_text(encoding="utf-8", errors="replace"), names))
    was = count(before)
    return [f"{'FAIL' if now - was > allowed else 'pass'}: decided states {was} -> {now} (up to {allowed} allowed)"]


def check_code_lines(output, wanted, never):
    """Grades on the finding codes in `vela check` output. A code the case needs must appear; a code it
    forbids must not. This is how a case proves an override turned an error into its warning."""
    seen = set(re.findall(r"^\S+?:\d+: ([EW]\d{3}) ", output, re.M))
    return [f"{'pass' if code in seen else 'FAIL'}: check reports {code}" for code in wanted] + \
           [f"{'FAIL' if code in seen else 'pass'}: check never reports {code}" for code in never]


def grade(workspace, spec):
    """Mechanical grades for one kept workspace, as Markdown lines. A failure line starts '- FAIL'."""
    argv = [sys.executable, str(VELA), "check", "--vault", str(workspace), "--today", spec["today"]]
    if spec["gate"]:
        argv += ["--gate", "epics"]
    check = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    status = subprocess.run(["git", "-C", str(workspace), "status", "--porcelain"], capture_output=True, text=True, timeout=60)
    inbox = subprocess.run(["git", "-C", str(workspace), "ls-files", ".inbox"], capture_output=True, text=True, timeout=60)
    summary = check.stdout.splitlines()[0] if check.stdout else check.stderr.strip()
    lines = [f"- workspace: `{workspace}`",
             f"- {'pass' if check.returncode == 0 else 'FAIL'}: check exit {check.returncode}: {summary}"]
    lines += [f"  - {f}" for f in check.stdout.splitlines()[1:]]
    dirty = bool(status.stdout.strip())
    if spec.get("readonly"):
        lines.append(f"- {'FAIL: git status DIRTY (a read-only skill changed files): ' + ' '.join(status.stdout.split()) if dirty else 'pass: git status clean'}")
    else:
        lines.append(f"- git status: {'DIRTY: ' + ' '.join(status.stdout.split()) if dirty else 'clean'}")
    lines.append(f"- {'FAIL: .inbox in git: ' + ' '.join(inbox.stdout.split()) if inbox.stdout.strip() else 'pass: .inbox not in git'}")
    lines += [f"- {line}" for line in invented_ids(workspace) + decided_growth(workspace, spec.get("may_decide", 0))]
    lines += [f"- {line}" for line in check_code_lines(check.stdout, spec.get("check_codes", []), spec.get("check_never", []))]
    lines += [f"- {line}" for line in file_checks(workspace, spec["expect"], True) + file_checks(workspace, spec["forbid"], False)]
    return lines


def failed(lines):
    return any(line.startswith("- FAIL") for line in lines)


PLUGINS_ENTRY = re.compile(r"^plugins:\n- (\S+)\n", re.M)
SCAFFOLD_CALL = '"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../scaffold.py"'


def staged_case(case, arm, root):
    """The case's folder copied inside a copy of the plugin it names, so `plugin eval` loads that plugin. Claude Code
    2.1.305 and later load a case's plugin only from inside the case's enclosing plugin; the cases name it by a relative
    path out of tests/evals, which it refuses. The scaffold call is made absolute, since the copy moved the case."""
    source = HERE / arm / case
    text = (source / "case.yaml").read_text(encoding="utf-8")
    entry = PLUGINS_ENTRY.search(text)
    if entry is None:
        raise EvalError(f"{source / 'case.yaml'} names no plugin on one line under plugins:")
    plugin = (source / entry.group(1)).resolve()
    home = pathlib.Path(root) / plugin.name
    shutil.copytree(plugin, home, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    staged = home / "evals" / case
    shutil.copytree(source, staged)
    (staged / "case.yaml").write_text(PLUGINS_ENTRY.sub("plugins:\n- ../..\n", text, count=1), encoding="utf-8")
    fixture = staged / "fixture.sh"
    if fixture.is_file():
        script = fixture.read_text(encoding="utf-8")
        if SCAFFOLD_CALL not in script:
            raise EvalError(f"{source / 'fixture.sh'} doesn't call ../../scaffold.py the way staged_case expects")
        fixture.write_text(script.replace(SCAFFOLD_CALL, f'"{HERE / "scaffold.py"}"'), encoding="utf-8")
    return staged / "case.yaml"


def run_arm(case, arm, args, out_dir):
    """(Markdown lines, whether any grade FAILed). Raises EvalError when the run cannot be graded."""
    if not (HERE / arm / case / "case.yaml").is_file():
        raise EvalError(f"{HERE / arm / case / 'case.yaml'} is missing")
    with tempfile.TemporaryDirectory(prefix="vela-eval-") as root:
        return run_staged_arm(case, arm, args, out_dir, staged_case(case, arm, root))


def run_staged_arm(case, arm, args, out_dir, case_yaml):
    log_path = out_dir / f"{case}-{arm}.log"
    argv = ["claude", "plugin", "eval", str(case_yaml), "--no-publish", "--keep-temp", "--scaffold", "--trust-plugin",
            "--ablation", "none", "--threshold", "1", "--runs", str(args.runs), "--max-cost-usd", str(args.max_cost_usd),
            "--model", args.model, "--judge-model", args.judge_model,
            "--output-dir", str(out_dir / f"{case}-{arm}"), "--report", str(out_dir / f"{case}-{arm}.html"),
            "--allow-tools", "Write", "Edit", "Bash"]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        raise EvalError(f"plugin eval timed out after 600s on {case}-{arm}") from exc
    log = result.stdout + "\n" + result.stderr
    log_path.write_text(log, encoding="utf-8")
    if result.returncode not in (0, 1):
        raise EvalError(f"plugin eval exited {result.returncode} (2 is the cost ceiling); read {log_path}")
    workspaces = find_workspaces(log)
    if len(workspaces) != args.runs:
        raise EvalError(f"expected {args.runs} kept workspaces for {case} ({arm}), found {len(workspaces)}. The eval exited "
                        f"{result.returncode}; read {log_path} and, if --keep-temp prints paths differently, update find_workspaces().")
    lines = [f"### {arm} arm", "", f"- plugin eval exit {result.returncode}, {len(workspaces)} kept workspaces", ""]
    bad = result.returncode == 1
    if bad:
        lines += ["- FAIL: plugin eval exited 1: a case scored below --threshold 1, so a native grader failed. See the HTML report.", ""]
    for workspace in workspaces:
        graded = grade(workspace, CASES[case])
        bad = bad or failed(graded)
        lines += graded + [""]
    return lines, bad


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="*", help="case names; default: all")
    parser.add_argument("--model", required=True, help="model under test, pinned for the whole run")
    parser.add_argument("--judge-model", required=True, help="model for llm graders, pinned for the whole run")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-cost-usd", type=float, default=10, help="ceiling per plugin eval invocation, so per arm per case")
    args = parser.parse_args(argv)
    unknown = [c for c in args.cases if c not in CASES]
    if unknown:
        parser.error(f"unknown cases: {', '.join(unknown)}. Known: {', '.join(CASES)}")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    out_dir = RESULTS / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    unusable = graded_fail = False
    for case in args.cases or list(CASES):
        lines = [f"# {case}", "", f"Model {args.model}, judge {args.judge_model}, {args.runs} runs per arm, {stamp}.", ""]
        for arm in ARMS:
            try:
                arm_lines, bad = run_arm(case, arm, args, out_dir)
                graded_fail = graded_fail or bad
                lines += arm_lines
            except EvalError as exc:
                unusable = True
                lines += [f"### {arm} arm", "", f"- could not grade: {exc}", ""]
        (out_dir / f"{case}.md").write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
    print(f"Results: {out_dir}")
    return 2 if unusable else 1 if graded_fail else 0


if __name__ == "__main__":
    sys.exit(main())
