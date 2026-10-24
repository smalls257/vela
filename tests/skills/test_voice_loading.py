"""Every rewritten skill still loads the voice before it talks and before it writes page prose.

The overhaul slims each skill; the voice loads are the easiest lines to lose because no check fails without them and
the session still runs, only in the model's default voice. The conversation voice is loaded once, in START.md step 0
(voice/VOICE.md first, then CONVERSATION-VOICE.md and its examples); mode skills reach it by running START's steps,
and skills that run only some of START's steps name step 0 or the files themselves. Page prose goes through
house-voice.
"""
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILLS = REPO / "plugin" / "skills"
START = REPO / "plugin" / "references" / "START.md"

RUNS_ALL_OF_START = ("grill", "epics", "boundary", "discover", "import", "dump", "shape")
RUNS_START_STEP_0 = {"challenge": "start the session (its steps 0 and 1)",
                     "voice-seed": "Run steps 0 and 1 of `${CLAUDE_PLUGIN_ROOT}/references/START.md`"}
NAMES_THE_VOICE_FILE = ("proposals", "propose", "open", "house-voice")
WRITES_PAGE_PROSE = {"discover": "SKILL.md", "import": "SKILL.md", "epics": "SKILL.md", "boundary": "PAGES.md"}


def text(skill, name="SKILL.md"):
    return (SKILLS / skill / name).read_text(encoding="utf-8")


def test_start_step_0_loads_the_owners_voice_then_the_conversation_voice():
    step = START.read_text(encoding="utf-8").split("## 0. Read how to talk", 1)[1].split("\n## ", 1)[0]
    assert "Before you say anything to the lead" in step
    assert "references/CONVERSATION-VOICE.md" in step
    assert "voice/VOICE.md" in step and step.index("voice/VOICE.md") < step.index("references/CONVERSATION-VOICE.md")


@pytest.mark.parametrize("skill", RUNS_ALL_OF_START)
def test_mode_skill_runs_starts_steps_so_it_loads_the_voice(skill):
    assert "Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md`" in text(skill)


@pytest.mark.parametrize("skill,steps", sorted(RUNS_START_STEP_0.items()))
def test_partial_start_skill_still_runs_step_0(skill, steps):
    body = text(skill)
    assert steps in body and "references/START.md" in body


@pytest.mark.parametrize("skill", NAMES_THE_VOICE_FILE)
def test_skill_outside_start_reads_the_conversation_voice_before_its_first_question(skill):
    body = text(skill)
    assert "references/CONVERSATION-VOICE.md" in body
    assert "before your first question" in body.lower()


VERBATIM_RELAY = ("in its own words", "in its words", "show the error", "show what it printed", "as it prints")


@pytest.mark.parametrize("skill", RUNS_ALL_OF_START + tuple(RUNS_START_STEP_0) + NAMES_THE_VOICE_FILE)
def test_skill_says_command_output_in_the_voice_not_verbatim(skill):
    """A relayed tool line or a raw git error skips the voice the session just loaded (voice audit, 2026-10-14)."""
    body = "\n".join(p.read_text(encoding="utf-8") for p in sorted((SKILLS / skill).glob("*.md")))
    assert not [phrase for phrase in VERBATIM_RELAY if phrase in body]


@pytest.mark.parametrize("skill,name", sorted(WRITES_PAGE_PROSE.items()))
def test_skill_that_writes_page_prose_names_house_voice(skill, name):
    assert "`house-voice`" in text(skill, name)
