"""The probe rebuild (tests/sim/probe_scale.py, probe_keep.py and the cases in tests/sim/scale/): scaled checks that
return a measure, the oracle ceiling run, the mean and spread over runs with the "real change" rule, the voice on
lead-facing turns, and the keep rule. Nothing here calls a model: every probe passes --stub.

Tests that touch a holdout persona assert on counts only, so a failing test never prints its brief."""
import importlib.util
import json
import os
import re
import subprocess
import sys
import types

import pytest
import yaml

from conftest import REPO

SIM = REPO / "tests" / "sim"
spec = importlib.util.spec_from_file_location("sim_probe_for_scale", SIM / "probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
sim, scale = probe.sim, probe.scale
keep_spec = importlib.util.spec_from_file_location("sim_probe_keep", SIM / "probe_keep.py")
keep = importlib.util.module_from_spec(keep_spec)
keep_spec.loader.exec_module(keep)

MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]


def spoken_run(tmp_path, turns, persona_data=None, decisions=(), tools=None):
    """A finished run held in memory: (speaker, text) or (speaker, text, session) turns, empty vault and snapshot."""
    entries = []
    for n, turn in enumerate(turns, 1):
        who, text, session = (turn + (1,))[:3]
        entries.append({"turn": n, "speaker": who, "text": text, "session": session,
                        "tool_calls": [{"name": "Read", "input": (tools or {}).get(n, "")}] if tools else []})
    for name in ("vault", "snap", "run"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    return types.SimpleNamespace(transcript=types.SimpleNamespace(spoken=lambda: entries, entries=entries),
                                 vault=tmp_path / "vault", snapshot=tmp_path / "snap", dir=tmp_path / "run",
                                 persona=persona_data or {}, decisions=list(decisions), notes=[])


# ------------------------------------------------------------------ the voice

def voice(tmp_path, turns, tools=None):
    run = spoken_run(tmp_path, turns, tools=tools)
    return {m["name"]: m["value"] for m in scale.voice_measures(run, probe.THIS, sim)}


def test_codes_and_ids_are_counted_by_the_lead_patterns_once_per_span(tmp_path):
    assert scale.lead_codes("UNK-004 blocks CAP-001.FR2; run vela check --gate grill") >= 4
    assert scale.lead_codes("Nothing here a lead can't read.") == 0
    found = voice(tmp_path, [("lead", "go"), ("assistant", "I filed UNK-004 for it."), ("assistant", "Who decides?")])
    assert found["voice: codes and IDs per turn"] == 0.5
    assert found["voice: score (turns with no code, of 100)"] == 50


def test_a_turn_that_settles_without_asking_is_told_not_asked(tmp_path):
    found = voice(tmp_path, [("assistant", "I've gone with the line manager approving. Done."),
                             ("assistant", "I'd go with the line manager. Does that work for you?")])
    assert found["voice: turns that told rather than asked"] == 1


def test_more_than_four_things_in_one_turn_is_counted(tmp_path):
    five = "\n".join(f"- point {n}" for n in range(5))
    table = "| a | b |\n|---|---|\n" + "\n".join(f"| {n} | x |" for n in range(5))
    found = voice(tmp_path, [("assistant", five), ("assistant", table), ("assistant", "- one\n- two\n  - nested")])
    assert found["voice: turns offering more than 4 things"] == 2


def test_the_voice_loading_step_counts_only_before_the_first_question(tmp_path):
    read = "plugin/references/CONVERSATION-VOICE.md"
    ran = voice(tmp_path / "a", [("assistant", "Reading.", 1), ("assistant", "What first?", 1), ("assistant", "Hi?", 2)],
                tools={1: read, 3: read})
    assert ran["voice: voice-loading step ran (share of sessions)"] == 1.0
    late = voice(tmp_path / "b", [("assistant", "What first?"), ("assistant", "ok")], tools={2: read})
    assert late["voice: voice-loading step ran (share of sessions)"] == 0.0


# ------------------------------------------------------------------ the scaled checks

def test_gaps_raised_returns_a_measure_of_every_gap(tmp_path):
    data = {"unaware": [{"id": f"U{n}", "category": "fact", "keywords": [f"thing{n}"]} for n in range(1, 9)]}
    run = spoken_run(tmp_path, [("lead", "thing1 worries me"),
                                ("assistant", "What does thing1 mean for thing2? And does thing3 clash with it?\n\n"
                                              "- thing4 is in the memo.")], data)
    passed, summary, _, m = probe.CHECKS["gaps-raised"][0](run, {"at_least": 0.25})
    assert passed and summary.startswith("gaps the lead hadn't noticed, raised first: 2 of 8"), summary
    # thing1 the lead said first; thing4 was only read back (listed), so neither counts
    assert m == {"name": "gaps raised first", "value": 2, "of": 8, "better": "higher"}


def test_positions_heard_only_when_asked_are_facts_and_still_count(tmp_path):
    data = {"knows": [{"id": "K30", "category": "stakeholder-conflict", "who": "Treasurer", "fact": "x",
                       "keywords": ["once a month"]},
                      {"id": "K31", "category": "stakeholder-conflict", "who": "HR Director", "fact": "y",
                       "keywords": ["out of pocket"]}]}
    run = spoken_run(tmp_path, [("assistant", "The Treasurer wants once a month, while the HR Director rules it out.")],
                     data)
    (run.vault / "11-unknowns-and-risks.md").write_text("### UNK-001 Pay-back timing\n\nThe Treasurer wants once a month.\n",
                                                        encoding="utf-8")
    passed, summary, _, m = probe.CHECKS["positions-surfaced"][0](run, {"at_least": 0.5})
    assert passed and m["value"] == 1 and m["of"] == 2 and "disagreement named for 2" in summary


def test_ready_decided_reads_each_items_state_and_fails_on_a_blocked_one(tmp_path):
    page = ("---\nid: CAP-001\ntype: capability\n---\n\n## Functional requirements\n\n"
            "### CAP-001.FR1 One\n\n- **State:** decided\n\n### CAP-001.FR2 Two\n\n- **State:** assumption\n\n"
            "### CAP-001.FR3 Three\n\n- **State:** decided\n")
    data = {"decisions": [{"id": "D1", "item": "CAP-001.FR1"}, {"id": "D2", "item": "CAP-001.FR2"},
                          {"id": "D3", "item": "CAP-001.FR3", "blocked": True}]}
    pinned = [{"turn": 4, "file": "capabilities/CAP-001.md", "line": "- **State:** decided", "with_yes": True}]
    run = spoken_run(tmp_path, [], data, decisions=pinned)
    (run.vault / "capabilities").mkdir()
    (run.vault / "capabilities" / "CAP-001.md").write_text(page, encoding="utf-8")
    passed, summary, detail, m = probe.CHECKS["ready-decided"][0](run, {"at_least": 0.5})
    assert m["value"] == 1 and m["of"] == 2
    assert not passed and "blocked items decided: 1 of 1" in summary
    assert scale.item_state(run.vault, "CAP-001.FR2", sim) == "assumption"


def test_ready_decided_counts_no_more_decisions_than_the_yeses_on_that_page(tmp_path):
    page = "---\nid: CAP-001\n---\n\n### CAP-001.FR1 A\n\n- **State:** decided\n\n### CAP-001.FR2 B\n\n- **State:** decided\n"
    data = {"decisions": [{"id": "D1", "item": "CAP-001.FR1"}, {"id": "D2", "item": "CAP-001.FR2"}]}
    pinned = [{"turn": 4, "file": "c.md", "line": "x", "with_yes": True}, {"turn": 6, "file": "c.md", "line": "x",
                                                                            "with_yes": False}]
    run = spoken_run(tmp_path, [], data, decisions=pinned)
    (run.vault / "c.md").write_text(page, encoding="utf-8")
    assert probe.CHECKS["ready-decided"][0](run, {"at_least": 0.5})[3]["value"] == 1


def test_unsure_proposed_needs_the_question_named_with_a_proposal_and_asked(tmp_path):
    data = {"handle": "@sim-lead", "knows": [
        {"id": "K50", "fact": "a", "keywords": ["which currency"], "open_question": True},
        {"id": "K51", "fact": "b", "keywords": ["cost centre"], "open_question": True},
        {"id": "K52", "fact": "c", "keywords": ["not open"]}]}
    turns = [("assistant", "Who should own which currency a claim is paid in?"), ("lead", "Honestly not sure."),
             ("assistant", "On which currency: I'd suggest the Financial Controller as owner, by 30 October. Does that work?"),
             ("lead", "Yes, the Financial Controller."), ("assistant", "And the cost centre match is open.")]
    run = spoken_run(tmp_path, turns, data)
    passed, summary, _, m = probe.CHECKS["unsure-proposed"][0](run, {"at_least": 0.5})
    assert passed and m["value"] == 1 and m["of"] == 2
    assert "owners or dates written unconfirmed: 0" in summary


# ------------------------------------------------------------------ mean, spread and the rule

def records(values, name="gaps raised first", better="higher"):
    return [{"measures": [scale.measure(name, v, 8, better)]} for v in values]


def test_summary_gives_mean_and_sample_spread_and_skips_failed_runs():
    got = scale.summarize(records([2, 4, 3]) + [{"failure": "claude", "measures": [scale.measure("gaps raised first", 9, 8)]}])
    row = got["gaps raised first"]
    assert row["values"] == [2, 4, 3] and row["mean"] == 3 and row["spread"] == 1.0 and row["of"] == 8
    assert scale.summarize(records([5]))["gaps raised first"]["spread"] == 0.0
    text = "\n".join(scale.summary_lines(got))
    assert "gaps raised first: 3 of 8 ± 1" in text and "more than the larger of the two spreads" in text


def test_a_change_is_real_only_beyond_the_larger_spread_and_direction_matters():
    before, small, big = (scale.summarize(records(v)) for v in ([2, 3, 2, 3, 2], [4, 5, 4, 5, 4], [1, 6, 2, 7, 4]))
    assert scale.compare(before, small)[0]["verdict"] == "gain"
    assert scale.compare(before, big)[0]["verdict"] == "noise", "the after spread is wider than the move"
    codes_b, codes_a = (scale.summarize(records(v, "voice: codes and IDs per turn", "lower")) for v in ([0, 0, 0], [2, 3, 2]))
    row = scale.compare(codes_b, codes_a)[0]
    assert row["verdict"] == "loss" and row["voice"]


def summary_file(tmp_path, name, persona, rows, oracle=False):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"case": "scale-gaps", "persona": persona, "oracle": oracle, "measures": rows}),
                    encoding="utf-8")
    return str(path)


def merged(*parts):
    out = {}
    for part in parts:
        out.update(part)
    return out


def test_the_keep_rule_reverts_a_gain_that_hurts_the_voice(tmp_path):
    acc = lambda v: scale.summarize(records(v))  # noqa: E731
    voice_rows = lambda v: scale.summarize(records(v, "voice: codes and IDs per turn", "lower"))  # noqa: E731
    args = ["--dev-before", summary_file(tmp_path, "db", "heron-claims", merged(acc([1, 2, 1]), voice_rows([0, 0, 0]))),
            "--dev-after", summary_file(tmp_path, "da", "heron-claims", merged(acc([5, 6, 5]), voice_rows([2, 3, 2]))),
            "--holdout-before", summary_file(tmp_path, "hb", "holdout-nursing", merged(acc([2, 2, 3]), voice_rows([0, 0, 0]))),
            "--holdout-after", summary_file(tmp_path, "ha", "holdout-nursing", merged(acc([2, 3, 2]), voice_rows([0, 0, 0]))),
            "--skip-tests"]
    assert keep.main(args) == 1
    args[3] = summary_file(tmp_path, "da2", "heron-claims", merged(acc([5, 6, 5]), voice_rows([0, 0, 0])))
    assert keep.main(args) == 0
    args[1] = summary_file(tmp_path, "or", "heron-claims", merged(acc([1, 2, 1])), oracle=True)
    assert keep.main(args) == 2, "a ceiling run is never a before or an after"


def test_the_keep_rule_refuses_a_holdout_in_the_dev_pair(tmp_path):
    rows = scale.summarize(records([1, 2]))
    args = ["--dev-before", summary_file(tmp_path, "a", "holdout-nursing", rows),
            "--dev-after", summary_file(tmp_path, "b", "holdout-nursing", rows),
            "--holdout-before", summary_file(tmp_path, "c", "holdout-nursing", rows),
            "--holdout-after", summary_file(tmp_path, "d", "holdout-nursing", rows), "--skip-tests"]
    assert keep.main(args) == 2


def test_the_gate_tests_are_the_voice_loading_leak_and_conversation_voice_tests():
    assert set(keep.GATE_TESTS) >= {"tests/test_conversation_voice.py", "tests/test_sim_seal.py"}
    for path in keep.GATE_TESTS:
        assert (REPO / path).is_file(), path


# ------------------------------------------------------------------ the oracle, end to end on the stub

def run_probe(tmp_path, case, name, *extra, env=None):
    out = tmp_path / "out"
    done = subprocess.run([sys.executable, str(SIM / "probe.py"), case, "--persona", name, "--stub", *MODELS,
                           "--budget", "2", "--loop-ledger", str(tmp_path / "ledger.json"), "--loop-budget", "50",
                           "--out", str(out), *extra], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, timeout=900)
    return done.returncode, done.stdout, done.stderr, out


def test_the_oracle_reaches_only_the_assistant_and_the_summary_is_written(tmp_path):
    log = tmp_path / "calls.jsonl"
    case = probe.load_case("scale-gaps")
    code, out, err, folder = run_probe(tmp_path, "scale-gaps", "heron-claims", "--runs", "1", "--oracle",
                                       env={"SIM_STUB_LOG": str(log)})
    assert code in (0, 1), err
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assistant = [c for c in calls if c["role"] == "assistant"]
    assert assistant and all(c["argv"][c["argv"].index("--append-system-prompt") + 1] == case["oracle"] for c in assistant)
    assert not any("--append-system-prompt" in c["argv"] for c in calls if c["role"] != "assistant")
    assert "ORACLE (ceiling run)" in out and "reachable ceiling" in out
    summary = json.loads(next(folder.glob("*-oracle-summary.json")).read_text())
    assert summary["oracle"] is True and "gaps raised first" in summary["measures"]
    assert all("-oracle-" in name for name in summary["folders"]), "a ceiling run beside its baseline never collides"
    assert "voice: codes and IDs per turn" in summary["measures"]
    ledger = json.loads((tmp_path / "ledger.json").read_text())
    assert ledger["invocations"][0]["oracle"] is True and ledger["invocations"][0]["summary"]


def test_a_case_without_an_oracle_has_no_ceiling_run(tmp_path):
    code, _, err, _ = run_probe(tmp_path, "unsure-owner", "heron-desk", "--runs", "1", "--oracle")
    assert code == 2 and "has no oracle" in err


def test_five_runs_by_default(tmp_path):
    code, out, err, folder = run_probe(tmp_path, "unsure-owner", "heron-desk")
    assert code in (0, 1), err
    assert "5 run(s)" in out and "summary over 5 run(s)" in out
    assert len([p for p in folder.iterdir() if p.is_dir()]) == 5


# ------------------------------------------------------------------ the material: personas, snapshots, cases

SCALE = SIM / "scale"
SCALE_SNAPSHOTS = sorted(p for p in (SCALE / "snapshots").glob("*/*") if p.is_dir())
SCALE_CASES = sorted((SCALE / "cases").glob("*.yaml"))
SPLITS = {"heron-claims": "dev", "holdout-nursing": "holdout"}


def persona(name):
    return yaml.safe_load((SIM / "personas" / f"{name}.yaml").read_text(encoding="utf-8"))


def test_the_scale_snapshots_are_the_ones_the_cases_name():
    named = set()
    for path in SCALE_CASES:
        case = probe.load_case(str(path))
        assert set(case["snapshot"]) == set(SPLITS), path.name
        named |= {f"{p}/{s}" for p, s in case["snapshot"].items()}
    assert named == {p.relative_to(SCALE / "snapshots").as_posix() for p in SCALE_SNAPSHOTS}
    assert {p.stem for p in SCALE_CASES} == {"scale-gaps", "scale-conflicts", "scale-unsure", "scale-decisions"}


@pytest.mark.parametrize("snapshot", SCALE_SNAPSHOTS, ids=lambda p: p.relative_to(SCALE / "snapshots").as_posix())
def test_every_scale_snapshot_is_a_clean_vault_with_its_personas_inbox(snapshot):
    assert not (snapshot / ".claude" / "skills").exists() and not (snapshot / ".git").exists()
    assert len(probe.inbox_problems(snapshot, persona(snapshot.parent.name))) == 0
    check = subprocess.run([sys.executable, str(sim.VELA), "check", "--vault", str(snapshot)],
                           capture_output=True, text=True, timeout=120)
    assert check.returncode == 0 and re.search(r"vela check: 0 errors,", check.stdout) is not None


def test_the_scale_inboxes_are_in_git_although_a_vault_ignores_them():
    tracked = subprocess.run(["git", "ls-files", "tests/sim/scale/snapshots"], cwd=REPO, capture_output=True, text=True,
                             timeout=60).stdout.split()
    if not tracked:
        pytest.skip("the scale snapshots are not committed yet")
    for snapshot in SCALE_SNAPSHOTS:
        for doc in (snapshot / ".inbox").iterdir():
            assert doc.relative_to(REPO).as_posix() in tracked, doc.name


def test_the_splits_and_the_scales_counts_only():
    for name, split in SPLITS.items():
        data = persona(name)
        assert probe.seal.split_of(data) == split and sim.persona_problems(data) == []
        positions = probe.brief_items(data, ["stakeholder-conflict"])
        decisions = [d for d in data["decisions"] if d.get("item")]
        assert len(data["unaware"]) == 8, name
        assert len(positions) == 8 and all(p.get("who") for p in positions), name
        assert sum(1 for k in data["knows"] if k.get("open_question")) == 6, name
        assert len(decisions) == 11 and sum(1 for d in decisions if d.get("blocked")) == 3, name
        assert all(d.get("refuse_until") for d in decisions if d.get("blocked")), "a blocked item the lead would decide"
        assert not data.get("conflicts"), "a C item is relayed on any who-wants-what question, so positions are facts"


def test_a_position_is_heard_only_when_asked_and_no_brief_hands_a_key_over():
    for name in SPLITS:
        data = persona(name)
        docs = " ".join(d["text"] for d in data["docs"])
        positions = probe.brief_items(data, ["stakeholder-conflict"])
        others = " ".join(k["fact"] for k in data["knows"] if k.get("category") != "stakeholder-conflict")
        lead_says = " ".join(k["fact"] for k in data["knows"]) + " " + data["opening"]
        assert all(p["fact"].startswith("Only if you are asked") for p in positions), name
        assert sum(1 for p in positions if sim.mentions(docs, p["keywords"]) or sim.mentions(others, p["keywords"])) == 0
        assert sum(1 for u in data["unaware"] if sim.mentions(lead_says, u["keywords"])) == 0
        assert sum(1 for u in data["unaware"] if sim.mentions(docs, u["keywords"])) == 8, "each gap rests on the documents"


def test_the_grill_ready_vaults_hold_exactly_the_ready_and_blocked_items_the_persona_says():
    for name in SPLITS:
        decisions = [d for d in persona(name)["decisions"] if d.get("item")]
        vault = SCALE / "snapshots" / name / "grill-ready"
        argv = [sys.executable, str(sim.VELA), "check", "--gate", "grill", "--vault", str(vault), "--json"]
        for d in decisions:
            argv += ["--item", d["item"]]
        found = json.loads(subprocess.run(argv, capture_output=True, text=True, timeout=120).stdout)
        ready = {i["id"] for i in found["items"] if i["ready"]}
        want = {d["item"] for d in decisions if not d.get("blocked")}
        assert len(ready ^ want) == 0, name
        assert sum(1 for d in decisions if scale.item_state(vault, d["item"], sim) == "assumption") == 11


def test_no_oracle_names_anything_from_a_brief():
    """An oracle is a plain instruction of the measured behavior, the same for every persona: a key term in it would
    make the ceiling a lookup of the answer key."""
    terms = probe.seal.persona_terms()
    for path in SCALE_CASES:
        oracle = probe.load_case(str(path))["oracle"]
        assert len(probe.seal.leaks_in(oracle, terms)) == 0, path.name


def brief_strings(data):
    strings = [" ".join(data["opening"].split())]
    for kind in sim.ID_KINDS:
        for item in data.get(kind) or []:
            strings += list(item["keywords"])
            for field in sim.ITEM_FIELDS[kind] + ("who",):
                value = item.get(field)
                values = [str(v) for v in value] if isinstance(value, list) else [str(value)] if value else []
                strings += [v for v in values if len(v.split()) >= 3]
    return strings


@pytest.mark.parametrize("case", ["scale-gaps", "scale-conflicts", "scale-unsure", "scale-decisions"])
def test_every_scale_case_runs_on_the_stub_and_the_holdout_prints_counts_only(tmp_path, case):
    data = persona("holdout-nursing")
    code, out, err, folder = run_probe(tmp_path, case, "holdout-nursing", "--runs", "2")
    assert code in (0, 1), "a tool failure"
    flat = (out + err).replace(str(tmp_path.resolve()), "").replace(str(tmp_path), "")
    assert sum(1 for s in brief_strings(data) if sim.mentions(flat, [s])) == 0
    assert ", blind." in out and "summary over 2 run(s)" in out and "voice: codes and IDs per turn" in out
    summary = json.loads(next(folder.glob("*-summary.json")).read_text())
    assert summary["blind"] is True and len(summary["measures"]) >= 6
    dev_code, _, dev_err, _ = run_probe(tmp_path / "dev", case, "heron-claims", "--runs", "1")
    assert dev_code in (0, 1), dev_err
