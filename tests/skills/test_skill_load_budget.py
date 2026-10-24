"""The trim's sensor: a skill's load stays under a budget, so the text doesn't grow back (trim strategy, Stage 4).

Every session pays for what the model reads before it acts. A rule the command already prints, restated in a skill, is
read once and fades while the command's own line comes back each time (Leaky Narrative in reverse). The trim cut that
restatement; without a budget, one well-meant sentence at a time puts it back. "Load" is a skill's SKILL.md plus the
shared references every mode skill reads first: START.md, the CONVERSATION-VOICE.md that START step 0 names, and
MODES.md when the skill names it. Branch files read only on a branch (close's LEDGER.md, grill's HANDOFF.md) don't
count. Raise a number only with a reason in the commit, and lower it when a trim lands."""
import re

from conftest import REPO

SKILLS = REPO / "plugin" / "skills"
REFERENCES = REPO / "plugin" / "references"
ALWAYS = ("START.md", "CONVERSATION-VOICE.md")
SKILL_BUDGET = 1780  # the largest skill is challenge at 1,728 words (untouched by the second trim); was 2,700
LOAD_BUDGET = 5040  # the largest load is challenge at 4,894 words; boundary is 4,764; was 6,950
SHARED_BUDGETS = {"START.md": 1270, "MODES.md": 1290, "CONVERSATION-VOICE.md": 720}  # 1,232, 1,253 and 681 words; were 1,950 and 1,900


def words(path):
    return len(path.read_text(encoding="utf-8").split())


def mode_skills():
    """The skills that open a session: they send the model to START.md first."""
    return [p for p in sorted(SKILLS.glob("*/SKILL.md")) if "references/START.md" in p.read_text(encoding="utf-8")]


def load(skill):
    text = skill.read_text(encoding="utf-8")
    named = set(re.findall(r"references/([A-Z][A-Z0-9-]+\.md)", text))
    shared = set(ALWAYS) | ({"MODES.md"} & named)
    return words(skill) + sum(words(REFERENCES / name) for name in shared)


def test_there_are_mode_skills_to_measure():
    assert len(mode_skills()) >= 10


def test_no_skill_file_grows_past_its_budget():
    over = {p.parent.name: words(p) for p in sorted(SKILLS.glob("*/SKILL.md")) if words(p) > SKILL_BUDGET}
    assert not over, f"over {SKILL_BUDGET} words: {over}"


def test_no_mode_skill_loads_past_the_budget():
    over = {p.parent.name: load(p) for p in mode_skills() if load(p) > LOAD_BUDGET}
    assert not over, f"over {LOAD_BUDGET} words with START, CONVERSATION-VOICE and MODES: {over}"


def test_the_shared_references_every_session_reads_stay_small():
    over = {name: words(REFERENCES / name) for name, cap in SHARED_BUDGETS.items() if words(REFERENCES / name) > cap}
    assert not over, over
