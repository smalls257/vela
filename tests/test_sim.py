"""The session simulator, run end to end against the scripted fake claude in tests/sim/stub/. Nothing here calls a
model or spends money: every run passes --stub, and --out keeps results in tmp_path."""
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest
import yaml

from conftest import REPO, built_once

SIM = REPO / "tests" / "sim"
spec = importlib.util.spec_from_file_location("sim_run", SIM / "run.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]
TWO_SESSIONS = {"name": "two", "sessions": [
    {"mode": "dump", "cap": 3, "vela": "/vela:dump {opening}", "baseline": "Let's dump what we know. {opening}"},
    {"mode": "close", "cap": 3, "vela": "/vela:close", "baseline": "Close out this session."}]}


def simulate(tmp_path, *extra, env=None, arms="vela", script_data=None, sim_dir=SIM):
    """One stub run. Returns (exit code, stderr, run folder or None, stub call log)."""
    script = tmp_path / "two.yaml"
    script.write_text(yaml.safe_dump(script_data or TWO_SESSIONS), encoding="utf-8")
    out, log = tmp_path / "results", tmp_path / "stub-log.jsonl"
    full_env = {**os.environ, "SIM_STUB_LOG": str(log), **(env or {})}
    done = subprocess.run([sys.executable, str(sim_dir / "run.py"), "coastal-merger", "--stub", "--script", str(script),
                           "--arms", arms, "--out", str(out), *MODELS, *extra],
                          capture_output=True, text=True, env=full_env, timeout=600)
    runs = sorted(out.iterdir()) if out.is_dir() else []
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []
    return done.returncode, done.stderr, runs[0] if runs else None, calls


def entries(arm_dir):
    return [json.loads(line) for line in (arm_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()]


def _build_full_run(folder):
    tmp = folder / "run"
    tmp.mkdir()
    code, err, run_dir, calls = simulate(tmp, "--budget", "5", arms="vela,vela-seuss,baseline")
    (folder / "meta.json").write_text(json.dumps({"code": code, "err": err, "run": str(run_dir), "calls": calls}), encoding="utf-8")


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    """All three arms over the two-session script, built once per session however many workers ask. Read-only."""
    folder = built_once(tmp_path_factory, "sim-full-run", _build_full_run)
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    return {**meta, "run": pathlib.Path(meta["run"]), "tmp": folder / "run"}


def test_full_run_exits_0_and_writes_every_output(full_run):
    assert full_run["code"] == 0, full_run["err"]
    run_dir = full_run["run"]
    assert (run_dir / "compare.html").is_file() and (run_dir / "run.json").is_file()
    for arm in ("vela", "vela-seuss", "baseline"):
        for name in ("transcript.jsonl", "transcript.html", "viewer.html", "scorecard.json", "scorecard.md",
                     "vault-git-log.txt", "vault-check.txt"):
            assert (run_dir / arm / name).is_file(), f"{arm}/{name}"
        assert (run_dir / arm / "vault" / ".git").is_dir()
    compare = (run_dir / "compare.html").read_text(encoding="utf-8")
    assert "vela-seuss/transcript.html" in compare and "baseline/viewer.html" in compare


def test_transcript_records_both_sessions_turn_by_turn(full_run):
    log = entries(full_run["run"] / "vela")
    spoken = [e for e in log if e["speaker"] in ("lead", "assistant")]
    assert [e["turn"] for e in spoken] == list(range(1, len(spoken) + 1))
    assert {e["session"] for e in spoken} == {1, 2}
    assert spoken[0]["scripted"] and spoken[0]["text"].startswith("/vela:dump The CIO's mandate")
    assistant = [e for e in spoken if e["speaker"] == "assistant"]
    assert all(e["cost_usd"] == 0.01 and e["tool_calls"][0]["name"] == "Bash" for e in assistant)
    ends = [e for e in log if e.get("event") == "session-end"]
    assert [e["reason"] for e in ends] == ["persona-end", "persona-end"]
    assert not any(e["text"] == "[END]" for e in spoken), "the persona's [END] ends the session and is not a turn"


def test_transcript_html_escapes_every_turn_and_holds_no_script(full_run):
    page = (full_run["run"] / "vela" / "transcript.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(" in page
    assert "<script" not in page.lower()
    assert "<details><summary>1 tool calls</summary>" in page
    assert "<h2>Session 1: dump" in page and "<h2>Session 2: close" in page


def test_resume_is_used_from_the_second_turn_of_each_session(full_run):
    calls = [c["argv"] for c in full_run["calls"] if c["role"] == "assistant" and "vela" in c["cwd"].split(os.sep)]
    assert len(calls) == 4
    for first, second in (calls[0:2], calls[2:4]):
        assert "--resume" not in first
        assert "--resume" in second
    log = entries(full_run["run"] / "vela")
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


def test_the_gh_stub_is_first_on_path_records_a_pr_and_fails_everything_else(full_run, tmp_path):
    for call in full_run["calls"]:
        arm_dir = full_run["run"] / call["cwd"].split(str(full_run["run"]) + os.sep, 1)[1].split(os.sep)[0]
        assert call["gh"] == str(arm_dir / "bin" / "gh")
    assistant = [e for e in entries(full_run["run"] / "vela") if e["speaker"] == "assistant"]
    assert "https://github.invalid/sim/heron/pull/1" in assistant[0]["text"]
    gh = full_run["run"] / "vela" / "bin" / "gh"
    login = subprocess.run([str(gh), "api", "user", "-q", ".login"], capture_output=True, text=True, timeout=30)
    assert login.returncode == 0 and login.stdout.strip() == "sim-lead"  # so vela whoami never asks the lead
    for other in (["auth", "status"], ["pr", "merge", "1"]):
        done = subprocess.run([str(gh), *other], capture_output=True, text=True, timeout=30)
        assert done.returncode == 1 and sim.GH_MESSAGE in done.stderr, other


def stub_gh(tmp_path):
    """A vault on a session branch with the gh stub written for it, as an arm has them."""
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    arm_dir = tmp_path / "vela"
    arm_dir.mkdir()
    vault, _ = sim.build_vault(arm_dir, "vela", persona)
    sim.write_gh_stub(arm_dir / "bin", arm_dir / "origin.git")
    gh = lambda *a: subprocess.run([str(arm_dir / "bin" / "gh"), *a], capture_output=True, text=True, timeout=30, cwd=vault)
    return arm_dir, vault, gh


def test_open_the_pr_is_observable_through_the_gh_stub_create_list_view_and_comment(tmp_path):
    """The Black Box this removes: with every gh call refused, "open the PR" could never happen in a run, so a close
    that skipped it and a close that tried looked the same. Now the PR is recorded and every read of it answers."""
    arm_dir, vault, gh = stub_gh(tmp_path)
    branch = "session/2026-10-05-x"
    sim.git("switch", "-q", "-c", branch, "main", cwd=vault)
    made = gh("pr", "create", "--base", "main", "--title", "2026-10-05 Close: x", "--body-file", "/dev/null")
    assert made.returncode == 0 and made.stdout.strip() == "https://github.invalid/sim/heron/pull/1"
    again = gh("pr", "create", "--base", "main", "--head", branch, "--title", "again")
    assert again.returncode == 1 and "already exists" in again.stderr, "one open PR per head, as gh has it"
    listed = gh("pr", "list", "--head", branch, "--state", "open", "--json", "number,url")
    assert json.loads(listed.stdout) == [{"number": 1, "url": "https://github.invalid/sim/heron/pull/1"}]
    assert json.loads(gh("pr", "list", "--search", "Close: x", "--json", "number,title").stdout)[0]["number"] == 1
    assert json.loads(gh("pr", "list", "--search", "Challenge", "--json", "number").stdout) == []
    viewed = json.loads(gh("pr", "view", "1", "--json", "number,headRefName,title,state").stdout)
    assert viewed == {"number": 1, "headRefName": branch, "title": "2026-10-05 Close: x", "state": "OPEN"}
    assert json.loads(gh("pr", "view", "--json", "number").stdout) == {"number": 1}, "no argument: the current branch's PR"
    body = tmp_path / "answer.md"
    body.write_text("The answer.", encoding="utf-8")
    assert gh("pr", "comment", "1", "--body-file", str(body)).stdout.strip().endswith("/pull/1#issuecomment-1")
    assert "The answer." in gh("pr", "view", "1", "--comments").stdout
    missing = gh("pr", "view", "9")
    assert missing.returncode == 1 and "no pull requests found" in missing.stderr
    assert sim.opened_prs(arm_dir) == {branch: 1}, "a comment line is not a PR"


def test_a_pr_the_reviewer_merged_reads_merged_through_the_gh_stub(tmp_path):
    arm_dir, vault, gh = stub_gh(tmp_path)
    branch = "session/2026-10-05-y"
    sim.git("switch", "-q", "-c", branch, "main", cwd=vault)
    (vault / "sessions").mkdir(exist_ok=True)
    (vault / "sessions" / "2026-10-05-y.md").write_text("---\nid: 2026-10-05-y\nstatus: closed\n---\n", encoding="utf-8")
    sim.git("add", "-A", cwd=vault)
    sim.git("commit", "-q", "-m", "Close session", cwd=vault)
    gh("pr", "create", "--base", "main", "--head", branch, "--title", "y")
    assert json.loads(gh("pr", "list", "--state", "merged", "--json", "number").stdout) == []
    assert sim.merge_closed(vault, arm_dir) == [f"merged PR 1 as the reviewer: {branch} into main on origin"]
    assert json.loads(gh("pr", "view", "1", "--json", "state").stdout) == {"state": "MERGED"}
    assert json.loads(gh("pr", "list", "--state", "merged", "--json", "number").stdout) == [{"number": 1}]
    assert json.loads(gh("pr", "list", "--json", "number").stdout) == [], "open is the default, as gh has it"


def test_seuss_examples_reach_voice_local_only_in_the_seuss_arm(full_run):
    seuss, plain = full_run["run"] / "vela-seuss" / "vault", full_run["run"] / "vela" / "vault"
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
    assert (full_run["run"] / "vela" / "vault" / ".claude" / "skills" / "vela" / "scripts" / "vela").is_file()
    for call in full_run["calls"]:
        if call["role"] != "assistant":
            continue
        in_baseline = f"{os.sep}baseline{os.sep}" in call["cwd"] + os.sep
        assert ("--plugin-dir" in call["argv"]) is not in_baseline
        if in_baseline:
            assert not call["argv"][-1].startswith("/")


def test_scorecard_drops_claims_without_a_valid_citation(full_run):
    card = json.loads((full_run["run"] / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["unaware"][0]["surfaced"] is True
    assert card["wrong"][0]["challenged"] is False and "dropped" in card["wrong"][0]
    assert card["knows"][0]["captured"] is True and card["knows"][1]["captured"] is False
    assert len(card["dropped"]) == 2
    assert card["max_questions_in_one_turn"]["count"] == 1
    md = (full_run["run"] / "vela" / "scorecard.md").read_text(encoding="utf-8")
    assert "## Dropped claims" in md and "no-such-page.md" in md


def a_repo_of_its_own(destination):
    """The parts of this repo a stub run reads, as a fresh git repo that nothing else is editing. The test checks that
    repo, not the shared working tree: another session's edit to the real tree is not a write by the run."""
    ignore = shutil.ignore_patterns("snapshots", "scale", "results", "__pycache__", "*.pyc")
    for part in ("tests/sim", "tests/evals", "tools", "plugin", "template"):
        shutil.copytree(REPO / part, destination / part, ignore=ignore)
    for step in (["init", "-q", "-b", "main"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"]):
        subprocess.run(["git", *step], cwd=destination, check=True, capture_output=True, timeout=120)
    return destination


def test_nothing_is_written_outside_the_run_folder(full_run, tmp_path):
    assert sorted(p.name for p in full_run["tmp"].iterdir()) == ["results", "stub-log.jsonl", "two.yaml"]
    run_dir = str(full_run["run"]) + os.sep
    for call in full_run["calls"]:
        assert call["cwd"].startswith(run_dir) and call["tmpdir"].startswith(run_dir)
    repo = a_repo_of_its_own(tmp_path / "repo")
    out = tmp_path / "elsewhere"
    out.mkdir()
    code, err, _, _ = simulate(out, "--budget", "5", arms="vela,baseline", sim_dir=repo / "tests" / "sim",
                               env={"PYTHONDONTWRITEBYTECODE": "1"})  # a .pyc is the interpreter's write, not the run's
    assert code == 0, err
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, timeout=60).stdout
    assert status == "", f"the run changed its repo:\n{status}"
    assert not (repo / "tests" / "sim" / "results").exists(), "a run with --out wrote to the default results folder"


def test_budget_stop_exits_1_and_still_writes_the_scorecard(tmp_path):
    code, err, run_dir, calls = simulate(tmp_path, "--budget", "1", env={"SIM_STUB_COST": "0.5"})
    assert code == 1, err
    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert [e["reason"] for e in summary["per_arm"]["vela"]["endings"]] == ["budget", "not run: budget"]
    assert summary["spent_usd"] <= 1.0
    assert (run_dir / "vela" / "scorecard.md").is_file() and (run_dir / "vela" / "transcript.html").is_file()
    assert [c["category"] for c in calls if c["role"] == "judge"] == list(sim.JUDGE_CATEGORIES)


def test_a_missing_json_field_is_a_tool_failure(tmp_path):
    code, err, run_dir, _ = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_DROP": "total_cost_usd"})
    assert code == 2
    assert "total_cost_usd" in err and "CLI output changed" in err
    assert (run_dir / "vela" / "transcript.html").is_file()
    assert not (run_dir / "vela" / "scorecard.json").exists()


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


def test_default_arms_are_vela_and_seuss_and_unknown_arms_are_refused():
    assert sim.parse_args(["x", "--budget", "1", *MODELS]).arm_list == ["vela", "vela-seuss"]
    with pytest.raises(SystemExit):
        sim.parse_args(["x", "--budget", "1", "--arms", "vela,plain", *MODELS])


def test_every_persona_and_script_validates():
    """A holdout persona (split: holdout) is checked by counts only, so a failure here never prints its brief."""
    for persona_path in sorted((SIM / "personas").glob("*.yaml")):
        persona = yaml.safe_load(persona_path.read_text(encoding="utf-8"))
        sealed = sim.SEAL.split_of(persona) != "dev"
        if persona.get("team_persona") is True:
            continue
        problems = sim.persona_problems(persona)
        count = len(problems)
        if sealed:
            assert count == 0, persona_path.name
        else:
            assert problems == [], persona_path.name
        if persona.get("outsider") is True:  # speaks only in the sessions that name it, so no script is written for it
            continue
        for script_path in sorted((SIM / "scripts").glob("*.yaml")):
            script = yaml.safe_load(script_path.read_text(encoding="utf-8"))
            if script.get("persona") not in (None, persona_path.stem):
                continue  # a script written for one persona's topics
            problems = sim.script_problems(script, persona)
            count = len(problems)
            if sealed:
                assert count == 0, script_path.name
            else:
                assert problems == [], script_path.name


def test_every_persona_says_whether_it_is_dev_or_holdout():
    """The seal (seal.py): heron-desk and the personas its runs bring in are dev, and so is civic-permits, the scaled
    probes' second dev persona; the rest are holdout."""
    splits = {p.stem: sim.SEAL.split_of(yaml.safe_load(p.read_text(encoding="utf-8")))
              for p in sorted((SIM / "personas").glob("*.yaml"))}
    assert all(split in ("dev", "holdout") for split in splits.values()), splits
    assert {name for name, split in splits.items() if split == "dev"} == \
        {n for n in splits if n.startswith("heron-")} | {"civic-permits"}
    assert {"coastal-merger", "holdout-hospitals", "trading-coach", "holdout-nursing", "holdout-freight"} <= \
        {n for n, s in splits.items() if s == "holdout"}


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


# Character names and lines a reader would recognize from the published books. None may appear.
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
    arm_dir = tmp_path / "vela"
    arm_dir.mkdir()
    vault, _ = sim.build_vault(arm_dir, "vela", persona)
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
    argv = sim.assistant_argv("hi", "m", None, 1.0, "vela", tmp_path / "origin.git")
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
    card["knows"] = [{"id": "K4", "grounds": "read 01-goals.md", "captured": False, "where": None},
                     {"id": "K2", "grounds": "read the risks", "captured": True, "where": "11-unknowns-and-risks.md"}]
    hits = {"K4": {"kind": "knows", "keywords": ["FERRYMASTER"], "assistant_turns": [],
                   "vault_files": [{"file": "01-goals.md", "keywords": ["FERRYMASTER"]}]},
            "K2": {"kind": "knows", "keywords": ["SeaBook"], "assistant_turns": [], "vault_files": []}}
    checks = sim.disagreements(card, hits)
    assert checks == ["K4: judge: no; vault mentions FERRYMASTER in 01-goals.md",
                      "K2: judge: yes; no vault page holds any of its keywords (SeaBook)"]
    card.update(hits=hits, check_these=checks, judge_calls=[], max_questions_in_one_turn={"count": 0, "turn": None},
                endings=[], spent_usd=0, judge_usd=0, arm="vela", dropped=[], told_not_asked=[],
                decided_without_yes=[], invented_facts=[], session_endings=[],
                models={"assistant": "a", "persona": "p", "judge": "j"})
    md = sim.render_scorecard_md(card, persona)
    assert md.index("## Check these") < md.index("## Facts captured")
    assert "- K4: judge: no; vault mentions FERRYMASTER in 01-goals.md" in md
    assert "| K4 |" in md and "| vault 01-goals.md | read 01-goals.md |" in md


def test_the_full_run_scorecard_sets_hits_beside_the_verdicts(full_run):
    card = json.loads((full_run["run"] / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    # The stub assistant echoes the opening, so K1's keywords are in T2 but in no vault page.
    assert card["hits"]["K1"]["assistant_turns"][0]["turn"] == 2 and card["hits"]["K1"]["vault_files"] == []
    assert any(c.startswith("K1: judge: yes; no vault page holds") for c in card["check_these"])
    assert any(c.startswith("U1: judge: yes; no assistant turn holds") for c in card["check_these"])
    assert all(row["grounds"].startswith("stub: read") for kind in sim.SCORE_LISTS for row in card[kind])
    md = (full_run["run"] / "vela" / "scorecard.md").read_text(encoding="utf-8")
    assert md.index("## Check these") < md.index("## Gaps surfaced")
    assert "keyword hits" in (full_run["run"] / "compare.html").read_text(encoding="utf-8")


def test_the_scorecard_reports_what_the_vault_records_for_the_explorer(full_run):
    card = json.loads((full_run["run"] / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["capture"]["counts"]["apps"] == 0 and card["capture"]["checks"][0]["check"] == "every app has a domain"
    assert "## Recorded for the explorer" in (full_run["run"] / "vela" / "scorecard.md").read_text(encoding="utf-8")


def test_the_judge_is_called_once_per_category_and_asked_to_think(full_run):
    for arm in ("vela", "vela-seuss", "baseline"):
        calls = [c for c in full_run["calls"] if c["role"] == "judge" and f"{os.sep}{arm}{os.sep}" in c["cwd"] + os.sep]
        assert [c["category"] for c in calls] == list(sim.JUDGE_CATEGORIES), arm
        precision = json.loads((full_run["run"] / arm / "precision.json").read_text(encoding="utf-8"))
        assert precision["missing"] == "the final vault has no written items to sample", \
            "a stub vault holds only the template's own text, which no session wrote, so there is nothing to judge"
        for call in calls:
            argv = call["argv"]
            assert argv[argv.index("--effort") + 1] == sim.JUDGE_EFFORT
            assert json.loads(argv[argv.index("--settings") + 1])["alwaysThinkingEnabled"] is True
    for call in (c["argv"] for c in full_run["calls"] if c["role"] == "persona"):
        assert "--effort" not in call and "alwaysThinkingEnabled" not in call[call.index("--settings") + 1]
    raws = sorted(p.name for p in (full_run["run"] / "vela" / "raw").glob("*-judge-*.txt"))
    assert [r.split("-judge-")[1] for r in raws] == [f"{c}.txt" for c in sim.JUDGE_CATEGORIES]


def test_each_call_holds_only_its_own_items_and_the_hints_say_a_hint_is_not_proof(full_run):
    persona = coastal()
    transcript = sim.Transcript.load(full_run["run"] / "vela" / "transcript.jsonl")
    vault = full_run["run"] / "vela" / "vault"
    hits = sim.vault_hits(persona, transcript, vault)
    knows = sim.judge_input(persona, transcript, vault, "knows", hits)
    assert "IDS knows: K1, K2" in knows and "U1" not in knows and "THE FINAL VAULT" in knows
    assert "- K1 (keywords: one customer, one journey, one account" in knows and "assistant turns T2" in knows
    unaware = sim.judge_input(persona, transcript, vault, "unaware", hits)
    assert "THE FINAL VAULT" not in unaware and "no lead turn" in unaware and "keywords:" not in unaware.split("HINTS")[0]
    assert "A hint is not proof" in sim.judge_system_prompt("unaware")


def test_every_verdict_needs_a_grounds_note_written_first():
    persona = coastal()
    rows = [{"id": i["id"], "grounds": "T4 names it", "captured": False, "where": None} for i in persona["knows"]]
    assert sim.category_problems({"knows": rows}, persona, "knows") == []
    rows[0] = {"id": "K1", "captured": False, "where": None}
    rows[1] = {"id": "K2", "captured": False, "grounds": "  ", "where": None}
    rows[2] = {"id": "K3", "captured": False, "where": None, "grounds": "written afterwards"}
    problems = sim.category_problems({"knows": rows}, persona, "knows")
    assert problems == ["knows K1: 'grounds' must name the turns and files that bear on it and what they say",
                        "knows K2: 'grounds' must name the turns and files that bear on it and what they say",
                        "knows K3: write 'grounds' before 'captured'"]
    shape = {key: [] for key in sim.SHAPE_LISTS}
    assert sim.category_problems(shape, persona, "shape") == ["the reply: 'grounds' must name the turns and files that bear on it and what they say"]
    assert sim.category_problems({"grounds": "every turn", **shape}, persona, "shape") == []
    # The shape checks that were there before are as strict as they were.
    missing = [{"id": "K1", "grounds": "x", "captured": "yes"}]
    assert sim.category_problems({"knows": missing}, persona, "knows")[:2] == [
        f"'knows' must list exactly {', '.join(i['id'] for i in persona['knows'])}, once each; got ['K1']",
        "knows K1: 'captured' must be true or false"]


def test_a_reply_without_grounds_notes_is_asked_again_once_then_exits_2(tmp_path):
    code, err, _, calls = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_JUDGE": "nogrounds"})
    assert code == 2 and "'grounds' must name" in err
    assert [c["category"] for c in calls if c["role"] == "judge"] == ["knows", "knows"]


def test_rejudge_scores_a_finished_run_again_without_replaying_it(full_run, tmp_path):
    import shutil
    run_dir = tmp_path / full_run["run"].name
    shutil.copytree(full_run["run"], run_dir, symlinks=True)
    transcripts = {arm: (run_dir / arm / "transcript.jsonl").read_bytes() for arm in ("vela", "baseline")}
    run_json = (run_dir / "run.json").read_bytes()
    old_raws = sorted(p.name for p in (run_dir / "vela" / "raw").iterdir())
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
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["rejudged"] and card["models"] == {"assistant": "test-model", "persona": "test-persona", "judge": "other-judge"}
    assert card["endings"] == json.loads(run_json)["per_arm"]["vela"]["endings"]
    new_raws = sorted(p.name for p in (run_dir / "vela" / "raw").iterdir())
    assert new_raws[:len(old_raws)] == old_raws and len(new_raws) == len(old_raws) + len(sim.JUDGE_CATEGORIES)
    assert "Rejudged" in (run_dir / "vela" / "scorecard.md").read_text(encoding="utf-8")
    assert "other-judge" in (run_dir / "rejudge.json").read_text(encoding="utf-8")
    assert "keyword hits" in (run_dir / "compare.html").read_text(encoding="utf-8")


def test_a_run_recorded_before_the_rename_rejudges_and_compares_as_it_is(full_run, tmp_path):
    """Runs recorded before the rename keep their old arm folder. --rejudge reads arm names from run.json and never
    checks them against ARMS, so such a run is scored again as it is; the comparison pairs it with today's arm."""
    import shutil
    spec_c = importlib.util.spec_from_file_location("sim_compare", SIM / "compare_runs.py")
    compare = importlib.util.module_from_spec(spec_c)
    spec_c.loader.exec_module(compare)
    old_name = {new: old for old, new in compare.LEGACY_NAMES.items()}["vela"]
    run_dir = tmp_path / "old-run"
    shutil.copytree(full_run["run"], run_dir, symlinks=True)
    (run_dir / "vela").rename(run_dir / old_name)
    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    summary["arms"] = [old_name if a == "vela" else a for a in summary["arms"]]
    summary["per_arm"] = {old_name if a == "vela" else a: v for a, v in summary["per_arm"].items()}
    (run_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--rejudge", str(run_dir), "--stub",
                           "--judge-model", "other-judge", "--budget", "1"],
                          capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stderr
    card = json.loads((run_dir / old_name / "scorecard.json").read_text(encoding="utf-8"))
    assert card["rejudged"] and card["arm"] == old_name
    out = tmp_path / "compare.json"
    compared = subprocess.run([sys.executable, str(SIM / "compare_runs.py"), str(run_dir), str(full_run["run"]),
                               "--arm", "vela", "--baseline-checkout", str(REPO), "--midpoint-checkout", str(REPO),
                               "--json", str(out)], capture_output=True, text=True, timeout=600)
    assert compared.returncode in (0, 1, 3), compared.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["baseline"]["arm"] == old_name and report["midpoint"]["arm"] == "vela"
    voice = report["detail"]
    assert voice["baseline"]["voice"] == voice["midpoint"]["voice"], "the same turns, counted alike under either name"
    assert voice["baseline"]["scorecard"]["knows"] == voice["midpoint"]["scorecard"]["knows"]


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
    arm.session_costs, arm.calls, arm.name, arm.dir, arm.vault, arm.env = {}, 0, "vela", sim.pathlib.Path("/tmp"), None, {}
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
    session = [{"mode": "dump", "cap": 1, "vela": "/vela:dump", "baseline": "go"}]
    assert sim.script_problems({"sessions": session, "news": {"knows": [{"fact": "no id"}]}}, persona)
    assert sim.script_problems({"sessions": session, "news": {"rumors": []}}, persona)
    assert sim.script_problems({"sessions": session, "start": "no-such-snapshot"}, persona)


def test_a_vault_built_from_a_snapshot_gets_the_current_plugin_and_the_news_documents(tmp_path, monkeypatch):
    snapshots = tmp_path / "snapshots"
    (snapshots / "s" / ".claude" / "skills" / "vela").mkdir(parents=True)
    (snapshots / "s" / ".claude" / "skills" / "vela" / "STALE").write_text("old", encoding="utf-8")
    (snapshots / "s" / "01-goals.md").write_text("# Goals\n", encoding="utf-8")
    monkeypatch.setattr(sim, "SNAPSHOTS", snapshots)
    arm = tmp_path / "arm"
    arm.mkdir()
    persona = {"docs": [{"name": "cio-reply.md", "text": "Link, don't merge."}]}
    vault, notes = sim.build_vault_from(arm, "s", persona)
    assert (vault / "01-goals.md").exists() and (vault / ".inbox" / "cio-reply.md").exists()
    assert not (vault / ".claude" / "skills" / "vela" / "STALE").exists()
    assert (vault / ".claude" / "skills" / "vela" / "skills").is_dir()
    log = subprocess.run(["git", "log", "--oneline", "origin/main"], cwd=vault, capture_output=True, text=True)
    assert "Vault from snapshot s" in log.stdout


def test_news_can_change_how_the_lead_takes_a_decision():
    persona = {"knows": [], "decisions": [{"id": "D6", "choice": "x"}, {"id": "D7", "choice": "y"}]}
    after = sim.with_news(persona, {"decisions": [{"id": "D6", "override_if_blocked": "the CIO said not to wait"}]})
    assert after["decisions"][0] == {"id": "D6", "choice": "x", "override_if_blocked": "the CIO said not to wait"}
    assert after["decisions"][1] == {"id": "D7", "choice": "y"} and "override_if_blocked" not in persona["decisions"][0]
    assert sim.news_problems({"decisions": [{"id": "D6", "choice": "changed"}]})


def test_a_judge_refusal_is_retried_once_cut_short_then_that_category_reads_not_scored(tmp_path):
    reply = tmp_path / "long-reply.md"
    reply.write_text("A long first turn, so cutting each turn to 800 characters changes the input. " * 30
                     + "\n\nWhat else is on your mind?", encoding="utf-8")
    code, err, run_dir, calls = simulate(tmp_path, "--budget", "5",
                                         env={"SIM_STUB_JUDGE": "refuse:wrong", "SIM_STUB_REPLY": str(reply)})
    assert code == 0, err
    wrong = [c for c in calls if c["role"] == "judge" and c["category"] == "wrong"]
    assert len(wrong) == 2 and wrong[1]["stdin_chars"] < wrong[0]["stdin_chars"]
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert list(card["not_scored"]) == ["wrong"] and card["wrong"] == []
    assert any(c.startswith("judge: wrong not scored: the judge model refused twice (flagged [reasoning_extraction])")
               for c in card["check_these"])
    md = (run_dir / "vela" / "scorecard.md").read_text(encoding="utf-8")
    assert "## Wrong beliefs challenged (W): not scored" in md
    assert "## Facts captured (K):" in md  # the other categories still count


def test_a_refused_judge_input_already_cut_short_is_not_sent_again(tmp_path):
    # Every stub turn is under 800 characters, so the cut-short retry would be the same request at the same price.
    code, err, run_dir, calls = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_JUDGE": "refuse:wrong"})
    assert code == 0, err
    assert [c["category"] for c in calls if c["role"] == "judge"].count("wrong") == 1
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert list(card["not_scored"]) == ["wrong"]
    assert "so it was not sent again" in card["not_scored"]["wrong"]


# The judge thinks (--effort, alwaysThinkingEnabled). Asked as well to write in its reply what it looked for, where,
# and what it found, it was refused by the model's safeguards as [reasoning_extraction]: knows, wrong and tracer on
# every call of the 2026-10-14 heron-desk run, on Sonnet 5.5 and Opus 5.5 alike. The note before each verdict names
# the text it rests on instead, and no prompt may ask the judge to narrate, disclose or quote its own reasoning.
REASONING_EXTRACTION_PHRASES = (
    r"what you looked for", r"where you looked", r"what you found", r"\bsearch\b", r"\byour (own )?(reasoning|thinking|"
    r"thoughts|thought process)\b", r"\bchain[- ]of[- ]thought\b", r"\bstep[- ]by[- ]step\b", r"\bexplain (your|how you)\b",
    r"\bshow your work\b", r"\bthink(ing)? (out loud|aloud)\b", r"\breason(ing)? (first|out loud|aloud)\b")


@pytest.mark.parametrize("category", sim.SCORING_CALLS)
def test_no_judge_prompt_asks_the_judge_to_disclose_its_reasoning(category):
    prompt = sim.judge_system_prompt(category)
    found = [p for p in REASONING_EXTRACTION_PHRASES if re.search(p, prompt, re.I)]
    assert not found, f"the {category} judge prompt asks for its reasoning in the reply: {found}"
    # Not weakened: it still names its grounds before every verdict, and every yes still cites a turn and a quote.
    if category == "precision":  # its citations are a document, a lead turn or the item itself, each quoted
        assert '"grounds"' in prompt and "Every quote is copied exactly" in prompt and '"turn" is the lead turn' in prompt
        return
    assert '"grounds"' in prompt and "turn number T<n>" in prompt and "a quote copied exactly" in prompt


def test_the_judge_still_thinks():
    argv = sim.text_call_argv("m", sim.judge_system_prompt("knows"), 1.0, thinking=True)
    assert argv[argv.index("--effort") + 1] == sim.JUDGE_EFFORT
    assert json.loads(argv[argv.index("--settings") + 1])["alwaysThinkingEnabled"] is True


def test_a_refusal_names_the_classifier_that_flagged_it():
    result = {"result": "API Error: flagged.\n\nDetails: `[reasoning_extraction]`\n\nRequest ID: req_1"}
    assert sim.refusal_flag(result) == " (flagged [reasoning_extraction])"
    assert sim.refusal_flag({"result": "API Error: flagged."}) == ""


def test_two_closed_sessions_that_clash_are_merged_by_union_keeping_mains_state(tmp_path):
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    arm_dir = tmp_path / "vela"
    arm_dir.mkdir()
    vault, _ = sim.build_vault(arm_dir, "vela", persona)
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


def test_the_drafted_message_detector_counts_salutations_and_skips_vela_bullets(tmp_path):
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
                           "--arms", "vela", "--out", str(out), *MODELS, "--budget", "5"],
                          capture_output=True, text=True, env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    arm = sorted(out.iterdir())[0] / "vela"
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
    (inbox / "02-bad.yaml").write_text("rumors: []\n", encoding="utf-8")
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


def test_a_reply_past_the_cap_is_never_a_lead_turn_the_assistant_did_not_read(tmp_path):
    """The Paper Tiger this prevents: the lead's reply past the cap was written as a lead turn and never reached the
    assistant, so the judge marked a fact "not captured" that the assistant was never told (K34, mid-point T207).
    The reply is kept as a driver note the judge doesn't read; an [END] at the cap still ends the session as the lead's."""
    capped = {"name": "capped", "sessions": [
        {"mode": "dump", "cap": 1, "vela": "/vela:dump {opening}", "baseline": "Dump. {opening}"},
        {"mode": "close", "cap": 2, "vela": "/vela:close", "baseline": "Close out this session."}]}
    code, err, run_dir, _ = simulate(tmp_path, "--budget", "5", script_data=capped)
    assert code == 1, err  # a turn cap ended a session early
    said = entries(run_dir / "vela")
    first = [e for e in said if e.get("session") == 1 and e["speaker"] in ("lead", "assistant")]
    assert [e["speaker"] for e in first] == ["lead", "assistant"], "the scripted opening, the assistant's turn, nothing after"
    assert "What else is on your mind?" in first[-1]["text"], "the stub's first turn asks, so the lead answers"
    unsent = [e for e in said if e.get("event") == "lead-unsent"]
    assert len(unsent) == 1 and unsent[0]["session"] == 1 and "Honestly not sure" in unsent[0]["text"]
    assert "turn" not in unsent[0] and unsent[0]["speaker"] == "driver"
    endings = {e["session"]: e for e in said if e.get("event") == "session-end"}
    assert endings[1]["reason"] == "turn-cap" and endings[1]["turns"] == 1
    assert endings[2]["reason"] == "persona-end" and endings[2]["turns"] == 2, \
        "the assistant ended session 2 on its last allowed turn, and the lead's [END] still counts"


def test_the_lead_ends_a_finished_session_and_never_starts_another_mode_or_invents_a_pr():
    """S19 T485-T498 of the 2026-10-14 mid-point: the handoff was done, the lead said "PR's open at #521" and "Main's
    got it", then typed /planner:shape, and a whole Shape ran inside the Grill until the cap. Each rule below names the
    behavior that run showed, so a rewording that drops one fails here."""
    rules = sim.persona_prompt(coastal())
    assert "asks you to close the session" in rules and "here when you are back" in rules
    assert "refuses because an earlier step is missing" in rules
    assert "Do not thank it, wish it luck or say goodbye first" in rules
    assert 'Never type a slash command' in rules and "never ask to start another kind of session" in rules
    assert "no pull request number" in rules and "merged, approved, reviewed or sent" in rules
    assert "news included, are everything you know" in rules


def test_the_lead_keeps_going_on_an_offer_to_close_while_the_sessions_goal_has_more():
    """S1 of the 2026-10-14 confirm run: the dump's T16 ended "Do you want to keep going, or shall I close this out?",
    as START.md tells the model to ask at about two thirds, and the old rule 9 read that as a request to close: the
    dump ended at 8 turns and 32 fewer captures than the baseline's 16. An offer ends nothing; a done session does."""
    rules = sim.persona_prompt(coastal())
    nine = rules[rules.index("\n9. "):rules.index("\n10. ")]
    assert "An offer is not an ending" in nine and "say keep going" in nine
    assert "goal is what its first message asked for" in nine and "that goal has been worked through" in nine
    assert "after doing this session's work, it asks you to close the session" in nine
    assert "Stay in this session's kind of work" in rules, "the no-mode-hopping rule stays"


def test_a_lead_turn_that_starts_another_mode_or_invents_a_pr_is_flagged(tmp_path):
    t = sim.Transcript(tmp_path / "t.jsonl")
    t.add(session=19, mode="grill", speaker="lead", text="/vela:grill the offline rule", turn=470, scripted=True)
    t.add(session=19, mode="grill", speaker="assistant", text="Closed. The pull request is open: "
          "https://github.invalid/sim/heron/pull/3", turn=476)
    t.add(session=19, mode="grill", speaker="lead", text="Good, PR 3 it is.", turn=477)
    t.add(session=19, mode="grill", speaker="lead", text="PR's open at #521.", turn=485)
    t.add(session=19, mode="grill", speaker="lead", text="Main's got it, it's merged.", turn=491)
    t.add(session=19, mode="grill", speaker="lead", text="/planner:shape APP-admin-console", turn=497)
    t.add(session=20, mode="close", speaker="lead", text="/vela:close", turn=500, scripted=True)
    assert sim.mode_hops(t) == [497], "a scripted opening is the driver's, not the persona's"
    assert sim.invented_prs(t) == [485, 491], "repeating the PR the assistant opened is not inventing one"


def test_a_team_session_runs_in_the_team_repo_with_copies_of_the_named_skills(tmp_path):
    script = {"name": "team", "persona": "coastal-merger",
              "team_repos": {"x": {"title": "X", "skills": ["requirements-grill"]}},
              "sessions": [{"mode": "requirements-grill", "cap": 2, "repo": "x", "persona": "coach-lead",
                            "vela": "/requirements-grill x", "baseline": "/requirements-grill x"}]}
    if not (sim.USER_SKILLS / "requirements-grill" / "SKILL.md").is_file():
        pytest.skip("the user's requirements-grill skill is not installed on this machine")
    path = tmp_path / "team.yaml"
    path.write_text(yaml.safe_dump(script), encoding="utf-8")
    out, log = tmp_path / "results", tmp_path / "stub-log.jsonl"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "coastal-merger", "--stub", "--script", str(path),
                           "--arms", "vela", "--out", str(out), *MODELS, "--budget", "2"],
                          capture_output=True, text=True, env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    arm = sorted(out.iterdir())[0] / "vela"
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
        shutil.copy(page, run_dir / "vela" / "vault" / page.name)
    for arm in ("vela-seuss", "baseline"):
        shutil.rmtree(run_dir / arm)
    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    summary["per_arm"] = {"vela": summary["per_arm"]["vela"]}
    summary["arms"] = ["vela"]
    (run_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    log = tmp_path / "rejudge-log.jsonl"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--rejudge", str(run_dir), "--stub",
                           "--judge-model", "j", "--budget", "1"],
                          capture_output=True, text=True, env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert set(card["judge_cuts"]) >= {"knows", "decisions"}
    assert any(c.startswith("judge input (knows) was cut to fit") for c in card["check_these"])
    assert "judge input (knows) was cut to fit" in (run_dir / "vela" / "scorecard.md").read_text(encoding="utf-8")
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
    assert "[vela] knows: " in done.stdout and f"of {sim.JUDGE_INPUT_CHARS}" in done.stdout
    assert done.stdout.count("[vela] ") == len(sim.JUDGE_CATEGORIES)


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
    for arm in ("vela-seuss", "baseline"):
        shutil.rmtree(run_dir / arm)
    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    summary["per_arm"] = {"vela": summary["per_arm"]["vela"]}
    summary["arms"] = ["vela"]
    (run_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    big = long_run_transcript(tmp_path, coastal())
    (run_dir / "vela" / "transcript.jsonl").write_text(big.path.read_text(encoding="utf-8"), encoding="utf-8")
    log = tmp_path / "long-log.jsonl"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--rejudge", str(run_dir), "--stub", "--judge-model", "j",
                           "--budget", "1"], capture_output=True, text=True,
                          env={**os.environ, "SIM_STUB_LOG": str(log)}, timeout=600)
    assert done.returncode == 0, done.stderr
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert any("left out: T" in c for c in card["check_these"] + sum(card["judge_cuts"].values(), []))
    sizes = [json.loads(line)["stdin_chars"] for line in log.read_text(encoding="utf-8").splitlines()]
    assert max(sizes) <= sim.JUDGE_INPUT_CHARS


def breakdown_run(tmp_path, written):
    """A stub run whose breakdown session writes `written` to docs/plan/x-breakdown.md in the team repo."""
    if not (sim.USER_SKILLS / "work-breakdown" / "SKILL.md").is_file():
        pytest.skip("the user's work-breakdown skill is not installed on this machine")
    script = {"name": "team", "persona": "coastal-merger", "team_repos": {"x": {"title": "X", "skills": ["work-breakdown"]}},
              "sessions": [{"mode": "breakdown", "cap": 3, "repo": "x", "persona": "coach-lead",
                            "vela": "/work-breakdown x", "baseline": "break it down"}]}
    path = tmp_path / "team.yaml"
    path.write_text(yaml.safe_dump(script), encoding="utf-8")
    env = {**os.environ}
    if written is not None:
        env["SIM_STUB_WRITE"] = f"docs/plan/x-breakdown.md::{written}"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "coastal-merger", "--stub", "--script", str(path),
                           "--arms", "vela", "--out", str(tmp_path / "results"), *MODELS, "--budget", "2"],
                          capture_output=True, text=True, env=env, timeout=600)
    return done, sorted((tmp_path / "results").iterdir())[0] / "vela"


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


# ---------------------------------------------------------------- the explorer the tool builds at the end of a run

DEMO = REPO / "tests" / "fixtures" / "explorer" / "demo_designs"
EXPLORER_DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)


def team_in_vault_run(tmp_path, write):
    """A stub run from the trading snapshot (APP-coach is in it): the team's two sessions and a closing close, all from the vault
    root. The stub's close runs the plugin's `vela explore`, as the close skill's last step does; `write` is what the stub's
    first turns create under docs/ (a JSON object of path to text), or None."""
    for skill in ("tech-design-grill", "work-breakdown"):
        if not (sim.USER_SKILLS / skill / "SKILL.md").is_file():
            pytest.skip(f"the user's {skill} skill is not installed on this machine")
    script = {"name": "team", "persona": "trading-coach", "start": "trading-coach/after-final",
              "vault_skills": ["tech-design-grill", "work-breakdown"],
              "sessions": [{"mode": "tech-design-grill", "cap": 2, "persona": "coach-lead", "vela": "/tech-design-grill coach", "baseline": "design it"},
                           {"mode": "breakdown", "cap": 2, "persona": "coach-lead", "vela": "/work-breakdown coach", "baseline": "plan it"},
                           {"mode": "close", "cap": 2, "vela": "/vela:close", "baseline": "Close out."}]}
    path = tmp_path / "team.yaml"
    path.write_text(yaml.safe_dump(script), encoding="utf-8")
    env = {**os.environ}
    if write is not None:
        env["SIM_STUB_WRITE"] = json.dumps(write)
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "trading-coach", "--stub", "--script", str(path), "--arms", "vela",
                           "--out", str(tmp_path / "results"), *MODELS, "--budget", "2"],
                          capture_output=True, text=True, env=env, timeout=600)
    return done, sorted((tmp_path / "results").iterdir())[0] / "vela"


def page_data(arm):
    page = (arm / "vault" / "dashboard.html").read_text(encoding="utf-8")
    return json.loads(EXPLORER_DATA.search(page).group(1))


def test_the_final_close_leaves_an_explorer_with_the_design_and_plan_found_in_the_vaults_docs(tmp_path):
    design = (DEMO / "pricing" / "docs/tech-design/pricing.md").read_text(encoding="utf-8").replace("prereqs:\n", "vault:\n  app: APP-coach\nprereqs:\n", 1)
    plan = (DEMO / "booking" / "docs/plan/booking-breakdown.md").read_text(encoding="utf-8").replace("docs/tech-design/booking.md", "docs/tech-design/coach.md")
    done, arm = team_in_vault_run(tmp_path, {"docs/tech-design/coach.md": design, "docs/plan/coach-breakdown.md": plan})
    assert done.returncode == 0, done.stderr
    data = page_data(arm)
    assert [d["appId"] for d in data["designs"].values()] == ["APP-coach"] and [p["appId"] for p in data["plans"].values()] == ["APP-coach"]
    assert any(e.get("event") == "explorer" and "1 tech design(s), 1 build plan(s)" in e["text"] for e in entries(arm))


def test_a_run_whose_team_wrote_no_design_still_ends_with_the_page_and_says_none_was_loaded(tmp_path):
    done, arm = team_in_vault_run(tmp_path, None)
    assert done.returncode == 0, done.stderr
    data = page_data(arm)
    assert data["designs"] == {} and data["plans"] == {}
    assert any(e.get("event") == "explorer" and "0 tech design(s), 0 build plan(s)" in e["text"] for e in entries(arm))


RETIRED = SIM / "scripts" / "retired"


def test_retired_scripts_are_kept_out_of_the_live_checks():
    """The four scripts that ran the user's own (removed) skills live in scripts/retired/, which the script checks
    above never read (their glob is one folder deep), and no live script still asks for the user's skills."""
    retired = {p.stem for p in RETIRED.glob("*.yaml")}
    assert {"heron-desk-full", "heron-desk-design", "heron-desk-design-2", "heron-desk-resume"} <= retired
    live = sorted((SIM / "scripts").glob("*.yaml"))
    assert not retired & {p.stem for p in live}
    assert [p.name for p in live if "vault_skills" in yaml.safe_load(p.read_text(encoding="utf-8"))] == []


@pytest.mark.skip(reason="heron-desk-full is retired (tests/sim/scripts/retired/): it ran the user's removed skills")
def test_the_full_heron_script_ends_with_the_explorer_the_tool_built_in_its_vault(tmp_path):
    script = RETIRED / "heron-desk-full.yaml"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "heron-desk", "--stub", "--script", str(script), "--arms", "vela",
                           "--out", str(tmp_path / "results"), *MODELS, "--budget", "5"], capture_output=True, text=True, timeout=900)
    assert done.returncode == 0, done.stderr
    arm = sorted((tmp_path / "results").iterdir())[0] / "vela"
    assert (arm / "vault" / "dashboard.html").is_file()
    assert (arm / "vault" / ".claude" / "skills" / "tech-design-grill" / "SKILL.md").is_file() and not (arm / "team-agent").exists()
    assert any(e.get("event") == "explorer" for e in entries(arm))


def test_the_vela_heron_script_uses_the_plugins_team_skills_and_leaves_the_tickets_to_the_tickets_session(tmp_path):
    script = SIM / "scripts" / "heron-desk-vela.yaml"
    data = yaml.safe_load(script.read_text(encoding="utf-8"))
    assert "vault_skills" not in data
    assert [s["mode"] for s in data["sessions"] if s["mode"] in sim.PLUGIN_TEAM_MODES] == ["design", "breakdown", "tickets"]
    prompts = " ".join(s[arm] for s in data["sessions"] for arm in ("vela", "baseline"))
    assert not re.search(r"\b(S, M|sized)\b", prompts)
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "heron-desk", "--stub", "--script", str(script), "--arms", "vela",
                           "--out", str(tmp_path / "results"), *MODELS, "--budget", "5"], capture_output=True, text=True, timeout=900)
    assert done.returncode == 0, done.stderr
    arm = sorted((tmp_path / "results").iterdir())[0] / "vela"
    assert (arm / "vault" / "dashboard.html").is_file() and not (arm / "tickets").exists()
    assert not any(e.get("event") == "tickets" for e in entries(arm))


def test_the_vela_heron_script_cuts_the_boundary_after_the_direction_is_decided():
    """Both 2026-10-14 runs put boundary before the grill that decides on-device against cloud; boundary stopped on
    the undecided direction, as it should, and no app, contract, allocation, release or tracer was ever recorded."""
    script = SIM / "scripts" / "heron-desk-vela.yaml"
    modes = [s["mode"] for s in yaml.safe_load(script.read_text(encoding="utf-8"))["sessions"]]
    boundary = modes.index("boundary")
    assert modes.index("grill") < modes.index("requirements") < boundary < modes.index("allocate"), modes
    assert modes[boundary + 1] == "close"
    assert "NOT like with like" in script.read_text(encoding="utf-8"), "the header says the order change breaks comparability"


def test_a_pr_opened_through_the_gh_stub_is_merged_by_number_and_a_handoff_reaches_origin_main(tmp_path):
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    arm_dir = tmp_path / "vela"
    arm_dir.mkdir()
    vault, _ = sim.build_vault(arm_dir, "vela", persona)
    sim.write_gh_stub(arm_dir / "bin", arm_dir / "origin.git")
    branch = "session/2026-10-05-handoff"
    sim.git("switch", "-q", "-c", branch, "main", cwd=vault)
    (vault / "sessions").mkdir(exist_ok=True)
    (vault / "sessions" / "2026-10-05-handoff.md").write_text("---\nid: 2026-10-05-handoff\nstatus: closed\n---\n", encoding="utf-8")
    (vault / "handoff-page.md").write_text('---\nhanded_off: "Booking senior, 2026-10-05, PR #1"\n---\n', encoding="utf-8")
    sim.git("add", "-A", cwd=vault)
    sim.git("commit", "-q", "-m", "Close session", cwd=vault)
    made = subprocess.run([str(arm_dir / "bin" / "gh"), "pr", "create", "--base", "main", "--head", branch, "--title", "t"],
                          capture_output=True, text=True, timeout=30, cwd=vault)
    assert made.returncode == 0 and made.stdout.strip().endswith("/pull/1")
    assert sim.merge_closed(vault, arm_dir) == [f"merged PR 1 as the reviewer: {branch} into main on origin"]
    sim.git("fetch", "-q", "origin", cwd=vault)
    page = sim.git("show", "origin/main:handoff-page.md", cwd=vault).stdout
    assert "handed_off:" in page, "the next session, team sessions included, finds the handoff on origin/main"


def test_merge_prs_must_be_true_or_false_and_defaults_on():
    persona = yaml.safe_load((SIM / "personas" / "coastal-merger.yaml").read_text(encoding="utf-8"))
    script = yaml.safe_load((SIM / "scripts" / "smoke.yaml").read_text(encoding="utf-8"))
    assert "merge_prs" not in script
    assert not sim.script_problems(script, persona)
    assert any("merge_prs" in p for p in sim.script_problems({**script, "merge_prs": "no"}, persona))
    assert not sim.script_problems({**script, "merge_prs": False}, persona)


def test_the_persona_prompt_forbids_claiming_or_promising_any_action_outside_the_chat():
    source = (SIM / "run.py").read_text(encoding="utf-8")
    assert "Never claim to do, send, run, check or chase anything outside this conversation, in any tense" in source
    assert "You may say once what you will do later." not in source


def test_parse_stream_ignores_text_blocks_with_parent_tool_use_id(tmp_path):
    """Text blocks from subagents (with parent_tool_use_id) are excluded from main assistant text
    and counted separately, preventing subagent output from inflating question counts."""
    fake_stream = json.dumps({"type": "system", "subtype": "init"}) + "\n" + \
                  json.dumps({"type": "assistant", "message": {"content": [
                      {"type": "text", "text": "Main assistant response"},
                      {"type": "text", "text": "Subagent review", "parent_tool_use_id": "tool-123"},
                      {"type": "tool_use", "name": "Agent", "input": {}}
                  ]}}) + "\n" + \
                  json.dumps({"type": "result", "total_cost_usd": 0.01, "is_error": False, "session_id": "test",
                              "result": ""})
    raw_path = tmp_path / "test.jsonl"
    raw_path.write_text(fake_stream, encoding="utf-8")
    parsed = sim.parse_stream(fake_stream, raw_path)
    assert "Main assistant response" in parsed["text"]
    assert "Subagent review" not in parsed["text"]
    assert "Subagent review" in parsed["subagent_text"]
    assert len(parsed["tools"]) == 1


def test_run_json_is_written_at_the_start(tmp_path):
    """run.json is written when a run starts so a stopped run can be rescored with --rejudge."""
    exit_code, stderr, run_folder, calls = simulate(tmp_path, "--budget", "0.5")
    assert exit_code == 0, stderr
    assert run_folder is not None
    assert (run_folder / "run.json").is_file(), "run.json should exist for a completed run"
    run_json = json.loads((run_folder / "run.json").read_text(encoding="utf-8"))
    assert "run_id" in run_json
    assert run_json["stub"] is True
    assert "started" in run_json


def test_the_teams_sessions_can_run_the_plugins_own_skills_and_the_old_user_skill_path_still_validates():
    persona = {"opening": "x", "topics": {}}

    def sessions(*pairs):
        return [{"mode": mode, "cap": 1, "persona": "coach-lead", "vela": opening, "baseline": "go"} for mode, opening in pairs]

    plugin = sessions(("design", "/vela:design coach"), ("breakdown", "/vela:breakdown coach"), ("tickets", "/vela:tickets coach"))
    assert sim.script_problems({"sessions": plugin}, persona) == []
    legacy = sessions(("tech-design-grill", "/tech-design-grill coach"), ("breakdown", "/work-breakdown coach"))
    assert sim.script_problems({"sessions": legacy, "vault_skills": ["tech-design-grill", "work-breakdown"]}, persona) == []
    wrong = sessions(("tickets", "/vela:breakdown coach"))
    assert any("must start with /vela:tickets" in p for p in sim.script_problems({"sessions": wrong}, persona))
    assert set(sim.PLUGIN_TEAM_MODES) <= set(sim.TEAM_MODES) and "tech-design-grill" in sim.TEAM_MODES


# ---- the tracer question: one scored question, does release one name a tracer or record why not

TRACER_LINE = "- **Tracer:** [[FLO-001-switch-on|FLO-001]], a person switches Heron on and gets the digest"


def test_the_judge_has_one_tracer_question_that_reads_the_releases_page(full_run):
    assert sim.JUDGE_CATEGORIES[-1] == "tracer"
    prompt = sim.judge_system_prompt("tracer")
    assert "through every app and contract it needs" in prompt and "Tracer:** none" in prompt
    persona = coastal()
    run = full_run["run"] / "vela"
    transcript = sim.Transcript.load(run / "transcript.jsonl")
    hits = sim.vault_hits(persona, transcript, run / "vault")
    text = sim.judge_input(persona, transcript, run / "vault", "tracer", hits)
    assert "THE RELEASES PAGES" in text and "----- FILE 04b-releases.md -----" in text


def test_a_tracer_reply_needs_a_grounds_note_a_known_answer_and_a_yes_or_no_for_a_tracer():
    ok = {"grounds": "the releases page", "answer": "tracer", "through_every_app": True, "where": "x", "quote": "y"}
    assert sim.category_problems(ok, {}, "tracer") == []
    assert sim.category_problems({"grounds": "x", "answer": "none_with_reason"}, {}, "tracer") == []
    assert sim.category_problems({"answer": "tracer", "through_every_app": True}, {}, "tracer") == [
        "the reply: 'grounds' must name the turns and files that bear on it and what they say"]
    assert sim.category_problems({"grounds": "x", "answer": "maybe"}, {}, "tracer") == [
        "'answer' must be one of tracer, none_with_reason, not_recorded, no_releases_session"]
    assert sim.category_problems({"grounds": "x", "answer": "tracer"}, {}, "tracer") == [
        "'through_every_app' must be true or false when the answer is tracer"]


def test_a_tracer_verdict_counts_only_when_the_page_holds_its_quote_and_it_reaches_every_app():
    pages = {"04b-releases.md": f"## Release one\n\n{TRACER_LINE}\n- **Not in the tracer:** Teams transcripts, waits on review\n"}
    quote = TRACER_LINE.lstrip("- ")
    dropped = []
    full = sim.checked_tracer({"answer": "tracer", "through_every_app": True, "where": "04b-releases.md", "quote": quote},
                              pages, dropped)
    assert full["ok"] and full["answer"] == "tracer" and dropped == []
    partial = sim.checked_tracer({"answer": "tracer", "through_every_app": False, "where": "04b-releases.md", "quote": quote},
                                 pages, dropped)
    assert partial["answer"] == "tracer" and not partial["ok"]
    invented = sim.checked_tracer({"answer": "tracer", "through_every_app": True, "where": "04b-releases.md",
                                   "quote": "**Tracer:** everything"}, pages, dropped)
    assert invented["answer"] == "not_recorded" and not invented["ok"] and len(dropped) == 1
    nowhere = sim.checked_tracer({"answer": "none_with_reason", "where": "nope.md", "quote": quote}, pages, dropped)
    assert nowhere["answer"] == "not_recorded" and len(dropped) == 2
    none = sim.checked_tracer({"answer": "none_with_reason", "where": "04b-releases.md",
                               "quote": "**Not in the tracer:** Teams transcripts, waits on review"}, pages, dropped)
    assert none["ok"] and none["answer"] == "none_with_reason"
    assert not sim.checked_tracer({"answer": "no_releases_session"}, pages, dropped)["ok"]


def test_the_scorecard_scores_the_tracer_question_from_the_releases_page(tmp_path):
    env = {"SIM_STUB_WRITE": f"04b-releases.md::\n{TRACER_LINE}\n"}
    code, err, run_dir, _ = simulate(tmp_path, "--budget", "5", env=env)
    assert code == 0, err
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["tracer"]["answer"] == "tracer" and card["tracer"]["ok"] and card["tracer"]["where"] == "04b-releases.md"
    md = (run_dir / "vela" / "scorecard.md").read_text(encoding="utf-8")
    assert "## Tracer in release one" in md and "yes: a tracer is named, through every app and contract it needs" in md
    assert "Tracer in release one" in (run_dir / "compare.html").read_text(encoding="utf-8")


def test_a_release_page_with_no_tracer_scores_no(tmp_path):
    code, err, run_dir, _ = simulate(tmp_path, "--budget", "5")
    assert code == 0, err
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["tracer"]["answer"] == "not_recorded" and not card["tracer"]["ok"]
    md = (run_dir / "vela" / "scorecard.md").read_text(encoding="utf-8")
    assert "no: release one records neither a tracer nor why not" in md


def test_a_refused_tracer_call_reads_not_scored_and_the_rest_still_count(tmp_path):
    code, err, run_dir, _ = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_JUDGE": "refuse:tracer"})
    assert code == 0, err
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert list(card["not_scored"]) == ["tracer"] and card["tracer"] is None
    md = (run_dir / "vela" / "scorecard.md").read_text(encoding="utf-8")
    assert "## Tracer in release one" in md and "## Facts captured (K):" in md


# ---- T22: the conversation-voice rule is counted, not hoped for

def voice_transcript(tmp_path, turns):
    t = sim.Transcript(tmp_path / "t.jsonl")
    for n, (speaker, text, extra) in enumerate(turns, 1):
        t.add(session=1, mode="grill", speaker=speaker, text=text, turn=n, **extra)
    return t


def test_codes_are_counted_in_what_the_assistant_says_to_the_lead(tmp_path):
    t = voice_transcript(tmp_path, [
        ("lead", "What about UNK-004 and W343?", {}),  # the lead's words never count
        ("assistant", "The pilot date is a plan, not a fact yet. What would move it?", {}),
        ("assistant", "That trips W343 and E316, and CON-002 waits on UNK-004.", {}),
        ("assistant", "It passes GATE-2 and CAP-001.FR3 is covered; run it with --gate epics.", {}),
        ("assistant", "Fine. The epics gate and the grill gate are both plain words here.", {}),
    ])
    assert sim.codes_in("W343 then CAP-001.FR3, GATE-2") == ["check code W343", "id CAP-001.FR3", "gate GATE-2"]
    voice = sim.codes_in_conversation(t)
    assert (voice["turns"], voice["turns_with_codes"], voice["codes"]) == (4, 2, 7)
    assert voice["score"] == 50
    assert [f["turn"] for f in voice["flagged"]] == [3, 4]
    assert voice["flagged"][0]["codes"] == ["check code W343", "check code E316", "id CON-002", "id UNK-004"]


def test_tool_output_and_subagent_text_are_not_what_a_person_reads(tmp_path):
    tool = [{"name": "Bash", "input": "vela check -> W343 at UNK-004 under GATE-2"}]
    t = voice_transcript(tmp_path, [("assistant", "All clear. Want the next item?", {"tool_calls": tool, "subagent_text": "E316 CON-001 CAP-002"})])
    voice = sim.codes_in_conversation(t)
    assert voice["codes"] == 0 and voice["score"] == 100 and voice["flagged"] == []


def test_a_subagent_event_is_kept_out_of_the_assistants_text_whichever_level_marks_it(tmp_path):
    stream = "\n".join(json.dumps(e) for e in [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Main reply"}]}},
        {"type": "assistant", "parent_tool_use_id": "toolu_1", "message": {"content": [{"type": "text", "text": "Review says W343 on UNK-004"}]}},
        {"type": "result", "total_cost_usd": 0.01, "is_error": False, "session_id": "s", "result": ""}])
    parsed = sim.parse_stream(stream, tmp_path / "raw.jsonl")
    assert parsed["text"] == "Main reply" and "W343" in parsed["subagent_text"]


def test_a_run_with_no_assistant_turns_has_no_voice_score(tmp_path):
    assert sim.codes_in_conversation(voice_transcript(tmp_path, [("lead", "Hello", {})]))["score"] is None


def test_the_scorecard_and_the_shape_judge_carry_the_voice_count(tmp_path):
    reply = tmp_path / "reply.txt"
    reply.write_text("It trips W343, E316 and UNK-004. Want to fix it?", encoding="utf-8")
    code, err, run_dir, _ = simulate(tmp_path, "--budget", "5", env={"SIM_STUB_REPLY": str(reply)})
    assert code == 0, err
    card = json.loads((run_dir / "vela" / "scorecard.json").read_text(encoding="utf-8"))
    assert card["voice"]["turns_with_codes"] >= 1 and card["voice"]["score"] < 100
    assert any(c.startswith("voice: T") and "W343" in c for c in card["check_these"])
    md = (run_dir / "vela" / "scorecard.md").read_text(encoding="utf-8")
    assert "## Voice: codes the lead reads" in md and f"Voice score {card['voice']['score']} of 100" in md
    persona = coastal()
    transcript = sim.Transcript.load(run_dir / "vela" / "transcript.jsonl")
    hits = sim.vault_hits(persona, transcript, run_dir / "vela" / "vault")
    shape = sim.judge_input(persona, transcript, run_dir / "vela" / "vault", "shape", hits)
    assert f"voice score {card['voice']['score']} of 100" in shape and "Do not count codes yourself" in shape


def test_a_subagent_reply_without_a_turn_renders():
    """The 2026-10-14 baseline run finished every session, then crashed writing transcript.html: a subagent's reply
    carries no turn number of its own. The page must render it, labeled, with no turn."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("simrun", REPO / "tests" / "sim" / "run.py")
    simrun = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(simrun)
    page = simrun.render_transcript("x", [{"speaker": "subagent", "session": "1", "mode": "dump", "text": "found <it>", "cost_usd": "0"}])
    assert "Subagent" in page and "found &lt;it&gt;" in page


# ---- the judge preflight: a judge that can't score stops the run before the sessions it would pay for

def fake_claude_env(tmp_path, **extra):
    """The stub first on PATH, so a run without --stub still never reaches a real model."""
    return {"PATH": os.pathsep.join([str(SIM / "stub"), os.environ.get("PATH", "")]),
            "SIM_STUB_LOG": str(tmp_path / "stub-log.jsonl"), **extra}


def logged_calls(tmp_path):
    log = tmp_path / "stub-log.jsonl"
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []


def test_a_refusing_judge_stops_the_run_at_setup_before_any_session(tmp_path):
    script = tmp_path / "two.yaml"
    script.write_text(yaml.safe_dump(TWO_SESSIONS), encoding="utf-8")
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "coastal-merger", "--script", str(script),
                           "--arms", "vela", "--out", str(tmp_path / "results"), *MODELS, "--budget", "5"],
                          capture_output=True, text=True, timeout=600,
                          env={**os.environ, **fake_claude_env(tmp_path, SIM_STUB_JUDGE="refuse:knows")})
    assert done.returncode == 4, done.stderr
    assert "failed its preflight, so no session ran" in done.stderr
    assert "knows: refused by the model's safeguards (flagged [reasoning_extraction])" in done.stderr
    calls = logged_calls(tmp_path)
    assert {c["role"] for c in calls} == {"judge"}  # no assistant or persona call was made
    assert sorted(c["category"] for c in calls) == sorted(sim.SCORING_CALLS)
    run_json = json.loads(next((tmp_path / "results").iterdir()).joinpath("run.json").read_text(encoding="utf-8"))
    assert run_json["exit"] == 4 and run_json["preflight"][0].startswith("knows: refused")


def test_the_preflight_passes_a_judge_that_answers_and_names_an_erroring_one(tmp_path, monkeypatch):
    for key, value in fake_claude_env(tmp_path).items():
        monkeypatch.setenv(key, value)
    args = sim.parse_args(["coastal-merger", *MODELS, "--budget", "5"])
    spent, problems = sim.judge_preflight(args, tmp_path / "ok")
    assert problems == [] and spent == pytest.approx(0.01 * len(sim.SCORING_CALLS))
    monkeypatch.setenv("SIM_STUB_JUDGE", "toolong:shape")
    _, problems = sim.judge_preflight(args, tmp_path / "bad")
    assert len(problems) == 1 and problems[0].startswith("shape: failed because the prompt was too long")


def test_every_preflight_input_has_the_real_shape_and_is_tiny(tmp_path):
    inputs = dict(sim.preflight_inputs(tmp_path))
    assert list(inputs) == list(sim.SCORING_CALLS)
    for category, text in inputs.items():
        assert ("THE LEAD'S WORDS" if category == "precision" else "THE TRANSCRIPT:\n") in text, category
        assert len(text) < 6000, category
    assert "----- ITEM P1 " in inputs["precision"] and "SOURCE cio-note.md" in inputs["precision"]
    assert "HINTS, which turns and files hold" in inputs["knows"] and "FILE 01-goals.md" in inputs["knows"]
    assert "INBOX DOCUMENTS:" in inputs["wrong"] and "04b-releases.md" in inputs["tracer"]


def test_a_stub_run_skips_the_preflight(tmp_path):
    code, err, run_dir, calls = simulate(tmp_path, "--budget", "5")
    assert code == 0, err
    assert not (run_dir / "judge-preflight").exists()
    assert not any(str(c.get("cwd", "")).endswith("judge-preflight") for c in calls)
