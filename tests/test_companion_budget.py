"""Both companions finish in under 0.5 s of CPU on the 24-app synthetic vault (design, "Owner decisions"). Measured
from an installed-shape copy after one warm-up run; wall time is printed, never asserted (plan ruling 4)."""
import os

import pytest

from budget import BUDGET, installed_copy, measure
from companion_vault import stress_session


@pytest.fixture(scope="module")
def stress(tmp_path_factory):
    root = tmp_path_factory.mktemp("budget")
    return {"vault": stress_session(root), "plugin": installed_copy(root),
            "env": {**os.environ, "VELA_PYCACHE": str(root / "cache")}}


def companion(stress, *args):
    got = measure(stress["plugin"], ["companion", *args, "--vault", str(stress["vault"]), "--today", "2026-10-24"],
                  stress["env"])
    print(f"companion {' '.join(args)}: {got['cpu']:.3f} s CPU, {got['wall']:.3f} s wall")
    return got


def test_the_session_panel_is_under_budget(stress):
    got = companion(stress, "session", "--json")
    assert set(got["codes"]) == {0} and got["cpu"] < BUDGET, got


def test_the_session_panel_after_a_page_write_is_under_budget(stress):
    page = next((stress["vault"] / "06-runtime").rglob("*.md"))
    page.write_text(page.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    got = companion(stress, "session", "--json")
    assert got["cpu"] < BUDGET, got


def test_the_session_command_never_imports_the_whole_cli(stress):
    from test_fast_start import imported
    found = imported(["companion", "session", "--json", "--vault", str(stress["vault"])])
    assert "vela.cli" not in found and "vela.explorer.build" not in found
