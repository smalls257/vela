"""The replay (overhaul plan Task 3, 8.1): a session plays the exact commands the skills name, end to end, for free.

Each command has its own tests, and each skill's text has its pins, yet a close can still fail to run end to end: one
command's output is not what the next one reads, or a commit's message is not in the grammar check reads. That passes
every unit test and fails the first live session (Paper Tiger). The replay is the free check that sees it.

It copies the heron-desk snapshot `after-full-1` into tmp_path, makes a bare local repo its `origin`, puts the `gh` stub
tests/sim uses first on PATH, and runs every `tests/replay/step_*.py` in file-name order. A step is a module with
`run(ctx)`. `ctx.vela(*args, check=True)` runs `plugin/scripts/vela` in the vault, as a skill's Bash call does, and
returns (exit code, output); `ctx.outputs` holds what earlier steps kept. A later task adds its command as a new step
file (`step_NN_<command>.py`) and never edits this test, which is what keeps the batches' files apart (Shield).

After the steps it asserts, by parsing and never by byte comparison: `vela check` has no error that was not there before
the steps; the record's captures, marks and Changes rows read in today's grammar; every commit the steps made has a
message the close skill and START write; and no `--for-lead` output carries a code or ID (`say.LEAD_PATTERNS`).
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import types

from conftest import REPO, FINDING
from vela import closefinish, closegate, ledger, parse, say, schema
from vela.commands import close_stage, decide, voice_settle

SNAPSHOT = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"
STEPS = REPO / "tests" / "replay"
PROGRAM = REPO / "plugin" / "scripts" / "vela"
TODAY = "2026-10-14"
RECORD_ID = f"{TODAY}-desk-agent-calendar"

_spec = importlib.util.spec_from_file_location("sim_run_for_replay", REPO / "tests" / "sim" / "run.py")
sim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sim)

# A mark as CONVENTIONS ("Captures") defines it: `keep: [[<page>#<heading>|<ID>]] (<state>)`, `park`, or `drop: <reason>`.
MARK = re.compile(r"^(?:keep: \[\[[^\]#|]+#[^\]|]+\|(?P<id>[^\]]+)\]\] \((?P<state>[\w-]+)\)|park|drop: \S.*)$")
# A kept capture's state is one an item, an unknown, a risk, a concern cell or a ledger row can hold, as vela reads them.
MARK_STATES = set(schema.STATE_ITEM) | set(schema.UNKNOWN_STATES) | set(schema.RISK_STATES) | set(schema.CELL_STATES) \
    | set(schema.CONTAINER_STATES) | set(ledger.STATES) \
    | {state for spec in schema.PAGE_TYPES.values() for state in (spec.get("states") or ())}
# Every commit message a session makes today: START opens the record, close stage commits, a merge brings main in.
COMMIT_GRAMMAR = [re.compile(r"^Open session (?P<id>\S+)$"), re.compile(r"^Merge (?:remote-tracking )?branch '[^']+'")]
COMMIT_GRAMMAR += [re.compile("^" + re.escape(message).replace(re.escape("{id}"), r"(?P<id>\S+)") + "$")
                   for message in close_stage.MESSAGES.values()]
# Messages later commands write, read from the constants that own them so a reworded commit can't drift past the replay.
# In close finish `{id}` is the session; `{app}` and the voice rewrite's page id match any one word.
COMMIT_GRAMMAR += [re.compile("^" + re.escape(message).replace(re.escape("{id}"), r"(?P<id>\S+)")
                              .replace(re.escape("{app}"), r"\S+") + "$") for message in closefinish.MESSAGES]
COMMIT_GRAMMAR += [re.compile("^" + re.escape(voice_settle.REWRITE_MESSAGE).replace(re.escape("{id}"), r"\S+") + "$")]
# A decision names its item (a release by its heading, so any words), never the session.
COMMIT_GRAMMAR += [re.compile("^" + re.escape(message).replace(re.escape("{id}"), r".+") + "$")
                   for message in decide.MESSAGES.values()]


def git(vault, *args):
    done = subprocess.run(["git", *args], cwd=vault, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, f"git {' '.join(args)}: {done.stderr}"
    return done.stdout


def build(tmp_path):
    vault, origin, bin_dir = tmp_path / "vault", tmp_path / "origin.git", tmp_path / "bin"
    shutil.copytree(SNAPSHOT, vault, ignore=shutil.ignore_patterns(".git"))
    git(tmp_path, "init", "-q", "-b", "main", str(vault))
    git(vault, "config", "user.name", "Replay Lead")
    git(vault, "config", "user.email", "replay-lead@example.invalid")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "Vault from snapshot heron-desk/after-full-1")
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(vault, "remote", "add", "origin", str(origin))
    git(vault, "push", "-q", "-u", "origin", "main")
    sim.write_gh_stub(bin_dir, origin)
    return vault, origin, bin_dir


class Context(types.SimpleNamespace):
    """What a step gets: the vault, the runner, and what earlier steps kept."""

    def typed(self, text):
        """What the lead typed, logged as the UserPromptSubmit hook does, so `record add` can check their words."""
        from vela.edge import saidlog
        saidlog.append(self.vault, "replay-session", f"{self.today}T09:00:00Z", text)

    def vela(self, *args, check=True):
        env = dict(os.environ, PATH=f"{self.bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
        for name in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN"):
            env.pop(name, None)
        done = subprocess.run([sys.executable, str(PROGRAM), *args], cwd=self.vault, env=env, capture_output=True,
                              text=True, timeout=120)
        output = done.stdout + done.stderr
        self.calls.append((args, done.returncode, output))
        assert not check or done.returncode == 0, f"vela {' '.join(args)} exited {done.returncode}:\n{output}"
        return done.returncode, output

    def git(self, *args):
        return git(self.vault, *args)


def steps():
    found = sorted(STEPS.glob("step_*.py"))
    assert found, f"no steps in {STEPS}"
    for path in found:
        spec = importlib.util.spec_from_file_location(f"replay_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert callable(getattr(module, "run", None)), f"{path.name} has no run(ctx)"
        yield path.stem, module


def errors(output):
    return {(m["code"], m["path"]) for m in map(FINDING.match, output.splitlines()) if m and m["code"].startswith("E")}


def check_errors(ctx):
    code, output = ctx.vela("check", "--today", TODAY, check=False)
    assert code in (0, 1), f"vela check failed as a tool (exit {code}):\n{output}"
    return errors(output)


def record_problems(text):
    """Lines of the record that do not read in today's grammar."""
    problems, section = [], None
    meta = parse.split_frontmatter(text)[0]
    if meta.get("type") != "session" or meta.get("status") not in ("open", "closed"):
        problems.append(f"frontmatter: {meta}")
    found = closegate.captures(text)
    for line in text.split("\n"):
        if line.startswith("## "):
            section = line[3:].strip()
        if section == "Captures" and line.startswith("- ["):
            match = closegate.CAPTURE_RE.match(line.strip())
            if not match:
                problems.append(f"capture: {line}")
            elif match["mark"] is not None:
                mark = MARK.match(match["mark"])
                if not mark or (mark["state"] and mark["state"] not in MARK_STATES):
                    problems.append(f"mark: {match['mark']}")
    rows = closegate.change_rows(text)
    table = [line for line in text.split("## Changes", 1)[-1].split("\n## ", 1)[0].split("\n")
             if line.startswith("|") and not set(line.replace("|", "").strip()) <= {"-", ":", " "}]
    if len(rows) != len(table) - 1:  # the header row is not a change
        problems.append(f"changes: {len(table) - 1} table rows, {len(rows)} read")
    for row in rows:
        if row.capture_number and row.capture_number not in found:
            problems.append(f"changes row {row.item} cites ^c{row.capture_number}, which no capture holds")
    return problems


def test_a_session_replays_end_to_end_on_todays_commands(tmp_path):
    vault, origin, bin_dir = build(tmp_path)
    ctx = Context(vault=vault, origin=origin, bin_dir=bin_dir, today=TODAY, record_id=RECORD_ID, outputs={}, calls=[])
    errors_before = check_errors(ctx)
    start = ctx.git("rev-parse", "HEAD").strip()
    ran = []
    for name, module in steps():
        module.run(ctx)
        ran.append(name)

    new_errors = check_errors(ctx) - errors_before
    assert not new_errors, f"the steps {ran} left errors vela check did not report before: {sorted(new_errors)}"

    record = vault / "sessions" / f"{RECORD_ID}.md"
    assert record.is_file(), "no step wrote the session record"
    problems = record_problems(record.read_text(encoding="utf-8"))
    assert not problems, "the record does not read in today's grammar:\n" + "\n".join(problems)

    subjects = ctx.git("log", "--format=%s", f"{start}..HEAD").splitlines()
    assert subjects, "the steps made no commit"
    for subject in subjects:
        match = next((m for m in (g.match(subject) for g in COMMIT_GRAMMAR) if m), None)
        assert match, f"commit {subject!r} is not a message START or close writes"
        assert match.groupdict().get("id") in (None, RECORD_ID), f"commit {subject!r} names another session"

    lead = [(args, output) for args, _, output in ctx.calls if "--for-lead" in args]
    assert lead, "no step ran a --for-lead output"
    for args, output in lead:
        assert say.leak_in(output) is None, f"vela {' '.join(args)} --for-lead showed the lead {say.leak_in(output)}:\n{output}"
        for kind, pattern in say.LEAD_PATTERNS.items():
            assert not pattern.search(output), f"vela {' '.join(args)}: a {kind} reached the lead:\n{output}"


def test_the_grammar_checks_catch_a_bad_record_and_a_bad_commit():
    good = ("---\nid: x\ntype: session\ndate: 2026-10-14\nmodes: [grill]\nstatus: open\nsummary: s.\n---\n\n# x\n\n"
            "## Captures\n\n- [decision] (@lead) \"Yes.\" → keep: [[p#CON-001 X|CON-001]] (decided) ^c01\n\n"
            "## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n| CON-001 | assumption | decided | [[x#^c01]] |\n")
    assert record_problems(good) == []
    assert record_problems(good.replace("(decided) ^c01", "(settled) ^c01"))
    assert record_problems(good.replace("[[x#^c01]]", "[[x#^c09]]"))
    assert record_problems(good.replace("| CON-001 | assumption | decided | [[x#^c01]] |", "| CON-001 | decided |"))
    assert not any(g.match("Close the session") for g in COMMIT_GRAMMAR)
    assert any(g.match(f"Close session {RECORD_ID}") for g in COMMIT_GRAMMAR)
