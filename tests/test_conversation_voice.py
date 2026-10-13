"""The conversation voice (design session 18, part A): nine rules, read by every session, with the owner's VOICE.md first."""
import re

from conftest import REPO

PLUGIN = REPO / "plugin"
VOICE = (PLUGIN / "references" / "CONVERSATION-VOICE.md").read_text(encoding="utf-8")
START = (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")
MODE_SKILLS = ("grill", "shape", "boundary", "discover", "dump", "requirements", "allocate", "releases", "epics",
               "challenge", "close", "import")
COPIES = ("template", "plugin/vault", "examples/unified-booking", "tests/stub-conventions")


def skill(name):
    return (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_the_conversation_voice_has_nine_rules_as_sentences():
    rules = re.findall(r"^(\d+)\. \*\*", VOICE, re.M)
    assert rules == [str(n) for n in range(1, 10)]
    assert "For what's ahead, picture a specific moment" in VOICE and "don't record a guess as a fact" in VOICE
    assert "assumed, decided or open" in VOICE
    assert "Play back the lead's words, not yours" in VOICE


def test_examples_lead_and_voice_md_comes_first():
    assert "The examples lead" in VOICE
    assert "voice/examples/conversation/*.md" in VOICE and "voice/local/conversation/*.md" in VOICE
    assert "`state: active`" in VOICE and "file-name order" in VOICE
    assert VOICE.index("voice/VOICE.md") < VOICE.index("voice/examples/conversation")
    house = skill("house-voice")
    assert "`voice/VOICE.md`, read it first" in house
    assert house.index("voice/VOICE.md") < house.index("Read every example of that type")


def test_start_reads_the_conversation_voice_before_the_first_question():
    step = START.split("## 6. Read how to talk", 1)[1].split("\n## ", 1)[0]
    assert "references/CONVERSATION-VOICE.md" in step and "voice/VOICE.md" in step
    assert START.index("## 5. Open the record") < START.index("## 6. Read how to talk")


def test_every_mode_skill_reaches_the_conversation_voice():
    for name in MODE_SKILLS:
        text = skill(name)
        assert "references/START.md" in text, name
        if name == "challenge":  # runs chosen steps only
            assert "Run steps 1, 2, 5 and 6 of" in text
        elif name == "close":
            assert "CONVERSATION-VOICE.md" in text
        elif name in ("epics", "import"):
            assert re.search(r"Run the steps in `\$\{CLAUDE_PLUGIN_ROOT\}/references/START.md`", text), name
        else:
            assert "Run the steps in `${CLAUDE_PLUGIN_ROOT}/references/START.md`" in text, name


def test_no_skill_tells_the_lead_a_code():
    assert "W324" not in skill("grill").split("Tell the user the owner confirms later", 1)[1].split("\n", 1)[0]
    assert "without the code" in skill("challenge")


def test_voice_seed_knows_the_conversation_type_and_the_owners_own_rules():
    seed = skill("voice-seed")
    assert "conversation" in seed.split("---", 2)[1]
    assert "VX-conversation-NNN.md" in seed
    assert "The conversation type" in seed and "2 or 3 exchanges" in seed
    assert "voice/VOICE.md" in seed and "never invented by you" in seed
    assert "Never invent a rule for `voice/VOICE.md`" in seed


def test_conventions_lists_the_type_and_voice_md_in_every_copy():
    texts = [(REPO / d / "CONVENTIONS.md").read_text(encoding="utf-8") for d in COPIES]
    assert len(set(texts)) == 1
    assert "`conversation` for how sessions talk to the lead" in texts[0]
    assert "`voice/VOICE.md` is optional" in texts[0] and "Both voices read it first" in texts[0]


def test_the_new_instructions_name_no_listed_word():
    from planner import reading
    words = reading.lint_words((PLUGIN / "references" / "lint-words.txt").read_text(encoding="utf-8"))
    for text in (VOICE, skill("voice-seed"), skill("house-voice")):
        for word in words:
            assert not reading.lint_pattern(word).search(text.replace("lint-words.txt", "")), word


def test_the_guide_explains_both_voices():
    guide = (REPO / "docs" / "GUIDE.md").read_text(encoding="utf-8")
    assert "### Two voices, and how to set yours" in guide and "voice/VOICE.md" in guide
