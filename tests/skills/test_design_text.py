"""What the design skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

from conftest import REPO, skill_text
from test_skill_commands_exist import calls, is_a_mention, parse_error
from vela import cli

PLUGIN = REPO / "plugin"


SKILL = PLUGIN / "skills" / "design"
VOICE_LINE = re.compile(r"^.*`voice/VOICE\.md`.*references/CONVERSATION-VOICE\.md.*$", re.M)


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


def test_design_cites_only_the_start_sections_that_exist():
    # MODES once listed the design session and START once had a shell section; both went in the October 23 trim
    design = read("skills/design/SKILL.md")
    assert "A design opens no session" in design and "`docs/tech-design/<slug>.md`" in design
    assert "Shell that runs on a Mac and on Linux" not in design
    # (the START headings it cites are checked against START in test_start_text.py)


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


def test_the_self_audit_is_read_from_the_one_reference_and_the_copy_is_gone():
    """Two byte-identical copies were waiting to drift; design, its loop, frontmatter and review now point at one."""
    assert not (SKILL / "NEG-AUDIT.md").exists()
    for name in ("SKILL.md", "GRILL-LOOP.md", "FRONTMATTER-FORMAT.md", "REVIEW-CHECKPOINT.md"):
        assert "`${CLAUDE_PLUGIN_ROOT}/references/NEG-AUDIT.md`" in skill_text_design_skill(name), name
    for path in sorted((REPO / "plugin").rglob("*.md")):
        assert "design/NEG-AUDIT.md" not in path.read_text(encoding="utf-8"), path


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
    text = all_skill_text()
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


# ---- tests/test_stale_branch.py: S23 checked the handoff on a stale branch (diagnosis 6B)

def test_design_checks_freshness_first_and_stops_when_behind():
    start = read("skills/design/SKILL.md").split("## 1. Start", 1)[1]
    voice, fresh = start.split("\n\n", 3)[1:3]
    assert VOICE_LINE.search(voice)  # the voice is read before anything is said (voice audit S4)
    assert fresh.startswith("First run `vela freshness --for-lead`. If it exits 3") and "stop, say what it printed in your words" in fresh
    assert "offer to bring it up to date" in fresh and "in its words" not in fresh
    assert start.index("vela freshness") < start.index("vela handoff verify") < start.index("vela check-slice")


# --- Task 22k: the overhaul rewrite.


def test_design_loads_the_voice_before_its_first_question_and_names_house_voice():
    body = skill_text_design_skill().split("---\n", 2)[2]
    line = VOICE_LINE.search(body).group(0)
    assert line.startswith("Before your first question") and "`house-voice`" in line
    assert body.index(line) < body.index('?"') and body.index(line) < body.index("vela freshness")


def test_flow_check_line_team_side():
    body = skill_text_design_skill()
    assert "Read your app's slices' flow check from the handoff rather than running it again" in body
    assert ("If the handoff record has no `## Flow checks when written` section, run `vela check-slice <slice> --for-lead` once. "
            "If a slice is 'not fully checked' or has open findings, tell the team lead before you design against it.") in body
    assert "Until the handoff carries it" not in body


def test_design_says_states_in_words_and_team_lead_not_senior():
    body = skill_text_design_skill()
    assert '"The design is finished, with 3 known gaps. Close the gaps, redo it, or start a separate design?"' in body
    assert '"Nobody named the first working path yet, so this one is a proposal for the team lead to confirm."' in body
    assert "`# Questions the <app> team is raising with the planning lead`" in body and "items to raise with" not in body
    assert "senior" not in all_skill_text().lower()


def test_design_review_packets_come_from_the_cli():
    review = skill_text_design_skill("REVIEW-CHECKPOINT.md")
    assert "vela reviewers prepare --team" in review
    assert "| Vendors and integrations |" not in review  # the areas and their questions live in the packets


def test_design_description_is_short_and_has_no_angle_brackets():
    import yaml
    description = yaml.safe_load(skill_text_design_skill().split("---\n", 2)[1])["description"]
    assert len(description) <= 250 and "<" not in description and ">" not in description


def test_design_names_only_commands_that_exist():
    parser = cli.build_parser()
    found = [c for path in sorted(SKILL.glob("*.md")) for c in calls(path)]
    assert len(found) >= 5, found
    for line, written, argv in found:
        assert is_a_mention(parser, argv) or parse_error(parser, argv) is None, (line, written)


# ---- trim, stage 2 (lane D): what a command prints or refuses is not narrated here again

def test_design_leaves_what_the_commands_print_to_them():
    body = skill_text_design_skill()
    assert "Every file this skill names sits beside this one" not in body
    assert "records the vault commit" not in body  # TECH-DESIGN-FROM-VAULT.md and handoff verify say it
    assert "the commit stops on a choice no yes names" not in body  # vela team commit asks for the yes itself
    assert "stopped a cancel-hold flow from drawing" not in body and "never `;`" in body
    assert "Exit 1 names every diagram" not in body and "W604" not in body  # check-diagrams prints the Node.js fix


def test_design_stays_under_its_word_cap():
    assert len(skill_text_design_skill().split()) <= 1610  # 1,604 before the trim; 1,557 after


def test_a_tech_design_says_each_operations_fields_and_where_its_spec_is():
    body = (SKILL / "TECH-DESIGN-FORMAT.md").read_text(encoding="utf-8")
    assert "request and response fields" in body and "- Spec:" in body
