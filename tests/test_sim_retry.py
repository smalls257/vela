"""A slow persona or judge call is sent once more; a slow assistant call is not, because it may have edited files."""
import importlib.util
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sim_run_retry", REPO / "tests" / "sim" / "run.py")
sim = importlib.util.module_from_spec(spec)
sys.modules["sim_run_retry"] = sim
spec.loader.exec_module(sim)


def slow_then(answer, calls):
    def run(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output="half a reply")
        return subprocess.CompletedProcess(argv, 0, stdout=answer, stderr="")
    return run


def test_a_slow_persona_call_is_sent_once_more_and_its_partial_output_kept(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(sim.subprocess, "run", slow_then('{"result": "fine"}', calls))
    done = sim.call(["claude"], env={}, cwd=tmp_path, raw_path=tmp_path / "raw" / "001-persona.txt", kind="persona", stdin="hi")
    assert done.stdout == '{"result": "fine"}' and len(calls) == 2
    assert "sending it once more" in capsys.readouterr().out


def test_a_slow_assistant_call_fails_at_once_with_its_partial_output_on_disk(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sim.subprocess, "run", slow_then("unused", calls))
    raw = tmp_path / "raw" / "001-assistant.txt"
    with pytest.raises(sim.ToolFailure, match="assistant call ran past"):
        sim.call(["claude"], env={}, cwd=tmp_path, raw_path=raw, kind="assistant")
    assert len(calls) == 1 and "half a reply" in raw.read_text(encoding="utf-8")


def test_a_persona_call_slow_twice_fails_and_says_twice(tmp_path, monkeypatch):
    def always_slow(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
    monkeypatch.setattr(sim.subprocess, "run", always_slow)
    with pytest.raises(sim.ToolFailure, match="twice"):
        sim.call(["claude"], env={}, cwd=tmp_path, raw_path=tmp_path / "raw" / "002-persona.txt", kind="persona", stdin="hi")
