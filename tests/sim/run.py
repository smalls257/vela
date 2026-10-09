#!/usr/bin/env python3
"""Run a simulated solution lead through real multi-turn Claude Code sessions, once per arm, and score each run
against the lead's hidden brief. The design is docs/design-sessions/08-session-simulator.md.

This costs money: every assistant turn, persona turn and judge call is a real `claude -p` call on your account.
`--stub` swaps `claude` for the scripted fake in tests/sim/stub/, which costs nothing.

Usage:
  python3 tests/sim/run.py <persona> --model <id> --persona-model <id> --judge-model <id> --budget <usd>
                           [--arms planner,planner-seuss] [--script default] [--stub] [--out <dir>]
  python3 tests/sim/run.py --rejudge <run-dir> --judge-model <id> --budget <usd> [--stub]

--rejudge scores a finished run again from its transcript.jsonl and vault/, without replaying any session. It
rewrites each arm's scorecard.json and scorecard.md and the run's compare.html, and writes what it cost to
rejudge.json. It exits 0 when every arm was scored and 2 on a tool failure.

The judge makes one call per category: knows, wrong, unaware, conflicts, decisions, and the shape of the guidance.
Beside each verdict the scorecard sets the driver's own keyword hits for the item, and lists every disagreement
between the two under "Check these" at the top.

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
SNAPSHOTS = HERE / "snapshots"
REPO = HERE.parent.parent
PLUGIN = REPO / "plugin"
PLANNER = PLUGIN / "bin" / "planner"
SCAFFOLD = REPO / "tests" / "evals" / "scaffold.py"
RESULTS = HERE / "results"
STUB_DIR = HERE / "stub"
SEUSS = HERE / "voices" / "seuss-style"

ARMS = ("planner", "planner-seuss", "baseline")
DEFAULT_ARMS = "planner,planner-seuss"
MODES = ("dump", "close", "discover", "shape", "boundary", "grill", "epics")
# Wide enough for every planner skill: START's git and planner calls, voice-seed's heredoc, cmp and awk checks,
# close's mktemp and voicecheck. gh is allowed so its failure paths run against the stub, not a permission denial.
# Agent lets close dispatch the voice reviewer and a review checkpoint dispatch the area reviewers.
ALLOWED_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(git *)", "Bash(python3 *)", "Bash(mkdir *)",
                 "Bash(cat *)", "Bash(date *)", "Bash(shasum *)", "Bash(cmp *)", "Bash(awk *)", "Bash(sed *)",
                 "Bash(rm *)", "Bash(mktemp *)", "Bash(gh *)", "Skill", "Agent"]
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
KEYWORD_COUNT = (2, 4)  # one keyword is a single point of failure; more than four starts matching everything
# The probes (probe.py) score a capability by category, so a blind run can report "2 of 4 flagged" without naming an
# item. The set is fixed and small: a new category would make earlier probe results incomparable.
CATEGORIES = ("cross-source-mismatch", "legal-regulatory", "finance-liability", "third-party-contract",
              "unnamed-stakeholder", "data-identity", "stakeholder-conflict", "timeline", "fact")


def normalise(text):
    """Case, whitespace, quote marks and emphasis do not change what a turn says. Used for quotes and keywords alike."""
    return re.sub(r"\s+", " ", re.sub(r"[\"'“”‘’`*_]", "", str(text))).strip().lower()


def mentions(text, keywords):
    """The keywords text holds, matched from the start of a word so that "partner hotel" finds "partner hotels" and
    "dpo" does not find "endpoint"."""
    flat = normalise(text)
    return [k for k in keywords if re.search(r"(?<![a-z0-9])" + re.escape(normalise(k)), flat)]


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
            problems += keyword_problems(kind, item_id, item, data.get("opening"))
            if item.get("category") not in CATEGORIES:
                problems.append(f"{kind} {item_id}: 'category' must be one of {', '.join(CATEGORIES)}, "
                                f"not {item.get('category')!r}")
            if kind == "decisions" and not (isinstance(item.get("options"), list) and len(item["options"]) >= 2):
                problems.append(f"decisions {item_id}: 'options' must list at least two")
    for n, doc in enumerate(data.get("docs") or [], 1):
        if not isinstance(doc, dict) or not DOC_NAME.match(str(doc.get("name", ""))) or not doc.get("text"):
            problems.append(f"docs[{n}] needs a lower-case 'name' ending .md and a 'text'")
    return problems


def keyword_problems(kind, item_id, item, opening_text):
    """The keywords are the scorecard's mechanical evidence. Without them a judge's "no" has nothing to be checked
    against, so a missing list is a broken brief, never an item that is quietly left unchecked."""
    words = item.get("keywords")
    if not isinstance(words, list) or not words:
        return [f"{kind} {item_id}: 'keywords' must be a non-empty list"]
    if not all(isinstance(w, str) and normalise(w) for w in words):
        return [f"{kind} {item_id}: every keyword must be a non-empty string"]
    problems = []
    if not KEYWORD_COUNT[0] <= len(words) <= KEYWORD_COUNT[1]:
        problems.append(f"{kind} {item_id}: give {KEYWORD_COUNT[0]} to {KEYWORD_COUNT[1]} keywords, not {len(words)}")
    if len({normalise(w) for w in words}) != len(words):
        problems.append(f"{kind} {item_id}: a keyword is listed twice")
    # Every assistant turn may echo the opening, so a keyword it holds proves nothing. The one exception is a fact
    # that is itself the opening, such as the mandate, where writing it down is the capture.
    own_text = normalise(" ".join(str(item.get(f, "")) for f in ITEM_FIELDS[kind]))
    for word in words:
        if isinstance(opening_text, str) and mentions(opening_text, [word]) and not (kind == "knows" and mentions(own_text, [word])):
            problems.append(f"{kind} {item_id}: keyword {word!r} is in the opening, so every echo of it would match")
    return problems


def opening(session, arm, persona):
    """The scripted first message of a session for an arm: the skill command for planner arms, plain words for baseline."""
    template = session["baseline" if arm == "baseline" else "planner"]
    return template.format(opening=persona["opening"].strip(), topics=persona.get("topics") or {})


def with_news(persona, news):
    """The persona as it stands once a script's news has arrived: facts the lead now knows, appended as K items,
    documents now in the inbox, and changes to how the lead takes a decision (an override they would now give). The persona file is untouched, so a run from the start never sees them."""
    if not news:
        return persona
    out = dict(persona)
    out["knows"] = list(persona["knows"]) + list(news.get("knows") or [])
    out["docs"] = list(persona.get("docs") or []) + list(news.get("docs") or [])
    changes = {d["id"]: d for d in news.get("decisions") or []}
    out["decisions"] = [{**d, **changes.get(d["id"], {})} for d in persona.get("decisions") or []]
    return out


def news_problems(news):
    if news is None:
        return []
    if not isinstance(news, dict) or set(news) - {"knows", "docs", "decisions"}:
        return ["'news' must be a mapping with only 'knows', 'docs' and 'decisions'"]
    problems = []
    for change in news.get("decisions") or []:
        if not (isinstance(change, dict) and str(change.get("id", "")).startswith("D")
                and set(change) - {"id"} <= {"override_if_blocked", "refuse_until"}):
            problems.append(f"news decisions item {change!r} needs an id D.. and only override_if_blocked or refuse_until")
    for item in news.get("knows") or []:
        if not (isinstance(item, dict) and str(item.get("id", "")).startswith("K") and item.get("fact")):
            problems.append(f"news knows item {item!r} needs an id K.. and a fact")
    for doc in news.get("docs") or []:
        if not (isinstance(doc, dict) and doc.get("name") and doc.get("text")):
            problems.append(f"news doc {doc!r} needs a name and a text")
    return problems


def script_problems(data, persona):
    if not isinstance(data, dict) or not isinstance(data.get("sessions"), list) or not data["sessions"]:
        return ["the script must be a mapping with a non-empty 'sessions' list"]
    problems = news_problems(data.get("news"))
    events = data.get("events")
    if events is not None:
        if not isinstance(events, list):
            problems.append("'events' must be a list, each with 'after: <session number>' and its news")
        else:
            afters = []
            for event in events:
                if not isinstance(event, dict) or not isinstance(event.get("after"), int) \
                        or not 1 <= event["after"] < len(data["sessions"]):
                    problems.append(f"event {event!r} needs 'after', a session number before the last session")
                    continue
                afters.append(event["after"])
                problems += news_problems({k: v for k, v in event.items() if k != "after"})
            if len(afters) != len(set(afters)):
                problems.append("two events have the same 'after'; put their news in one event")
    if data.get("start") is not None and not (SNAPSHOTS / str(data["start"])).is_dir():
        problems.append(f"'start' {data['start']!r} is not a folder in {SNAPSHOTS}")
    if any(problems):
        return problems
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
    written_for = script.get("persona") if isinstance(script, dict) else None
    if written_for and written_for != persona_path.stem:
        raise ToolFailure(f"{script_path.name} is written for the persona {written_for}, not {persona_path.stem}")
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

def isolation_flags(origin=None, thinking=False):
    """Every call loads only the vault's own settings and CLAUDE.md. The user's plugins, hooks and global CLAUDE.md
    would otherwise steer every arm alike and hide the difference the run exists to show.

    An assistant call also runs in Claude Code's sandbox with sandboxed Bash auto-allowed: nobody is there to answer
    a permission prompt, so an unsandboxed allowlist denies START's first compound write and the skills never get
    to work. The sandbox confines writes to the vault, plus the arm's scratch origin so that `git push` works."""
    home_claude = pathlib.Path.home() / ".claude"
    settings = {"claudeMdExcludes": [str(home_claude / "CLAUDE.md"), str(home_claude / "**" / "*.md")]}
    if thinking:
        settings["alwaysThinkingEnabled"] = True
    if origin is not None:
        # Auto-allow alone still denies compound commands (variables, heredocs, loops), which START uses. So all
        # Bash is allowed, and no command may leave the sandbox: writes stay in the vault and the origin.
        settings["sandbox"] = {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False}
        settings["permissions"] = {"allow": ["Bash", f"Edit(/{pathlib.Path(origin).resolve()}/**)"]}
    return ["--setting-sources", "project,local", "--strict-mcp-config", "--settings", json.dumps(settings)]


def assistant_argv(message, model, session_id, budget, arm, origin=None):
    argv = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--model", model,
            "--permission-mode", "acceptEdits", "--permission-prompts", "none",
            "--allowedTools", ",".join(ALLOWED_TOOLS), "--max-budget-usd", f"{budget:.4f}", *isolation_flags(origin)]
    if arm != "baseline":
        argv += ["--plugin-dir", str(PLUGIN)]
    if session_id:
        argv += ["--resume", session_id]
    # "--" ends the options, so a message that starts with "-" is still the prompt, and a slash command stays a
    # prompt argument rather than stdin text.
    return argv + ["--", message]


JUDGE_EFFORT = "high"


def text_call_argv(model, system_prompt, budget, thinking=False):
    """A persona or judge call: no tools, no skills, no saved session. The input goes on stdin.

    A judge call thinks first. The judge that answered 35 of 37 items "no" over a vault that named most of them
    replied with 0 thinking tokens, so judge calls ask for thinking twice over: --effort and alwaysThinkingEnabled.
    The thinking tokens each call reports go on the scorecard, so a judge that still did not think is visible."""
    effort = ["--effort", JUDGE_EFFORT] if thinking else []
    return ["claude", "-p", "--output-format", "json", "--model", model, "--system-prompt", system_prompt,
            "--no-session-persistence", "--disable-slash-commands", "--max-budget-usd", f"{budget:.4f}", *effort,
            *isolation_flags(thinking=thinking), "--tools", ""]


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

    def __init__(self, path, entries=None):
        """A new transcript starts an empty file. Pass entries only through load(), which never writes."""
        self.path = path
        self.entries = entries or []
        self.turn = max([e["turn"] for e in self.entries if "turn" in e] or [0])
        if entries is None:
            path.write_text("", encoding="utf-8")

    @classmethod
    def load(cls, path):
        """An existing run's transcript, read and never rewritten. A transcript with no spoken turn has nothing to
        score, so it is refused rather than scored as a run where nothing happened."""
        if not path.is_file():
            raise ToolFailure(f"{path} does not exist")
        entries = []
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ToolFailure(f"{path} line {n} is not JSON: {exc}") from exc
            if not isinstance(entry, dict) or "speaker" not in entry or "text" not in entry:
                raise ToolFailure(f"{path} line {n} is not a transcript entry")
            entries.append(entry)
        transcript = cls(path, entries)
        if not transcript.spoken():
            raise ToolFailure(f"{path} holds no spoken turns, so there is nothing to judge")
        return transcript

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
9. When the assistant says the session is over, or tells you to run a command, reply with exactly {end} and
   nothing else. You cannot run commands; the next session is how a command runs.
10. Say a worry once. Do not repeat a worry, a deadline or a blocker you have already said in this session unless
   the assistant asks about it. Answer what the assistant asked, then let it move on.
11. You can do nothing outside this chat. Never say you ran a command or a skill, sent or received a message, made
   a call or got a reply, unless one of your facts says it happened. Never report what someone said back, such as
   "Back from the CEO, they said...": if asked what someone thinks and no fact says, say you have not heard yet.
   You may say once what you will do later.
12. The IDs in this brief (K1, W2, C3, D4 and the like) are your private notes. Never say them, and never call a
   belief or a decision by its ID: say it in your own words.

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
                        + (f" Refuse until: {i['refuse_until']}" if i.get("refuse_until") else "")
                        + (f" If a gate blocks this decision, override it once: tell the assistant to decide it anyway"
                           f" on the owner's behalf, name the gate it said failed, and give this reason: "
                           f"{i['override_if_blocked']}" if i.get("override_if_blocked") else "")))
    # The U items are left out on purpose: a persona cannot leak a gap it was never told.


def persona_input(transcript, session_index, mode):
    """This session in full, and from each earlier session only the lead's last two messages, each cut to 300
    characters, so the lead stays consistent with where it left off. Every earlier assistant turn passed 200k
    tokens by session 21 of a long run, and every earlier lead message made the lead repeat its own worries."""
    spoken = transcript.spoken()
    current = [e for e in spoken if e.get("session") == session_index]
    earlier = []
    for session in sorted({e.get("session") for e in spoken if e.get("session") != session_index},
                          key=lambda s: (s is None, s if isinstance(s, int) else 0, str(s))):
        said = [e for e in spoken if e.get("session") == session and e["speaker"] == "lead"][-2:]
        earlier += [{**e, "text": e["text"] if len(e["text"]) <= 300 else e["text"][:300] + " [...]"} for e in said]
    latest = next((e["text"] for e in reversed(spoken) if e["speaker"] == "assistant"), "")
    return (f"Where you left each earlier session, in your own words:\n\n{as_chat(earlier) or 'nothing yet'}\n\n"
            f"This session so far:\n\n{as_chat(current) or 'nothing yet'}\n\n"
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



def build_vault_from(arm_dir, start, persona):
    """A script with 'start: <snapshot>' begins from that saved vault, with the current plugin installed over it,
    so a long run can pick up where an earlier one stopped. Its .inbox must hold the persona's docs."""
    snapshot = SNAPSHOTS / start
    if not snapshot.is_dir():
        raise ToolFailure(f"the script's start {start!r} is not a folder in {SNAPSHOTS}")
    vault, origin = arm_dir / "vault", arm_dir / "origin.git"
    shutil.copytree(snapshot, vault, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    skills = vault / ".claude" / "skills"
    if skills.exists():
        shutil.rmtree(skills)
    shutil.copytree(PLUGIN, skills / "planner", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    inbox = vault / ".inbox"
    # As planner upgrade would: a snapshot saved before the format changed starts with the plugin's own copy.
    shutil.copyfile(PLUGIN / "vault" / "CONVENTIONS.md", vault / "CONVENTIONS.md")
    for doc in persona.get("docs") or []:
        inbox.mkdir(exist_ok=True)
        (inbox / doc["name"]).write_text(doc["text"].strip() + "\n", encoding="utf-8")
    git("init", "-q", "-b", "main", cwd=vault)
    git("add", "-A", cwd=vault)
    git("commit", "-q", "-m", f"Vault from snapshot {start}", cwd=vault)
    git("config", "user.name", "Sim Lead", cwd=vault)
    git("config", "user.email", "sim-lead@example.invalid", cwd=vault)
    git("init", "-q", "--bare", "-b", "main", str(origin), cwd=arm_dir)
    git("remote", "add", "origin", str(origin), cwd=vault)
    git("push", "-q", "-u", "origin", "main", cwd=vault)
    return vault, [f"vault copied from snapshot {start}, current plugin installed"]


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


CONFLICT_HUNK = re.compile(r"<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n", re.S)


STATE_LINE = re.compile(r"^\s*(state:|- \*\*State:\*\*)", re.I)


def union_hunk(match, lost):
    """How a reviewer settles a clash between two session PRs: main's generated blocks (render rebuilds those), main's
    state lines, and every other line from both sides, main's first. Each state line of the session's that is not
    kept goes in `lost`, so the merge report says what the session's PR gave up."""
    ours, theirs = match.group(1), match.group(2)
    if "<!-- generated:" in ours or "<!-- generated:" in theirs:
        return ours
    seen = set(ours.splitlines())
    ours_states = [line for line in ours.splitlines() if STATE_LINE.match(line)]
    extra = []
    for line in theirs.splitlines():
        if line in seen:
            continue
        if STATE_LINE.match(line) and ours_states:
            lost.append(line.strip())
            continue
        extra.append(line)
    return ours + ("\n".join(extra) + "\n" if extra else "")


def check_errors(clone):
    """(error count, first line) of planner check in the clone; the count is None when check itself failed."""
    planner = clone / ".claude" / "skills" / "planner" / "bin" / "planner"
    done = subprocess.run([sys.executable, str(planner), "check"], cwd=clone, capture_output=True, text=True)
    first = (done.stdout.splitlines() or [done.stderr.strip() or "no output"])[0]
    found = re.search(r"(\d+) errors", first) if done.returncode in (0, 1) else None
    return (int(found.group(1)) if found else None), first


def resolve_conflicts(clone, files, errors_before, lost):
    """Settle each conflicted file by union_hunk, rebuild the generated blocks, and keep the merge only if the vault
    has no more check errors than main had. Returns "" when it is committed, or why it was not."""
    if errors_before is None:
        return "planner check failed on main before the merge, so a union could not be judged"
    for rel in files:
        path = clone / rel
        text = CONFLICT_HUNK.sub(lambda m: union_hunk(m, lost), path.read_text(encoding="utf-8"))
        if any(mark in text for mark in ("<<<<<<<", ">>>>>>>", "|||||||")):
            return f"{rel} still holds conflict markers after the union"
        path.write_text(text, encoding="utf-8")
    planner = [sys.executable, str(clone / ".claude" / "skills" / "planner" / "bin" / "planner")]
    render = subprocess.run(planner + ["render", "--discard-edits"], cwd=clone, capture_output=True, text=True)
    if render.returncode != 0:
        return f"planner render failed after the union: {(render.stdout + render.stderr).strip()[:200]}"
    errors, first = check_errors(clone)
    if errors is None or errors > errors_before:
        return f"the union adds check errors, {errors_before} on main before: {first}"
    git("add", "-A", cwd=clone)
    git("commit", "-q", "--no-edit", cwd=clone)
    return ""


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
        errors_before = check_errors(clone)[0]
        merged = git("-c", "merge.conflictStyle=merge", "merge", "--no-ff", "-q", "-m", f"Merge {branch} (simulated PR merge)", f"refs/sim/{branch}",
                     cwd=clone, check=False)
        if merged.returncode != 0:
            files = git("diff", "--name-only", "--diff-filter=U", cwd=clone).stdout.split()
            lost = []
            problem = resolve_conflicts(clone, files, errors_before, lost) if files else "the merge failed with no conflicted file"
            if problem:
                git("merge", "--abort", cwd=clone, check=False)
                reports.append(f"not merged: {branch} conflicts with main, and the union did not settle it: {problem}")
                continue
            git("push", "-q", "origin", "main", cwd=clone)
            reports.append(f"merged {branch} into main on origin after settling conflicts in {', '.join(files)} as a "
                           "reviewer would: main's state lines, both sides' other lines, generated blocks rebuilt"
                           + (f"; the session's state lines not kept: {'; '.join(lost)}" if lost else ""))
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
        self.prior_spent = 0.0  # what an earlier run spent, when this arm is only being judged again
        self.judge_calls = []
        write_gh_stub(self.dir / "bin")
        self.env = arm_env(self.dir, args.stub)
        (self.dir / "persona-cwd").mkdir()
        self.transcript = Transcript(self.dir / "transcript.jsonl")
        self.session_costs = {}

    @classmethod
    def reopen(cls, name, run_dir, args, persona, share, record):
        """An arm of a finished run, for --rejudge. It reads the transcript and the vault and writes nothing but new
        raw judge files, numbered after the run's own so none is overwritten."""
        arm = cls.__new__(cls)
        arm.name, arm.args, arm.persona = name, args, persona
        arm.dir = run_dir / name
        arm.vault = arm.dir / "vault"
        if not arm.vault.is_dir():
            raise ToolFailure(f"{arm.vault} does not exist, so there is no final vault to judge")
        arm.ledger = Ledger(share)
        arm.calls = len(list((arm.dir / "raw").glob("*.txt")))
        arm.endings = record.get("endings") or []
        arm.notes, arm.failure, arm.scorecard, arm.judge_calls = [], None, None, []
        arm.prior_spent = float(record.get("spent_usd") or 0)
        arm.env = arm_env(arm.dir, args.stub)
        (arm.dir / "persona-cwd").mkdir(exist_ok=True)
        arm.transcript = Transcript.load(arm.dir / "transcript.jsonl")
        return arm

    def raw(self, kind):
        self.calls += 1
        return self.dir / "raw" / f"{self.calls:03d}-{kind}.txt"

    def log(self, message):
        print(f"[{self.name}] {message} (spent ${self.ledger.spent:.2f} of ${self.ledger.share:.2f})", file=sys.stderr)

    def assistant_turn(self, message, session_id):
        # A resumed session reports total_cost_usd as its running total, so only the increase is new spend, and
        # --max-budget-usd caps that running total: allow what was already spent in the session plus the room left.
        before = self.session_costs.get(session_id, 0.0) if session_id else 0.0
        room = self.ledger.session_room()
        raw = self.raw("assistant")
        done = call(assistant_argv(message, self.args.model, session_id, room + before, self.name, self.dir / "origin.git"),
                    env=self.env, cwd=self.vault, raw_path=raw, kind="assistant")
        parsed = parse_stream(done.stdout, raw)
        result = parsed["result"]
        total = float(result["total_cost_usd"])
        if total < before:
            raise ToolFailure(f"session {session_id} reported a running cost of {total} after {before}; its cost cannot fall. Read {raw}")
        self.session_costs[result["session_id"]] = total
        self.ledger.add(total - before)
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
        self.persona = with_news(self.persona, script.get("news"))
        if script.get("start"):
            self.vault, self.notes = build_vault_from(self.dir, script["start"], self.persona)
        else:
            self.vault, self.notes = build_vault(self.dir, self.name, self.persona)
        for note in self.notes:
            self.transcript.add(speaker="driver", session=0, mode="setup", event="setup", text=note)
        events = {e["after"]: e for e in script.get("events") or []}
        inbox = self.dir / "news-inbox"
        (inbox / "applied").mkdir(parents=True, exist_ok=True)
        for index, session in enumerate(script["sessions"], 1):
            if index - 1 in events:
                self.arrive(index, session["mode"], events[index - 1])
            self.arrive_live(index, session["mode"], inbox)
            if self.ledger.session_room() < MIN_CALL_USD:
                self.endings.append({"session": index, "mode": session["mode"], "reason": "not run: budget", "turns": 0})
                self.transcript.add(speaker="driver", session=index, mode=session["mode"], event="session-skipped",
                                    text=f"Session {index} ({session['mode']}) not run: the session budget is spent")
                continue
            self.run_session(index, session)

    def arrive(self, index, mode, event):
        """News that reaches the lead between sessions: facts they now know, documents now in the inbox, and how
        they now take a decision. What a lead would hear back while the work goes on, not before it starts."""
        news = {k: v for k, v in event.items() if k != "after"}
        self.persona = with_news(self.persona, news)
        inbox = self.vault / ".inbox"
        for doc in news.get("docs") or []:
            inbox.mkdir(exist_ok=True)
            (inbox / doc["name"]).write_text(doc["text"].strip() + "\n", encoding="utf-8")
        said = [f"facts {', '.join(k['id'] for k in news.get('knows') or [])}" if news.get("knows") else "",
                f"documents {', '.join(d['name'] for d in news.get('docs') or [])}" if news.get("docs") else "",
                f"decision changes {', '.join(d['id'] for d in news.get('decisions') or [])}" if news.get("decisions") else ""]
        self.transcript.add(speaker="driver", session=index, mode=mode, event="news",
                            text=f"News arrives after session {event['after']}: " + "; ".join(s for s in said if s))

    def arrive_live(self, index, mode, inbox):
        """News dropped into the arm's news-inbox while the run goes on: each *.yaml there, in name order, holds
        the same keys as a script's news. It reaches the lead before the next session and moves to applied/, so
        a person watching can answer what a lead would get back in the world. A file that is not valid news is
        refused loudly and left where it is, never half applied."""
        for path in sorted(inbox.glob("*.yaml")):
            try:
                news = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raise ToolFailure(f"{path} is not YAML: {exc}") from exc
            problems = news_problems(news)
            if problems:
                raise ToolFailure(f"{path} is not valid news: " + "; ".join(problems))
            self.arrive(index, mode, {"after": index - 1, **news})
            path.rename(inbox / "applied" / path.name)

    def early(self):
        return any(e["reason"] != "persona-end" for e in self.endings)


# ------------------------------------------------------------------ mechanical evidence

SCORE_LISTS = {"unaware": "surfaced", "wrong": "challenged", "knows": "captured", "decisions": "decided",
               "conflicts": "surfaced"}
LEAD_FIRST_KINDS = ("wrong", "unaware")  # a gap or a correction the lead raised first is not one the assistant found
TEMPLATE = REPO / "template"


def vault_pages(vault):
    """The final vault's own pages: what a lead would read. Tooling, voice examples, the conventions and the inbox
    are left out. The inbox holds the lead's source documents, so finding a fact there is not a capture."""
    skip = {"CONVENTIONS.md", "CLAUDE.md", "README.md"}
    pages = []
    for path in sorted(vault.rglob("*.md")):
        rel = path.relative_to(vault)
        if rel.parts[0] in (".git", ".claude", ".github", ".obsidian", ".inbox", "voice") or rel.as_posix() in skip:
            continue
        pages.append((rel.as_posix(), path.read_text(encoding="utf-8", errors="replace")))
    return pages


def boilerplate(rel):
    """The template's own text for a page, so a keyword the template already held is not counted as a capture."""
    path = TEMPLATE / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def keyword_hits(persona, spoken, pages):
    """Per brief item: which assistant turns and which final vault pages hold one of its keywords, and for W and U
    items which lead turns do. A pure function over the transcript and the pages, so it is tested without a vault.

    pages is a list of (path, text, boilerplate); a keyword the boilerplate holds does not count for that page."""
    hits = {}
    for kind in ID_KINDS:
        for item in persona.get(kind) or []:
            words = item["keywords"]
            hit = {"kind": kind, "keywords": words, "assistant_turns": [], "vault_files": []}
            if kind in LEAD_FIRST_KINDS:
                hit["lead_turns"] = []
            for e in spoken:
                found = mentions(e["text"], words)
                if found and e["speaker"] == "assistant":
                    hit["assistant_turns"].append({"turn": e["turn"], "keywords": found})
                elif found and kind in LEAD_FIRST_KINDS:
                    hit["lead_turns"].append({"turn": e["turn"], "keywords": found})
            for rel, text, template_text in pages:
                found = [k for k in mentions(text, words) if not mentions(template_text, [k])]
                if found:
                    hit["vault_files"].append({"file": rel, "keywords": found})
            hits[item["id"]] = hit
    return hits


def vault_hits(persona, transcript, vault):
    pages = [(rel, text, boilerplate(rel)) for rel, text in vault_pages(vault)]
    return keyword_hits(persona, transcript.spoken(), pages)


def first_turn(rows):
    return min((r["turn"] for r in rows), default=None)


def where_said(rows, place, limit=3):
    """'FERRYMASTER in 01-goals.md, Tidemiles in 11-unknowns-and-risks.md', or the same for turns."""
    parts = [f"{' and '.join(r['keywords'])} in {r[place] if place == 'file' else 'T' + str(r['turn'])}"
             for r in rows[:limit]]
    more = f" and {len(rows) - limit} more" if len(rows) > limit else ""
    return ", ".join(parts) + more


def hits_summary(hit):
    """One line for a scorecard cell: every turn and file that holds a keyword."""
    parts = []
    if hit["assistant_turns"]:
        parts.append("assistant " + ", ".join(f"T{r['turn']}" for r in hit["assistant_turns"]))
    if hit.get("lead_turns"):
        parts.append("lead " + ", ".join(f"T{r['turn']}" for r in hit["lead_turns"]))
    if hit["vault_files"]:
        parts.append("vault " + ", ".join(r["file"] for r in hit["vault_files"]))
    return "; ".join(parts) or "none"


def disagreements(card, hits):
    """Every item where the judge's verdict and the keyword hits point different ways. Neither is proof, so each one
    is listed for a person to read, at the top of the scorecard."""
    out = []
    for kind, flag in SCORE_LISTS.items():
        for row in card[kind]:
            hit, said = hits[row["id"]], row[flag]
            verdict = f"judge: {yes_no(said)}" + (f" (its claim was dropped: {row['dropped']})" if row.get("dropped") else "")
            for problem in disagreement(kind, row, hit, said):
                out.append(f"{row['id']}: {verdict}; {problem}")
    return out


def disagreement(kind, row, hit, said):
    """What the hits say against the verdict, if anything. K items live in the vault; D items in the vault or the
    transcript; W, U and C items in what the assistant said, and W and U only if the lead did not say it first."""
    vault, turns = hit["vault_files"], hit["assistant_turns"]
    if kind == "knows":
        if not said and vault:
            return [f"vault mentions {where_said(vault, 'file')}"]
        if said and not vault:
            return [f"no vault page holds any of its keywords ({', '.join(hit['keywords'])})"]
        return []
    if kind == "decisions":
        if not said and (vault or turns):
            return ["; ".join(p for p in (turns and f"assistant mentions {where_said(turns, 'turn')}",
                                          vault and f"vault mentions {where_said(vault, 'file')}") if p)]
        if said and not (vault or turns):
            return [f"no turn or vault page holds any of its keywords ({', '.join(hit['keywords'])})"]
        return []
    lead_first = first_turn(hit.get("lead_turns") or [])
    assistant_first = first_turn(turns)
    lead_raised = lead_first is not None and (assistant_first is None or lead_first < assistant_first)
    if not said and turns and not lead_raised:
        return [f"assistant mentions {where_said(turns, 'turn')}"]
    if said and not turns:
        return [f"no assistant turn holds any of its keywords ({', '.join(hit['keywords'])})"]
    cited_turn = row.get("turn") if isinstance(row.get("turn"), int) else None
    if said and lead_raised and cited_turn is not None and lead_first < cited_turn:
        return [f"the lead said {where_said(hit['lead_turns'], 'turn', 1)} before the cited T{cited_turn}, "
                "so the assistant may not have raised it first"]
    return []


# ------------------------------------------------------------------ judge

JUDGE_CATEGORIES = ("knows", "wrong", "unaware", "conflicts", "decisions", "shape")

JUDGE_COMMON = """SIMULATOR JUDGE: {category}. You score one part of a simulated planning run against the lead's hidden
brief. You are mechanical, not a critic. You have no tools. Reply with one JSON object and nothing else: no prose,
no fences.

Work through the items one at a time. For every item write "search" first: one or two sentences on what you
looked for, where you looked (which turns, which files) and what you found there. Only then give the verdict. A
row whose "search" is missing, empty or written after the verdict is rejected.

Every "yes" needs evidence: the turn number T<n> where it happened and a quote copied exactly from that turn, at
most 25 words. A claim without a turn and an exact quote is dropped by the driver and counts as no. A "where" must
be a file path in the final vault exactly as listed after FILE. If, after looking, you are unsure, answer no.

HINTS. For each item the driver lists the turns and files that hold one of its keywords. Check every one of them
before you answer. A hint is not proof: a keyword can sit in a question, in the lead's own words, in an idea the
assistant parked, or in a heading, and none of those is a capture, a challenge or a surfaced gap. A missing hint is
not proof either: the text may say it in other words. Decide from what the text says.

{rules}

The JSON shape, with every ID listed exactly once:
{shape}
"""

JUDGE_RULES = {
    "knows": ("- knows K*: captured is true when the fact is written somewhere in the final vault. \"where\" is the "
              "file path. The inbox documents are the lead's sources, not the vault, so a fact found only there is "
              "not captured.",
              '{"knows": [{"id": "K1", "search": "...", "captured": true, "where": "01-goals.md"}]}'),
    "wrong": ("- wrong W*: challenged is true when the ASSISTANT questioned the belief or gave a reason or source "
              "against it. Quote the assistant. Repeating the belief, or the lead correcting it unprompted, is not a "
              "challenge.",
              '{"wrong": [{"id": "W1", "search": "...", "challenged": false, "turn": null, "quote": null}]}'),
    "unaware": ("- unaware U*: surfaced is true when the ASSISTANT raised the gap, or asked a question that names it, "
                "before the lead did. Quote the assistant. If the lead turns in the hints raised it first, it was "
                "not surfaced.",
                '{"unaware": [{"id": "U1", "search": "...", "surfaced": true, "turn": 12, "quote": "..."}]}'),
    "conflicts": ("- conflicts C*: surfaced is true when the ASSISTANT named the disagreement between stakeholders as "
                  "something to resolve, rather than picking a side. Naming one stakeholder's wish is not enough. "
                  "Quote the assistant.",
                  '{"conflicts": [{"id": "C1", "search": "...", "surfaced": false, "turn": null, "quote": null}]}'),
    "decisions": ("- decisions D*: decided is true when the vault or transcript records it as decided. yes_asked is "
                  "true when the assistant asked the lead for an explicit yes before recording it. Quote the decision "
                  "turn. A question, an option or a parked idea is not a decision.",
                  '{"decisions": [{"id": "D1", "search": "...", "decided": false, "yes_asked": false, "turn": null, '
                  '"quote": null}]}'),
    "shape": ("The shape of the guidance. Write one \"search\" note first, on what you read for. Then:\n"
              "- decided_without_yes: every item the assistant wrote as decided without the lead's explicit yes.\n"
              "- told_not_asked: assistant turns that told the lead what the answer is instead of asking.\n"
              "- session_endings: for each session number, whether it ended with a clear next step. Quote the step.\n"
              "- invented_facts: assistant statements of fact the brief, the documents and the lead never gave. "
              "Quote them.",
              '{\n  "search": "...",\n  "decided_without_yes": [{"item": "...", "turn": 30, "quote": "..."}],\n'
              '  "told_not_asked": [{"turn": 7, "quote": "..."}],\n'
              '  "session_endings": [{"session": 1, "clear_next_step": true, "turn": 9, "quote": "..."}],\n'
              '  "invented_facts": [{"turn": 15, "quote": "..."}]\n}'),
}
SHAPE_LISTS = ("decided_without_yes", "told_not_asked", "session_endings", "invented_facts")
# What each call reads besides the transcript. K and D items are found in the vault; W items and invented facts
# are weighed against the documents. Leaving the rest out keeps every call small enough to read item by item.
JUDGE_READS = {"knows": ("vault",), "wrong": ("inbox",), "unaware": (), "conflicts": (), "decisions": ("vault",),
               "shape": ("inbox", "whole brief")}


def judge_system_prompt(category):
    rules, shape = JUDGE_RULES[category]
    return JUDGE_COMMON.format(category=category, rules=rules, shape=shape)


def hint_lines(persona, category, hits):
    """The hints for one category. Vault files are named only where the judge reads the vault."""
    lines = []
    for item in persona.get(category) or []:
        hit = hits[item["id"]]
        parts = [f"assistant turns {', '.join('T' + str(r['turn']) for r in hit['assistant_turns'])}"
                 if hit["assistant_turns"] else "no assistant turn"]
        if "lead_turns" in hit:
            parts.append(f"lead turns {', '.join('T' + str(r['turn']) for r in hit['lead_turns'])} (the lead's own words)"
                         if hit["lead_turns"] else "no lead turn")
        if "vault" in JUDGE_READS[category]:
            parts.append(f"vault files {', '.join(r['file'] for r in hit['vault_files'])}"
                         if hit["vault_files"] else "no vault file")
        lines.append(f"- {item['id']} (keywords: {', '.join(hit['keywords'])}): " + "; ".join(parts))
    return "\n".join(lines)


def compact_chat(entries, limit=800):
    """The transcript with each turn cut to `limit` characters, for a judge call to retry after a refusal."""
    return as_chat([{**e, "text": e["text"] if len(e["text"]) <= limit else e["text"][:limit] + " [...]"}
                    for e in entries])


def judge_input(persona, transcript, vault, category, hits, compact=False):
    """One call's input: its own brief items and their hints, the transcript, and only what the category needs.
    `compact` cuts each turn short: the retry after the judge model's safeguards refused the full input."""
    reads = JUDGE_READS[category]
    strip = lambda items: [{k: v for k, v in i.items() if k != "keywords"} for i in items or []]
    kinds = list(ID_KINDS) if "whole brief" in reads else [category]
    brief = {kind: strip(persona.get(kind)) for kind in kinds}
    sessions = sorted({e["session"] for e in transcript.spoken()})
    parts = [f"THE HIDDEN BRIEF (YAML):\n{yaml.safe_dump(brief, sort_keys=False, allow_unicode=True)}"]
    if category in ID_KINDS:
        parts.append(f"IDS {category}: {', '.join(i['id'] for i in persona.get(category) or [])}")
        parts.append(f"HINTS, which turns and files hold each item's keywords:\n{hint_lines(persona, category, hits)}")
    parts.append(f"SESSIONS THAT RAN: {', '.join(map(str, sessions))}")
    if "inbox" in reads:
        docs = "\n\n".join(f"----- INBOX {d['name']} -----\n{d['text']}" for d in persona.get("docs") or [])
        parts.append(f"INBOX DOCUMENTS:\n{docs or 'none'}")
    parts.append(f"THE TRANSCRIPT:\n{compact_chat(transcript.spoken()) if compact else as_chat(transcript.spoken())}")
    if "vault" in reads:
        pages = "\n\n".join(f"----- FILE {name} -----\n{text}" for name, text in vault_pages(vault))
        parts.append(f"THE FINAL VAULT:\n{pages}")
    return "\n\n".join(parts) + "\n"


def strip_fences(text):
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    return fenced.group(1) if fenced else text


def search_problem(row, label, flag):
    """The search note must exist and come before the verdict, so the judge writes what it looked at first.
    JSON objects keep their key order in Python, so the order the judge wrote is the order checked here."""
    note = row.get("search")
    if not isinstance(note, str) or not note.strip():
        return f"{label}: 'search' must say what you looked for and where"
    keys = list(row)
    if flag in keys and keys.index("search") > keys.index(flag):
        return f"{label}: write 'search' before '{flag}'"
    return None


def category_problems(data, persona, category):
    """Shape errors only. Citations are checked afterwards, and a bad one drops the claim instead of failing."""
    if not isinstance(data, dict):
        return ["the reply is not a JSON object"]
    if category == "shape":
        problems = [p for p in [search_problem(data, "the reply", SHAPE_LISTS[0])] if p]
        for key in SHAPE_LISTS:
            if not isinstance(data.get(key), list) or not all(isinstance(r, dict) for r in data[key]):
                problems.append(f"'{key}' must be a list of objects")
        return problems
    flag = SCORE_LISTS[category]
    rows = data.get(category)
    want = [i["id"] for i in persona.get(category) or []]
    if not isinstance(rows, list):
        return [f"'{category}' must be a list"]
    problems = []
    got = [r.get("id") for r in rows if isinstance(r, dict)]
    if sorted(got) != sorted(want) or len(got) != len(rows):
        problems.append(f"'{category}' must list exactly {', '.join(want) or 'nothing'}, once each; got {got}")
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = f"{category} {row.get('id')}"
        problem = search_problem(row, label, flag)
        if problem:
            problems.append(problem)
        if not isinstance(row.get(flag), bool):
            problems.append(f"{label}: '{flag}' must be true or false")
        if category == "decisions" and not isinstance(row.get("yes_asked"), bool):
            problems.append(f"{label}: 'yes_asked' must be true or false")
    return problems


def turn_number(value):
    """A cited turn as a number: 193, or "T193" and "193" as the judge sometimes writes them. None otherwise."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    found = re.fullmatch(r"\s*T?(\d+)\s*", str(value)) if isinstance(value, str) else None
    return int(found.group(1)) if found else None


def cited(row, turns):
    """True when row cites a turn that exists and quotes it exactly, give or take whitespace, quotes and emphasis.
    A turn written "T193" counts: the trading run's judge wrote every turn that way, and all its claims were dropped."""
    turn, quote = turn_number(row.get("turn")), row.get("quote")
    if turn is None or turn not in turns:
        return False
    if isinstance(quote, str) and bool(normalise(quote)) and normalise(quote) in normalise(turns[turn]):
        row["turn"] = turn
        return True
    return False


def enforce_citations(data, transcript, vault):
    """Every claim needs a quoted turn number, or it is dropped. Drops are listed, never hidden."""
    turns = {e["turn"]: e["text"] for e in transcript.spoken()}
    pages = {rel for rel, _ in vault_pages(vault)}
    dropped = []
    for kind, flag in SCORE_LISTS.items():
        for row in data[kind]:
            if not row[flag]:
                continue
            if kind == "knows":
                where = str(row.get("where") or "")
                ok = where in pages
                why = f"'where' {where!r} is not a page of the final vault"
            else:
                ok, why = cited(row, turns), f"turn {row.get('turn')!r} does not hold the quote {short(row.get('quote'), 80)!r}"
            if not ok:
                row[flag] = False
                row["dropped"] = why
                dropped.append(f"{row['id']}: {why}")
    for key in SHAPE_LISTS:
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


def thinking_tokens(result):
    """What the call reports it spent thinking, or None when the CLI does not say."""
    details = (result.get("usage") or {}).get("output_tokens_details") or {}
    value = details.get("thinking_tokens")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def judge_category(arm, category, hits):
    """One judge call for one category. Re-ask once on bad JSON with the problems named, then give up with exit 2.
    A refusal by the judge model's safeguards is retried once with each turn cut short; a second refusal returns
    None and the reason, so the category reads "not scored" on the scorecard and the other categories still count."""
    stdin = judge_input(arm.persona, arm.transcript, arm.vault, category, hits)
    problems, refused, bad = [], False, 0
    for attempt in (1, 2, 3):
        room = arm.ledger.judge_room()
        if room < MIN_CALL_USD:
            raise ToolFailure(f"no budget left for the {category} judge call")
        raw = arm.raw(f"judge-{category}")
        prompt = stdin if not problems else (stdin + "\n\nYOUR LAST REPLY WAS REJECTED:\n- " + "\n- ".join(problems)
                                             + "\nReply again with the JSON object only.")
        done = call(text_call_argv(arm.args.judge_model, judge_system_prompt(category), room, thinking=True),
                    env=arm.env, cwd=arm.dir / "persona-cwd", raw_path=raw, kind="judge", stdin=prompt)
        result = parse_single(done.stdout, raw)
        arm.ledger.add(float(result["total_cost_usd"]))
        arm.judge_calls.append({"category": category, "attempt": attempt, "raw": raw.name,
                                "cost_usd": result["total_cost_usd"], "thinking_tokens": thinking_tokens(result)})
        if result.get("stop_reason") == "refusal":
            if refused:
                return None, f"the judge model refused twice, the second time with each turn cut to 800 characters. Read {raw}"
            refused, problems = True, []
            stdin = judge_input(arm.persona, arm.transcript, arm.vault, category, hits, compact=True)
            continue
        if result["is_error"]:
            raise ToolFailure(f"the {category} judge call reported an error ({result.get('subtype')}). Read {raw}")
        try:
            data = json.loads(strip_fences(result["result"]))
        except json.JSONDecodeError as exc:
            problems = [f"the reply is not JSON: {exc}"]
        else:
            problems = category_problems(data, arm.persona, category)
            if not problems:
                return data, ""
        bad += 1
        if bad == 2:
            break
    raise ToolFailure(f"the {category} judge's JSON was bad twice: " + "; ".join(problems))


def judge(arm, hits):
    """One call per category, so each call is small enough for the judge to look at every item in it."""
    arm.judge_calls = []
    data = {"not_scored": {}}
    for category in JUDGE_CATEGORIES:
        reply, why = judge_category(arm, category, hits)
        if reply is None:
            data["not_scored"][category] = why
            if category == "shape":
                data["shape_search"] = ""
                data.update({key: [] for key in SHAPE_LISTS})
            else:
                data[category] = []
            continue
        if category == "shape":
            data["shape_search"] = reply["search"]
            data.update({key: reply[key] for key in SHAPE_LISTS})
        else:
            data[category] = reply[category]
    return data


def judge_alerts(calls):
    """A judge that thought about nothing is the failure this scorecard exists to catch, so it is flagged."""
    reported = [c["thinking_tokens"] for c in calls if c["thinking_tokens"] is not None]
    if reported and not any(reported):
        return ["judge: every call reports 0 thinking tokens, so --effort and alwaysThinkingEnabled did not take; "
                "read the verdicts as unreasoned"]
    return []


def score_arm(arm):
    """Hits first, then the judge with the hits as hints, then the scorecard with both side by side."""
    hits = vault_hits(arm.persona, arm.transcript, arm.vault)
    return build_scorecard(arm, judge(arm, hits), hits)


# A drafted message opens with an email subject line or a salutation, often inside a blockquote or a code block.
# "- **Subject:** SV-01" is a planner bullet, not a message, so a list item never counts.
DRAFTED_MESSAGE = re.compile(r"^(?:>\s*)*(?:\*\*)?Subject:(?:\*\*)?\s|^(?:>\s*)*(?:Hi|Hello|Dear)\s+[^\n,]{1,40},\s*$", re.M)


BRIEF_ID = re.compile(r"(?<![\w-])[KWCUD]\d{1,2}(?![\w-])")


CLAIMED_ACTION = re.compile(
    r"\b(?:i\s+(?:just\s+)?(?:ran|pushed|ran it|spoke to|talked to|called|checked with|caught)|just ran|it'?s pushed|"
    r"shape'?s done|(?:back|heard back) from|spoke to|caught them|(?:they|she|he) (?:said|confirmed|replied|wrote)|"
    r"got (?:the|their) (?:answer|name|reply))\b", re.I)


def claimed_actions(transcript):
    """Lead turns that report something done outside the chat, such as running a command, pushing a branch, or a
    reply from someone. The persona cannot do any of that, so each one is something it made up."""
    return [e["turn"] for e in transcript.spoken() if e["speaker"] == "lead" and CLAIMED_ACTION.search(e["text"])]


def leaked_brief_ids(transcript):
    """Lead turns that say an ID of the hidden brief, such as "I'll lock D1". The persona is told never to."""
    return [e["turn"] for e in transcript.spoken() if e["speaker"] == "lead" and BRIEF_ID.search(e["text"])]


def drafted_messages(transcript):
    """Assistant turns holding a message for the lead to send: a "Subject:" line or a salutation. The skills say Claude never
    drafts one, so this is counted by code, not left to the judge."""
    return [e["turn"] for e in transcript.spoken() if e["speaker"] == "assistant" and DRAFTED_MESSAGE.search(e["text"])]


def build_scorecard(arm, data, hits):
    card = enforce_citations(data, arm.transcript, arm.vault)
    card["hits"] = hits
    card["not_scored"] = data.get("not_scored") or {}
    card["check_these"] = ([f"judge: {category} not scored: {why}" for category, why in card["not_scored"].items()]
                           + judge_alerts(arm.judge_calls) + disagreements(card, hits))
    card["judge_calls"] = arm.judge_calls
    card["max_questions_in_one_turn"] = max_questions(arm.transcript)
    card["drafted_messages"] = drafted_messages(arm.transcript)
    claimed = claimed_actions(arm.transcript)
    if claimed:
        card["check_these"].append(f"persona: claimed an action outside the chat in {len(claimed)} turns "
                                   f"({', '.join(f'T{t}' for t in claimed[:8])}); read them before trusting what followed")
    leaks = leaked_brief_ids(arm.transcript)
    if leaks:
        card["check_these"].append(f"persona: said a brief ID in {len(leaks)} turns ({', '.join(f'T{t}' for t in leaks[:8])})")
    card["endings"] = arm.endings
    card["spent_usd"] = round(arm.prior_spent + arm.ledger.spent, 4)
    card["judge_usd"] = round(sum(c["cost_usd"] for c in arm.judge_calls), 4)
    card["arm"] = arm.name
    card["models"] = {"assistant": arm.args.model, "persona": arm.args.persona_model, "judge": arm.args.judge_model}
    return card


def write_scorecard(arm):
    (arm.dir / "scorecard.json").write_text(json.dumps(arm.scorecard, indent=2, ensure_ascii=False), encoding="utf-8")
    (arm.dir / "scorecard.md").write_text(render_scorecard_md(arm.scorecard, arm.persona), encoding="utf-8")


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
    calls = card.get("judge_calls") or []
    thought = ", ".join(f"{c['category']} {c['thinking_tokens'] if c['thinking_tokens'] is not None else 'not reported'}"
                        for c in calls)
    lines = [f"# Scorecard: {card['arm']}", "",
             f"Models: assistant {card['models']['assistant']}, persona {card['models']['persona']}, "
             f"judge {card['models']['judge']}. Spent ${card['spent_usd']:.2f}, of which this judging "
             f"${card.get('judge_usd', 0):.2f} over {len(calls)} calls."
             + (f" Rejudged {card['rejudged']}." if card.get("rejudged") else ""), "",
             f"Judge thinking tokens per call: {thought or 'none'}.", "",
             "Every yes cites a turn and a quote, or a vault file. Claims without one were dropped and are listed at the end.",
             "Keyword hits are the driver's own grep of the transcript and the final vault for each item's keywords.",
             "Neither the judge nor a hit is proof: a hit can be a question, and a capture can be in other words.", "",
             "## Check these", ""]
    lines += [f"- {c}" for c in card.get("check_these") or []] or ["- none: the judge and the keyword hits agree"]
    lines.append("")
    titles = {"unaware": "Gaps surfaced (U)", "wrong": "Wrong beliefs challenged (W)", "knows": "Facts captured (K)",
              "decisions": "Decisions (D)", "conflicts": "Stakeholder conflicts surfaced (C)"}
    hits = card.get("hits") or {}
    for kind, flag in SCORE_LISTS.items():
        rows = card[kind]
        if kind in (card.get("not_scored") or {}):
            lines += [f"## {titles[kind]}: not scored", "", f"- {card['not_scored'][kind]}", ""]
            continue
        if not rows:
            continue
        count = sum(1 for r in rows if r[flag])
        lines += [f"## {titles[kind]}: {count} of {len(rows)}", "", "| ID | Brief | " + flag.capitalize()
                  + (" | Yes asked" if kind == "decisions" else "") + " | Evidence | Keyword hits | Judge's search |",
                  "|---|---|---|" + ("---|" if kind == "decisions" else "") + "---|---|---|"]
        for r in rows:
            cells = [r["id"], text[kind].get(r["id"], ""), yes_no(r[flag])]
            if kind == "decisions":
                cells.append(yes_no(r.get("yes_asked")))
            cells += [evidence(r), hits_summary(hits[r["id"]]) if r["id"] in hits else "", r.get("search", "")]
            lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
        lines.append("")
    mq = card["max_questions_in_one_turn"]
    unscored = "shape" in (card.get("not_scored") or {})
    count = (lambda key: "not scored") if unscored else (lambda key: len(card[key]))
    lines += ["## Shape of the guidance", ""]
    if unscored:
        lines += [f"The judge did not score this part: {card['not_scored']['shape']}", ""]
    lines += [f"- Most questions in one assistant turn: {mq['count']}" + (f" (T{mq['turn']})" if mq["turn"] else ""),
              f"- Turns that told rather than asked: {count('told_not_asked')}"]
    lines += [f"  - T{r['turn']}: \"{r['quote']}\"" for r in card["told_not_asked"]]
    drafted = card.get("drafted_messages") or []
    lines.append(f"- Messages drafted for the lead to send: {len(drafted)}"
                 + (f" ({', '.join(f'T{t}' for t in drafted)})" if drafted else ""))
    lines.append(f"- Decided without an explicit yes: {count('decided_without_yes')}")
    lines += [f"  - {r.get('item', '?')} at T{r['turn']}: \"{r['quote']}\"" for r in card["decided_without_yes"]]
    lines.append(f"- Invented facts: {count('invented_facts')}")
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
    row("Spent", [f"${a.prior_spent + a.ledger.spent:.2f}" for a in arms])
    row("Status", [esc(a.failure or ("ended early" if a.early() else "complete")) for a in arms])
    row("Endings", ["<br>".join(esc(f"{e['session']} {e['mode']}: {e['reason']}") for e in a.endings) for a in arms])
    row("Check these", ["<br>".join(esc(c) for c in a.scorecard["check_these"]) or "none" if a.scorecard
                        else "not scored" for a in arms])
    for kind, flag in SCORE_LISTS.items():
        for item in persona.get(kind) or []:
            cells = []
            for a in arms:
                found = next((r for r in (a.scorecard or {}).get(kind, []) if r["id"] == item["id"]), None)
                hit = (a.scorecard or {}).get("hits", {}).get(item["id"])
                if found is None:
                    cells.append("not scored")
                else:
                    cells.append(f"<span class={yes_no(found[flag])}>{yes_no(found[flag])}</span> "
                                 f"{esc(short(evidence(found), 160))}"
                                 + (f"<br><small>keyword hits: {esc(hits_summary(hit))}</small>" if hit else ""))
            label = item.get("gap") or item.get("belief") or item.get("fact") or item.get("question") or item.get("who")
            row(f"{item['id']} {short(label, 70)}", cells)
    row("Most questions in one turn", [esc((a.scorecard or {}).get("max_questions_in_one_turn", {}).get("count", "")) for a in arms])
    def shape_cell(a, key):
        if not a.scorecard or (key != "dropped" and "shape" in (a.scorecard.get("not_scored") or {})):
            return "not scored"
        return esc(len(a.scorecard.get(key, [])))
    for key in ("told_not_asked", "decided_without_yes", "invented_facts", "dropped"):
        row(key.replace("_", " "), [shape_cell(a, key) for a in arms])
    row("messages drafted for the lead", [esc(len(a.scorecard.get("drafted_messages", []))) if a.scorecard
                                          else "not scored" for a in arms])
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
    parser.add_argument("persona", nargs="?", help="persona name in tests/sim/personas/, or a .yaml path")
    parser.add_argument("--arms", help=f"comma-separated, from {', '.join(ARMS)}; default {DEFAULT_ARMS}")
    parser.add_argument("--model", help="assistant model, pinned for every arm; required unless --rejudge")
    parser.add_argument("--persona-model", help="persona model, pinned; required unless --rejudge")
    parser.add_argument("--judge-model", required=True, help="judge model, pinned")
    parser.add_argument("--budget", required=True, type=float, help="USD ceiling for the whole run; no default")
    parser.add_argument("--script", help="script name in tests/sim/scripts/, or a .yaml path; default 'default'")
    parser.add_argument("--stub", action="store_true", help="use the scripted fake claude in tests/sim/stub/; costs nothing")
    parser.add_argument("--out", default=str(RESULTS), help="results folder; the run gets its own folder inside")
    parser.add_argument("--rejudge", metavar="RUN_DIR",
                        help="score a finished run again from its transcript.jsonl and vault/, without replaying it")
    args = parser.parse_args(argv)
    if args.budget <= 0:
        parser.error("--budget must be more than 0")
    if args.rejudge:
        # The run already fixed these. Taking them again would let a scorecard name models the run never used.
        given = [name for name, value in (("<persona>", args.persona), ("--model", args.model),
                                          ("--persona-model", args.persona_model), ("--script", args.script),
                                          ("--arms", args.arms)) if value]
        if given:
            parser.error(f"--rejudge reads the persona, models, script and arms from the run's run.json; drop {', '.join(given)}")
        return args
    missing = [name for name, value in (("<persona>", args.persona), ("--model", args.model),
                                        ("--persona-model", args.persona_model)) if not value]
    if missing:
        parser.error(f"the following arguments are required: {', '.join(missing)}")
    args.script = args.script or "default"
    args.arms = args.arms or DEFAULT_ARMS
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARMS]
    if unknown or not arms or len(set(arms)) != len(arms):
        parser.error(f"--arms must name distinct arms from {', '.join(ARMS)}; got {args.arms!r}")
    args.arm_list = arms
    return args


def load_run(run_dir):
    """run.json of a finished run, with what --rejudge needs from it. A missing field is a broken run, not a default."""
    summary_path = run_dir / "run.json"
    if not summary_path.is_file():
        raise ToolFailure(f"{summary_path} does not exist, so {run_dir} is not a run folder")
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolFailure(f"{summary_path} is not JSON: {exc}") from exc
    lacks = [key for key in ("persona", "models", "per_arm") if not summary.get(key)]
    if lacks:
        raise ToolFailure(f"{summary_path} lacks {', '.join(lacks)}")
    return summary


def rejudge(args):
    """Score every arm of a finished run again: new hits, new judge calls, new scorecards and compare.html. The
    transcript, the vault and run.json are read and never written; what this judging cost goes in rejudge.json."""
    run_dir = pathlib.Path(args.rejudge).resolve()
    try:
        summary = load_run(run_dir)
        persona_path = resolve(summary["persona"], "personas")
        persona = load_yaml(persona_path)
        problems = persona_problems(persona)
        if problems:
            raise ToolFailure(f"{persona_path} is not a valid persona:\n  " + "\n  ".join(problems))
    except ToolFailure as exc:
        print(f"sim: {exc}", file=sys.stderr)
        return 2
    args.model, args.persona_model = summary["models"].get("assistant"), summary["models"].get("persona")
    names = [name for name in summary.get("arms") or summary["per_arm"] if name in summary["per_arm"]]
    share = args.budget / len(names)
    when = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    arms, failed = [], False
    for name in names:
        try:
            arm = Arm.reopen(name, run_dir, args, persona, share, summary["per_arm"][name])
        except ToolFailure as exc:
            print(f"[{name}] tool failure: {exc}", file=sys.stderr)
            failed = True
            break
        arms.append(arm)
        try:
            arm.scorecard = score_arm(arm)
            arm.scorecard["rejudged"] = when
            write_scorecard(arm)
        except ToolFailure as exc:
            arm.failure = f"tool failure: {exc}"
            failed = True
            print(f"[{name}] {arm.failure}", file=sys.stderr)
            break
    if arms:
        (run_dir / "compare.html").write_text(render_compare(summary.get("run_id", run_dir.name), persona, arms),
                                              encoding="utf-8")
    record = {"rejudged": when, "judge_model": args.judge_model, "budget_usd": args.budget, "stub": args.stub,
              "spent_usd": round(sum(a.ledger.spent for a in arms), 4),
              "per_arm": {a.name: {"spent_usd": round(a.ledger.spent, 4), "failure": a.failure,
                                   "judge_calls": a.judge_calls} for a in arms},
              "exit": 2 if failed else 0}
    (run_dir / "rejudge.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Rejudged for ${record['spent_usd']:.2f} of ${args.budget:.2f}. Results: {run_dir}")
    return record["exit"]


def main(argv=None):
    args = parse_args(argv)
    if args.rejudge:
        return rejudge(args)
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
            arm.scorecard = score_arm(arm)
            write_scorecard(arm)
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
