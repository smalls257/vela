"""What the design skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO, skill_text

PLUGIN = REPO / "plugin"


SKILL = PLUGIN / "skills" / "design"


def skill_text_design_skill(name="SKILL.md"):
    return (SKILL / name).read_text(encoding="utf-8")


def section(text, heading):
    """The body of a `## heading` section, up to the next `## `."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def all_skill_text():
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(SKILL.glob("*.md")))


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_design_skill.py: /vela:design (P13, S48, S52): the plugin's design skill, the summary-first doc
# it writes, and the Heron fixture.

# --- hard requirement 3: the skill text ---------------------------------------------------------------------------


def test_the_kept_practices_are_in_the_skill():
    loop = skill_text_design_skill("GRILL-LOOP.md")
    assert "One question at a time." in loop and "*Recommended: <answer>. <one-line reason>.*" in loop
    assert "three line items, one already shipped" in loop
    order = section(loop, "The loop").split("**Check against what's known,**", 1)[1]
    assert order.index("**This conversation.**") < order.index("**The documents.**") < order.index("**The code,**")
    fm = skill_text_design_skill("FRONTMATTER-FORMAT.md")
    assert "**What we know:**" in fm and "**What would unblock:**" in fm and "**Affects:**" in fm
    assert "never reused or renumbered" in fm
    adr = skill_text_design_skill("ADR-FORMAT.md")
    assert "## Template" in adr and "All three hold" in adr and "**Reversibility cost:**" in adr
    assert "## Template" in skill_text_design_skill("TECH-DESIGN-FORMAT.md")
    assert "Start five subagents in parallel" in skill_text_design_skill("REVIEW-CHECKPOINT.md")


def test_the_self_audit_is_the_users_own_but_its_header():
    original = (REPO / "integrations" / "tech-design-grill" / "skill" / "NEG-AUDIT.md").read_text(encoding="utf-8")
    want = original.replace("## Violation Guide (from `~/.claude/CLAUDE.md`)", "## Violation Guide (the failure modes below)")
    assert want != original and skill_text_design_skill("NEG-AUDIT.md") == want


def test_the_built_in_rules_are_in_the_skill():
    skill = skill_text_design_skill()
    assert "--app APP-x" in skill and "the folder this runs in" in skill
    assert "references/TECH-DESIGN-FROM-VAULT.md" in skill and "`vela handoff verify`" in skill
    assert '"Where vela runs from"' in skill  # vela found as START.md says, so a marketplace install works
    assert "CONVERSATION-VOICE.md" in skill and "`voice/VOICE.md`" in skill and "skills/house-voice/SKILL.md" in skill
    assert "names, not codes" in skill
    walking = section(skill, "2. Start from the walking skeleton")
    assert "- **Tracer:**" in walking and "- **Not in the tracer:**" in walking and "`**Tracer:** none, <reason>`" in walking
    assert "record their words as an override" in walking and "not its coverage" in walking
    assert "`design/<slug>`" in skill and "pull request" in skill
    fmt = skill_text_design_skill("TECH-DESIGN-FORMAT.md")
    for part in ("## Summary", "**Decisions that shape it:**", "**Walking skeleton:**", "**Still open:**", "## Walking skeleton"):
        assert part in fmt
    assert "under about 120 words" in fmt and "holds `None.`" in fmt


def test_the_stop_rule_is_one_rule():
    """The old skill said "stop the session" and, two lines on, "do not stop the session"."""
    text = all_skill_text()
    assert "Hard rule" not in text and "stop the session" not in text.lower()
    vault = section(skill_text_design_skill(), "5. When the vault is wrong or silent")
    assert "carry on with every branch it doesn't touch" in vault and "`/vela:challenge <vault ID>`" in vault
    assert "carry on with the branches it doesn't touch" in skill_text_design_skill("STANDALONE.md")


def test_the_skill_names_no_dead_file_and_no_vendored_path():
    pending = {"CONVERSATION-VOICE.md"}  # being written by the conversation-voice batch; START.md will name it
    for path in SKILL.glob("*.md"):
        body = path.read_text(encoding="utf-8")
        assert ".claude/skills/vela" not in body and "to-issues" not in body and "skill 1" not in body, path.name
        for name in re.findall(r"`([A-Z][A-Z0-9-]*\.md)`", body):
            assert ((SKILL / name).exists() or (PLUGIN / "references" / name).exists() or name in {"SKILL.md", "CONTEXT.md", "AGENTS.md"}  # files of the repo the design runs in
                    or name in pending), f"{path.name} names {name}"
        for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", body):
            assert (PLUGIN / rel.rstrip(".")).exists(), f"{path.name} names {rel}"
        for rel in re.findall(r"`references/([A-Z-]+\.md)`", body):
            assert (PLUGIN / "references" / rel).exists() or rel in pending, f"{path.name} names references/{rel}"


def test_the_skill_is_written_for_current_models():
    from vela import reading
    lint = (PLUGIN / "references" / "lint-words.txt").read_text(encoding="utf-8")
    text = all_skill_text().replace((SKILL / "NEG-AUDIT.md").read_text(encoding="utf-8"), "")  # the user's own words
    for word in reading.lint_words(lint):
        assert not reading.lint_pattern(word).search(text), word
    assert "relentlessly" not in text and not re.search(r"\b(MUST|NEVER|ALWAYS|CRITICAL)\b", text)
    assert len(skill_text_design_skill().splitlines()) < 150


# --- From tests/test_tracer_skills.py: The lead-side tracer guidance (S52, step 2): present in each skill, never a
# gate, the example in the plan's format, and no codes read to the lead.


def test_design_leaves_the_tracer_definition_to_conventions():
    assert "thin path through every app" not in skill_text("design")  # said once, in CONVENTIONS


def test_design_never_makes_the_tracer_a_gate():
    for sentence in re.split(r"(?<=[.?!])\s+", read("skills/design/SKILL.md")):
        if re.search(r"tracer", sentence, re.I):
            assert not re.search(r"\b(stop|stops|refuse|refuses|block|blocks|gate)\b", sentence, re.I), sentence
