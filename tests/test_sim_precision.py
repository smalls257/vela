"""tests/sim/precision.py: the precision pass that sits beside recall in compare_runs.py's verdict.

The Paper Tiger it guards against: recall rising because a run wrote more, with the extra padding, repeats or facts
nobody gave. These tests pin how items are found, how the sample is drawn (stratified, seeded, the same every time),
and that a classification the driver can't check against its citation reads unsupported, never backed. The judge is
the stub (tests/sim/stub/claude); nothing calls a model.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

from conftest import REPO

SIM = REPO / "tests" / "sim"
MODELS = ["--model", "test-model", "--persona-model", "test-persona", "--judge-model", "test-judge"]


def load(name):
    key = f"sim_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, SIM / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        spec.loader.exec_module(module)
    return sys.modules[key]


precision = load("precision")
sim = load("run")

UNKNOWNS = ("---\ntype: unknowns\n---\n# Unknowns\n\n### UNK-001 Privacy sign-off\n\nWho signs off the privacy notice "
            "before the pilot starts?\n\n- **State:** open\n\n### UNK-002 Pilot size\n\nThe pilot covers forty desks in "
            "the Leeds office from January.\n\n- **State:** open\n\n### UNK-003 Pilot desks\n\nThe pilot covers forty "
            "desks in the Leeds office, from January on.\n\n- **State:** open\n")
GOALS = ("---\ntype: goals\n---\n# Goals\n\nPilot the desk helper at forty desks in the Leeds office this year.\n\n"
         "- Every person in the pilot sees their own morning note and nobody else's.\n- Short.\n")


def write(vault, pages):
    for rel, text in pages.items():
        (vault / rel).parent.mkdir(parents=True, exist_ok=True)
        (vault / rel).write_text(text, encoding="utf-8")


def test_items_are_sections_or_paragraphs_and_never_session_records_team_docs_or_template_text(tmp_path):
    template = tmp_path / "template"
    write(template, {"01-goals.md": "# Goals\n\n- Every person in the pilot sees their own morning note and nobody else's.\n"})
    write(tmp_path / "v", {"11-unknowns-and-risks.md": UNKNOWNS, "01-goals.md": GOALS,
                           "sessions/2026-10-15-s.md": "---\ntype: session\n---\n# S\n\nThe lead said a great many words here. ^c01\n",
                           "docs/tech-design/x.md": "# Design\n\nThe design says a great many words about the agent.\n"})
    units = precision.units_of(tmp_path / "v", template)
    assert [(u.path, u.key) for u in units] == [("01-goals.md", "part 1"), ("11-unknowns-and-risks.md", "UNK-001"),
                                                ("11-unknowns-and-risks.md", "UNK-002"),
                                                ("11-unknowns-and-risks.md", "UNK-003")]
    assert {u.page_type for u in units} == {"goals", "unknowns"}


def test_the_sample_is_stratified_by_page_type_seeded_and_the_same_every_time():
    units = [precision.Unit(f"p{t}.md", t, f"part {i}", f"item {t} {i} with enough words to count here")
             for t, n in (("a", 40), ("b", 8), ("c", 1)) for i in range(n)]
    one, two = precision.stratified_sample(units, 30, 7), precision.stratified_sample(units, 30, 7)
    assert [u.key for _, u in one] == [u.key for _, u in two], "a fixed seed draws the same items"
    counts = {t: sum(1 for _, u in one if u.page_type == t) for t in "abc"}
    assert counts == {"a": 24, "b": 5, "c": 1} and sum(counts.values()) == 30, "proportional, every type at least one"
    assert [label for label, _ in one] == [f"P{i}" for i in range(1, 31)]
    assert [u.key for _, u in precision.stratified_sample(units, 30, 8)] != [u.key for _, u in one]
    assert len(precision.stratified_sample(units[:5], 30, 7)) == 5, "a small vault is sampled whole"


def test_each_item_is_shown_with_its_nearest_neighbours_for_the_duplicate_check(tmp_path):
    write(tmp_path, {"11-unknowns-and-risks.md": UNKNOWNS})
    units = precision.units_of(tmp_path, tmp_path / "no-template")
    near = precision.neighbours(units[1], units)
    assert [u.key for u in near] == ["UNK-003"], "the one item that says the same thing, not the unrelated one"


def test_a_citation_the_driver_cannot_find_reads_unsupported_and_is_listed():
    unit = precision.Unit("01-goals.md", "goals", "part 1", "Pilot the helper at forty desks, if the lead agrees?")
    sample = [(f"P{i}", unit) for i in range(1, 6)]
    labels = {f"P{i}": {f"P{i}.N1"} for i in range(1, 6)}
    docs = [{"name": "cio-note.md", "text": "The pilot is 40 desks in Leeds."}]
    spoken = [{"turn": 3, "speaker": "lead", "text": "Forty desks, yes."}, {"turn": 4, "speaker": "assistant", "text": "Ok."}]
    reply = {"items": [
        {"id": "P1", "class": "backed", "basis": "source", "where": "cio-note.md", "quote": "40 desks in Leeds"},
        {"id": "P2", "class": "backed", "basis": "lead", "turn": 4, "quote": "Ok."},
        {"id": "P3", "class": "backed", "basis": "question", "quote": "if the lead agrees"},
        {"id": "P4", "class": "duplicate", "duplicate_of": "P1.N1"},
        {"id": "P5", "class": "padding"}]}
    rows, dropped = precision.enforce(reply, sample, labels, docs, spoken)
    assert [r["class"] for r in rows] == ["backed", "unsupported", "backed", "unsupported", "padding"]
    assert dropped == ["P2 (backed): turn 4 is not a lead turn", "P4 (duplicate): duplicate_of 'P1.N1' is not listed under it"]
    summary = precision.summarize(rows, dropped, 9)
    assert summary["precision"] == 0.4 and summary["counts"]["unsupported"] == 2, "unsupported and padding count against"


def test_a_reply_that_is_bad_twice_is_a_failure_and_a_refusal_is_not_scored():
    replies = iter([{"is_error": False, "result": "not json"}, {"is_error": False, "result": '{"items": []}'}])
    try:
        precision.ask(lambda text: next(replies), "x", ["P1"])
    except precision.JudgeFailure as exc:
        assert "bad twice" in str(exc) and "must list P1" in str(exc)
    else:
        raise AssertionError("bad JSON twice must fail")
    assert precision.ask(lambda text: {"stop_reason": "refusal"}, "x", ["P1"]) == (None, "the judge model refused the precision call")


def stub_run(tmp_path):
    """A stub run of the smoke script on heron-desk whose assistant writes two pages the template doesn't have (the
    stub creates a file only when it does not exist yet)."""
    env = {**os.environ, "SIM_STUB_WRITE": json.dumps({"pilot-unknowns.md": UNKNOWNS, "pilot-goals.md": GOALS})}
    done = subprocess.run([sys.executable, str(SIM / "run.py"), "heron-desk", "--stub", *MODELS, "--budget", "5",
                           "--arms", "vela", "--script", "smoke", "--out", str(tmp_path / "out")],
                          capture_output=True, text=True, env=env, timeout=600)
    assert done.returncode == 0, done.stderr[-2000:]
    return next((tmp_path / "out").iterdir())


def test_the_precision_call_goes_through_the_judge_machinery_on_the_arms_ledger(tmp_path):
    run_dir = stub_run(tmp_path)
    args = sim.parse_args(["--rejudge", str(run_dir), "--stub", "--judge-model", "j", "--budget", "1"])
    summary = sim.load_run(run_dir)
    persona, _, _ = sim.brief_of_run(summary, sim.load_yaml(sim.resolve("heron-desk", "personas")))
    arm = sim.Arm.reopen("vela", run_dir, args, persona, 1.0, summary["per_arm"]["vela"])
    record = sim.judge_precision(arm, arm.vault, "working tree", seeds=(precision.SEED,), quick=True)
    assert record["sampled"] == record["population"] >= 4
    classes = [r["class"] for r in record["items"]]
    assert classes[0] == "padding" and classes[-1] == "unsupported", "the stub's padding and its dropped citation"
    assert record["dropped"] == [f"P{len(classes)} (backed): turn 999 is not a lead turn"]
    assert [c["category"] for c in arm.judge_calls] == ["precision"] and arm.ledger.spent > 0
    assert any(p.name.endswith("-judge-precision.txt") for p in (arm.dir / "raw").iterdir())


def test_the_command_line_pass_writes_precision_json_and_compare_reads_it(tmp_path):
    run_dir = stub_run(tmp_path)
    vault = run_dir / "vela" / "vault"
    subprocess.run(["git", "remote", "remove", "origin"], cwd=vault, check=True, capture_output=True)
    shutil.rmtree(run_dir / "vela" / "origin.git")  # so the written pages, never pushed, are the final vault
    done = subprocess.run([sys.executable, str(SIM / "precision.py"), str(run_dir), "--stub", "--judge-model", "j",
                           "--budget", "1"], capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("Precision ") and "±" in done.stdout and "4 passes" in done.stdout
    assert "citations failed and read unsupported" in done.stdout
    record = json.loads((run_dir / "vela" / "precision.json").read_text(encoding="utf-8"))
    assert record["vault"] == "working tree on main" and record["judge_model"] == "j"
    assert record["seed"] == [101, 202, 303, 404] and len(record["passes"]) == 4 and "plus_minus" in record
    compare = load("compare_runs")
    run = compare.Run("x", run_dir, "vela", REPO)
    assert compare.precision_section(run)["precision"] == record["precision"]


# ---------------------------------------------------------------- only what the model wrote is sampled

PROSE = "The pilot covers forty desks in the Leeds office from the first of January onward."
EPIC = ("---\nid: EPC-001\ntype: epic\n---\n# EPC-001 Consent\n\nHeron reads nothing until a person says yes, and stops "
        "when they withdraw.\n\n## Done when\n\n### Nothing is read before a yes\n\nA person who has not said yes has "
        "nothing read from their calendar.\n\n- Trace: CAP-025.FR2, CON-021, CON-022  \u00b7  AC1  \u00b7  [testing]\n\n"
        "## History\n\n- **Decision:** [[2026-10-19-desk-agent-team-epics]]\n- **Why:** \"I need consent first.\" "
        "[[2026-10-19-desk-agent-team-epics#^c01]]\n")
HANDOFF = ("---\ntype: handoff\n---\n# Handoff record: Desktop agent\n\nMade by vela handoff; do not edit it by hand "
           "ever, since the Hash column is a fingerprint.\n\n| ID | Kind | Page | State | Hash |\n|---|---|---|---|---|\n"
           "| APP-desktop-agent | app | 05-building-blocks/desktop-agent.md | assumption | 413155ca4d62 |\n\n"
           "- Consent check (CON-021) is not decided yet: nobody has said yes to it.\n")
INDEX = ("---\ntype: index\n---\n# Epics\n\nOne page per epic, named `EPC-nnn-<slug>.md`.\n\n## Traceability\n\n"
         "<!-- generated:traceability sha=1: do not edit, run vela render -->\n| Item | What is missing |\n|---|---|\n"
         "| Get a prep note before a meeting | No epic delivers it, so nobody is planned to build it at all. |\n"
         "<!-- /generated:traceability -->\n\n" + PROSE + "\n")


def texts(units):
    return " ".join(u.text for u in units)


def test_handoff_pages_are_never_sampled(tmp_path):
    write(tmp_path, {"handoffs/APP-desktop-agent.md": HANDOFF, "01-goals.md": GOALS})
    units = precision.units_of(tmp_path, tmp_path / "no-template")
    assert {u.path for u in units} == {"01-goals.md"}


def test_epic_trace_lines_and_decision_links_are_left_out_but_the_models_acceptance_prose_and_why_stay(tmp_path):
    write(tmp_path, {"13-epics/EPC-001-consent.md": EPIC})
    found = texts(precision.units_of(tmp_path, tmp_path / "no-template"))
    assert "Trace:" not in found and "**Decision:**" not in found
    assert "nothing read from their calendar" in found and "I need consent first" in found


def test_trace_lines_nested_under_a_requirement_on_a_capability_page_are_left_out_too(tmp_path):
    page = ("---\ntype: capability\n---\n# CAP-022 Morning note\n\n## Requirements\n\n- A person sees only their own note "
            "each morning, and nobody else's.\n  - Trace: UNK-063, UNK-086\n")
    write(tmp_path, {"capabilities/CAP-022.md": page})
    found = texts(precision.units_of(tmp_path, tmp_path / "no-template", tmp_path / "no-catalog"))
    assert "Trace:" not in found and "only their own note" in found


def test_template_sentences_current_and_retired_are_left_out_even_when_the_vault_template_lacks_them(tmp_path):
    catalog = tmp_path / "catalog"
    write(catalog, {"template-lines.txt": "What this initiative cannot change.\n",
                    "template-lines-retired.txt": "One page per epic, named `EPC-nnn-<slug>.md`.\n"})
    write(tmp_path / "v", {"13-epics/00-index.md": INDEX,
                           "02-constraints.md": "---\ntype: constraints\n---\n# Constraints\n\nWhat this initiative cannot change.\n\n" + PROSE + "\n"})
    found = texts(precision.units_of(tmp_path / "v", tmp_path / "no-template", catalog))
    assert "One page per epic" not in found and "cannot change" not in found
    assert found.count(PROSE) == 2, "the model's own sentence next to them stays"


def test_cli_rendered_generated_blocks_are_left_out_and_the_models_prose_beside_them_stays(tmp_path):
    write(tmp_path, {"13-epics/00-index.md": INDEX})
    found = texts(precision.units_of(tmp_path, tmp_path / "no-template", tmp_path / "no-catalog"))
    assert "nobody is planned to build" not in found and "Gaps" not in found and PROSE in found


def test_model_written_table_cells_prose_and_captures_stay_in(tmp_path):
    page = ("---\ntype: concern\n---\n# Testing\n\n| App | State | Why |\n|---|---|---|\n"
            "| Desktop agent | unexamined | Nobody has looked at this yet, so there is no test plan at all. |\n\n"
            "Strategy: prove one Zoom client call on a single pilot laptop before any wider rollout begins.\n")
    write(tmp_path, {"08-concerns/concern-testing.md": page})
    found = texts(precision.units_of(tmp_path, tmp_path / "no-template", tmp_path / "no-catalog"))
    assert "Nobody has looked at this yet" in found and "prove one Zoom client call" in found


def test_the_real_catalog_lines_are_loaded_and_the_excluded_kinds_are_named():
    lines = precision.template_lines()
    assert precision.normalize("Flow pages live in `flows/` and app runtime pages in `apps/`.") in lines
    assert precision.normalize("One page per decision, named `ADR-nnnn-<slug>.md`.") in lines or len(lines) > 10
    assert "handoff page" in precision.GENERATED_KINDS


def record_of(seed, against, n=30):
    rows = [{"class": "padding" if i < against else "backed", "page_type": "goals"} for i in range(n)]
    return {**precision.summarize(rows, [], 50, cuts=[], seed=seed, vault="v"), "size": n}


def test_the_pooled_score_adds_the_items_and_reports_the_seed_spread():
    pooled = precision.pool([record_of(101, 3), record_of(202, 6), record_of(303, 9), record_of(404, 6)],
                            (101, 202, 303, 404))
    assert pooled["sampled"] == 120 and pooled["counts"]["padding"] == 24 and pooled["precision"] == 0.8
    assert [p["precision"] for p in pooled["passes"]] == [0.9, 0.8, 0.7, 0.8]
    assert pooled["plus_minus"] == 0.1 and pooled["precision_range"] == [0.7, 0.9]
    assert pooled["seed"] == [101, 202, 303, 404]


def test_a_pooled_pass_with_one_seed_not_scored_is_missing_not_a_smaller_score(tmp_path):
    write(tmp_path, {"01-goals.md": GOALS})
    refusals = lambda text: {"stop_reason": "refusal"}
    record = precision.score_pooled(tmp_path, [], [], refusals, 30, (1, 2))
    assert "missing" in record and "seed 1" in record["missing"] and "precision" not in record
