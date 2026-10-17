"""`vela record add` (overhaul Task 6b): the capture line written and numbered in code, so a deleted number is never
handed out again (two captures sharing `^c12` break every consent check that cites it)."""
import json

from conftest import run
from sharing import git, make_vault
from test_session_cli import TODAY, no_gh, reader_copy, shim, start


def add(vault, *args):
    return run("record", "add", "--vault", str(vault), *args)


def numbered(found):
    """(exit, the first line): the capture's number. The lines after it are the topic map's (see the map tests)."""
    code, output = found
    return code, output.splitlines()[0] if output else ""


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
    assert numbered(add(vault, "--origin", "@priya", "--tag", "idea", '"A shared calendar."')) == (0, "^c01")
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
    assert numbered(add(vault, "--origin", "claude", "--tag", "idea", "four")) == (0, "^c04")


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
    assert numbered(add(vault, "--origin", "claude", "--tag", "idea", "six")) == (0, "^c06")


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
    assert numbered(add(copy, "--origin", "@reader", "--tag", "thought", '"Hm."')) == (0, "^c01")
    assert not git_log.exists()


def test_no_origin_writes_the_leads_handle_so_the_consent_check_reads_their_yes(tmp_path, monkeypatch):
    """A capture written without --origin is the lead's: `@<handle>` from vela whoami, which is what the send's
    consent check (`consent.from_the_lead`) compares the yes with."""
    from vela import closegate
    from vela.decisions import consent
    vault = started(tmp_path, monkeypatch)
    assert run("whoami", "--vault", str(vault), "--set", "Priya-K")[0] == 0
    assert numbered(add(vault, "--tag", "decision", '"Yes, send it."')) == (0, "^c01")
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


MAP = f".vela/map/{TODAY}-consent.json"


def map_of(vault):
    return json.loads((vault / MAP).read_text(encoding="utf-8"))


def test_a_tagged_capture_goes_on_the_map_and_ends_with_the_next_move(tmp_path, monkeypatch):
    """The first caller of --kind/--group: the capture is written as before, the same words go on the session's map,
    and the last line is the map's next move, so the session is steered by the call it already makes."""
    vault = started(tmp_path, monkeypatch)
    code, output = add(vault, "--origin", "@priya", "--tag", "idea", "--kind", "goals", "--kind", "money",
                       "--group", "finance", "--group", "the works council", '"Refunds paid within a day."')
    lines = output.splitlines()
    assert code == 0 and lines[0] == "^c01"
    assert lines[1] == ('map: added group finance (named 1); group the works council (named 1); '
                        'goals: "Refunds paid within a day."; money: "Refunds paid within a day."')
    assert lines[-1].startswith("next: ") and len(lines) == 3
    state = map_of(vault)
    assert [n["kind"] for n in state["notes"]] == ["goals", "money"]
    assert [g["name"] for g in state["groups"]] == ["finance", "the works council"]
    assert '"Refunds paid within a day." ^c01' in record_of(vault).read_text(encoding="utf-8")
    found = json.loads(add(vault, "--origin", "claude", "--tag", "idea", "--kind", "risks", "x", "--json")[1])
    assert found["tagged"] is True and found["next"]["move"] and found["map"] == MAP


def test_an_untagged_capture_says_the_map_cant_steer_and_writes_no_map(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    code, output = add(vault, "--origin", "@priya", "--tag", "idea", '"A shared calendar."')
    lines = output.splitlines()
    assert code == 0 and lines[0] == "^c01"
    assert lines[1].startswith("not tagged: the map can't steer from this answer (kinds: goals, people,")
    assert lines[2].startswith("next: ")
    assert not (vault / MAP).exists()
    assert json.loads(add(vault, "--origin", "claude", "--tag", "idea", "y", "--json")[1])["tagged"] is False


def test_for_lead_never_shows_the_map(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    for tags in ((), ("--kind", "goals", "--group", "finance")):
        assert add(vault, "--origin", "@priya", "--tag", "idea", *tags, '"Faster."', "--for-lead") == (
            0, "Noted in the session record.\n")


def test_two_groups_that_clash_on_a_topic_are_put_side_by_side_with_both_holders(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    add(vault, "--origin", "@priya", "--tag", "thought", "--group", "sales", "--topic", "approval speed",
        "--position", "same-day approval", '"Sales want it the same day."')
    code, output = add(vault, "--origin", "@priya", "--tag", "thought", "--group", "finance", "--topic",
                       "approval speed", "--position", "a weekly review", '"Finance review weekly."')
    assert code == 0 and output.splitlines()[-1] == (
        "next: Put these side by side on approval speed: sales wants same-day approval; finance wants a weekly "
        "review. Ask when both can't hold, then open it as a conflict naming both and ask who decides.")


def test_an_unasked_group_on_the_current_topic_comes_next(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    add(vault, "--origin", "@priya", "--tag", "thought", "--group", "legal", '"Legal will want a say."')
    code, output = add(vault, "--origin", "@priya", "--tag", "thought", "--group", "sales", "--topic", "refunds",
                       "--position", "pay at once", '"Sales want them paid at once."')
    assert output.splitlines()[-1] == "next: Ask where legal stands on refunds; not asked yet."


def test_three_waiting_items_make_the_next_move_a_summary(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    for n in range(3):
        assert run("map", "open", "--vault", str(vault), "--type", "gap", f"Open point {n}.")[0] == 0
    code, output = add(vault, "--origin", "@priya", "--tag", "idea", "--kind", "goals", '"Faster."')
    assert output.splitlines()[-1].startswith("next: 3 items wait: summarize first")


def test_a_tag_the_map_refuses_writes_neither_the_capture_nor_the_map(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    before = record_of(vault).read_text(encoding="utf-8")
    code, output = add(vault, "--origin", "@priya", "--tag", "idea", "--kind", "cash", '"Faster."')
    assert code == 1 and "kind 'cash' is not one of goals" in output
    code, output = add(vault, "--origin", "@priya", "--tag", "idea", "--group", "sales", "--position", "fast", "x")
    assert code == 1 and "needs the one --group that holds it and the --topic" in output
    assert record_of(vault).read_text(encoding="utf-8") == before and not (vault / MAP).exists()


def test_an_unreadable_map_stops_a_tagged_capture_and_is_said_under_an_untagged_one(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    (vault / MAP).parent.mkdir(parents=True, exist_ok=True)
    (vault / MAP).write_text("{broken", encoding="utf-8")
    before = record_of(vault).read_text(encoding="utf-8")
    code, output = add(vault, "--origin", "@priya", "--tag", "idea", "--kind", "goals", '"Faster."')
    assert code == 2 and "the tags weren't kept" in output and record_of(vault).read_text(encoding="utf-8") == before
    code, output = add(vault, "--origin", "@priya", "--tag", "idea", '"Faster."')
    assert code == 0 and output.splitlines()[0] == "^c01"
    assert output.splitlines()[1].startswith("not tagged: the map can't steer from this answer, and the map couldn't")


def test_record_add_and_map_add_keep_one_map_through_one_implementation(tmp_path, monkeypatch):
    """`vela map add` and `vela record add --kind` both go through topicmap.tag, so the same answer leaves the same
    map either way; and neither command module touches the map's parts directly."""
    import pathlib
    import vela.commands
    from vela import topicmap
    calls = []
    real = topicmap.tag
    monkeypatch.setattr(topicmap, "tag", lambda *a, **k: calls.append(a[3:5]) or real(*a, **k))
    vault = started(tmp_path, monkeypatch)
    add(vault, "--origin", "@priya", "--tag", "idea", "--kind", "goals", "--group", "finance", "Faster.")
    by_record = map_of(vault)
    (vault / MAP).unlink()
    run("map", "add", "--vault", str(vault), "--group", "finance")
    run("map", "add", "--vault", str(vault), "--kind", "goals", "Faster.")
    assert map_of(vault) == by_record
    assert calls == [(["goals"], ["finance"]), ([], ["finance"]), (["goals"], [])]
    folder = pathlib.Path(vela.commands.__file__).parent
    for name in ("record.py", "map.py"):
        text = (folder / name).read_text(encoding="utf-8")
        assert not any(f"topicmap.{part}(" in text for part in ("add_note", "name_group", "add_position", "set_topic"))
