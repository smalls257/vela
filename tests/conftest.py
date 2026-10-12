"""Shared test helpers. Tests build broken copies of a vault in tmp_path."""
import io
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


def findings(output):
    """[(code, path)] for every finding line in check output."""
    return [(m["code"], m["path"]) for m in map(FINDING.match, output.splitlines()) if m]


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


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "browser: browser smoke tests (require Chrome; slow)")

