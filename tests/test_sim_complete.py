"""Task 29: the near-complete Heron script, its outsider personas and the scorecard's completeness gate. Nothing here
calls a model: the one run is --stub."""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

from conftest import REPO

SIM = REPO / "tests" / "sim"
spec = importlib.util.spec_from_file_location("sim_run_complete", SIM / "run.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]


def status_line(percent):
    return (f"Completeness: {percent}%, the average of 15 of 18 items settled, 20 of 28 open questions answered, "
            f"18 of 24 cross-cutting concern checks made, 121 of 121 standard questions dealt with, 22 of 22 pages written.")


def test_the_gate_fails_a_vault_at_79_percent_and_names_what_held_it_back():
    verdict = sim.completeness_verdict(sim.parse_completeness(status_line(79)), 80)
    assert verdict["passed"] is False and verdict["fails_run"] is True
    # weakest share first; a share at 100% held nothing back
    assert verdict["held_back"] == ["open questions answered: 20 of 28 (71%)",
                                    "cross-cutting concern checks made: 18 of 24 (75%)", "items settled: 15 of 18 (83%)"]


def test_the_gate_passes_a_vault_at_80_percent():
    verdict = sim.completeness_verdict(sim.parse_completeness(status_line(80)), 80)
    assert verdict["passed"] is True and verdict["fails_run"] is False


def test_a_missing_completeness_figure_fails_the_gate_rather_than_passing_it():
    verdict = sim.completeness_verdict(sim.parse_completeness("vela status: 3 apps"), 80)
    assert verdict["passed"] is False and verdict["fails_run"] and verdict["held_back"][0].startswith("no figure")


def test_a_stub_run_reports_the_gate_without_failing_the_run():
    verdict = sim.completeness_verdict(sim.parse_completeness(status_line(46)), 80, enforced=False)
    assert verdict["passed"] is False and verdict["fails_run"] is False


def test_under_the_gate_exits_3_and_a_tool_failure_still_outranks_it():
    assert sim.run_exit(False, False, ["arm"]) == 3
    assert sim.run_exit(False, True, ["arm"]) == 3, "an early stop does not hide a run that does not count"
    assert sim.run_exit(True, False, ["arm"]) == 2
    assert sim.run_exit(False, True, []) == 1 and sim.run_exit(False, False, []) == 0


def test_the_scorecard_reads_the_completeness_line_vela_status_prints_for_the_vault(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(SIM / "snapshots" / "heron-desk" / "after-design-2", vault)
    found = sim.completeness_of(vault)
    assert "error" not in found, found
    assert found["line"].startswith(f"Completeness: {found['percent']}%") and len(found["shares"]) == 5
    arm = SimpleNamespace(vault=vault, completeness_gate=80, args=SimpleNamespace(stub=False))
    md = "\n".join(sim.render_completeness({"completeness": found,
                                            "completeness_gate": sim.completeness_verdict(found, arm.completeness_gate)}))
    assert "## Completeness" in md and "Gate 80%: FAIL" in md and "held back by open questions answered" in md


SCRIPT = SIM / "scripts" / "heron-desk-complete.yaml"
SNAPSHOT_RUNS = ("after-full-1", "after-handoff-1", "after-design-2")


def complete_script():
    return yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))


def persona(name):
    return yaml.safe_load((SIM / "personas" / f"{name}.yaml").read_text(encoding="utf-8"))


def snapshot_unknowns():
    found = set()
    for run in SNAPSHOT_RUNS:
        page = SIM / "snapshots" / "heron-desk" / run / "11-unknowns-and-risks.md"
        found |= set(re.findall(r"^### (UNK-\d+ .+?)\s*$", page.read_text(encoding="utf-8"), re.M))
    return found


def news_facts(script):
    items = list((script.get("news") or {}).get("knows") or [])
    for event in script.get("events") or []:
        items += event.get("knows") or []
    return {k["id"]: k for k in items}


def test_every_outsider_answer_is_in_a_persona_news():
    """Every open unknown of the earlier Heron runs has an answer in some persona's facts, with the fact's owner, and
    every outsider who answers is one a session brings in. An answer nobody holds would have to be invented."""
    script = complete_script()
    table = {row["unknown"]: row["by"] for row in script["answers"]}
    missing = sorted(snapshot_unknowns() - set(table))
    assert not missing, f"unknowns with no answer in the table: {missing}"
    brought_in = {s["persona"] for s in script["sessions"] if s.get("persona")}
    news = news_facts(script)
    for unknown, refs in table.items():
        assert refs, unknown
        for ref in refs:
            source, item_id = ref.split(":")
            if source == "news":
                fact = news.get(item_id)
            else:
                assert source == "heron-desk" or source in brought_in, f"{unknown}: {source} is never brought into a session"
                fact = next((k for k in persona(source)["knows"] if k["id"] == item_id), None)
            assert fact and fact.get("owner"), f"{unknown}: {ref} is not a fact with an owner"


def test_the_outsiders_cannot_hand_over_the_leads_gaps_or_correct_its_beliefs():
    lead = persona("heron-desk")
    guarded = [k for kind in ("unaware", "wrong") for item in lead[kind] for k in item["keywords"]]
    for name in {s["persona"] for s in complete_script()["sessions"] if s.get("persona")} - {"heron-agent-lead"}:
        outsider = persona(name)
        assert outsider.get("outsider") is True and sim.persona_problems(outsider) == [], name
        for fact in outsider["knows"]:
            assert fact.get("owner"), (name, fact["id"])
            assert not sim.mentions(fact["fact"], guarded), (name, fact["id"], sim.mentions(fact["fact"], guarded))


def test_the_script_brings_each_outsider_in_and_keeps_vela_unchanged():
    script = complete_script()
    named = [s["persona"] for s in script["sessions"] if s.get("persona")]
    for outsider in ("heron-ciso", "heron-dpo", "heron-legal", "heron-identity", "heron-vendor", "heron-pilot-lead",
                     "heron-works-council"):
        assert outsider in named
    assert script["completeness_gate"] == 80 and script["start"] == "heron-desk/empty"
    vela = yaml.safe_load((SIM / "scripts" / "heron-desk-vela.yaml").read_text(encoding="utf-8"))
    assert "completeness_gate" not in vela
    assert {s.get("persona") for s in vela["sessions"]} <= {None, "heron-agent-lead"}
    assert sim.script_problems(script, persona("heron-desk")) == []


def test_a_session_naming_a_persona_that_is_not_there_is_refused_before_any_call():
    script = {"sessions": [{"mode": "grill", "cap": 2, "persona": "heron-nobody", "vela": "/vela:grill x",
                            "baseline": "Take me through x."}]}
    assert any("heron-nobody" in p for p in sim.script_problems(script, persona("heron-desk")))


@pytest.fixture(scope="module")
def complete_run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("complete")
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "heron-desk", "--stub", "--script", str(SCRIPT),
                           "--arms", "vela", "--out", str(tmp / "results"), *MODELS, "--budget", "20"],
                          capture_output=True, text=True, timeout=1800)
    return done, sorted((tmp / "results").iterdir())[0] / "vela"


def test_the_stub_run_passes_with_every_outsider_session(complete_run):
    done, arm = complete_run
    assert done.returncode == 0, done.stderr[-3000:]
    rows = [json.loads(line) for line in (arm / "transcript.jsonl").read_text(encoding="utf-8").splitlines()]
    spoke = {r.get("persona") for r in rows if r.get("speaker") == "lead" and r.get("persona")}
    assert {s["persona"] for s in complete_script()["sessions"] if s.get("persona")} <= spoke
    endings = json.loads((arm.parent / "run.json").read_text(encoding="utf-8"))["per_arm"]["vela"]["endings"]
    assert len(endings) == len(complete_script()["sessions"]) and all(e["reason"] == "persona-end" for e in endings)


def test_the_stub_scorecard_reports_completeness_and_the_gate_it_does_not_enforce(complete_run):
    _, arm = complete_run
    card = json.loads((arm / "scorecard.json").read_text(encoding="utf-8"))
    assert "error" not in card["completeness"], card["completeness"]
    verdict = card["completeness_gate"]
    assert verdict["gate"] == 80 and verdict["enforced"] is False and verdict["fails_run"] is False
    md = (arm / "scorecard.md").read_text(encoding="utf-8")
    assert "## Completeness" in md and card["completeness"]["line"] in md


def test_the_invented_facts_judge_reads_what_each_outsider_could_say(complete_run):
    _, arm = complete_run
    transcript = sim.Transcript.load(arm / "transcript.jsonl")
    script = complete_script()
    lead = sim.final_brief(persona("heron-desk"), script)
    outsiders = list(sim.outsiders_of(script).values())
    hits = sim.vault_hits(lead, transcript, arm / "vault")
    shape, _ = sim.build_judge_input(lead, transcript, arm / "vault", "shape", hits, outsiders=outsiders)
    assert "Helen Achterberg" in shape and "only review" in shape and "K55" in shape
    knows, _ = sim.build_judge_input(lead, transcript, arm / "vault", "knows", hits, outsiders=outsiders)
    assert "Helen Achterberg" not in knows, "only the whole-brief call reads the outsiders; the K list is the lead's own"
