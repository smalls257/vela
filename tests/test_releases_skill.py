"""/vela:releases writes the page releases.py reads; vela next offers it after allocation and before epics."""

from conftest import run
from test_releases import vault_with

TODAY = "2026-11-20"


def test_next_does_not_nag_a_vault_that_already_has_epics(tmp_path):
    vault = vault_with(tmp_path, "")
    assert "initiative, releases" not in run("next", "--vault", str(vault), "--today", TODAY)[1]
