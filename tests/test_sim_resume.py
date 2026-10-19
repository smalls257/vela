"""--resume-run: a run that was killed, crashed or ran out of budget goes on from where it stopped, against the stub.
The bar is the user's: nothing already paid for is paid for again, and a resume that can't afford one more session
says so before it spends anything."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml

from conftest import REPO, built_once

SIM = REPO / "tests" / "sim"
spec = importlib.util.spec_from_file_location("sim_run_resume", SIM / "run.py")
sim = importlib.util.module_from_spec(spec)
sys.modules["sim_run_resume"] = sim
spec.loader.exec_module(sim)

MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]
THREE_SESSIONS = {"name": "three", "sessions": [
    {"mode": "dump", "cap": 3, "vela": "/vela:dump {opening}", "baseline": "Let's dump what we know. {opening}"},
    {"mode": "discover", "cap": 3, "vela": "/vela:discover", "baseline": "What don't we know yet?"},
    {"mode": "close", "cap": 3, "vela": "/vela:close", "baseline": "Close out this session."}]}
ARMS = "vela,vela-seuss"
ASSISTANT_CALLS_PER_SESSION = 2  # the stub asks once, then says the session is over


def stub_env(log, **extra):
    return {**os.environ, "SIM_STUB_LOG": str(log), **extra}


def start(tmp_path, *extra, env=None):
    """A new stub run over the three-session script. Returns (exit code, stderr, run folder)."""
    script = tmp_path / "three.yaml"
    script.write_text(yaml.safe_dump(THREE_SESSIONS), encoding="utf-8")
    out = tmp_path / "results"
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "coastal-merger", "--stub", "--script", str(script),
                           "--arms", ARMS, "--out", str(out), "--budget", "5", *MODELS, *extra],
                          capture_output=True, text=True, env=env or stub_env(tmp_path / "log.jsonl"), timeout=600)
    runs = sorted(out.iterdir()) if out.is_dir() else []
    return done.returncode, done.stderr, runs[0] if runs else None


def resume(run_dir, log, *extra):
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "--resume-run", str(run_dir), *extra],
                          capture_output=True, text=True, env=stub_env(log), timeout=600)
    return done.returncode, done.stderr


def calls(log):
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []


def entries(arm_dir):
    return [json.loads(line) for line in (arm_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()]


def run_json(run_dir):
    return json.loads((run_dir / "run.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def uninterrupted(tmp_path_factory):
    """The whole three-session stub run, built once per session; tests read it and copy it before changing it."""
    def build(folder):
        code, err, _ = start(folder)
        assert code == 0, err
    return sorted((built_once(tmp_path_factory, "resume-uninterrupted", build) / "results").iterdir())[0]


def killed(tmp_path, at):
    """A run whose driver the stub kills at its `at`-th assistant call, as a crash would."""
    log = tmp_path / "log.jsonl"
    code, err, run_dir = start(tmp_path, env=stub_env(log, SIM_STUB_KILL_AT=str(at)))
    assert code == -9, f"the driver should have been killed: exit {code}\n{err}"
    return run_dir, log


def session_list(run_dir):
    return {arm: record["endings"] for arm, record in run_json(run_dir)["per_arm"].items()}


@pytest.mark.parametrize("at, where", [(2 * ASSISTANT_CALLS_PER_SESSION + 1, "at session 3's opening"),
                                       (2 * ASSISTANT_CALLS_PER_SESSION + 2, "inside session 3")])
def test_a_run_killed_after_session_2_resumes_to_the_session_list_of_an_uninterrupted_run(tmp_path, uninterrupted, at, where):
    run_dir, log = killed(tmp_path, at)
    # run.json was written after every session, so the kill cost it nothing it had already said
    after_kill = run_json(run_dir)
    assert after_kill["per_arm"]["vela"]["through_session"] == 2 and "exit" not in after_kill
    assert [e["session"] for e in after_kill["per_arm"]["vela"]["endings"]] == [1, 2]
    assert not (run_dir / "vela-seuss").exists(), "the second arm never started"
    before = len(calls(log))

    code, err = resume(run_dir, log)
    assert code == 0, err
    assert session_list(run_dir) == session_list(uninterrupted)
    made = calls(log)[before:]
    vela_calls = [c for c in made if c["role"] == "assistant" and "/vela-seuss/" not in c["cwd"]]
    # sessions 1 and 2 are never played again; session 3 goes on where it stopped
    assert len(vela_calls) == (2 if where == "at session 3's opening" else 1)
    assert not any("/vela:dump" in " ".join(c["argv"]) or "/vela:discover" in " ".join(c["argv"]) for c in vela_calls)
    vela = entries(run_dir / "vela")
    for index in (1, 2, 3):
        assert sum(1 for e in vela if e.get("event") == "session-start" and e["session"] == index) == 1
        assert sum(1 for e in vela if e.get("event") == "session-end" and e["session"] == index) == 1
    continued = [e for e in vela if e.get("event") == "session-continued"]
    assert len(continued) == 1 and "uncommitted" in continued[0]["text"]
    if where == "inside session 3":
        first_reply = next(e for e in vela if e["speaker"] == "assistant" and e["session"] == 3)
        assert vela_calls[0]["argv"][vela_calls[0]["argv"].index("--resume") + 1] == first_reply["session_id"]
    summary = run_json(run_dir)
    assert summary["exit"] == 0 and summary["resumes"][0]["from"]["vela"].startswith("goes on from session 3")
    assert summary["spent_usd"] == pytest.approx(run_json(uninterrupted)["spent_usd"], abs=0.011)
    assert (run_dir / "vela" / "scorecard.json").is_file() and (run_dir / "vela-seuss" / "scorecard.json").is_file()
    assert (run_dir / "compare.html").is_file() and (run_dir / "vela" / "transcript.html").is_file()


def test_a_killed_run_whose_run_json_has_no_per_arm_resumes_with_its_spend_rebuilt(tmp_path, uninterrupted):
    run_dir, log = killed(tmp_path, 2 * ASSISTANT_CALLS_PER_SESSION + 2)
    summary = run_json(run_dir)
    del summary["per_arm"], summary["preflight_usd"], summary["spent_usd"]
    (run_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    code, err = resume(run_dir, log)
    assert code == 0, err
    after = run_json(run_dir)
    assert session_list(run_dir) == session_list(uninterrupted)
    assert any("no per_arm" in note and "rebuilt from transcript.jsonl" in note for note in after["notes"])
    assert after["spent_usd"] == pytest.approx(run_json(uninterrupted)["spent_usd"], abs=0.011)


def test_a_finished_run_that_crashed_before_its_summary_is_finished_without_a_single_call(tmp_path, uninterrupted):
    """The 2026-10-14 baseline: every session ran and was judged, then transcript.html raised and run.json kept no
    per_arm. A resume pays for nothing: it writes the pages and the summary from what is on disk."""
    run_dir = tmp_path / uninterrupted.name
    shutil.copytree(uninterrupted, run_dir, symlinks=True)
    summary = run_json(run_dir)
    for key in ("per_arm", "exit", "spent_usd", "preflight_usd"):
        summary.pop(key)
    (run_dir / "run.json").write_text(json.dumps(summary), encoding="utf-8")
    for arm in ("vela", "vela-seuss"):
        (run_dir / arm / "transcript.html").unlink()
    log = tmp_path / "log.jsonl"
    code, err = resume(run_dir, log)
    assert code == 0, err
    assert calls(log) == []
    after = run_json(run_dir)
    assert session_list(run_dir) == session_list(uninterrupted)
    assert after["spent_usd"] == pytest.approx(run_json(uninterrupted)["spent_usd"], abs=1e-6)
    assert all((run_dir / arm / "transcript.html").is_file() for arm in ("vela", "vela-seuss"))
    assert "scored already" in after["resumes"][0]["from"]["vela"]


def test_a_budget_too_small_for_one_more_session_is_refused_with_the_number_before_anything_is_spent(tmp_path):
    run_dir, log = killed(tmp_path, 2 * ASSISTANT_CALLS_PER_SESSION + 1)
    before_json, before_calls = (run_dir / "run.json").read_bytes(), len(calls(log))
    code, err = resume(run_dir, log, "--budget", "0.05")
    assert code == sim.RESUME_REFUSED, err
    assert "nothing was spent" in err and "vela arm has $0.00 of session room left" in err
    needed = float(err.split("Resume with --budget ")[1].split()[0])
    assert needed > 0.05
    assert (run_dir / "run.json").read_bytes() == before_json and len(calls(log)) == before_calls
    assert not (run_dir / "vela-seuss").exists()
    # The number buys the session it names. No arm here has been judged, so judging is held to the 15% reserve,
    # which the stub's judge outspends: the run stops at the judge, and a resume with more money only judges.
    code, err = resume(run_dir, log, "--budget", f"{needed:.2f}")
    assert "has been judged yet" in err
    assert [e["reason"] for e in sim.endings_in(entries(run_dir / "vela"))] == ["persona-end"] * 3
    if code == 2:
        assert "no budget left for the" in err
        played = len(calls(log))
        code, err = resume(run_dir, log, "--budget", "5")
        assert code == 0, err
        assert not [c for c in calls(log)[played:] if c["role"] == "assistant" and "/vela-seuss/" not in c["cwd"]]
    assert code == 0, err
    assert [e["session"] for e in run_json(run_dir)["per_arm"]["vela"]["endings"]] == [1, 2, 3]


def test_a_failure_writing_an_arms_pages_is_recorded_and_the_summary_still_written(tmp_path, monkeypatch):
    script = tmp_path / "three.yaml"
    script.write_text(yaml.safe_dump(THREE_SESSIONS), encoding="utf-8")
    monkeypatch.setenv("SIM_STUB_LOG", str(tmp_path / "log.jsonl"))

    def broken(*_):
        raise KeyError("turn")
    monkeypatch.setattr(sim, "render_transcript", broken)
    code = sim.main(["coastal-merger", "--stub", "--script", str(script), "--arms", "vela", "--out",
                     str(tmp_path / "results"), "--budget", "5", *MODELS])
    run_dir = next((tmp_path / "results").iterdir())
    summary = run_json(run_dir)
    assert code == 2 and summary["exit"] == 2
    assert "KeyError" in summary["per_arm"]["vela"]["finish_failure"]
    assert len(summary["per_arm"]["vela"]["endings"]) == 3 and (run_dir / "vela" / "scorecard.json").is_file()
    monkeypatch.undo()
    log = tmp_path / "resume-log.jsonl"
    code, err = resume(run_dir, log)
    assert code == 0, err
    assert calls(log) == [] and (run_dir / "vela" / "transcript.html").is_file()
    assert run_json(run_dir)["per_arm"]["vela"]["finish_failure"] is None


def test_resume_takes_the_models_script_and_arms_from_run_json_only(tmp_path):
    for flag in (["--model", "m"], ["--judge-model", "j"], ["--arms", "vela"], ["--stub"], ["coastal-merger"]):
        with pytest.raises(SystemExit):
            sim.parse_args(["--resume-run", str(tmp_path), *flag])
    assert sim.parse_args(["--resume-run", str(tmp_path)]).budget is None
    assert sim.parse_args(["--resume-run", str(tmp_path), "--budget", "3"]).budget == 3


def test_a_script_changed_since_the_run_is_refused():
    entries = [{"speaker": "driver", "event": "session-start", "session": 1, "mode": "dump", "text": ""}]
    with pytest.raises(sim.ToolFailure, match="session 1 was dump and is now close"):
        sim.check_script_matches({"sessions": [{"mode": "close"}]}, entries)


def test_news_recorded_before_it_rode_along_is_matched_to_the_script_then_the_applied_inbox(tmp_path):
    persona = {"knows": [{"id": "K1", "fact": "a"}], "decisions": []}
    script = {"events": [{"after": 1, "knows": [{"id": "K2", "fact": "from the script"}]}]}
    applied = tmp_path / "applied"
    applied.mkdir()
    (applied / "01.yaml").write_text(yaml.safe_dump({"knows": [{"id": "K3", "fact": "dropped in live"}]}), encoding="utf-8")
    news = [{"speaker": "driver", "event": "news", "session": 2, "text": ""},
            {"speaker": "driver", "event": "news", "session": 2, "text": ""},
            {"speaker": "driver", "event": "news", "session": 3, "text": "", "news": {"knows": [{"id": "K4", "fact": "x"}]}}]
    assert [k["id"] for k in sim.news_so_far(persona, script, news, applied)["knows"]] == ["K1", "K2", "K3", "K4"]
    with pytest.raises(sim.ToolFailure, match="neither the script nor news-inbox/applied"):
        sim.news_so_far(persona, script, news[:2] * 2, applied)
