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
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True).stdout
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
                                       capture_output=True, text=True).stdout
            assert f"\nstate: {state}\n" in committed, seed
    status = subprocess.run(["git", "status", "--porcelain"], cwd=seuss, capture_output=True, text=True).stdout
    assert "voice/" not in status, "voice/local must stay gitignored and the retirement committed"


def test_house_voice_reads_local_owner_examples_first():
    """The Seuss arm relies on this ordering and on two owner examples per type being enough."""
    text = (REPO / "plugin" / "skills" / "house-voice" / "SKILL.md").read_text(encoding="utf-8")
    assert "local `owner` and `owner-edit` examples first" in text
    assert "fewer than two active examples" in text


def test_baseline_vault_has_no_skills_and_no_plugin(full_run):
    vault = full_run["run"] / "baseline" / "vault"
    assert not (vault / ".claude" / "skills").exists()
    assert (full_run["run"] / "planner" / "vault" / ".claude" / "skills" / "planner" / "bin" / "planner").is_file()
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
    assert sum(1 for c in calls if c["role"] == "judge") == 1


def test_a_missing_json_field_is_a_tool_failure(tmp_path):
    code, err, run_dir, _ = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_DROP": "total_cost_usd"})
    assert code == 2
    assert "total_cost_usd" in err and "CLI output changed" in err
    assert (run_dir / "planner" / "transcript.html").is_file()
    assert not (run_dir / "planner" / "scorecard.json").exists()


def test_bad_judge_json_is_asked_again_once_then_exits_2(tmp_path):
    code, err, run_dir, calls = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_JUDGE": "bad"})
    assert code == 2 and "bad twice" in err
    assert sum(1 for c in calls if c["role"] == "judge") == 2
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
    for persona_path in sorted((SIM / "personas").glob("*.yaml")):
        persona = yaml.safe_load(persona_path.read_text(encoding="utf-8"))
        assert sim.persona_problems(persona) == [], persona_path
        for script_path in sorted((SIM / "scripts").glob("*.yaml")):
            script = yaml.safe_load(script_path.read_text(encoding="utf-8"))
            assert sim.script_problems(script, persona) == [], script_path


def test_the_coastal_merger_brief_is_big_and_messy():
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    assert 12 <= len(persona["knows"]) <= 15
    assert 5 <= len(persona["wrong"]) <= 6
    assert 6 <= len(persona["unaware"]) <= 8
    assert 3 <= len(persona["conflicts"]) <= 4
    assert 4 <= len(persona["decisions"]) <= 5 and any(d.get("refuse_until") for d in persona["decisions"])
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
    assert settings["sandbox"] == {"enabled": True, "autoAllowBashIfSandboxed": True}
    assert settings["permissions"]["allow"] == [f"Edit(/{(tmp_path / 'origin.git').resolve()}/**)"]
    assert "Skill" in argv[argv.index("--allowedTools") + 1].split(",")
    persona = sim.isolation_flags()
    assert "sandbox" not in _json.loads(persona[persona.index("--settings") + 1])
