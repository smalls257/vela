"""vela companion session: what this session is about, what it decided, what's open and what's next."""
import json

import pytest

from companion_vault import SESSION, grill_session, notes, open_session, run_companion
from vela import companionsession


@pytest.fixture
def plan(tmp_path):
    return grill_session(tmp_path)


def session_json(root, *extra):
    code, out = run_companion(root, "session", "--json", *extra)
    assert code == 0, out
    return json.loads(out)


def test_decided_lists_this_sessions_rows_into_decided_by_name(plan):
    got = session_json(plan)
    assert [(d["id"], d["name"], d["from"], d["label"]) for d in got["decided"]] == [
        ("FLO-001", "Hold, pay, confirm", "assumption", "decided today"),
        ("RUN-booking", "Booking runtime", "assumption", "decided today")]
    assert got["decided"][0]["page"] == "06-runtime/flows/FLO-001-hold-pay-confirm.md"


def test_a_session_resumed_on_a_later_day_says_this_session(tmp_path):
    got = session_json(grill_session(tmp_path, opened="2026-10-22"))
    assert {d["label"] for d in got["decided"]} == {"decided this session"}


def test_a_yes_waiting_names_what_holds_it(plan):
    assert session_json(plan)["said_yes"] == [{"id": "CON-007", "name": "Tidepay payment outcome",
                                               "blocked_by": "Tidepay outcome wording", "who": "Booking senior"}]


def test_a_question_added_this_session_is_open_and_new(plan):
    opened = session_json(plan)["open"]
    assert opened[0]["id"] == "UNK-009" and opened[0]["new_this_session"] and opened[0]["who"] == "Booking senior"


def test_next_is_the_first_open_agenda_item(plan):
    assert session_json(plan)["next"] == {"text": "Pricing runtime", "id": "RUN-pricing", "source": "agenda", "left_after": 0}


def test_with_no_agenda_left_next_says_where_it_came_from(plan):
    path = plan / "sessions/private" / f"{SESSION}.md"
    path.write_text(path.read_text(encoding="utf-8").replace("status open", "status decided"), encoding="utf-8")
    assert session_json(plan)["next"]["source"] in ("map", "vela", "none")


def test_touched_names_the_pages_this_session_changed(plan):
    got = {t["page"]: t["change"] for t in session_json(plan)["touched"]}
    assert got == {"06-runtime/flows/FLO-001-hold-pay-confirm.md": "decided", "11-unknowns-and-risks.md": "new question"}


def test_the_capture_count_is_the_highest_number_in_the_notes(plan):
    assert session_json(plan)["capture"] == 14


def test_the_placeholder_summary_is_no_summary(tmp_path):
    root = grill_session(tmp_path)
    open_session(root, text=notes(summary="In progress."))
    assert session_json(root)["about"] == ""


def test_every_form_is_written_and_the_json_is_what_was_printed(plan):
    got = session_json(plan)
    folder = plan / ".vela" / "companion"
    assert json.loads((folder / "session.json").read_text(encoding="utf-8")) == got
    assert (folder / "session.md").is_file() and (folder / "session.html").is_file()
    assert not (folder / "published.json").exists()   # only --html writes the marker (ruling 10)


def test_no_session_is_said_and_an_old_panel_is_cleared(plan):
    session_json(plan)
    (plan / "sessions" / f"{SESSION}.md").unlink()
    code, out = run_companion(plan, "session", "--json")
    assert code == 1 and "No session is open in this folder." in out
    assert not (plan / ".vela" / "companion" / "session.json").exists()


def test_two_open_sessions_are_listed_not_guessed(plan):
    open_session(plan, session="2026-10-24-something-else")
    code, out = run_companion(plan, "session", "--json")
    assert code == 3 and json.loads(out)["needs_lead"]


def test_unreadable_notes_never_read_as_nothing_decided(plan):
    (plan / "sessions/private" / f"{SESSION}.md").unlink()
    code, out = run_companion(plan, "session", "--json")
    got = json.loads(out)
    assert code == 2 and got["notes"] == "unreadable" and got["decided"] is None and got["warnings"]


def test_the_core_reads_no_clock():
    meta = {"id": SESSION, "title": "Grill: x", "modes": ["grill"], "status": "open", "date": "2026-10-24"}
    got = companionsession.unreadable(meta, "missing", "2026-10-24", "09:00")
    assert got["as_of"] == "2026-10-24T09:00"


@pytest.mark.parametrize("write,companion", [(0, 1), (0, 3), (2, 0), (4, 1), (0, 0)])
def test_the_skills_suffix_gives_the_writes_exit_code_whatever_the_redraw_does(tmp_path, write, companion):
    """Runs the shell line the skill tells Claude to run, with a fake vela whose write and companion exit as told."""
    import os
    import re
    import subprocess
    from conftest import REPO
    text = (REPO / "plugin" / "skills" / "companion" / "SKILL.md").read_text(encoding="utf-8")
    suffix = re.search(r"put `([^`]*companion session --html[^`]*)` at the end", text).group(1)
    scripts = tmp_path / "plugin" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "run-vela").write_text('#!/bin/sh\nif [ "$1" = companion ]; then touch "$MARK"; exit $COMPANION_CODE; fi\nexit $WRITE_CODE\n',
                                      encoding="utf-8")
    command = "sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela decide X " + suffix
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(tmp_path / "plugin"), "WRITE_CODE": str(write), "COMPANION_CODE": str(companion),
           "MARK": str(tmp_path / "redrawn")}
    done = subprocess.run(["sh", "-c", command], cwd=tmp_path, capture_output=True, text=True, env=env)
    assert done.returncode == write
    assert (tmp_path / "redrawn").exists() == (write == 0)  # a failed write is never redrawn


def _with_rows(plan, *rows):
    open_session(plan, text=notes(extra_rows=rows))
    return session_json(plan)


def test_a_reopened_item_is_no_longer_listed_as_decided(plan):
    got = _with_rows(plan, f"| FLO-001 | decided | assumption | [[{SESSION}#^c11]] |")
    assert [d["id"] for d in got["decided"]] == ["RUN-booking"]


def test_a_question_resolved_later_in_the_session_is_not_new_and_open(plan):
    got = _with_rows(plan, f"| UNK-009 | open | resolved | [[{SESSION}#^c11]] |")
    assert not [o for o in got["open"] if o["id"] == "UNK-009" and o["new_this_session"]]


def test_an_item_decided_twice_is_listed_once(plan):
    got = _with_rows(plan, f"| FLO-001 | assumption | decided | [[{SESSION}#^c11]] |")
    assert [d["id"] for d in got["decided"]].count("FLO-001") == 1


def test_closing_a_session_panel_leaves_the_explain_panels_marker(plan):
    session_json(plan)
    marker = plan / ".vela" / "companion" / "published.json"
    marker.write_text(json.dumps({"capture": 14, "at": "x", "session": SESSION, "explain": {"view": "stuck", "at": "x"}}),
                      encoding="utf-8")
    (plan / "sessions" / f"{SESSION}.md").unlink()
    assert run_companion(plan, "session", "--json")[0] == 1
    assert json.loads(marker.read_text(encoding="utf-8")) == {"explain": {"view": "stuck", "at": "x"}}
