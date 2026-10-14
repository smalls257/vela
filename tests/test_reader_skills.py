"""Reader mode in the skill text: no git in a read copy, owner-only skills refuse, a reader's decisions are pending,
and every skill finds the installed vela by the one order START.md states."""
import re

import pytest
import yaml
from conftest import REPO, run
from sharing import make_vault

PLUGIN = REPO / "plugin"
SKILLS = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
VENDORED_PROGRAM = "python3 .claude/skills/vela/scripts/vela"


def meta(path):
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---\n", 2)[1])


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_no_skill_hard_codes_the_vendored_program(path):
    assert VENDORED_PROGRAM not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_every_vela_permission_is_the_one_loose_pattern(path):
    allowed = meta(path).get("allowed-tools", "")
    assert re.findall(r"Bash\(python3 [^)]*vela[^)]*\)", allowed) in ([], ["Bash(python3 *scripts/vela *)"]), path


@pytest.fixture
def reader_copy(tmp_path):
    vault = make_vault(tmp_path)
    assert run("publish", "--vault", str(vault), "--out", str(tmp_path / "copy"), "--today", "2026-10-11")[0] == 0
    assert run("open", str(tmp_path / "copy"), "--into", str(tmp_path / "ws"), "--author", "Sam Okoye", "--today", "2026-10-12")[0] == 0
    return tmp_path / "ws"


def test_a_reader_cannot_hand_off_or_upgrade_and_is_told_whose_call_it_is(reader_copy):
    for argv in (["handoff", "APP-till"], ["upgrade"]):
        code, out = run(*argv, "--vault", str(reader_copy))
        assert code == 2 and "Priya Nair's call" in out, (argv, out)


def test_a_reader_may_still_verify_a_handoff_read_only(reader_copy):
    code, out = run("handoff", "verify", "APP-till", "--vault", str(reader_copy))
    assert "owner's job" not in out
