"""What the explore skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re

import yaml
from conftest import REPO, skill_text
from test_skill_commands_exist import calls, is_a_mention, parse_error
from vela import cli

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
    assert "If the command exits 2, say in a plain sentence what stopped it, that no page was built, and stop." in explore
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


# --- Task 22k: explore relays `vela explore --for-lead` instead of translating each kind of build line itself.

EXPLORE = PLUGIN / "skills" / "explore" / "SKILL.md"
VOICE_LINE = re.compile(r"^.*`voice/VOICE\.md`.*references/CONVERSATION-VOICE\.md.*$", re.M)


def test_explore_builds_with_for_lead_and_the_build_report_list_is_gone():
    explore = text("skills/explore/SKILL.md")
    assert "## What the build reports" not in explore
    for line in ("first build: wrote the pinned positions", "vela check reports it as E105", "asks for icon:"):
        assert line not in explore, line
    steps = explore.split("## Steps", 1)[1]
    assert steps.index("vela explore --for-lead") < steps.index("vela explore --serve")
    assert "without `--for-lead`" in steps  # the command refuses --serve with --for-lead
    assert "answer first" in steps and "about four things at most" in steps


def test_explore_loads_the_voice_before_it_says_anything():
    body = EXPLORE.read_text(encoding="utf-8").split("---\n", 2)[2]
    line = VOICE_LINE.search(body).group(0)
    assert body.index(line) < body.index("## Steps")


def test_explore_about_says_it_plainly():
    about = text("skills/explore/ABOUT.md")
    assert "The question box can read the plan but can't change it." in about
    assert "The file works offline and doesn't load anything from the internet." in about
    assert "headless" not in about and "Web Audio" not in about and "senior" not in about


def test_explore_description_is_short_and_has_no_angle_brackets():
    description = frontmatter(EXPLORE)["description"]
    assert len(description) <= 250 and "<" not in description and ">" not in description


def test_explore_names_only_commands_that_exist():
    parser = cli.build_parser()
    found = list(calls(EXPLORE)) + list(calls(PLUGIN / "skills" / "explore" / "ABOUT.md"))
    assert len(found) >= 3, found
    for line, written, argv in found:
        assert is_a_mention(parser, argv) or parse_error(parser, argv) is None, (line, written)
