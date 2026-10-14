"""What the start reference says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


PLUGIN = REPO / "plugin"


def read_override(*parts):
    return (PLUGIN.joinpath(*parts)).read_text(encoding="utf-8")


START_RULE = ("The user may override any rule in these skills. Say once, in one plain sentence and without the rule's code, what the rule protects. "
              "Then do what they asked, and record an `**Override:**` bullet (or the session's Changes row note) "
              "naming the rule and their reason. Never refuse, and never ask twice.")


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def text_of(*parts):
    return (REPO.joinpath(*parts)).read_text(encoding="utf-8")


def section_session_experience(body, heading):
    """The text under a `## heading` up to the next `## `."""
    return body.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


# --- From tests/test_answer.py: Answering a challenge: START opens an answer session on the challenge's own branch, a
# Grill (or the lead setting the item back) works there, and close pushes to that branch and comments on the open
# challenge PR instead of opening a new one.


def test_start_offers_an_answer_session():
    assert "Epics, Challenge or Answer." in read("plugin", "references", "START.md")


def test_start_answers_a_challenge_on_its_own_branch():
    start = read("plugin", "references", "START.md")
    answer = section(start, "## Answer a challenge", "## Captures during the session") + read("plugin", "references", "ANSWER-A-CHALLENGE.md")
    assert "ANSWER-A-CHALLENGE.md" in section(start, "## Answer a challenge", "## Closing a session")  # START points; the steps load only when needed
    assert 'gh pr list --search "Challenge: <ID>" --state open --json number,headRefName,title' in answer
    assert "title ends with exactly `Challenge: <ID>`" in answer
    assert "instead of `git switch main`" in answer
    assert "git switch <headRefName>" in answer and "git pull --ff-only" in answer
    assert "`<date>-answer-<id-lowercased>`" in answer
    assert "modes: [answer]" in answer and "Answer: <ID>" in answer
    assert "Do not run `git switch -c`" in answer
    assert "If none is open, or more than one, stop" in answer


def test_start_finds_an_answer_record_on_a_shared_branch():
    command = "git grep -l '^status: open' <branch> -- sessions/"
    assert command in read("plugin", "references", "START.md")


# --- From tests/test_challenge.py: /vela:challenge: a senior's challenge after handoff becomes an open unknown they
# own, which blocks the item, and a Dissent line on it.


def test_start_offers_a_challenge_session():
    assert "Epics, Challenge or Answer." in (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")


# --- From tests/test_final_fixes.py: Fixes from the final whole-branch review: each test names the failure it keeps
# out.

# 1, M6, M9, M5, M4, 7, M2, M3, README: the words the skills and template must carry


def test_checkpoint_commits_stage_by_exact_path():
    assert "by exact path, never `git add -A`" in read("plugin/references/START.md")


# --- From tests/test_final_wave.py: The last fix wave: the root README describes v2, and close, START, CONVENTIONS
# and the plugin manifest say what the code and the workflow actually do.

# M2: a suggestion to chase an unknown reaches the lead as plain words, not as the name of a skill that does not exist


def test_start_never_mentions_a_probe_skill_because_next_says_what_to_do():
    start = read("plugin", "references", "START.md").split("## 4.", 1)[1].split("## 5.", 1)[0]
    assert "probe" not in start.lower()
    assert "Ask the user whether they know the answer now" in start


# M6: the plugin manifest


def test_start_does_not_offer_to_resume_a_waiting_challenge():
    start = read("plugin", "references", "START.md")
    assert "challenge waiting for an answer" in start and "offer the \"Answer a challenge\" path" in start


# --- From tests/test_next_id.py: vela next-id: a number an open session branch already holds is never handed out
# again (UNK-026 twice, heron run).


def test_start_tries_skill_dir_first():
    """`${CLAUDE_SKILL_DIR}` is the variable both apps document expanding in skill text, so START and `vela where`
    try it before `${CLAUDE_PLUGIN_ROOT}`, and in the same order."""
    from conftest import REPO
    from vela import pluginroot
    start = (REPO / "plugin" / "references" / "START.md").read_text(encoding="utf-8")
    order = start.split("## Where vela runs from")[1].split("\n## ")[0]
    assert order.index("1. `${CLAUDE_SKILL_DIR}/../../scripts/vela`") < order.index("2. `${CLAUDE_PLUGIN_ROOT}/scripts/vela`")
    assert [c.source for c in pluginroot.candidates("/p", "/s", "/v", "")][:2] == ["${CLAUDE_SKILL_DIR}", "${CLAUDE_PLUGIN_ROOT}"]


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.

# ------------------------------------------------------------- skill text


def test_start_holds_the_shared_override_rule_and_its_hard_stops():
    start = read_override("references", "START.md")
    assert START_RULE in start
    assert "Hard stops are not process rules" in start
    for stop in ("`~/.claude`", "company material", "unless the tool printed it"):
        assert stop in start


def test_every_never_list_is_a_default_the_user_can_override_because_start_says_so_once():
    start = (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")
    assert 'every "never" and "must not" in the skills' in start and "Never refuse, and never ask twice." in start
    for doc in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        text = doc.read_text(encoding="utf-8")
        assert "These are the defaults" not in text, doc.parent.name  # said once, in START, so the copies cannot drift
        if "\n## Never\n" in text:
            section = text.split("\n## Never\n", 1)[1]
            assert not re.search(r"cannot be overridden|may not be overridden|no override", section, re.I), doc.parent.name


# --- From tests/test_reader_skills.py: Reader mode in the skill text: no git in a read copy, owner-only skills
# refuse, a reader's decisions are pending, and every skill finds the installed vela by the one order START.md states.


def test_the_resolution_order_is_stated_once_in_start():
    start = text("references/START.md")
    assert start.count("## Where vela runs from") == 1
    order = start.split("## Where vela runs from")[1].split("## ")[0]
    positions = [order.index(m) for m in ("1. `${CLAUDE_SKILL_DIR}/../../scripts/vela`", "2. `${CLAUDE_PLUGIN_ROOT}/scripts/vela`",
                                          "3. An installed copy in the plugins folder", "/synced/*/vela/scripts/vela",
                                          "4. `.claude/skills/vela/scripts/vela`", "vela_path")]
    assert positions == sorted(positions)
    assert "I cannot find the vela program. Run `/vela:where` and send me what it prints." in order


def test_start_skips_git_for_a_reader_and_still_writes_the_record():
    start = text("references/START.md")
    assert "This is a read copy, so I will not use git" in start
    assert "Session records are still written" in start
    for step in ("## 1.", "## 2.", "## 3.", "## 5."):
        assert "**Reader copy:**" in start.split(step)[1].split("\n## ")[0], step
    assert "- **Pending approval:** @<their handle>, <today>" in start


# --- From tests/test_reading_load.py: Pages a person can hold in mind: plain names in prose, IDs on a Trace line, and
# the five reading-load warnings.

# ---------------------------------------------------------------- the rule is written where sessions read it


def test_start_states_the_reading_load():
    assert "Plain names and a page a person can hold" in text_of("plugin", "references", "START.md")


# --- From tests/test_reviewers.py: The focused reviewers and the review checkpoints in the session skills.

# ------------------------------------------------------------------ close writes the ledger and proposes entries


def test_start_keeps_its_override_rule():
    start = text("references/START.md")
    assert "## The user may override any rule" in start and "Never refuse, and never ask twice." in start


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S24: close starts on the lead's word, and still confirms before anything leaves the machine


def test_start_never_starts_close_and_close_waits_for_a_yes_before_sending():
    start = section_session_experience(text("references/START.md"), "Closing a session")
    assert "Never start close" in start and "Before it does, close says what will be sent and waits for a yes" in start


# --- S27: no rule codes, raw IDs or gate names in what the lead reads


def test_start_forbids_codes_in_conversation_and_names_what_counts():
    plain = section_session_experience(text("references/START.md"), "Plain names and a page a person can hold")
    for kind in ("check codes", "gate names", "capture numbers", "copy and finding IDs", "unknowns", "capabilities",
                 "contracts", "flows", "epics", "apps", "parties", "runs"):
        assert kind in plain, kind
    assert "The lead reads names, never codes." in plain  # one definition for every kind of ID


# --- S25: record by default, ask only the few unsettled items, never the tool's own filing


def test_the_handle_is_asked_once_and_kept():
    start = text("references/START.md")
    assert ".vela/handle" in start and "never again in any skill" in start
    assert ".vela/*" in (REPO / "template" / ".gitignore").read_text(encoding="utf-8")  # so the file is never committed


# --- S36 to S47


def test_start_stages_the_explorer_pins_and_leaves_the_rest():
    start = text("references/START.md")
    assert "stage it by exact path when it changed" in start
    assert "(`findings/`, `owed/`, `pr-body*.md`, `handle`)" in start


def test_start_names_every_mode_that_marks_at_once():
    start = text("references/START.md")
    marks = start.split("Leave the mark off until close")[1].split("\n")[0]
    for name in ("Grill", "Discover", "Boundary", "Requirements", "Allocate", "Releases"):
        assert name in marks, f"START does not name {name} among the modes that mark at once"


# --- From tests/test_skill_commands.py: Skill text that names the v2 commands: vela next at start, the Options
# considered bullet Shape leaves and next reads, and the handoff manifest close writes.


def test_start_offers_vela_next_as_a_suggestion():
    start = text("references/START.md")
    assert "## 4. Offer the overdue unknowns and the next step" in start
    assert "Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela next` and show its line." in start
    assert "never a decision" in start


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# Session start, dump and close (V1-08). Each assertion pins a rule whose loss would be silent.


def test_start_stops_on_a_dirty_clone_and_says_when_main_is_old():
    start = text("references/START.md")
    assert "Never start from an old `main` without saying so." in start
    assert "add `-2`" in start
    assert "Never close a session the user has not asked to close" in start
    assert "Review comments were not checked" in start or "review comments were not checked" in start
    assert "claude, from <name>" in start


def test_start_finds_open_sessions_on_their_branches_and_ids_do_not_collide():
    start = text("references/START.md")
    assert "git branch --list 'session/*'" in start and "git branch -r --list 'origin/session/*'" in start
    assert "add `-2`, then `-3`" in start
    assert "If there is none yet, skip the merged-PR search" in start
    assert "pulls/<number>/reviews" in start
    assert "<Mode name>" in start and "Dump & Diverge" in start


# grill (V1-10)


def test_start_knows_the_grill_mark_and_its_agenda():
    start = text("references/START.md")
    assert "(decided)" in start and "## Agenda" in start


# discover and shape (V1-11). There is no probe skill: unknowns are offered at start and in MODES.md.


def test_start_says_discover_marks_its_facts():
    start = text("references/START.md")
    assert "(fact)" in start and "a Discover, which marks" in start


# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_start_never_drafts_an_ask():
    assert "Never draft an ask for the user to send, and never offer to." in text("references/START.md")


def test_no_skill_or_reference_tells_the_session_to_edit_in_place_with_sed():
    """S10: a session ran GNU-only sed on macOS. The only `sed -i` allowed in the plugin's text is one that forbids it."""
    texts = [*PLUGIN.glob("skills/*/SKILL.md"), *PLUGIN.glob("references/*.md"), *PLUGIN.glob("agents/*.md")]
    assert texts
    for path in texts:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "sed -i" in line:
                assert "Never" in line or "no `sed -i`" in line, f"{path}:{number} suggests sed -i"
    start = (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")
    assert "Edit tool" in start and "no `sed -i`" in start


# --- From tests/test_vault_title.py: S49: the first session asks for the initiative's short name once, and vela check
# warns (W718) while the vault still carries the title the template ships.


def test_the_first_session_asks_for_the_name_once_and_writes_it():
    start = (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")
    assert "**Name the initiative, once.**" in start
    paragraph = start.split("**Name the initiative, once.**", 1)[1].split("\n", 1)[0]
    assert "What short name should this initiative go by?" in paragraph
    assert "`title:` in `.vela.yaml`" in paragraph and "never ask again" in paragraph
    assert "Reader copy" in paragraph
