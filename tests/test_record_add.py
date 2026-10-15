"""`vela record add` (overhaul Task 6b): the capture line written and numbered in code, so a deleted number is never
handed out again (two captures sharing `^c12` break every consent check that cites it)."""
import json

from conftest import run
from sharing import git, make_vault
from test_session_cli import TODAY, no_gh, reader_copy, shim, start


def add(vault, *args):
    return run("record", "add", "--vault", str(vault), *args)


def record_of(vault):
    return vault / "sessions" / f"{TODAY}-consent.md"


def started(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    no_gh(tmp_path, monkeypatch)
    code, output = start(vault, "--mode", "dump", "--topic", "consent")
    assert code == 0, output
    return vault


def test_add_appends_numbered_lines_and_prints_the_number(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    assert add(vault, "--origin", "@priya", "--tag", "idea", '"A shared calendar."') == (0, "^c01\n")
    code, output = add(vault, "--origin", "claude", "--tag", "worry", "The calendar may be private.", "--json")
    assert code == 0 and json.loads(output)["number"] == "^c02"
    text = record_of(vault).read_text(encoding="utf-8")
    assert '- [idea] (@priya) "A shared calendar." ^c01\n- [worry] (claude) The calendar may be private. ^c02\n' in text


def test_capture_numbers_never_reused_after_delete(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    for words in ("one", "two", "three"):
        assert add(vault, "--origin", "claude", "--tag", "idea", words)[0] == 0
    path = record_of(vault)
    path.write_text(path.read_text(encoding="utf-8").replace("- [idea] (claude) three ^c03\n", ""), encoding="utf-8")
    assert add(vault, "--origin", "claude", "--tag", "idea", "four") == (0, "^c04\n")


def test_a_number_only_git_remembers_is_not_reused(tmp_path, monkeypatch):
    """Another machine, no `.vela/session.json`: the record's history still knows ^c05 was used."""
    vault = started(tmp_path, monkeypatch)
    path = record_of(vault)
    body = path.read_text(encoding="utf-8")
    path.write_text(body.replace("## Captures\n\n", "## Captures\n\n- [idea] (claude) five ^c05\n", 1),
                    encoding="utf-8")
    git(vault, "commit", "-q", "-am", f"Checkpoint {TODAY}-consent")
    path.write_text(body, encoding="utf-8")
    git(vault, "commit", "-q", "-am", f"Checkpoint {TODAY}-consent")
    (vault / ".vela" / "session.json").unlink()
    assert add(vault, "--origin", "claude", "--tag", "idea", "six") == (0, "^c06\n")


def test_mark_written_at_once(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    mark = "keep: [[shop-building-blocks#CON-001 Orders|CON-001]] (decided)"
    assert add(vault, "--origin", "@priya", "--tag", "decision", '"Yes."', "--mark", mark)[0] == 0
    assert f'- [decision] (@priya) "Yes." → {mark} ^c01\n' in record_of(vault).read_text(encoding="utf-8")


def test_no_open_record_exits_1(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    code, output = add(vault, "--origin", "claude", "--tag", "idea", "x")
    assert (code, output) == (1, "No session is open, so there's no record to add the note to.\n")


def test_a_line_that_would_not_parse_is_refused(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    code, output = add(vault, "--origin", "a (b)", "--tag", "idea", "x")
    assert code == 1 and "origin" in output
    assert "^c" not in record_of(vault).read_text(encoding="utf-8").split("## Captures", 1)[1].split("## Changes")[0]


def test_reader_copy_adds_without_git(tmp_path, monkeypatch):
    copy = reader_copy(tmp_path)
    git_log = shim(tmp_path, monkeypatch, "git")
    no_gh(tmp_path, monkeypatch)
    assert start(copy, "--mode", "dump", "--topic", "consent")[0] == 0
    assert add(copy, "--origin", "@reader", "--tag", "thought", '"Hm."') == (0, "^c01\n")
    assert not git_log.exists()
