"""What the releases skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO, run, skill_text, assert_offered_then_asked
from test_releases import LINK, check, vault_with
from vela import cli, releases

SKILL = (REPO / "plugin" / "skills" / "releases" / "SKILL.md").read_text(encoding="utf-8")


def skill_example():
    """The release section the skill tells Claude to write, pointed at a requirement the fixture has."""
    block = re.search(r"## 3\. Write the confirmed slices and releases.*?```\n(.*?)```", SKILL, re.S).group(1)
    return block.replace(r"[[CAP-002-unlock-a-bike#CAP-002.FR2 Unlock with the app\|CAP-002.FR2]]", LINK)


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
    assert release.name == "Release one: March dock pilot"
    assert (release.target, release.state, release.slices) == ("2027-01-15", "assumption", ("SLC-001", "SLC-002"))
    assert [(r.requirement, r.criteria, r.note) for r in release.rows] == [("CAP-014.FR1", (1, 2), "AC3 in release two")]
    out = check(vault)
    assert not any(code in out for code in ("E340", "E341", "E342", "E344")), out


def test_the_skill_names_the_exact_header_and_the_codes_it_must_pass():
    assert "| Delivers | Criteria | Note |" in SKILL
    assert releases.HEADER == ("Delivers", "Criteria", "Note")
    for code in ("E344", "E340", "E341", "W343", "E394", "W392", "W393", "W347", "W349"):
        assert code not in SKILL  # each check's own message names its fix (rule deletion)


def test_next_offers_releases_once_allocation_is_carried_and_no_release_exists(tmp_path):
    vault = vault_with(tmp_path, "")
    for epic in (vault / "13-epics").glob("EPC-*.md"):
        epic.unlink()
    said = run("next", "--vault", str(vault), "--today", TODAY)[1]
    assert "for the whole plan: date the releases" in said, said
    (vault / "04b-releases.md").write_text(vault_with(tmp_path / "second", skill_example()).joinpath("04b-releases.md").read_text(encoding="utf-8"),
                                           encoding="utf-8")
    assert "initiative, releases" not in run("next", "--vault", str(vault), "--today", TODAY)[1]


# --- From tests/test_session_experience.py: What the skills make a lead go through (the constraints the skills put on a lead's session).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_releases_stays_the_leads_to_start():
    assert_offered_then_asked("releases")


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
    assert "**Tracer:**" not in text and "**Not in the tracer:**" not in text  # no vault is on the old releases-page tracer
    assert '`vela conventions "Slices"` gives' in text


def test_the_conversation_asks_for_names_not_codes():
    section = read("skills/releases/SKILL.md").split("3. **The first thin path (the tracer).**", 1)[1].split("4. **The next slices.**", 1)[0]
    assert not re.search(r"\b(FLO|CAP|CON|APP)-\d", section)
    for word in LINT:
        assert not re.search(rf"\b{re.escape(word)}\b", section, re.I), word


# ---- tests/test_stale_branch.py: S15 read a stale branch and said nothing was allocated (diagnosis 6B)

def test_releases_checks_freshness_first_and_stops_when_behind():
    start = SKILL.split("## 1. Start", 1)[1].split("\n\n", 3)[2]  # the paragraph after the voice line
    assert start.startswith("Then, before any other command, run `vela freshness --for-lead`. If it exits 3") and "stop, say what it printed in your words" in start
    assert "vela session start --mode releases" in start


# ---- overhaul plan Task 22f: the conversation voice first, the commands that own the lookups and the slice grammar


def voice_line(text):
    return next(p for p in text.split("\n\n") if "references/CONVERSATION-VOICE.md`" in p and "voice/VOICE.md" in p)


def test_releases_loads_the_voice_before_freshness_and_before_its_first_question():
    line = voice_line(SKILL)
    assert line.index("voice/VOICE.md") < line.index("references/CONVERSATION-VOICE.md`")
    assert "house-voice" in line  # releases writes page prose: the release opening and each slice's opening
    at = SKILL.index(line)
    assert at < SKILL.index("vela freshness"), "the lead hears freshness's news in the voice, so the voice comes first"
    assert at < SKILL.index("Ask one question at a time")
    first_command = re.search(r"`vela [a-z-]+", SKILL[SKILL.index("## 1. Start"):]).group(0)
    assert first_command == "`vela freshness"


def test_releases_says_command_output_in_its_own_words_never_the_tools():
    assert "in its words" not in SKILL and "as printed" not in SKILL
    assert "say what it printed in your words and offer to bring it up to date" in SKILL
    assert "say in one plain sentence that you couldn't check" in SKILL


def test_releases_flow_check_line_carried_as_written():
    assert ("When you've added slices or changed their After, run `vela check-slice --changed --for-lead` and tell the lead, in "
            "your words, which slices it checked and why.") in SKILL


def test_releases_names_only_commands_that_exist():
    import shlex
    parser = cli.build_parser()
    calls = re.findall(r"`vela ([a-z][^`]*)`", SKILL)
    assert {"releases brief --for-lead", "releases tracer-candidates --for-lead", "check-slice --changed --for-lead"} <= set(calls)
    for call in calls:
        argv = shlex.split(re.sub(r"<[^>]*>", "X", call).replace("^cNN", "^c01"))
        _, extras = parser.parse_known_args(argv)
        assert not extras, (call, extras)


def test_the_brief_and_add_slice_replace_the_reading_list_and_the_slice_grammar():
    assert "vela releases brief --for-lead" in SKILL and "vela releases tracer-candidates --for-lead" in SKILL
    assert "vela add slice --title" in SKILL
    # the page-by-page reading list and the hand-written slice bullets are the brief's and add slice's now
    assert "the `allocation` block (run `vela render` first)" not in SKILL
    assert "Leave `**Status:**` out" not in SKILL and "numbered with `vela next-id SLC`" not in SKILL
    assert "`→ keep: [[SLC-nnn-<slug>]] (new)`" not in SKILL  # add slice --capture writes the mark and the row


def test_releases_keeps_the_release_format_block_until_a_release_kind_exists():
    # The release format block stays: `vela apply --schema release` refuses (decision-kind-not-built), because Task 15b's
    # `release` kind was dropped. Its deletion assert belongs to the task that builds that kind.
    assert "- **Target:** 2027-01-15" in SKILL and "| Delivers | Criteria | Note |" in SKILL


def test_releases_reads_criteria_back_by_their_words_and_says_grill_lower_case():
    workshop = SKILL.split("## 2. One question at a time", 1)[1].split("## 3.", 1)[0]
    assert "list its criteria as AC1, AC2" not in workshop and "such as AC1 and AC2" not in workshop
    assert not re.search(r"\bGrill\b", SKILL)
    assert "the user" not in SKILL.split("---", 2)[2]  # the person in the room is the lead



def test_releases_says_what_to_do_with_the_ready_to_decide_hand_off():
    from conftest import REPO
    text = (REPO / "plugin/skills/releases/SKILL.md").read_text(encoding="utf-8")
    # rule deletion: MODES.md and `vela decide` itself (decide-not-in-this-session) say it; the copy here is gone
    assert "run `vela decide` on it" not in text and "ready to decide, offer the lead a short grill" not in text


def test_releases_drafts_the_paragraph_of_each_item_it_files_now():
    body = (REPO / "plugin" / "skills" / "releases" / "SKILL.md").read_text(encoding="utf-8")
    assert "Draft" in body and "paragraph" in body and "START.md" in body
    assert "Draft the paragraph when the item is filed" in body or "Draft each filed item's paragraph now" in body


# ---- trim, stage 2 and 3 (lane D): what a command enforces or prints is not said here again

def test_releases_leaves_what_the_commands_enforce_to_them():
    assert "It numbers the page, writes its bullets" not in SKILL
    assert "Only a grill decides, unless the lead overrides it" not in SKILL
    assert "A stale copy is how a releases session says nothing is allocated" not in SKILL
    assert "A bad date fails" not in SKILL and "W349 notes it" not in SKILL


def test_a_stale_branch_decision_still_names_its_fix():
    """The skill no longer pre-explains `vela decide` outside a grill; the command's refusal must carry the offer."""
    from vela.commands import decide
    import inspect
    source = inspect.getsource(decide.cannot_decide_here)
    assert "Offer the lead a short grill on it now" in source and "Nothing was decided" in source


def test_releases_stays_under_its_word_cap():
    assert len(SKILL.split()) <= 1820  # 2,041 before the trim; 1,767 after
