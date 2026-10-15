"""What the releases skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO, run, skill_text
from test_releases import LINK, check, vault_with
from vela import cli, releases

SKILL = (REPO / "plugin" / "skills" / "releases" / "SKILL.md").read_text(encoding="utf-8")


def skill_example():
    """The release section the skill tells Claude to write, pointed at a requirement the fixture has."""
    block = re.search(r"## 3\. Write the confirmed slices and releases.*?```\n(.*?)```", SKILL, re.S).group(1)
    return block.replace(r"[[CAP-002-paper-trade-a-stock#CAP-002.FR2 Place a paper order\|CAP-002.FR2]]", LINK)


TODAY = "2026-11-20"


PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


LINT = [w.strip() for w in (PLUGIN / "references" / "lint-words.txt").read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]


# --- From tests/test_releases_skill.py: /vela:releases writes the page releases.py reads; vela next offers it after
# allocation and before epics.


def test_the_format_the_skill_writes_round_trips_through_releases_py(tmp_path):
    vault = vault_with(tmp_path, skill_example())
    found = releases.releases(cli.load_vault(vault))
    assert len(found) == 1
    release = found[0]
    assert release.name == "Release one: January board demo"
    assert (release.target, release.state, release.slices) == ("2027-01-15", "assumption", ("SLC-001", "SLC-002"))
    assert [(r.requirement, r.criteria, r.note) for r in release.rows] == [("CAP-014.FR1", (1, 2), "AC3 in release two")]
    out = check(vault)
    assert not any(code in out for code in ("E340", "E341", "E342", "E344")), out


def test_the_skill_names_the_exact_header_and_the_codes_it_must_pass():
    assert "| Delivers | Criteria | Note |" in SKILL
    assert releases.HEADER == ("Delivers", "Criteria", "Note")
    for code in ("E344", "E340", "E341", "W343"):
        assert code in SKILL


def test_next_offers_releases_once_allocation_is_carried_and_no_release_exists(tmp_path):
    vault = vault_with(tmp_path, "")
    for epic in (vault / "13-epics").glob("EPC-*.md"):
        epic.unlink()
    said = run("next", "--vault", str(vault), "--today", TODAY)[1]
    assert "for the whole plan: date the releases" in said, said
    (vault / "04b-releases.md").write_text(vault_with(tmp_path / "second", skill_example()).joinpath("04b-releases.md").read_text(encoding="utf-8"),
                                           encoding="utf-8")
    assert "initiative, releases" not in run("next", "--vault", str(vault), "--today", TODAY)[1]


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_releases_stays_the_leads_to_start():
    assert "disable-model-invocation: true" in text("skills/releases/SKILL.md"), "releases must stay the lead's to start"


def test_releases_hands_the_lead_to_start_not_to_a_slash_command_they_must_type():
    body = text("skills/releases/SKILL.md")
    assert "Closing a session" in body, "releases must say how its session ends"
    assert "Do not run close yourself" not in body
    assert not re.search(r'[Tt]ell the user: "Run `/vela:close`', body)


# --- S26 and S43: the review digest is small, plain, once


def test_releases_leaves_the_digest_to_review():
    assert "high and blocking lines in full" not in text("skills/releases/SKILL.md")


# --- S36 to S47


def test_releases_marks_its_own_captures():
    assert "→ keep: [[" in text("skills/releases/SKILL.md"), "releases no longer marks its own captures"


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_releases_carries_its_tracer_guidance():
    releases = read("skills/releases/SKILL.md")
    for part in ("the apps it crosses", "the new contracts it crosses", "Break a tie", "if two flows each cross three apps and three new contracts", "each requirement the tracer touches",
                 "Not in this slice", "kept it all", "**Flows:** none, <reason>", "no flow page yet", "The tracer is the slice page SLC-001"):
        assert part in releases, part


def test_releases_explains_the_tracer_as_the_first_thin_path():
    # The amendment of 2026-10-13: a slice is the unit of done and the tracer is slice one, so a sentence may say both.
    text = skill_text("releases")  # the tracer is defined once, in CONVENTIONS; each skill names it the first thin path
    assert "first thin path" in text and ("Releases" in text or "Slices" in text)


def test_releases_leaves_the_tracer_definition_to_conventions():
    assert "thin path through every app" not in skill_text("releases")  # said once, in CONVENTIONS


def test_releases_opens_with_the_tracer_boundary_recorded():
    releases = read("skills/releases/SKILL.md")
    assert "the first thin path the boundary session recorded" in releases and "open with it and ask whether it is still right" in releases


def test_releases_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read("skills/releases/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence


def test_the_releases_example_matches_the_plans_bullet_format():
    text = read("skills/releases/SKILL.md")
    block = text.split("```", 2)[1]
    assert block.index("**State:**") < block.index("**Slices:** SLC-001") < block.index("| Delivers")
    assert "`**Tracer:**`, `**Not in the tracer:**`" in text  # a vault still on the releases page keeps working
    assert '`vela conventions "Slices"` gives' in text


def test_the_conversation_asks_for_names_not_codes():
    section = read("skills/releases/SKILL.md").split("3. **The first thin path (the tracer).**", 1)[1].split("4. **The next slices.**", 1)[0]
    assert not re.search(r"\b(FLO|CAP|CON|APP)-\d", section)
    for word in LINT:
        assert not re.search(rf"\b{re.escape(word)}\b", section, re.I), word


# ---- tests/test_stale_branch.py: S15 read a stale branch and said nothing was allocated (diagnosis 6B)

def test_releases_checks_freshness_first_and_stops_when_behind():
    start = SKILL.split("## 1. Start", 1)[1].split("\n\n", 2)[1]
    assert start.startswith("First run `vela freshness`. If it exits 3") and "stop, tell the lead" in start
    assert "vela session start --mode releases" in start
