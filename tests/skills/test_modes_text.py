"""What the modes reference says, pinned in one place (overhaul plan Task 3; rewritten by Task 22j).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Task 22j left MODES the conversation rules ("ask the lead first", "never draft an ask", the unknowns and owed
questions) and moved what the CLI enforces to it: `vela add unknown` numbers and dates an unknown, and a `resolve`
decision through `vela apply` writes the answer.
"""
import re

from conftest import REPO

PLUGIN = REPO / "plugin"
MODES = (PLUGIN / "references" / "MODES.md").read_text(encoding="utf-8")


def section(heading):
    """The body of a `## heading` section, up to the next `## `."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", MODES, re.M | re.S)
    return match.group(1) if match else ""


def test_modes_lists_every_session_mode_row():
    for row in ("| Answer (`answer`)", "| Challenge (`challenge`)", "| Boundary (`boundary`) |", "| Epics (`epics`)"):
        assert row in MODES, row
    for row in ("| `answer` |", "| `boundary` |", "| `epics` | `draft` epic pages"):
        assert row in MODES, row


def test_modes_names_the_design_session():
    team = section("Team-side sessions")
    assert "`/vela:design --app APP-x`" in team and "`docs/tech-design/<slug>.md`" in team


def test_modes_says_epics_runs_render_too():
    assert "Close runs `vela render` for those." not in MODES and "so does `epics`" in MODES


def test_modes_says_the_user_may_override_any_rule():
    assert "The user may override any of them" in MODES


def test_modes_has_no_question_cap_and_no_sweep():
    assert "at most two questions" not in MODES and "concern sweep" not in MODES
    assert "## Owed questions" in MODES and "No question is dropped and none is owed a quota" in MODES
    assert MODES.count("question ledger rows") == 5  # dump, discover, shape, boundary and grill write them at close
    assert "no cap" not in MODES.lower()


def test_modes_asks_once_what_the_lead_might_not_know_they_need():
    assert "**Ask what they might not know they need.**" in MODES
    assert "In Discover, Shape and a grill" in MODES and "who has to agree or be consulted" in MODES
    assert "street-works permit" in MODES  # the worked example of asking, not answering, stays word for word


def test_modes_says_where_to_start():
    start = section("Where to start")
    assert "`vela next` names the one app and mode" in start and "`vela status` shows every app's stage" in start
    assert "never a decision" in start


def test_modes_writes_assumptions_with_options_considered():
    assert "`assumption` items with `**Options considered:**`" in MODES


def test_there_is_no_probe_skill():
    assert not (PLUGIN / "skills" / "probe").exists()
    assert "probe" not in MODES.lower()


def test_modes_asks_the_lead_first_never_drafts_an_ask_and_ends_a_blocked_session():
    assert "**Ask the lead first.**" in MODES and "**A blocked session ends.**" in MODES
    assert "Claude never drafts an email, a message, a chase or an ask for anyone to send, and never offers to." in MODES
    assert "Never fill a blocked session with other work." in MODES


def test_modes_carries_its_tracer_guidance():
    assert "offer the tracer" in MODES and "first epic is on release one's tracer" in MODES


def test_unknowns_are_written_by_the_command_and_roles_are_spelled_out():
    unknowns = section("Unknowns")
    assert "`vela add unknown`" in unknowns and "`--ask`" in unknowns
    assert '"the data protection officer", not "DPO"' in unknowns
    assert "`resolve` decision through `vela apply`" in unknowns
    # an unsure lead gets a proposed role and date to confirm, never a filled-in one
    assert "propose one of each and ask" in unknowns and "Write only what the lead agreed to or named." in unknowns
    assert "leave `--ask` off" in unknowns and "not a deadline anyone agreed" in unknowns
    # rule deletion: numbering, the E208 clash and the resolved-bullet grammar are the CLI's now
    for old in ("vela next-id UNK", "E208", "`**State:** resolved`", "`**Resolved in:**`", "no `**Ask by:**`"):
        assert old not in MODES, old


def test_modes_says_team_lead_and_grill_in_lower_case():
    assert "senior" not in MODES
    prose = "\n".join(line for line in MODES.splitlines() if not line.startswith("| Grill (`grill`)"))
    assert not re.search(r"\bGrill\b", prose)
