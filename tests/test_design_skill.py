"""/vela:design (P13, S48, S52): the plugin's design skill, the summary-first doc it writes, and the Heron fixture.

    python3 -m pytest tests/test_design_skill.py

tests/fixtures/team-skills/heron/ is the Heron vault from the 2026-10-12 design run, with its design doc and ADR
re-shaped into the skill's format. heron-original/ holds the run's own files, unchanged except the clone path in
`origin:`, so every count here is held against the original, not against a number typed in.
"""
import re
import shutil

import pytest

from conftest import REPO
from vela import cli
from vela.explorer import breakdown_find, build, design_data, design_find, plan_data

PLUGIN = REPO / "plugin"
SKILL = PLUGIN / "skills" / "design"
FIXTURES = REPO / "tests" / "fixtures" / "team-skills"
HERON = FIXTURES / "heron"
ORIGINAL = FIXTURES / "heron-original"
NEW_DOC = HERON / "docs" / "tech-design" / "desktop-agent.md"
OLD_DOC = ORIGINAL / "docs" / "tech-design" / "desktop-agent.md"
APP = "APP-desktop-agent"


def section(text, heading):
    """The body of a `## heading` section, up to the next `## `."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


# --- the reader: two backward-compatible changes ------------------------------------------------------------------

DOC = """---
slug: x
status: in-progress
last_session: 2026-10-12
---

# Tech Design — X

## Summary
X shows the digest.

**Decisions that shape it:**
- One process.

## Walking skeleton
The digest first.
- **Flow:** the digest (FLO-002)
- **Path:** Gate → Reader

## Components
### Gate
- Responsibility: ask.
- Owns: the grant.
- Depends on: Consent and identity (CON-003), Reader.
- Exposes: grant.

### Reader
- Responsibility: read.
- Owns: nothing.
- Depends on: Consent and identity.
- Exposes: read.

## Integration points
| System | Direction | Protocol | Auth |
|--------|-----------|----------|------|
| Consent and identity (CON-003) | agent calls | HTTPS | token |
"""


def write(tmp_path, text):
    path = tmp_path / "docs" / "tech-design" / "x.md"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_dependency_whose_name_holds_and_is_read_whole_when_the_design_names_it(tmp_path):
    design = design_data.read_design(write(tmp_path, DOC))
    gate = next(c for c in design["components"] if c["name"] == "Gate")
    assert gate["depends_on_other"] == ["Consent and identity (CON-003)"] and gate["depends_on_components"] == ["Reader"]
    assert not [p for p in design["problems"] if "depends on" in p["message"]], design["problems"]


def test_a_dependency_list_joined_by_and_still_splits():
    assert design_data._split_names("A, B and C") == ["A", "B", "C"]
    assert design_data._split_names("A and B", known={"c"}) == ["A", "B"]
    assert design_data._split_names("Consent and identity, A", known={"consent and identity"}) == ["Consent and identity", "A"]


def test_the_summary_and_walking_skeleton_are_read_and_never_required(tmp_path):
    design = design_data.read_design(write(tmp_path, DOC))
    assert design["summary"]["text"].startswith("X shows the digest.")
    assert design["walking_skeleton"]["fields"]["Path"] == "Gate → Reader"
    assert not design["extra_sections"]
    older = design_data.read_design(write(tmp_path / "old", DOC.split("## Summary")[0] + "## Components\n"))
    assert older["summary"] == {"text": "", "mermaid": []} and older["walking_skeleton"]["fields"] == {}
    assert not [p for p in older["problems"] if "Summary" in p["message"] or "Walking" in p["message"]]


def test_the_missing_design_line_names_the_design_command(tmp_path):
    vault = cli.load_vault(HERON)
    _, said = design_find.discover(vault, tmp_path, [])
    assert any("/vela:design --app <app ID>" in line for line in said), said


# --- hard requirement 1: as detailed as before -------------------------------------------------------------------

def components(design):
    """The real components: a ### under Components that carries a Responsibility bullet."""
    return [c["name"] for c in design["components"] if c["responsibility"]]


def decisions(text):
    body = section(text, "Architecture overview")
    block = body.split("### Decisions", 1)[1].split("\n### ", 1)[0]
    return [line for line in block.splitlines() if line.startswith("- ")]


@pytest.fixture(scope="module")
def old():
    return design_data.read_design(OLD_DOC)


@pytest.fixture(scope="module")
def new():
    return design_data.read_design(NEW_DOC)


def test_the_fixture_keeps_every_component_decision_and_adr(old, new):
    assert components(new) == components(old) and len(components(new)) == 7
    assert [c["name"] for c in new["components"]] == components(old)  # the gate note is no longer misread as a component
    assert decisions(NEW_DOC.read_text()) == decisions(OLD_DOC.read_text()) and len(decisions(OLD_DOC.read_text())) == 3
    assert [a["id"] for a in new["adrs"]] == [a["id"] for a in old["adrs"]] == ["ADR-0001"]
    old_adrs, new_adrs = sorted((ORIGINAL / "docs" / "adr").glob("*.md")), sorted((HERON / "docs" / "adr").glob("*.md"))
    assert [p.name for p in new_adrs] == [p.name for p in old_adrs]
    assert all(n.read_text() == o.read_text() for n, o in zip(new_adrs, old_adrs))  # the ADR format did not change
    for c_old, c_new in zip([c for c in old["components"] if c["responsibility"]], new["components"]):
        for field in ("responsibility", "owns", "exposes", "container"):
            assert c_new[field] == c_old[field], (c_new["name"], field)


def test_the_fixture_keeps_every_open_question_deferral_and_gap(old, new):
    assert [q["id"] for q in new["open_questions"]] == [q["id"] for q in old["open_questions"]] == [f"OQ-{n:03d}" for n in range(1, 11)]
    for q_old, q_new in zip(old["open_questions"], new["open_questions"]):
        assert q_new["title"] == q_old["title"] and q_new["what_we_know"] == q_old["what_we_know"] and q_new["affects"] == q_old["affects"]
        assert q_new["what_would_unblock"].startswith(q_old["what_would_unblock"])
        assert q_new["other"] == q_old["other"]
    assert [q["challenges"] for q in new["open_questions"]][:9] == [q["challenges"] for q in old["open_questions"]][:9]
    assert new["open_questions"][9]["challenges"] == []  # OQ-010 challenges nothing, so it has no Challenges line
    assert new["frontmatter"]["deferred"] == old["frontmatter"]["deferred"] and len(old["frontmatter"]["deferred"]) == 4
    keep = lambda gaps: [(g["id"], g.get("oq"), g["why"], g["revisit"]) for g in gaps]
    assert keep(new["frontmatter"]["gaps"]) == keep(old["frontmatter"]["gaps"]) and len(new["frontmatter"]["gaps"]) == 11


def test_gaps_say_what_is_wrong_in_plain_words_and_name_a_person(new):
    names = ("Distributed Monolith", "Black Box", "Leaky Narrative", "Infected Core", "Silent Fallback", "God Class")
    for gap in new["frontmatter"]["gaps"]:
        assert not any(n in gap["what"] for n in names), gap
        assert gap["acknowledged_by"].startswith("@"), gap


def test_the_fixture_keeps_every_trace_row_table_row_rule_and_term(old, new):
    def table_trace(design):
        return {(c, e["id"]) for c, entries in design["trace"].items() for e in entries if "trace table" in e["via"]}

    def strip(rows):
        return [{k: v for k, v in r.items() if k != "line"} for r in rows]
    assert table_trace(new) == table_trace(old) and len(table_trace(new)) > 0 and new["trace_source"] == "recorded"
    for key in ("matrix", "tech_stack", "constraints", "risks"):
        assert strip(new[key]) == strip(old[key]), key
    assert len(new["nfrs"]) == len(old["nfrs"]) == 6  # one cell now points at API contracts, where the failure table went
    assert [r["system"] for r in new["integrations"]][:3] == [r["system"] for r in old["integrations"]]
    assert {k: v for k, v in new["operations"].items() if k != "raw"} == {k: v for k, v in old["operations"].items() if k != "raw"}
    assert new["data_model"]["entities"] == old["data_model"]["entities"] and new["data_model"]["stores"] == old["data_model"]["stores"]
    assert len(new["flows"]) == len(old["flows"]) == 1
    old_api, new_api = section(OLD_DOC.read_text(), "API contracts"), section(NEW_DOC.read_text(), "API contracts")
    assert len(re.findall(r"^\d\. \*\*", old_api, re.M)) == 5
    assert sorted(re.findall(r"^- Rule (\d),", new_api, re.M)) == ["1", "2", "3", "4", "5"]
    assert len(re.findall(r"^\| CON-00\d ", old_api, re.M)) == len(re.findall(r"^- On failure:", new_api, re.M)) == 4
    assert [t["term"] for t in new["context"]["glossary"]] == [t["term"] for t in old["context"]["glossary"]]


def test_no_word_of_the_original_is_lost_but_the_audit_names_and_retitled_rules():
    def words(text):
        return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", text)}
    lost = words(OLD_DOC.read_text()) - words(NEW_DOC.read_text())
    # the audit's names left the gaps; "fail closed everywhere" and "Retry and recovery rules follow the table" were
    # headings over the failure table, which now sits under each component's public surface
    assert lost <= {"black", "distributed", "monolith", "deploy", "everywhere", "follow", "table"}, sorted(lost)


def test_the_summary_comes_first_and_stays_short(new):
    body = NEW_DOC.read_text().split("\n---\n", 1)[1]
    assert re.findall(r"^## .+$", body, re.M)[:3] == ["## Summary", "## Walking skeleton", "## Architecture overview"]
    summary = section(body, "Summary")
    assert len(summary.split()) <= 220 and summary.count("\n- ") in range(3, 6)
    assert "**Walking skeleton:**" in summary and "**Still open:**" in summary
    assert new["walking_skeleton"]["fields"]["Path"].startswith("Scheduler")


# --- hard requirement 2: the explorer reads it --------------------------------------------------------------------

def built(root):
    """(data, report lines) as `vela explore` builds them, without writing the page."""
    vault = cli.load_vault(root)
    found, said = design_find.discover(vault, root, [])
    plans, plan_said = breakdown_find.discover(vault, root, [], found)
    data = build.extract(vault, root, "2026-10-12", designs=design_data.designs_for(found), plans=plan_data.plans_for(plans))
    return data, said + build.design_lines(data["designs"]) + plan_said + build.plan_lines(data["plans"])


def built_with(tmp_path, doc, plan=None):
    root = tmp_path / doc.parent.parent.parent.name / "vault"
    shutil.copytree(HERON, root)
    shutil.copy(doc, root / "docs" / "tech-design" / "desktop-agent.md")
    if plan:
        (root / "docs" / "plan").mkdir()
        shutil.copy(plan, root / "docs" / "plan" / "desktop-agent-breakdown.md")
    return built(root)


def app_entry(data, field):
    return next(d for d in data[field].values() if d["appId"] == APP)


def test_the_explorer_reads_the_fixture_with_nothing_it_could_not_read(tmp_path):
    data, said = built(HERON)
    line = next(s for s in said if s.startswith(f"{APP} design desktop-agent.md"))
    assert line == f"{APP} design desktop-agent.md: complete-with-gaps, 7 components, 0 things it could not read", said
    design = app_entry(data, "designs")
    assert design["frontmatter"]["status"] in ("complete", "complete-with-gaps")
    assert design["trace_source"] == "recorded" and not design["resolved"]["untraced"] and not design["resolved"]["unresolved"]
    assert len(design["stubs"]) >= 3 and design["depends"] and design["summary"]["text"]
    original, _ = built_with(tmp_path, OLD_DOC)
    assert len(app_entry(original, "designs")["problems"]) == 16  # the run's own doc, for the record


def test_the_original_build_plan_reads_the_same_beside_the_reshaped_design(tmp_path):
    plan = ORIGINAL / "docs" / "plan" / "desktop-agent-breakdown.md"
    old_data, _ = built_with(tmp_path / "old", OLD_DOC, plan)
    new_data, _ = built_with(tmp_path / "new", NEW_DOC, plan)
    old_plan, new_plan = app_entry(old_data, "plans"), app_entry(new_data, "plans")
    assert (new_plan["totals"]["stories"], new_plan["totals"]["tasks"], new_plan["totals"]["points"]) == (12, 42, 153)
    assert new_plan["totals"] == old_plan["totals"]
    assert new_plan["problems"] == old_plan["problems"]  # the plan's own, and nothing the new design adds
    assert new_plan["coverage"]["targets"] == old_plan["coverage"]["targets"]
    phantom = "Enforcing the gate inside one process"  # a note the old doc kept under Components, read as an eighth
    assert new_plan["coverage"]["components"] == [c for c in old_plan["coverage"]["components"] if c["name"] != phantom]
    assert len(old_plan["coverage"]["components"]) == 8 and len(new_plan["coverage"]["components"]) == 7


@pytest.mark.browser
def test_the_fixture_page_opens_the_design_on_its_summary(tmp_path):
    """The page's own selftest opens Inside this app for the Desktop agent: components drawn, the panel on the summary."""
    import subprocess
    import sys
    from test_explorer_browser import _check_selftest_in_chrome, find_chrome
    chrome = find_chrome()
    vault = tmp_path / "vault"
    shutil.copytree(HERON, vault)
    cmd = [sys.executable, str(PLUGIN / "scripts" / "vela"), "explore", "--selftest", str(vault), "--today", "2026-10-12"]
    assert subprocess.run(cmd, timeout=120, capture_output=True, text=True).returncode == 0
    lines = _check_selftest_in_chrome(chrome, vault / "dashboard.html", "team-skills/heron")
    assert any("the design panel opens on its summary, with the walking skeleton below" in line for line in lines)


# --- design as a known mode ---------------------------------------------------------------------------------------

def test_vela_next_offers_the_design_for_a_handed_off_app_with_none(tmp_path):
    from conftest import run
    vault = tmp_path / "vault"
    shutil.copytree(HERON, vault)
    code, out = run("next", "--vault", str(vault), "--today", "2026-10-12")
    assert code == 0 and ", design." not in out, out  # the design is there, so no design step is named
    assert out.splitlines()[0].startswith("vela next: Consent and identity: grill"), out  # the lead's step stays first
    assert "vela next: for the Desktop agent team: their design is" in out and "/vela:breakdown" in out, out  # the team's own next step
    shutil.rmtree(vault / "docs" / "tech-design")
    code, out = run("next", "--vault", str(vault), "--today", "2026-10-12")
    # what is not firm at handoff is its own line and an indented list; the lead's step and the team's step are the two others
    lines = [l for l in out.splitlines() if not l.startswith(("  ", 'What "')) and "not settled yet:" not in l]
    assert code == 0 and len(lines) == 2 and lines[0].startswith("vela next: Consent and identity: grill"), out
    assert lines[1] == ("vela next: for the Desktop agent team: the app is handed over but has no technical design "
                        f"yet. They start it with /vela:design --app {APP}."), out


# --- hard requirement 3: the skill text ---------------------------------------------------------------------------

