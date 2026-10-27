"""Every `vela records` subcommand run with --for-lead: none may trip the no-IDs guard (exit 2, "vela bug: a line meant
for the lead held an ID"). The plain line names no file path, branch, session slug or command; the path stays in the
default and --json output."""
import shutil

import pytest

from conftest import run
from test_session_cli import TODAY, owner, start
import session_files

OTHER = "2026-10-12-till-options"
NOTES = "---\nid: 2026-10-12-till-options\npart: 1\n---\n\n## Captures\n\n- [idea] (@lead) The till rounds up. ^c01\n"


@pytest.fixture
def started(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    shutil.rmtree(vault / "sessions" / "private")
    assert start(vault, "--mode", "dump", "--topic", "consent")[0] == 0
    return vault


def lead(*args):
    code, out = run("records", *args, "--for-lead")
    assert code != 2, out  # 2 is "vela bug: a line meant for the lead held an ID"
    assert "vela bug" not in out
    return code, out


def test_verify_when_the_notes_are_not_on_this_machine(started):
    record = f"{TODAY}-consent"
    (started / "sessions" / "private" / f"{record}.md").unlink()
    code, out = lead("verify", record, "--vault", str(started))
    assert code == 1 and "not on this machine" in out and "sessions/private" not in out
    code, detail = run("records", "verify", record, "--vault", str(started))
    assert code == 1 and f"sessions/private/{record}.md" in detail  # the path stays in the non-plain output


def test_verify_seal_and_show_in_every_state(started):
    record = f"{TODAY}-consent"
    vault = ["--vault", str(started)]
    assert lead("verify", record, *vault)[0] == 1  # not fingerprinted yet
    assert lead("seal", record, *vault)[0] == 0
    assert lead("seal", record, *vault)[0] == 0  # already fingerprinted
    assert lead("verify", record, *vault)[0] == 0
    notes = session_files.record_text(started, record)
    session_files.write_private(started, record, notes + "\n- [idea] (@lead) Changed. ^c01\n")
    assert lead("verify", record, *vault)[0] == 1
    assert lead("seal", record, *vault)[0] == 1
    assert lead("seal", "2026-10-01-nothing-here", *vault)[0] == 1
    assert lead("show", record, "^c01", *vault)[0] == 1  # no handle cached yet
    assert lead("show", record, "nonsense", *vault)[0] == 1


def test_backup_on_success_and_on_refusal(tmp_path, started):
    session_files.write_private(started, OTHER, NOTES)
    code, out = lead("backup", "--to", str(tmp_path / "keep.zip"), "--vault", str(started), "--today", TODAY)
    assert code == 0 and "Copied" in out and "keep.zip" not in out
    code, out = lead("backup", "--to", str(tmp_path / "folder"), "--vault", str(started), "--today", TODAY)
    assert code == 0, out
    assert lead("backup", "--to", str(started / "inside"), "--vault", str(started), "--today", TODAY)[0] == 1
    shutil.rmtree(started / "sessions" / "private")
    assert lead("backup", "--to", str(tmp_path / "other.zip"), "--vault", str(started), "--today", TODAY)[0] == 1


def test_split_dry_run_and_apply_refusals(started):
    assert lead("split", "--dry-run", "--vault", str(started), "--today", TODAY)[0] in (0, 3)
    assert lead("split", "--vault", str(started), "--today", TODAY)[0] in (0, 1, 3)
