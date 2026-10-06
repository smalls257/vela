#!/usr/bin/env python3
"""Probe one capability of the planner skills in a single simulated session, from a saved vault snapshot, and
check it with mostly mechanical criteria. A full run.py run is 12 sessions and about $36 to $55; a probe is one
session and about $1 to $3, so a controller can edit a skill, probe it, and read the result in a loop.

Everything a session needs comes from run.py, imported, not copied: the claude calls and their isolation flags,
the sandbox, the persona and its prompt, the gh stub, the transcript and its HTML, the per-run budget. What is new
here is the starting vault (a snapshot, with the current plugin installed over it), the criteria, blind output
and the loop ledger.

This costs money unless --stub is given: every assistant, persona and judge call is a real `claude -p` call.

Usage:
  python3 tests/sim/probe.py <case> --persona <name> --runs N --model <id> --persona-model <id>
                             --judge-model <id> --budget <usd> --loop-ledger <path> --loop-budget <usd>
                             [--blind] [--stub] [--out <dir>]

<case> is a name in tests/sim/probes/ or a .yaml path. <name> is a persona in tests/sim/personas/.
--budget is the ceiling for this invocation, split evenly over the runs. --loop-ledger is a JSON file that adds up
what every invocation spent; probe.py refuses to start when that total plus --budget would pass --loop-budget.
--blind prints categories and counts only, never an item ID, its text or its keywords, and writes the detail to
detail-DO-NOT-READ-WHEN-BLIND.md in each run folder. A persona with `holdout: true` is always blind.

Exit codes: 0 every run passed every criterion; 1 a run failed a criterion, a run ended on its budget, or the
loop ledger refused to start; 2 a tool failed (claude, git, a snapshot, a case or persona file, the judge's JSON).
"""
import argparse
import collections
import datetime
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import traceback

import yaml

HERE = pathlib.Path(__file__).resolve().parent


def _load_driver():
    """tests/sim/run.py, the driver every probe session runs through. Loaded by path under its own name, because a
    plain `import run` finds whichever `run` module was imported first, such as tests/evals/run.py."""
    name = "sim_run_driver"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, HERE / "run.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


sim = _load_driver()

ToolFailure = sim.ToolFailure
SNAPSHOTS = HERE / "snapshots"
PROBES = HERE / "probes"
PROBE_RESULTS = sim.RESULTS / "probes"
DETAIL_NAME = "detail-DO-NOT-READ-WHEN-BLIND.md"
EXCERPT = 200


# ------------------------------------------------------------------ persona, case, snapshot

def load_persona(ref):
    """The persona and whether it is blind. A holdout persona's problems are written to a file, never printed,
    because they name its items and keywords."""
    path = sim.resolve(ref, "personas")
    data = sim.load_yaml(path)
    holdout = isinstance(data, dict) and data.get("holdout") is True
    return path, data, holdout, sim.persona_problems(data)


CHECKS = {}  # name -> (function, the parameters it requires)


def check(name, *params):
    def register(fn):
        CHECKS[name] = (fn, params)
        return fn
    return register


def case_problems(case):
    if not isinstance(case, dict):
        return ["the case must be a mapping"]
    problems = []
    snapshots = case.get("snapshot")
    if not isinstance(snapshots, dict) or not snapshots:
        problems.append("'snapshot' must map each persona name to a snapshot name")
    else:
        for persona, name in snapshots.items():
            if not (SNAPSHOTS / str(persona) / str(name)).is_dir():
                problems.append(f"snapshot {persona}/{name} is not a folder in {SNAPSHOTS}")
    if not isinstance(case.get("opening"), str) or not case["opening"].startswith("/planner:"):
        problems.append("'opening' must be a /planner: command")
    elif case["opening"].split()[0].split(":", 1)[1] not in sim.MODES:
        problems.append(f"'opening' must start with one of /planner:{', /planner:'.join(sim.MODES)}")
    if not isinstance(case.get("cap"), int) or case["cap"] < 1:
        problems.append("'cap' must be a whole number of assistant turns, at least 1")
    if "close" in case and not (isinstance(case["close"], int) and not isinstance(case["close"], bool) and case["close"] >= 1):
        problems.append("'close' must be the close session's cap in assistant turns, at least 1, or left out")
    criteria = case.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        problems.append("'criteria' must be a non-empty list")
        return problems
    for n, criterion in enumerate(criteria, 1):
        name = criterion.get("check") if isinstance(criterion, dict) else None
        if name not in CHECKS:
            problems.append(f"criteria[{n}]: check {name!r} is not one of {', '.join(sorted(CHECKS))}")
            continue
        missing = [p for p in CHECKS[name][1] if p not in criterion]
        if missing:
            problems.append(f"criteria[{n}] {name}: needs {', '.join(missing)}")
        categories = criterion.get("categories") or ([criterion["category"]] if "category" in criterion else [])
        for category in categories:
            if category not in sim.CATEGORIES:
                problems.append(f"criteria[{n}] {name}: {category!r} is not a category")
    return problems


def load_case(ref):
    path = pathlib.Path(ref) if str(ref).endswith(".yaml") else PROBES / f"{ref}.yaml"
    case = sim.load_yaml(path)
    problems = case_problems(case)
    if problems:
        raise ToolFailure(f"{path} is not a valid probe case:\n  " + "\n  ".join(problems))
    case["name"] = path.stem
    case["mode"] = case["opening"].split()[0].split(":", 1)[1]
    return case


def opening_text(case, persona):
    """The case's opening with the persona's words put in: {opening}, {topics[...]} and {first_decision}."""
    try:
        return case["opening"].format(opening=" ".join(persona["opening"].split()), topics=persona.get("topics") or {},
                                      first_decision=persona["decisions"][0]["question"])
    except (KeyError, IndexError) as exc:
        raise ToolFailure(f"the case opening names {exc}, which the persona does not hold") from exc


def snapshot_dir(case, persona_name):
    name = (case.get("snapshot") or {}).get(persona_name)
    if not name:
        raise ToolFailure(f"case {case['name']} has no snapshot for persona {persona_name}")
    return SNAPSHOTS / persona_name / name


def inbox_problems(vault, persona):
    """The snapshot's .inbox must hold the persona's documents exactly as run.py writes them, or the probe tests
    a different brief from the one it scores against."""
    want = {d["name"]: d["text"].strip() + "\n" for d in persona.get("docs") or []}
    inbox = vault / ".inbox"
    have = {p.name: p.read_text(encoding="utf-8") for p in sorted(inbox.iterdir())} if inbox.is_dir() else {}
    return sorted(name for name in set(want) | set(have) if want.get(name) != have.get(name))


def build_probe_vault(run_dir, snapshot, persona):
    """The snapshot copied into the run, the current plugin installed over it, then git and origin as run.py does.
    A plugin inside the snapshot is removed first: the probe exists to test the skills as they are now."""
    vault, origin = run_dir / "vault", run_dir / "origin.git"
    shutil.copytree(snapshot, vault, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    label = snapshot.relative_to(SNAPSHOTS).as_posix() if snapshot.is_relative_to(SNAPSHOTS) else str(snapshot)
    notes = [f"vault copied from snapshot {label}"]
    skills = vault / ".claude" / "skills"
    if skills.exists():
        shutil.rmtree(skills)
        notes.append("the snapshot held .claude/skills; it was removed")
    shutil.copytree(sim.PLUGIN, skills / "planner", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    notes.append("current plugin/ installed at .claude/skills/planner")
    stale = inbox_problems(vault, persona)
    if stale:
        raise ToolFailure(f"the snapshot's .inbox does not match the persona's docs: {', '.join(stale)}")
    sim.git("init", "-q", "-b", "main", cwd=vault)
    sim.git("add", "-A", cwd=vault)
    sim.git("commit", "-q", "-m", f"Vault from snapshot {snapshot.name}", cwd=vault)
    sim.git("config", "user.name", "Sim Lead", cwd=vault)
    sim.git("config", "user.email", "sim-lead@example.invalid", cwd=vault)
    sim.git("init", "-q", "--bare", "-b", "main", str(origin), cwd=run_dir)
    sim.git("remote", "add", "origin", str(origin), cwd=vault)
    sim.git("push", "-q", "-u", "origin", "main", cwd=vault)
    check = subprocess.run([sys.executable, str(sim.PLANNER), "check", "--vault", str(vault)],
                           capture_output=True, text=True)
    (run_dir / "start-check.txt").write_text(f"exit {check.returncode}\n{check.stdout}{check.stderr}", encoding="utf-8")
    notes.append(f"planner check on the starting vault: exit {check.returncode}")
    return vault, notes


# ------------------------------------------------------------------ decisions, seen turn by turn

# A decision is a state set to decided, a table cell that says decided (a Changes row), or a Decision bullet. A
# capture's keep mark "(decided)" only points at a decision already made, at close: counting it read close's own
# record of a grilled decision as a second decision with no yes.
DECIDED = re.compile(r"^\s*state:\s*decided\b|\*\*State:\*\*\s*decided\b|\|\s*decided\s*\|"
                     r"|^\s*-\s*\*\*Decision:\*\*", re.I)
YES = re.compile(r"(?<![a-z])yes\b")


def decided_lines(vault):
    """Every vault line that records something as decided: a state, a table cell, a capture mark, a Decision
    bullet. Counted, so a second copy of the same line is a second decision."""
    return collections.Counter((rel, line.strip()) for rel, text in sim.vault_pages(vault)
                               for line in text.splitlines() if DECIDED.search(line))


def explicit_yes(lead_message, asked):
    """A decision counts as the lead's when the message that led to it says yes to a question the assistant put."""
    return bool(asked) and bool(YES.search(sim.normalise(lead_message)))


class ProbeLedger(sim.Ledger):
    """run.py's per-run ledger, with the judge's reserve only when the case calls the judge."""

    def __init__(self, share, reserve):
        super().__init__(share)
        self.reserve = reserve

    def session_room(self):
        return self.share * (1 - self.reserve) - self.spent


class ProbeRun(sim.Arm):
    """One probe run: run.py's Arm, started from a snapshot, watching the vault for decisions after every turn."""

    def __init__(self, folder, out, args, persona, share, snapshot, reserve):
        super().__init__(folder, out, args, persona, share)
        self.ledger = ProbeLedger(share, reserve)
        self.snapshot = snapshot
        self.decisions = []
        self.seen = collections.Counter()
        self.options = None

    def start(self):
        self.vault, self.notes = build_probe_vault(self.dir, self.snapshot, self.persona)
        self.seen = decided_lines(self.vault)
        for note in self.notes:
            self.transcript.add(speaker="driver", session=0, mode="setup", event="setup", text=note)

    def assistant_turn(self, message, session_id):
        parsed, result = super().assistant_turn(message, session_id)
        turn = self.transcript.turn + 1  # the turn number the transcript is about to give this reply
        previous = next((e["text"] for e in reversed(self.transcript.spoken()) if e["speaker"] == "assistant"), "")
        now = decided_lines(self.vault)
        for (rel, line), count in (now - self.seen).items():
            for _ in range(count):
                self.decisions.append({"turn": turn, "file": rel, "line": line,
                                       "with_yes": explicit_yes(message, "?" in previous)})
        self.seen = now
        return parsed, result


# ------------------------------------------------------------------ flag detection

LIST_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)]|\|)\s")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
CUE = re.compile(r"\bconflict|\bmismatch|\bdiffer(?:s|ed|ing|ence|ences)?\b|\bdisagree|\bclash|\bcontradict"
                 r"|\bboth sources\b|\btwo different\b|\b(?:doesnt|does not|dont|do not) match\b|\binconsisten"
                 r"|\bflag|\bsame job\b|\btwo systems\b|\bduplicat|\boverlap"
                 r"|\bno source\b|\bno line\b|\bnowhere\b|\bno place\b|\bhas anywhere\b|\bcan ?not follow\b|\bcant follow\b")
# "SeaBook is 99.9%, right?" asks for a yes, not about a conflict, so a bare confirmation tag is not a question
# that flags anything. Without this, a read-back list with "right?" on every line would flag every item on it.
CONFIRM_TAIL = re.compile(r"(?:^|[,;:(]\s*|\s[-–—]\s*)(?:is (?:that|this|it) (?:right|correct)|(?:that|this) (?:right|correct)"
                          r"|right|correct|yes|yes or no|yes/no|ok|okay|agreed|confirm(?:ed)?|true)\s*\)?\s*\?$")


def units(text):
    """Each sentence of an assistant turn, with the bullet or table row it sits in. A list line is one container,
    so a cue anywhere on the line counts for every sentence on it."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        listed = bool(LIST_LINE.match(line))
        for sentence in SENTENCE_END.split(stripped):
            if sentence.strip():
                yield sentence, (stripped if listed else sentence), listed


def is_question(sentence):
    flat = sim.normalise(sentence).rstrip(" )]")
    return flat.endswith("?") and not CONFIRM_TAIL.search(flat)


def has_cue(text):
    return bool(CUE.search(sim.normalise(text)))


def excerpt(text, keyword, limit=EXCERPT):
    flat = " ".join(text.split())
    at = flat.lower().find(keyword.lower())
    start = max(0, (at if at >= 0 else 0) - limit // 3)
    piece = flat[start:start + limit]
    return ("…" if start else "") + piece + ("…" if start + limit < len(flat) else "")


SPOT_HEADING = re.compile(r"^### ((?:UNK|R)-\d+)\b.*$", re.M)
SPOT_CAPTURE = re.compile(r"^- \[(?:unknown|worry)\].*$", re.M)
ANY_HEADING = re.compile(r"^#{1,3} ", re.M)


def flag_spots(pages):
    """Where a vault records an unknown or a risk: a ### UNK- or ### R- section, or an [unknown] or [worry]
    capture in a session record, which is where a session that has not closed yet keeps them."""
    spots = {}
    for rel, text in pages:
        for match in SPOT_HEADING.finditer(text):
            after = ANY_HEADING.search(text, match.end())
            spots[(rel, match.group(1))] = text[match.start():after.start() if after else len(text)]
        for match in SPOT_CAPTURE.finditer(text):
            spots[(rel, match.group(0))] = match.group(0)
    return spots


def vault_flagged(keywords, final_spots, start_spots):
    """The keywords the session put into an unknown or a risk. A keyword the snapshot already held in the same
    spot does not count: the probe scores what this session did."""
    found = {}
    for key, text in final_spots.items():
        before = start_spots.get(key, "")
        for word in sim.mentions(text, keywords):
            if not sim.mentions(before, [word]):
                found.setdefault(word, (key[0], text))
    return found


def item_flags(item, spoken, final_spots, start_spots):
    """FLAGGED, LISTED or NEVER for one brief item, with the turn and an excerpt that decided it."""
    in_vault = vault_flagged(item["keywords"], final_spots, start_spots)
    first_listed, flagged = None, None
    for entry in (e for e in spoken if e["speaker"] == "assistant"):
        for sentence, container, listed in units(entry["text"]):
            for word in sim.mentions(sentence, item["keywords"]):
                how = ("question" if is_question(sentence) else "cue" if has_cue(container)
                       else "vault" if word in in_vault else None)
                hit = {"turn": entry["turn"], "keyword": word, "how": how, "in_list": listed,
                       "excerpt": excerpt(container, word)}
                if how and flagged is None:
                    flagged = hit
                    if how == "vault":
                        rel, text = in_vault[word]
                        hit["vault"] = {"file": rel, "excerpt": excerpt(text, word)}
                if first_listed is None:
                    first_listed = hit
    status = "flagged" if flagged else "listed" if first_listed else "never"
    return {"id": item["id"], "category": item["category"], "status": status, "hit": flagged or first_listed}


def brief_items(persona, categories=None):
    return [item for kind in sim.ID_KINDS for item in persona.get(kind) or []
            if categories is None or item["category"] in categories]


# ------------------------------------------------------------------ shape options

OPTION_MARK = re.compile(
    r"^\s{0,3}(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)?(?:\*\*|__)?\s*option\s+(?P<a>[a-d1-4]|one|two|three|four)\b"
    r"|^\s{0,3}(?:#{1,6}\s+(?:\*\*)?|\*\*)(?P<b>[A-D1-4])[.):](?:\*\*)?\s", re.I)
PART_LABEL = re.compile(r"^\s*(?:\*\*|__)?(?:what it does|does|costs?|rules? out|ruled out|trade-?offs?|who|stakeholders?"
                        r"|owners?|unknowns?|risks?|pros?|cons?|effort|time|needs|depends on|why)\b", re.I)
WORDS = {"one": "1", "two": "2", "three": "3", "four": "4"}
COST_CUE = re.compile(r"\bcosts?\b|\bcosting\b|\beffort\b|\bexpensive\b|\bcheap|\bprice\b|\bspend\b|£|\$|\bbudget\b")
RULES_OUT_CUE = re.compile(r"\brules? out\b|\bruled out\b|\bruling out\b|\bpreclud|\bforeclos|\bcloses off\b"
                           r"|\bgives up\b|\boff the table\b|\bno longer possible\b")
UNKNOWN_CUE = re.compile(r"\bunk-\d+|\bunknowns?\b|\bopen question\b")
ROLE_CUE = re.compile(r"\b(?:ceo|cfo|cio|coo|dpo|director|officer|controller|guardian|board|committee|procurement"
                      r"|auditors?|regulator|unions?|healthwatch|clinicians?|commissioners?)\b")
PARTS = ("costs", "rules_out", "stakeholder_or_unknown")


def option_blocks(text):
    """The options one turn offers, by label, read from headings and bold or "Option X" labels. A label seen twice
    ends the options: "Option A is my pick" after the list is not a fifth option."""
    lines, blocks, current = text.splitlines(), [], None
    for n, line in enumerate(lines):
        mark = OPTION_MARK.match(line)
        label = None
        if mark:
            raw = (mark.group("a") or mark.group("b")).lower()
            label = WORDS.get(raw, raw).upper()
        if label and label in [b["label"] for b in blocks]:
            break
        if label:
            current = {"label": label, "lines": [line]}
            blocks.append(current)
        elif current is not None:
            current["lines"].append(line)
    if blocks:
        last, kept, blank = blocks[-1]["lines"], [], False
        for line in last:
            if not line.strip():
                blank = True
                kept.append(line)
                continue
            if kept and (line.startswith("#") or line.strip() in ("---", "***")):
                break
            if blank and not (LIST_LINE.match(line) or line.startswith((" ", "\t")) or PART_LABEL.match(line)):
                break
            blank = False
            kept.append(line)
        blocks[-1]["lines"] = kept
    return [{"label": b["label"], "text": "\n".join(b["lines"]).strip()} for b in blocks]


def stakeholder_terms(persona):
    terms = {sim.normalise(c["who"]) for c in persona.get("conflicts") or []}
    for item in persona.get("knows") or []:
        for part in re.split(r"[;,]", str(item.get("owner") or "")):
            if len(sim.normalise(part)) >= 3 and "nobody" not in part:
                terms.add(sim.normalise(part))
    return sorted(terms)


def mechanical_parts(block, terms):
    flat = sim.normalise(block)
    return {"costs": bool(COST_CUE.search(flat)), "rules_out": bool(RULES_OUT_CUE.search(flat)),
            "stakeholder_or_unknown": bool(UNKNOWN_CUE.search(flat) or ROLE_CUE.search(flat)
                                           or any(t in flat for t in terms))}


def options_turn(spoken):
    """The first assistant turn with two or more labelled options, else the first that talks about options."""
    assistant = [e for e in spoken if e["speaker"] == "assistant"]
    for entry in assistant:
        if len(option_blocks(entry["text"])) >= 2:
            return entry, option_blocks(entry["text"])
    for entry in assistant:
        if re.search(r"\boptions?\b", sim.normalise(entry["text"])):
            return entry, []
    return None, []


OPTIONS_JUDGE = """SIMULATOR JUDGE: options. You check the options that one assistant turn of a planning session offered.
You are mechanical, not a critic. You have no tools. Reply with one JSON object and nothing else: no prose, no fences.

For each option write "search" first: one sentence on what you read. Then, for each part, "present" true or false
and a "quote" copied exactly from the turn, at most 20 words. A part marked present without an exact quote is
dropped by the driver. If you are unsure, answer false.
- costs: what choosing it costs: money, time, effort, people, or a risk taken on.
- rules_out: what choosing it rules out, closes off or gives up.
- stakeholder_or_unknown: it names at least one stakeholder, owner, team or open unknown that bears on it.
{labels_rule}

The JSON shape:
{{"search": "...", "options": [{{"label": "A", "search": "...", "label_quote": "...",
  "costs": {{"present": true, "quote": "..."}}, "rules_out": {{"present": false, "quote": null}},
  "stakeholder_or_unknown": {{"present": true, "quote": "..."}}}}]}}
"""


def options_judge_problems(data, labels):
    if not isinstance(data, dict) or not isinstance(data.get("options"), list):
        return ["the reply must be an object with an 'options' list"]
    problems = []
    got = [o.get("label") for o in data["options"] if isinstance(o, dict)]
    if labels and sorted(map(str, got)) != sorted(labels):
        problems.append(f"'options' must list exactly the labels {', '.join(labels)}; got {got}")
    for option in data["options"]:
        if not isinstance(option, dict):
            problems.append("every option must be an object")
            continue
        for part in PARTS:
            value = option.get(part)
            if not isinstance(value, dict) or not isinstance(value.get("present"), bool):
                problems.append(f"option {option.get('label')}: '{part}' must be {{\"present\": bool, \"quote\": ...}}")
    return problems


def ask_options_judge(run, entry, blocks):
    """One small call for what the labels and cue words could not settle. Its "present" counts only with a quote
    that is really in the turn, so a careless judge can fail an option but never pass one."""
    labels = [b["label"] for b in blocks]
    rule = ("- The driver found these options by their labels. Answer for exactly these labels, once each."
            if labels else "- Find the options yourself. Give each a short label and a label_quote that starts it.")
    prompt = OPTIONS_JUDGE.format(labels_rule=rule)
    stdin = "".join(f"LABEL: {b['label']}\n" for b in blocks) + f"\nTHE TURN (T{entry['turn']}):\n{entry['text']}\n"
    problems = []
    for attempt in (1, 2):
        room = run.ledger.judge_room()
        if room < sim.MIN_CALL_USD:
            raise ToolFailure("no budget left for the options judge call")
        raw = run.raw("judge-options")
        text = stdin if attempt == 1 else stdin + "\n\nYOUR LAST REPLY WAS REJECTED:\n- " + "\n- ".join(problems)
        done = sim.call(sim.text_call_argv(run.args.judge_model, prompt, room), env=run.env,
                        cwd=run.dir / "persona-cwd", raw_path=raw, kind="judge", stdin=text)
        result = sim.parse_single(done.stdout, raw)
        run.ledger.add(float(result["total_cost_usd"]))
        run.judge_calls.append({"category": "options", "attempt": attempt, "raw": raw.name,
                                "cost_usd": result["total_cost_usd"]})
        if result["is_error"]:
            raise ToolFailure(f"the options judge call reported an error ({result.get('subtype')}). Read {raw}")
        try:
            data = json.loads(sim.strip_fences(result["result"]))
        except json.JSONDecodeError as exc:
            problems = [f"the reply is not JSON: {exc}"]
            continue
        problems = options_judge_problems(data, labels)
        if not problems:
            return data
    raise ToolFailure("the options judge's JSON was bad twice: " + "; ".join(problems))


def quoted(quote, text):
    return isinstance(quote, str) and bool(sim.normalise(quote)) and sim.normalise(quote) in sim.normalise(text)


def analyse_options(run):
    """The options the shape turn offered and, per option, which parts it names and how that was known."""
    if run.options is not None:
        return run.options
    entry, blocks = options_turn(run.transcript.spoken())
    if entry is None:
        run.options = {"turn": None, "options": [], "judged": False, "source": "none"}
        return run.options
    terms = stakeholder_terms(run.persona)
    options = []
    for block in blocks:
        parts = mechanical_parts(block["text"], terms)
        options.append({"label": block["label"], "text": block["text"], "parts": parts,
                        "how": {p: ("cue word" if parts[p] else None) for p in PARTS}})
    source, judged = ("labels" if options else "judge"), False
    if not options or not all(all(o["parts"].values()) for o in options):
        judged = True
        reply = ask_options_judge(run, entry, blocks)
        by_label = {str(o.get("label")): o for o in reply["options"]}
        if not options:
            options = [{"label": str(o.get("label")), "text": str(o.get("label_quote") or ""),
                        "parts": {p: False for p in PARTS}, "how": {p: None for p in PARTS}}
                       for o in reply["options"] if quoted(o.get("label_quote"), entry["text"])]
            by_label = {str(o.get("label")): o for o in reply["options"]}
        for option in options:
            verdict = by_label.get(option["label"], {})
            for part in PARTS:
                answer = verdict.get(part) or {}
                if not option["parts"][part] and answer.get("present") and quoted(answer.get("quote"), entry["text"]):
                    option["parts"][part] = True
                    option["how"][part] = f"judge: \"{answer['quote']}\""
    run.options = {"turn": entry["turn"], "options": options, "judged": judged, "source": source}
    return run.options


# ------------------------------------------------------------------ criteria
# Each returns (passed, summary, detail). The summary holds only categories and counts, so it is safe to print
# blind. The detail may hold item IDs, keywords and transcript text, and goes only where a blind run never prints.

def pct(share):
    return f"{share * 100:.0f}%"


@check("flagged-share", "category", "at_least")
def flagged_share(run, criterion):
    category = criterion["category"]
    pages = sim.vault_pages(run.vault)
    final, start = flag_spots(pages), flag_spots(sim.vault_pages(run.snapshot))
    rows = [item_flags(i, run.transcript.spoken(), final, start) for i in brief_items(run.persona, [category])]
    counts = collections.Counter(r["status"] for r in rows)
    share = counts["flagged"] / len(rows) if rows else 0.0
    passed = bool(rows) and share >= criterion["at_least"]
    summary = (f"{category}: {counts['flagged']} of {len(rows)} flagged, {counts['listed']} listed, "
               f"{counts['never']} never ({pct(share)}; need at least {pct(criterion['at_least'])})")
    detail = [flag_line(r) for r in rows]
    return passed, summary, detail


def flag_line(row):
    hit = row["hit"]
    if hit is None:
        return f"- {row['id']} ({row['category']}): NEVER"
    where = f"T{hit['turn']}, keyword {hit['keyword']!r}" + (" in a list line" if hit["in_list"] else "")
    how = {"question": "its sentence is a question", "cue": "its sentence or line has a flag cue",
           "vault": "the keyword is in an unknown or risk in the final vault"}.get(hit["how"], "no question, no cue")
    line = f"- {row['id']} ({row['category']}): {row['status'].upper()} at {where}; {how}. \"{hit['excerpt']}\""
    if hit.get("vault"):
        line += f" Vault, {hit['vault']['file']}: \"{hit['vault']['excerpt']}\""
    return line


@check("decided-without-yes", "at_most")
def decided_without_yes(run, criterion):
    bad = [d for d in run.decisions if not d["with_yes"]]
    passed = len(bad) <= criterion["at_most"]
    summary = (f"decided without an explicit yes: {len(bad)} (need at most {criterion['at_most']}); "
               f"decisions recorded in all: {len(run.decisions)}")
    return passed, summary, [decision_line(d) for d in run.decisions]


@check("decisions-recorded", "at_most")
def decisions_recorded(run, criterion):
    passed = len(run.decisions) <= criterion["at_most"]
    summary = f"decisions recorded: {len(run.decisions)} (need at most {criterion['at_most']})"
    return passed, summary, [decision_line(d) for d in run.decisions]


def decision_line(d):
    return f"- T{d['turn']} {d['file']}: {sim.short(d['line'])} ({'after a yes' if d['with_yes'] else 'no yes'})"


@check("questions-per-turn", "at_most")
def questions_per_turn(run, criterion):
    most = sim.max_questions(run.transcript)
    passed = most["count"] <= criterion["at_most"]
    where = f" (T{most['turn']})" if most["turn"] else ""
    return passed, f"most questions in one assistant turn: {most['count']}{where} (need at most {criterion['at_most']})", []


# Generic words for each kind of concern. A dump cannot name an item the lead has never heard of, only its kind, so a
# category counts as raised when the assistant names the kind (these cues) or the item (its keywords) before the lead
# does. The cues hold no persona's facts, so they cannot leak a brief into the skills.
CATEGORY_CUES = {
    "legal-regulatory": ["regulator", "regulation", "regulatory", "compliance", "legal basis", "lawful basis", "law ",
                         "licence", "license", "liable", "liability rule", "statutory"],
    "finance-liability": ["liabilit", "balance sheet", "who carries the cost", "who pays", "financial exposure",
                          "accounting", "finance team", "budget owner", "write-off", "write off"],
    "third-party-contract": ["contract", "supplier", "vendor", "partner agreement", "agreement with", "third part",
                             "outside part", "terms with"],
    "unnamed-stakeholder": ["who else", "nobody has named", "not named", "not been named", "affected team",
                            "stakeholder", "who is affected", "who would be affected"],
}


def first_turn(spoken, who, words):
    return min((e["turn"] for e in spoken if e["speaker"] == who and sim.mentions(e["text"], words)), default=None)


@check("categories-raised-first", "categories", "at_least")
def categories_raised_first(run, criterion):
    spoken = run.transcript.spoken()
    raised, detail = set(), []
    for category in criterion["categories"]:
        words = CATEGORY_CUES.get(category, []) + [k for i in brief_items(run.persona, [category]) for k in i["keywords"]]
        turns = {who: first_turn(spoken, who, words) for who in ("assistant", "lead")}
        if turns["assistant"] is not None and (turns["lead"] is None or turns["assistant"] < turns["lead"]):
            raised.add(category)
            text = next(e["text"] for e in spoken if e["turn"] == turns["assistant"])
            said = sim.mentions(text, words)
            detail.append(f"- category {category}: assistant first at T{turns['assistant']}. \"{excerpt(text, said[0])}\"")
    for item in brief_items(run.persona, criterion["categories"]):
        turns = {who: min((e["turn"] for e in spoken if e["speaker"] == who and sim.mentions(e["text"], item["keywords"])),
                          default=None) for who in ("assistant", "lead")}
        first = turns["assistant"] is not None and (turns["lead"] is None or turns["assistant"] < turns["lead"])
        if first:
            raised.add(item["category"])
        text = next((e["text"] for e in spoken if e["turn"] == turns["assistant"]), "")
        said = sim.mentions(text, item["keywords"])
        at = {who: f"T{turn}" if turn else "never" for who, turn in turns.items()}
        detail.append(f"- {item['id']} ({item['category']}): assistant first {at['assistant']}, lead first "
                      f"{at['lead']}; {'RAISED FIRST' if first else 'not raised first'}"
                      + (f". \"{excerpt(text, said[0])}\"" if said else ""))
    names = [c for c in criterion["categories"] if c in raised]
    passed = len(names) >= criterion["at_least"]
    summary = (f"categories raised first by the assistant: {len(names)} of {len(criterion['categories'])}"
               f" ({', '.join(names) or 'none'}; need at least {criterion['at_least']})")
    return passed, summary, detail


@check("option-count", "between")
def option_count(run, criterion):
    found = analyse_options(run)
    low, high = criterion["between"]
    n = len(found["options"])
    where = f" in T{found['turn']}" if found["turn"] else ""
    how = {"labels": "read from their labels", "judge": "found by the judge", "none": "no turn offered options"}
    summary = f"options offered: {n}{where}, {how[found['source']]} (need {low} to {high})"
    detail = [f"- option {o['label']}: \"{sim.short(' '.join(o['text'].split()), EXCERPT)}\"" for o in found["options"]]
    return low <= n <= high, summary, detail


@check("option-parts", "parts")
def option_parts(run, criterion):
    found = analyse_options(run)
    options = found["options"]
    counts = {p: sum(1 for o in options if o["parts"][p]) for p in criterion["parts"]}
    passed = bool(options) and all(c == len(options) for c in counts.values())
    summary = ("options naming each part: " + ", ".join(f"{p.replace('_', '-')} {c} of {len(options)}"
                                                        for p, c in counts.items())
               + f" (need every option to name every part; judge {'called' if found['judged'] else 'not needed'})")
    detail = [f"- option {o['label']}: " + "; ".join(f"{p} {o['how'][p] or 'missing'}" for p in criterion["parts"])
              for o in options]
    return passed, summary, detail


# ------------------------------------------------------------------ the question ledger and the reviewers

LEDGER_FLAGS = re.compile(r": (E801|E802|E803) ")


def planner_output(vault, *argv):
    """The output of the current plugin's planner on the final vault. A tool failure (exit 2) stops the probe."""
    done = subprocess.run([sys.executable, str(sim.PLANNER), *argv, "--vault", str(vault)], capture_output=True, text=True)
    if done.returncode == 2:
        raise ToolFailure(f"planner {argv[0]} failed on the final vault: {done.stdout.strip().splitlines()[:1]}")
    return done.stdout


@check("owed-copies-disposed", "severity")
def owed_copies_disposed(run, criterion):
    """Every owed copy of the severity (`high`, or `any`) has a ledger row that says more than open, and
    planner check flags no ledger row (E801, E802, E803): every owed copy has a valid disposition."""
    answer = json.loads(planner_output(run.vault, "questions", "--json"))
    severity = criterion["severity"]
    wanted = [c for c in answer["copies"] if severity == "any" or c["severity"] == severity]
    undisposed = [c for c in wanted if c["state"] in ("no row", "open")]
    flagged = [line for line in planner_output(run.vault, "check").splitlines() if LEDGER_FLAGS.search(line)]
    passed = bool(wanted) and not undisposed and not flagged
    summary = (f"owed copies ({severity}) with a disposition: {len(wanted) - len(undisposed)} of {len(wanted)}; "
               f"ledger rows planner check flags: {len(flagged)} (need every copy disposed and no flagged row)")
    detail = [f"- {c['id']}: {c['state']}" for c in undisposed] + [f"- {line}" for line in flagged]
    return passed, summary, detail


TAKE = re.compile(r"^- \[\w+\] \([^)]*\) (?P<id>Q-[A-Z]{3}-\d{2}@[A-Za-z0-9*-]+|F\d+\.\d+):.*?\^(?P<cid>c\d+)\s*$", re.M)
REVIEW_ROW = re.compile(r"^\| (?P<f>F\d+\.\d+) \| [A-Z]{3} \| \w+ \| (?P<copy>\S+) \| (?P<question>.*?) \| .* \|$", re.M)


def _flat(text):
    return " ".join(re.sub(r"[^\w ]", " ", text.lower()).split())


def _take_problem(answer, taken, findings):
    """Why a copy or finding the lead took has no valid row, or "" when it has one. A take may end in any state
    but `open`: answered, assumed, unknown, not-applicable, or asked when the lead sent it on."""
    copies = {c["id"]: c for c in answer["copies"]}
    if taken.startswith("F"):
        row = findings.get(taken)
        if row is None:
            return "no such finding in the record's ## Reviews"
        if row["copy"] == "new":
            mine = [r for r in answer["reviewer"] if _flat(r["question"] or "") == _flat(row["question"])]
            if not mine:
                return f'no reviewer row asks "{row["question"]}"'
            return "" if any(r["valid"] and r["state"] != "open" for r in mine) else f"{mine[0]['id']}: open"
        taken = row["copy"]
    if taken.endswith("*"):
        matched = [c for i, c in copies.items() if i.startswith(taken[:-1])]
    else:
        matched = [copies[taken]] if taken in copies else []
    if not matched:
        return "not an owed copy"
    bad = [c for c in matched if not c["valid"] or c["state"] in ("no row", "open")]
    return ", ".join(f"{c['id'] + ' ' if len(matched) > 1 else ''}{c['state'] if c['valid'] else 'invalid'}"
                     for c in bad)


@check("taken-copies-recorded")
def taken_copies_recorded(run, criterion):
    """Every copy or finding the lead took in a capture (its words start with the copy ID or the finding ID)
    has a valid row that says more than open. Copies the lead never took are not counted: they may stay open."""
    answer = json.loads(planner_output(run.vault, "questions", "--json"))
    detail, total = [], 0
    for rel, text in sim.vault_pages(run.vault):
        if not rel.startswith("sessions/"):
            continue
        findings = {m["f"]: m for m in REVIEW_ROW.finditer(text)}
        for m in TAKE.finditer(text):
            total += 1
            problem = _take_problem(answer, m["id"], findings)
            if problem:
                detail.append(f"- {rel} ^{m['cid']} {m['id']}: {problem}")
    summary = f"copies and findings the lead took in a capture with a valid row: {total - len(detail)} of {total}"
    return not detail, summary, detail


COVERAGE = re.compile(r"^- \*\*Coverage:\*\* (?P<line>.+)$", re.M)
AREA_RESULT = re.compile(r"\b(?P<area>[A-Z]{3}) (?P<status>found \d+(?:, \d+ dropped)?|checked, none|did not run \([^)]*\))")


def catalogue_areas():
    data = yaml.safe_load((sim.PLUGIN / "catalog" / "questions.yaml").read_text(encoding="utf-8"))
    return list(data["areas"])


@check("area-coverage", "require")
def area_coverage(run, criterion):
    """Every review checkpoint the session records gives each focus area one result: found N, checked,
    none, or did not run with its reason. `require: ran` also needs every area to have run."""
    areas = catalogue_areas()
    lines = [(rel, m["line"]) for rel, text in sim.vault_pages(run.vault) if rel.startswith("sessions/")
             for m in COVERAGE.finditer(text)]
    detail, good = [], 0
    for rel, line in lines:
        results = {m["area"]: m["status"] for m in AREA_RESULT.finditer(line)}
        missing = [a for a in areas if a not in results]
        failed = [a for a in areas if results.get(a, "").startswith("did not run")]
        ok = not missing and (criterion["require"] != "ran" or not failed)
        good += ok
        detail.append(f"- {rel}: {line}" + (f" (no result for {', '.join(missing)})" if missing else ""))
    passed = bool(lines) and good == len(lines)
    need = "every area to run" if criterion["require"] == "ran" else "every area to have a result"
    summary = f"review checkpoints recorded: {len(lines)}; with {need}: {good} of {len(lines)}"
    return passed, summary, detail


def score(run, case):
    rows = []
    for criterion in case["criteria"]:
        fn = CHECKS[criterion["check"]][0]
        passed, summary, detail = fn(run, criterion)
        rows.append({"check": criterion["check"], "passed": passed, "summary": summary, "detail": detail})
    return rows


# ------------------------------------------------------------------ the loop ledger

class LoopLedger:
    """What every probe invocation of one iteration loop has spent, kept in a JSON file. A missing file is an empty
    loop; a file that does not parse is a tool failure, never a fresh start, because a fresh start would forget
    real spend."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.data = {"spent_usd": 0.0, "invocations": []}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ToolFailure(f"the loop ledger {self.path} is not JSON: {exc}") from exc
            if not isinstance(data, dict) or not isinstance(data.get("spent_usd"), (int, float)) \
                    or not isinstance(data.get("invocations"), list):
                raise ToolFailure(f"the loop ledger {self.path} lacks spent_usd (number) and invocations (list)")
            self.data = data

    @property
    def spent(self):
        return float(self.data["spent_usd"])

    def record(self, entry):
        self.data["invocations"].append(entry)
        self.data["spent_usd"] = round(self.spent + entry["spent_usd"], 4)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        tmp.replace(self.path)


# ------------------------------------------------------------------ one run, and the output

def headline(message):
    """The part of a failure message before its first ': ', which names what failed without quoting any text."""
    return str(message).split(": ", 1)[0]


def run_once(case, persona, persona_name, args, n, stamp, share):
    folder = f"{stamp}-{case['name']}-{persona_name}-{n}"
    reserve = sim.JUDGE_RESERVE if any(c["check"].startswith("option-") for c in case["criteria"]) else 0.0
    run = ProbeRun(folder, pathlib.Path(args.out).resolve(), args, persona, share,
                   snapshot_dir(case, persona_name), reserve)
    run.rows, run.failure = [], None
    text = opening_text(case, persona)
    session = {"mode": case["mode"], "cap": case["cap"], "planner": text.replace("{", "{{").replace("}", "}}"),
               "baseline": text.replace("{", "{{").replace("}", "}}")}
    try:
        run.start()
        run.run_session(1, session)
        if case.get("close"):  # the ledger is written at close, so a case that reads it closes the session first
            run.run_session(2, {"mode": "close", "cap": case["close"], "planner": "/planner:close",
                                "baseline": "/planner:close"})
        run.rows = score(run, case)
    except ToolFailure as exc:
        run.failure = str(exc)
    except Exception as exc:  # a bug in the probe is a tool failure (exit 2), never a failed criterion (exit 1)
        (run.dir / "probe-traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        run.failure = f"probe error {type(exc).__name__}: {exc}. Read probe-traceback.txt"
    finally:
        sim.finish_arm(run)
    return run


def run_record(run, blind):
    endings = run.endings or [{"reason": "not run", "turns": 0}]
    budget = next((e for e in endings if e["reason"] == "budget"), None)
    ending = budget or endings[-1]
    return {"folder": run.dir.name, "blind": blind, "spent_usd": round(run.ledger.spent, 4),
            "ending": ending["reason"], "assistant_turns": sum(e["turns"] for e in endings),
            "failure": headline(run.failure) if (run.failure and blind) else run.failure,
            "passed": run.failure is None and ending["reason"] != "budget" and all(r["passed"] for r in run.rows),
            "criteria": [{"check": r["check"], "passed": r["passed"], "summary": r["summary"]} for r in run.rows]}


def write_outputs(run, case, persona_name, blind):
    record = run_record(run, blind)
    (run.dir / "probe.json").write_text(json.dumps({"case": case["name"], "persona": persona_name, **record},
                                                   indent=2), encoding="utf-8")
    lines = [f"# Probe {case['name']}, {persona_name}, {run.dir.name}", "",
             f"Ended: {record['ending']} after {record['assistant_turns']} assistant turns. Spent ${record['spent_usd']:.2f}.",
             f"Opening: {opening_text(case, run.persona)}", ""]
    if run.failure:
        lines += ["## Tool failure", "", run.failure, ""]
    for row in run.rows:
        lines += [f"## {'PASS' if row['passed'] else 'FAIL'} {row['check']}", "", row["summary"], ""] + row["detail"] + [""]
    if run.options:
        lines += ["## Options as read", ""] + [f"### Option {o['label']}\n\n{o['text']}\n" for o in run.options["options"]]
    (run.dir / DETAIL_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return record


def print_run(record, run, n, runs, blind):
    status = "PASS" if record["passed"] else "FAIL"
    print(f"run {n} of {runs}: {status}  ended {record['ending']} after {record['assistant_turns']} assistant turns, "
          f"spent ${record['spent_usd']:.2f}  {run.dir}")
    if run.failure:
        print(f"  TOOL FAILURE: {record['failure']}" + (f" (full message in {DETAIL_NAME})" if blind else ""))
    if record["ending"] == "budget":
        print("  BUDGET STOP: the session ended on its budget share, so the criteria below read a cut-off session")
    for row in run.rows:
        print(f"  {'PASS' if row['passed'] else 'FAIL'} {row['check']}: {row['summary']}")
        if not blind:
            for line in row["detail"]:
                print(f"      {line}")
    if blind:
        print(f"  blind: item detail is in {DETAIL_NAME} in the run folder; do not read it while iterating")


# ------------------------------------------------------------------ main

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("case", help="case name in tests/sim/probes/, or a .yaml path")
    parser.add_argument("--persona", required=True, help="persona name in tests/sim/personas/")
    parser.add_argument("--runs", type=int, default=1, help="how many runs of the case, one after another; default 1")
    parser.add_argument("--model", required=True, help="assistant model, pinned")
    parser.add_argument("--persona-model", required=True, help="persona model, pinned")
    parser.add_argument("--judge-model", required=True, help="judge model, pinned; only option checks call it")
    parser.add_argument("--budget", required=True, type=float, help="USD ceiling for this invocation, all runs")
    parser.add_argument("--loop-ledger", required=True, help="JSON file that adds up spend across invocations")
    parser.add_argument("--loop-budget", required=True, type=float, help="USD ceiling for the whole loop")
    parser.add_argument("--blind", action="store_true", help="print categories and counts only")
    parser.add_argument("--stub", action="store_true", help="use the scripted fake claude in tests/sim/stub/")
    parser.add_argument("--out", default=str(PROBE_RESULTS), help="results folder; each run gets its own folder")
    args = parser.parse_args(argv)
    for name in ("budget", "loop_budget"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be more than 0")
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    return args


def refuse_blind_problems(problems, out):
    """A blind persona's validation problems name its items, so they go to a file and only their count is shown."""
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.datetime.now():%Y-%m-%d-%H%M%S}-validation-{DETAIL_NAME}"
    path.write_text("\n".join(f"- {p}" for p in problems) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    sys.stdout.reconfigure(line_buffering=True)  # so the summary and the per-turn log on stderr interleave in order
    args = parse_args(argv)
    persona_name = pathlib.Path(args.persona).stem
    try:
        _, persona, holdout, problems = load_persona(args.persona)
        blind = args.blind or holdout
        if problems:
            if blind:
                path = refuse_blind_problems(problems, pathlib.Path(args.out))
                raise ToolFailure(f"the persona is not valid ({len(problems)} problems, listed in {path})")
            raise ToolFailure("the persona is not valid:\n  " + "\n  ".join(problems))
        case = load_case(args.case)
        snapshot_dir(case, persona_name)
        opening_text(case, persona)
        ledger = LoopLedger(args.loop_ledger)
    except ToolFailure as exc:
        print(f"probe: {exc}", file=sys.stderr)
        return 2
    if ledger.spent + args.budget > args.loop_budget + 1e-9:
        print(f"probe: refused to start. The loop has spent ${ledger.spent:.2f} of ${args.loop_budget:.2f}; this "
              f"invocation's --budget ${args.budget:.2f} would take it to ${ledger.spent + args.budget:.2f}.")
        return 1
    print(f"probe {case['name']}, persona {persona_name}, {args.runs} run(s), budget ${args.budget:.2f}"
          f"{', blind' if blind else ''}. Loop spend so far ${ledger.spent:.2f} of ${args.loop_budget:.2f}.")
    stamp = f"{datetime.datetime.now():%Y-%m-%d-%H%M%S}"
    share = args.budget / args.runs
    records, failed, current = [], False, None
    try:
        for n in range(1, args.runs + 1):
            current = None
            current = run_once(case, persona, persona_name, args, n, stamp, share)
            record = write_outputs(current, case, persona_name, blind)
            records.append(record)
            print_run(record, current, n, args.runs, blind)
            if current.failure:
                failed = True
                break
    except Exception as exc:  # a bug in the probe is a tool failure (exit 2), never a failed criterion (exit 1)
        failed = True
        print(f"probe: tool failure: {type(exc).__name__}" + ("" if blind else f": {exc}"), file=sys.stderr)
        if current is not None and len(records) < n:
            records.append({"folder": current.dir.name, "spent_usd": round(current.ledger.spent, 4), "passed": False})
    finally:
        spent = round(sum(r["spent_usd"] for r in records), 4)
        code = 2 if failed else 0 if all(r["passed"] for r in records) else 1
        ledger.record({"at": stamp, "case": case["name"], "persona": persona_name, "runs": len(records),
                       "budget_usd": args.budget, "spent_usd": spent, "stub": args.stub, "exit": code,
                       "folders": [r["folder"] for r in records]})
    passed = sum(1 for r in records if r["passed"])
    print(f"probe: {passed} of {len(records)} run(s) passed every criterion. Spent ${spent:.2f} of ${args.budget:.2f}; "
          f"loop spend now ${ledger.spent:.2f} of ${args.loop_budget:.2f}. Exit {code}.")
    return code


if __name__ == "__main__":
    sys.exit(main())
