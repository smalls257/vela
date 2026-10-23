"""What the modes reference says, pinned in one place (overhaul plan Task 3; rewritten by Task 22j).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Task 22j left MODES the conversation rules ("ask the lead first", "never draft an ask", the unknowns and owed
questions) and moved what the CLI enforces to it: `vela add unknown` numbers and dates an unknown, and a `resolve`
decision through `vela apply` writes the answer.
"""
import inspect
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
    # rule deletion: what each mode writes, and when, is its own skill's and the commands'; the table keeps the grade
    assert "## Who writes what, and when" not in MODES and "| During the session | At close |" not in MODES
    assert "| `epics` | `draft` epic pages" not in MODES and "stub: boundary" not in MODES


def test_modes_no_longer_names_the_design_session():
    # rule deletion: the design skill holds its own rules and no mode session reads MODES for it
    assert "## Team-side sessions" not in MODES and "`/vela:design --app APP-x`" not in MODES
    design = (PLUGIN / "skills" / "design" / "SKILL.md").read_text(encoding="utf-8")
    assert "A design opens no session" in design and "`docs/tech-design/<slug>.md`" in design
    assert "Shell that runs on a Mac and on Linux" not in design, "START no longer has that section"


def test_modes_says_epics_runs_render_too():
    assert "Close runs `vela render` for those." not in MODES and "so does `epics`" in MODES
    assert "stages every file it reports, by exact path" not in MODES  # close_stage and the hook own staging


def test_modes_is_leaner_than_it_was():
    # The eval cases grade the "Claude must not" column, so the table stays word for word; the mechanics around it went.
    assert len(MODES.split()) <= 1290  # 2,301 before the first trim; 1,838 after it; 1,253 after the second


def test_modes_says_the_user_may_override_any_rule():
    assert "The user may override any of them" in MODES


def test_modes_has_no_question_cap_and_no_sweep():
    assert "at most two questions" not in MODES and "concern sweep" not in MODES
    assert "## Owed questions" in MODES and "No question is owed a quota" in MODES
    assert "question ledger rows" not in MODES
    assert "at most three at a time, once per session" not in MODES  # questions.py's digest does it
    assert "no cap" not in MODES.lower()


def test_modes_asks_once_what_the_lead_might_not_know_they_need():
    assert "**Ask what they might not know they need.**" in MODES
    assert "In Discover, Shape and a grill" in MODES and "who has to agree or be consulted" in MODES
    assert "street-works permit" in MODES  # the worked example of asking, not answering, stays word for word


def test_modes_says_where_to_start():
    assert "## Where to start" not in MODES  # rule deletion: `vela session brief` names the next step
    start = (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")
    assert "offer the brief's next step as a suggestion, never a decision" in start


def test_modes_writes_assumptions_with_options_considered():
    assert "`assumption` items with `**Options considered:**`" not in MODES  # the shape skill and the gate own it


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
    assert "propose one of each and ask" in unknowns and "with the reason for the date" in unknowns
    assert "file `--ask-by` only with that capture behind it" in unknowns
    # rule deletion: `add unknown` refuses a date nobody gave (decisions/add_unknown.py) and numbers and links itself
    for gone in ("it never picks one", "It never picks an ask-by date", "which numbers it and links", "won't file a date"):
        assert gone not in unknowns, gone
    assert "leave `--ask` off" in unknowns and "check-back date" not in unknowns and "two weeks out" not in unknowns
    # rule deletion: numbering, the E208 clash and the resolved-bullet grammar are the CLI's now
    for old in ("vela next-id UNK", "E208", "`**State:** resolved`", "`**Resolved in:**`", "no `**Ask by:**`"):
        assert old not in MODES, old


def test_modes_says_team_lead_and_grill_in_lower_case():
    assert "senior" not in MODES
    prose = "\n".join(line for line in MODES.splitlines() if not line.startswith("| Grill (`grill`)"))
    assert not re.search(r"\bGrill\b", prose)


def test_a_yes_in_a_session_that_cannot_decide_goes_through_vela_decide():
    from conftest import REPO
    modes = (REPO / "plugin/references/MODES.md").read_text(encoding="utf-8")
    assert "run `vela decide` on it anyway" in modes and "says what to offer" in modes
    assert "offer the lead a short grill" not in modes and "an assumption nobody sees again" not in modes
    # the command says it, in the refusal's fix: offer a short grill now, or say it is marked and move on
    from vela.commands import decide
    source = inspect.getsource(decide.cannot_decide_here)
    assert "Offer the lead a short grill on it now" in source and "say it is marked and move on" in source

