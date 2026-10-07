"""The probe harness, run against the scripted fake claude in tests/sim/stub/. Nothing here calls a model or spends
money: every probe passes --stub, and --out and --loop-ledger keep results in tmp_path.

Tests that touch the holdout persona assert on counts only, so a failing test never prints its brief."""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

import pytest
import yaml

from conftest import REPO

SIM = REPO / "tests" / "sim"
spec = importlib.util.spec_from_file_location("sim_probe", SIM / "probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
sim = probe.sim

MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]
HOLDOUT = SIM / "personas" / "holdout-hospitals.yaml"


def persona(name):
    return yaml.safe_load((SIM / "personas" / f"{name}.yaml").read_text(encoding="utf-8"))


def run_probe(tmp_path, case, name, *extra, env=None, budget="1", loop_budget="5"):
    """One stub invocation. Returns (exit code, stdout, stderr, run folders)."""
    out = tmp_path / "out"
    full_env = {**os.environ, **(env or {})}
    done = subprocess.run([sys.executable, str(SIM / "probe.py"), case, "--persona", name, "--stub", *MODELS,
                           "--budget", budget, "--loop-ledger", str(tmp_path / "ledger.json"),
                           "--loop-budget", loop_budget, "--out", str(out), *extra],
                          capture_output=True, text=True, env=full_env, timeout=600)
    runs = sorted(p for p in out.iterdir() if p.is_dir()) if out.is_dir() else []
    return done.returncode, done.stdout, done.stderr, runs


def reply(tmp_path, text):
    path = tmp_path / "reply.md"
    path.write_text(text, encoding="utf-8")
    return {"SIM_STUB_REPLY": str(path)}


# ------------------------------------------------------------------ snapshots

def plugin_files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")


def test_the_probe_vault_gets_the_current_plugin_never_the_snapshots(tmp_path):
    snapshot = tmp_path / "snap"
    shutil.copytree(SIM / "snapshots" / "coastal-merger" / "after-s2", snapshot)
    stale = snapshot / ".claude" / "skills" / "planner" / "skills" / "dump" / "SKILL.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("STALE SKILL FROM A SNAPSHOT\n", encoding="utf-8")
    (snapshot / ".claude" / "skills" / "other").mkdir()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    vault, notes = probe.build_probe_vault(run_dir, snapshot, persona("coastal-merger"))
    installed = vault / ".claude" / "skills" / "planner"
    assert plugin_files(installed) == plugin_files(sim.PLUGIN)
    assert (installed / "skills" / "dump" / "SKILL.md").read_bytes() == (sim.PLUGIN / "skills" / "dump" / "SKILL.md").read_bytes()
    assert sorted(p.name for p in (vault / ".claude" / "skills").iterdir()) == ["planner"]
    assert any("held .claude/skills; it was removed" in n for n in notes)
    log = sim.git("log", "--oneline", "main", cwd=vault).stdout.splitlines()
    assert len(log) == 1
    assert sim.git("ls-remote", "origin", "main", cwd=vault).stdout.strip(), "main is pushed to the bare origin"
    tracked = sim.git("ls-files", cwd=vault).stdout.split()
    assert ".claude/skills/planner/skills/dump/SKILL.md" in tracked and not any(p.startswith(".inbox/") for p in tracked)
    assert sorted(p.name for p in (vault / ".inbox").iterdir()) == sorted(d["name"] for d in persona("coastal-merger")["docs"])
    assert (run_dir / "start-check.txt").read_text(encoding="utf-8").startswith("exit 0")


def test_a_snapshot_inbox_that_drifted_from_the_persona_is_a_tool_failure(tmp_path):
    snapshot = tmp_path / "snap"
    shutil.copytree(SIM / "snapshots" / "coastal-merger" / "empty", snapshot)
    (snapshot / ".inbox" / "cio-memo.md").write_text("an older memo\n", encoding="utf-8")
    (tmp_path / "run").mkdir()
    with pytest.raises(sim.ToolFailure, match="does not match the persona's docs: cio-memo.md"):
        probe.build_probe_vault(tmp_path / "run", snapshot, persona("coastal-merger"))


SNAPSHOT_DIRS = sorted(p for p in (SIM / "snapshots").glob("*/*") if p.is_dir())


def test_the_snapshots_are_the_ones_the_cases_name():
    names = {p.relative_to(SIM / "snapshots").as_posix() for p in SNAPSHOT_DIRS}
    assert names == {"coastal-merger/empty", "coastal-merger/after-s2", "coastal-merger/after-s4", "coastal-merger/after-v3-s8",
                     "coastal-merger/after-complete-s21", "coastal-merger/after-cio-s4", "coastal-merger/after-boundary-s2",  # where scripts start, not probes
                     "holdout-hospitals/empty", "holdout-hospitals/after-dump", "holdout-hospitals/after-discover"}
    for case_path in sorted((SIM / "probes").glob("*.yaml")):
        case = probe.load_case(str(case_path))
        # Every probe runs on coastal-merger; holdout-hospitals only where it has a vault that far along.
        assert "coastal-merger" in case["snapshot"] and set(case["snapshot"]) <= {"coastal-merger", "holdout-hospitals"}, case_path


@pytest.mark.parametrize("snapshot", SNAPSHOT_DIRS, ids=lambda p: p.relative_to(SIM / "snapshots").as_posix())
def test_every_snapshot_is_a_clean_vault_with_its_personas_inbox(snapshot):
    assert not (snapshot / ".claude" / "skills").exists(), "the plugin is installed at probe time, never stored"
    assert not (snapshot / ".git").exists()
    stale = probe.inbox_problems(snapshot, persona(snapshot.parent.name))
    assert len(stale) == 0
    check = subprocess.run([sys.executable, str(sim.PLANNER), "check", "--vault", str(snapshot)],
                           capture_output=True, text=True)
    assert check.returncode == 0
    assert re.search(r"planner check: 0 errors,", check.stdout) is not None


def test_the_snapshot_inboxes_are_in_git_although_a_vault_ignores_them():
    """A vault's .gitignore holds .inbox/, and git reads it inside the snapshot too, so they are added with -f."""
    tracked = subprocess.run(["git", "ls-files", "tests/sim/snapshots"], cwd=REPO, capture_output=True, text=True).stdout
    if not tracked.strip():
        pytest.skip("the snapshots are not committed yet")
    for snapshot in SNAPSHOT_DIRS:
        for doc in (snapshot / ".inbox").iterdir():
            assert doc.relative_to(REPO).as_posix() in tracked.split(), doc.name


# ------------------------------------------------------------------ categories

def test_every_brief_item_has_one_category_from_the_fixed_set():
    assert sim.CATEGORIES == ("cross-source-mismatch", "legal-regulatory", "finance-liability", "third-party-contract",
                              "unnamed-stakeholder", "data-identity", "stakeholder-conflict", "timeline", "fact")
    for name in ("coastal-merger", "holdout-hospitals"):
        problems = sim.persona_problems(persona(name))
        count = len(problems)
        assert count == 0, name
    broken = persona("coastal-merger")
    del broken["unaware"][0]["category"]
    broken["knows"][0]["category"] = "vibes"
    problems = sim.persona_problems(broken)
    assert any(p.startswith("unaware U1: 'category' must be one of cross-source-mismatch") for p in problems)
    assert any(p.startswith("knows K1: 'category' must be one of") and p.endswith("not 'vibes'") for p in problems)


def test_the_coastal_mismatches_are_the_four_the_discover_probe_counts():
    items = probe.brief_items(persona("coastal-merger"), ["cross-source-mismatch"])
    assert sorted(i["id"] for i in items) == ["U7", "U8", "W4", "W5"]


def test_the_holdout_has_the_same_shape_and_covers_the_coastal_categories():
    holdout, coastal = persona("holdout-hospitals"), persona("coastal-merger")
    assert holdout.get("holdout") is True
    sizes = [len(holdout[k]) for k in ("knows", "wrong", "unaware", "conflicts", "decisions", "docs")]
    assert 12 <= sizes[0] <= 14 and sizes[1:] == [5, 7, 4, 4, 3]
    used = {i["category"] for k in ("unaware", "wrong") for i in coastal[k]}
    held = {i["category"] for k in ("unaware", "wrong") for i in holdout[k]}
    assert used <= held
    assert sum(1 for i in probe.brief_items(holdout, ["cross-source-mismatch"])) >= 3
    for script in ("default", "smoke"):
        problems = sim.script_problems(yaml.safe_load((SIM / "scripts" / f"{script}.yaml").read_text()), holdout)
        count = len(problems)
        assert count == 0


# ------------------------------------------------------------------ flag detection

ITEM = {"id": "U7", "category": "cross-source-mismatch", "keywords": ["99.5%", "99.9%", "service level"]}


def flags(text, final=(), start=()):
    spoken = [{"turn": 1, "speaker": "lead", "text": "go"}, {"turn": 2, "speaker": "assistant", "text": text}]
    return probe.item_flags(ITEM, spoken, probe.flag_spots(list(final)), probe.flag_spots(list(start)))


def test_a_question_flags_the_item():
    row = flags("SeaBook runs 24/7. Which service level does one journey get, if RailCore only offers 99.5%?")
    assert row["status"] == "flagged" and row["hit"]["how"] == "question" and row["hit"]["turn"] == 2


def test_a_cue_word_flags_the_item_even_inside_a_list():
    row = flags("Here's what I think exists:\n1. SeaBook: 99.9% target (SRC-01)\n2. RailCore: 99.5%, which conflicts with SRC-01")
    assert row["status"] == "flagged" and row["hit"]["how"] == "cue" and row["hit"]["in_list"]
    assert "conflicts with SRC-01" in row["hit"]["excerpt"]


def test_a_read_back_list_with_no_cue_is_listed():
    text = ("Here's what I think exists:\n1. SeaBook: 99.9% availability May to September (SRC-01)\n"
            "2. RailCore: vendor SLA 99.5%, right?\n\nIs each line right?")
    row = flags(text)
    assert row["status"] == "listed" and row["hit"]["how"] is None and row["hit"]["in_list"]


def test_an_unknown_in_the_final_vault_flags_the_item_and_one_already_there_does_not():
    text = "1. SeaBook: 99.9% (SRC-01)"
    page = ("11-unknowns-and-risks.md", "## Unknowns\n\n### UNK-010 Which SLA\n\n- **Question:** 99.9% or 99.5%?\n\n## Risks\n")
    row = flags(text, final=[page])
    assert row["status"] == "flagged" and row["hit"]["how"] == "vault"
    assert row["hit"]["vault"]["file"] == "11-unknowns-and-risks.md"
    assert flags(text, final=[page], start=[page])["status"] == "listed", "the snapshot already held it"
    capture = ("sessions/s.md", "## Captures\n\n- [unknown] (claude) Which of 99.9% and 99.5% holds? ^c01\n")
    assert flags(text, final=[capture])["status"] == "flagged"
    risk = ("11-unknowns-and-risks.md", "## Risks\n\n### R-02 Weaker SLA\n\n- **Notes:** one journey inherits 99.9% at best\n")
    assert flags(text, final=[risk])["status"] == "flagged"


def test_an_item_no_turn_names_is_never():
    assert flags("Nothing about availability here.")["status"] == "never"


def test_cue_words_and_confirmation_tags():
    for text in ("the two lists differ", "they disagree", "SRC-01 and SRC-02 contradict each other", "a mismatch",
                 "both sources say", "two different numbers", "this doesn't match", "inconsistent dates",
                 "I'll flag it"):
        assert probe.has_cue(text), text
    for text in ("a different target", "the lists agree", "matches SRC-01"):
        assert not probe.has_cue(text), text
    assert probe.is_question("Which one does the mandate accept?")
    assert not probe.is_question("SeaBook is 99.9%, right?") and not probe.is_question("Is that right?")
    assert not probe.is_question("RailCore: 99.5% (yes/no)?")


# ------------------------------------------------------------------ decisions and options

def test_decided_lines_and_the_yes_that_makes_one_the_leads(tmp_path):
    (tmp_path / "sessions").mkdir()
    (tmp_path / "sessions" / "s.md").write_text(
        "- [thought] (lead) that's decided, grill to confirm ^c01\n- [idea] (lead) x → keep: [[a|A]] (decided) ^c02\n"
        "| D1 | assumption | decided | x |\n", encoding="utf-8")
    (tmp_path / "01-goals.md").write_text("---\nstate: decided\n---\n- **Decision:** [[s]]\n", encoding="utf-8")
    lines = probe.decided_lines(tmp_path)
    assert sum(lines.values()) == 3  # the keep mark "(decided)" points at a decision; it is not one
    assert not any("grill to confirm" in line for _, line in lines)
    assert probe.explicit_yes("Yes, go with option A.", asked=True)
    assert not probe.explicit_yes("Yes.", asked=False) and not probe.explicit_yes("Eyes on it", asked=True)


def test_a_decision_written_during_a_probe_fails_decisions_recorded(tmp_path):
    env = {"SIM_STUB_WRITE": "sessions/stub.md::| G9 | inkling | decided | [[stub#^c99]] |"}
    code, out, err, runs = run_probe(tmp_path, "dump-sweep", "coastal-merger", env=env)
    assert code == 1, err
    assert "FAIL decisions-recorded: decisions recorded: 1" in out
    assert "T2 sessions/stub.md" in out, "the decision is pinned to the turn that wrote it"


OPTIONS = """Three options.

**Option A: Link the records**
- Costs: three months.
- Rules out: one view on day one.
- Owner: the Northway Platform team.

### Option B — Merge the records
Expensive clean-up. It gives up the April date, and UNK-004 is open.

**Option C: A new account**
- Costs: a new identity provider.

I prefer A.
Option A is the one I would pick.

Which is closest?"""


def test_options_are_read_from_their_labels_and_a_repeated_label_ends_them():
    blocks = probe.option_blocks(OPTIONS)
    assert [b["label"] for b in blocks] == ["A", "B", "C"]
    assert "I prefer A" not in blocks[2]["text"]
    terms = probe.stakeholder_terms(persona("coastal-merger"))
    parts = [probe.mechanical_parts(b["text"], terms) for b in blocks]
    assert parts[0] == {"costs": True, "rules_out": True, "stakeholder_or_unknown": True}
    assert parts[1] == {"costs": True, "rules_out": True, "stakeholder_or_unknown": True}
    assert parts[2] == {"costs": True, "rules_out": False, "stakeholder_or_unknown": False}
    assert probe.option_blocks("1. **SeaBook** runs ferry\n2. **RailCore** runs rail") == [], "a numbered list is not options"


def test_the_options_judge_counts_a_part_only_with_a_quote_from_the_turn(tmp_path):
    code, out, err, runs = run_probe(tmp_path, "shape-options", "coastal-merger", env=reply(tmp_path, OPTIONS))
    assert code == 1, err
    assert "PASS option-count: options offered: 3 in T2, read from their labels" in out
    assert "FAIL option-parts: options naming each part: costs 3 of 3, rules-out 2 of 3, stakeholder-or-unknown 2 of 3" in out
    assert "judge called" in out
    stub_log = [c for c in (runs[0] / "raw").iterdir() if "judge-options" in c.name]
    assert len(stub_log) == 1
    good = [{"label": "C", "search": "read C", "label_quote": "A new account", "costs": {"present": True, "quote": "x"},
             "rules_out": {"present": True, "quote": "a new identity provider"},
             "stakeholder_or_unknown": {"present": True, "quote": "words the turn never says"}}]
    assert probe.options_judge_problems({"options": good}, ["C"]) == []
    assert probe.quoted("a new identity provider", OPTIONS) and not probe.quoted("words the turn never says", OPTIONS)
    assert probe.options_judge_problems({"options": good}, ["A", "C"])[0].startswith("'options' must list exactly")


# ------------------------------------------------------------------ blind output

def brief_strings(data):
    """Every ID, keyword and piece of brief text in a persona: what blind output must never hold. Text of one or
    two words, such as the option "never", is left out: it says nothing about the brief and is in ordinary output."""
    strings = []
    for kind in sim.ID_KINDS:
        for item in data.get(kind) or []:
            strings += [item["id"], *item["keywords"]]
            for field in sim.ITEM_FIELDS[kind] + ("owner", "refuse_until"):
                value = item.get(field)
                values = [str(v) for v in value] if isinstance(value, list) else [str(value)] if value else []
                strings += [v for v in values if len(v.split()) >= 3]
    return strings + [" ".join(data["opening"].split())]


def leaks(text, data, tmp_path):
    flat = text.replace(str(tmp_path.resolve()), "").replace(str(tmp_path), "")
    words = [s for s in brief_strings(data) if not re.fullmatch(r"[KWUCD]\d+", s)]
    ids = [s for s in brief_strings(data) if re.fullmatch(r"[KWUCD]\d+", s)]
    return (sum(1 for w in words if sim.mentions(flat, [w]))
            + sum(1 for i in ids if re.search(rf"(?<![A-Za-z0-9]){i}(?![0-9])", flat)))


HOLDOUT_REPLY = """Here's what I think exists:
1. Fenwick runs Ardent PAS and MyFenwick at 99.9% (SRC-01)
2. Calder runs Keystone PAS; its booking module is 99.0%, 8am to 6pm, which conflicts with SRC-01
3. The board paper says a shared PAS and 70,000 patients. Do the two lists count the waiting list the same way?
4. The Keystone contract ends September 2027 with a 9-month notice period (SRC-02)"""


def test_blind_output_holds_no_id_keyword_or_brief_text(tmp_path):
    code, out, err, runs = run_probe(tmp_path, "discover-implications", "holdout-hospitals", "--blind",
                                     env=reply(tmp_path, HOLDOUT_REPLY))
    assert code == 1, "the stub's session fails the criteria"
    data = persona("holdout-hospitals")
    count = leaks(out + err, data, tmp_path)
    assert count == 0
    assert re.search(r"cross-source-mismatch: \d of 4 flagged, \d listed, \d never", out) is not None
    detail = (runs[0] / probe.DETAIL_NAME).read_text(encoding="utf-8")
    assert leaks(detail, data, tmp_path) > 0, "the detail went to the file instead"
    record = json.loads((runs[0] / "probe.json").read_text(encoding="utf-8"))
    count = leaks(json.dumps(record), data, tmp_path)
    assert count == 0 and record["blind"] is True


def test_the_holdout_is_blind_without_the_flag(tmp_path):
    code, out, err, runs = run_probe(tmp_path, "shape-options", "holdout-hospitals", env=reply(tmp_path, HOLDOUT_REPLY))
    assert code == 1
    assert ", blind." in out and "blind: item detail is in detail-DO-NOT-READ-WHEN-BLIND.md" in out
    count = leaks(out + err, persona("holdout-hospitals"), tmp_path)
    assert count == 0


def test_blind_on_coastal_hides_its_items_and_open_output_shows_them(tmp_path):
    text = "1. Halyard CRM in Kestrel Bay (SRC-01)\n2. Signal CRM in Dunmere, so the two centres use a separate CRM each?"
    code, out, err, _ = run_probe(tmp_path, "discover-implications", "coastal-merger", "--blind", env=reply(tmp_path, text))
    assert code == 1 and leaks(out + err, persona("coastal-merger"), tmp_path) == 0
    assert "cross-source-mismatch: 1 of 4 flagged, 0 listed, 3 never" in out
    code, out, err, _ = run_probe(tmp_path / "open", "discover-implications", "coastal-merger", env=reply(tmp_path, text))
    assert "- W4 (cross-source-mismatch): FLAGGED at T2" in out and "its sentence is a question" in out


def test_a_broken_holdout_persona_is_refused_without_naming_its_problems(tmp_path):
    data = persona("holdout-hospitals")
    del data["unaware"][2]["category"]
    data["wrong"][1]["keywords"] = ["mandate", "x y"]
    path = tmp_path / "holdout-broken.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    code, out, err, _ = run_probe(tmp_path, "dump-sweep", str(path))
    assert code == 2 and "the persona is not valid (2 problems, listed in" in err
    count = leaks(out + err, persona("holdout-hospitals"), tmp_path)
    assert count == 0


# ------------------------------------------------------------------ the loop ledger and exit codes

SWEEP = ("Before we go on: is there a lawful basis for linking the two companies' records? Who signs off the "
         "loyalty points on the balance sheet? And do the hotel contract terms let you share booking data?")


def test_exit_0_when_every_run_passes_and_the_ledger_adds_up(tmp_path):
    code, out, err, runs = run_probe(tmp_path, "dump-sweep", "coastal-merger", "--runs", "2", env=reply(tmp_path, SWEEP))
    assert code == 0, out + err
    assert "PASS categories-raised-first: categories raised first by the assistant: 3 of 4 (legal-regulatory, " \
           "finance-liability, third-party-contract; need at least 3)" in out
    assert [r.name.rsplit("-", 1)[1] for r in runs] == ["1", "2"]
    for run in runs:
        for name in ("transcript.jsonl", "transcript.html", probe.DETAIL_NAME, "probe.json", "vault-check.txt"):
            assert (run / name).is_file(), name
        assert (run / "vault" / ".git").is_dir()
    ledger = json.loads((tmp_path / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["spent_usd"] == pytest.approx(sum(json.loads((r / "probe.json").read_text())["spent_usd"] for r in runs))
    assert ledger["invocations"][0]["exit"] == 0 and ledger["invocations"][0]["runs"] == 2
    code, out, _, _ = run_probe(tmp_path, "dump-sweep", "coastal-merger", env=reply(tmp_path, SWEEP))
    assert code == 0
    assert f"Loop spend so far ${ledger['spent_usd']:.2f} of $5.00" in out
    assert len(json.loads((tmp_path / "ledger.json").read_text())["invocations"]) == 2


def test_exit_1_when_a_criterion_fails(tmp_path):
    code, out, err, runs = run_probe(tmp_path, "dump-sweep", "coastal-merger")
    assert code == 1, err
    assert "FAIL categories-raised-first" in out and "Exit 1." in out


def test_exit_1_and_no_run_when_the_loop_budget_would_be_passed(tmp_path):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"spent_usd": 4.5, "invocations": [{"spent_usd": 4.5}]}), encoding="utf-8")
    before = ledger.read_bytes()
    code, out, err, runs = run_probe(tmp_path, "dump-sweep", "coastal-merger", budget="1", loop_budget="5")
    assert code == 1
    assert "refused to start. The loop has spent $4.50 of $5.00" in out and "would take it to $5.50" in out
    assert runs == [] and ledger.read_bytes() == before


def test_exit_1_on_a_budget_stop(tmp_path):
    code, out, err, runs = run_probe(tmp_path, "dump-sweep", "coastal-merger", budget="0.5",
                                     env={"SIM_STUB_COST": "0.3", **reply(tmp_path, SWEEP)})
    assert code == 1, err
    assert "ended budget" in out and "BUDGET STOP" in out


def test_exit_2_on_a_tool_failure_and_the_spend_still_reaches_the_ledger(tmp_path):
    code, out, err, runs = run_probe(tmp_path, "dump-sweep", "coastal-merger", env={"SIM_STUB_DROP": "total_cost_usd"})
    assert code == 2
    assert "TOOL FAILURE" in out and "CLI output changed" in out
    assert json.loads((tmp_path / "ledger.json").read_text())["invocations"][0]["exit"] == 2
    assert (runs[0] / "transcript.html").is_file()


def test_exit_2_on_a_bad_case_persona_or_ledger(tmp_path):
    assert run_probe(tmp_path, "no-such-case", "coastal-merger")[0] == 2
    assert run_probe(tmp_path, "dump-sweep", "no-such-persona")[0] == 2
    (tmp_path / "ledger.json").write_text("not json", encoding="utf-8")
    code, _, err, runs = run_probe(tmp_path, "dump-sweep", "coastal-merger")
    assert code == 2 and "is not JSON" in err and runs == []


def test_a_case_is_refused_with_every_problem_named():
    problems = probe.case_problems({"snapshot": {"coastal-merger": "nope"}, "opening": "/planner:fly", "cap": 0,
                                    "criteria": [{"check": "vibes"}, {"check": "flagged-share", "category": "x"}]})
    assert "snapshot coastal-merger/nope is not a folder in " + str(probe.SNAPSHOTS) in problems
    assert any(p.startswith("'opening' must start with one of") for p in problems)
    assert any("'cap'" in p for p in problems)
    assert any("check 'vibes' is not one of" in p for p in problems)
    assert "criteria[2] flagged-share: needs at_least" in problems
    assert "criteria[2] flagged-share: 'x' is not a category" in problems


@pytest.mark.parametrize("missing", ["--budget", "--loop-ledger", "--loop-budget", "--model", "--persona-model",
                                     "--judge-model", "--persona"])
def test_money_models_and_the_ledger_are_required(missing):
    argv = ["dump-sweep", "--persona", "coastal-merger", "--budget", "1", "--loop-ledger", "l.json",
            "--loop-budget", "5", *MODELS]
    i = argv.index(missing)
    del argv[i:i + 2]
    with pytest.raises(SystemExit) as exc:
        probe.parse_args(argv)
    assert exc.value.code == 2


def test_every_case_opens_with_its_mode_and_fills_in_from_both_personas():
    for case_path in sorted((SIM / "probes").glob("*.yaml")):
        case = probe.load_case(str(case_path))
        for name in ("coastal-merger", "holdout-hospitals"):
            text = probe.opening_text(case, persona(name))
            assert text.startswith(f"/planner:{case['mode']}") and "{" not in text
    shape = probe.load_case("shape-options")
    assert probe.opening_text(shape, persona("coastal-merger")) == \
        '/planner:shape What does "one account" mean for the first release?'


@pytest.mark.parametrize("name", ["coastal-merger", "holdout-hospitals"])
def test_every_real_persona_passes_its_own_validation(name):
    """A persona edited for a probe must still load, or the paid run stops before it starts."""
    import yaml as _yaml
    data = _yaml.safe_load((REPO / "tests" / "sim" / "personas" / f"{name}.yaml").read_text(encoding="utf-8"))
    assert sim.persona_problems(data) == []



# ------------------------------------------------------------------ the question ledger and the reviewers

FIXTURE = REPO / "examples" / "unified-booking"


def fake_run(vault):
    import types
    return types.SimpleNamespace(vault=vault)


def test_owed_copies_disposed_passes_when_every_copy_has_a_valid_row(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    passed, summary, detail = probe.owed_copies_disposed(fake_run(vault), {"severity": "any"})
    assert passed and detail == []
    assert summary == ("owed copies (any) with a disposition: 57 of 57; ledger rows planner check flags: 0 "
                       "(need every copy disposed and no flagged row)")


def test_owed_copies_disposed_fails_on_an_undisposed_copy_or_a_flagged_row(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    ledger = vault / "11-unknowns-and-risks.md"
    text = ledger.read_text(encoding="utf-8")
    text = text.replace("| Q-REG-01@INI-002 | not-applicable |", "| Q-REG-01@INI-002 | open |")
    ledger.write_text(text.replace("| Q-FIN-04@SV-01 | not-applicable | reason:", "| Q-FIN-04@SV-01 | not-applicable | why:"),
                      encoding="utf-8")
    passed, summary, detail = probe.owed_copies_disposed(fake_run(vault), {"severity": "any"})
    assert not passed
    assert "with a disposition: 56 of 57; ledger rows planner check flags: 2" in summary
    assert "- Q-REG-01@INI-002: open" in detail and any(" E801 " in line for line in detail)
    assert probe.owed_copies_disposed(fake_run(vault), {"severity": "high"})[1].startswith(
        "owed copies (high) with a disposition: 15 of 15")


def session_with(vault, *coverage):
    (vault / "sessions").mkdir(parents=True, exist_ok=True)
    lines = "".join(f"- **Coverage:** {c}\n" for c in coverage)
    (vault / "sessions" / "2026-10-06-x.md").write_text(f"---\nid: x\n---\n\n## Reviews\n\n{lines}", encoding="utf-8")


def test_area_coverage_needs_a_result_for_every_area(tmp_path):
    ran = "FIN found 3; DAT checked, none; PTN found 2, 1 dropped; REG checked, none; OPS found 1"
    session_with(tmp_path, ran)
    assert probe.area_coverage(fake_run(tmp_path), {"require": "ran"})[:2] == (
        True, "review checkpoints recorded: 1; with every area to run: 1 of 1")
    session_with(tmp_path, ran, "FIN found 1; DAT did not run (no findings file); PTN checked, none; REG checked, none; "
                 "OPS checked, none")
    assert probe.area_coverage(fake_run(tmp_path), {"require": "ran"})[0] is False
    assert probe.area_coverage(fake_run(tmp_path), {"require": "reported"})[0] is True
    session_with(tmp_path, "FIN found 1; DAT checked, none")
    passed, _, detail = probe.area_coverage(fake_run(tmp_path), {"require": "reported"})
    assert not passed and "no result for PTN, REG, OPS" in detail[0]


def test_area_coverage_fails_when_no_checkpoint_ran(tmp_path):
    session_with(tmp_path)
    assert probe.area_coverage(fake_run(tmp_path), {"require": "reported"})[:2] == (
        False, "review checkpoints recorded: 0; with every area to have a result: 0 of 0")


def test_a_case_with_close_runs_the_close_session_and_reads_the_ledger_after_it(tmp_path):
    code, out, err, runs = run_probe(tmp_path, "discover-reviewers", "coastal-merger")
    assert code == 1, out + err  # the stub writes no ledger, so the criteria fail; the tool did not
    assert "FAIL area-coverage: review checkpoints recorded: 0" in out
    assert "FAIL owed-copies-disposed: owed copies (high) with a disposition: 0 of" in out
    assert "PASS taken-copies-recorded: copies and findings the lead took in a capture with a valid row: 0 of 0" in out
    turns = [json.loads(line) for line in (runs[0] / "transcript.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {t["session"] for t in turns if t.get("speaker") == "assistant"} == {1, 2}
    assert any(t.get("speaker") == "lead" and t.get("text") == "/planner:close" for t in turns)


def test_close_must_be_a_turn_cap():
    case = probe.load_case("discover-reviewers")
    case["close"] = True
    assert "'close' must be the close session's cap in assistant turns, at least 1, or left out" in probe.case_problems(case)


def test_the_assistant_may_dispatch_subagents():
    assert "Agent" in sim.ALLOWED_TOOLS


def taken_session(vault, *captures, reviews=""):
    lines = "".join(f"- [thought] (lead) {c} ^c{n:02d}\n" for n, c in enumerate(captures, 1))
    (vault / "sessions" / "2026-11-21-take.md").write_text(
        f"---\nid: 2026-11-21-take\ntype: session\n---\n\n## Captures\n\n{lines}\n{reviews}", encoding="utf-8")


REVIEWS = """## Reviews

### 1. after the read-back, 2026-11-21

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | Q-FIN-03@SV-01 | Who carries the points? | "because points are earned at reservation" in [[04a-capability-delta]] |
| F1.2 | FIN | high | new | Who signs off a points conversion? | "because points are earned at reservation" in [[04a-capability-delta]] |
"""


def test_taken_copies_recorded_passes_when_every_take_has_a_valid_row(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    taken_session(vault, "Q-FIN-03@SV-01: finance carries them", "Q-FIN-02@INI-002: asked Platform",
                  "Q-OPS-01@APP-*: each team runs its own", "F1.1: finance again", "Not a take at all",
                  reviews=REVIEWS)
    passed, summary, detail = probe.taken_copies_recorded(fake_run(vault), {})
    assert passed and detail == [], detail
    assert summary == "copies and findings the lead took in a capture with a valid row: 4 of 4"


def test_taken_copies_recorded_fails_on_a_take_left_open_or_never_written(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    ledger = vault / "11-unknowns-and-risks.md"
    text = ledger.read_text(encoding="utf-8")
    old = next(l for l in text.splitlines() if l.startswith("| Q-FIN-03@SV-01 | answered |"))
    ledger.write_text(text.replace(old, "| Q-FIN-03@SV-01 | open |  |  |  |"), encoding="utf-8")
    taken_session(vault, "Q-FIN-03@SV-01: finance carries them", "F1.2: nobody signs it off yet",
                  "Q-FIN-09@SV-01: no such entry", reviews=REVIEWS)
    passed, summary, detail = probe.taken_copies_recorded(fake_run(vault), {})
    assert not passed
    assert summary == "copies and findings the lead took in a capture with a valid row: 0 of 3"
    assert detail == ["- sessions/2026-11-21-take.md ^c01 Q-FIN-03@SV-01: open",
                      "- sessions/2026-11-21-take.md ^c02 F1.2: no reviewer row asks \"Who signs off a points conversion?\"",
                      "- sessions/2026-11-21-take.md ^c03 Q-FIN-09@SV-01: not an owed copy"]


def test_the_discover_reviewers_probe_needs_high_copies_and_every_take_recorded():
    case = probe.load_case("discover-reviewers")
    checks = {c["check"]: c for c in case["criteria"]}
    assert checks["owed-copies-disposed"]["severity"] == "high"
    assert "taken-copies-recorded" in checks
    comment = (SIM / "probes" / "discover-reviewers.yaml").read_text(encoding="utf-8")
    assert "may stay open by design" in comment


def test_a_read_back_that_asks_for_the_yes_in_words_counts_and_generated_rows_decide_nothing(tmp_path):
    assert probe.ASKS_FOR_YES.search("I need an explicit yes to write it, or the changes you want.")
    assert not probe.ASKS_FOR_YES.search("CON-002 is now decided and committed.")
    (tmp_path / "a.md").write_text("- **State:** decided\n<!-- generated:contracts-consumed sha=1 -->\n"
                                   "| CON-1 | X | decided |\n<!-- /generated:contracts-consumed -->\n", encoding="utf-8")
    assert sum(probe.decided_lines(tmp_path).values()) == 1


def test_a_case_can_take_news_and_blocked_grill_switches_the_override_off():
    case = probe.load_case("blocked-grill")
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    after = probe.sim.with_news(persona, case["news"])
    assert not after["decisions"][0]["override_if_blocked"] and persona["decisions"][0]["override_if_blocked"]
    assert "override it once" not in probe.sim.persona_prompt(after).split("D1:")[1].split("\n- D2")[0]
