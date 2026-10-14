"""`vela epics frontier` and `vela epics lint [--fix-shape]` (overhaul Task 21e).

The epics skill used to read the traceability block, check the tracer and run a three-step boundary test on every
criterion by hand. Each is countable, so a command reports it and the skill keeps the judgment (the cuts, the rewrite
at the boundary). These tests hold the counts to the vault and the AC numbers to the page: other pages cite
`EPC-nnn.ACn`, so a shape rewrite that renumbers a criterion silently repoints every citation (Anchor).
"""
import json
import shutil

from conftest import REPO, run
from vela import criteria, parse, say

HERON = REPO / "tests" / "fixtures" / "team-skills" / "heron"
HERON_DESK = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"
NUMBERED = REPO / "tests" / "fixtures" / "readable" / "EPC-001-calendar.md"
TRACER = ("- **Tracer:** [[FLO-002-get-morning-digest|FLO-002]], a person switches Heron on and gets the 7:30 digest "
          "from calendar entries only\n")


def copy_of(tmp_path, source=HERON):
    vault = tmp_path / "vault"
    shutil.copytree(source, vault, ignore=shutil.ignore_patterns(".vela", ".planner"))
    return vault


def epic(vault, number, criteria_md, apps="[APP-desktop-agent]", flows="[FLO-001]"):
    path = vault / "13-epics" / f"EPC-{number:03d}-lint-me.md"
    path.write_text(f"""---
id: EPC-{number:03d}
type: epic
title: Lint me
state: draft
owner: "@sim-lead"
authored: mixed
apps: {apps}
delivers: [CAP-005]
consumes: [CON-003]
flows: {flows}
depends_on: []
---

# Lint me

Stub.

**Owning team:** @sim-lead

## Done when

{criteria_md}
## Out of scope

Nothing.
""", encoding="utf-8")
    return f"EPC-{number:03d}"


def headed(n, heading, sentence, trace):
    return f"### {heading}\n\n{sentence}\n\n- Trace: {trace}  ·  AC{n}\n\n"


def lint(vault, *argv):
    code, out = run("epics", "lint", "--vault", str(vault), "--json", *argv)
    return code, json.loads(out)


# ------------------------------------------------------------------------------------------------ lint

def test_lint_flags_component_name_in_criterion(tmp_path):
    vault = copy_of(tmp_path)
    ident = epic(vault, 90, headed(1, "Reads only after consent", "The Source reader reads nothing until the consent "
                                   "check says yes.", "CAP-005.FR1, CON-003")
                 + headed(2, "Reads only after consent, said at the boundary", "Nothing is asked of Microsoft until "
                          "the consent check says yes.", "CAP-005.FR1, CON-003")
                 + headed(3, "Kept somewhere", "Each choice is written to the consent database.",
                          "CAP-005.FR1, CON-004"))
    code, data = lint(vault, ident)
    assert code == 1
    found = {(f["ac"], f["kind"]): f for f in data["findings"]}
    assert found[(1, "component")]["words"] == ["Source reader"]
    assert found[(3, "technology")]["words"] == ["database"]
    assert not [f for f in data["findings"] if f["ac"] == 2]  # a boundary criterion is never flagged


def test_lint_flags_missing_contract_or_flow(tmp_path):
    vault = copy_of(tmp_path)
    ident = epic(vault, 91, headed(1, "Two separate choices", "A person is offered calendar entries and transcripts "
                                   "as two choices.", "CAP-005.FR1")
                 + headed(2, "Two separate choices, traced", "A person is offered calendar entries and transcripts "
                          "as two choices.", "CAP-005.FR1, FLO-001")
                 + headed(3, "An ID in the sentence", "The person sees CON-003 answer no.", "CAP-005.FR1, CON-003"))
    code, data = lint(vault, ident)
    assert code == 1
    kinds = {(f["ac"], f["kind"]) for f in data["findings"]}
    assert (1, "no-boundary") in kinds
    assert (3, "id-in-sentence") in kinds
    assert not any(ac == 2 for ac, _ in kinds)


def test_more_than_seven_criteria_flagged(tmp_path):
    vault = copy_of(tmp_path)
    seven = "".join(headed(n, f"Criterion number {n}", "Nothing is read before the consent check says yes.",
                           "CAP-005.FR1, CON-003") for n in range(1, 8))
    ident = epic(vault, 92, seven)
    code, data = lint(vault, ident)
    assert code == 0 and data["findings"] == []
    ident = epic(vault, 93, seven + headed(8, "Criterion number 8", "Nothing is read before the consent check says "
                                           "yes.", "CAP-005.FR1, CON-003"))
    code, data = lint(vault, ident)
    assert code == 1
    assert [(f["kind"], f["count"]) for f in data["findings"]] == [("too-many", 8)]


def test_fix_shape_keeps_ac_numbers(tmp_path):
    vault = copy_of(tmp_path, HERON_DESK)
    path = vault / "13-epics" / "EPC-001-calendar.md"
    text = NUMBERED.read_text(encoding="utf-8")
    # Strike one and leave a gap, so the numbers are plainly written ones and not counted ones.
    text = text.replace("3. When the calendar", "3. ~~When the calendar").replace(
        "not the old one.\n", "not the old one.~~\n").replace("7. Past calendar", "9. Past calendar")
    text = text.replace("no note appears for a call that does not count.", "no note appears for a call that does "
                        "not count. [testing]")
    path.write_text(text, encoding="utf-8")
    before = criteria.read(parse.parse_page("13-epics/EPC-001-calendar.md", text))

    code, out = run("epics", "lint", "--vault", str(vault), "--fix-shape", "EPC-001")
    assert code == 0, out
    after_text = path.read_text(encoding="utf-8")
    after = criteria.read(parse.parse_page("13-epics/EPC-001-calendar.md", after_text))
    assert [c.n for c in after] == [c.n for c in before] == [1, 2, 3, 4, 5, 6, 9]
    assert [c.form for c in after] == ["headed"] * 7 and all(c.declared for c in after)
    assert [(c.struck, c.markers, c.trace, c.group, c.text) for c in after] == \
           [(c.struck, c.markers, c.trace, c.group, c.text) for c in before]
    assert "## Epic acceptance criteria" not in after_text and "## Done when" in after_text
    assert after_text.index("## Who this is for and what changes") < after_text.index("## Done when")
    assert "- Trace: CAP-001.FR1, CON-001, FLO-001  ·  AC1  ·  [testing]" in after_text
    assert "#### " in after_text  # grouped criteria drop a level under their group heading
    assert criteria.problems(parse.parse_page("13-epics/EPC-001-calendar.md", after_text)) == []

    code, out = run("epics", "lint", "--vault", str(vault), "--fix-shape", "EPC-001")
    assert code == 0 and "already" in out and path.read_text(encoding="utf-8") == after_text


# ------------------------------------------------------------------------------------------------ frontier

def test_frontier_lists_team_gaps(tmp_path):
    code, out = run("epics", "frontier", "--vault", str(HERON), "--team", "@product-owner", "--json")
    data = json.loads(out)
    assert code == 1
    assert sorted(g["subject"] for g in data["gaps"]) == ["CON-002", "CON-003", "CON-004", "CON-005"]
    assert data["counts"]["gaps"] == {"T1": 0, "T2": 4, "T4": 0, "T6": 0}
    # No allocation row carries CAP-006, so it is no team's yet; it is said on every frontier, never dropped.
    assert [g["subject"] for g in data["unowned"]] == ["CAP-006"]
    assert sorted(a["id"] for a in data["apps"]) == ["APP-consent-and-identity", "APP-summarizer"]

    code, out = run("epics", "frontier", "--vault", str(HERON), "--team", "sim-lead", "--json")
    data = json.loads(out)
    assert code == 0 and data["gaps"] == []  # the other team's gaps are not this team's
    assert [g["subject"] for g in data["unowned"]] == ["CAP-006"]
    assert data["counts"]["epics"] == 4 and data["counts"]["criteria"] > 0

    code, out = run("epics", "frontier", "--vault", str(HERON), "--team", "@nobody")
    assert code == 1 and "@sim-lead" in out and "@product-owner" in out


def test_first_epic_on_tracer_said(tmp_path):
    code, out = run("epics", "frontier", "--vault", str(HERON), "--team", "@sim-lead", "--json")
    assert json.loads(out)["tracer"]["state"] == "no-tracer"

    vault = copy_of(tmp_path)
    releases = vault / "04b-releases.md"
    text = releases.read_text(encoding="utf-8")
    releases.write_text(text.replace("- **State:** assumption\n\n|", "- **State:** assumption\n" + TRACER + "\n|", 1),
                        encoding="utf-8")
    code, out = run("epics", "frontier", "--vault", str(vault), "--team", "@sim-lead", "--json")
    tracer = json.loads(out)["tracer"]
    assert (tracer["state"], tracer["epic"], tracer["tracer_flows"]) == ("off", "EPC-032", ["FLO-002"])
    code, out = run("epics", "frontier", "--vault", str(vault), "--team", "@sim-lead")
    assert "EPC-032" in out and "not on the tracer" in out

    first = vault / "13-epics" / "EPC-032-switch-on-and-withdraw.md"
    first.write_text(first.read_text(encoding="utf-8").replace("flows: [FLO-001, FLO-004]", "flows: [FLO-002]"),
                     encoding="utf-8")
    code, out = run("epics", "frontier", "--vault", str(vault), "--team", "@sim-lead", "--json")
    tracer = json.loads(out)["tracer"]
    assert (tracer["state"], tracer["on_tracer"]) == ("on", ["FLO-002"])


def test_for_lead_passes_the_leak_check(tmp_path):
    vault = copy_of(tmp_path)
    epic(vault, 94, headed(1, "Reads only after consent", "The Source reader reads nothing until CON-003 says yes.",
                           "CAP-005.FR1"))
    for argv in (("frontier", "--team", "@product-owner"), ("frontier", "--team", "@sim-lead"), ("lint",)):
        code, out = run("epics", *argv, "--vault", str(vault), "--for-lead")
        assert code in (0, 1), out
        assert "vela bug" not in out and out.strip()
        for kind, pattern in say.LEAD_PATTERNS.items():
            assert not pattern.search(out), (argv, kind, pattern.search(out).group(0))
    code, out = run("epics", "frontier", "--team", "@product-owner", "--vault", str(vault), "--for-lead")
    assert "Consent check" in out  # the contract by its name, never "(CON-003)"
