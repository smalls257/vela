"""Skill text that names the v2 commands: planner next at start, the Options considered
bullet Shape leaves and next reads, and the handoff manifest close writes."""
import re

from conftest import REPO, skill_text
from planner import progress
from planner.model import build
from planner.parse import parse_page

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


def test_start_offers_planner_next_as_a_suggestion():
    start = text("references/START.md")
    assert "## 4. Offer the overdue unknowns and the next step" in start
    assert "Then run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner next` and show its line." in start
    assert "never a decision" in start


def test_modes_says_where_to_start():
    modes = text("references/MODES.md")
    assert "## Where to start" in modes
    assert "`planner next` names the one app and mode" in modes and "`planner status` shows every app's stage" in modes


def test_options_considered_is_one_bullet_in_every_skill():
    assert "`**Options considered:**` bullet, at page level or under the item's heading" in skill_text("close")
    assert "`- **Options considered:** <picked option> (picked); <option>: rejected, <reason>; ...`" in skill_text("close")
    assert "`**Options considered:**` bullet naming the picked option" in text("skills/shape/SKILL.md")
    assert "written down in its `**Options considered:**` bullet" in text("skills/grill/SKILL.md")
    assert "`assumption` items with `**Options considered:**`" in text("references/MODES.md")
    for path in list((PLUGIN / "skills").glob("*/SKILL.md")) + list((PLUGIN / "references").glob("*.md")):
        assert '"Options considered" list' not in path.read_text(encoding="utf-8"), path


def test_close_writes_the_handoff_manifest_when_a_senior_takes_an_app():
    close = skill_text("close")
    assert "If this session set `handed_off:` on an app page, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner handoff <APP-id>` only now, after that commit" in close
    assert "run it with `--replace` only once they say so in this session" in close
    # S34: the manifest is written after the session's commit, so it records a clean commit, and is committed alone.
    assert close.index("planner close stage --close --session <id>") < close.index("handoff <APP-id>` only now")
    assert "Handoff manifest for <APP-id>" in close


APP = """---
id: APP-shop
type: app-building-blocks
title: Shop
state: decided
owner: "@t"
authored: mixed
change: changed
stage: target
sources: [SRC-01]
---

# Shop

### CON-001 Sale API

- **Consumers:** [[till-building-blocks|Till]]
- **Change:** new
- **State:** assumption
{options}
"""


def suggestion(options):
    page = parse_page("05-building-blocks/shop-building-blocks.md", APP.format(options=options))
    [row] = progress.grid(build([page], {"initiative": "INI-900", "title": "Mini"}), "2026-01-15")
    return row.mode, row.subject


def test_the_bullet_close_writes_is_what_planner_next_reads():
    form = re.search(r"`(- \*\*Options considered:\*\* [^`]+)`", skill_text("close")).group(1)
    filled = (form.replace("<picked option>", "versioned API").replace("<option>", "one shared schema")
              .replace("<reason>", "kiosks lag six months").replace("; ...", ""))
    assert suggestion("") == ("shape", "CON-001")
    assert suggestion(filled) == ("grill", "CON-001")
