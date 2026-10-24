"""hook said tells Claude when the published session panel is behind the notes, and says nothing otherwise."""
import json
import subprocess
import sys

from companion_vault import SESSION, grill_session, notes, open_session, run_companion
from conftest import REPO

SCRIPT = REPO / "plugin" / "scripts" / "vela"


def said(root):
    done = subprocess.run([sys.executable, str(SCRIPT), "hook", "said"], capture_output=True, text=True,
                          input=json.dumps({"cwd": str(root), "prompt": "yes, go on", "session_id": "s1"}))
    assert done.returncode == 0
    return done.stdout


def test_nothing_is_said_before_a_panel_was_ever_published(tmp_path):
    assert said(grill_session(tmp_path)) == ""


def test_a_current_panel_is_left_alone(tmp_path):
    root = grill_session(tmp_path)
    assert run_companion(root, "session", "--html")[0] == 0
    assert said(root) == ""


def test_a_panel_two_captures_behind_is_named(tmp_path):
    root = grill_session(tmp_path)
    run_companion(root, "session", "--html")
    open_session(root, text=notes(captures=16))
    line = said(root)
    assert "2 captures behind" in line and "companion session --html" in line


def test_the_mods_json_never_sets_it_off(tmp_path):
    root = grill_session(tmp_path)
    run_companion(root, "session", "--json")
    open_session(root, text=notes(captures=16))
    assert said(root) == ""


def test_a_corrupt_marker_never_blocks_the_message_and_the_words_are_still_logged(tmp_path):
    root = grill_session(tmp_path)
    run_companion(root, "session", "--html")
    marker = root / ".vela" / "companion" / "published.json"
    data = json.loads(marker.read_text())
    data["capture"] = None
    marker.write_text(json.dumps(data))
    done = subprocess.run([sys.executable, str(SCRIPT), "hook", "said"], capture_output=True, text=True,
                          input=json.dumps({"cwd": str(root), "prompt": "yes, go on", "session_id": "s1"}))
    assert done.returncode == 0 and done.stdout == ""
    assert "couldn't tell" in done.stderr
    logs = list((root / ".vela" / "said").glob("*.log"))
    assert logs and "yes, go on" in logs[0].read_text()
