"""What the breakdown skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO
from vela import breakdown

PLUGIN = REPO / "plugin"


BREAKDOWN = PLUGIN / "skills" / "breakdown"


def text(path):
    return path.read_text(encoding="utf-8")


LINT = [w.strip() for w in (PLUGIN / "references" / "lint-words.txt").read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]


def skill_text_breakdown_tickets_skills(folder):
    return "\n".join(text(p) for p in sorted(folder.glob("*.md")))


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_breakdown_tickets_skills.py: The text of /vela:breakdown and /vela:tickets: each kept item and
# each built-in rule is there, nothing points at a file that is not, and the plan format's own example is something
# the reader reads clean.


def test_the_kept_items_are_in_the_breakdown_skill():
    body = text(BREAKDOWN / "SKILL.md")
    assert "one question at a time with your recommendation and a one-line reason" in body
    assert "A customer cancels an order with three line items, one already shipped" in body
    assert "this conversation, then the docs, then the code" in body
    assert "what we know / what would unblock / affects" in body
    assert "IDs are never renumbered" in body or "never renumbered or reused" in body
    assert "references/NEG-AUDIT.md" in body and "Paper Tiger" in body and "Distributed Monolith" in body
    assert "PG-" in body and "continue it or start again" in body


def test_each_fix_from_the_review_and_session_18_is_in_the_breakdown_skill():
    body = text(BREAKDOWN / "SKILL.md")
    assert "word for word from the epic criterion or requirement" in body and "put every ID on the `Traces to:` line" in body
    assert "Never copy vault text" not in body and "not copied here" not in body
    assert "No IDs, no trace lines" in body  # the read-back says story names
    assert "`- **Tracer:**` bullet" in body and "`- **Not in the tracer:**`" in body and "`- **Tracer:** yes`" in body
    assert "first story is its piece of that flow" in body and "vertical slices" in body and "`Slice: layer`" in body
    assert "unblocks the most" in body and body.index("tracer stories first") < body.index("unblocks the most")
    assert "before the next release date" in body and "cannot tell" in body and "from their numbers" in body
    assert "Plan only around people the design or the vault names" in body and "asked about" in body
    assert "deferred, held or split keep every field" in body.replace("Stories deferred, held or split keep every field a built story has", "deferred, held or split keep every field")
    assert "override" in body and "Never split, merge, drop or reorder agreed stories without reading the change back" in body


def test_breakdown_reads_the_voices_through_start_and_the_conversation_voice_file():
    body = text(BREAKDOWN / "SKILL.md")
    assert "references/CONVERSATION-VOICE.md" in body and "voice/VOICE.md" in body and "references/START.md" in body
    assert "skills/house-voice/SKILL.md" in text(BREAKDOWN / "SKILL.md")


def test_breakdown_names_no_missing_plugin_file_and_no_word_the_lint_list_holds():
    folder = BREAKDOWN
    body = skill_text_breakdown_tickets_skills(folder)
    for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", body):
        rel = rel.rstrip(".")
        assert (PLUGIN / rel).exists(), f"{folder.name} names {rel}"
    for word in LINT:
        assert not re.search(rf"\b{re.escape(word)}", body, re.I), f"{folder.name} uses {word!r}"
    assert "~/.claude" not in body and "skill 1" not in body.lower() and "to-issues" not in body


def test_the_example_story_in_the_plan_format_reads_without_problems():
    body = text(BREAKDOWN / "PLAN-FORMAT.md")
    story = re.search(r"```markdown\n(### S-02.*?)```", body, re.S).group(1)
    stories, _, problems = breakdown.parse("---\nstatus: complete\n---\n\n## Summary\n| Story | Traces to | Size total | Blocked by |\n|---|---|---|---|\n"
                                           "| S-02 Switch on | CAP-005.FR1 | 1 M, 1 S | S-01 |\n\n## Stories\n\n" + story + "\n## Build order\n1. S-02: first\n")
    assert [p for p in problems if "S-02" in p and "S-01" not in p] == []
    only = stories[0]
    assert only.tracer and only.slice == "tracer" and only.done_when and only.fit.startswith("cannot tell") and len(only.criteria) == 3


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_breakdown_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read("skills/breakdown/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence
