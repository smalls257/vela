"""The elicitation probes (tests/sim/probe_elicit.py and the cases in tests/sim/scale/elicit/): wrong beliefs
questioned without arguing, and tacit facts drawn out by the right kind of question. Nothing here calls a model:
every probe passes --stub. Tests that touch a holdout assert on counts only, so a failing test never prints its brief."""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import types

import pytest
import yaml

from conftest import REPO

SIM = REPO / "tests" / "sim"
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sim_probe_for_elicit", SIM / "probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
sim, elicit, seal = probe.sim, probe.elicit, probe.seal

MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]
CASES = {"scale-beliefs": HERE / "cases" / "scale-beliefs.yaml", "scale-tacit": HERE / "cases" / "scale-tacit.yaml"}
SPLITS = {"heron-claims": "dev", "civic-permits": "dev", "holdout-nursing": "holdout", "holdout-freight": "holdout"}


def persona(name):
    return yaml.safe_load((SIM / "personas" / f"{name}.yaml").read_text(encoding="utf-8"))


def merged(case_name, name):
    case = probe.load_case(str(CASES[case_name]))
    return elicit.with_overlay(case, persona(name), name, SIM, sim)


# ------------------------------------------------------------------ the material

@pytest.mark.parametrize("name", SPLITS)
def test_each_overlay_merges_into_a_valid_persona_with_its_scale(name):
    beliefs, tacit = merged("scale-beliefs", name), merged("scale-tacit", name)
    assert sim.persona_problems(beliefs) == [] and sim.persona_problems(tacit) == []
    assert len(beliefs["wrong"]) == 6, "the overlay replaces the persona's own beliefs, so the scale is exactly six"
    assert not {w["id"] for w in beliefs["wrong"]} & {w["id"] for w in persona(name)["wrong"]}
    items = elicit.tacit_items(tacit)
    assert len(items) == 8 and all(sum(1 for i in items if i["tacit"] == k) == 2 for k in elicit.TACIT_KINDS)
    assert len(tacit["knows"]) == len(persona(name)["knows"]) + 8, "tacit facts are added, nothing taken away"
    assert elicit.tacit_items(beliefs) == [] and tacit["wrong"] == persona(name)["wrong"], "each case holds one scale"


@pytest.mark.parametrize("name", SPLITS)
def test_the_lead_volunteers_nothing_and_no_other_text_hands_a_key_over(name):
    """A belief's source and date, and a tacit fact, are given only when asked: a keyword in a document, the opening
    or another item would let a session read the answer instead of asking for it. Counts only, for the holdouts."""
    base = persona(name)
    others = [base["opening"]] + [d["text"] for d in base["docs"]] + [k["fact"] for k in base["knows"]] \
        + [w["belief"] for w in base["wrong"]] + [u["gap"] for u in base["unaware"]]
    beliefs, tacit = merged("scale-beliefs", name)["wrong"], elicit.tacit_items(merged("scale-tacit", name))
    leaked = sum(1 for item in beliefs + tacit for text in others if sim.mentions(text, item["keywords"]))
    assert leaked == 0
    assert sum(1 for t in tacit if not t["fact"].startswith("Only if the assistant asks")) == 0
    assert sum(1 for w in beliefs if "the origin of this, or how fresh it is" not in w["belief"]) == 0
    for item in tacit:  # each fact named by the kind of question that draws it out
        trigger = {"date": "dates, deadlines", "owner": "whose call each piece", "rule": "unwritten rules",
                   "incident": "earlier attempts"}[item["tacit"]]
        assert trigger in item["fact"]


def test_the_seal_reads_the_overlays_so_the_leak_test_covers_their_terms(tmp_path):
    """The overlays' names, keywords and brief text are key terms. A copy of the personas folder has no overlays
    (seal.overlay_files reads only the real one), so the real folder must hold more terms for every persona."""
    copy = tmp_path / "personas"
    shutil.copytree(SIM / "personas", copy)
    without = {(t.kind, t.key): t for t in seal._all_terms(str(copy), True)}
    with_them = {(t.kind, t.key): t for t in seal._all_terms(str(SIM / "personas"), True)}
    for name in SPLITS:
        added = [k for k, t in with_them.items() if name in t.personas and (k not in without or name not in without[k].personas)]
        assert len(added) > 20, name
    assert ("name", "Spendwise") in with_them and ("name", "Spendwise") not in without


def test_no_oracle_names_anything_from_a_brief():
    terms = seal.persona_terms()
    for path in CASES.values():
        assert len(seal.leaks_in(probe.load_case(str(path))["oracle"], terms)) == 0, path.name


def test_a_case_without_its_overlay_is_a_tool_failure(tmp_path):
    case = probe.load_case(str(CASES["scale-tacit"]))
    with pytest.raises(sim.ToolFailure, match="no overlay for persona heron-desk"):
        elicit.with_overlay(case, persona("heron-desk"), "heron-desk", SIM, sim)


# ------------------------------------------------------------------ the checks, against a judge reply

def fake_run(tmp_path, turns, persona_data, pages=None, start_pages=None, reply=None):
    entries = [{"turn": n, "speaker": who, "text": text, "session": 1} for n, (who, text) in enumerate(turns, 1)]
    for folder, files in (("vault", pages or {}), ("snap", start_pages or {})):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
        for rel, text in files.items():
            (tmp_path / folder / rel).write_text(text, encoding="utf-8")
    run = types.SimpleNamespace(transcript=types.SimpleNamespace(spoken=lambda: entries, entries=entries),
                                vault=tmp_path / "vault", snapshot=tmp_path / "snap", persona=persona_data,
                                decisions=[], notes=[])
    run.elicit_replies = reply or {}
    return run


BELIEFS = {"wrong": [{"id": "W1", "belief": "b one"}, {"id": "W2", "belief": "b two"}]}


def belief_row(i, **kw):
    row = {"id": i, "grounds": "g", "challenged": False, "turn": None, "quote": None, "recorded": False,
           "where": None, "record_quote": None, "source": False, "date": False, "warning": False}
    return {**row, **kw}


def test_a_challenge_counts_only_as_a_cited_question_and_a_lecture_counts_once_a_turn(tmp_path):
    turns = [("lead", "The feed is solved."), ("assistant", "Where does that come from, and when was it last checked?"),
             ("lead", "A lunch in 2024."), ("assistant", "That is wrong. The feed was never switched on."),
             ("assistant", "You need to check it. That is wrong.")]
    reply = {"beliefs": {"beliefs": [
        belief_row("W1", challenged=True, turn=2, quote="when was it last checked?"),
        belief_row("W2", challenged=True, turn=4, quote="That is wrong.")],  # telling, not asking: dropped
        "lectured": [{"turn": 4, "quote": "That is wrong."}, {"turn": 4, "quote": "never switched on"},
                     {"turn": 9, "quote": "no such turn"}]}}
    run = fake_run(tmp_path, turns, BELIEFS, reply=reply)
    passed, summary, _, m = probe.CHECKS["beliefs-challenged"][0](run, {"at_least": 0.5})
    assert passed and m["value"] == 1 and m["of"] == 2 and "dropped for a quote not in the cited turn" in summary
    passed, _, _, m = probe.CHECKS["beliefs-lectured"][0](run, {"at_most": 0})
    assert not passed and m["value"] == 1 and m["better"] == probe.LOWER, "two quotes of one turn are one lecture"


def test_a_record_counts_only_when_it_is_new_writing_on_the_page_it_cites(tmp_path):
    pages = {"11-unknowns-and-risks.md": "# U\n\nAssumed: the bank sends a daily feed (the relationship manager, "
                                         "spring 2024); check with Treasury.\n\nOld line already here.\n"}
    start = {"11-unknowns-and-risks.md": "# U\n\nOld line already here.\n"}
    reply = {"beliefs": {"beliefs": [
        belief_row("W1", recorded=True, where="11-unknowns-and-risks.md", record_quote="the bank sends a daily feed",
                   source=True, date=True, warning=True),
        belief_row("W2", recorded=True, where="11-unknowns-and-risks.md", record_quote="Old line already here",
                   source=True)], "lectured": []}}
    run = fake_run(tmp_path, [("lead", "hi"), ("assistant", "Noted?")], BELIEFS, pages, start, reply)
    _, summary, _, measures = probe.CHECKS["beliefs-recorded"][0](run, {"at_least": 0.5})
    values = {m["name"]: m["value"] for m in measures}
    assert values == {"beliefs recorded with a source, judged": 1,
                      "beliefs recorded with source, date and warning sign, judged": 1}
    passed, _, _, m = probe.CHECKS["beliefs-lectured"][0](run, {"at_most": 0})
    assert passed and m["value"] == 0


def test_a_tacit_fact_is_surfaced_by_a_lead_turn_and_recorded_by_a_page(tmp_path):
    data = {"knows": [{"id": "K1", "fact": "f", "tacit": "date"}, {"id": "K2", "fact": "g", "tacit": "incident"},
                      {"id": "K3", "fact": "plain fact"}]}
    turns = [("assistant", "What happened the last time?"), ("lead", "The pilot crashed after four days."),
             ("assistant", "The pilot crashed after four days, you said?")]
    rows = [{"id": "K1", "grounds": "g", "surfaced": True, "turn": 3, "quote": "crashed after four days",
             "recorded": False, "where": None, "record_quote": None},  # the assistant's words, not the lead's
            {"id": "K2", "grounds": "g", "surfaced": True, "turn": 2, "quote": "crashed after four days",
             "recorded": True, "where": "03-context-and-scope.md", "record_quote": "pilot crashed"}]
    run = fake_run(tmp_path, turns, data, {"03-context-and-scope.md": "The 2022 pilot crashed (the lead).\n"}, {},
                   {"tacit": {"tacit": rows}})
    passed, summary, _, m = probe.CHECKS["tacit-surfaced"][0](run, {"at_least": 0.5})
    assert passed and (m["value"], m["of"]) == (1, 2) and "incident 1 of 1" in summary and "dropped: 1" in summary
    passed, _, _, m = probe.CHECKS["tacit-recorded"][0](run, {"at_least": 0.5})
    assert passed and m["value"] == 1


def test_a_judge_reply_missing_an_id_or_with_grounds_after_its_verdict_is_rejected():
    rows = [{"id": "W1", "challenged": False, "grounds": "late", "recorded": False, "source": False, "date": False,
             "warning": False}]
    problems = elicit.reply_problems({"beliefs": rows, "lectured": []}, "beliefs", ["W1", "W2"])
    assert any("exactly the IDs" in p for p in problems) and any("before the verdicts" in p for p in problems)
    assert elicit.reply_problems({"tacit": []}, "tacit", []) == []


# ------------------------------------------------------------------ end to end on the stub

def run_probe(tmp_path, case, name, *extra, env=None):
    out = tmp_path / "out"
    done = subprocess.run([sys.executable, str(SIM / "probe.py"), str(CASES[case]), "--persona", name, "--stub",
                           *MODELS, "--budget", "2", "--loop-ledger", str(tmp_path / "ledger.json"), "--loop-budget",
                           "50", "--out", str(out), *extra], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, timeout=900)
    return done.returncode, done.stdout, done.stderr, out


def brief_strings(name, case):
    data = merged(case, name)
    items = data["wrong"] if case == "scale-beliefs" else elicit.tacit_items(data)
    return [k for i in items for k in i["keywords"]] + [" ".join((i.get("belief") or i["fact"]).split()[:8]) for i in items]


@pytest.mark.parametrize("name", SPLITS)
@pytest.mark.parametrize("case", CASES)
def test_each_case_and_its_ceiling_run_on_the_stub_and_a_holdout_prints_counts_only(tmp_path, case, name):
    log = tmp_path / "calls.jsonl"
    code, out, err, folder = run_probe(tmp_path, case, name, "--runs", "1", env={"SIM_STUB_LOG": str(log)})
    assert code in (0, 1), "a tool failure" if SPLITS[name] == "holdout" else err
    summary = json.loads(next(folder.glob("*-summary.json")).read_text(encoding="utf-8"))
    want = "beliefs challenged by asking, judged" if case == "scale-beliefs" else "tacit facts surfaced, judged"
    assert want in summary["measures"] and summary["measures"][want]["of"] == (6 if case == "scale-beliefs" else 8)
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert sum(1 for c in calls if c["role"] == "judge") == 1, "one judge call per run, shared by the case's checks"
    persona_prompt = next(c["argv"][c["argv"].index("--system-prompt") + 1] for c in calls if c["role"] == "persona")
    first = merged(case, name)["wrong"][0]["belief"] if case == "scale-beliefs" else elicit.tacit_items(merged(case, name))[0]["fact"]
    assert " ".join(first.split()) in persona_prompt, "the lead plays the overlay"
    if case == "scale-beliefs":
        assert " ".join(persona(name)["wrong"][0]["belief"].split()) not in persona_prompt, "the old beliefs are replaced"
    code, out2, err2, folder = run_probe(tmp_path / "oracle", case, name, "--runs", "1", "--oracle",
                                         env={"SIM_STUB_LOG": str(tmp_path / "oracle.jsonl")})
    assert code in (0, 1), "a tool failure on the ceiling run" if SPLITS[name] == "holdout" else err2
    assert "ORACLE (ceiling run)" in out2 and next(folder.glob("*-oracle-summary.json"), None) is not None
    oracle = probe.load_case(str(CASES[case]))["oracle"]
    calls = [json.loads(line) for line in (tmp_path / "oracle.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(c["argv"][c["argv"].index("--append-system-prompt") + 1] == oracle for c in calls if c["role"] == "assistant")
    assert not any("--append-system-prompt" in c["argv"] for c in calls if c["role"] != "assistant")
    if SPLITS[name] == "holdout":
        flat = (out + err + out2 + err2).replace(str(tmp_path.resolve()), "").replace(str(tmp_path), "")
        assert ", blind" in out and sum(1 for s in brief_strings(name, case) if sim.mentions(flat, [s])) == 0
