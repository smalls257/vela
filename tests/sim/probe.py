#!/usr/bin/env python3
"""Probe one capability of the vela skills in a single simulated session, from a saved vault snapshot, and
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
                             [--blind] [--reveal] [--stub] [--out <dir>]

<case> is a name in tests/sim/probes/ or a .yaml path. <name> is a persona in tests/sim/personas/.
--budget is the ceiling for this invocation, split evenly over the runs. --loop-ledger is a JSON file that adds up
what every invocation spent; probe.py refuses to start when that total plus --budget would pass --loop-budget.
--blind prints categories and counts only, never an item ID, its text or its keywords, and writes the detail to
detail-DO-NOT-READ-WHEN-BLIND.md in each run folder. A persona with `split: holdout` (seal.py) is always blind unless
--reveal is given, so a holdout's per-item results are never printed by default.

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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "plugin" / "lib"))  # the plugin's bundled PyYAML
import yaml  # noqa: E402

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
seal = sim.load_sim_module("seal")
scale = sim.load_sim_module("probe_scale")
precision = sim.load_sim_module("precision")  # the precision judge, reused for the design's claims
elicit = sim.load_sim_module("probe_elicit")  # the belief and tacit-fact probes, and the overlays their cases name
importing = sim.load_sim_module("probe_import")  # the guided importer's checks: decided with a recorded yes, kept wording

ToolFailure = sim.ToolFailure
SNAPSHOTS = HERE / "snapshots"
PROBES = HERE / "probes"
SCALE_CASES = HERE / "scale" / "cases"  # the scaled cases and their snapshots (probe_scale.py); a case may name its root
PROBE_RESULTS = sim.RESULTS / "probes"
# A probe may open any skill a script can, and the import, which no full-run script plays: it starts from material.
OPENING_MODES = sim.MODES + sim.PLUGIN_TEAM_MODES + ("import",)
DETAIL_NAME = "detail-DO-NOT-READ-WHEN-BLIND.md"
EXCERPT = 200


# ------------------------------------------------------------------ persona, case, snapshot

def load_persona(ref):
    """The persona and whether it is blind. A holdout persona's problems are written to a file, never printed,
    because they name its items and keywords."""
    path = sim.resolve(ref, "personas")
    data = sim.load_yaml(path)
    holdout = seal.split_of(data) != "dev"  # a persona that says neither is sealed, never open by default
    return path, data, holdout, sim.persona_problems(data)


CHECKS = {}  # name -> (function, the parameters it requires)
JUDGED_CHECKS = set()  # checks that call the judge, so a run that scores one keeps the judge's reserve
measure, HIGHER, LOWER = scale.measure, scale.HIGHER, scale.LOWER


def check(name, *params, judged=False):
    """Register a check. `judged=True` for any check that calls the judge (here or in probe_scale), so the run's
    budget keeps the judge's reserve; a judged check without it could spend the share dry before the judge runs."""
    def register(fn):
        CHECKS[name] = (fn, params)
        if judged:
            JUDGED_CHECKS.add(name)
        return fn
    return register


def case_problems(case):
    if not isinstance(case, dict):
        return ["the case must be a mapping"]
    problems = []
    snapshots, root = case.get("snapshot"), snapshot_root(case)
    if not isinstance(snapshots, dict) or not snapshots:
        problems.append("'snapshot' must map each persona name to a snapshot name")
    else:
        for persona, name in snapshots.items():
            if not (root / str(persona) / str(name)).is_dir():
                problems.append(f"snapshot {persona}/{name} is not a folder in {root}")
    if "oracle" in case and not (isinstance(case["oracle"], str) and case["oracle"].strip()):
        problems.append("'oracle' must be the plain instruction a ceiling run passes the assistant, or left out")
    problems += sim.news_problems(case.get("news"))
    if not isinstance(case.get("opening"), str) or not case["opening"].startswith("/vela:"):
        problems.append("'opening' must be a /vela: command")
    elif case["opening"].split()[0].split(":", 1)[1] not in OPENING_MODES:
        problems.append(f"'opening' must start with one of /vela:{', /vela:'.join(OPENING_MODES)}")
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


def snapshot_root(case):
    """SNAPSHOTS, or the folder a case names with `snapshot_root:` (relative to tests/sim), such as scale/snapshots."""
    root = case.get("snapshot_root") if isinstance(case, dict) else None
    return HERE / root if root else SNAPSHOTS


def load_case(ref):
    path = pathlib.Path(ref) if str(ref).endswith(".yaml") else PROBES / f"{ref}.yaml"
    if not path.is_file() and not str(ref).endswith(".yaml") and (SCALE_CASES / f"{ref}.yaml").is_file():
        path = SCALE_CASES / f"{ref}.yaml"
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
    return snapshot_root(case) / persona_name / name


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
    label = snapshot.relative_to(SNAPSHOTS).as_posix() if snapshot.is_relative_to(SNAPSHOTS) else \
        snapshot.relative_to(HERE).as_posix() if snapshot.is_relative_to(HERE) else str(snapshot)
    notes = [f"vault copied from snapshot {label}"]
    skills = vault / ".claude" / "skills"
    if skills.exists():
        shutil.rmtree(skills)
        notes.append("the snapshot held .claude/skills; it was removed")
    shutil.copytree(sim.PLUGIN, skills / "vela", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    notes.append("current plugin/ installed at .claude/skills/vela")
    # As vela upgrade would: a snapshot saved before the format changed starts with the plugin's own copy.
    shutil.copyfile(sim.PLUGIN / "vault" / "CONVENTIONS.md", vault / "CONVENTIONS.md")
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
    check = subprocess.run([sys.executable, str(sim.VELA), "check", "--vault", str(vault)],
                           capture_output=True, text=True, timeout=120)
    (run_dir / "start-check.txt").write_text(f"exit {check.returncode}\n{check.stdout}{check.stderr}", encoding="utf-8")
    notes.append(f"vela check on the starting vault: exit {check.returncode}")
    return vault, notes


# ------------------------------------------------------------------ decisions, seen turn by turn

# A decision is a state set to decided, a table cell that says decided (a Changes row), or a Decision bullet. A
# capture's keep mark "(decided)" only points at a decision already made, at close: counting it read close's own
# record of a grilled decision as a second decision with no yes.
DECIDED = re.compile(r"^\s*state:\s*decided\b|\*\*State:\*\*\s*decided\b|\|\s*decided\s*\|"
                     r"|^\s*-\s*\*\*Decision:\*\*", re.I)
YES = re.compile(r"(?<![a-z])yes\b")
# A read-back asks for the yes as often in words as with a question mark: "I need an explicit yes to write it".
ASKS_FOR_YES = re.compile(r"\?|\b(?:explicit|your) yes\b|\bsay yes\b|\bneed (?:a|your) yes\b", re.I)
GENERATED = re.compile(r"<!-- generated:.*?<!-- /generated:[^>]*-->", re.S)


def decided_lines(vault):
    """Every vault line that records something as decided: a state, a table cell, a capture mark, a Decision
    bullet. Counted, so a second copy of the same line is a second decision. A generated block is left out: render
    copies a decided contract into the consumer's contracts-consumed table, and that copy decides nothing."""
    return collections.Counter((rel, line.strip()) for rel, text in sim.vault_pages(vault)
                               for line in GENERATED.sub("", text).splitlines() if DECIDED.search(line))


# A design choice is an ADR (its title line is the one choice it records) or, anywhere else under docs/, a line that
# says what was picked. Design docs carry no state: decided marker, so DECIDED never sees them.
ADR_TITLE = re.compile(r"^#\s+ADR-\d+", re.I)
CHOICE = re.compile(r"\bwe(?:'ll|\u2019ll| will| are going to)\s+(?:use|build|adopt|go with|run|store|ship|write|keep)\b"
                    r"|\bchosen (?:option|approach|design)\b|\b(?:option|approach)\s+[a-d1-4]\s+(?:is|was) (?:chosen|picked|selected)\b"
                    r"|^\s*(?:[-*+]\s+)?(?:\*\*)?(?:decision|chosen option|choice)(?:\*\*)?\s*:", re.I)


DECISIONS_HEAD = re.compile(r"^\s*(?:#{2,4}\s+decisions?\b|>?\s*\*\*decisions\b[^*]*\*\*)", re.I)
BULLET = re.compile(r"^\s*>?\s*[-*+]\s+\S")


def design_choice_lines(vault):
    """Every line under docs/ that writes a design choice: an ADR's title, a bullet under a Decisions heading (the
    design format's "Decisions that shape it" and "### Decisions"), or a line that says what was picked. Counted like
    decided_lines, so one new copy is one new choice. Inside an ADR only the title counts: its Decision paragraph
    restates the choice the title already records."""
    found = collections.Counter()
    for path in sorted((pathlib.Path(vault) / "docs").rglob("*.md")):
        rel = path.relative_to(vault).as_posix()
        is_adr = "/adr/" in f"/{rel}"
        listing = False
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if is_adr:
                hit = bool(ADR_TITLE.match(line))
            else:
                if DECISIONS_HEAD.match(line):
                    listing = True
                elif listing and not BULLET.match(line) and line.strip():
                    listing = False
                hit = (listing and bool(BULLET.match(line))) or bool(CHOICE.search(line))
            if hit:
                found[(rel, line.strip())] += 1
    return found


def explicit_yes(lead_message, asked):
    """A decision counts as the lead's when the message that led to it says yes to a question the assistant put."""
    return bool(asked) and bool(YES.search(sim.normalize(lead_message)))


def item_states(vault, ids):
    """id -> its state, or None: probe_scale.item_states, the loop's one reader, which reads through vela's parser."""
    return scale.item_states(vault, ids)


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
        self.design_choices, self.design_seen = [], collections.Counter()
        self.seen = collections.Counter()
        self.options = None
        self.watch = []  # item IDs a decided-items criterion names, whose state is read after every turn
        self.item_decisions, self.item_seen = [], {}
        self.yes_pending = False  # the lead said yes to a question, and no decision has used that yes yet
        self.oracle = ""  # a ceiling run's plain instruction, appended to the assistant's system prompt

    def start(self):
        self.vault, self.notes = build_probe_vault(self.dir, self.snapshot, self.persona)
        self.seen = decided_lines(self.vault)
        self.design_seen = design_choice_lines(self.vault)
        self.item_seen = item_states(self.vault, self.watch)
        for note in self.notes:
            self.transcript.add(speaker="driver", session=0, mode="setup", event="setup", text=note)

    def assistant_turn(self, message, session_id, cwd=None):
        with scale.oracle_argv(sim, self.oracle):
            parsed, result = super().assistant_turn(message, session_id, cwd)
        turn = self.transcript.turn + 1  # the turn number the transcript is about to give this reply
        previous = next((e["text"] for e in reversed(self.transcript.spoken()) if e["speaker"] == "assistant"), "")
        now = decided_lines(self.vault)
        # A grill reads back, gets the yes, then asks why and files the decision after the why answer (grill
        # SKILL.md section 4), so the yes is a turn or two before the decision. The yes counts until a decision
        # uses it: a 2026-10-15 grill-ready run filed both decisions one turn after their yes, and read 6 of 6
        # "without a yes" when only the message right before the decision was read.
        self.yes_pending = self.yes_pending or explicit_yes(message, bool(ASKS_FOR_YES.search(previous)))
        with_yes, decided_now = self.yes_pending, False
        for (rel, line), count in (now - self.seen).items():
            for _ in range(count):
                self.decisions.append({"turn": turn, "file": rel, "line": line, "with_yes": with_yes})
                decided_now = True
        self.seen = now
        chosen = design_choice_lines(self.vault)
        for (rel, line), count in (chosen - self.design_seen).items():
            for _ in range(count):
                self.design_choices.append({"turn": turn, "file": rel, "line": line, "with_yes": with_yes})
                decided_now = True
        self.design_seen = chosen
        if self.watch:
            states = item_states(self.vault, self.watch)
            for item, state in states.items():
                if state == "decided" and self.item_seen.get(item) != "decided":
                    self.item_decisions.append({"id": item, "turn": turn, "with_yes": with_yes})
                    decided_now = True
            self.item_seen = states
        if decided_now:
            self.yes_pending = False
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
    flat = sim.normalize(sentence).rstrip(" )]")
    return flat.endswith("?") and not CONFIRM_TAIL.search(flat)


def has_cue(text):
    return bool(CUE.search(sim.normalize(text)))


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
    terms = {sim.normalize(c["who"]) for c in persona.get("conflicts") or []}
    for item in persona.get("knows") or []:
        for part in re.split(r"[;,]", str(item.get("owner") or "")):
            if len(sim.normalize(part)) >= 3 and "nobody" not in part:
                terms.add(sim.normalize(part))
    return sorted(terms)


def mechanical_parts(block, terms):
    flat = sim.normalize(block)
    return {"costs": bool(COST_CUE.search(flat)), "rules_out": bool(RULES_OUT_CUE.search(flat)),
            "stakeholder_or_unknown": bool(UNKNOWN_CUE.search(flat) or ROLE_CUE.search(flat)
                                           or any(t in flat for t in terms))}


def options_turn(spoken):
    """The first assistant turn with two or more labeled options, else the first that talks about options."""
    assistant = [e for e in spoken if e["speaker"] == "assistant"]
    for entry in assistant:
        if len(option_blocks(entry["text"])) >= 2:
            return entry, option_blocks(entry["text"])
    for entry in assistant:
        if re.search(r"\boptions?\b", sim.normalize(entry["text"])):
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
            raise ToolFailure(f"the options judge call {sim.error_in_words(result)}. Read {raw}")
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
    return isinstance(quote, str) and bool(sim.normalize(quote)) and sim.normalize(quote) in sim.normalize(text)


def analyze_options(run):
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
    return passed, summary, detail, measure(f"{category} flagged", counts["flagged"], len(rows))


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
    return (passed, summary, [decision_line(d) for d in run.decisions],
            measure("decided without a yes", len(bad), better=LOWER))


DESIGN_FOLDER = "docs"
@check("design-choice-without-yes", "at_most")
def design_choice_without_yes(run, criterion):
    """decided-without-yes for design, which writes choices as prose and ADRs, not as decided states. It reads the
    yes the same way (ProbeRun.yes_pending), so there is one yes-tracker."""
    bad = [d for d in run.design_choices if not d["with_yes"]]
    passed = len(bad) <= criterion["at_most"]
    summary = (f"design choices written without a yes: {len(bad)} (need at most {criterion['at_most']}); "
               f"choices written in all: {len(run.design_choices)}")
    return (passed, summary, [decision_line(d) for d in run.design_choices],
            measure("design choice without a yes", len(bad), better=LOWER))


CLAIM_SOURCE_CHARS = 120_000  # of vault pages given the claims judge as sources; the rest of its input is the senior's words


def design_units(vault):
    """The items a design session wrote under docs/: a section under an item heading, or a paragraph, bullet or row."""
    out = []
    for path in sorted((pathlib.Path(vault) / DESIGN_FOLDER).rglob("*.md")):
        rel = path.relative_to(vault).as_posix()
        _, body = precision.compare.frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        body = precision.clean(body)
        found = precision.item_sections(body.splitlines())
        parts = [(item_id, f"{item_id} {name}\n" + "\n".join(lines)) for item_id, name, lines in found] or \
                [(f"part {n}", text) for n, text in enumerate(precision.loose_units(body), 1)]
        out += [precision.Unit(rel, "design", key, text) for key, text in parts
                if len(re.findall(r"\w+", text)) >= precision.MIN_WORDS]
    return out


def claim_sources(snapshot):
    """The vault pages the design started from, as the judge's source documents: smallest first until the room is
    used. Session notes and docs are left out; the senior's words are given separately, turn by turn."""
    pages = [(rel, text) for rel, text in sim.vault_pages(snapshot)
             if rel.split("/")[0] not in ("sessions", DESIGN_FOLDER)]
    docs, used = [], 0
    for rel, text in sorted(pages, key=lambda p: (len(p[1]), p[0])):
        if used + len(text) <= CLAIM_SOURCE_CHARS:
            docs.append({"name": rel, "text": text})
            used += len(text)
    return docs


@check("claims-unsupported", "at_most", judged=True)
def claims_unsupported(run, criterion):
    """Lines the session wrote under docs/ that state something as fact which neither the senior's words nor a vault
    page give: precision.py's judge, aimed at the design instead of the vault. Its citations are checked the same way
    (a quote the driver can't find turns the line unsupported), so a careless judge can fail a line but never pass one."""
    units, docs, what = claim_units(run, criterion)
    if not units:
        where = " under docs/" if what == "design" else ""
        return (True, f"{what} lines written{where}: 0, nothing to judge (need at most {criterion['at_most']} "
                      "unsupported)", [], measure(f"unsupported {what} claims", 0, 0, better=LOWER))

    def send(text):
        room = min(run.ledger.judge_room(), precision.BUDGET_USD)
        if room < sim.MIN_CALL_USD:
            raise ToolFailure("no budget left for the design claims judge call")
        raw = run.raw("judge-claims")
        done = sim.call(sim.text_call_argv(run.args.judge_model, precision.SYSTEM_PROMPT, room, thinking=True),
                        env=run.env, cwd=run.dir / "persona-cwd", raw_path=raw, kind="judge", stdin=text)
        result = sim.parse_single(done.stdout, raw)
        run.ledger.add(float(result["total_cost_usd"]))
        run.judge_calls.append({"category": "claims", "raw": raw.name, "cost_usd": result["total_cost_usd"],
                                "thinking_tokens": sim.thinking_tokens(result)})
        return result

    sample, spoken = precision.stratified_sample(units), run.transcript.spoken()
    try:
        text, labels, _ = precision.build_input(sample, units, docs, spoken)
        data, why = precision.ask(send, text, [label for label, _ in sample])
    except precision.JudgeFailure as exc:
        raise ToolFailure(str(exc)) from exc
    if data is None:
        raise ToolFailure(f"the design claims judge did not score the session: {why}")
    for row in data.get("items") or []:  # a judge may cite an inbox document by its folder too; the name is the key
        if isinstance(row, dict) and str(row.get("where") or "").startswith(".inbox/"):
            row["where"] = row["where"][len(".inbox/"):]
    rows, _ = precision.enforce(data, sample, labels, docs, spoken)
    bad = [r for r in rows if r["class"] == "unsupported"]
    passed = len(bad) <= criterion["at_most"]
    summary = (f"{what} lines stated as fact that nobody gave: {len(bad)} of {len(rows)} sampled from "
               f"{len(units)} written (need at most {criterion['at_most']})")
    detail = [f"- {r['path']} {r['item']}: {r.get('dropped') or r.get('quote')}. Grounds: {r.get('grounds')}" for r in bad]
    return passed, summary, detail, measure(f"unsupported {what} claims", len(bad), len(rows), better=LOWER)


def claim_units(run, criterion):
    """(units, source documents, what) for the claims judge. `where: docs` (the default) is a design session's lines
    under docs/, judged against the vault it started from; `where: plan` is an import's plan pages, every item the
    snapshot didn't already hold, judged against the inbox documents first, then the starting vault."""
    if criterion.get("where", "docs") == "plan":
        inbox = [{"name": d["name"], "text": d["text"]} for d in run.persona.get("docs") or []]  # as the judge names them
        return precision.units_of(run.vault, template=run.snapshot), inbox + claim_sources(run.snapshot), "plan"
    return design_units(run.vault), claim_sources(run.snapshot), "design"


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


@check("option-count", "between", judged=True)
def option_count(run, criterion):
    found = analyze_options(run)
    low, high = criterion["between"]
    n = len(found["options"])
    where = f" in T{found['turn']}" if found["turn"] else ""
    how = {"labels": "read from their labels", "judge": "found by the judge", "none": "no turn offered options"}
    summary = f"options offered: {n}{where}, {how[found['source']]} (need {low} to {high})"
    detail = [f"- option {o['label']}: \"{sim.short(' '.join(o['text'].split()), EXCERPT)}\"" for o in found["options"]]
    return low <= n <= high, summary, detail


@check("option-parts", "parts", judged=True)
def option_parts(run, criterion):
    found = analyze_options(run)
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


def vela_output(vault, *argv):
    """What the current plugin's `vela` prints for the final vault. A tool failure (exit 2) stops the probe."""
    done = subprocess.run([sys.executable, str(sim.VELA), *argv, "--vault", str(vault)], capture_output=True, text=True, timeout=120)
    if done.returncode == 2:
        raise ToolFailure(f"vela {argv[0]} failed on the final vault: {done.stdout.strip().splitlines()[:1]}")
    return done.stdout


@check("owed-copies-disposed", "severity")
def owed_copies_disposed(run, criterion):
    """Every owed copy of the severity (`high`, or `any`) has a ledger row that says more than open, and
    vela check flags no ledger row (E801, E802, E803): every owed copy has a valid disposition."""
    answer = json.loads(vela_output(run.vault, "questions", "--json"))
    severity = criterion["severity"]
    wanted = [c for c in answer["copies"] if severity == "any" or c["severity"] == severity]
    undisposed = [c for c in wanted if c["state"] in ("no row", "open")]
    flagged = [line for line in vela_output(run.vault, "check").splitlines() if LEDGER_FLAGS.search(line)]
    passed = bool(wanted) and not undisposed and not flagged
    summary = (f"owed copies ({severity}) with a disposition: {len(wanted) - len(undisposed)} of {len(wanted)}; "
               f"ledger rows vela check flags: {len(flagged)} (need every copy disposed and no flagged row)")
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
    answer = json.loads(vela_output(run.vault, "questions", "--json"))
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


def catalog_areas():
    data = yaml.safe_load((sim.PLUGIN / "catalog" / "questions.yaml").read_text(encoding="utf-8"))
    return list(data["areas"])


@check("area-coverage", "require")
def area_coverage(run, criterion):
    """Every review checkpoint the session records gives each focus area one result: found N, checked,
    none, or did not run with its reason. `require: ran` also needs every area to have run."""
    areas = catalog_areas()
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


@check("drafted-messages", "at_most")
def drafted_messages(run, criterion):
    """Messages drafted for the lead to send, counted by code: the skills say Claude never drafts one."""
    turns = sim.drafted_messages(run.transcript)
    passed = len(turns) <= criterion["at_most"]
    return passed, f"messages drafted for the lead to send: {len(turns)} (need at most {criterion['at_most']})", \
        [f"- T{t}" for t in turns]


@check("merge-scoped")
def merge_scoped(run, criterion):
    """Every `vela findings merge` the session ran names --changed, so a new question can only be about what this
    session changed. A session that merged nothing fails: its checkpoint never ran."""
    merges = [(e["turn"], str(t.get("input", ""))) for e in run.transcript.entries if e.get("speaker") == "assistant"
              for t in e.get("tool_calls") or [] if "findings merge" in str(t.get("input", ""))]
    scoped = [m for m in merges if "--changed" in m[1]]
    passed = bool(merges) and len(scoped) == len(merges)
    return passed, f"findings merges: {len(merges)}; with --changed: {len(scoped)}", \
        [f"- T{turn}: {sim.short(text, 200)}" for turn, text in merges]


@check("main-session-turns", "at_most")
def main_session_turns(run, criterion):
    """Assistant turns before close. A blocked session ends rather than filling itself with other work."""
    turns = [e for e in run.transcript.spoken() if e["speaker"] == "assistant" and e.get("mode") != "close"]
    passed = len(turns) <= criterion["at_most"]
    return passed, f"assistant turns before close: {len(turns)} (need at most {criterion['at_most']})", []


# ------------------------------------------------------------------ gaps, decisions, conflicts, unsure owners
# These read the persona's items by kind and category only. A case file names a check and a threshold, never an
# item, so a case can be shown to anyone; the items stay in the persona file and the blind detail.

@check("unaware-raised-first", "at_least")
def unaware_raised_first(run, criterion):
    """The gaps the lead does not know about (U items) that an assistant turn names before any lead turn does.
    The lead is never told them, so a lead turn that names one is repeating the assistant or a document."""
    spoken = run.transcript.spoken()
    rows = []
    for item in run.persona.get("unaware") or []:
        turns = {who: first_turn(spoken, who, item["keywords"]) for who in ("assistant", "lead")}
        first = turns["assistant"] is not None and (turns["lead"] is None or turns["assistant"] < turns["lead"])
        rows.append((item, turns, first))
    raised = sum(1 for _, _, first in rows if first)
    share = raised / len(rows) if rows else 0.0
    passed = bool(rows) and share >= criterion["at_least"]
    summary = (f"gaps the lead didn't know about, raised first by the assistant: {raised} of {len(rows)} "
               f"({pct(share)}; need at least {pct(criterion['at_least'])})")
    detail = [f"- {i['id']} ({i['category']}): assistant {('T%d' % t['assistant']) if t['assistant'] else 'never'}, "
              f"lead {('T%d' % t['lead']) if t['lead'] else 'never'}; {'RAISED FIRST' if f else 'not first'}"
              for i, t, f in rows]
    return passed, summary, detail, measure("gaps raised first, by keyword", raised, len(rows))


@check("decided-with-yes", "at_least")
def decided_with_yes(run, criterion):
    """Decisions the session recorded after the lead's explicit yes to a read-back. A grill that decides nothing
    passes decided-without-yes trivially, so this is its other half."""
    good = [d for d in run.decisions if d["with_yes"]]
    passed = len(good) >= criterion["at_least"]
    summary = (f"decisions recorded after an explicit yes: {len(good)} (need at least {criterion['at_least']}); "
               f"without a yes: {len(run.decisions) - len(good)}")
    return passed, summary, [decision_line(d) for d in run.decisions], measure("decided with a yes", len(good))


@check("decided-items", "decidable", "blocked", "at_least")
def decided_items(run, criterion):
    """A grill from a vault built to hold both kinds: items the plan's gate finds ready (options written, no open
    unknown blocking them) and items an open unknown blocks. It passes when at least `at_least` ready items are
    decided after the lead's explicit yes, none is decided without one, and no blocked item is decided. A grill that
    decides nothing, or decides everything, fails either way, so the probe tells a careful grill from a timid one."""
    by_id = {}
    for d in run.item_decisions:
        by_id.setdefault(d["id"], d)
    ready = [i for i in criterion["decidable"] if i in by_id and by_id[i]["with_yes"]]
    no_yes = [i for i in criterion["decidable"] if i in by_id and not by_id[i]["with_yes"]]
    blocked = [i for i in criterion["blocked"] if i in by_id]
    passed = len(ready) >= criterion["at_least"] and not no_yes and not blocked
    summary = (f"ready items decided after an explicit yes: {len(ready)} of {len(criterion['decidable'])} (need at "
               f"least {criterion['at_least']}); ready items decided without a yes: {len(no_yes)}; blocked items "
               f"decided: {len(blocked)} of {len(criterion['blocked'])} (need 0)")
    detail = [f"- {i} (ready): " + (f"decided at T{by_id[i]['turn']}, {'with' if by_id[i]['with_yes'] else 'WITHOUT'} a yes"
                                    if i in by_id else "not decided") for i in criterion["decidable"]]
    detail += [f"- {i} (blocked): " + (f"DECIDED at T{by_id[i]['turn']}" if i in by_id else "not decided")
               for i in criterion["blocked"]]
    return passed, summary, detail, [measure("watched ready items decided with a yes", len(ready),
                                             len(criterion["decidable"])),
                                     measure("watched blocked items decided", len(blocked), len(criterion["blocked"]),
                                             LOWER)]


@check("gaps-surfaced", "at_least", judged=True)
def gaps_surfaced(run, criterion):
    """The gaps the lead does not know about (U items) that the assistant raised before the lead did, in any words.
    unaware-raised-first needs one of an item's keywords, which are a specialist's terms, so a session that asks
    whether anyone in Germany has to agree before staff are watched scored nothing for that gap. Here run.py's
    unaware judge reads the gap items and the session and decides each, citing a turn and a quote; a claim whose
    quote is not in that assistant turn is dropped, so a careless judge can fail a gap but never pass one. The
    per-item verdicts go to the blind detail only; the summary is counts."""
    items = run.persona.get("unaware") or []
    if not items:
        return (False, "gaps the lead didn't know about: the persona lists none", [],
                measure("gaps surfaced first, judged", 0, 0))
    hits = sim.vault_hits(run.persona, run.transcript, run.vault)
    reply, why = sim.judge_category(run, "unaware", hits)
    if reply is None:
        raise ToolFailure(f"the gaps judge did not score the session: {why}")
    turns = {e["turn"]: e["text"] for e in run.transcript.spoken() if e["speaker"] == "assistant"}
    rows, dropped, detail = {r["id"]: r for r in reply["unaware"]}, 0, []
    for item in items:
        row = rows[item["id"]]
        ok = bool(row.get("surfaced")) and sim.cited(row, turns)
        if row.get("surfaced") and not ok:
            dropped += 1
        verdict = (f"SURFACED at T{row['turn']}: \"{row['quote']}\"" if ok
                   else "claim dropped, the quote is not in that assistant turn" if row.get("surfaced") else "not surfaced")
        detail.append(f"- {item['id']} ({item['category']}): {verdict}. Grounds: {row.get('grounds')}")
        row["ok"] = ok
    surfaced = sum(1 for r in rows.values() if r.get("ok"))
    share = surfaced / len(items)
    passed = share >= criterion["at_least"]
    summary = (f"gaps the lead didn't know about, surfaced first by the assistant in any words (judged): {surfaced} "
               f"of {len(items)} ({pct(share)}; need at least {pct(criterion['at_least'])}); judge claims dropped for "
               f"a quote not in the cited assistant turn: {dropped}")
    return passed, summary, detail, measure("gaps surfaced first, judged", surfaced, len(items))


PARTY_SPLIT = re.compile(r"\s*(?:,|/|&|\band\b|\bvs\.?|\bversus\b)\s*", re.I)
PARTY_FILLER = re.compile(r"^(?:the|our|a|an)\s+|\s+(?:rep|representative|team|lead|office|function)$", re.I)


def parties(who):
    """The names a stakeholder position is held by, each also without a filler word ("the", "rep", "team"),
    so "HR and works council rep" is held by "HR" and "works council"."""
    names = []
    for part in PARTY_SPLIT.split(who or ""):
        part = part.strip()
        if part:
            names += [part, PARTY_FILLER.sub("", PARTY_FILLER.sub("", part)).strip()]
    return [n for n in dict.fromkeys(names) if len(n) >= 2]


# A stakeholder disagreement is said in more ways than a source mismatch: "wants X while Y rules it out".
SIDE_CUE = re.compile(r"\bwhile\b|\bwhereas\b|\bversus\b|\bvs\b|\bagainst\b|\btension\b|\bat odds\b|\bopposite"
                      r"|\bpull(?:s|ing)? (?:in )?different|\bdifferent things\b|\brules? (?:it |that |this )?out\b"
                      r"|\bwon'?t (?:accept|allow|sign)|\bblocks?\b|\bobject|\bbreaks? the tie\b|\btie-?break")


def side_cue(text):
    return has_cue(text) or bool(SIDE_CUE.search(sim.normalize(text)))


def conflict_parts(item, spoken, final_spots, start_spots):
    """Per stakeholder position: named (an assistant sentence or the list line it sits in carries a disagreement
    cue and names the position, by its keyword or by who holds it), side (such a line names who holds it) and
    recorded (a new unknown, risk, [unknown] or [worry] capture holds the position's keyword, or names who holds it
    with a disagreement cue). People paraphrase a position more than they repeat it, so the holder counts too."""
    who = parties(item.get("who"))
    named = side = None
    for entry in (e for e in spoken if e["speaker"] == "assistant"):
        for sentence, container, _ in units(entry["text"]):
            keyword, holder = sim.mentions(container, item["keywords"]), sim.mentions(container, who)
            if (keyword or holder) and side_cue(container):
                named = named or entry["turn"]
                if holder and side is None:
                    side = entry["turn"]
    recorded = bool(vault_flagged(item["keywords"], final_spots, start_spots)) or any(
        sim.mentions(text, who) and side_cue(text) and text != start_spots.get(key)
        for key, text in final_spots.items())
    return {"named": named, "side": side, "recorded": recorded}


@check("conflicts-surfaced", "at_least")
def conflicts_surfaced(run, criterion):
    """Stakeholder positions that contradict each other, each surfaced in full: the session named the disagreement,
    said who holds this side, and recorded it as an open question or a risk rather than picking a side."""
    final, start = flag_spots(sim.vault_pages(run.vault)), flag_spots(sim.vault_pages(run.snapshot))
    items = brief_items(run.persona, ["stakeholder-conflict"])
    rows = [(i, conflict_parts(i, run.transcript.spoken(), final, start)) for i in items]
    full = sum(1 for _, p in rows if p["named"] and p["side"] and p["recorded"])
    share = full / len(rows) if rows else 0.0
    count = {k: sum(1 for _, p in rows if p[k]) for k in ("named", "side", "recorded")}
    passed = bool(rows) and share >= criterion["at_least"]
    summary = (f"stakeholder positions surfaced in full: {full} of {len(rows)} ({pct(share)}; need at least "
               f"{pct(criterion['at_least'])}); disagreement named {count['named']}, holder named {count['side']}, "
               f"recorded as open {count['recorded']}")
    detail = [f"- {i['id']}: named {p['named'] and 'T%d' % p['named'] or 'no'}, side {p['side'] and 'T%d' % p['side'] or 'no'}, "
              f"recorded {'yes' if p['recorded'] else 'no'}" for i, p in rows]
    of = len(rows)
    return passed, summary, detail, [measure("conflicts surfaced in full", full, of),
                                     measure("conflicts: disagreement named", count["named"], of),
                                     measure("conflicts: holder named", count["side"], of),
                                     measure("conflicts: recorded as open", count["recorded"], of)]


UNSURE = re.compile(r"\b(?:not sure|unsure|no idea|don'?t know|do not know|couldn'?t tell you|can'?t say|no clue|"
                    r"haven'?t (?:a clue|checked|heard))\b", re.I)
ASKS_OWNER_OR_DATE = re.compile(r"\b(?:who (?:would|might|else would) know|who (?:should|would|will|can|could)?\s*(?:own|owns|take|chase|answer|hold)|owner|"
                                r"by when|what date|which date|due|deadline|ask-by|ask by|when (?:should|would|do|does|can))"
                                r"\b[^?]{0,200}\?", re.I)
# A turn that proposes who to ask or by when. The unsure-owner check wants the question within 200 characters of it,
# as a reply to one unsure answer; the scaled check (probe_scale) lets one closing question confirm a batch.
PROPOSAL_CUE = (r"\b(?:owner|own it|owns it|take it on|due|deadline|by when|ask-by|ask by|what date|"
                r"which date|by (?:mon|tues|wednes|thurs|fri)day|by the end of|i'?d (?:put|suggest|propose)|"
                r"i (?:suggest|propose)|i'?d ask|by \d{1,2}(?:st|nd|rd|th)? [a-z]+)\b")
PROPOSES_AND_ASKS = re.compile(PROPOSAL_CUE + r"[^?]{0,200}\?", re.I)
# Who is asked and by when. --owner counts too, except the lead's own handle: the lead owns what they chase.
WRITES = re.compile(r"--(?P<flag>owner|ask|due|by|ask-by)[= ](?P<value>\"[^\"]*\"|'[^']*'|\S+)")


def assistant_tool_text(run):
    """turn -> the full text of every tool input that assistant turn sent, from raw/ (the transcript keeps only 200
    characters of each), matched to the transcript's assistant turns in order."""
    compare = sim.load_sim_module("compare_runs")
    turns = [e for e in run.transcript.spoken() if e["speaker"] == "assistant"]
    raw = compare.raw_tool_inputs(run.dir / "raw")
    calls = raw[0] if raw else []
    out = {}
    for n, entry in enumerate(turns):
        tools = calls[n] if n < len(calls) else entry.get("tool_calls") or []
        out[entry["turn"]] = "\n".join(str(t.get("input", "")) for t in tools)
    return out


MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


# A written --ask often holds more than the lead said: "Ruth Okoye, Finance Operations" after the lead said yes to
# Ruth, or "Brandt & Kessler, through Ruth Okoye". Any one part the lead confirmed confirms the value (T39).
VALUE_PARTS = re.compile(r"\s*(?:[,;()]|\b(?:or|and|plus|through|via)\b)\s*")
ARTICLE = re.compile(r"^(?:(?:the|a|an|our|to put to|whoever (?:runs|holds|owns))\s+)+")
INITIALS_SKIP = {"of", "the", "and", "for", "&", "in", "on", "to"}


def value_parts(flat):
    """The names a written value holds, each without its article; a spelled-out role's initials ("chief
    information security officer" is also "ciso", the way a lead says it); and a long name with one inner word left
    out ("corrigan software account contact" is said as "corrigan account contact"). The first and last words
    stay: "data protection officer" is never confirmed by "data protection"."""
    parts = []
    for part in VALUE_PARTS.split(flat):
        part = ARTICLE.sub("", part.strip())
        if len(part) < 3:
            continue
        parts.append(part)
        words = part.split()
        content = [w for w in words if w not in INITIALS_SKIP]
        if len(content) >= 3:
            parts.append("".join(w[0] for w in content))
        if len(words) >= 4:
            parts += [" ".join(words[:n] + words[n + 1:]) for n in range(1, len(words) - 1)]
    return list(dict.fromkeys(parts))


def ordinal(day):
    return f"{day}{'th' if 10 <= day % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')}"


def value_forms(value):
    """How a written value reads in a conversation: an ISO date as "29 october", "october 29" or "the 29th" (the
    month is the one under discussion), a name or role as any of its parts (value_parts), else itself. A shell
    variable ($3) is no value the session chose, so it has no forms."""
    flat = re.sub(r"^(?:the|a|an|our) ", "", plain(value.strip("\"'").lstrip("@")))
    if not flat or flat.startswith("$"):
        return []
    m = ISO_DATE.match(flat)
    if not m:
        return list(dict.fromkeys([flat] + value_parts(flat)))
    if not 1 <= int(m[2]) <= 12:
        return [flat]
    month, day = MONTHS[int(m[2]) - 1], int(m[3])
    nth = ordinal(day)
    return [flat, f"{day} {month}", f"{month} {day}", f"{nth} {month}", f"{month} {nth}", f"{day}th {month}",
            f"{month} {day}th", f"the {nth}"]


def said_in(form, text):
    """form said as whole words in text: "cio" is not confirmed by "precious"."""
    return re.search(r"(?<!\w)" + re.escape(form) + r"(?!\w)", text) is not None


def source_owner(text, at):
    """The --owner at this offset belongs to `vela add source`: a document's author, read from the document, never
    who to ask about an open question."""
    start = text.rfind("vela ", 0, at)
    return start >= 0 and text[start:at].startswith("vela add source")


# "Those four work for me" agrees to a proposed person and date as plainly as "yes" does. Only this check reads it:
# a decision still needs the yes word (explicit_yes).
AGREES = re.compile(r"\b(?:works?|work for me|sounds (?:good|right)|agreed?|go with (?:that|those|it))\b")
NOT_AGREED = re.compile(r"\b(?:not|no|doesnt|dont|wont|never|cant)\b\W+(?:\w+\W+){0,3}?(?:works?|agree)")


def agrees(lead_message):
    flat = sim.normalize(lead_message)
    return bool(YES.search(flat)) or (bool(AGREES.search(flat)) and not NOT_AGREED.search(flat))


def plain(text):
    """normalize, with a possessive dropped: "Corrigan's account contact" says "corrigan account contact"."""
    return sim.normalize(re.sub(r"(?<=\w)['’]s\b", "", str(text)))


def confirmed_values(spoken, upto):
    """What the lead had confirmed before spoken[upto]: each lead message's own words, and each assistant turn
    the lead's next message agreed to."""
    said = []
    for i, e in enumerate(spoken[:upto]):
        if e["speaker"] != "lead":
            continue
        said.append(plain(e["text"]))
        before = next((x for x in reversed(spoken[:i]) if x["speaker"] == "assistant"), None)
        if before and ASKS_FOR_YES.search(before["text"]) and agrees(e["text"]):
            said.append(plain(before["text"]))
    return said


@check("unsure-owner-asked", "at_most")
def unsure_owner_asked(run, criterion):
    """When the lead says they're not sure who owns something or by when, the session proposes one and asks, and
    writes only who to ask and by when as the lead confirmed. The case's news tells the lead they don't know any, so
    every --ask, --ask-by, --due, --by or --owner other than the lead's own handle counts: as confirmed when an
    earlier lead message names that value, or the lead said yes to an assistant turn that named it (a date in words
    or as YYYY-MM-DD), and as unconfirmed otherwise."""
    spoken, tools = run.transcript.spoken(), assistant_tool_text(run)
    own = sim.normalize(str(run.persona.get("handle", "")).lstrip("@"))
    moments, handled, unconfirmed, detail = 0, 0, [], []
    for i, entry in enumerate(spoken):
        if entry["speaker"] != "assistant":
            continue
        lead = next((e for e in reversed(spoken[:i]) if e["speaker"] == "lead"), None)
        asked_before = next((e for e in reversed(spoken[:i]) if e["speaker"] == "assistant"), None)
        if lead and asked_before and UNSURE.search(lead["text"]) and ASKS_OWNER_OR_DATE.search(asked_before["text"]):
            moments += 1
            ok = bool(PROPOSES_AND_ASKS.search(entry["text"]))
            handled += ok
            detail.append(f"- T{entry['turn']}: lead unsure about an owner or date; {'proposed and asked' if ok else 'did not propose and ask'}")
        # A command retried after a failure writes the same value again: count each value once per turn.
        sent = tools.get(entry["turn"], "")
        writes = list({(m["flag"], m["value"]): m for m in WRITES.finditer(sent)}.values())
        said = confirmed_values(spoken, i) if writes else []
        for m in writes:
            forms = value_forms(m["value"])
            if not forms or (m["flag"] == "owner" and (forms[0] == own or source_owner(sent, m.start()))):
                continue
            if not any(said_in(f, text) for f in forms for text in said):
                unconfirmed.append(entry["turn"])
                detail.append(f"- T{entry['turn']}: wrote --{m['flag']} the lead had not confirmed")
    passed = moments > 0 and handled == moments and len(unconfirmed) <= criterion["at_most"]
    summary = (f"times the lead was unsure of an owner or date: {moments}; the session proposed one and asked: "
               f"{handled} of {moments}; owners or dates written without the lead's confirmation: {len(unconfirmed)} "
               f"(need every time proposed and asked, and at most {criterion['at_most']} unconfirmed)")
    return passed, summary, detail


class _ThisModule:
    """This module's names, read when used: loaded by path (as tests do), probe.py may not be in sys.modules."""

    def __getattr__(self, name):
        try:
            return globals()[name]
        except KeyError:
            raise AttributeError(name) from None


THIS = _ThisModule()
scale.register(THIS)
elicit.register(THIS)
importing.register(THIS)


def score(run, case):
    """Each criterion's row. A check may return a fourth value: its measure (probe_scale.measure, a count of N), or a
    list of them. probe_scale.summarize is the one place a measure is averaged over the runs; a row holds no other
    number, so nothing is averaged twice."""
    rows = []
    for criterion in case["criteria"]:
        fn = CHECKS[criterion["check"]][0]
        passed, summary, detail, *rest = fn(run, criterion)
        found = rest[0] if rest else []
        rows.append({"check": criterion["check"], "passed": passed, "summary": summary, "detail": detail,
                     "measures": found if isinstance(found, list) else [found]})
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
        """Add this invocation under a lock, re-reading the file first: two probes of one loop may run side by side
        (the dev persona and a holdout), and the one that finished second must not write over the first's spend."""
        import fcntl
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_name(self.path.name + ".lock"), "w", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.data = LoopLedger(self.path).data
            self.data["invocations"].append(entry)
            self.data["spent_usd"] = round(self.spent + entry["spent_usd"], 4)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
            tmp.replace(self.path)


# ------------------------------------------------------------------ one run, and the output

def headline(message):
    """The part of a failure message before its first ': ', which names what failed without quoting any text."""
    return str(message).split(": ", 1)[0]


def run_once(case, persona, persona_name, args, n, stamp, share):
    # A ceiling run is named apart, so it can run beside its baseline and is never read as one.
    folder = f"{stamp}-{case['name']}-{persona_name}{'-oracle' if getattr(args, 'oracle', False) else ''}-{n}"
    reserve = sim.JUDGE_RESERVE if any(c["check"] in JUDGED_CHECKS for c in case["criteria"]) else 0.0
    run = ProbeRun(folder, pathlib.Path(args.out).resolve(), args, persona, share,
                   snapshot_dir(case, persona_name), reserve)
    run.watch = [i for c in case["criteria"] if c["check"] == "decided-items" for i in c["decidable"] + c["blocked"]]
    run.rows, run.failure = [], None
    run.oracle = case.get("oracle", "") if getattr(args, "oracle", False) else ""
    text = opening_text(case, persona)
    session = {"mode": case["mode"], "cap": case["cap"], "vela": text.replace("{", "{{").replace("}", "}}"),
               "baseline": text.replace("{", "{{").replace("}", "}}")}
    try:
        run.start()
        run.run_session(1, session)
        if case.get("close"):  # the ledger is written at close, so a case that reads it closes the session first
            run.run_session(2, {"mode": "close", "cap": case["close"], "vela": "/vela:close",
                                "baseline": "/vela:close"})
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
            "criteria": [{"check": r["check"], "passed": r["passed"], "summary": r["summary"]} for r in run.rows],
            "oracle": bool(run.oracle), "measures": run_measures(run)}


def run_measures(run):
    """The criteria's measures, then the voice on the lead-facing turns. Counts only, so blind-safe. A voice sensor
    that breaks is a tool failure (exit 2), never a quiet zero that would read as a clean voice."""
    found = [m for r in run.rows for m in r["measures"]] + scale.voice_measures(run, THIS, sim)
    twice = sorted(n for n, c in collections.Counter(m["name"] for m in found).items() if c > 1)
    if twice:  # two numbers under one name would be averaged as one measure, a mean of two different things
        raise ToolFailure(f"measures named twice in one run: {', '.join(twice)}")
    return found


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
    for m in record.get("measures") or []:
        print(f"  measure {m['name']}: {m['value']:g}" + (f" of {m['of']}" if m.get("of") else ""))
    if blind:
        print(f"  blind: item detail is in {DETAIL_NAME} in the run folder; do not read it while iterating")


# ------------------------------------------------------------------ main

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("case", help="case name in tests/sim/probes/, or a .yaml path")
    parser.add_argument("--persona", required=True, help="persona name in tests/sim/personas/")
    parser.add_argument("--runs", type=int, default=5,
                        help="how many runs of the case, one after another; default 5, enough for a spread")
    parser.add_argument("--oracle", action="store_true",
                        help="the ceiling run: pass the case's oracle: text to the assistant as an appended system "
                             "prompt, for this probe only; it measures the material, never a skill")
    parser.add_argument("--model", required=True, help="assistant model, pinned")
    parser.add_argument("--persona-model", required=True, help="persona model, pinned")
    parser.add_argument("--judge-model", required=True, help="judge model, pinned; only option checks call it")
    parser.add_argument("--budget", required=True, type=float, help="USD ceiling for this invocation, all runs")
    parser.add_argument("--loop-ledger", required=True, help="JSON file that adds up spend across invocations")
    parser.add_argument("--loop-budget", required=True, type=float, help="USD ceiling for the whole loop")
    parser.add_argument("--blind", action="store_true", help="print categories and counts only")
    parser.add_argument("--reveal", action="store_true",
                        help="print per-item results for a holdout persona too; never while iterating on the skills")
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
        blind = args.blind or (holdout and not args.reveal)
        if problems:
            if blind:
                path = refuse_blind_problems(problems, pathlib.Path(args.out))
                raise ToolFailure(f"the persona is not valid ({len(problems)} problems, listed in {path})")
            raise ToolFailure("the persona is not valid:\n  " + "\n  ".join(problems))
        case = load_case(args.case)
        # A case's news changes the lead for this probe only, such as an override the persona would otherwise give.
        persona = sim.with_news(persona, case.get("news"))
        persona = elicit.with_overlay(case, persona, persona_name, HERE, sim)
        snapshot_dir(case, persona_name)
        opening_text(case, persona)
        if args.oracle and not case.get("oracle"):
            raise ToolFailure(f"case {case['name']} has no oracle: text, so it has no ceiling run")
        ledger = LoopLedger(args.loop_ledger)
    except ToolFailure as exc:
        print(f"probe: {exc}", file=sys.stderr)
        return 2
    if ledger.spent + args.budget > args.loop_budget + 1e-9:
        print(f"probe: refused to start. The loop has spent ${ledger.spent:.2f} of ${args.loop_budget:.2f}; this "
              f"invocation's --budget ${args.budget:.2f} would take it to ${ledger.spent + args.budget:.2f}.")
        return 1
    print(f"probe {case['name']}, persona {persona_name}, {args.runs} run(s), budget ${args.budget:.2f}"
          f"{', blind' if blind else ''}{', ORACLE (ceiling run)' if args.oracle else ''}. Loop spend so far ${ledger.spent:.2f} of ${args.loop_budget:.2f}.")
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
        summary = scale.summarize(records)
        ledger.record({"at": stamp, "case": case["name"], "persona": persona_name, "runs": len(records),
                       "budget_usd": args.budget, "spent_usd": spent, "stub": args.stub, "exit": code,
                       "oracle": args.oracle, "folders": [r["folder"] for r in records], "summary": summary})
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{stamp}-{case['name']}-{persona_name}{'-oracle' if args.oracle else ''}-summary.json").write_text(
            json.dumps({"case": case["name"], "persona": persona_name, "oracle": args.oracle, "blind": blind,
                        "runs": len(records), "folders": [r["folder"] for r in records], "measures": summary},
                       indent=2), encoding="utf-8")
    for line in scale.summary_lines(summary, args.oracle):
        print(line)
    passed = sum(1 for r in records if r["passed"])
    print(f"probe: {passed} of {len(records)} run(s) passed every criterion. Spent ${spent:.2f} of ${args.budget:.2f}; "
          f"loop spend now ${ledger.spent:.2f} of ${args.loop_budget:.2f}. Exit {code}.")
    return code


if __name__ == "__main__":
    sys.exit(main())
