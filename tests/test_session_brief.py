"""The session brief's line for an exception that has ended: it is said by the item's name, with the day it ended,
so a close that no longer blocks on it does not let it go quiet (Sensor)."""
import json

from conftest import run
from sharing import make_vault
import test_close_gate

TODAY = "2026-10-20"
ENDED = "- **Override:** E318 by @priya on 2026-09-01 until 2026-10-01: the vendor tests the stock read"
RUNNING = ENDED.replace("2026-10-01: ", "2026-12-01: ")


def vault_with(tmp_path, bullet):
    vault = make_vault(tmp_path)
    page = vault / test_close_gate.STOCK
    page.write_text(page.read_text(encoding="utf-8").replace("- **Source:** SRC-01", "- **Source:** SRC-01\n" + bullet, 1),
                    encoding="utf-8")
    return vault


def test_the_brief_names_an_ended_exception(tmp_path):
    vault = vault_with(tmp_path, ENDED)
    code, out = run("session", "brief", "--vault", str(vault), "--today", TODAY, "--for-lead")
    assert "Your exception on Stock level ended on October 1, 2026: extend it, settle the item, or reopen it?" in out, out
    assert "CON-002" not in out and "E318" not in out
    code, out = run("session", "brief", "--vault", str(vault), "--today", TODAY, "--json")
    assert json.loads(out)["ended_exceptions"] == [{"on": "CON-002", "rules": ["E318"], "until": "2026-10-01"}]


def test_the_brief_is_quiet_about_an_exception_still_running(tmp_path):
    vault = vault_with(tmp_path, RUNNING)
    code, out = run("session", "brief", "--vault", str(vault), "--today", TODAY, "--json")
    assert json.loads(out)["ended_exceptions"] == []
