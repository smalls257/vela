"""The session simulator, run end to end against the scripted fake claude in tests/sim/stub/. Nothing here calls a
model or spends money: every run passes --stub, and --out keeps results in tmp_path."""
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest
import yaml

from conftest import REPO

SIM = REPO / "tests" / "sim"
spec = importlib.util.spec_from_file_location("sim_run", SIM / "run.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]
TWO_SESSIONS = {"name": "two", "sessions": [
    {"mode": "dump", "cap": 3, "planner": "/planner:dump {opening}", "baseline": "Let's dump what we know. {opening}"},
    {"mode": "close", "cap": 3, "planner": "/planner:close", "baseline": "Close out this session."}]}


def simulate(tmp_path, *extra, env=None, arms="planner"):
    """One stub run. Returns (exit code, stderr, run folder or None, stub call log)."""
    script = tmp_path / "two.yaml"
    script.write_text(yaml.safe_dump(TWO_SESSIONS), encoding="utf-8")
    out, log = tmp_path / "results", tmp_path / "stub-log.jsonl"
    full_env = {**os.environ, "SIM_STUB_LOG": str(log), **(env or {})}
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "coastal-merger", "--stub", "--script", str(script),
                           "--arms", arms, "--out", str(out), *MODELS, *extra],
                          capture_output=True, text=True, env=full_env, timeout=600)
    runs = sorted(out.iterdir()) if out.is_dir() else []
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []
    return done.returncode, done.stderr, runs[0] if runs else None, calls


def entries(arm_dir):
    return [json.loads(line) for line in (arm_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()]


def repo_state():
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, timeout=60).stdout
    results = sorted(p.name for p in (SIM / "results").iterdir()) if (SIM / "results").is_dir() else []
    return status, results


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    """All three arms over the two-session script, with the repo's state taken before and after."""
    tmp = tmp_path_factory.mktemp("sim")
    before = repo_state()
    code, err, run_dir, calls = simulate(tmp, "--budget", "5", arms="planner,planner-seuss,baseline")
    return {"code": code, "err": err, "run": run_dir, "calls": calls, "tmp": tmp, "before": before, "after": repo_state()}


def test_full_run_exits_0_and_writes_every_output(full_run):
    assert full_run["code"] == 0, full_run["err"]
    run_dir = full_run["run"]
    assert (run_dir / "compare.html").is_file() and (run_dir / "run.json").is_file()
    for arm in ("planner", "planner-seuss", "baseline"):
        for name in ("transcript.jsonl", "transcript.html", "viewer.html", "scorecard.json", "scorecard.md",
                     "vault-git-log.txt", "vault-check.txt"):
            assert (run_dir / arm / name).is_file(), f"{arm}/{name}"
        assert (run_dir / arm / "vault" / ".git").is_dir()
    compare = (run_dir / "compare.html").read_text(encoding="utf-8")
    assert "planner-seuss/transcript.html" in compare and "baseline/viewer.html" in compare


def test_transcript_records_both_sessions_turn_by_turn(full_run):
    log = entries(full_run["run"] / "planner")
    spoken = [e for e in log if e["speaker"] in ("lead", "assistant")]
    assert [e["turn"] for e in spoken] == list(range(1, len(spoken) + 1))
    assert {e["session"] for e in spoken} == {1, 2}
    assert spoken[0]["scripted"] and spoken[0]["text"].startswith("/planner:dump The CIO's mandate")
    assistant = [e for e in spoken if e["speaker"] == "assistant"]
    assert all(e["cost_usd"] == 0.01 and e["tool_calls"][0]["name"] == "Bash" for e in assistant)
    ends = [e for e in log if e.get("event") == "session-end"]
    assert [e["reason"] for e in ends] == ["persona-end", "persona-end"]
    assert not any(e["text"] == "[END]" for e in spoken), "the persona's [END] ends the session and is not a turn"


def test_transcript_html_escapes_every_turn_and_holds_no_script(full_run):
    page = (full_run["run"] / "planner" / "transcript.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(" in page
    assert "<script" not in page.lower()
    assert "<details><summary>1 tool calls</summary>" in page
    assert "<h2>Session 1: dump" in page and "<h2>Session 2: close" in page


def test_resume_is_used_from_the_second_turn_of_each_session(full_run):
    calls = [c["argv"] for c in full_run["calls"] if c["role"] == "assistant" and "planner" in c["cwd"].split(os.sep)]
    assert len(calls) == 4
    for first, second in (calls[0:2], calls[2:4]):
        assert "--resume" not in first
        assert "--resume" in second
    log = entries(full_run["run"] / "planner")
    ids = [e["session_id"] for e in log if e["speaker"] == "assistant"]
    assert calls[1][calls[1].index("--resume") + 1] == ids[0]


def test_every_assistant_call_is_pinned_and_permissioned(full_run):
    for call in (c["argv"] for c in full_run["calls"] if c["role"] == "assistant"):
        assert call[call.index("--model") + 1] == "test-model"
        assert call[call.index("--permission-mode") + 1] == "acceptEdits"
        assert call[call.index("--allowedTools") + 1].split(",") == sim.ALLOWED_TOOLS
        assert "--max-budget-usd" in call and call[-2] == "--"
    for call in (c["argv"] for c in full_run["calls"] if c["role"] in ("persona", "judge")):
        assert call[call.index("--tools") + 1] == ""
        assert call[call.index("--model") + 1] in ("test-persona", "test-judge")


def test_the_gh_stub_is_first_on_path_and_says_why_it_failed(full_run):
    for call in full_run["calls"]:
        arm_dir = full_run["run"] / call["cwd"].split(str(full_run["run"]) + os.sep, 1)[1].split(os.sep)[0]
        assert call["gh"] == str(arm_dir / "bin" / "gh")
    assistant = [e for e in entries(full_run["run"] / "planner") if e["speaker"] == "assistant"]
    assert sim.GH_MESSAGE in assistant[0]["text"]


def test_seuss_examples_reach_voice_local_only_in_the_seuss_arm(full_run):
    seuss, plain = full_run["run"] / "planner-seuss" / "vault", full_run["run"] / "planner" / "vault"
    sources = sorted(p.relative_to(SIM / "voices" / "seuss-style") for p in (SIM / "voices" / "seuss-style").glob("*/*.md"))
    copied = sorted(p.relative_to(seuss / "voice" / "local") for p in (seuss / "voice" / "local").glob("*/*.md"))
    assert copied == sources and len(sources) == 6
    assert not (plain / "voice" / "local").exists()
    # house-voice reads every active example; the committed seed is retired so the owner's voice is all it reads.
    for vault, state in ((seuss, "retired"), (plain, "active")):
        for seed in (vault / "voice" / "examples").glob("*/*.md"):
            committed = subprocess.run(["git", "show", f"HEAD:{seed.relative_to(vault).as_posix()}"], cwd=vault,
                                       capture_output=True, text=True, timeout=60).stdout
            assert f"\nstate: {state}\n" in committed, seed
    status = subprocess.run(["git", "status", "--porcelain"], cwd=seuss, capture_output=True, text=True, timeout=60).stdout
    assert "voice/" not in status, "voice/local must stay gitignored and the retirement committed"


def test_house_voice_reads_local_owner_examples_first():
    """The Seuss arm relies on this ordering and on two owner examples per type being enough."""
    text = (REPO / "plugin" / "skills" / "house-voice" / "SKILL.md").read_text(encoding="utf-8")
    assert "local `owner` and `owner-edit` examples first" in text
    assert "fewer than two active examples" in text


def test_baseline_vault_has_no_skills_and_no_plugin(full_run):
    vault = full_run["run"] / "baseline" / "vault"
    assert not (vault / ".claude" / "skills").exists()
    assert (full_run["run"] / "planner" / "vault" / ".claude" / "skills" / "planner" / "scripts" / "planner").is_file()
    for call in full_run["calls"]:
        if call["role"] != "assistant":
            continue
        in_baseline = f"{os.sep}baseline{os.sep}" in call["cwd"] + os.sep
        assert ("--plugin-dir" in call["argv"]) is not in_baseline
        if in_baseline:
            assert not call["argv"][-1].startswith("/")


def test_scorecard_drops_claims_without_a_valid_citation(full_run):
    card = json.loads((full_run["run"] / "planner" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["unaware"][0]["surfaced"] is True
    assert card["wrong"][0]["challenged"] is False and "dropped" in card["wrong"][0]
    assert card["knows"][0]["captured"] is True and card["knows"][1]["captured"] is False
    assert len(card["dropped"]) == 2
    assert card["max_questions_in_one_turn"]["count"] == 1
    md = (full_run["run"] / "planner" / "scorecard.md").read_text(encoding="utf-8")
    assert "## Dropped claims" in md and "no-such-page.md" in md


def test_nothing_is_written_outside_the_run_folder(full_run):
    assert full_run["before"] == full_run["after"], "the repo changed during a run"
    assert sorted(p.name for p in full_run["tmp"].iterdir()) == ["results", "stub-log.jsonl", "two.yaml"]
    run_dir = str(full_run["run"]) + os.sep
    for call in full_run["calls"]:
        assert call["cwd"].startswith(run_dir) and call["tmpdir"].startswith(run_dir)


def test_budget_stop_exits_1_and_still_writes_the_scorecard(tmp_path):
    code, err, run_dir, calls = simulate(tmp_path, "--budget", "1", env={"SIM_STUB_COST": "0.5"})
    assert code == 1, err
    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert [e["reason"] for e in summary["per_arm"]["planner"]["endings"]] == ["budget", "not run: budget"]
    assert summary["spent_usd"] <= 1.0
    assert (run_dir / "planner" / "scorecard.md").is_file() and (run_dir / "planner" / "transcript.html").is_file()
    assert [c["category"] for c in calls if c["role"] == "judge"] == list(sim.JUDGE_CATEGORIES)


def test_a_missing_json_field_is_a_tool_failure(tmp_path):
    code, err, run_dir, _ = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_DROP": "total_cost_usd"})
    assert code == 2
    assert "total_cost_usd" in err and "CLI output changed" in err
    assert (run_dir / "planner" / "transcript.html").is_file()
    assert not (run_dir / "planner" / "scorecard.json").exists()


def test_bad_judge_json_is_asked_again_once_then_exits_2(tmp_path):
    code, err, run_dir, calls = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_JUDGE": "bad"})
    assert code == 2 and "knows judge's JSON was bad twice" in err
    assert [c["category"] for c in calls if c["role"] == "judge"] == ["knows", "knows"]
    assert (run_dir / "compare.html").is_file()


@pytest.mark.parametrize("missing", ["--budget", "--model", "--persona-model", "--judge-model"])
def test_budget_and_every_model_are_required(missing):
    argv = ["coastal-merger", "--budget", "1", *MODELS]
    i = argv.index(missing)
    del argv[i:i + 2]
    with pytest.raises(SystemExit) as exc:
        sim.parse_args(argv)
    assert exc.value.code == 2


def test_default_arms_are_planner_and_seuss_and_unknown_arms_are_refused():
    assert sim.parse_args(["x", "--budget", "1", *MODELS]).arm_list == ["planner", "planner-seuss"]
    with pytest.raises(SystemExit):
        sim.parse_args(["x", "--budget", "1", "--arms", "planner,plain", *MODELS])


def test_every_persona_and_script_validates():
    """A holdout persona is checked in test_probe.py, by counts only, so a failure here never prints its brief."""
    for persona_path in sorted((SIM / "personas").glob("*.yaml")):
        persona = yaml.safe_load(persona_path.read_text(encoding="utf-8"))
        if persona.get("holdout") is True or persona.get("team_persona") is True:
            continue
        assert sim.persona_problems(persona) == [], persona_path
        for script_path in sorted((SIM / "scripts").glob("*.yaml")):
            script = yaml.safe_load(script_path.read_text(encoding="utf-8"))
            if script.get("persona") not in (None, persona_path.stem):
                continue  # a script written for one persona's topics
            assert sim.script_problems(script, persona) == [], script_path


def test_the_coastal_merger_brief_is_big_and_messy():
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    assert 12 <= len(persona["knows"]) <= 18  # K16-K18: what a lead knows once an app is in sight
    assert 5 <= len(persona["wrong"]) <= 6
    assert 6 <= len(persona["unaware"]) <= 8
    assert 3 <= len(persona["conflicts"]) <= 4
    assert 4 <= len(persona["decisions"]) <= 8 and any(d.get("refuse_until") for d in persona["decisions"])
    assert 3 <= len(persona["docs"]) <= 4
    prompt = sim.persona_prompt(persona)
    for gap in persona["unaware"]:
        assert gap["gap"] not in prompt and gap["why"] not in prompt, "the persona must never see a U item"
    for wrong in persona["wrong"]:
        assert wrong["truth"] not in prompt


def test_the_default_script_runs_the_bigger_sequence():
    script = yaml.safe_load((SIM / "scripts" / "default.yaml").read_text(encoding="utf-8"))
    modes = [s["mode"] for s in script["sessions"]]
    assert modes == ["dump", "close", "discover", "close", "shape", "close", "discover", "close", "shape", "close",
                     "grill", "close"]
    caps = {s["mode"]: s["cap"] for s in script["sessions"]}
    assert caps == {"dump": 14, "discover": 14, "shape": 12, "grill": 16, "close": 6}


def test_a_broken_persona_is_refused_with_every_problem_named():
    problems = sim.persona_problems({"name": "x", "knows": [{"id": "X1"}], "wrong": []})
    assert any("'role'" in p for p in problems)
    assert any("X1" in p for p in problems)
    assert any("'wrong' must be a non-empty list" in p for p in problems)


# Character names and lines a reader would recognise from the published books. None may appear.
PUBLISHED = ["grinch", "lorax", "sneetch", "horton", "yertle", "zax", "truffula", "thneed", "sam-i-am",
             "thing one", "thing two", "whoville", "cat in the hat", "green eggs", "one fish", "places you'll go",
             "i speak for the trees", "bar-ba-loot", "who-hash", "oobleck", "fox in socks", "lifted lorax"]


def test_seuss_style_voice_files_are_original_pastiche_in_the_example_format():
    files = sorted((SIM / "voices" / "seuss-style").glob("*/*.md"))
    assert {p.parent.name for p in files} == {"diagnosis", "decision", "how-it-works"} and len(files) == 6
    for path in files:
        text = path.read_text(encoding="utf-8")
        _, front, body = text.split("---\n", 2)
        meta = yaml.safe_load(front)
        assert meta == {"id": path.stem, "voice_type": path.parent.name, "source": "owner", "author": "@sim-lead",
                        "from": "original pastiche for the simulator, no published text", "state": "active",
                        "added": meta["added"]}
        assert "from: 'original pastiche for the simulator, no published text'\n" in front
        assert re.fullmatch(r"VX-(diagnosis|decision|how-it-works)-00[45]", path.stem)
        lines = [line for line in body.strip().splitlines() if line.strip()]
        assert 4 <= len(lines) <= 8, path
        assert not any(word in body.lower() for word in PUBLISHED), path


def test_a_closed_session_branch_is_merged_into_origin_main_and_an_open_one_is_not(tmp_path):
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    arm_dir = tmp_path / "planner"
    arm_dir.mkdir()
    vault, _ = sim.build_vault(arm_dir, "planner", persona)
    assert sorted(p.name for p in (vault / ".inbox").iterdir()) == sorted(d["name"] for d in persona["docs"])
    for branch, status in (("session/2026-10-05-closed", "closed"), ("session/2026-10-05-open", "open")):
        sim.git("switch", "-q", "-c", branch, "main", cwd=vault)
        name = branch.split("/", 1)[1]
        (vault / "sessions" / f"{name}.md").write_text(f"---\nid: {name}\nstatus: {status}\n---\n", encoding="utf-8")
        sim.git("add", f"sessions/{name}.md", cwd=vault)
        sim.git("commit", "-q", "-m", f"Open session {name}", cwd=vault)
    reports = sim.merge_closed(vault, arm_dir)
    assert reports[0].startswith("merged session/2026-10-05-closed")
    assert reports[1].startswith("not merged: session/2026-10-05-open")
    sim.git("fetch", "-q", "origin", cwd=vault)
    tree = sim.git("ls-tree", "-r", "--name-only", "origin/main", cwd=vault).stdout.split()
    assert "sessions/2026-10-05-closed.md" in tree and "sessions/2026-10-05-open.md" not in tree
    assert sim.merge_closed(vault, arm_dir) == [reports[1]], "a merged branch is not merged twice"


def test_assistant_calls_run_sandboxed_with_only_the_vault_and_origin_writable(tmp_path):
    import json as _json
    argv = sim.assistant_argv("hi", "m", None, 1.0, "planner", tmp_path / "origin.git")
    settings = _json.loads(argv[argv.index("--settings") + 1])
    assert settings["sandbox"] == {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False}
    assert settings["permissions"]["allow"] == ["Bash", f"Edit(/{(tmp_path / 'origin.git').resolve()}/**)"]
    assert "Skill" in argv[argv.index("--allowedTools") + 1].split(",")
    persona = sim.isolation_flags()
    assert "sandbox" not in _json.loads(persona[persona.index("--settings") + 1])


# ------------------------------------------------------------------ the judge and its mechanical evidence

def coastal():
    return yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))


def test_every_brief_item_needs_its_keywords_and_a_broken_list_is_a_tool_error(tmp_path):
    persona = coastal()
    del persona["knows"][3]["keywords"]
    persona["unaware"][0]["keywords"] = []
    persona["wrong"][0]["keywords"] = ["only one"]
    persona["conflicts"][0]["keywords"] = ["CFO", "next summer"]
    problems = sim.persona_problems(persona)
    assert "knows K4: 'keywords' must be a non-empty list" in problems
    assert "unaware U1: 'keywords' must be a non-empty list" in problems
    assert any(p.startswith("wrong W1: give 2 to 4 keywords") for p in problems)
    assert any("conflicts C1: keyword 'next summer' is in the opening" in p for p in problems)
    # The mandate is the opening itself, so K1 may hold it; nothing else may.
    assert not any(p.startswith("knows K1") for p in problems)
    broken = tmp_path / "broken.yaml"
    broken.write_text(yaml.safe_dump(persona), encoding="utf-8")
    with pytest.raises(sim.ToolFailure, match="K4: 'keywords'"):
        sim.load_brief(str(broken), str(SIM / "scripts" / "smoke.yaml"))


def test_keyword_hits_name_turns_and_pages_and_skip_the_templates_own_text():
    persona = {"knows": [{"id": "K4", "keywords": ["FERRYMASTER", "ledger of record"]}],
               "unaware": [{"id": "U1", "keywords": ["lawful basis", "DPO"]}], "wrong": [], "conflicts": [], "decisions": []}
    spoken = [{"turn": 1, "speaker": "lead", "text": "Ask the DPO? And FERRYMASTER."},
              {"turn": 2, "speaker": "assistant", "text": "What is the **lawful basis** for linking records?"},
              {"turn": 3, "speaker": "assistant", "text": "FERRYMASTER is the ledger of record. The endpoint is fine."}]
    pages = [("01-goals.md", "Nothing touches Ferrymaster.", ""),
             ("02-constraints.md", "The ledger of record is a heading.", "The ledger of record is a heading."),
             ("11-unknowns-and-risks.md", "Who owns the lawful basis?", "")]
    hits = sim.keyword_hits(persona, spoken, pages)
    assert hits["K4"]["assistant_turns"] == [{"turn": 3, "keywords": ["FERRYMASTER", "ledger of record"]}]
    assert hits["K4"]["vault_files"] == [{"file": "01-goals.md", "keywords": ["FERRYMASTER"]}]
    assert "lead_turns" not in hits["K4"], "a K item is captured in the vault, whoever said it"
    assert hits["U1"]["lead_turns"] == [{"turn": 1, "keywords": ["DPO"]}]
    assert hits["U1"]["assistant_turns"] == [{"turn": 2, "keywords": ["lawful basis"]}], "endpoint is not DPO"
    assert hits["U1"]["vault_files"] == [{"file": "11-unknowns-and-risks.md", "keywords": ["lawful basis"]}]


def test_a_gap_the_lead_raised_first_is_not_counted_for_the_assistant():
    hit = {"kind": "unaware", "keywords": ["GDPR"], "vault_files": [],
           "assistant_turns": [{"turn": 10, "keywords": ["GDPR"]}], "lead_turns": [{"turn": 9, "keywords": ["GDPR"]}]}
    no = {"id": "U1", "surfaced": False}
    assert sim.disagreement("unaware", no, hit, False) == [], "the lead said it first, so no is right"
    yes = {"id": "U1", "surfaced": True, "turn": 10, "quote": "GDPR"}
    assert sim.disagreement("unaware", yes, hit, True) == [
        "the lead said GDPR in T9 before the cited T10, so the assistant may not have raised it first"]
    assistant_first = {**hit, "lead_turns": [{"turn": 11, "keywords": ["GDPR"]}]}
    assert sim.disagreement("unaware", no, assistant_first, False) == ["assistant mentions GDPR in T10"]
    assert sim.disagreement("conflicts", no, {**hit, "lead_turns": None}, False) == ["assistant mentions GDPR in T10"]


def test_disagreements_lead_the_scorecard_under_check_these():
    persona = coastal()
    card = {kind: [] for kind in sim.SCORE_LISTS}
    card["knows"] = [{"id": "K4", "search": "read 01-goals.md", "captured": False, "where": None},
                     {"id": "K2", "search": "read the risks", "captured": True, "where": "11-unknowns-and-risks.md"}]
    hits = {"K4": {"kind": "knows", "keywords": ["FERRYMASTER"], "assistant_turns": [],
                   "vault_files": [{"file": "01-goals.md", "keywords": ["FERRYMASTER"]}]},
            "K2": {"kind": "knows", "keywords": ["SeaBook"], "assistant_turns": [], "vault_files": []}}
    checks = sim.disagreements(card, hits)
    assert checks == ["K4: judge: no; vault mentions FERRYMASTER in 01-goals.md",
                      "K2: judge: yes; no vault page holds any of its keywords (SeaBook)"]
    card.update(hits=hits, check_these=checks, judge_calls=[], max_questions_in_one_turn={"count": 0, "turn": None},
                endings=[], spent_usd=0, judge_usd=0, arm="planner", dropped=[], told_not_asked=[],
                decided_without_yes=[], invented_facts=[], session_endings=[],
                models={"assistant": "a", "persona": "p", "judge": "j"})
    md = sim.render_scorecard_md(card, persona)
    assert md.index("## Check these") < md.index("## Facts captured")
    assert "- K4: judge: no; vault mentions FERRYMASTER in 01-goals.md" in md
    assert "| K4 |" in md and "| vault 01-goals.md | read 01-goals.md |" in md


def test_the_full_run_scorecard_sets_hits_beside_the_verdicts(full_run):
    card = json.loads((full_run["run"] / "planner" / "scorecard.json").read_text(encoding="utf-8"))
    # The stub assistant echoes the opening, so K1's keywords are in T2 but in no vault page.
    assert card["hits"]["K1"]["assistant_turns"][0]["turn"] == 2 and card["hits"]["K1"]["vault_files"] == []
    assert any(c.startswith("K1: judge: yes; no vault page holds") for c in card["check_these"])
    assert any(c.startswith("U1: judge: yes; no assistant turn holds") for c in card["check_these"])
    assert all(row["search"].startswith("stub: read") for kind in sim.SCORE_LISTS for row in card[kind])
    md = (full_run["run"] / "planner" / "scorecard.md").read_text(encoding="utf-8")
    assert md.index("## Check these") < md.index("## Gaps surfaced")
    assert "keyword hits" in (full_run["run"] / "compare.html").read_text(encoding="utf-8")


def test_the_scorecard_reports_what_the_vault_records_for_the_explorer(full_run):
    card = json.loads((full_run["run"] / "planner" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["capture"]["counts"]["apps"] == 0 and card["capture"]["checks"][0]["check"] == "every app has a domain"
    assert "## Recorded for the explorer" in (full_run["run"] / "planner" / "scorecard.md").read_text(encoding="utf-8")


def test_the_judge_is_called_once_per_category_and_asked_to_think(full_run):
    for arm in ("planner", "planner-seuss", "baseline"):
        calls = [c for c in full_run["calls"] if c["role"] == "judge" and f"{os.sep}{arm}{os.sep}" in c["cwd"] + os.sep]
        assert [c["category"] for c in calls] == list(sim.JUDGE_CATEGORIES), arm
        for call in calls:
            argv = call["argv"]
            assert argv[argv.index("--effort") + 1] == sim.JUDGE_EFFORT
            assert json.loads(argv[argv.index("--settings") + 1])["alwaysThinkingEnabled"] is True
    for call in (c["argv"] for c in full_run["calls"] if c["role"] == "persona"):
        assert "--effort" not in call and "alwaysThinkingEnabled" not in call[call.index("--settings") + 1]
    raws = sorted(p.name for p in (full_run["run"] / "planner" / "raw").glob("*-judge-*.txt"))
    assert [r.split("-judge-")[1] for r in raws] == [f"{c}.txt" for c in sim.JUDGE_CATEGORIES]


def test_each_call_holds_only_its_own_items_and_the_hints_say_a_hint_is_not_proof(full_run):
    persona = coastal()
    transcript = sim.Transcript.load(full_run["run"] / "planner" / "transcript.jsonl")
    vault = full_run["run"] / "planner" / "vault"
    hits = sim.vault_hits(persona, transcript, vault)
    knows = sim.judge_input(persona, transcript, vault, "knows", hits)
    assert "IDS knows: K1, K2" in knows and "U1" not in knows and "THE FINAL VAULT" in knows
    assert "- K1 (keywords: one customer, one journey, one account" in knows and "assistant turns T2" in knows
    unaware = sim.judge_input(persona, transcript, vault, "unaware", hits)
    assert "THE FINAL VAULT" not in unaware and "no lead turn" in unaware and "keywords:" not in unaware.split("HINTS")[0]
    assert "A hint is not proof" in sim.judge_system_prompt("unaware")


def test_every_verdict_needs_a_search_note_written_first():
    persona = coastal()
    rows = [{"id": i["id"], "search": "looked in T4", "captured": False, "where": None} for i in persona["knows"]]
    assert sim.category_problems({"knows": rows}, persona, "knows") == []
    rows[0] = {"id": "K1", "captured": False, "where": None}
    rows[1] = {"id": "K2", "captured": False, "search": "  ", "where": None}
    rows[2] = {"id": "K3", "captured": False, "where": None, "search": "looked afterwards"}
    problems = sim.category_problems({"knows": rows}, persona, "knows")
    assert problems == ["knows K1: 'search' must say what you looked for and where",
                        "knows K2: 'search' must say what you looked for and where",
                        "knows K3: write 'search' before 'captured'"]
    shape = {key: [] for key in sim.SHAPE_LISTS}
    assert sim.category_problems(shape, persona, "shape") == ["the reply: 'search' must say what you looked for and where"]
    assert sim.category_problems({"search": "read every turn", **shape}, persona, "shape") == []
    # The shape checks that were there before are as strict as they were.
    missing = [{"id": "K1", "search": "x", "captured": "yes"}]
    assert sim.category_problems({"knows": missing}, persona, "knows")[:2] == [
        f"'knows' must list exactly {', '.join(i['id'] for i in persona['knows'])}, once each; got ['K1']",
        "knows K1: 'captured' must be true or false"]


def test_a_reply_without_search_notes_is_asked_again_once_then_exits_2(tmp_path):
    code, err, _, calls = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_JUDGE": "nosearch"})
    assert code == 2 and "'search' must say" in err
    assert [c["category"] for c in calls if c["role"] == "judge"] == ["knows", "knows"]


def test_rejudge_scores_a_finished_run_again_without_replaying_it(full_run, tmp_path):
    import shutil
    run_dir = tmp_path / full_run["run"].name
    shutil.copytree(full_run["run"], run_dir, symlinks=True)
    transcripts = {arm: (run_dir / arm / "transcript.jsonl").read_bytes() for arm in ("planner", "baseline")}
    run_json = (run_dir / "run.json").read_bytes()
    old_raws = sorted(p.name for p in (run_dir / "planner" / "raw").iterdir())
    log = tmp_path / "rejudge-log.jsonl"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--rejudge", str(run_dir), "--stub",
                           "--judge-model", "other-judge", "--budget", "1"],
                          capture_output=True, text=True, env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert {c["role"] for c in calls} == {"judge"}, "a rejudge calls neither the assistant nor the persona"
    assert len(calls) == 3 * len(sim.JUDGE_CATEGORIES)
    assert all(c["argv"][c["argv"].index("--model") + 1] == "other-judge" for c in calls)
    for arm, before in transcripts.items():
        assert (run_dir / arm / "transcript.jsonl").read_bytes() == before, "the transcript is read, never rewritten"
    assert (run_dir / "run.json").read_bytes() == run_json
    card = json.loads((run_dir / "planner" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["rejudged"] and card["models"] == {"assistant": "test-model", "persona": "test-persona", "judge": "other-judge"}
    assert card["endings"] == json.loads(run_json)["per_arm"]["planner"]["endings"]
    new_raws = sorted(p.name for p in (run_dir / "planner" / "raw").iterdir())
    assert new_raws[:len(old_raws)] == old_raws and len(new_raws) == len(old_raws) + len(sim.JUDGE_CATEGORIES)
    assert "Rejudged" in (run_dir / "planner" / "scorecard.md").read_text(encoding="utf-8")
    assert "other-judge" in (run_dir / "rejudge.json").read_text(encoding="utf-8")
    assert "keyword hits" in (run_dir / "compare.html").read_text(encoding="utf-8")


def test_rejudge_refuses_an_empty_transcript_and_flags_it_does_not_need(tmp_path):
    empty = tmp_path / "transcript.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(sim.ToolFailure, match="no spoken turns"):
        sim.Transcript.load(empty)
    assert empty.read_text(encoding="utf-8") == ""
    with pytest.raises(SystemExit):
        sim.parse_args(["--rejudge", str(tmp_path), "--judge-model", "j", "--budget", "1", "--model", "m"])
    args = sim.parse_args(["--rejudge", str(tmp_path), "--judge-model", "j", "--budget", "1"])
    assert args.rejudge == str(tmp_path)


def test_a_resumed_session_adds_only_the_increase_in_its_running_cost(monkeypatch):
    """claude -p --resume reports total_cost_usd as the session's running total. Summing it per turn counted every
    earlier turn again: a real $13 run read as $114 and stopped at session 9 of 16."""
    import types
    arm = sim.Arm.__new__(sim.Arm)
    arm.ledger = sim.Ledger(10.0)
    arm.session_costs, arm.calls, arm.name, arm.dir, arm.vault, arm.env = {}, 0, "planner", sim.pathlib.Path("/tmp"), None, {}
    arm.args = types.SimpleNamespace(model="m")
    arm.check_plugin = lambda *a: None
    arm.raw = lambda kind: sim.pathlib.Path("/tmp/x")
    budgets, totals = [], iter([0.10, 0.25, 0.45])
    def fake_call(argv, **kw):
        budgets.append(float(argv[argv.index("--max-budget-usd") + 1]))
        return types.SimpleNamespace(stdout="")
    monkeypatch.setattr(sim, "call", fake_call)
    monkeypatch.setattr(sim, "parse_stream", lambda out, raw: {"init": {}, "result": {
        "total_cost_usd": next(totals), "session_id": "s1", "is_error": False}})
    arm.assistant_turn("first", None)
    arm.assistant_turn("second", "s1")
    arm.assistant_turn("third", "s1")
    assert round(arm.ledger.spent, 2) == 0.45
    assert budgets[2] > budgets[1] - 0.2  # the cap given to claude includes what the session already spent


def test_the_persona_sees_only_its_own_earlier_words_and_this_session_in_full(tmp_path):
    t = sim.Transcript(tmp_path / "t.jsonl")
    t.add(session=1, mode="dump", speaker="lead", text="EARLIER LEAD WORDS", turn=1)
    t.add(session=1, mode="dump", speaker="assistant", text="EARLIER ASSISTANT WALL", turn=2)
    t.add(session=2, mode="shape", speaker="assistant", text="CURRENT ASSISTANT", turn=3)
    text = sim.persona_input(t, 2, "shape")
    assert "EARLIER LEAD WORDS" in text and "CURRENT ASSISTANT" in text
    assert "EARLIER ASSISTANT WALL" not in text


def test_news_adds_facts_and_inbox_documents_without_touching_the_persona():
    persona = {"knows": [{"id": "K1", "fact": "old"}], "docs": [{"name": "a.md", "text": "A"}]}
    news = {"knows": [{"id": "K19", "fact": "the CIO replied"}], "docs": [{"name": "cio-reply.md", "text": "Link."}]}
    after = sim.with_news(persona, news)
    assert [k["id"] for k in after["knows"]] == ["K1", "K19"]
    assert [d["name"] for d in after["docs"]] == ["a.md", "cio-reply.md"]
    assert [k["id"] for k in persona["knows"]] == ["K1"] and len(persona["docs"]) == 1
    assert sim.with_news(persona, None) is persona


def test_a_script_with_bad_news_or_a_missing_start_is_refused():
    persona = {"opening": "x", "topics": {}}
    session = [{"mode": "dump", "cap": 1, "planner": "/planner:dump", "baseline": "go"}]
    assert sim.script_problems({"sessions": session, "news": {"knows": [{"fact": "no id"}]}}, persona)
    assert sim.script_problems({"sessions": session, "news": {"rumours": []}}, persona)
    assert sim.script_problems({"sessions": session, "start": "no-such-snapshot"}, persona)


def test_a_vault_built_from_a_snapshot_gets_the_current_plugin_and_the_news_documents(tmp_path, monkeypatch):
    snapshots = tmp_path / "snapshots"
    (snapshots / "s" / ".claude" / "skills" / "planner").mkdir(parents=True)
    (snapshots / "s" / ".claude" / "skills" / "planner" / "STALE").write_text("old", encoding="utf-8")
    (snapshots / "s" / "01-goals.md").write_text("# Goals\n", encoding="utf-8")
    monkeypatch.setattr(sim, "SNAPSHOTS", snapshots)
    arm = tmp_path / "arm"
    arm.mkdir()
    persona = {"docs": [{"name": "cio-reply.md", "text": "Link, don't merge."}]}
    vault, notes = sim.build_vault_from(arm, "s", persona)
    assert (vault / "01-goals.md").exists() and (vault / ".inbox" / "cio-reply.md").exists()
    assert not (vault / ".claude" / "skills" / "planner" / "STALE").exists()
    assert (vault / ".claude" / "skills" / "planner" / "skills").is_dir()
    log = subprocess.run(["git", "log", "--oneline", "origin/main"], cwd=vault, capture_output=True, text=True)
    assert "Vault from snapshot s" in log.stdout


def test_news_can_change_how_the_lead_takes_a_decision():
    persona = {"knows": [], "decisions": [{"id": "D6", "choice": "x"}, {"id": "D7", "choice": "y"}]}
    after = sim.with_news(persona, {"decisions": [{"id": "D6", "override_if_blocked": "the CIO said not to wait"}]})
    assert after["decisions"][0] == {"id": "D6", "choice": "x", "override_if_blocked": "the CIO said not to wait"}
    assert after["decisions"][1] == {"id": "D7", "choice": "y"} and "override_if_blocked" not in persona["decisions"][0]
    assert sim.news_problems({"decisions": [{"id": "D6", "choice": "changed"}]})


def test_a_judge_refusal_is_retried_once_cut_short_then_that_category_reads_not_scored(tmp_path):
    code, err, run_dir, calls = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_JUDGE": "refuse:wrong"})
    assert code == 0, err
    assert [c["category"] for c in calls if c["role"] == "judge"].count("wrong") == 2
    card = json.loads((run_dir / "planner" / "scorecard.json").read_text(encoding="utf-8"))
    assert list(card["not_scored"]) == ["wrong"] and card["wrong"] == []
    assert any(c.startswith("judge: wrong not scored: the judge model refused twice") for c in card["check_these"])
    md = (run_dir / "planner" / "scorecard.md").read_text(encoding="utf-8")
    assert "## Wrong beliefs challenged (W): not scored" in md
    assert "## Facts captured (K):" in md  # the other categories still count


def test_two_closed_sessions_that_clash_are_merged_by_union_keeping_mains_state(tmp_path):
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    arm_dir = tmp_path / "planner"
    arm_dir.mkdir()
    vault, _ = sim.build_vault(arm_dir, "planner", persona)
    page = "12-glossary.md"
    base = (vault / page).read_text(encoding="utf-8")
    for name, line in (("2026-10-05-first", "- **Term A:** first session's line"),
                       ("2026-10-05-second", "- **Term B:** second session's line")):
        sim.git("switch", "-q", "-c", f"session/{name}", "main", cwd=vault)
        (vault / page).write_text(base.rstrip("\n") + "\n\n" + line + "\n", encoding="utf-8")
        (vault / "sessions" / f"{name}.md").write_text(
            f"---\nid: {name}\ntype: session\ndate: 2026-10-05\nmodes: [dump]\nstatus: closed\nsummary: a test\n---\n"
            f"# {name}\n", encoding="utf-8")
        sim.git("add", page, f"sessions/{name}.md", cwd=vault)
        sim.git("commit", "-q", "-m", f"Close session {name}", cwd=vault)
    reports = sim.merge_closed(vault, arm_dir)
    assert reports[0].startswith("merged session/2026-10-05-first")
    assert reports[1].startswith("merged session/2026-10-05-second into main on origin after settling conflicts in "
                                 "12-glossary.md"), reports[1]
    sim.git("fetch", "-q", "origin", cwd=vault)
    merged = sim.git("show", f"origin/main:{page}", cwd=vault).stdout
    assert "first session's line" in merged and "second session's line" in merged and "<<<<<<<" not in merged


def test_the_persona_gets_only_where_it_left_each_earlier_session_and_rules_against_repeating_and_inventing(tmp_path):
    t = sim.Transcript(tmp_path / "t.jsonl")
    for n, text in enumerate(["FIRST WORDS", "MIDDLE WORDS", "LAST WORDS " + "x" * 400], 1):
        t.add(session=1, mode="dump", speaker="lead", text=text, turn=n)
    t.add(session=2, mode="shape", speaker="assistant", text="CURRENT ASSISTANT", turn=4)
    text = sim.persona_input(t, 2, "shape")
    assert "FIRST WORDS" not in text and "MIDDLE WORDS" in text and "LAST WORDS" in text and "[...]" in text
    rules = sim.persona_prompt(coastal())
    assert "Say a worry once." in rules and "You can do nothing outside this chat." in rules


def test_a_message_drafted_for_the_lead_is_counted_by_code(tmp_path):
    t = sim.Transcript(tmp_path / "t.jsonl")
    t.add(session=1, mode="grill", speaker="assistant", text="Here it is:\n\n> **Subject: Who owns Northway ID?**\n> Hi,", turn=2)
    t.add(session=1, mode="grill", speaker="assistant", text="The subject of this grill is the login.", turn=4)
    assert sim.drafted_messages(t) == [2]


def test_the_drafted_message_detector_counts_salutations_and_skips_planner_bullets(tmp_path):
    t = sim.Transcript(tmp_path / "t.jsonl")
    t.add(session=1, mode="grill", speaker="assistant", text="> Hi Priya,\n> Can your team run it?", turn=2)
    t.add(session=1, mode="grill", speaker="assistant", text="- **Subject:** SV-01 Tidemiles", turn=4)
    t.add(session=1, mode="grill", speaker="assistant", text="```\nHello [name],\nOne question.\n```", turn=6)
    assert sim.drafted_messages(t) == [2, 6]


def test_earlier_sessions_reach_the_persona_in_number_order(tmp_path):
    t = sim.Transcript(tmp_path / "t.jsonl")
    for session in (1, 2, 10):
        t.add(session=session, mode="dump", speaker="lead", text=f"SESSION {session} WORDS", turn=session)
    text = sim.persona_input(t, 11, "grill")
    assert text.index("SESSION 1 WORDS") < text.index("SESSION 2 WORDS") < text.index("SESSION 10 WORDS")


def test_a_state_line_the_union_drops_is_reported(tmp_path):
    hunk = sim.CONFLICT_HUNK.search("<<<<<<< HEAD\n- **State:** open\n=======\n- **State:** resolved\n- **Notes:** x\n>>>>>>> b\n")
    lost = []
    assert sim.union_hunk(hunk, lost) == "- **State:** open\n- **Notes:** x\n" and lost == ["- **State:** resolved"]


def test_news_can_arrive_after_a_given_session(tmp_path):
    script = {"sessions": TWO_SESSIONS["sessions"], "events": [
        {"after": 1, "knows": [{"id": "K90", "category": "fact", "keywords": ["counsel replied"],
                                "fact": "Counsel replied: education is fine."}],
         "docs": [{"name": "counsel-reply.md", "text": "# Counsel\n\nEducation is fine."}]}]}
    path = tmp_path / "events.yaml"
    path.write_text(yaml.safe_dump(script), encoding="utf-8")
    out, log = tmp_path / "results", tmp_path / "stub-log.jsonl"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "coastal-merger", "--stub", "--script", str(path),
                           "--arms", "planner", "--out", str(out), *MODELS, "--budget", "5"],
                          capture_output=True, text=True, env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    arm = sorted(out.iterdir())[0] / "planner"
    news = [e for e in entries(arm) if e.get("event") == "news"]
    assert len(news) == 1 and news[0]["session"] == 2 and "K90" in news[0]["text"]
    assert (arm / "vault" / ".inbox" / "counsel-reply.md").is_file()
    persona_calls = [c for c in (json.loads(l) for l in log.read_text().splitlines()) if c["role"] == "persona"]
    assert persona_calls, "the stub ran no persona call"


def test_an_event_must_say_after_which_session():
    persona = {"opening": "x", "topics": {}}
    sessions = TWO_SESSIONS["sessions"]
    assert sim.script_problems({"sessions": sessions, "events": [{"knows": []}]}, persona)
    assert sim.script_problems({"sessions": sessions, "events": [{"after": len(sessions)}]}, persona)
    assert sim.script_problems({"sessions": sessions, "events": [{"after": 1}, {"after": 1}]}, persona)


def test_a_turn_cited_as_T193_counts_like_193():
    turns = {193: "Release one for users is lessons and paper."}
    assert sim.cited({"turn": "T193", "quote": "release one for users is lessons"}, turns)
    assert sim.cited({"turn": 193, "quote": "release one for users is lessons"}, turns)
    assert not sim.cited({"turn": "T194", "quote": "release one"}, turns)
    assert not sim.cited({"turn": True, "quote": "release one"}, turns)


def test_a_lead_turn_that_says_a_brief_id_is_flagged(tmp_path):
    t = sim.Transcript(tmp_path / "t.jsonl")
    t.add(session=1, mode="grill", speaker="lead", text="I'll lock D1 now.", turn=1)
    t.add(session=1, mode="grill", speaker="lead", text="UNK-004 and CON-001 are fine, and so is option D.", turn=3)
    assert sim.leaked_brief_ids(t) == [1]
    rules = sim.persona_prompt(coastal())
    assert "Never report what someone said back" in rules and "are your private notes" in rules


def test_news_dropped_into_the_inbox_reaches_the_lead_before_the_next_session(tmp_path):
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    arm = sim.Arm.__new__(sim.Arm)
    arm.persona, arm.vault, arm.dir = persona, tmp_path / "vault", tmp_path
    arm.vault.mkdir()
    arm.transcript = sim.Transcript(tmp_path / "t.jsonl")
    inbox = tmp_path / "news-inbox"
    (inbox / "applied").mkdir(parents=True)
    (inbox / "01-counsel.yaml").write_text(yaml.safe_dump({"knows": [
        {"id": "K90", "category": "fact", "keywords": ["counsel cleared"], "fact": "Counsel cleared the list."}]}),
        encoding="utf-8")
    arm.arrive_live(13, "discover", inbox)
    assert any(k["id"] == "K90" for k in arm.persona["knows"])
    assert (inbox / "applied" / "01-counsel.yaml").is_file() and not (inbox / "01-counsel.yaml").exists()
    (inbox / "02-bad.yaml").write_text("rumours: []\n", encoding="utf-8")
    with pytest.raises(sim.ToolFailure):
        arm.arrive_live(14, "close", inbox)
    assert (inbox / "02-bad.yaml").exists()


def test_a_lead_turn_that_claims_an_action_outside_the_chat_is_flagged(tmp_path):
    t = sim.Transcript(tmp_path / "t.jsonl")
    t.add(session=1, mode="grill", speaker="lead", text="Shape's done. It's pushed, session/x.", turn=1)
    t.add(session=1, mode="grill", speaker="lead", text="Spoke to the consultant, she said yes.", turn=3)
    t.add(session=1, mode="grill", speaker="lead", text="I'll ask the consultant tomorrow.", turn=5)
    assert sim.claimed_actions(t) == [1, 3]
    assert "You cannot run commands" in sim.persona_prompt(coastal())


def test_a_team_session_runs_in_the_team_repo_with_copies_of_the_named_skills(tmp_path):
    script = {"name": "team", "persona": "coastal-merger",
              "team_repos": {"x": {"title": "X", "skills": ["requirements-grill"]}},
              "sessions": [{"mode": "requirements-grill", "cap": 2, "repo": "x", "persona": "coach-lead",
                            "planner": "/requirements-grill x", "baseline": "/requirements-grill x"}]}
    if not (sim.USER_SKILLS / "requirements-grill" / "SKILL.md").is_file():
        pytest.skip("the user's requirements-grill skill is not installed on this machine")
    path = tmp_path / "team.yaml"
    path.write_text(yaml.safe_dump(script), encoding="utf-8")
    out, log = tmp_path / "results", tmp_path / "stub-log.jsonl"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "coastal-merger", "--stub", "--script", str(path),
                           "--arms", "planner", "--out", str(out), *MODELS, "--budget", "2"],
                          capture_output=True, text=True, env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    arm = sorted(out.iterdir())[0] / "planner"
    assert (arm / "team-x" / ".claude" / "skills" / "requirements-grill" / "SKILL.md").is_file()
    calls = [json.loads(l) for l in log.read_text().splitlines()]
    assert any(c["role"] == "assistant" and c["cwd"].endswith("team-x") for c in calls)
    lead = [e for e in entries(arm) if e["speaker"] == "lead"]
    assert lead and all(e.get("persona") == "coach-lead" for e in lead)


def padded_vault(tmp_path, persona, pages=60, chars=60_000):
    """A vault far over the judge's budget: every page is a run of sections, and the first keyword of each knows and
    decisions item sits in a few of them. Returns the vault folder and the facts' markers."""
    vault = tmp_path / "vault"
    vault.mkdir()
    items = [i for kind in ("knows", "decisions") for i in persona[kind]]
    for n in range(pages):
        sections = []
        for s in range(chars // 600):
            item = items[(n + s) % len(items)] if s % 2 == 0 else None
            mention = f" Recorded: {item['keywords'][0]}." if item else ""
            sections.append(f"## Section {n}.{s}\n\n" + "Filler about nothing in particular. " * 15 + mention)
        (vault / f"page-{n:02d}.md").write_text("\n\n".join(sections), encoding="utf-8")
    return vault


def short_transcript(tmp_path):
    path = tmp_path / "transcript.jsonl"
    rows = [{"turn": t, "session": 1, "mode": "dump", "speaker": "lead" if t % 2 else "assistant",
             "text": f"turn {t} " + "words " * 40} for t in range(1, 21)]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return sim.Transcript.load(path)


def test_a_vault_over_the_old_budget_gives_every_item_its_evidence_under_the_budget(tmp_path):
    persona = coastal()
    vault = padded_vault(tmp_path, persona)
    transcript = short_transcript(tmp_path)
    hits = sim.vault_hits(persona, transcript, vault)
    whole = sum(len(text) for _, text in sim.vault_pages(vault))
    assert whole > 3 * sim.JUDGE_INPUT_CHARS, "the fixture must be too big for the old input, which sent the whole vault"
    for category in ("knows", "decisions"):
        text, cuts = sim.build_judge_input(persona, transcript, vault, category, hits)
        assert len(text) <= sim.JUDGE_INPUT_CHARS
        assert "PAGE INDEX of the final vault" in text and "FILE page-00.md" in text
        for item in persona[category]:
            block = text.split(f"=== EVIDENCE FOR {item['id']} ===\n", 1)[1].split("\n\n=== EVIDENCE FOR", 1)[0]
            assert item["keywords"][0] in block, f"{item['id']} lost its evidence"
        assert any("left out" in cut for cut in cuts), "something was cut, so the cut is named"
    for category in ("wrong", "unaware", "conflicts", "shape"):
        assert "THE FINAL VAULT" not in sim.judge_input(persona, transcript, vault, category, hits)


def test_an_item_no_page_mentions_says_so_and_a_long_transcript_is_cut_in_the_open(tmp_path):
    persona = coastal()
    vault = padded_vault(tmp_path, persona, pages=2, chars=3_000)
    (vault / "page-00.md").write_text("## Only\n\nnothing here", encoding="utf-8")
    (vault / "page-01.md").write_text("## Only\n\nnothing here either", encoding="utf-8")
    path = tmp_path / "long.jsonl"
    rows = [{"turn": t, "session": 1, "mode": "dump", "speaker": "lead" if t % 2 else "assistant", "text": "long " * 400}
            for t in range(1, 201)]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    transcript = sim.Transcript.load(path)
    hits = sim.vault_hits(persona, transcript, vault)
    text, cuts = sim.build_judge_input(persona, transcript, vault, "knows", hits)
    assert len(text) <= sim.JUDGE_INPUT_CHARS
    assert any(c.startswith("K1: no page holds a keyword") for c in cuts)
    assert any(c.startswith("transcript: ") and "cut to" in c for c in cuts)
    assert "no page of the final vault holds one of its keywords" in text


def test_a_cut_judge_input_is_named_in_check_these_on_the_scorecard(full_run, tmp_path):
    import shutil
    run_dir = tmp_path / full_run["run"].name
    shutil.copytree(full_run["run"], run_dir, symlinks=True)
    persona = coastal()
    big = padded_vault(tmp_path, persona)
    for page in big.glob("*.md"):
        shutil.copy(page, run_dir / "planner" / "vault" / page.name)
    for arm in ("planner-seuss", "baseline"):
        shutil.rmtree(run_dir / arm)
    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    summary["per_arm"] = {"planner": summary["per_arm"]["planner"]}
    summary["arms"] = ["planner"]
    (run_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    log = tmp_path / "rejudge-log.jsonl"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--rejudge", str(run_dir), "--stub",
                           "--judge-model", "j", "--budget", "1"],
                          capture_output=True, text=True, env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    card = json.loads((run_dir / "planner" / "scorecard.json").read_text(encoding="utf-8"))
    assert set(card["judge_cuts"]) >= {"knows", "decisions"}
    assert any(c.startswith("judge input (knows) was cut to fit") for c in card["check_these"])
    assert "judge input (knows) was cut to fit" in (run_dir / "planner" / "scorecard.md").read_text(encoding="utf-8")
    sizes = [json.loads(line)["stdin_chars"] for line in log.read_text(encoding="utf-8").splitlines()]
    assert len(sizes) == len(sim.JUDGE_CATEGORIES) and max(sizes) <= sim.JUDGE_INPUT_CHARS


def test_a_prompt_too_long_judge_call_says_so_instead_of_error_success(tmp_path):
    code, err, _, _ = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_JUDGE": "toolong:knows"})
    assert code == 2
    assert "the knows judge call failed because the prompt was too long for the model" in err
    assert "(success)" not in err


def test_dry_judge_reports_every_input_size_without_calling_claude(full_run):
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--dry-judge", str(full_run["run"])],
                          capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stderr
    assert "[planner] knows: " in done.stdout and f"of {sim.JUDGE_INPUT_CHARS}" in done.stdout
    assert done.stdout.count("[planner] ") == len(sim.JUDGE_CATEGORIES)


def long_run_transcript(tmp_path, persona, sessions=23, per_session=30, size=2_000):
    """A run far over the judge's cap: every turn is padding, and one lead turn per session holds a keyword."""
    rows, turn = [], 0
    keyword = persona["knows"][0]["keywords"][0]
    for session in range(1, sessions + 1):
        for n in range(per_session):
            turn += 1
            text = ("padding " * (size // 8)) + (f" {keyword}" if n == 7 else "")
            rows.append({"turn": turn, "session": session, "mode": "grill", "speaker": "lead" if turn % 2 else "assistant",
                         "text": text})
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return sim.Transcript.load(path)


def test_a_transcript_far_over_the_cap_still_fits_every_call_and_names_what_it_left_out(tmp_path):
    persona = coastal()
    vault = padded_vault(tmp_path, persona, pages=3, chars=6_000)
    transcript = long_run_transcript(tmp_path, persona)
    assert len(sim.as_chat(transcript.spoken())) > 3 * sim.JUDGE_INPUT_CHARS
    hits = sim.vault_hits(persona, transcript, vault)
    keyword = persona["knows"][0]["keywords"][0]
    for category in sim.JUDGE_CATEGORIES:
        for compact in (False, True):
            text, cuts = sim.build_judge_input(persona, transcript, vault, category, hits, compact)
            assert len(text) <= sim.JUDGE_INPUT_CHARS, category
            assert any(c.startswith("transcript:") and "left out: T" in c for c in cuts), category
            assert text.count("=== Session ") == 23, "every session keeps its header"
            assert "[... left out: T" in text
    knows, _ = sim.build_judge_input(persona, transcript, vault, "knows", hits)
    assert keyword in knows.split("THE TRANSCRIPT:", 1)[1].split("THE FINAL VAULT", 1)[0]


def test_the_turns_beside_a_keyword_outrank_the_rest_when_the_transcript_is_cut(tmp_path):
    persona = coastal()
    transcript = long_run_transcript(tmp_path, persona, sessions=2, per_session=40, size=1_000)
    spoken = transcript.spoken()
    chat, cut = sim.relevant_chat(spoken, [persona["knows"][0]["keywords"][0]], 9_000)
    hit = next(e["turn"] for e in spoken if persona["knows"][0]["keywords"][0] in e["text"])
    assert f"[T{hit}]" in chat and f"[T{hit + 1}]" in chat and f"[T{hit - 1}]" in chat
    assert len(chat) <= 9_000 and "left out:" in cut


def test_rejudge_scores_a_synthetic_run_far_over_the_cap_with_the_stub(full_run, tmp_path):
    import shutil
    run_dir = tmp_path / full_run["run"].name
    shutil.copytree(full_run["run"], run_dir, symlinks=True)
    for arm in ("planner-seuss", "baseline"):
        shutil.rmtree(run_dir / arm)
    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    summary["per_arm"] = {"planner": summary["per_arm"]["planner"]}
    summary["arms"] = ["planner"]
    (run_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    big = long_run_transcript(tmp_path, coastal())
    (run_dir / "planner" / "transcript.jsonl").write_text(big.path.read_text(encoding="utf-8"), encoding="utf-8")
    log = tmp_path / "long-log.jsonl"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--rejudge", str(run_dir), "--stub", "--judge-model", "j",
                           "--budget", "1"], capture_output=True, text=True,
                          env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    card = json.loads((run_dir / "planner" / "scorecard.json").read_text(encoding="utf-8"))
    assert any("left out: T" in c for c in card["check_these"] + sum(card["judge_cuts"].values(), []))
    sizes = [json.loads(line)["stdin_chars"] for line in log.read_text(encoding="utf-8").splitlines()]
    assert max(sizes) <= sim.JUDGE_INPUT_CHARS


def breakdown_run(tmp_path, written):
    """A stub run whose breakdown session writes `written` to docs/plan/x-breakdown.md in the team repo."""
    if not (sim.USER_SKILLS / "work-breakdown" / "SKILL.md").is_file():
        pytest.skip("the user's work-breakdown skill is not installed on this machine")
    script = {"name": "team", "persona": "coastal-merger", "team_repos": {"x": {"title": "X", "skills": ["work-breakdown"]}},
              "sessions": [{"mode": "breakdown", "cap": 3, "repo": "x", "persona": "coach-lead",
                            "planner": "/work-breakdown x", "baseline": "break it down"}]}
    path = tmp_path / "team.yaml"
    path.write_text(yaml.safe_dump(script), encoding="utf-8")
    env = {**os.environ}
    if written is not None:
        env["SIM_STUB_WRITE"] = f"docs/plan/x-breakdown.md::{written}"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "coastal-merger", "--stub", "--script", str(path),
                           "--arms", "planner", "--out", str(tmp_path / "results"), *MODELS, "--budget", "2"],
                          capture_output=True, text=True, env=env, timeout=600)
    return done, sorted((tmp_path / "results").iterdir())[0] / "planner"


def test_the_breakdown_session_is_followed_by_tickets_from_the_breakdown_not_a_model(tmp_path):
    fixture = (REPO / "tests" / "fixtures" / "breakdown" / "desk-agent-breakdown.md").read_text(encoding="utf-8")
    done, arm = breakdown_run(tmp_path, fixture)
    assert done.returncode == 0, done.stderr
    assert (arm / "tickets" / "tickets.csv").read_text(encoding="utf-8").count("\n") > 8
    assert "Import into Jira" in (arm / "tickets" / "README.md").read_text(encoding="utf-8")
    assert any(e.get("event") == "tickets" and "every line mapped" in e["text"] for e in entries(arm))


def test_a_run_whose_breakdown_is_missing_says_so_in_tickets_and_the_transcript_and_still_exits_0(tmp_path):
    done, arm = breakdown_run(tmp_path, None)
    assert done.returncode == 0, done.stderr
    assert "found 0" in (arm / "tickets" / "README.md").read_text(encoding="utf-8")
    assert any(e.get("event") == "tickets" and "no tickets" in e["text"] for e in entries(arm))
