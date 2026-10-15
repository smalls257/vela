#!/usr/bin/env python3
"""Compare two sim runs of Vela: a BASELINE and a later run (the MID-POINT of the overhaul, or any run after it).

It answers the overhaul plan's section 8.1 question (docs/plans/2026-10-14-cli-skill-overhaul.md): did the slimmer
skills keep sessions as detailed, and did reliability improve? Every figure is measured the same way on both runs (one
ruler), except Completeness, `check` and `capture`, which each run's own checkout prints, as the plan asks.

This is the repo's one comparison tool. It took over tests/sim/compare.py, whose arm pairing lives on as
LEGACY_NAMES; /tmp/compare/compare_runs.py is a copy of this file, so it needs nothing from the repo to run.

Missing data is said aloud and never read as zero: a figure that can't be read is {"missing": "<why>"} in the JSON
and "missing (<why>)" in the Markdown, and its delta is "n/a". The verdict names what it could not read.

Usage:
  python3 compare_runs.py [--baseline RUN_DIR] [--midpoint RUN_DIR] [--arm vela]
                          [--baseline-checkout DIR] [--midpoint-checkout DIR]
                          [--threshold 0.10] [--json OUT.json]
  python3 compare_runs.py <baseline run> <later run> [options]

RUN_DIR defaults to the newest folder in /tmp/baseline-wt/tests/sim/results/ and /tmp/midpoint-wt/tests/sim/results/.
A checkout defaults to the folder three levels above RUN_DIR (<checkout>/tests/sim/results/<run-id>) when it holds
the plugin, else the repo this file sits in, and the notes say so. `--arm` is today's arm name; a run recorded before
the rename keeps its old folder (`planner`), and LEGACY_NAMES pairs it. Markdown goes to stdout, the JSON to --json
(default: compare-<baseline-id>-vs-<midpoint-id>.json in the system's temp folder).

Exit: 0 GO, 1 ADJUST, 3 STOP, 2 the tool could not read a run folder at all. It reads only: it never starts a sim run,
never calls claude, and never writes into a run folder or a checkout.
"""
import argparse
import json
import pathlib
import re
import statistics
import subprocess
import sys
import tempfile

DEFAULT_ROOTS = {"baseline": pathlib.Path("/tmp/baseline-wt/tests/sim/results"),
                 "midpoint": pathlib.Path("/tmp/midpoint-wt/tests/sim/results")}
# Arm folders of runs recorded before the tool was renamed, by the arm they are today. The only place the old names
# live: a run keeps its folder as it was recorded, and `--arm vela` finds `planner` in such a run.
LEGACY_NAMES = {"planner": "vela", "planner-seuss": "vela-seuss"}  # legacy-name
THRESHOLD = 0.10  # the plan's mid-point gate: a detail count more than 10% below baseline is thinning (8.3)
CLI_TIMEOUT = 180


# ------------------------------------------------------------------ missing data

def missing(why):
    return {"missing": why}


def is_missing(value):
    return isinstance(value, dict) and set(value) == {"missing"}


def show(value):
    if is_missing(value):
        return f"missing ({value['missing']})"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".") if abs(value) < 100 else f"{value:.1f}"
    return str(value)


# ------------------------------------------------------------------ reading the run folder

def newest_run(root):
    runs = sorted(p for p in root.glob("*") if p.is_dir() and (p / "run.json").exists())
    return runs[-1] if runs else None


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return missing(f"{path.name} not written")
    except json.JSONDecodeError as exc:
        return missing(f"{path.name} does not parse: {exc}")


def read_transcript(path):
    if not path.exists():
        return missing("transcript.jsonl not written")
    entries, bad = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            bad += 1  # the run may be writing the last line right now
    return {"entries": entries, "unparsed": bad}


def raw_tool_inputs(raw_dir):
    """Full tool inputs per assistant call, from raw/NNN-assistant.txt in call order. The transcript keeps only the
    first 200 characters of each input, which can cut a chained git command before its push. Subagent calls are left
    out, as run.py leaves out their text. Returns (calls, lines that look like JSON and don't parse), or None."""
    if not raw_dir.is_dir():
        return None
    calls, unparsed = [], 0
    for path in sorted(raw_dir.glob("*-assistant.txt")):
        tools = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                unparsed += 1  # a call cut off mid-line; counted, and the notes say how many
                continue
            if event.get("type") != "assistant" or event.get("parent_tool_use_id"):
                continue
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools.append({"name": block.get("name", "?"), "input": tool_text(block.get("input"))})
        calls.append(tools)
    return calls, unparsed


def tool_text(value):
    if isinstance(value, dict) and isinstance(value.get("command"), str):
        return value["command"]
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def load_script(checkout, name, notes):
    """The script's sessions, read from the run's own checkout. PyYAML comes from the plugin's bundled copy; without
    it the session lines are read by pattern, and `notes` says so."""
    path = checkout / "tests" / "sim" / "scripts" / f"{name}.yaml"
    if not path.exists():
        return missing(f"script {path} not found")
    for lib in (checkout / "plugin" / "lib",):
        if str(lib) not in sys.path:
            sys.path.insert(0, str(lib))
    try:
        import yaml
    except ImportError:
        notes.append(f"no PyYAML in {checkout}: the script's modes were read by pattern, its caps not at all")
        modes = re.findall(r"^\s*- mode: *(\S+)", path.read_text(encoding="utf-8"), re.M)
        return [{"mode": m, "cap": None} for m in modes]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return missing(f"script {path} does not parse: {exc}")
    return [{"mode": s.get("mode"), "cap": s.get("cap")} for s in data.get("sessions") or []]


def stored_arm(run_dir, arm):
    """The arm folder a run holds for today's arm `arm`: the folder itself, or the name it had before the rename."""
    names = [arm] + [old for old, new in LEGACY_NAMES.items() if new == arm] + [LEGACY_NAMES.get(arm, arm)]
    return next((n for n in dict.fromkeys(names) if (run_dir / n).is_dir()), None)


def has_plugin(checkout):
    return any((checkout / "plugin" / "scripts" / name).exists() for name in ("vela", "planner"))  # legacy-name


class Run:
    def __init__(self, label, run_dir, arm, checkout):
        self.label, self.dir, self.arm_name = label, run_dir, arm
        self.arm = run_dir / arm
        self.checkout = checkout
        self.notes = []
        self.raw_unparsed = 0
        self.run_json = read_json(run_dir / "run.json")
        self.scorecard = read_json(self.arm / "scorecard.json")
        self.transcript = read_transcript(self.arm / "transcript.jsonl")
        self.vault = self.arm / "vault"
        self.finished = not is_missing(self.run_json) and "exit" in self.run_json
        if not self.finished:
            self.notes.append("run not finished: run.json has no exit code, so every figure is a snapshot of a run in progress")
        script = self.run_json.get("script") if not is_missing(self.run_json) else None
        self.script = load_script(checkout, script, self.notes) if script else missing("run.json names no script")
        self.cli = next((p for p in (checkout / "plugin" / "scripts" / "planner",  # legacy-name
                                     checkout / "plugin" / "scripts" / "vela") if p.exists()), None)
        self.turn_tools = self._turn_tools()

    def spoken(self):
        if is_missing(self.transcript):
            return []
        return [e for e in self.transcript["entries"] if e.get("speaker") in ("assistant", "lead") and "turn" in e]

    def assistant_turns(self):
        return [e for e in self.spoken() if e["speaker"] == "assistant"]

    def _turn_tools(self):
        """turn number -> list of {name, input}, full inputs from raw/ when the counts line up, else the transcript's."""
        turns = self.assistant_turns()
        read = raw_tool_inputs(self.arm / "raw")
        raw, full = (read[0] if read else None), {}
        if read and read[1]:
            self.notes.append(f"raw/ holds {read[1]} JSON-looking lines that don't parse (calls cut off mid-line); "
                              "their tool inputs are not counted")
        if raw is None:
            self.notes.append("no raw/ folder: tool inputs are the transcript's 200-character cut")
        elif len(raw) != len(turns):
            self.notes.append(f"raw/ has {len(raw)} assistant calls and the transcript {len(turns)} assistant turns; "
                              f"the first {min(len(raw), len(turns))} are matched in order, the rest use the transcript's cut")
        for i, e in enumerate(turns):
            if raw is not None and i < len(raw):
                full[e["turn"]] = raw[i]
            else:
                full[e["turn"]] = [{"name": t.get("name"), "input": t.get("input", "")} for t in e.get("tool_calls") or []]
        return full

    def run_cli(self, vault, *args):
        if self.cli is None:
            return None, f"no plugin/scripts/vela (or planner) in {self.checkout}"  # legacy-name
        if not vault.is_dir():
            return None, "the arm has no vault/"
        try:
            done = subprocess.run([sys.executable, str(self.cli), *args, "--vault", str(vault)],
                                  capture_output=True, text=True, timeout=CLI_TIMEOUT)
        except subprocess.TimeoutExpired:
            return None, f"{' '.join(args)} timed out after {CLI_TIMEOUT}s"
        return done, None


# ------------------------------------------------------------------ sessions, spend, turns

def sessions_section(run):
    if is_missing(run.transcript):
        return {"missing": run.transcript["missing"]}
    entries = run.transcript["entries"]
    started = {e["session"]: e.get("mode") for e in entries if e.get("event") == "session-start"}
    ended = {e["session"]: e.get("reason") for e in entries if e.get("event") == "session-end"}
    skipped = {e["session"] for e in entries if e.get("event") == "session-skipped"}
    if not is_missing(run.run_json) and run.run_json.get("per_arm", {}).get(run.arm_name, {}).get("endings"):
        endings = run.run_json["per_arm"][run.arm_name]["endings"]
        ended = {e["session"]: e["reason"] for e in endings}
    turns = {}
    for e in run.assistant_turns():
        turns[e["session"]] = turns.get(e["session"], 0) + 1
    planned = len(run.script) if not is_missing(run.script) else missing(run.script["missing"])
    reasons = list(ended.values())
    per_session = []
    for index in sorted(set(started) | set(skipped)):
        per_session.append({"session": index, "mode": started.get(index, "?"),
                            "ended": "skipped" if index in skipped else ended.get(index, "in progress"),
                            "assistant_turns": turns.get(index, 0)})
    ended_turns = [turns.get(i, 0) for i in ended]
    by_mode = {}
    for s in per_session:
        if s["ended"] not in ("in progress", "skipped"):
            by_mode.setdefault(s["mode"], []).append(s["assistant_turns"])
    # An assistant turn's cost_usd is its Claude session's running total (run.py, assistant_turn), so a session costs
    # its highest figure; adding the turns up would count the early turns again on every resume. A lead turn's cost
    # is that call's own.
    cost = {"assistant": 0.0, "lead": 0.0}
    running = {}
    for e in run.spoken():
        if e["speaker"] == "assistant":
            key = e.get("session_id") or f"turn-{e['turn']}"
            running[key] = max(running.get(key, 0.0), float(e.get("cost_usd") or 0))
        else:
            cost["lead"] += float(e.get("cost_usd") or 0)
    cost["assistant"] = sum(running.values())
    if run.finished and "spent_usd" in run.run_json:
        spend = run.run_json["spent_usd"]
        spend_source = "run.json"
    else:
        spend = round(cost["assistant"] + cost["lead"], 4)
        spend_source = "transcript sum (run.json has no final spend)"
    judge = (run.scorecard.get("judge_usd") if not is_missing(run.scorecard)
             else missing("no scorecard: the run is not judged yet"))
    return {
        "planned": planned,
        "started": len(started),
        "finished": reasons.count("persona-end"),
        "cut_by_budget": reasons.count("budget"),
        "cut_by_turn_cap": reasons.count("turn-cap"),
        "skipped": len(skipped),
        "in_progress": len([i for i in started if i not in ended]),
        "not_started": (planned - len(started) - len(skipped)) if not is_missing(planned) else planned,
        "spend_usd": spend, "spend_source": spend_source,
        "spend_assistant_usd": round(cost["assistant"], 4), "spend_lead_usd": round(cost["lead"], 4),
        "spend_judge_usd": judge,
        "assistant_turns": sum(turns.values()),
        "turns_per_ended_session": round(statistics.mean(ended_turns), 2) if ended_turns else missing("no session ended"),
        "turns_per_mode": {m: round(statistics.mean(v), 2) for m, v in sorted(by_mode.items())},
        "per_session": per_session,
    }


# ------------------------------------------------------------------ the scorecard

SCORE_LISTS = {"knows": ("captured", "K facts captured"), "unaware": ("surfaced", "U gaps surfaced"),
               "wrong": ("challenged", "W wrong beliefs challenged"), "conflicts": ("surfaced", "C conflicts surfaced"),
               "decisions": ("decided", "D decisions decided")}


def scorecard_section(run):
    card = run.scorecard
    if is_missing(card):
        why = card["missing"] + (", the run is still going" if not run.finished else "")
        return {"missing": why}
    out, items = {}, {}
    not_scored = card.get("not_scored") or {}
    for kind, (flag, label) in SCORE_LISTS.items():
        rows = card.get(kind)
        if kind in not_scored or not isinstance(rows, list):
            out[kind] = missing(f"judge did not score it: {not_scored.get(kind, 'no rows')}")
            continue
        out[kind] = sum(1 for r in rows if r.get(flag))
        out[kind + "_of"] = len(rows)
        items.update({r["id"]: bool(r.get(flag)) for r in rows if "id" in r})
        if kind == "decisions":
            out["decisions_yes_asked"] = sum(1 for r in rows if r.get(flag) and r.get("yes_asked"))
    out["dropped_claims"] = len(card.get("dropped") or [])
    out["dropped_claim_list"] = card.get("dropped") or []
    shape_unscored = "shape" in not_scored
    for key in ("told_not_asked", "decided_without_yes", "invented_facts"):
        out[key] = missing("shape not scored") if shape_unscored else len(card.get(key) or [])
    endings = card.get("session_endings") or []
    out["clear_next_step"] = missing("shape not scored") if shape_unscored else sum(1 for r in endings if r.get("clear_next_step"))
    out["clear_next_step_of"] = len(endings)
    voice = card.get("voice") or {}
    out["voice_score"] = voice.get("score") if voice.get("score") is not None else missing("no voice score")
    out["max_questions_in_one_turn"] = (card.get("max_questions_in_one_turn") or {}).get("count", missing("not recorded"))
    out["drafted_messages"] = len(card.get("drafted_messages") or [])
    tracer = card.get("tracer")
    out["tracer_ok"] = (missing("tracer not scored") if "tracer" in not_scored or not isinstance(tracer, dict)
                        else bool(tracer.get("ok")))
    out["check_these"] = len(card.get("check_these") or [])
    out["items"] = items
    return out


# ------------------------------------------------------------------ codes, IDs and tool names the lead reads

SUBCOMMANDS = ("check|check-slice|check-diagrams|render|view|explore|role|next-id|publish|freshness|open|propose|proposals|"
               "terms|doctor|where|status|next|capture|style|ladder|upgrade|health|query|questions|findings|handoff|export|"
               "tickets|voicecheck|voicescore|session|close|guard|conventions|record|marks|decide|whoami|apply")
LEAK_KINDS = {  # kind -> (pattern, counts toward the leak total)
    "raw ID (run.py's set)": (re.compile(r"\b(?:UNK|CAP|CON|EPC)-\d{1,3}(?:\.FR\d+)?\b"), True),
    "other ID": (re.compile(r"\b(?:FLO|SLC|ADR|PTY|SV|EVT|ENT|OQ|SRC|CST|INI|RUN|R)-\d{1,4}\b|\bAPP-[a-z][a-z0-9-]+\b"
                            r"|\bQ-[A-Z]{2,4}-\d{2}\b"), True),
    "check code": (re.compile(r"\b[WE]\d{3}\b"), True),
    "gate name": (re.compile(r"\bGATE-\w+|--gate\b|\bgate\s+\d\b", re.I), True),
    "capture number": (re.compile(r"\^c\d{2,3}\b|(?<![\w/.-])c\d{2}\b"), True),
    "CLI command (planner or vela)": (re.compile(rf"\b(?:planner|vela)\s+(?:{SUBCOMMANDS})\b|`(?:planner|vela)`", re.I), True),
    "git or gh command": (re.compile(r"\bgit\s+(?:push|commit|merge|fetch|switch|branch|add|rebase|checkout|status|log)\b"
                                     r"|\bgh\s+(?:pr|api|auth)\b"), True),
    "path or variable": (re.compile(r"(?:/private)?/tmp/\S+|\$\{?CLAUDE_[A-Z_]+\}?|\bplugin/scripts\b|\.claude/"), True),
    "slash command (/planner: or /vela:)": (re.compile(r"/(?:planner|vela):[a-z-]+"), False),
    "file name": (re.compile(r"\b[\w.-]+\.(?:md|json|ya?ml|html)\b"), False),
    "product name (planner or Vela)": (re.compile(r"(?<![/:\w])(?:planner|vela)(?![:\w-])", re.I), False),
}


def leaks_in(text):
    found = {}
    taken = []  # a span counted by an earlier kind is not counted again
    for kind, (pattern, _) in LEAK_KINDS.items():
        for m in pattern.finditer(text):
            if any(m.start() < b and a < m.end() for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            found.setdefault(kind, []).append(m.group(0))
    return found


def voice_section(run):
    turns = run.assistant_turns()
    if not turns:
        return {"missing": "no assistant turns in the transcript"}
    by_kind = {k: 0 for k in LEAK_KINDS}
    dirty, total, worst = 0, 0, []
    for e in turns:
        found = leaks_in(e.get("text") or "")
        counted = sum(len(v) for k, v in found.items() if LEAK_KINDS[k][1])
        for k, v in found.items():
            by_kind[k] += len(v)
        total += counted
        dirty += counted > 0
        if counted:
            worst.append((counted, e["turn"], [w for k, v in found.items() if LEAK_KINDS[k][1] for w in v][:6]))
    worst.sort(reverse=True)
    return {"lead_facing_turns": len(turns), "turns_with_leaks": dirty, "leaks": total,
            "leaks_per_turn": round(total / len(turns), 3), "share_of_turns_with_leaks": round(dirty / len(turns), 3),
            "by_kind": by_kind, "worst_turns": [{"turn": t, "count": c, "sample": s} for c, t, s in worst[:5]]}


# ------------------------------------------------------------------ close steps

# The tool, in every form a session ran it: `vela close`, `python3 /…/plugin/scripts/vela close`, a shell function
# named for it, the old name, and a variable holding the command (`P="python3 …/vela"; $P close`, `"${VELA}" close`).
# Missing the variable form made S8 of the 2026-10-14 mid-point read as two skipped close steps it had run.
TOOL = r"(?<![\w-])(?:planner|vela)"  # legacy-name
CLI = rf"(?:{TOOL}|\$\{{?[A-Za-z_]\w*\}}?)['\"]?\s+"
SKILL_CLI = rf"{TOOL} "  # how a close skill names a command it asks for: `vela render`, or `planner render` in an old one
CLOSE_STEPS = {  # step -> (what in a tool input shows it ran, what in the checkout's close skill shows it is asked for)
    "find the session": (rf"git branch (?:-r )?--list|git show \S+:sessions/|git grep -l|{CLI}session open", r"Find the session"),
    "bring in main": (rf"merge-base --is-ancestor|git merge\b[^\n]*origin/main|git fetch origin|{CLI}close sync-main",
                      r"bring in `main`"),
    "render": (rf"{CLI}render\b", rf"{SKILL_CLI}render"),
    "check": (rf"{CLI}check(?![-\w])", rf"{SKILL_CLI}check"),
    "close gate": (rf"{CLI}close gate\b", r"close gate"),
    # `close finish` closes the record, commits it and rebuilds the dashboard (overhaul Task 22a), so a close skill
    # that asks for it asks for both steps, and a run of it ran both.
    "close commit": (rf"Close session|{CLI}close stage[^\n]*--close|{CLI}close finish\b",
                     r"Close session|close stage --close|close finish"),
    "push": (rf"git push\b|{CLI}close push\b", r"git push|close push"),
    "open the PR": (rf"gh pr (?:create|comment)|{CLI}close pr\b", r"gh pr create|close pr"),
    "rebuild the explorer": (rf"{CLI}explore\b|{CLI}close (?:finish|dashboard)\b",
                             rf"{SKILL_CLI}explore|close finish|close dashboard"),
}
NO_SESSION = re.compile(r"no (?:open )?session (?:is )?open|nothing (?:is )?open|no session to close|"
                        r"(?:isn't|is not|wasn't) (?:a|any) (?:open )?session", re.I)
NO_SESSION_STEPS = ("find the session", "rebuild the explorer")


def close_skill_text(checkout):
    for path in (checkout / "plugin" / "skills" / "close" / "SKILL.md",):
        if path.exists():
            return path.read_text(encoding="utf-8")
    return None


def close_section(run):
    sessions = sessions_section(run)
    if "missing" in sessions:
        return {"missing": sessions["missing"]}
    skill = close_skill_text(run.checkout)
    if skill is None:
        return {"missing": f"no close SKILL.md in {run.checkout}"}
    expected = [s for s, (_, marker) in CLOSE_STEPS.items() if re.search(marker, skill)]
    spoken = run.assistant_turns()
    closes, skipped, cut_missing, by_step = [], 0, 0, {s: 0 for s in expected}
    for s in sessions["per_session"]:
        if s["mode"] != "close":
            continue
        turns = [e for e in spoken if e["session"] == s["session"]]
        tools = " \n".join(t["input"] for e in turns for t in run.turn_tools.get(e["turn"], []))
        ran = [step for step in expected if re.search(CLOSE_STEPS[step][0], tools)]
        nothing_open = "close commit" not in ran and any(NO_SESSION.search(e.get("text") or "") for e in turns)
        want = [x for x in expected if x in NO_SESSION_STEPS] if nothing_open else expected
        absent = [x for x in want if x not in ran]
        cut = s["ended"] in ("budget", "turn-cap", "in progress")
        if cut:
            cut_missing += len(absent)
        else:
            skipped += len(absent)
            for x in absent:
                by_step[x] += 1
        closes.append({"session": s["session"], "ended": s["ended"], "nothing_open": nothing_open,
                       "missing_steps": absent, "counted_as": "cut short" if cut else "skipped"})
    return {"expected_steps": expected, "close_sessions": len(closes),
            "close_sessions_with_a_skip": sum(1 for c in closes if c["missing_steps"] and c["counted_as"] == "skipped"),
            "skipped_steps": skipped, "missing_in_cut_sessions": cut_missing, "skipped_by_step": by_step,
            "per_close": closes}


# ------------------------------------------------------------------ consent before push

PUSH = re.compile(rf"git push\b|{CLI}close push\b")
SAID_PUSH = re.compile(r"\bpush\b|open the (?:pr|pull request)|go ahead|ship it|send it", re.I)
YES = re.compile(r"^\W*(?:yes|yep|yeah|yup|sure|ok|okay|go|do it|please|sounds good|fine|correct|right|absolutely|"
                 r"definitely|let's do it|that's fine)\b", re.I)
ASKED_PUSH = re.compile(r"push|pull request|\bPR\b|send (?:it|this) (?:up|for review)|for review|share", re.I)


def consent_section(run):
    spoken = run.spoken()
    if not spoken:
        return {"missing": "no turns in the transcript"}
    pushes, without = 0, []
    for i, e in enumerate(spoken):
        if e["speaker"] != "assistant":
            continue
        tools = [t["input"] for t in run.turn_tools.get(e["turn"], [])]
        if not any(PUSH.search(t) for t in tools):
            continue
        pushes += 1
        before = [x for x in spoken[:i] if x["session"] == e["session"]]
        consent = False
        for j, x in enumerate(before):
            if x["speaker"] != "lead":
                continue
            text = x.get("text") or ""
            if SAID_PUSH.search(text) and not re.search(r"\b(?:don't|do not|not yet|wait|hold)\b", text, re.I):
                consent = True
            prior = before[j - 1] if j else None
            if YES.search(text) and prior and prior["speaker"] == "assistant" and "?" in (prior.get("text") or "") \
                    and ASKED_PUSH.search(prior.get("text") or ""):
                consent = True
        if not consent:
            without.append({"turn": e["turn"], "session": e["session"]})
    return {"pushes": pushes, "pushes_with_consent": pushes - len(without), "pushes_without_consent": len(without),
            "without_consent": without}


# ------------------------------------------------------------------ the vault

SKIP_DIRS = {".git", ".claude", "voice", ".inbox", ".planner", ".github", "dashboard", "node_modules", "bin"}
SKIP_FILES = {"CONVENTIONS.md", "CLAUDE.md", "README.md"}
ID_TOKEN = r"(?:CAP-\d+\.FR\d+|APP-[a-z][a-z0-9-]*|[A-Z]{1,4}-\d+)"
ITEM_HEADING = re.compile(rf"^(#{{2,4}}) ({ID_TOKEN})\b\s*(.*)$")
HEADING = re.compile(r"^(#{1,6}) ")
STATE_BULLET = re.compile(r"^\s*- \*\*State:\*\*\s*([A-Za-z-]+)")
ASK_BULLET = re.compile(r"^\s*- \*\*Ask:\*\*\s*\S")
CASE_HEADER = re.compile(r"^\|\s*Case\s*\|\s*When\s*\|\s*Status\s*\|", re.I)
GENERATED = re.compile(r"<!-- generated:.*?<!-- /generated[^>]*-->", re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
FENCE = re.compile(r"^```.*?^```", re.S | re.M)
WORD = re.compile(r"[A-Za-z0-9][\w'’-]*")
CAPTURE = re.compile(r"\^c\d+\s*$")
MARK = re.compile(r"→\s*(keep|drop|park|merge|answer|promote|move)\b", re.I)
RESOLVED_STATES = {"answered", "resolved", "closed", "decided", "fact", "dropped", "done", "retired", "accepted"}


def frontmatter(text):
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip().strip("'\"")
    return meta, text[end + 4:]


def vault_files(vault):
    for path in sorted(vault.rglob("*.md")):
        rel = path.relative_to(vault)
        if set(rel.parts[:-1]) & SKIP_DIRS or rel.name in SKIP_FILES:
            continue
        yield rel, path.read_text(encoding="utf-8", errors="replace")


def prose_words(body):
    body = FENCE.sub(" ", COMMENT.sub(" ", GENERATED.sub(" ", body)))
    return len(WORD.findall(body))


def sections(lines):
    """Item sections: (level, id, name, body lines), skipping headings under ## History, which are history refs."""
    out, in_history = [], False
    for i, line in enumerate(lines):
        h = HEADING.match(line)
        if h and len(h.group(1)) <= 2:
            in_history = line.strip().lower().startswith("## history")
        m = ITEM_HEADING.match(line)
        if not m or in_history:
            continue
        level = len(m.group(1))
        end = next((j for j in range(i + 1, len(lines))
                    if HEADING.match(lines[j]) and len(HEADING.match(lines[j]).group(1)) <= level), len(lines))
        out.append((level, m.group(2), m.group(3).strip(), lines[i + 1:end]))
    return out


def kind_of(item_id):
    if ".FR" in item_id:
        return "FR (functional requirement)"
    return item_id.split("-")[0]


# ------------------------------------------------------------------ the shared vault, not the working tree

GIT_TIMEOUT = 120


class Scored:
    """The copy of a run's vault that is scored: where it is, the ref it holds, and where the working tree stood.
    `shared` is False when no origin could be read and the working tree is scored instead, which the verdict says."""

    def __init__(self, path, ref, working_tree, shared, why=""):
        self.path, self.ref, self.working_tree, self.shared, self.why = path, ref, working_tree, shared, why


def git_out(cwd, *args):
    """(exit code, stdout, stderr) of a git command that only reads `cwd`'s sources; hooks off."""
    try:
        done = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=cwd, capture_output=True,
                              text=True, errors="replace", timeout=GIT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return 124, "", f"git {args[0]} took more than {GIT_TIMEOUT}s"
    return done.returncode, done.stdout, done.stderr


def origin_of(run):
    """(the arm's shared repo, why not): its own origin.git, which a copied run folder carries, else the vault's
    origin remote when that path still exists."""
    own = run.arm / "origin.git"
    if own.is_dir():
        return own, ""
    code, out, _ = git_out(run.vault, "remote", "get-url", "origin")
    if code != 0:
        return None, "the arm has no origin.git and the vault no origin remote"
    path = pathlib.Path(out.strip())
    return (path, "") if path.exists() else (None, f"the vault's origin {path} doesn't exist any more")


def scoring_copy(run, workdir):
    """A clone of the arm's origin with origin/main checked out, and the vault's own branches fetched in as local/*
    so the history scan still sees work never pushed. The final vault is what the next session and the team would
    pull, not whatever branch the last session left checked out: the 2026-10-14 mid-point ended on a dashboard
    branch 21 commits behind main, without the handoff, and read as thinner for it."""
    code, out, _ = git_out(run.vault, "branch", "--show-current")
    branch = out.strip() if code == 0 and out.strip() else "(detached or no git)"
    origin, why = origin_of(run)
    if origin is not None:
        clone = workdir / "vault"
        steps = [(workdir, "clone", "-q", "--no-hardlinks", "--no-checkout", str(origin), str(clone)),
                 (clone, "fetch", "-q", str(run.vault.resolve()), "+refs/heads/*:refs/remotes/local/*"),
                 (clone, "checkout", "-q", "--detach", "origin/main")]
        for cwd, *args in steps:
            code, _, err = git_out(cwd, *args)
            if code != 0:
                why = f"git {args[0]} failed: {err.strip()[:160]}"
                break
        else:
            sha = git_out(clone, "rev-parse", "--short", "HEAD")[1].strip()
            code, counts, _ = git_out(clone, "rev-list", "--left-right", "--count", f"origin/main...local/{branch}")
            if code == 0 and len(counts.split()) == 2:
                behind, ahead = counts.split()
                tree = f"{branch}: {behind} commits behind origin/main, {ahead} ahead"
            else:
                tree = f"{branch} (not compared with origin/main)"
            return Scored(clone, f"origin/main at {sha}", tree, True)
    run.notes.append(f"the final vault is the working tree on {branch}, not origin/main, because {why}")
    return Scored(run.vault, f"working tree on {branch}", branch, False, why)


TEAM_DIR = "docs"  # the team's own documents: the tech design, its decision records, the work breakdown
TEAM_GROUP = "Team documents (docs/: the design and the breakdown, apart from the plan's items)"


def team_branch_docs(scored):
    """[(path, text, ref)]: team documents on origin branches not merged into origin/main and missing from it, the
    most recently committed branch's copy of each. The baseline's design lives only on design/desktop-agent, so
    reading origin/main alone would lose it."""
    if not scored.shared:
        return []
    clone = scored.path
    on_main = set(git_out(clone, "ls-tree", "-r", "--name-only", "origin/main", "--", TEAM_DIR)[1].splitlines())
    refs = git_out(clone, "for-each-ref", "--sort=-committerdate", "--format=%(refname:short)", "refs/remotes/origin")[1]
    found = {}
    for ref in refs.splitlines():
        if ref in ("origin", "origin/main", "origin/HEAD"):
            continue
        if git_out(clone, "merge-base", "--is-ancestor", ref, "origin/main")[0] == 0:
            continue
        for rel in git_out(clone, "ls-tree", "-r", "--name-only", ref, "--", TEAM_DIR)[1].splitlines():
            if rel.endswith(".md") and rel not in on_main and rel not in found:
                found[rel] = (ref, git_out(clone, "show", f"{ref}:{rel}")[1])
    return [(pathlib.PurePosixPath(rel), text, ref) for rel, (ref, text) in sorted(found.items())]


def team_docs(vault_pages, scored):
    """The team's documents, counted apart from the plan's own items: a blocked design session must not read as the
    plan thinning (the 2026-10-14 baseline's design and breakdown held all 15 OQ and 8 S items of its 82)."""
    out = {"pages": 0, "words": 0, "items_by_kind": {}, "from": {}}
    ids = set()
    found = [(rel, text, scored.ref) for rel, text in vault_pages] + team_branch_docs(scored)
    for rel, text, ref in found:
        _, body = frontmatter(text)
        out["pages"] += 1
        out["words"] += prose_words(body)
        out["from"][str(rel)] = ref
        for _, item_id, _, _ in sections(body.splitlines()):
            ids.add(item_id)
            kind = kind_of(item_id)
            out["items_by_kind"][kind] = out["items_by_kind"].get(kind, 0) + 1
    out["items"] = sum(out["items_by_kind"].values())
    out["items_by_kind"] = dict(sorted(out["items_by_kind"].items()))
    return out, ids


def vault_section(run, scored):
    vault = scored.path
    if not vault.is_dir():
        return {"missing": "the arm has no vault/"}
    pages, items, defined = {}, {}, set()
    unknowns, contracts = {}, {"total": 0, "with_case_table": 0, "with_error_case": 0}
    flows, mermaid, slices = {"total": 0, "drawn": 0}, 0, 0
    captures = {"captures": 0, "marked": 0, "by_mark": {}}
    ledger = {"rows": 0, "by_state": {}}
    tracer_bullet = False
    item_words = {}
    files = list(vault_files(vault))
    team, team_ids = team_docs([(rel, text) for rel, text in files if rel.parts[0] == TEAM_DIR], scored)
    defined |= team_ids
    for rel, text in files:
        if rel.parts[0] == TEAM_DIR:
            continue
        meta, body = frontmatter(text)
        ptype = meta.get("type") or f"untyped ({rel.parts[0] if len(rel.parts) > 1 else 'root'})"
        page = pages.setdefault(ptype, {"pages": 0, "words": 0})
        page["pages"] += 1
        page["words"] += prose_words(body)
        mermaid += len(re.findall(r"^```mermaid", body, re.M))
        if meta.get("id"):
            defined.add(meta["id"])
        page_id = meta.get("id", "")
        if re.match(r"(?:CAP|FLO|EPC|SLC|ADR)-\d+$", page_id):
            kind = page_id.split("-")[0] + " page"
            state = meta.get("state") or "no state"
            items.setdefault(kind, {})[state] = items.setdefault(kind, {}).get(state, 0) + 1
        if ptype == "flow" or page_id.startswith("FLO-"):
            flows["total"] += 1
            if re.search(r"^```mermaid\s*\n\s*sequenceDiagram", body, re.M):
                flows["drawn"] += 1
        if ptype == "slice":
            slices += 1
        if rel.name.startswith("04b-releases") and re.search(r"\*\*Tracer:\*\*", body):
            tracer_bullet = True
        lines = body.splitlines()
        for row in re.findall(r"^\|\s*\[?\[?([A-Z]{1,4}-?\d+(?:\.FR\d+)?)", body, re.M):
            defined.add(row)
        for level, item_id, name, sect in sections(lines):
            defined.add(item_id)
            kind = kind_of(item_id)
            state = next((STATE_BULLET.match(x).group(1).lower() for x in sect if STATE_BULLET.match(x)), "no state")
            items.setdefault(kind, {})[state] = items.setdefault(kind, {}).get(state, 0) + 1
            item_words.setdefault(kind, []).append(prose_words("\n".join(sect)))
            if kind == "UNK":
                u = unknowns.setdefault("by_state", {})
                u[state] = u.get(state, 0) + 1
                unknowns["with_ask"] = unknowns.get("with_ask", 0) + any(ASK_BULLET.match(x) for x in sect)
            if kind == "CON":
                contracts["total"] += 1
                table = [x for x in sect if x.startswith("|")]
                if any(CASE_HEADER.match(x) for x in table):
                    contracts["with_case_table"] += 1
                    statuses = [c[2].strip().lower() for c in (x.split("|") for x in table) if len(c) > 3]
                    if any(s == "error" or (s.isdigit() and int(s) >= 400) for s in statuses):
                        contracts["with_error_case"] += 1
        if ptype == "session" or rel.parts[0] == "sessions":
            for line in lines:
                if CAPTURE.search(line):
                    captures["captures"] += 1
                    m = MARK.search(line)
                    if m:
                        captures["marked"] += 1
                        captures["by_mark"][m.group(1).lower()] = captures["by_mark"].get(m.group(1).lower(), 0) + 1
        if rel.name == "11-unknowns-and-risks.md":
            in_ledger = False
            for line in lines:
                if line.startswith("## "):
                    in_ledger = line.strip().lower() == "## question ledger"
                if in_ledger and line.startswith("|") and not re.match(r"^\|\s*(?:Copy\s*\||-)", line):
                    ledger["rows"] += 1
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    st = cells[1].lower() if len(cells) > 1 else "?"
                    ledger["by_state"][st] = ledger["by_state"].get(st, 0) + 1
    by_state = {}
    for kind, states in items.items():
        for st, n in states.items():
            by_state[st] = by_state.get(st, 0) + n
    unk_states = unknowns.get("by_state", {})
    return {
        "scored_ref": scored.ref, "working_tree": scored.working_tree, "scored_from_origin": scored.shared,
        "pages_total": sum(p["pages"] for p in pages.values()),
        "pages_by_type": {k: v["pages"] for k, v in sorted(pages.items())},
        "words_by_type": {k: v["words"] for k, v in sorted(pages.items())},
        "words_per_page_by_type": {k: round(v["words"] / v["pages"], 1) for k, v in sorted(pages.items())},
        "items_total": sum(sum(s.values()) for s in items.values()),
        "items_by_kind": {k: sum(v.values()) for k, v in sorted(items.items())},
        "items_by_state": dict(sorted(by_state.items())),
        "items_by_kind_and_state": {k: dict(sorted(v.items())) for k, v in sorted(items.items())},
        "words_per_item_by_kind": {k: round(statistics.mean(v), 1) for k, v in sorted(item_words.items())},
        "unknowns_total": sum(unk_states.values()),
        "unknowns_open": unk_states.get("open", 0),
        "unknowns_resolved": sum(n for st, n in unk_states.items() if st in RESOLVED_STATES),
        "unknowns_by_state": dict(sorted(unk_states.items())),
        "unknowns_with_ask": unknowns.get("with_ask", 0),
        "contracts": contracts["total"], "contracts_with_case_table": contracts["with_case_table"],
        "contracts_with_error_case": contracts["with_error_case"],
        "flows": flows["total"], "flows_drawn": flows["drawn"], "mermaid_diagrams": mermaid,
        "slices": slices, "release_tracer_bullet": tracer_bullet,
        "captures": captures["captures"], "captures_marked": captures["marked"],
        "captures_by_mark": dict(sorted(captures["by_mark"].items())),
        "ledger_rows": ledger["rows"], "ledger_by_state": dict(sorted(ledger["by_state"].items())),
        "team_docs_pages": team["pages"], "team_docs_words": team["words"], "team_docs_items": team["items"],
        "team_docs_items_by_kind": team["items_by_kind"], "team_docs_from": team["from"],
        "_defined_ids": sorted(defined),
    }


def cli_section(run, vault):
    """Completeness, check findings and capture counts, printed by the run's own checkout on the scored vault."""
    out = {}
    done, err = run.run_cli(vault, "status")
    if err:
        out["completeness"] = missing(err)
    else:
        m = re.search(r"^Completeness: (\d+)%, the average of (.*?)\.?$", done.stdout, re.M)
        out["completeness"] = (int(m.group(1)) if m and done.returncode == 0 else
                               missing(f"planner status exit {done.returncode}, no Completeness line"))
        out["completeness_line"] = m.group(0) if m else missing("no Completeness line")
    done, err = run.run_cli(vault, "check")
    if err:
        out["check"] = missing(err)
    else:
        codes = re.findall(r":\d+: ([EW]\d{3}) ", done.stdout + done.stderr)
        counts = {}
        for c in codes:
            counts[c] = counts.get(c, 0) + 1
        out["check"] = {"exit": done.returncode, "errors": sum(1 for c in codes if c[0] == "E"),
                        "warnings": sum(1 for c in codes if c[0] == "W"), "by_code": dict(sorted(counts.items()))}
    done, err = run.run_cli(vault, "capture", "--json")
    if err:
        out["capture"] = missing(err)
    elif done.returncode != 0:
        out["capture"] = missing(f"planner capture exit {done.returncode}: {(done.stdout + done.stderr).strip()[:160]}")
    else:
        try:
            counts = json.loads(done.stdout)["counts"]
            out["capture"] = {k: v for k, v in counts.items() if isinstance(v, (int, float))}
        except (json.JSONDecodeError, KeyError):
            out["capture"] = missing("planner capture --json did not parse")
    return out


# ------------------------------------------------------------------ IDs: reused or guessed

REUSE_CODES = ("E108", "E204", "E208", "E210")
# A question-ledger ID: a catalog copy (Q-DAT-01, Q-DAT-01@INI-001) or a reviewer question (R-FIN-06). Matched whole,
# so its tail (DAT-01, FIN-06) is never read as an ID of its own: those tails were 13 of the mid-point's 27 "guessed".
LEDGER_ID = r"[QR]-[A-Z]{2,4}-\d{2,3}"
NAMED_ID = re.compile(rf"(?<![\w-])(?:{LEDGER_ID}|{ID_TOKEN})(?!\w)")
# Vela's own item families, defined by a heading or a page id: one of these said to the lead and never defined is a
# guess. Any other family (a ledger row, a source, a goal, the team's D-001 or OQ-011) is defined in a table or a
# document of its own shape, so it counts as known when the vault's history holds that exact ID anywhere.
VELA_FAMILIES = {"UNK", "CAP", "CON", "EPC", "FLO", "SLC", "ADR", "APP", "PTY", "SV", "EVT", "ENT", "R"}


def id_family(item_id):
    return "ledger" if re.fullmatch(LEDGER_ID, item_id) else item_id.split("-")[0]


def ids_section(run, scored, vault, cli):
    if "missing" in vault:
        return {"missing": vault["missing"]}
    defined = set(vault["_defined_ids"])
    names = {}
    code, log, _ = git_out(scored.path, "log", "--all", "-p", "--unified=0", "--no-color", "--", "*.md")
    history = code == 0
    for line in log.splitlines():
        # A page or a table row defined on any branch, merged or not, as vault_section reads them on the final vault.
        page_id = re.match(r"^\+id:\s*['\"]?([^\s'\"]+)|^\+\|\s*\[?\[?([A-Z]{1,4}-?\d+(?:\.FR\d+)?)", line)
        if page_id:
            defined.add(page_id.group(1) or page_id.group(2))
        m = ITEM_HEADING.match(line[1:]) if line.startswith("+") and not line.startswith("+++") else None
        if m:
            defined.add(m.group(2))
            names.setdefault(m.group(2), set()).add(re.sub(r"\W+", " ", m.group(3)).strip().lower())
    many_names = {i: sorted(n) for i, n in names.items() if len({x for x in n if x}) > 1}
    held = {m.group(0) for text in [log, *(t for _, t in vault_files(scored.path))] for m in NAMED_ID.finditer(text)}
    named = {}
    for e in run.assistant_turns():
        for m in NAMED_ID.finditer(e.get("text") or ""):
            named.setdefault(m.group(0), []).append(e["turn"])
    known = lambda i: i in defined if id_family(i) in VELA_FAMILIES else i in held
    guessed = {i: t[:5] for i, t in sorted(named.items()) if not known(i)}
    by_held = sorted(i for i in named if id_family(i) not in VELA_FAMILIES and i in held and i not in defined)
    check = cli.get("check")
    reused = (missing(check["missing"]) if is_missing(check)
              else sum(check["by_code"].get(c, 0) for c in REUSE_CODES))
    next_id_calls = sum(1 for tools in run.turn_tools.values() for t in tools if re.search(rf"{CLI}next-id\b", t["input"]))
    return {"reused_in_final_vault": reused,
            "ids_with_more_than_one_name": len(many_names) if history else missing("vault git log failed"),
            "ids_with_more_than_one_name_list": {k: v[:3] for k, v in list(many_names.items())[:10]},
            "ids_named_to_lead_but_never_defined": len(guessed), "guessed_list": dict(list(guessed.items())[:15]),
            "ids_known_from_the_vaults_own_documents": len(by_held), "known_from_documents_list": by_held[:20],
            "next_id_calls": next_id_calls}


# ------------------------------------------------------------------ comparing

def num(v):
    return None if is_missing(v) or isinstance(v, (dict, list)) or v is None else float(v)


def delta_row(label, base, mid, better=None, kind="info", threshold=THRESHOLD):
    """better: 'higher', 'lower' or None. kind: 'detail' (thinning is a drop past the threshold), 'reliability'
    (worse is any move the wrong way), or 'info'."""
    row = {"measure": label, "baseline": base, "midpoint": mid, "better": better, "kind": kind}
    b, m = num(base), num(mid) if not isinstance(mid, bool) else float(mid)
    if isinstance(base, bool):
        b = float(base)
    if b is None or m is None:
        gone = [n for n, v in (("baseline", base), ("mid-point", mid)) if num(v) is None and not isinstance(v, bool)]
        row.update(delta="n/a", read=f"missing in {' and '.join(gone)}", status="missing")
        return row
    d = round(m - b, 3)
    row["delta"] = int(d) if d == int(d) else d
    row["change"] = None if b == 0 else round(d / b, 3)
    if better is None or d == 0:
        row.update(read="same" if d == 0 else "", status="same" if d == 0 else "info")
        return row
    good = (d > 0) == (better == "higher")
    if kind == "detail" and not good:
        drop = (-d / b) if b else 1.0
        if drop > threshold:
            row.update(read=f"THINNER by {drop:.0%}", status="thinned")
        else:
            row.update(read=f"lower by {drop:.0%}, within {threshold:.0%}", status="within")
        return row
    if kind == "reliability":
        row.update(read="better" if good else "WORSE", status="better" if good else "worse")
    else:  # a shown figure with a direction: say which way it moved, but it does not decide the verdict
        row.update(read=f"{'up' if d > 0 else 'down'}" + (f" {abs(d / b):.0%}" if b else ""), status="info")
    return row


def get(d, *path, default=None):
    for p in path:
        if is_missing(d):
            return d
        if not isinstance(d, dict) or p not in d:
            return default if default is not None else missing(f"no {p}")
        d = d[p]
    return d


def section_missing(sec, path):
    if isinstance(sec, dict) and "missing" in sec and len(sec) == 1:
        return missing(sec["missing"])
    return get(sec, *path)


def compare(b, m, threshold):
    rows = {}

    def add(group, label, path_b, path_m=None, better=None, kind="info"):
        rows.setdefault(group, []).append(delta_row(label, path_b(b), (path_m or path_b)(m), better, kind, threshold))

    S = lambda *p: (lambda r: section_missing(r["sessions"], p))
    for label, key, better, kind in [
            ("Sessions planned by the script", "planned", None, "info"),
            ("Sessions started", "started", "higher", "info"),
            ("Sessions finished by the lead ([END])", "finished", "higher", "info"),
            ("Sessions cut by the budget", "cut_by_budget", "lower", "reliability"),
            ("Sessions cut by the turn cap", "cut_by_turn_cap", "lower", "reliability"),
            ("Sessions skipped", "skipped", "lower", "info"),
            ("Sessions still in progress", "in_progress", None, "info"),
            ("Sessions not started", "not_started", None, "info"),
            ("Spend, USD (assistant + lead, or run.json)", "spend_usd", "lower", "info"),
            ("Spend on the judge, USD", "spend_judge_usd", None, "info"),
            ("Assistant turns", "assistant_turns", None, "info"),
            ("Assistant turns per ended session", "turns_per_ended_session", None, "info")]:
        add("Sessions, spend and turns", label, S(key), better=better, kind=kind)
    modes = sorted(set(get(b["sessions"], "turns_per_mode", default={}) or {}) |
                   set(get(m["sessions"], "turns_per_mode", default={}) or {})) \
        if not (is_missing(get(b["sessions"], "turns_per_mode")) and is_missing(get(m["sessions"], "turns_per_mode"))) else []
    for mode in modes:
        add("Sessions, spend and turns", f"Turns per {mode} session",
            lambda r, mode=mode: get(r["sessions"], "turns_per_mode", mode, default=missing(f"no ended {mode} session")))

    C = lambda *p: (lambda r: section_missing(r["scorecard"], p))
    for label, key, better, kind in [
            ("K facts captured", "knows", "higher", "detail"), ("U gaps surfaced", "unaware", "higher", "detail"),
            ("W wrong beliefs challenged", "wrong", "higher", "detail"),
            ("C conflicts surfaced", "conflicts", "higher", "detail"),
            ("D decisions decided", "decisions", None, "info"), ("D decided with the yes asked", "decisions_yes_asked", "higher", "info"),
            ("Dropped claims (judge citations that failed)", "dropped_claims", None, "info"),
            ("Prose judge: turns that told rather than asked", "told_not_asked", "lower", "info"),
            ("Prose judge: decided without an explicit yes", "decided_without_yes", "lower", "reliability"),
            ("Prose judge: invented facts", "invented_facts", "lower", "reliability"),
            ("Prose judge: sessions ending with a clear next step", "clear_next_step", "higher", "info"),
            ("Voice score (share of turns with no code, run.py)", "voice_score", "higher", "info"),
            ("Most questions in one turn", "max_questions_in_one_turn", "lower", "info"),
            ("Messages drafted for the lead to send", "drafted_messages", "lower", "info"),
            ("Tracer in release one recorded", "tracer_ok", "higher", "info"),
            ("Check these (scorecard)", "check_these", None, "info")]:
        add("Scorecard (judge, citations checked)", label, C(key), better=better, kind=kind)

    V = lambda *p: (lambda r: section_missing(r["voice"], p))
    add("Codes, IDs and tool names in lead-facing turns", "Lead-facing (assistant) turns", V("lead_facing_turns"))
    add("Codes, IDs and tool names in lead-facing turns", "Turns with any leak", V("turns_with_leaks"), better="lower")
    add("Codes, IDs and tool names in lead-facing turns", "Leaks per lead-facing turn", V("leaks_per_turn"),
        better="lower", kind="reliability")
    add("Codes, IDs and tool names in lead-facing turns", "Share of turns with a leak", V("share_of_turns_with_leaks"),
        better="lower", kind="reliability")
    for kind_name, (_, counted) in LEAK_KINDS.items():
        add("Codes, IDs and tool names in lead-facing turns",
            f"  {kind_name}" + ("" if counted else " (shown, not counted as a leak)"),
            V("by_kind", kind_name), better="lower" if counted else None)

    K = lambda *p: (lambda r: section_missing(r["close"], p))
    add("Skipped steps (close sessions)", "Close sessions", K("close_sessions"))
    add("Skipped steps (close sessions)", "Close sessions with a skipped step", K("close_sessions_with_a_skip"), better="lower")
    add("Skipped steps (close sessions)", "Steps skipped (sessions the lead ended)", K("skipped_steps"),
        better="lower", kind="reliability")
    add("Skipped steps (close sessions)", "Steps missing in close sessions cut short", K("missing_in_cut_sessions"))
    steps = list(dict.fromkeys(list(get(b["close"], "skipped_by_step", default={}) or {}) +
                               list(get(m["close"], "skipped_by_step", default={}) or {})))
    for step in steps:
        add("Skipped steps (close sessions)", f"  skipped: {step}",
            lambda r, step=step: get(r["close"], "skipped_by_step", step,
                                     default=missing("not a step this checkout's close skill names")), better="lower")

    I = lambda *p: (lambda r: section_missing(r["ids"], p))
    add("Wrong or reused IDs", "Reused IDs in the final vault (check E108, E204, E208, E210)", I("reused_in_final_vault"),
        better="lower", kind="reliability")
    add("Wrong or reused IDs", "IDs that carried more than one name in the vault's history", I("ids_with_more_than_one_name"),
        better="lower", kind="reliability")
    add("Wrong or reused IDs", "IDs said to the lead that the vault never had (guessed, or from outside the vault)", I("ids_named_to_lead_but_never_defined"),
        better="lower", kind="reliability")
    add("Wrong or reused IDs", "IDs said to the lead from the vault's own documents (ledger, sources, team docs)",
        I("ids_known_from_the_vaults_own_documents"))
    add("Wrong or reused IDs", "planner next-id calls", I("next_id_calls"))

    P = lambda *p: (lambda r: section_missing(r["consent"], p))
    add("Consent before push", "Pushes", P("pushes"))
    add("Consent before push", "Pushes with the lead's consent", P("pushes_with_consent"))
    add("Consent before push", "Pushes without consent", P("pushes_without_consent"), better="lower", kind="reliability")

    W = lambda *p: (lambda r: section_missing(r["vault"], p))
    L = lambda *p: (lambda r: section_missing(r["cli"], p))
    g = "Final vault"
    add(g, "Completeness (planner status, own checkout)", L("completeness"), better="higher", kind="detail")
    add(g, "planner check errors (own checkout)", L("check", "errors"), better="lower", kind="reliability")
    add(g, "planner check warnings (own checkout)", L("check", "warnings"), better="lower")
    add(g, "Pages", W("pages_total"), better="higher")
    for key, label, kind in [("captures", "Captures in session records", "detail"),
                             ("captures_marked", "Captures with a mark", "info"),
                             ("items_total", "Items written", "detail"),
                             ("ledger_rows", "Question ledger rows", "detail"),
                             ("unknowns_with_ask", "Unknowns with an Ask line", "detail"),
                             ("unknowns_total", "Unknowns", "info"), ("unknowns_open", "Unknowns open", "info"),
                             ("unknowns_resolved", "Unknowns resolved", "info"),
                             ("contracts", "Contracts", "info"),
                             ("contracts_with_case_table", "Contracts with a case table", "detail"),
                             ("contracts_with_error_case", "Contracts with an error case", "info"),
                             ("flows", "Flow pages", "info"), ("flows_drawn", "Flows drawn (sequence diagram)", "detail"),
                             ("mermaid_diagrams", "Mermaid diagrams", "info"),
                             ("slices", "Slice pages", "detail"),
                             ("release_tracer_bullet", "Releases page names a Tracer", "info")]:
        add(g, label, W(key), better="higher" if kind == "detail" or key in ("captures_marked", "unknowns_resolved") else None,
            kind=kind)
    # Shown, never deciding the verdict: the team's sessions run after the plan's and can be blocked by it, so a drop
    # here is a lost team tail to read in the transcript, not the plan's detail thinning.
    t = TEAM_GROUP
    add(t, "Team documents", W("team_docs_pages"), better="higher")
    add(t, "Team document words", W("team_docs_words"), better="higher")
    add(t, "Team document items (design and plan IDs)", W("team_docs_items"), better="higher")
    team_kinds = sorted({k for r in (b, m) if "missing" not in r["vault"] for k in r["vault"]["team_docs_items_by_kind"]})
    for key in team_kinds:
        add(t, f"  {key} items", lambda r, key=key: get(r["vault"], "team_docs_items_by_kind", key, default=0)
            if "missing" not in r["vault"] else missing(r["vault"]["missing"]), better="higher")
    cap_keys =sorted(set(get(b["cli"], "capture", default={}) or {}) | set(get(m["cli"], "capture", default={}) or {})) \
        if not (is_missing(get(b["cli"], "capture")) and is_missing(get(m["cli"], "capture"))) else ["counts"]
    for key in cap_keys:
        add("planner capture counts (own checkout)", key, L("capture", key), better="higher")

    def union(path):
        keys = set()
        for r in (b, m):
            v = get(r["vault"], path, default={})
            if isinstance(v, dict) and not is_missing(v):
                keys |= set(v)
        return sorted(keys)

    for key in union("items_by_kind"):
        add("Items by kind", f"{key} items", lambda r, key=key: get(r["vault"], "items_by_kind", key, default=0) if "missing" not in r["vault"]
            else missing(r["vault"]["missing"]), better="higher", kind="detail")
    for key in union("items_by_state"):
        add("Items by state", key, lambda r, key=key: get(r["vault"], "items_by_state", key, default=0) if "missing" not in r["vault"]
            else missing(r["vault"]["missing"]))
    for key in union("pages_by_type"):
        add("Pages by type", key, lambda r, key=key: get(r["vault"], "pages_by_type", key, default=0) if "missing" not in r["vault"]
            else missing(r["vault"]["missing"]), better="higher")
    for key in union("words_by_type"):
        base_words = num(get(b["vault"], "words_by_type", key, default=0)) or 0
        add("Words of detail per page type (prose only: no frontmatter, generated blocks or code)", f"{key}: words",
            lambda r, key=key: get(r["vault"], "words_by_type", key, default=0) if "missing" not in r["vault"]
            else missing(r["vault"]["missing"]), better="higher", kind="detail" if base_words >= 100 else "info")
        add("Words of detail per page type (prose only: no frontmatter, generated blocks or code)", f"{key}: words per page",
            lambda r, key=key: get(r["vault"], "words_per_page_by_type", key, default=missing("no page of this type"))
            if "missing" not in r["vault"] else missing(r["vault"]["missing"]), better="higher")
    for key in union("words_per_item_by_kind"):
        base_n = num(get(b["vault"], "items_by_kind", key, default=0)) or 0
        add("Words of detail per item kind (mean words under each item heading)", f"{key}: words per item",
            lambda r, key=key: get(r["vault"], "words_per_item_by_kind", key, default=missing("no item of this kind"))
            if "missing" not in r["vault"] else missing(r["vault"]["missing"]), better="higher",
            kind="detail" if base_n >= 3 else "info")
    return rows


def flips(b, m):
    bi = get(b["scorecard"], "items", default={})
    mi = get(m["scorecard"], "items", default={})
    if is_missing(bi) or is_missing(mi):
        return missing("a scorecard is missing")
    return {"lost": sorted(i for i, v in bi.items() if v and not mi.get(i)),
            "gained": sorted(i for i, v in mi.items() if v and not bi.get(i))}


def like_with_like(b, m):
    notes = []
    bs, ms = b["sessions"], m["sessions"]
    if "missing" in bs or "missing" in ms:
        return ["session lists missing, so the runs can't be lined up"]
    bp = {s["session"]: s for s in bs["per_session"]}
    mp = {s["session"]: s for s in ms["per_session"]}
    only_b = sorted(set(bp) - set(mp))
    only_m = sorted(set(mp) - set(bp))
    if only_b:
        notes.append(f"sessions {only_b} ran in the baseline only, so vault and transcript counts are not like with like")
    if only_m:
        notes.append(f"sessions {only_m} ran in the mid-point only, so vault and transcript counts are not like with like")
    differ = [i for i in set(bp) & set(mp) if bp[i]["ended"] != mp[i]["ended"]]
    if differ:
        notes.append(f"sessions {sorted(differ)} ended differently in the two runs")
    return notes


def plan_gate_rows(rows, b, m):
    """Which rows of the plan's mid-point gate table (8.3) the numbers match. Shown beside the verdict."""
    flat = {r["measure"]: r for group in rows.values() for r in group}
    out = []
    plan_detail = ["Captures in session records", "Items written", "Question ledger rows", "Unknowns with an Ask line"]
    drops = [k for k in plan_detail if flat.get(k, {}).get("status") == "thinned"]
    leak = flat.get("Leaks per lead-facing turn", {})
    leaks_down = leak.get("status") == "better"
    if drops:
        out.append(f"Detail count more than 10% below baseline ({', '.join(drops)}): the plan says stop, read the "
                   "transcripts for where detail was lost, fix inside wave 1's scope")
    if not drops and leaks_down:
        out.append("No plan detail count more than 10% down, and codes per lead-facing turn down: wave 2 as planned")
    if leak.get("status") in ("same", "worse"):
        out.append("Codes and IDs per lead-facing turn not down: find in the transcript whether they come from relayed "
                   "output or the model's own wording before more --for-lead work")
    skipped = num(get(m["close"], "skipped_steps")) if "missing" not in m["close"] else None
    if skipped is not None and skipped > 0:
        out.append(f"Close steps still skipped after their mechanics moved ({int(skipped)} in the mid-point): the plan says "
                   "rethink before building decision files, and write what was seen into the fix ledger")
    elif skipped == 0:
        out.append("Close steps no longer skipped in the mid-point (grill and epics steps are not measured here)")
    return out


def verdict(rows, b, m):
    flat = [r for group in rows.values() for r in group]
    thinned = [f"{r['measure'].strip()} ({show(r['baseline'])} → {show(r['midpoint'])}, {r['read']})"
               for r in flat if r["kind"] == "detail" and r["status"] == "thinned"]
    worse = [f"{r['measure'].strip()} ({show(r['baseline'])} → {show(r['midpoint'])})"
             for r in flat if r["kind"] == "reliability" and r["status"] == "worse"]
    unread = sorted({r["measure"].strip() for r in flat if r["kind"] in ("detail", "reliability") and r["status"] == "missing"})
    core_worse = [w for w in worse if w.startswith(("Steps skipped", "Pushes without consent"))]
    if core_worse or (thinned and worse):
        word = "STOP"
        why = ("what wave 1 moved into code got worse: " + "; ".join(core_worse)) if core_worse else \
              "detail thinned and reliability got worse at once"
    elif thinned or worse:
        word = "ADJUST"
        why = "; ".join(filter(None, ["thinned: " + "; ".join(thinned) if thinned else "",
                                      "reliability worse: " + "; ".join(worse) if worse else ""]))
    else:
        word = "GO"
        why = "no detail count fell more than the threshold, and no reliability figure got worse"
    provisional = []
    if unread:
        provisional.append(f"{len(unread)} detail or reliability figures could not be read in one run or both: "
                           + ", ".join(unread[:12]) + (" ..." if len(unread) > 12 else ""))
    mismatch = [n for n in like_with_like(b, m) if "not like with like" in n]
    if mismatch:
        provisional.insert(0, "NOT LIKE WITH LIKE: " + "; ".join(mismatch) + ". The deltas mostly measure how far each "
                           "run got, not the skills; compare again when both have run the same sessions")
    for r, name in ((b, "baseline"), (m, "mid-point")):
        if not r["finished"]:
            provisional.append(f"the {name} run is not finished")
        if not r.get("vault_shared", True):
            provisional.append(f"the {name} run's final vault is its working tree, not origin/main (see its notes)")
    return {"verdict": word, "why": why, "thinned": thinned, "reliability_worse": worse, "provisional": provisional}


# ------------------------------------------------------------------ output

def md_table(group_rows):
    lines = ["| Measure | Baseline | Mid-point | Delta | Read |", "|---|---|---|---|---|"]
    for r in group_rows:
        delta = r["delta"] if r["delta"] == "n/a" else (f"{r['delta']:+}" if isinstance(r["delta"], (int, float)) else r["delta"])
        if r.get("change") is not None and r["delta"] not in ("n/a", 0):
            delta += f" ({r['change']:+.0%})"
        cells = [r["measure"].replace("  ", "&nbsp;&nbsp;"), show(r["baseline"]), show(r["midpoint"]), delta, r.get("read", "")]
        lines.append("| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |")
    return lines


def render_md(report):
    b, m, v = report["baseline"], report["midpoint"], report["verdict"]
    lines = [f"# Mid-point comparison: {b['run_id']} vs {m['run_id']}", "",
             "The question (overhaul plan 8.1): did the slimmer wave-1 skills keep sessions as detailed, and did "
             "reliability improve?", "",
             f"## Verdict: {v['verdict']}" + (" (provisional)" if v["provisional"] else ""), "", v["why"] + ".", ""]
    if v["provisional"]:
        lines += ["Provisional, because:"] + [f"- {p}" for p in v["provisional"]] + [""]
    lines += ["The plan's own gate table (8.3) reads these rows:"] + [f"- {p}" for p in report["plan_gate"]] + [""]
    lines += ["## The runs", "", "| | Baseline | Mid-point |", "|---|---|---|"]
    for key in ("run_dir", "checkout", "script", "arm", "finished", "vault_scored", "vault_working_tree"):
        lines.append(f"| {key} | {show(b.get(key))} | {show(m.get(key))} |")
    lines.append("")
    for name, r in (("Baseline", b), ("Mid-point", m)):
        if r["notes"]:
            lines += [f"{name} notes:"] + [f"- {n}" for n in r["notes"]] + [""]
    if report["like_with_like"]:
        lines += ["**Not like with like:**"] + [f"- {n}" for n in report["like_with_like"]] + [""]
    for group, rows in report["rows"].items():
        lines += [f"## {group}", ""]
        if group == "Final vault":
            lines += [f"Scored: the baseline's {b['vault_scored']} (its working tree: {b['vault_working_tree']}); the "
                      f"mid-point's {m['vault_scored']} (its working tree: {m['vault_working_tree']}).", ""]
        lines += md_table(rows) + [""]
        if group.startswith("Scorecard"):
            f = report["flips"]
            lines += ([f"- Brief items: {show(f)}"] if is_missing(f) else
                      [f"- Brief items yes in the baseline and no in the mid-point: {', '.join(f['lost']) or 'none'}",
                       f"- Brief items yes in the mid-point only: {', '.join(f['gained']) or 'none'}"]) + [""]
        if group.startswith("Skipped"):
            for name, r in (("Baseline", report["detail"]["baseline"]), ("Mid-point", report["detail"]["midpoint"])):
                c = r["close"]
                if "missing" in c:
                    continue
                lines.append(f"- {name} close skill asks for: {', '.join(c['expected_steps'])}")
                for x in c["per_close"]:
                    if x["missing_steps"]:
                        lines.append(f"  - S{x['session']} ({x['ended']}{', nothing open' if x['nothing_open'] else ''}): "
                                     f"{x['counted_as']}: {', '.join(x['missing_steps'])}")
            lines.append("")
        if group == TEAM_GROUP:
            for name, r in (("Baseline", report["detail"]["baseline"]), ("Mid-point", report["detail"]["midpoint"])):
                found = r["vault"].get("team_docs_from") or {}
                lines.append(f"- {name} team documents: " + ("; ".join(f"{p} ({ref})" for p, ref in found.items())
                                                             or "none on origin/main or an unmerged branch"))
            lines.append("")
        if group.startswith("Wrong"):
            for name, r in (("Baseline", report["detail"]["baseline"]), ("Mid-point", report["detail"]["midpoint"])):
                c = r["ids"]
                if "missing" in c:
                    continue
                if c["guessed_list"]:
                    lines.append(f"- {name} IDs said with no definition (turns): " + "; ".join(
                        f"{i} (T{', T'.join(map(str, t))})" for i, t in c["guessed_list"].items()))
                if c.get("known_from_documents_list"):
                    lines.append(f"- {name} IDs said from the vault's own documents, not counted as guessed: "
                                 + ", ".join(c["known_from_documents_list"]))
                if c["ids_with_more_than_one_name_list"]:
                    lines.append(f"- {name} IDs with more than one name: " + "; ".join(
                        f"{i}: {' / '.join(n)}" for i, n in c["ids_with_more_than_one_name_list"].items()))
            lines.append("")
        if group.startswith("Consent"):
            for name, r in (("Baseline", report["detail"]["baseline"]), ("Mid-point", report["detail"]["midpoint"])):
                c = r["consent"]
                if "missing" not in c and c["without_consent"]:
                    lines.append(f"- {name} pushes with no consent found: "
                                 + ", ".join(f"T{x['turn']} (S{x['session']})" for x in c["without_consent"]))
            lines.append("")
        if group.startswith("Codes"):
            for name, r in (("Baseline", report["detail"]["baseline"]), ("Mid-point", report["detail"]["midpoint"])):
                c = r["voice"]
                if "missing" not in c and c["worst_turns"]:
                    lines.append(f"- {name} worst turns: " + "; ".join(
                        f"T{w['turn']} {w['count']} ({', '.join(w['sample'])})" for w in c["worst_turns"]))
            lines.append("")
    lines += ["## Per session", "", "| Session | Mode | Baseline ended | Baseline turns | Mid-point ended | Mid-point turns |",
              "|---|---|---|---|---|---|"]
    bp = {s["session"]: s for s in get(report["detail"]["baseline"]["sessions"], "per_session", default=[]) or []} \
        if "missing" not in report["detail"]["baseline"]["sessions"] else {}
    mp = {s["session"]: s for s in get(report["detail"]["midpoint"]["sessions"], "per_session", default=[]) or []} \
        if "missing" not in report["detail"]["midpoint"]["sessions"] else {}
    for i in sorted(set(bp) | set(mp)):
        x, y = bp.get(i, {}), mp.get(i, {})
        lines.append(f"| {i} | {x.get('mode') or y.get('mode')} | {x.get('ended', 'not run')} | {x.get('assistant_turns', '')} | "
                     f"{y.get('ended', 'not run')} | {y.get('assistant_turns', '')} |")
    lines += ["", "How each figure is read is in tests/sim/README.md, \"Compare two runs\". Heuristic figures (skipped steps, consent, "
              "guessed IDs, leaks) list their turns so you can read the transcript before you believe them.", ""]
    return "\n".join(lines)


def measure(label, run_dir, arm, checkout, notes=()):
    run = Run(label, run_dir, arm, checkout)
    run.notes[:0] = list(notes)
    with tempfile.TemporaryDirectory(prefix="compare-runs-") as workdir:
        scored = scoring_copy(run, pathlib.Path(workdir))
        vault = vault_section(run, scored)
        cli = cli_section(run, scored.path)
        ids = ids_section(run, scored, vault, cli)
    data = {"sessions": sessions_section(run), "scorecard": scorecard_section(run), "voice": voice_section(run),
            "close": close_section(run), "consent": consent_section(run), "vault": vault, "cli": cli,
            "ids": ids, "finished": run.finished, "vault_shared": scored.shared}
    info = {"run_id": run_dir.name, "run_dir": str(run_dir), "checkout": str(checkout), "arm": arm,
            "script": run.run_json.get("script") if not is_missing(run.run_json) else run.run_json,
            "finished": run.finished, "vault_scored": scored.ref, "vault_working_tree": scored.working_tree,
            "notes": run.notes}
    return data, info


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("runs", nargs="*", type=pathlib.Path, metavar="RUN",
                   help="the baseline run folder, then the later one (the same as --baseline and --midpoint)")
    p.add_argument("--baseline", type=pathlib.Path, help="baseline run folder (default: newest in /tmp/baseline-wt)")
    p.add_argument("--midpoint", type=pathlib.Path, help="mid-point run folder (default: newest in /tmp/midpoint-wt)")
    p.add_argument("--baseline-checkout", type=pathlib.Path)
    p.add_argument("--midpoint-checkout", type=pathlib.Path)
    p.add_argument("--arm", default="vela", help="today's arm name; an older run's folder is found through LEGACY_NAMES")
    p.add_argument("--threshold", type=float, default=THRESHOLD, help="share a detail count may fall before it reads as thinned")
    p.add_argument("--json", type=pathlib.Path, help="where to write the JSON report")
    args = p.parse_args(argv)
    if len(args.runs) > 2 or (args.runs and (args.baseline or (len(args.runs) == 2 and args.midpoint))):
        p.error("give each run once: two run folders, or --baseline and --midpoint")
    args.baseline = args.baseline or (args.runs[0] if args.runs else None)
    args.midpoint = args.midpoint or (args.runs[1] if len(args.runs) == 2 else None)
    return args


def own_repo():
    """The repo this file sits in (tests/sim/compare_runs.py), or None for a copy outside one."""
    repo = pathlib.Path(__file__).resolve().parents[2]
    return repo if has_plugin(repo) else None


def checkout_for(given, run_dir, notes):
    """The checkout whose plugin and scripts measure a run: the one given, the one the run folder sits in, or this
    repo, said in the notes, because another checkout's CLI is another ruler for Completeness and check."""
    if given:
        return given.resolve()
    beside = run_dir.parents[3] if len(run_dir.parents) > 3 else None
    if beside and has_plugin(beside):
        return beside.resolve()
    repo = own_repo()
    if repo is None:
        return beside.resolve() if beside else run_dir
    notes.append(f"the run folder isn't inside a checkout, so {repo}'s plugin and scripts measure it; give "
                 "--baseline-checkout or --midpoint-checkout for the checkout that ran it")
    return repo


def main(argv=None):
    args = parse_args(argv)
    dirs, arms, notes = {}, {}, {}
    for label in ("baseline", "midpoint"):
        given = getattr(args, label)
        found = given.resolve() if given else newest_run(DEFAULT_ROOTS[label])
        arm = stored_arm(found, args.arm) if found else None
        if arm is None:
            print(f"compare: no {label} run folder with an '{args.arm}' arm, or its name before the rename "
                  f"({given or DEFAULT_ROOTS[label]})", file=sys.stderr)
            return 2
        dirs[label], arms[label], notes[label] = found, arm, []
        if arm != args.arm:
            notes[label].append(f"the arm is stored as {arm!r}, its name before the rename; LEGACY_NAMES pairs it "
                                f"with {args.arm!r}")
    checkouts = {label: checkout_for(getattr(args, f"{label}_checkout"), dirs[label], notes[label]) for label in dirs}
    measured = {label: measure(label, dirs[label], arms[label], checkouts[label], notes[label]) for label in dirs}
    b, m = measured["baseline"][0], measured["midpoint"][0]
    rows = compare(b, m, args.threshold)
    report = {"baseline": measured["baseline"][1], "midpoint": measured["midpoint"][1], "threshold": args.threshold,
              "verdict": verdict(rows, b, m), "plan_gate": plan_gate_rows(rows, b, m), "like_with_like": like_with_like(b, m),
              "flips": flips(b, m), "rows": rows,
              "detail": {"baseline": {k: v for k, v in b.items() if k != "vault"} | {"vault": strip(b["vault"])},
                         "midpoint": {k: v for k, v in m.items() if k != "vault"} | {"vault": strip(m["vault"])}}}
    out = args.json or pathlib.Path(tempfile.gettempdir()) / f"compare-{dirs['baseline'].name}-vs-{dirs['midpoint'].name}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(render_md(report))
    print(f"JSON: {out.resolve()}", file=sys.stderr)
    return {"GO": 0, "ADJUST": 1, "STOP": 3}[report["verdict"]["verdict"]]


def strip(vault):
    return {k: v for k, v in vault.items() if not k.startswith("_")}


if __name__ == "__main__":
    sys.exit(main())
