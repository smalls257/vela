"""/planner:releases writes the page releases.py reads; planner next offers it after allocation and before epics."""
import re

from conftest import REPO, run
from planner import cli, releases
from test_releases import LINK, check, vault_with

SKILL = (REPO / "plugin" / "skills" / "releases" / "SKILL.md").read_text(encoding="utf-8")
TODAY = "2026-11-20"


def skill_example():
    """The release section the skill tells Claude to write, pointed at a requirement the fixture has."""
    block = re.search(r"## 3\. Write the confirmed releases.*?```\n(.*?)```", SKILL, re.S).group(1)
    return block.replace(r"[[CAP-002-paper-trade-a-stock#CAP-002.FR2 Place a paper order\|CAP-002.FR2]]", LINK)


def test_the_format_the_skill_writes_round_trips_through_releases_py(tmp_path):
    vault = vault_with(tmp_path, skill_example())
    found = releases.releases(cli.load_vault(vault))
    assert len(found) == 1
    release = found[0]
    assert release.name == "Release one: January board demo"
    assert (release.target, release.state) == ("2027-01-15", "assumption")
    assert [(r.requirement, r.criteria, r.note) for r in release.rows] == [("CAP-014.FR1", (1, 2), "AC3 in release two")]
    out = check(vault)
    assert not any(code in out for code in ("E340", "E341", "E342", "E344")), out


def test_the_skill_names_the_exact_header_and_the_codes_it_must_pass():
    assert "| Delivers | Criteria | Note |" in SKILL
    assert releases.HEADER == ("Delivers", "Criteria", "Note")
    for code in ("E344", "E340", "E341", "W343"):
        assert code in SKILL


def test_next_offers_releases_once_allocation_is_carried_and_no_release_exists(tmp_path):
    vault = vault_with(tmp_path, "")
    for epic in (vault / "13-epics").glob("EPC-*.md"):
        epic.unlink()
    said = run("next", "--vault", str(vault), "--today", TODAY)[1]
    assert "initiative, releases" in said, said
    (vault / "04b-releases.md").write_text(vault_with(tmp_path / "second", skill_example()).joinpath("04b-releases.md").read_text(encoding="utf-8"),
                                           encoding="utf-8")
    assert "initiative, releases" not in run("next", "--vault", str(vault), "--today", TODAY)[1]


def test_next_does_not_nag_a_vault_that_already_has_epics(tmp_path):
    vault = vault_with(tmp_path, "")
    assert "initiative, releases" not in run("next", "--vault", str(vault), "--today", TODAY)[1]
