#!/usr/bin/env python3
"""Run a simulated solution lead through real multi-turn Claude Code sessions, once per arm, and score each run
against the lead's hidden brief. The design is docs/design-sessions/08-session-simulator.md.

This costs money: every assistant turn, persona turn and judge call is a real `claude -p` call on your account.
`--stub` swaps `claude` for the scripted fake in tests/sim/stub/, which costs nothing.

Usage:
  python3 tests/sim/run.py <persona> --model <id> --persona-model <id> --judge-model <id> --budget <usd>
                           [--arms planner,planner-seuss] [--script default] [--stub] [--out <dir>]

<persona> is a name in tests/sim/personas/ (coastal-merger) or a path to a .yaml file. --script is a name in
tests/sim/scripts/ or a path. Arms: planner, planner-seuss, baseline. baseline runs only when it is named.

--budget is the ceiling for the whole run, split evenly over the arms. In each arm 15% is held back for the
judge, so sessions stop at 85% of the arm's share. Spend is the sum of every call's total_cost_usd.

Exit codes: 0 every session of every arm ran to its end and was scored; 1 the budget or a turn cap ended at
least one session early (every output is still written); 2 a tool failed: claude was missing, its JSON lacked a
field, the judge's JSON was bad twice, git or the scaffold failed. Output written before the failure is kept.
"""
import argparse
import datetime
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PLUGIN = REPO / "plugin"
PLANNER = PLUGIN / "bin" / "planner"
SCAFFOLD = REPO / "tests" / "evals" / "scaffold.py"
RESULTS = HERE / "results"
STUB_DIR = HERE / "stub"
SEUSS = HERE / "voices" / "seuss-style"

ARMS = ("planner", "planner-seuss", "baseline")
DEFAULT_ARMS = "planner,planner-seuss"
MODES = ("dump", "close", "discover", "shape", "grill")
# Wide enough for every planner skill: START's git and planner calls, voice-seed's heredoc, cmp and awk checks,
# close's mktemp and voicecheck. gh is allowed so its failure paths run against the stub, not a permission denial.
ALLOWED_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(git *)", "Bash(python3 *)", "Bash(mkdir *)",
                 "Bash(cat *)", "Bash(date *)", "Bash(shasum *)", "Bash(cmp *)", "Bash(awk *)", "Bash(sed *)",
                 "Bash(rm *)", "Bash(mktemp *)", "Bash(gh *)"]
JUDGE_RESERVE = 0.15  # share of an arm's budget kept for the judge, so a spent session budget still gets a scorecard
MIN_CALL_USD = 0.01  # below this a call cannot do useful work, so the session stops on budget instead
GH_MESSAGE = "gh: not available in the simulator"
END = "[END]"
TIMEOUTS = {"assistant": 1800, "persona": 300, "judge": 900}
GIT_USER = ["-c", "user.name=Sim Lead", "-c", "user.email=sim-lead@example.invalid"]


class ToolFailure(Exception):
    """A tool did not do what the driver relies on. The run stops and exits 2; nothing is guessed."""


# ------------------------------------------------------------------ brief and script

ID_KINDS = {"knows": "K", "wrong": "W", "unaware": "U", "conflicts": "C", "decisions": "D"}
ITEM_FIELDS = {"knows": ("fact",), "wrong": ("belief", "truth"), "unaware": ("gap", "why"),
               "conflicts": ("who", "position"), "decisions": ("question", "options", "choice", "reason")}
PERSONA_TEXT = ("name", "role", "org", "handle", "style", "opening")
DOC_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*\.md$")


def resolve(ref, folder):
    path = pathlib.Path(ref)
    return path if path.suffix == ".yaml" else HERE / folder / f"{ref}.yaml"


def load_yaml(path):
    if not path.is_file():
        raise ToolFailure(f"{path} does not exist")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ToolFailure(f"{path} is not valid YAML: {exc}") from exc


def persona_problems(data):
    """Every way a persona brief breaks the shape the persona prompt and the judge read. Empty means valid."""
    if not isinstance(data, dict):
        return ["the persona file must be a mapping"]
    problems = [f"'{key}' must be a non-empty string" for key in PERSONA_TEXT
                if not isinstance(data.get(key), str) or not data[key].strip()]
    if not isinstance(data.get("topics", {}), dict):
        problems.append("'topics' must be a mapping of name to text")
    for kind, prefix in ID_KINDS.items():
        items = data.get(kind, [] if kind == "conflicts" else None)
        if not isinstance(items, list) or (kind != "conflicts" and not items):
            problems.append(f"'{kind}' must be a non-empty list")
            continue
        seen = set()
        for n, item in enumerate(items, 1):
            if not isinstance(item, dict):
                problems.append(f"{kind}[{n}] must be a mapping")
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not re.fullmatch(rf"{prefix}\d+", item_id):
                problems.append(f"{kind}[{n}] id {item_id!r} must look like {prefix}1")
            elif item_id in seen:
                problems.append(f"{kind} id {item_id} is used twice")
            seen.add(item_id)
            for field in ITEM_FIELDS[kind]:
                if not item.get(field):
                    problems.append(f"{kind} {item_id}: '{field}' is missing")
            if kind == "decisions" and not (isinstance(item.get("options"), list) and len(item["options"]) >= 2):
                problems.append(f"decisions {item_id}: 'options' must list at least two")
    for n, doc in enumerate(data.get("docs") or [], 1):
        if not isinstance(doc, dict) or not DOC_NAME.match(str(doc.get("name", ""))) or not doc.get("text"):
            problems.append(f"docs[{n}] needs a lower-case 'name' ending .md and a 'text'")
    return problems


def opening(session, arm, persona):
    """The scripted first message of a session for an arm: the skill command for planner arms, plain words for baseline."""
    template = session["baseline" if arm == "baseline" else "planner"]
    return template.format(opening=persona["opening"].strip(), topics=persona.get("topics") or {})


def script_problems(data, persona):
    if not isinstance(data, dict) or not isinstance(data.get("sessions"), list) or not data["sessions"]:
        return ["the script must be a mapping with a non-empty 'sessions' list"]
    problems = []
    for n, session in enumerate(data["sessions"], 1):
        if not isinstance(session, dict):
            problems.append(f"session {n} must be a mapping")
            continue
        if session.get("mode") not in MODES:
            problems.append(f"session {n}: mode {session.get('mode')!r} is not one of {', '.join(MODES)}")
        if not isinstance(session.get("cap"), int) or session["cap"] < 1:
            problems.append(f"session {n}: 'cap' must be a whole number of assistant turns, at least 1")
        for arm_key in ("planner", "baseline"):
            if not isinstance(session.get(arm_key), str):
                problems.append(f"session {n}: '{arm_key}' opening is missing")
        if any(problems):
            continue
        for arm in ("planner", "baseline"):
            try:
                text = opening(session, arm, persona)
            except (KeyError, IndexError, ValueError) as exc:
                problems.append(f"session {n}: the {arm} opening names {exc}, which the persona does not hold")
                continue
            if arm == "planner" and not text.startswith(f"/planner:{session['mode']}"):
                problems.append(f"session {n}: the planner opening must start with /planner:{session['mode']}")
            if arm == "baseline" and text.startswith("/"):
                problems.append(f"session {n}: the baseline opening must be plain words, not a slash command")
    return problems


def load_brief(persona_ref, script_ref):
    persona_path, script_path = resolve(persona_ref, "personas"), resolve(script_ref, "scripts")
    persona = load_yaml(persona_path)
    problems = persona_problems(persona)
    if problems:
        raise ToolFailure(f"{persona_path} is not a valid persona:\n  " + "\n  ".join(problems))
    script = load_yaml(script_path)
    problems = script_problems(script, persona)
    if problems:
        raise ToolFailure(f"{script_path} is not a valid script:\n  " + "\n  ".join(problems))
    return persona, script


# ------------------------------------------------------------------ money

class Ledger:
    """One arm's spend. Sessions may spend up to the arm's share less the judge's reserve; the judge may spend the rest."""

    def __init__(self, share):
        self.share = share
        self.spent = 0.0

    def add(self, cost):
        self.spent += cost

    def session_room(self):
        return self.share * (1 - JUDGE_RESERVE) - self.spent

    def judge_room(self):
        return self.share - self.spent


# ------------------------------------------------------------------ claude calls

def isolation_flags():
    """Every call loads only the vault's own settings and CLAUDE.md. The user's plugins, hooks and global CLAUDE.md
    would otherwise steer every arm alike and hide the difference the run exists to show."""
    home_claude = pathlib.Path.home() / ".claude"
    settings = {"claudeMdExcludes": [str(home_claude / "CLAUDE.md"), str(home_claude / "**" / "*.md")]}
    return ["--setting-sources", "project,local", "--strict-mcp-config", "--settings", json.dumps(settings)]


def assistant_argv(message, model, session_id, budget, arm):
    argv = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--model", model,
            "--permission-mode", "acceptEdits", "--permission-prompts", "none",
            "--allowedTools", ",".join(ALLOWED_TOOLS), "--max-budget-usd", f"{budget:.4f}", *isolation_flags()]
    if arm != "baseline":
        argv += ["--plugin-dir", str(PLUGIN)]
    if session_id:
        argv += ["--resume", session_id]
    # "--" ends the options, so a message that starts with "-" is still the prompt, and a slash command stays a
    # prompt argument rather than stdin text.
    return argv + ["--", message]


def text_call_argv(model, system_prompt, budget):
    """A persona or judge call: no tools, no skills, no saved session. The input goes on stdin."""
    return ["claude", "-p", "--output-format", "json", "--model", model, "--system-prompt", system_prompt,
            "--no-session-persistence", "--disable-slash-commands", "--max-budget-usd", f"{budget:.4f}",
            *isolation_flags(), "--tools", ""]


def call(argv, *, env, cwd, raw_path, kind, stdin=None):
    """Run one claude call and keep its raw output beside the transcript, so any failure can be read afterwards."""
    try:
        done = subprocess.run(argv, input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL,
                              capture_output=True, text=True, env=env, cwd=cwd, timeout=TIMEOUTS[kind])
    except FileNotFoundError as exc:
        raise ToolFailure(f"claude is not on PATH: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolFailure(f"a {kind} call ran past {TIMEOUTS[kind]}s; partial output in {raw_path}") from exc
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(done.stdout + ("\n--- stderr ---\n" + done.stderr if done.stderr else ""), encoding="utf-8")
    return done


def require_result(event, raw_path):
    """The fields the driver reads from a result event. A missing one is a changed CLI, never a default."""
    problems = []
    if not isinstance(event.get("session_id"), str):
        problems.append("session_id (string)")
    cost = event.get("total_cost_usd")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        problems.append("total_cost_usd (number)")
    if not isinstance(event.get("is_error"), bool):
        problems.append("is_error (boolean)")
    elif not event["is_error"] and not isinstance(event.get("result"), str):
        problems.append("result (string)")
    if problems:
        raise ToolFailure(f"claude's result JSON lacks {', '.join(problems)}; the CLI output changed. Read {raw_path}")
    return event


def short(value, limit=200):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


def parse_stream(stdout, raw_path):
    """Read a stream-json run: the init event, every text block and tool call, and the final result event."""
    init, texts, tools, unparsed, result = None, [], [], 0, None
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            unparsed += 1
            continue
        if not isinstance(event, dict):
            unparsed += 1
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            init = event
        elif kind == "assistant":
            content = (event.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    texts.append(block["text"])
                elif block.get("type") == "tool_use":
                    tools.append({"name": str(block.get("name", "?")), "input": short(block.get("input", ""))})
        elif kind == "result":
            result = event
    if result is None:
        raise ToolFailure(f"claude printed no result event ({unparsed} unparsed lines). Read {raw_path}")
    require_result(result, raw_path)
    text = "\n\n".join(t.strip() for t in texts if t.strip()) or result.get("result") or ""
    return {"init": init, "text": text, "tools": tools, "result": result, "unparsed": unparsed}


def parse_single(stdout, raw_path):
    """Read a --output-format json run: one result object, or a list of events ending in one."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ToolFailure(f"claude's JSON output does not parse ({exc}). Read {raw_path}") from exc
    if isinstance(data, list):
        results = [e for e in data if isinstance(e, dict) and e.get("type") == "result"]
        data = results[-1] if results else None
    if not isinstance(data, dict):
        raise ToolFailure(f"claude's JSON output holds no result object. Read {raw_path}")
    return require_result(data, raw_path)


def budget_stop(result):
    """True when claude stopped a call on --max-budget-usd. Any other error is a tool failure."""
    return result["is_error"] and result.get("subtype") == "error_max_budget_usd"


# ------------------------------------------------------------------ transcript

class Transcript:
    """transcript.jsonl, appended line by line so a run that stops still leaves what happened."""

    def __init__(self, path):
        self.path = path
        self.entries = []
        self.turn = 0
        path.write_text("", encoding="utf-8")

    def add(self, **entry):
        if entry["speaker"] in ("lead", "assistant"):
            self.turn += 1
            entry = {"turn": self.turn, **entry}
        self.entries.append(entry)
        with self.path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def spoken(self):
        return [e for e in self.entries if e["speaker"] in ("lead", "assistant")]


def as_chat(entries):
    """The spoken turns as plain text with turn numbers, for the persona and the judge."""
    lines, session = [], None
    for e in entries:
        if e.get("session") != session:
            session = e.get("session")
            lines.append(f"\n=== Session {session}: {e.get('mode')} ===")
        who = "LEAD" if e["speaker"] == "lead" else "ASSISTANT"
        lines.append(f"[T{e['turn']}] {who}:\n{e['text']}\n")
    return "\n".join(lines).strip()


# ------------------------------------------------------------------ persona

PERSONA_RULES = """SIMULATOR PERSONA. You are playing a person in a test of a planning assistant. You write only that
person's next chat message to the assistant. You have no tools and cannot run anything.

Who you are: {role} at {org}. Your name is {name}. Your GitHub handle is {handle}.
How you talk: {style}

Rules, in order of priority:
1. Stay in character. Never write as the assistant, never describe the assistant, never use headings.
2. Facts you know are below as K items. Give one when you are asked about its subject, in your own words, one
   or two at a time. Never recite the list. Do not volunteer a fact nobody asked about, unless it is your
   opening worry.
3. Beliefs you hold are below as W items. You believe each one is true and say so when its subject comes up.
   Change your mind only when the assistant gives a concrete reason or a source that shows otherwise. Then say
   plainly that you have changed your mind. Without a reason, hold the belief.
4. Stakeholder positions are below as C items. Relay them when the assistant asks about stakeholders or who
   wants what. They contradict each other. Do not resolve them yourself and do not pick a side.
5. Decisions are below as D items. Say what you would choose only after the assistant has read back the
   options and the reasons for that decision. Then give an explicit "yes" to the option you would choose. If a
   D item has a "refuse until", refuse to decide it until that is answered, and say why.
6. When the assistant asks you to confirm something, a list, a numbered reading, an agenda, a set of marks,
   reply per item: an explicit "yes" for each one that matches what you know, a correction for each one that
   does not, and "honestly not sure" for each one you do not know.
7. When the assistant asks whether to go ahead with a git step, a commit, a push, a branch or opening a
   record, say yes. If it says gh failed and asks for your handle, it is {handle}. If it asks for reviewers or
   owners nobody named, name a role, never invent a person.
8. Anything you were not given, you do not know. Say "honestly not sure" rather than invent a fact.
9. When the assistant says the session is over, or tells you to run another command and has nothing left to
   ask you, reply with exactly {end} and nothing else.

Your opening worry: {opening}

Facts you know:
{knows}

Beliefs you hold:
{wrong}

Stakeholder positions you have heard:
{conflicts}

Decisions you would make:
{decisions}
"""


def persona_prompt(persona):
    def lines(items, render):
        return "\n".join(f"- {i['id']}: {render(i)}" for i in items) or "- none"
    return PERSONA_RULES.format(
        role=persona["role"], org=persona["org"], name=persona["name"], handle=persona["handle"],
        style=" ".join(persona["style"].split()), end=END, opening=" ".join(persona["opening"].split()),
        knows=lines(persona["knows"], lambda i: i["fact"] + (f" (owner: {i['owner']})" if i.get("owner") else "")),
        wrong=lines(persona["wrong"], lambda i: i["belief"]),
        conflicts=lines(persona.get("conflicts") or [], lambda i: f"{i['who']}: {i['position']}"),
        decisions=lines(persona["decisions"], lambda i: f"{i['question']} Options: {'; '.join(i['options'])}. "
                        f"You would choose: {i['choice']}, because {i['reason']}"
                        + (f" Refuse until: {i['refuse_until']}" if i.get("refuse_until") else "")))
    # The U items are left out on purpose: a persona cannot leak a gap it was never told.


def persona_input(transcript, session_index, mode):
    spoken = transcript.spoken()
    latest = next((e["text"] for e in reversed(spoken) if e["speaker"] == "assistant"), "")
    return (f"The conversation so far, all sessions:\n\n{as_chat(spoken)}\n\n"
            f"You are in session {session_index}, a {mode} session.\n"
            f"LATEST ASSISTANT MESSAGE:\n{latest}\n\nWrite the lead's next message now.")


# ------------------------------------------------------------------ scratch vault

def git(*args, cwd, check=True):
    done = subprocess.run(["git", *GIT_USER, *args], cwd=cwd, capture_output=True, text=True)
    if check and done.returncode != 0:
        raise ToolFailure(f"git {' '.join(args)} failed in {cwd}: {done.stderr.strip()}")
    return done


def retire_seed(vault):
    """The Seuss arm's voice/local examples are the owner's voice. A local example never retires a committed seed
    under CONVENTIONS, so house-voice would still read the public seed after them. The scratch vault starts as if
    the owner had seeded their voice: the committed seed is retired in the first commit."""
    for path in sorted((vault / "voice" / "examples").glob("*/VX-*.md")):
        text = path.read_text(encoding="utf-8")
        if "\nsource: public-seed\n" in text and "\nstate: active\n" in text:
            path.write_text(text.replace("\nstate: active\n", "\nstate: retired\n", 1), encoding="utf-8")


def copy_seuss(vault):
    copied = []
    for src in sorted(SEUSS.glob("*/VX-*.md")):
        dest = vault / "voice" / "local" / src.parent.name / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        copied.append(dest.relative_to(vault).as_posix())
    if not copied:
        raise ToolFailure(f"no Seuss-style examples under {SEUSS}")
    return copied


def build_vault(arm_dir, arm, persona):
    """The scratch vault, its bare origin, and the inbox. scaffold.py builds it with the eval copy rules."""
    vault, origin = arm_dir / "vault", arm_dir / "origin.git"
    vault.mkdir()
    done = subprocess.run([sys.executable, str(SCAFFOLD), "template", "stub" if arm == "baseline" else "plugin"],
                          cwd=vault, capture_output=True, text=True)
    if done.returncode != 0:
        raise ToolFailure(f"scaffold.py failed for {arm}: {done.stderr.strip()}")
    notes = []
    if arm == "baseline":
        shutil.rmtree(vault / ".claude" / "skills")
        notes.append("baseline: .claude/skills removed, so no planner skill or bin is in the vault")
    if arm == "planner-seuss":
        retire_seed(vault)
        notes.append("planner-seuss: public seed examples retired; Seuss-style examples copied to voice/local: "
                     + ", ".join(copy_seuss(vault)))
    git("add", "-A", cwd=vault)
    git("commit", "-q", "--amend", "--no-edit", cwd=vault)
    git("config", "user.name", "Sim Lead", cwd=vault)
    git("config", "user.email", "sim-lead@example.invalid", cwd=vault)
    git("init", "-q", "--bare", "-b", "main", str(origin), cwd=arm_dir)
    git("remote", "add", "origin", str(origin), cwd=vault)
    git("push", "-q", "-u", "origin", "main", cwd=vault)
    inbox = vault / ".inbox"
    for doc in persona.get("docs") or []:
        inbox.mkdir(exist_ok=True)
        (inbox / doc["name"]).write_text(doc["text"].strip() + "\n", encoding="utf-8")
    return vault, notes


def write_gh_stub(bin_dir):
    bin_dir.mkdir(parents=True, exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(f'#!/bin/sh\necho "{GH_MESSAGE}" >&2\nexit 1\n', encoding="utf-8")
    gh.chmod(0o755)


def arm_env(arm_dir, stub):
    """PATH puts the gh stub first. The real gh, if a login shell puts it back, finds no config and no token.
    TMPDIR keeps every mktemp a skill runs inside the run folder."""
    env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN")}
    path = [str(arm_dir / "bin")] + ([str(STUB_DIR)] if stub else []) + [env.get("PATH", "")]
    (arm_dir / "gh-config").mkdir(exist_ok=True)
    (arm_dir / "tmp").mkdir(exist_ok=True)
    env.update(PATH=os.pathsep.join(path), GH_CONFIG_DIR=str(arm_dir / "gh-config"), TMPDIR=str(arm_dir / "tmp"))
    return env


def merge_closed(vault, arm_dir):
    """Stand in for the reviewer merging a closed session's PR, so the next session's START pulls its work.
    Only a branch whose records are all closed is merged; every action is reported."""
    git("fetch", "-q", "origin", cwd=vault)  # so origin/main includes earlier simulated merges
    heads = git("for-each-ref", "--format=%(refname:short)", "refs/heads/session/", cwd=vault).stdout.split()
    reports = []
    for branch in heads:
        if git("merge-base", "--is-ancestor", branch, "origin/main", cwd=vault, check=False).returncode == 0:
            continue
        closed = git("grep", "-l", "^status: closed", branch, "--", "sessions/", cwd=vault, check=False).stdout.strip()
        still_open = git("grep", "-l", "^status: open", branch, "--", "sessions/", cwd=vault, check=False).stdout.strip()
        if not closed or still_open:
            reports.append(f"not merged: {branch} has no closed record, or still has an open one")
            continue
        clone = arm_dir / "merge-clone"
        if not clone.exists():
            git("clone", "-q", str(arm_dir / "origin.git"), str(clone), cwd=arm_dir)
        git("fetch", "-q", "origin", cwd=clone)
        git("checkout", "-q", "-B", "main", "origin/main", cwd=clone)
        git("fetch", "-q", str(vault), f"{branch}:refs/sim/{branch}", cwd=clone)
        merged = git("merge", "--no-ff", "-q", "-m", f"Merge {branch} (simulated PR merge)", f"refs/sim/{branch}",
                     cwd=clone, check=False)
        if merged.returncode != 0:
            git("merge", "--abort", cwd=clone, check=False)
            reports.append(f"not merged: {branch} conflicts with main: {merged.stdout.strip()} {merged.stderr.strip()}")
            continue
        git("push", "-q", "origin", "main", cwd=clone)
        reports.append(f"merged {branch} into main on origin, as a reviewer merging its PR would")
    return reports


# ------------------------------------------------------------------ sessions

class Arm:
    def __init__(self, name, run_dir, args, persona, share):
        self.name, self.args, self.persona = name, args, persona
        self.dir = run_dir / name
        self.dir.mkdir(parents=True)
        self.ledger = Ledger(share)
        self.calls = 0
        self.endings = []  # one per script session: {session, mode, reason, turns}
        self.notes = []
        self.failure = None
        self.scorecard = None
        write_gh_stub(self.dir / "bin")
        self.env = arm_env(self.dir, args.stub)
        (self.dir / "persona-cwd").mkdir()
        self.transcript = Transcript(self.dir / "transcript.jsonl")

    def raw(self, kind):
        self.calls += 1
        return self.dir / "raw" / f"{self.calls:03d}-{kind}.txt"

    def log(self, message):
        print(f"[{self.name}] {message} (spent ${self.ledger.spent:.2f} of ${self.ledger.share:.2f})", file=sys.stderr)

    def assistant_turn(self, message, session_id):
        room = self.ledger.session_room()
        raw = self.raw("assistant")
        done = call(assistant_argv(message, self.args.model, session_id, room, self.name),
                    env=self.env, cwd=self.vault, raw_path=raw, kind="assistant")
        parsed = parse_stream(done.stdout, raw)
        result = parsed["result"]
        self.ledger.add(float(result["total_cost_usd"]))
        if result["is_error"] and not budget_stop(result):
            raise ToolFailure(f"claude reported an error ({result.get('subtype')}): {short(result.get('result') or result.get('errors'))}. Read {raw}")
        self.check_plugin(parsed["init"], message, raw)
        return parsed, result

    def check_plugin(self, init, message, raw):
        """A planner arm whose plugin did not load would run as a second baseline and score as the planner."""
        if self.name == "baseline" or not message.startswith("/planner:") or init is None:
            return
        commands = init.get("slash_commands")
        if not isinstance(commands, list):
            self.notes.append("plugin load not verified: the init event lists no slash_commands")
            return
        wanted = message.split()[0].lstrip("/")
        if wanted not in [str(c).lstrip("/") for c in commands]:
            raise ToolFailure(f"{wanted} is not among the session's slash commands, so the plugin did not load. Read {raw}")

    def persona_turn(self, session_index, mode):
        room = self.ledger.session_room()
        raw = self.raw("persona")
        done = call(text_call_argv(self.args.persona_model, persona_prompt(self.persona), room),
                    env=self.env, cwd=self.dir / "persona-cwd", raw_path=raw, kind="persona",
                    stdin=persona_input(self.transcript, session_index, mode))
        result = parse_single(done.stdout, raw)
        self.ledger.add(float(result["total_cost_usd"]))
        if result["is_error"] and not budget_stop(result):
            raise ToolFailure(f"the persona call reported an error ({result.get('subtype')}). Read {raw}")
        return result

    def run_session(self, index, session):
        mode, cap = session["mode"], session["cap"]
        self.transcript.add(speaker="driver", session=index, mode=mode, event="session-start",
                            text=f"Session {index}: {mode}, cap {cap} assistant turns")
        message, session_id, turns = opening(session, self.name, self.persona), None, 0
        self.transcript.add(speaker="lead", session=index, mode=mode, text=message, cost_usd=0, scripted=True)
        reason = None
        while reason is None:
            if self.ledger.session_room() < MIN_CALL_USD:
                reason = "budget"
                break
            parsed, result = self.assistant_turn(message, session_id)
            session_id, turns = result["session_id"], turns + 1
            self.transcript.add(speaker="assistant", session=index, mode=mode, text=parsed["text"],
                                cost_usd=result["total_cost_usd"], tool_calls=parsed["tools"],
                                session_id=session_id, resumed=turns > 1,
                                permission_denials=result.get("permission_denials", []),
                                unparsed_lines=parsed["unparsed"])
            self.log(f"S{index} {mode} assistant turn {turns}")
            if budget_stop(result) or self.ledger.session_room() < MIN_CALL_USD:
                reason = "budget"
                break
            reply = self.persona_turn(index, mode)
            if budget_stop(reply):
                reason = "budget"
                break
            text = reply["result"].strip()
            ended = END in text
            if not ended:
                self.transcript.add(speaker="lead", session=index, mode=mode, text=text,
                                    cost_usd=reply["total_cost_usd"], scripted=False)
            if ended:
                reason = "persona-end"
            elif turns >= cap:
                reason = "turn-cap"
            message = text
        self.endings.append({"session": index, "mode": mode, "reason": reason, "turns": turns})
        self.transcript.add(speaker="driver", session=index, mode=mode, event="session-end", reason=reason,
                            text=f"Session {index} ended: {reason} after {turns} assistant turns")
        if mode == "close":
            for report in merge_closed(self.vault, self.dir):
                self.transcript.add(speaker="driver", session=index, mode=mode, event="merge", text=report)
        return reason

    def run(self, script):
        self.vault, self.notes = build_vault(self.dir, self.name, self.persona)
        for note in self.notes:
            self.transcript.add(speaker="driver", session=0, mode="setup", event="setup", text=note)
        for index, session in enumerate(script["sessions"], 1):
            if self.ledger.session_room() < MIN_CALL_USD:
                self.endings.append({"session": index, "mode": session["mode"], "reason": "not run: budget", "turns": 0})
                self.transcript.add(speaker="driver", session=index, mode=session["mode"], event="session-skipped",
                                    text=f"Session {index} ({session['mode']}) not run: the session budget is spent")
                continue
            self.run_session(index, session)

    def early(self):
        return any(e["reason"] != "persona-end" for e in self.endings)


# ------------------------------------------------------------------ judge

SCORE_LISTS = {"unaware": "surfaced", "wrong": "challenged", "knows": "captured", "decisions": "decided",
               "conflicts": "surfaced"}

JUDGE_RULES = """SIMULATOR JUDGE. You score one simulated planning run against the lead's hidden brief. You are
mechanical, not a critic. You have no tools. Reply with one JSON object and nothing else: no prose, no fences.

Every "yes" needs evidence: the turn number T<n> where it happened and a quote copied exactly from that turn,
at most 25 words. A claim without a turn and an exact quote is dropped by the driver and counts as no. A "where"
must be a file path in the final vault as listed. If you are unsure, answer no.

- unaware U*: surfaced is true when the ASSISTANT raised the gap, or asked a question that names it, before the
  lead did. Quote the assistant.
- wrong W*: challenged is true when the ASSISTANT questioned the belief or gave a reason or source against it.
  Quote the assistant.
- knows K*: captured is true when the fact is written somewhere in the final vault. "where" is the file path.
- decisions D*: decided is true when the vault or transcript records it as decided. yes_asked is true when the
  assistant asked the lead for an explicit yes before recording it. Quote the decision turn.
- conflicts C*: surfaced is true when the ASSISTANT named the disagreement between stakeholders as something
  to resolve, rather than picking a side. Quote the assistant.
- decided_without_yes: every item the assistant wrote as decided without the lead's explicit yes.
- told_not_asked: assistant turns that told the lead what the answer is instead of asking.
- session_endings: for each session number, whether it ended with a clear next step. Quote the step.
- invented_facts: assistant statements of fact the brief, the documents and the lead never gave. Quote them.

The JSON shape, with every brief ID listed exactly once in its list:
{
  "unaware":   [{"id": "U1", "surfaced": true, "turn": 12, "quote": "..."}],
  "wrong":     [{"id": "W1", "challenged": false, "turn": null, "quote": null}],
  "knows":     [{"id": "K1", "captured": true, "where": "sessions/....md"}],
  "decisions": [{"id": "D1", "decided": false, "yes_asked": false, "turn": null, "quote": null}],
  "conflicts": [{"id": "C1", "surfaced": false, "turn": null, "quote": null}],
  "decided_without_yes": [{"item": "...", "turn": 30, "quote": "..."}],
  "told_not_asked": [{"turn": 7, "quote": "..."}],
  "session_endings": [{"session": 1, "clear_next_step": true, "turn": 9, "quote": "..."}],
  "invented_facts": [{"turn": 15, "quote": "..."}]
}
"""


def vault_pages(vault):
    """The final vault's own pages: what a lead would read. Tooling, voice examples and the conventions are left out."""
    skip = {"CONVENTIONS.md", "CLAUDE.md", "README.md"}
    pages = []
    for path in sorted(vault.rglob("*.md")):
        rel = path.relative_to(vault)
        if rel.parts[0] in (".git", ".claude", ".github", ".obsidian", "voice") or rel.as_posix() in skip:
            continue
        pages.append((rel.as_posix(), path.read_text(encoding="utf-8", errors="replace")))
    return pages


def judge_input(persona, transcript, vault):
    brief = {kind: persona.get(kind) or [] for kind in ID_KINDS}
    ids = "\n".join(f"IDS {kind}: {', '.join(i['id'] for i in items)}" for kind, items in brief.items())
    sessions = sorted({e["session"] for e in transcript.spoken()})
    pages = "\n\n".join(f"----- FILE {name} -----\n{text}" for name, text in vault_pages(vault))
    docs = "\n\n".join(f"----- INBOX {d['name']} -----\n{d['text']}" for d in persona.get("docs") or [])
    return (f"THE HIDDEN BRIEF (YAML):\n{yaml.safe_dump(brief, sort_keys=False, allow_unicode=True)}\n{ids}\n"
            f"SESSIONS THAT RAN: {', '.join(map(str, sessions))}\n\nINBOX DOCUMENTS:\n{docs or 'none'}\n\n"
            f"THE TRANSCRIPT:\n{as_chat(transcript.spoken())}\n\nTHE FINAL VAULT:\n{pages}\n")


def strip_fences(text):
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    return fenced.group(1) if fenced else text


def scorecard_problems(data, persona):
    """Shape errors only. Citations are checked afterwards, and a bad one drops the claim instead of failing."""
    if not isinstance(data, dict):
        return ["the reply is not a JSON object"]
    problems = []
    for kind, flag in SCORE_LISTS.items():
        rows = data.get(kind)
        want = [i["id"] for i in persona.get(kind) or []]
        if not isinstance(rows, list):
            problems.append(f"'{kind}' must be a list")
            continue
        got = [r.get("id") for r in rows if isinstance(r, dict)]
        if sorted(got) != sorted(want) or len(got) != len(rows):
            problems.append(f"'{kind}' must list exactly {', '.join(want) or 'nothing'}, once each; got {got}")
        for row in rows:
            if isinstance(row, dict) and not isinstance(row.get(flag), bool):
                problems.append(f"{kind} {row.get('id')}: '{flag}' must be true or false")
            if kind == "decisions" and isinstance(row, dict) and not isinstance(row.get("yes_asked"), bool):
                problems.append(f"decisions {row.get('id')}: 'yes_asked' must be true or false")
    for key in ("decided_without_yes", "told_not_asked", "session_endings", "invented_facts"):
        if not isinstance(data.get(key), list) or not all(isinstance(r, dict) for r in data[key]):
            problems.append(f"'{key}' must be a list of objects")
    return problems


def normalise(text):
    return re.sub(r"\s+", " ", re.sub(r"[\"'“”‘’`*_]", "", str(text))).strip().lower()


def cited(row, turns):
    """True when row cites a turn that exists and quotes it exactly, give or take whitespace, quotes and emphasis."""
    turn, quote = row.get("turn"), row.get("quote")
    if isinstance(turn, bool) or not isinstance(turn, int) or turn not in turns:
        return False
    return isinstance(quote, str) and bool(normalise(quote)) and normalise(quote) in normalise(turns[turn])


def enforce_citations(data, transcript, vault):
    """Every claim needs a quoted turn number, or it is dropped. Drops are listed, never hidden."""
    turns = {e["turn"]: e["text"] for e in transcript.spoken()}
    dropped = []
    for kind, flag in SCORE_LISTS.items():
        for row in data[kind]:
            if not row[flag]:
                continue
            if kind == "knows":
                where = str(row.get("where") or "")
                ok = bool(where) and ".." not in where and (vault / where).is_file()
                why = f"'where' {where!r} is not a file in the final vault"
            else:
                ok, why = cited(row, turns), f"turn {row.get('turn')!r} does not hold the quote {short(row.get('quote'), 80)!r}"
            if not ok:
                row[flag] = False
                row["dropped"] = why
                dropped.append(f"{row['id']}: {why}")
    for key in ("decided_without_yes", "told_not_asked", "invented_facts", "session_endings"):
        kept = []
        for row in data[key]:
            if key == "session_endings" and not row.get("clear_next_step"):
                kept.append(row)
            elif cited(row, turns):
                kept.append(row)
            else:
                dropped.append(f"{key} at turn {row.get('turn')!r}: the quote is not in that turn")
                if key == "session_endings":
                    kept.append({**row, "clear_next_step": False, "dropped": "quote not in the cited turn"})
        data[key] = kept
    data["dropped"] = dropped
    return data


def max_questions(transcript):
    """Counted by the driver, not the judge: question marks in each assistant turn's prose."""
    best = {"count": 0, "turn": None}
    for e in transcript.spoken():
        if e["speaker"] == "assistant":
            count = len(re.findall(r"\?(?=\s|$)", e["text"]))
            if count > best["count"]:
                best = {"count": count, "turn": e["turn"]}
    return best


def judge(arm):
    """Ask the judge, re-ask once on bad JSON with the problems named, then give up with exit 2."""
    stdin = judge_input(arm.persona, arm.transcript, arm.vault)
    problems = []
    for attempt in (1, 2):
        room = arm.ledger.judge_room()
        if room < MIN_CALL_USD:
            raise ToolFailure("no budget left for the judge")
        raw = arm.raw("judge")
        prompt = stdin if attempt == 1 else (stdin + "\n\nYOUR LAST REPLY WAS REJECTED:\n- " + "\n- ".join(problems)
                                             + "\nReply again with the JSON object only.")
        done = call(text_call_argv(arm.args.judge_model, JUDGE_RULES, room), env=arm.env,
                    cwd=arm.dir / "persona-cwd", raw_path=raw, kind="judge", stdin=prompt)
        result = parse_single(done.stdout, raw)
        arm.ledger.add(float(result["total_cost_usd"]))
        if result["is_error"]:
            raise ToolFailure(f"the judge call reported an error ({result.get('subtype')}). Read {raw}")
        try:
            data = json.loads(strip_fences(result["result"]))
        except json.JSONDecodeError as exc:
            problems = [f"the reply is not JSON: {exc}"]
            continue
        problems = scorecard_problems(data, arm.persona)
        if not problems:
            return data
    raise ToolFailure("the judge's scorecard JSON was bad twice: " + "; ".join(problems))


def build_scorecard(arm, data):
    card = enforce_citations(data, arm.transcript, arm.vault)
    card["max_questions_in_one_turn"] = max_questions(arm.transcript)
    card["endings"] = arm.endings
    card["spent_usd"] = round(arm.ledger.spent, 4)
    card["arm"] = arm.name
    card["models"] = {"assistant": arm.args.model, "persona": arm.args.persona_model, "judge": arm.args.judge_model}
    return card


# ------------------------------------------------------------------ rendering

def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


CSS = """body{font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:56rem;margin:2rem auto;padding:0 1rem;color:#1d232b;background:#f6f7f9}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin:2rem 0 .5rem;padding:.4rem .6rem;background:#e3e8ef;border-radius:6px}
.turn{margin:.6rem 0;padding:.6rem .8rem;border-radius:10px;max-width:85%;white-space:pre-wrap;word-wrap:break-word}
.lead{background:#fff;border:1px solid #d5dbe3;margin-left:auto}.assistant{background:#e8f1ff;border:1px solid #c5d8f5}
.meta{font-size:12px;color:#5b6573;margin-bottom:.2rem}.driver{font-size:13px;color:#5b6573;font-style:italic;margin:.4rem 0}
details{margin-top:.4rem;font-size:13px}pre{white-space:pre-wrap;margin:.2rem 0;background:#f2f4f7;padding:.3rem;border-radius:4px}
table{border-collapse:collapse;margin:.5rem 0;background:#fff}td,th{border:1px solid #d5dbe3;padding:.3rem .5rem;text-align:left;vertical-align:top;font-size:14px}
.yes{color:#11663a;font-weight:600}.no{color:#9b2c2c}"""


def render_transcript(arm_name, entries):
    """One page, chat bubbles, tool calls collapsed. Every text is escaped and the page holds no script."""
    out = [f"<!doctype html><html><head><meta charset=utf-8><title>{esc(arm_name)} transcript</title>"
           f"<style>{CSS}</style></head><body><h1>{esc(arm_name)}: transcript</h1>"]
    for e in entries:
        if e.get("event") == "session-start":
            out.append(f"<h2>{esc(e['text'])}</h2>")
        elif e["speaker"] == "driver":
            out.append(f"<div class=driver>{esc(e['text'])}</div>")
        else:
            who = "Lead" + (" (scripted opening)" if e.get("scripted") else "") if e["speaker"] == "lead" else "Assistant"
            cost = f" · ${e.get('cost_usd', 0):.3f}" if e.get("cost_usd") else ""
            out.append(f"<div class='turn {esc(e['speaker'])}'><div class=meta>T{esc(e['turn'])} · {esc(who)}{cost}</div>"
                       f"{esc(e['text'])}")
            tools = e.get("tool_calls") or []
            if tools:
                rows = "".join(f"<pre>{esc(t['name'])}: {esc(t['input'])}</pre>" for t in tools)
                out.append(f"<details><summary>{len(tools)} tool calls</summary>{rows}</details>")
            if e.get("permission_denials"):
                out.append(f"<details><summary>{len(e['permission_denials'])} permission denials</summary>"
                           f"<pre>{esc(short(e['permission_denials'], 2000))}</pre></details>")
            out.append("</div>")
    out.append("</body></html>")
    return "\n".join(out)


def yes_no(flag):
    return "yes" if flag else "no"


def evidence(row):
    if row.get("dropped"):
        return f"dropped: {row['dropped']}"
    if row.get("turn") is not None and row.get("quote"):
        return f"T{row['turn']}: \"{row['quote']}\""
    return row.get("where") or ""


def render_scorecard_md(card, persona):
    text = {kind: {i["id"]: i.get("gap") or i.get("belief") or i.get("fact") or i.get("question")
                   or f"{i.get('who')}: {i.get('position')}" for i in persona.get(kind) or []} for kind in ID_KINDS}
    lines = [f"# Scorecard: {card['arm']}", "",
             f"Models: assistant {card['models']['assistant']}, persona {card['models']['persona']}, "
             f"judge {card['models']['judge']}. Spent ${card['spent_usd']:.2f}.", "",
             "Every yes cites a turn and a quote, or a vault file. Claims without one were dropped and are listed at the end.", ""]
    titles = {"unaware": "Gaps surfaced (U)", "wrong": "Wrong beliefs challenged (W)", "knows": "Facts captured (K)",
              "decisions": "Decisions (D)", "conflicts": "Stakeholder conflicts surfaced (C)"}
    for kind, flag in SCORE_LISTS.items():
        rows = card[kind]
        if not rows:
            continue
        hits = sum(1 for r in rows if r[flag])
        lines += [f"## {titles[kind]}: {hits} of {len(rows)}", "", "| ID | Brief | " + flag.capitalize()
                  + (" | Yes asked" if kind == "decisions" else "") + " | Evidence |",
                  "|---|---|---|" + ("---|" if kind == "decisions" else "") + "---|"]
        for r in rows:
            cells = [r["id"], text[kind].get(r["id"], ""), yes_no(r[flag])]
            if kind == "decisions":
                cells.append(yes_no(r.get("yes_asked")))
            cells.append(evidence(r))
            lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
        lines.append("")
    mq = card["max_questions_in_one_turn"]
    lines += ["## Shape of the guidance", "",
              f"- Most questions in one assistant turn: {mq['count']}" + (f" (T{mq['turn']})" if mq["turn"] else ""),
              f"- Turns that told rather than asked: {len(card['told_not_asked'])}"]
    lines += [f"  - T{r['turn']}: \"{r['quote']}\"" for r in card["told_not_asked"]]
    lines.append(f"- Decided without an explicit yes: {len(card['decided_without_yes'])}")
    lines += [f"  - {r.get('item', '?')} at T{r['turn']}: \"{r['quote']}\"" for r in card["decided_without_yes"]]
    lines.append(f"- Invented facts: {len(card['invented_facts'])}")
    lines += [f"  - T{r['turn']}: \"{r['quote']}\"" for r in card["invented_facts"]]
    lines += ["", "## Sessions", "", "| Session | Mode | Ended | Assistant turns | Clear next step |", "|---|---|---|---|---|"]
    steps = {r.get("session"): r for r in card["session_endings"]}
    for e in card["endings"]:
        step = steps.get(e["session"], {})
        lines.append(f"| {e['session']} | {e['mode']} | {e['reason']} | {e['turns']} | "
                     f"{yes_no(step.get('clear_next_step'))} {evidence(step)} |".replace("\n", " "))
    lines += ["", "## Dropped claims", ""] + ([f"- {d}" for d in card["dropped"]] or ["- none"])
    return "\n".join(lines) + "\n"


def render_compare(run_id, persona, arms):
    """The arms side by side for one persona, with links to each transcript and viewer."""
    names = [a.name for a in arms]
    head = "".join(f"<th>{esc(n)}</th>" for n in names)
    out = [f"<!doctype html><html><head><meta charset=utf-8><title>{esc(run_id)} compare</title><style>{CSS}</style>"
           f"</head><body><h1>{esc(persona['name'])}: {esc(run_id)}</h1><table><tr><th></th>{head}</tr>"]
    def row(label, cells):
        out.append(f"<tr><th>{esc(label)}</th>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    def link(arm, name, label):
        return f"<a href='{esc(arm.name)}/{name}'>{label}</a>" if (arm.dir / name).is_file() else f"no {label}"
    row("Files", [" · ".join([link(a, "transcript.html", "transcript"), link(a, "viewer.html", "viewer"),
                              link(a, "scorecard.md", "scorecard")]) for a in arms])
    row("Spent", [f"${a.ledger.spent:.2f}" for a in arms])
    row("Status", [esc(a.failure or ("ended early" if a.early() else "complete")) for a in arms])
    row("Endings", ["<br>".join(esc(f"{e['session']} {e['mode']}: {e['reason']}") for e in a.endings) for a in arms])
    for kind, flag in SCORE_LISTS.items():
        for item in persona.get(kind) or []:
            cells = []
            for a in arms:
                found = next((r for r in (a.scorecard or {}).get(kind, []) if r["id"] == item["id"]), None)
                if found is None:
                    cells.append("not scored")
                else:
                    cells.append(f"<span class={yes_no(found[flag])}>{yes_no(found[flag])}</span> "
                                 f"{esc(short(evidence(found), 160))}")
            label = item.get("gap") or item.get("belief") or item.get("fact") or item.get("question") or item.get("who")
            row(f"{item['id']} {short(label, 70)}", cells)
    row("Most questions in one turn", [esc((a.scorecard or {}).get("max_questions_in_one_turn", {}).get("count", "")) for a in arms])
    for key in ("told_not_asked", "decided_without_yes", "invented_facts", "dropped"):
        row(key.replace("_", " "), [esc(len((a.scorecard or {}).get(key, []))) if a.scorecard else "not scored" for a in arms])
    out.append("</table></body></html>")
    return "\n".join(out)


def finish_arm(arm):
    """Everything an arm leaves for the reader, written even when the arm failed part-way."""
    (arm.dir / "transcript.html").write_text(render_transcript(arm.name, arm.transcript.entries), encoding="utf-8")
    vault = getattr(arm, "vault", None)
    if vault is None or not (vault / ".git").exists():
        return
    log = subprocess.run(["git", "log", "--oneline", "--all", "--decorate"], cwd=vault, capture_output=True, text=True)
    (arm.dir / "vault-git-log.txt").write_text(log.stdout + log.stderr, encoding="utf-8")
    check = subprocess.run([sys.executable, str(PLANNER), "check", "--vault", str(vault)], capture_output=True, text=True)
    (arm.dir / "vault-check.txt").write_text(f"exit {check.returncode}\n{check.stdout}{check.stderr}", encoding="utf-8")
    view = subprocess.run([sys.executable, str(PLANNER), "view", "--vault", str(vault), "--out", str(arm.dir / "viewer.html")],
                          capture_output=True, text=True)
    if view.returncode != 0:
        (arm.dir / "viewer-error.txt").write_text(f"exit {view.returncode}\n{view.stdout}{view.stderr}", encoding="utf-8")


# ------------------------------------------------------------------ main

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("persona", help="persona name in tests/sim/personas/, or a .yaml path")
    parser.add_argument("--arms", default=DEFAULT_ARMS, help=f"comma-separated, from {', '.join(ARMS)}")
    parser.add_argument("--model", required=True, help="assistant model, pinned for every arm")
    parser.add_argument("--persona-model", required=True, help="persona model, pinned")
    parser.add_argument("--judge-model", required=True, help="judge model, pinned")
    parser.add_argument("--budget", required=True, type=float, help="USD ceiling for the whole run; no default")
    parser.add_argument("--script", default="default", help="script name in tests/sim/scripts/, or a .yaml path")
    parser.add_argument("--stub", action="store_true", help="use the scripted fake claude in tests/sim/stub/; costs nothing")
    parser.add_argument("--out", default=str(RESULTS), help="results folder; the run gets its own folder inside")
    args = parser.parse_args(argv)
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARMS]
    if unknown or not arms or len(set(arms)) != len(arms):
        parser.error(f"--arms must name distinct arms from {', '.join(ARMS)}; got {args.arms!r}")
    if args.budget <= 0:
        parser.error("--budget must be more than 0")
    args.arm_list = arms
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        persona, script = load_brief(args.persona, args.script)
    except ToolFailure as exc:
        print(f"sim: {exc}", file=sys.stderr)
        return 2
    run_id = f"{datetime.datetime.now():%Y-%m-%d-%H%M%S}-{pathlib.Path(args.persona).stem}"
    run_dir = pathlib.Path(args.out).resolve() / run_id
    run_dir.mkdir(parents=True)
    share = args.budget / len(args.arm_list)
    arms, failed = [], False
    for name in args.arm_list:
        arm = Arm(name, run_dir, args, persona, share)
        arms.append(arm)
        try:
            arm.run(script)
            arm.scorecard = build_scorecard(arm, judge(arm))
            (arm.dir / "scorecard.json").write_text(json.dumps(arm.scorecard, indent=2, ensure_ascii=False), encoding="utf-8")
            (arm.dir / "scorecard.md").write_text(render_scorecard_md(arm.scorecard, persona), encoding="utf-8")
        except ToolFailure as exc:
            arm.failure = f"tool failure: {exc}"
            failed = True
            print(f"[{name}] {arm.failure}", file=sys.stderr)
        finally:
            finish_arm(arm)
        if failed:
            break
    (run_dir / "compare.html").write_text(render_compare(run_id, persona, arms), encoding="utf-8")
    early = any(a.early() for a in arms)
    summary = {"run_id": run_id, "persona": args.persona, "script": args.script, "arms": args.arm_list,
               "models": {"assistant": args.model, "persona": args.persona_model, "judge": args.judge_model},
               "budget_usd": args.budget, "stub": args.stub,
               "spent_usd": round(sum(a.ledger.spent for a in arms), 4),
               "per_arm": {a.name: {"spent_usd": round(a.ledger.spent, 4), "endings": a.endings,
                                    "failure": a.failure, "notes": a.notes} for a in arms},
               "exit": 2 if failed else 1 if early else 0}
    (run_dir / "run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Spent ${summary['spent_usd']:.2f} of ${args.budget:.2f}. Results: {run_dir}")
    return summary["exit"]


if __name__ == "__main__":
    sys.exit(main())
