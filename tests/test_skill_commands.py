"""Skill text that names the v2 commands: vela next at start, the Options considered
bullet Shape leaves and next reads, and the handoff manifest close writes."""

from conftest import REPO

PLUGIN = REPO / "plugin"


def test_no_skill_or_reference_writes_options_considered_as_a_list():
    for path in list((PLUGIN / "skills").glob("*/SKILL.md")) + list((PLUGIN / "references").glob("*.md")):
        assert '"Options considered" list' not in path.read_text(encoding="utf-8"), path


