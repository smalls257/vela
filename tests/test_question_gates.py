"""The three gates that read the question ledger, and the override of the epics one.

Open rows are allowed between gates. At a gate the questions that matter there are said:
assumed rows at the end of a Shape, blocking rows in a Grill, undisposed high-severity rows
before epics are called complete. The user may override the epics gate; the override is
recorded and every overridden question still prints."""
import shutil

import pytest

from conftest import REPO, edit, findings, run

FIXTURE = REPO / "examples" / "unified-booking"
LEDGER = "11-unknowns-and-risks.md"
TODAY = "2026-11-20"


def _fixture_row(prefix):
    """The fixture's own ledger row, so a test that removes or edits it never restates its text."""
    text = (FIXTURE / LEDGER).read_text(encoding="utf-8")
    return next(line for line in text.splitlines() if line.startswith(prefix)) + "\n"


DAT_02_ALL = _fixture_row("| Q-DAT-02@APP-* |")
PTN_02 = _fixture_row("| Q-PTN-02@PTY-02 |")
ASSUMED_ROWS = sum(1 for line in (FIXTURE / LEDGER).read_text(encoding="utf-8").splitlines() if "| assumed |" in line)
OVERRIDE = "- **Override:** E805 by @hl-solution-lead on 2026-11-20: the CIO wants the epics out before the DPO is back\n\n"


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    return dest


def gate(vault, *argv):
    run("render", "--vault", str(vault))
    return run("check", "--vault", str(vault), "--today", TODAY, *argv)


def heading_line(vault):
    lines = (vault / LEDGER).read_text(encoding="utf-8").split("\n")
    return lines.index("## Question ledger") + 1


# ------------------------------------------------------------------ epics

def test_an_undisposed_high_question_fails_the_epics_gate_and_nothing_else(ub):
    edit(ub / LEDGER, DAT_02_ALL, "")
    code, out = gate(ub)
    assert code == 0 and findings(out) == [], "a plain check lets open questions be"
    code, out = gate(ub, "--gate", "epics")
    assert code == 1
    assert findings(out) == [("E805", LEDGER)] * 3, "call centre, kiosks and website"
    assert f"{LEDGER}:{heading_line(ub)}: E805 Q-DAT-02@APP-call-centre is high severity and has no ledger row: What customer data" in out


def test_an_open_or_asked_high_row_fails_the_gate_at_its_own_line(ub):
    edit(ub / LEDGER, PTN_02, "| Q-PTN-02@PTY-02 | asked | capture: [[2026-11-19-owed-questions#^c01]] | @hl-solution-lead | 2026-11-19 |\n")
    code, out = gate(ub, "--gate", "epics")
    assert code == 1 and findings(out) == [("E805", LEDGER)]
    assert "Q-PTN-02@PTY-02 is high severity and is asked:" in out
    edit(ub / LEDGER, "| Q-PTN-02@PTY-02 | asked | capture: [[2026-11-19-owed-questions#^c01]] | @hl-solution-lead | 2026-11-19 |\n",
         "| Q-PTN-02@PTY-02 | open |  |  |  |\n")
    assert "Q-PTN-02@PTY-02 is high severity and is open:" in gate(ub, "--gate", "epics")[1]


def test_an_invalid_high_row_disposes_of_nothing_and_the_gate_says_so(ub):
    text = (ub / LEDGER).read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| Q-FIN-03@SV-01 |"))
    edit(ub / LEDGER, row, row.split("; answer:")[0] + " | @hl-solution-lead | 2026-11-19 |")
    code, out = gate(ub, "--gate", "epics")
    assert code == 1 and ("E805", LEDGER) in findings(out)
    assert "Q-FIN-03@SV-01 is high severity and is invalid (answered):" in out


def test_a_copy_answered_through_a_wildcard_says_so(ub):
    edit(ub / LEDGER, DAT_02_ALL, DAT_02_ALL.split("| assumed |")[0] + "| open |  |  |  |\n")
    out = gate(ub, "--gate", "epics")[1]
    assert "Q-DAT-02@APP-kiosks is high severity and is open (by Q-DAT-02@APP-*):" in out


def test_a_high_reviewer_question_fails_the_gate(ub):
    edit(ub / LEDGER, "; severity: normal |", "; severity: high |")
    code, out = gate(ub, "--gate", "epics")
    assert code == 1 and findings(out) == [("E805", LEDGER)]
    assert "R-FIN-01 is high severity and is open:" in out


def test_the_user_may_override_the_epics_gate_and_every_question_still_prints(ub):
    edit(ub / LEDGER, DAT_02_ALL, "")
    edit(ub / LEDGER, "## Question ledger\n\n", "## Question ledger\n\n" + OVERRIDE)
    code, out = gate(ub, "--gate", "epics")
    assert code == 0, out
    assert findings(out) == [("W805", LEDGER)] * 3
    assert "Overridden: E805 by @hl-solution-lead on 2026-11-20: the CIO wants the epics out" in out


def test_the_epics_override_is_never_idle_on_a_plain_check(ub):
    edit(ub / LEDGER, "## Question ledger\n\n", "## Question ledger\n\n" + OVERRIDE)
    assert findings(gate(ub)[1]) == [], "a plain check cannot test E805, so it never calls the override idle"
    assert findings(gate(ub, "--gate", "epics")[1]) == [("W323", LEDGER)]


def test_a_misspelt_epics_override_is_e321_and_overrides_nothing(ub):
    edit(ub / LEDGER, DAT_02_ALL, "")
    edit(ub / LEDGER, "## Question ledger\n\n", "## Question ledger\n\n" + OVERRIDE.replace("E805", "E85"))
    code, out = gate(ub, "--gate", "epics")
    assert code == 1
    assert sorted(set(findings(out))) == [("E321", LEDGER), ("E805", LEDGER)]


# ------------------------------------------------------------------ shape

def test_the_shape_gate_warns_on_each_assumed_row(ub):
    code, out = gate(ub, "--gate", "shape")
    assert code == 0
    assert findings(out) == [("W806", LEDGER)] * ASSUMED_ROWS
    assert "Q-OPS-07@INI-002 is still assumed: customers amend online once they can." in out
    assert findings(gate(ub)[1]) == [] and findings(gate(ub, "--gate", "epics")[1]) == []


# ------------------------------------------------------------------ grill

def test_the_grill_gate_warns_at_the_item_for_each_open_question_that_blocks_it(ub):
    edit(ub / LEDGER, DAT_02_ALL, "")
    code, out = gate(ub, "--gate", "grill", "--item", "CON-001", "--item", "ADR-0001")
    assert code == 0
    assert out.splitlines()[0].endswith("Gate: grill. Items: ADR-0001, CON-001.")
    got = [line for line in out.splitlines() if " W807 " in line]
    assert len(got) == 3, "call centre, kiosks and website block CON-001; nothing open blocks ADR-0001"
    assert all(line.startswith("05-building-blocks/booking-building-blocks.md:") for line in got)
    assert "Q-DAT-02@APP-kiosks has no ledger row and blocks CON-001:" in out


def test_the_grill_gate_is_quiet_when_nothing_open_blocks_the_item(ub):
    assert findings(gate(ub, "--gate", "grill", "--item", "CON-002")[1]) == []


@pytest.mark.parametrize("argv, said", [
    (("--gate", "grill"), "--gate grill needs the agenda"),
    (("--item", "CON-001"), "--item names a Grill's agenda, so it goes with --gate grill."),
    (("--gate", "grill", "--item", "CON-099"), "--item CON-099 is not an ID in this vault."),
])
def test_grill_gate_arguments_that_cannot_work_exit_2(argv, said):
    code, out = run("check", "--vault", str(FIXTURE), "--today", TODAY, *argv)
    assert code == 2 and said in out


def test_a_vault_with_no_ledger_page_still_fails_the_epics_gate_loudly(tmp_path):
    vault = tmp_path / "bare"
    vault.mkdir()
    (vault / ".planner.yaml").write_text("initiative: INI-777\ntitle: Bare\n", encoding="utf-8")
    (vault / "README.md").write_text("---\nid: readme\ntype: index\ntitle: Bare\nauthored: authored\n---\n\n# Bare\n",
                                     encoding="utf-8")
    code, out = run("check", "--vault", str(vault), "--today", TODAY, "--gate", "epics")
    assert code == 1
    assert findings(out) == [("E805", LEDGER)] * 4
    assert f"{LEDGER}:1: E805 Q-DAT-01@INI-777 is high severity and has no ledger row:" in out


# ------------------------------------------------------------------ fix round 1

def strip_ledger_heading(vault):
    """The ledger page with its `## Question ledger` section cut off, as an older vault would have it."""
    path = vault / LEDGER
    text = path.read_text(encoding="utf-8")
    path.write_text(text[:text.index("## Question ledger")], encoding="utf-8")


def test_an_override_reaches_e805_at_line_1_when_the_ledger_heading_is_missing(ub):
    strip_ledger_heading(ub)
    code, out = run("check", "--vault", str(ub), "--today", TODAY, "--gate", "epics")
    assert code == 1 and f"{LEDGER}:1: E805" in out
    assert "The page has no ## Question ledger heading." in out and "Add ## Question ledger to the page." in out
    top = (ub / LEDGER).read_text(encoding="utf-8").replace("\n# ", "\n" + OVERRIDE + "# ", 1)
    (ub / LEDGER).write_text(top, encoding="utf-8")
    code, out = run("check", "--vault", str(ub), "--today", TODAY, "--gate", "epics")
    codes = {c for c, _ in findings(out)}
    assert "W805" in codes and "E805" not in codes and "W323" not in codes
    # the only error left is the owed-questions session's own link to the heading this test cut off
    assert codes - {"W805", "W809"} <= {"E202"}  # W809: no valid row answers Q-REG-02 while the ledger is cut off


def test_the_epics_gate_says_plainly_when_the_vault_has_no_ledger_page(tmp_path):
    vault = tmp_path / "bare"
    vault.mkdir()
    (vault / ".planner.yaml").write_text("initiative: INI-777\ntitle: Bare\n", encoding="utf-8")
    code, out = run("check", "--vault", str(vault), "--today", TODAY, "--gate", "epics")
    assert code == 1
    assert "The vault has no 11-unknowns-and-risks.md ledger page." in out


def test_an_invalid_high_reviewer_row_fails_the_gate_and_an_override_clears_it(ub):
    edit(ub / LEDGER, "; severity: normal |", "; severity: high |")
    edit(ub / LEDGER, '"because points are earned at reservation"', '"words the page never says"')
    code, out = gate(ub, "--gate", "epics")
    assert code == 1
    assert "R-FIN-01 is high severity and is invalid (open):" in out
    edit(ub / LEDGER, "## Question ledger\n\n", "## Question ledger\n\n" + OVERRIDE)
    out = gate(ub, "--gate", "epics")[1]
    assert "W805 R-FIN-01" in out and "W323" not in out


def test_a_grill_item_no_question_can_block_is_said_not_passed_quietly(ub):
    code, out = gate(ub, "--gate", "grill", "--item", "PTY-01")
    assert code == 0
    assert "No catalogue question blocks PTY-01" in out
