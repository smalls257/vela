"""What the explore skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

import yaml
from conftest import REPO, skill_text

PLUGIN = REPO / "plugin"


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no frontmatter"
    return yaml.safe_load(text.split("---\n", 2)[1])


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_design_skill.py: /vela:design (P13, S48, S52): the plugin's design skill, the summary-first doc
# it writes, and the Heron fixture.

# --- design as a known mode ---------------------------------------------------------------------------------------


def test_explore_says_designs_come_from_the_design_skill():
    explore = (PLUGIN / "skills" / "explore" / "ABOUT.md").read_text(encoding="utf-8")  # where designs live is product notes, read on request
    assert "from `/vela:design`" in explore


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# tech-design-grill vault mode (V1-18): read the slice, link back by ID and commit, never copy vault text.


def test_explore_opens_a_page_only_after_a_build_that_succeeded_and_writes_nothing_but_the_page_and_pins():
    explore = text("skills/explore/SKILL.md")
    assert "If the command exits 2, show its message in full, say no page was built, and stop." in explore
    assert "Never say the page is open unless the command succeeded." in explore
    assert "Nothing is written into the plugin folder." in skill_text("explore")  # product notes, in ABOUT.md, read on request
    meta = frontmatter(PLUGIN / "skills/explore/SKILL.md")
    assert "Write" not in meta["allowed-tools"].split() and "Edit" not in meta["allowed-tools"].split()


def test_every_flag_the_explore_skill_names_is_one_the_command_accepts():
    from vela import cli
    parser = cli.build_parser()
    sub = next(a for a in parser._actions if a.dest == "command").choices["explore"]
    accepted = {flag for action in sub._actions for flag in action.option_strings}
    named = set(re.findall(r"`(--[a-z]+)[ `]", text("skills/explore/SKILL.md"))) | {"-o"}
    assert named and named <= accepted, named - accepted


def test_explore_says_designs_and_plans_live_in_the_vault_docs_folder():
    explore = skill_text("explore")
    assert "`docs/tech-design/<slug>.md` (with `docs/adr/`" in explore and "team_repos" not in explore
    assert "write their own `docs/` files in the vault and never edit a vault page" in explore
    assert 'says "never edit the vault"' not in explore  # an outside skill's words go stale; say what is true here
