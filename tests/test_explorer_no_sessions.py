"""The dashboard and the reading copy do not show session records (the owner: "we don't need sessions logged in the dashboard").

    python3 -m pytest tests/test_explorer_no_sessions.py

Session records stay in the vault, and `vela check` still reads them; the Violation these tests guard against is a Leaky
Narrative: a reader of the plan shown the vault's filing system ("2026-08-12-goals-and-data") where the plan only means
"decided August 12". A decision keeps its date and its person as plain words.
"""
import json
import pathlib
import re

import pytest

from conftest import REPO, run
from vela import cli
from vela.explorer import build

import test_explorer
from test_explorer import BOOKING, DATA, built

HERON = pathlib.Path("/tmp/demo-vault")  # the Heron demo; read only


def session_marks(vault_root):
    """Every name a session record goes by: its ID, its path, and its title."""
    vault = cli.load_vault(vault_root)
    marks = []
    for s in vault.sessions:
        marks += [s.name, s.path, str(s.meta.get("title") or "")]
    return [m for m in marks if m]


def test_a_build_carries_no_session_record(tmp_path):
    page, data = built(tmp_path, BOOKING, "2026-11-20", "no-sessions")
    marks = session_marks(BOOKING)
    assert len(marks) > 10  # the example has sessions to leave out
    assert "sessions" not in data
    assert not [m for m in marks if m in page], "a session's ID, path or title is in the page"
    assert not [k for k, e in data["entities"].items() if e["kind"] == "session" or e["path"].startswith("sessions/")]
    assert not [k for k in data["reader"] if k in marks]
    assert not [r for r in data["search"]["rows"] if r["page"].startswith("sessions/")]


def test_a_decision_keeps_its_date_as_plain_words(tmp_path):
    _, data = built(tmp_path, BOOKING, "2026-11-20", "decided-on")
    carried = [w for t in data["garden"]["trees"] + data["garden"]["bare"] for w in t["carriedBy"]]
    dates = [d for w in carried for d in w["decidedOn"]]
    assert dates and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}|", d) for d in dates)
    assert "2026-08-12" in dates  # `- **Decision:** [[2026-08-12-goals-and-data]]` said so
    facts = " ".join(f["text"] + f["html"] for e in data["entities"].values() for f in e["facts"])
    assert "August 12, 2026" in facts and "goals-and-data" not in facts


def test_the_grills_say_when_and_who_never_which_session(tmp_path):
    _, data = built(tmp_path, BOOKING, "2026-11-20", "grills")
    for row in data["grills"]["rows"]:
        assert set(row["since"]) <= {"date", "kept"} and set(row["yes"]) <= {"date", "quote", "who"}


def test_the_reading_copy_carries_no_session_record(tmp_path):
    out = tmp_path / "view.html"
    code, text = run("view", "--vault", str(BOOKING), "--out", str(out), "--date", "2026-11-20", "--commit", "abc1234",
                     "--repo-url", "https://github.example/x/y")
    assert code == 0, text
    html = out.read_text(encoding="utf-8")
    marks = session_marks(BOOKING)
    assert not [m for m in marks if m in html]


@pytest.mark.skipif(not HERON.is_dir(), reason="the Heron demo vault is not at /tmp/demo-vault")
def test_the_heron_build_has_no_session_in_its_data_or_its_search_index(tmp_path):
    page, data = built(tmp_path, HERON, "2026-10-22", "heron")
    marks = session_marks(HERON)
    assert len(marks) >= 14 * 2
    blob = json.dumps(data, ensure_ascii=False)
    assert not [m for m in marks if m in blob], "a session record is in the page data"
    assert not [m for m in marks if m in json.dumps(data["search"], ensure_ascii=False)], "a session record is in the search index"
    assert not [m for m in marks if m in page]
