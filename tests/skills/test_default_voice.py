"""The default page voice (the conversational one the user picked, 2026-10-16) and what outranks it.

The Paper Tiger this guards against is a default stated in one file and quietly lost in another: the targets drift
between the skill that drafts and the copy the owner reads, the public seeds keep setting the sentences, or a vault's
own voice/VOICE.md stops winning. Each test pins one of those.
"""
import re

from conftest import REPO

SKILL = REPO / "plugin" / "skills" / "house-voice" / "SKILL.md"
DEFAULT = REPO / "plugin" / "template" / "voice" / "DEFAULT.md"
EXAMPLE_DEFAULT = REPO / "examples" / "unified-booking" / "voice" / "DEFAULT.md"
REVIEWER = REPO / "plugin" / "agents" / "voice-reviewer.md"
CONVERSATION = REPO / "plugin" / "references" / "CONVERSATION-VOICE.md"

TARGETS = {
    "Median sentence length": "10 to 16 words",
    "Three sentences in four": "22 words or fewer",
    "Contractions": "2 to 6 per 100 words",
    '"We" and "you" together': "1 to 6 per 100 words",
    "Passive sentences": "15 in 100 at most",
    "Formal linking words": "1 per 1,000 words at most",
    "Latin-rooted content words": "8% at most",
    "Reading grade (Flesch-Kincaid)": "8.5 at most",
}


def read(path):
    return path.read_text(encoding="utf-8")


def targets(text):
    return dict(re.findall(r"^\| ([^|]+?) \| ([^|]+?) \|$", text.split("| Measure | Target |", 1)[1], re.M))


def default_section():
    return read(SKILL).split("## The default voice", 1)[1].split("\n## ", 1)[0]


def test_the_owners_copy_carries_the_eight_targets_and_the_skill_no_longer_repeats_them():
    # Rule deletion (the October 23 trim): the skill's measures table is gone, so there is one copy of the numbers. The
    # owner's call: no command measures a draft against it, and the voice reviewer reads the default voice's sentences,
    # so put the table back (about 60 words) if drafts drift long.
    assert "| Measure | Target |" not in default_section()
    assert targets(read(DEFAULT)) == TARGETS


def test_the_example_vault_carries_the_template_copy_byte_for_byte():
    assert EXAMPLE_DEFAULT.read_bytes() == DEFAULT.read_bytes()


def test_the_voice_is_conversational_and_short():
    for text in (default_section(), read(DEFAULT)):
        assert "senior colleague explaining the plan across a desk" in text
        assert "no longer than" in text and "usually shorter" in text
        assert '"we"' in text and "hasn't, won't, can't" in text
        assert "No jokes" in text or "not from jokes" in text


def test_the_owners_voice_md_outranks_the_default():
    skill = read(SKILL)
    assert "wins over the default voice below and the examples" in skill
    assert skill.index("voice/VOICE.md") < skill.index("## The default voice")
    assert "A line in the owner's `voice/VOICE.md` wins over any line here" in default_section()
    owner = read(DEFAULT)
    assert "Don't edit this file to change it: put your rules in `voice/VOICE.md`" in owner
    assert "they win over every line here" in owner
    conventions = read(REPO / "plugin" / "template" / "CONVENTIONS.md")
    assert "| `voice/DEFAULT.md` |" in conventions and "edit `voice/VOICE.md` instead, which wins over it" in conventions


def test_public_seeds_set_what_a_page_covers_and_the_default_sets_the_sentences():
    """The seeds are formal published prose; matching their sentences would undo the default on every page."""
    assert "take the sentences from the default voice below" in read(SKILL)
    reviewer = read(REVIEWER)
    assert 'Judge the sentences against "The default voice"' in reviewer
    assert "never flag a paragraph for reading less formally than a seed" in reviewer


def test_the_rules_the_default_does_not_replace_stay():
    skill = read(SKILL)
    assert "don't twist them into positives" in skill and "Spell in American English" in skill
    assert "in words, not codes" in skill and "hold only a few new things at once" in skill
    owner = read(DEFAULT)
    assert "Spelling is American" in owner and "never their codes" in owner and "only a few new things" in owner


def test_a_reader_question_is_answered_not_asked():
    """The voice reviewer flags rhetorical questions, so the default answers the reader's next question as a statement."""
    assert "Say it as a statement, not as a question put to the reader" in default_section()
    assert "rhetorical questions" in read(REVIEWER)


def test_the_conversation_voice_borrows_habits_not_length():
    text = read(CONVERSATION)
    assert "may use the page voice's sentence habits" in text and "never its length" in text
    assert "| Measure | Target |" not in text


def test_the_voice_writes_only_what_the_record_holds():
    """Reason, next step, consequence, figure and absence are each written only from the record (Silent Fallback:
    the old rules pulled the model to invent a why, a next step, an 'if X then Y' or a date)."""
    for text in (default_section(), read(DEFAULT)):
        assert "the reason isn't recorded yet" in text
        assert "who's been asked" in text
        assert "only if someone said it" in text and "question for the lead" in text
        assert "no figure given yet" in text
        assert "not recorded as agreed" in text
        assert "marks decided" in text
        assert "usually why" not in text
        assert "what happens next" not in text
