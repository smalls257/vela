"""What the tech-design-from-vault reference says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
from conftest import REPO

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_challenge.py: /vela:challenge: a senior's challenge after handoff becomes an open unknown they
# own, which blocks the item, and a Dissent line on it.


def test_tech_design_points_the_senior_at_challenge():
    ref = (PLUGIN / "references" / "TECH-DESIGN-FROM-VAULT.md").read_text(encoding="utf-8")
    assert "`/vela:challenge <vault ID>`" in ref
    assert "handoff verify <APP-id> --vault <vault>" in ref


# --- From tests/test_design_skill.py: /vela:design (P13, S48, S52): the plugin's design skill, the summary-first doc
# it writes, and the Heron fixture.

# --- hard requirement 3: the skill text ---------------------------------------------------------------------------


def test_the_vault_reference_and_the_skill_agree():
    ref = (PLUGIN / "references" / "TECH-DESIGN-FROM-VAULT.md").read_text(encoding="utf-8")
    assert "`/vela:design --app <APP-id>`" in ref and "design/<slug>" in ref
    assert "- **Tracer:**" in ref and "| The glossary |" in ref and "| The voices |" in ref


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_tech_design_from_vault_reads_the_slice_and_links_back():
    ref = text("references/TECH-DESIGN-FROM-VAULT.md")
    assert "`handed_off:`" in ref
    for source in ("`contracts-consumed` block", "`epics-for-app` block", "`delivers` list", "**Blocks:**"):
        assert source in ref
    assert "Never copy vault text into the design doc." in ref
    assert "`challenges: <vault ID>`" in ref
    assert "The design never edits the vault." in ref


def test_the_vault_reference_says_designs_live_in_the_vault():
    ref = text("references/TECH-DESIGN-FROM-VAULT.md")
    assert "in the vault" in ref and "team_repos" not in ref


# --- From tests/test_team_side_skills.py: The team-side skills: the design reference a senior follows from a vault,
# and the work-breakdown skill (S19, S33, S35, S37).


def test_tech_design_never_reads_a_missing_program_as_no_manifest():
    ref = text("references/TECH-DESIGN-FROM-VAULT.md")
    assert "Where vela runs from" in ref and "A missing program is never \"no manifest\"." in ref
    assert 'message "does not exist"' in ref and "Any other exit 2" in ref


def test_tech_design_says_where_its_files_land_and_what_to_do_when_it_runs_out_of_room():
    ref = text("references/TECH-DESIGN-FROM-VAULT.md")
    assert "Do not commit them to `main`" in ref and "design/<slug>" in ref and "origin/main" in ref
    assert "## Running out of room" in ref and "status: in-progress" in ref


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_the_vault_design_reference_carries_its_tracer_guidance():
    assert "**Not in the tracer:**" in read("references/TECH-DESIGN-FROM-VAULT.md")


# --- Task 22k (diagnosis 6B): S23 checked the handoff on a stale branch, because the fetch came after the check.


def test_tech_design_fetches_before_it_checks_the_handoff():
    before = text("references/TECH-DESIGN-FROM-VAULT.md").split("## Before the first question", 1)[1].split("\n## ", 1)[0]
    assert before.index("git -C <vault> fetch origin") < before.index("`handed_off:`")
    assert "git -C <vault> show origin/main:05-building-blocks/<app>-building-blocks.md" in before
    assert "senior" not in text("references/TECH-DESIGN-FROM-VAULT.md")
