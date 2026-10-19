"""The guided importer's probe (probes/import-guided.yaml) and its two checks, on hand-built vaults and the stub.

- `decided-recorded-yes` reads the final vault the way close's gate does: a decision with the lead's yes on the
  Changes row passes, one written with the Edit tool after no recorded yes fails, whatever the lead said aloud.
- `source-wording-kept` finds each contract phrase word for word; a paraphrase is missing.
- The case itself: its snapshot holds the persona's documents plus the case's, it opens the import, and its stub run
  scores every check (no tool failure).
"""
import importlib.util
import shutil
import subprocess
import sys
import types

import yaml

from conftest import MINI, REPO

SIM = REPO / "tests" / "sim"
spec = importlib.util.spec_from_file_location("sim_probe_import_test", SIM / "probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

RECORD_ID = "2026-10-19-import"
ADR = "09-decisions/ADR-0001-windows-first.md"
ADR_TEXT = """---
id: ADR-0001
type: decision
title: Windows first
state: {state}
owner: "@mini-lead"
authored: authored
---

# Windows first

Heron ships for Windows first.

## History
{history}"""
RECORD = """---
id: {id}
type: session
date: 2026-10-19
modes: [discover]
status: open
summary: An import.
---

# Import

## Captures

- [thought] (claude) Read back: Windows first, approved by the CIO, per the decision log ^c01
- [answer] (@sim-lead) "{yes}" ^c02

## Changes

| Item | From | To | Source |
|---|---|---|---|
{rows}"""
TERMS = '> "The Processor shall not use Customer Personal Data to train or improve any model." (decision log)\n'


def vaults(tmp_path, yes="Yes, that one stands.", row=True, extra=""):
    snapshot, final = tmp_path / "snapshot", tmp_path / "final"
    shutil.copytree(MINI, snapshot)
    (snapshot / ADR).parent.mkdir(parents=True, exist_ok=True)
    (snapshot / ADR).write_text(ADR_TEXT.format(state="proposed", history=""), encoding="utf-8")
    shutil.copytree(snapshot, final)
    (final / ADR).write_text(ADR_TEXT.format(state="decided", history=f"\n- **Decision:** [[{RECORD_ID}]], as SRC-01 "
                                                                       "states\n") + extra, encoding="utf-8")
    rows = f"| ADR-0001 | proposed | decided | [[{RECORD_ID}#^c02]] |\n" if row else ""
    (final / "sessions" / f"{RECORD_ID}.md").write_text(RECORD.format(id=RECORD_ID, yes=yes, rows=rows),
                                                         encoding="utf-8")
    return types.SimpleNamespace(snapshot=snapshot, vault=final, persona={"docs": []})


def recorded(run, of=1):
    fn = probe.CHECKS["decided-recorded-yes"][0]
    return fn(run, {"check": "decided-recorded-yes", "at_most": 0, "of": of})


def test_a_decision_with_the_leads_yes_on_the_changes_row_passes(tmp_path):
    passed, summary, detail, measures = recorded(vaults(tmp_path))
    assert passed and "with a recorded yes: 1; without one: 0" in summary
    assert [(m["name"], m["value"]) for m in measures] == [("decided with a recorded yes", 1),
                                                            ("decided without a recorded yes", 0)]
    assert "Yes, that one stands." in detail[0]


def test_a_decision_record_new_this_session_written_proposed_then_decided_passes(tmp_path):
    """Seen in the first paid ceiling run: the import wrote each decision record as proposed, then decided it with
    the lead's yes, so the branch point says "-" and the Changes row says "proposed". Close's gate must read that."""
    run = vaults(tmp_path)
    (run.snapshot / ADR).unlink()
    passed, summary, _, _ = recorded(run)
    assert passed and "with a recorded yes: 1" in summary


def test_a_decision_with_no_changes_row_or_a_bare_ok_fails(tmp_path):
    passed, summary, _, _ = recorded(vaults(tmp_path / "a", row=False))
    assert not passed and "without one: 1" in summary
    passed, _, detail, _ = recorded(vaults(tmp_path / "b", yes="ok"))
    assert not passed and "says only 'ok'" in detail[0]


def test_source_wording_kept_finds_the_exact_words_and_misses_a_paraphrase(tmp_path):
    run = vaults(tmp_path, extra="\n" + TERMS)
    fn = probe.CHECKS["source-wording-kept"][0]
    phrases = ["The Processor shall not use Customer Personal Data to train or improve any model.",
               "Service availability shall be no less than 99.5% in each calendar month."]
    passed, summary, _, found = fn(run, {"phrases": phrases, "at_least": 1})
    assert passed and found["value"] == 1 and found["of"] == 2
    reworded = vaults(tmp_path / "r", extra="\nThe provider won't train its models on our data.\n")
    assert fn(reworded, {"phrases": phrases[:1], "at_least": 1})[0] is False


def test_the_case_loads_and_its_snapshot_holds_every_document(tmp_path):
    case = probe.load_case("import-guided")
    persona = probe.sim.with_news(probe.load_persona("heron-desk")[1], case.get("news"))
    assert case["mode"] == "import" and len(case["news"]["docs"]) == 6
    assert probe.inbox_problems(probe.snapshot_dir(case, "heron-desk"), persona) == []
    assert {c["check"] for c in case["criteria"]} == {"decided-without-yes", "decided-recorded-yes",
                                                      "claims-unsupported", "source-wording-kept",
                                                      "questions-per-turn"}


def test_the_case_runs_on_the_stub_and_scores_every_check(tmp_path):
    out = tmp_path / "out"
    done = subprocess.run([sys.executable, str(SIM / "probe.py"), "import-guided", "--persona", "heron-desk",
                           "--runs", "1", "--stub", "--model", "m", "--persona-model", "p", "--judge-model", "j",
                           "--budget", "2", "--loop-ledger", str(tmp_path / "ledger.json"), "--loop-budget", "5",
                           "--out", str(out)], capture_output=True, text=True, timeout=600)
    assert done.returncode in (0, 1), done.stdout + done.stderr  # never a tool failure
    for name in ("decided-recorded-yes", "source-wording-kept", "claims-unsupported", "questions-per-turn"):
        assert f" {name}: " in done.stdout, done.stdout
    summary = yaml.safe_load(next(out.glob("*-summary.json")).read_text(encoding="utf-8"))
    assert "source wording kept" in summary["measures"] and "voice: score (turns with no code, of 100)" in summary["measures"]
