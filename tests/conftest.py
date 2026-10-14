"""Shared test helpers. Tests build broken copies of a vault in tmp_path."""
import io
import os
import pathlib
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "plugin" / "lib"))

MINI = REPO / "tests" / "fixtures" / "mini"
FINDING = re.compile(r"^(?P<path>[^:\n]+):(?P<line>\d+): (?P<code>[EW]\d{3}) ")


def run(*argv):
    """Run the planner CLI in-process. Returns (exit code, output text)."""
    from planner import cli
    out = io.StringIO()
    code = cli.main(list(argv), out=out)
    return code, out.getvalue()


# Findings about the example's own content that no rule under test is about: its decided items record no Why yet
# (design 20: the example carries no reasons in the lead's words, and none are invented for it), and its flows were
# drawn before the flow check's strict form, so each slice is not fully checked (W391) until a boundary redraws them.
OPEN_IN_THE_EXAMPLE = ("W390", "W391")


def findings(output, keep_open=False):
    """[(code, path)] for every finding line in check output, except those the example leaves open on purpose."""
    found = [(m["code"], m["path"]) for m in map(FINDING.match, output.splitlines()) if m]
    return found if keep_open else [f for f in found if f[0] not in OPEN_IN_THE_EXAMPLE]


def edit(path, old, new):
    """Replace `old` with `new` in a file. `old` must occur exactly once."""
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    assert count == 1, f"{old!r} occurs {count} times in {path}, expected exactly 1"
    path.write_text(text.replace(old, new), encoding="utf-8")


@pytest.fixture
def mini(tmp_path):
    """A fresh copy of the mini vault."""
    dest = tmp_path / "mini"
    shutil.copytree(MINI, dest)
    return dest


def check(vault, today="2026-01-15"):
    return run("check", "--vault", str(vault), "--today", today)


@pytest.fixture(autouse=True)
def isolate_git_config(tmp_path, monkeypatch):
    """Isolate each test from the developer's global git config by setting environment variables.
    This ensures tests don't fail under global settings like commit signing or custom hooks."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    # Clear git-related env vars that might interfere
    for var in ["GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"]:
        monkeypatch.delenv(var, raising=False)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "browser: browser smoke tests (require Chrome; slow)")



def skill_text(name):
    """A skill's SKILL.md and the files beside it that it sends the model to, read together. A rule that moved to a file
    read only at the step that needs it is still the skill's rule."""
    folder = REPO / "plugin" / "skills" / name
    parts = [(folder / "SKILL.md").read_text(encoding="utf-8")]
    parts += [path.read_text(encoding="utf-8") for path in sorted(folder.glob("*.md")) if path.name != "SKILL.md"]
    return "\n".join(parts)
