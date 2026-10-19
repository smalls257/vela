"""`vela record add` (overhaul Task 6b): the capture line written and numbered in code, so a deleted number is never
handed out again (two captures sharing `^c12` break every consent check that cites it)."""
import json

from conftest import run
from vela.edge import saidlog
from sharing import git, make_vault
from test_session_cli import TODAY, no_gh, reader_copy, shim, start


def add(vault, *args):
    return run("record", "add", "--vault", str(vault), *args)


def typed(vault, *messages):
    """What the person typed, as the UserPromptSubmit hook logs it."""
    for message in messages:
        saidlog.append(vault, "test-session", "2026-10-14T09:00:00Z", message)


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
    typed(vault, "A shared calendar.")
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
    typed(vault, "Yes.")
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
    typed(copy, "Hm.")
    assert add(copy, "--origin", "@reader", "--tag", "thought", '"Hm."') == (0, "^c01\n")
    assert not git_log.exists()


def test_no_origin_writes_the_leads_handle_so_the_consent_check_reads_their_yes(tmp_path, monkeypatch):
    """A capture written without --origin is the lead's: `@<handle>` from vela whoami, which is what the send's
    consent check (`consent.from_the_lead`) compares the yes with."""
    from vela import closegate
    from vela.decisions import consent
    vault = started(tmp_path, monkeypatch)
    assert run("whoami", "--vault", str(vault), "--set", "Priya-K")[0] == 0
    typed(vault, "Yes, send it.")
    assert add(vault, "--tag", "decision", '"Yes, send it."') == (0, "^c01\n")
    line = next(l for l in record_of(vault).read_text(encoding="utf-8").splitlines() if l.endswith("^c01"))
    assert line == '- [decision] (@Priya-K) "Yes, send it." ^c01'
    found = closegate.CAPTURE_RE.match(line)
    capture = closegate.Capture(found["n"], found["tag"], found["origin"], found["words"])
    assert consent.from_the_lead(capture, "priya-k") is None


def test_no_origin_and_no_known_handle_asks_once_and_writes_nothing(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)  # gh is shimmed to fail, and .vela/handle is empty
    before = record_of(vault).read_text(encoding="utf-8")
    code, output = add(vault, "--tag", "idea", "x", "--for-lead")
    assert code == 3 and "GitHub handle" in output
    assert record_of(vault).read_text(encoding="utf-8") == before


def test_help_says_origin_defaults_to_the_lead(capsys):
    run("record", "add", "--help")
    assert "Default: the lead, as @<handle> from vela whoami" in " ".join(capsys.readouterr().out.split())
