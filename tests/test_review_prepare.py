"""`vela reviewers prepare` and `vela questions --digest --session` (overhaul Task 20).

REVIEW sections 1 and 2 were lists and lookups the model walked by hand (pages per reviewer, the ledger's line limit,
which areas to skip, the checkpoint's number); the digest's "never twice" was bookkeeping it kept in its head. Both
are counting, so both are code, and the digest's memory is a committed record line so it survives a second machine."""
import json
import shutil

from conftest import MINI, run
from sharing import git, make_vault
from test_session_cli import TODAY, no_gh, start
import session_files

LEDGER = "11-unknowns-and-risks.md"
RECORD_ID = f"{TODAY}-consent"
RECORD = f"sessions/private/{RECORD_ID}.md"  # the notes: what a reviewer reads and the checkpoint is written to


def started(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    no_gh(tmp_path, monkeypatch)
    code, output = start(vault, "--mode", "dump", "--topic", "consent")
    assert code == 0, output
    return vault


def prepare(vault, *args):
    code, out = run("reviewers", "prepare", "--vault", str(vault), "--today", TODAY, "--json", *args)
    return code, json.loads(out) if out.strip().startswith("{") else out


def packets(answer):
    return {p["area"]: p for p in answer["packets"]}


def test_skipped_area_reported_with_reason(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    assert run("record", "add", "--vault", str(vault), "--origin", "Priya", "--tag", "idea", "A shared till.")[0] == 0
    code, answer = prepare(vault, "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md")
    assert code == 0, answer
    assert answer["checkpoint"] == 1 and answer["first_finding"] == "F1.1"
    assert [s["area"] for s in answer["skipped"]] == ["PTN"], "the mini vault owes nothing about partners"
    assert "nothing is owed" in answer["skipped"][0]["reason"]
    assert sorted(packets(answer)) == ["DAT", "FIN", "OPS", "REG"]
    assert not (vault / ".vela" / "review" / "1" / "PTN.md").exists()
    assert answer["merge"].endswith(" --areas FIN,DAT,REG,OPS --skipped PTN")
    # the notes are never committed, and nothing else changed, so there is no checkpoint commit
    assert git(vault, "log", "-1", "--format=%s") == f"Open session {TODAY}-consent"
    assert git(vault, "ls-files", "sessions/private") == "" and answer["commit"] is None
    assert prepare(vault, "--checkpoint", "again", "--focus", "01-goals.md")[1]["commit"] is None, \
        "nothing new written, nothing committed"


def test_ledger_page_line_limit_written(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    limit = next(n for n, line in enumerate((vault / LEDGER).read_text(encoding="utf-8").split("\n"), 1)
                 if line == "## Question ledger") - 1
    code, answer = prepare(vault, "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md")
    assert code == 0, answer
    fin = packets(answer)["FIN"]
    assert f"{LEDGER}, lines 1 to {limit}" in fin["pages"]
    text = (vault / fin["packet"]).read_text(encoding="utf-8")
    assert f"- {LEDGER}, lines 1 to {limit}\n" in text
    assert f"Questions file: {fin['questions_file']}" in text
    assert json.loads((vault / fin["questions_file"]).read_text(encoding="utf-8"))["copies"], "the area's questions"
    assert RECORD in fin["pages"] and "sessions/2026-01-10-shop-api.md" not in fin["pages"], \
        "never an earlier session's record"


def test_changed_page_carries_only_its_changed_lines(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    page = vault / LEDGER
    lines = page.read_text(encoding="utf-8").split("\n")
    lines[29] = lines[29] + " Changed this session."
    page.write_text("\n".join(lines), encoding="utf-8")
    code, answer = prepare(vault, "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md")
    assert code == 0, answer
    assert f"{LEDGER}:30-30" in answer["changed"].split(",")
    assert git(vault, "status", "--porcelain", "--", LEDGER) == "", "the changed page is committed with the record"


def test_rerun_numbers_checkpoint_n_plus_1(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    session_files.edit_record(
        vault, RECORD_ID, "## Changes",
        "## Reviews\n\n### 1. after the pre-mortem, 2026-10-14\n\n- **Coverage:** FIN found 1\n\n## Changes")
    code, answer = prepare(vault, "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md",
                           "--rerun", "1", "--areas", "FIN,REG")
    assert code == 0, answer
    assert answer["checkpoint"] == 2 and answer["first_finding"] == "F2.1" and answer["rerun_of"] == 1
    assert answer["heading"] == f"### 2. Re-run of checkpoint 1: FIN, REG, {TODAY}"
    assert sorted(packets(answer)) == ["FIN", "REG"] and answer["skipped"] == []
    assert answer["merge"].startswith(f"vela findings merge .vela/findings/{TODAY}-consent/2 --changed ")
    assert answer["merge"].endswith(" --areas FIN,REG")
    assert git(vault, "log", "-1", "--format=%s") == f"Open session {TODAY}-consent"


def test_rerun_of_a_checkpoint_the_record_lacks_is_refused(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    code, out = prepare(vault, "--checkpoint", "x", "--focus", "01-goals.md", "--rerun", "3", "--areas", "FIN")
    assert code == 2 and "checkpoint 3" in json.dumps(out)


def test_team_checkpoint_packets(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(MINI, root)
    (root / "docs" / "tech-design").mkdir(parents=True)
    (root / "docs" / "tech-design" / "till.md").write_text("# Till design\n", encoding="utf-8")
    (root / "CONTEXT.md").write_text("# Context\n", encoding="utf-8")
    code, answer = prepare(root, "--team", "--checkpoint", "design review", "--focus", "docs/tech-design/till.md",
                           "CONTEXT.md")
    assert code == 0, answer
    assert [p["label"] for p in answer["packets"]] == ["Vendors and integrations", "Data and licensing",
                                                      "Failure and recovery", "Security", "Operations"]
    assert answer["checkpoint"] is None and answer["merge"] is None
    text = (root / answer["packets"][0]["packet"]).read_text(encoding="utf-8")
    assert "- docs/tech-design/till.md\n- CONTEXT.md\n" in text and "at most 8 findings" in text
    assert "rate limits" in text


def test_team_focus_page_must_exist(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(MINI, root)
    code, out = prepare(root, "--team", "--checkpoint", "design review", "--focus", "docs/none.md")
    assert code == 2 and "docs/none.md" in json.dumps(out)


def test_for_lead_says_the_skipped_angle_without_a_code(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    code, out = run("reviewers", "prepare", "--vault", str(vault), "--today", TODAY, "--for-lead",
                    "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md")
    assert code == 0, out
    assert "partners" in out.lower() and "PTN" not in out


def test_reader_copy_runs_no_git_and_commits_nothing(tmp_path, monkeypatch):
    from test_session_cli import shim
    copy = tmp_path / "copy"
    shutil.copytree(MINI, copy)
    (copy / ".vela").mkdir()
    (copy / ".vela" / "workspace.json").write_text('{"role": "reader"}', encoding="utf-8")
    shutil.copytree(MINI, copy / ".vela" / "baseline")
    from vela import privaterecord
    title = "Dump & Diverge: consent"
    (copy / "sessions" / f"{RECORD_ID}.md").write_text(privaterecord.new_stub(RECORD_ID, title, TODAY, ["dump"]),
                                                       encoding="utf-8")
    session_files.write_private(copy, RECORD_ID, privaterecord.new_private(RECORD_ID, title, TODAY, 1))
    git_log = shim(tmp_path, monkeypatch, "git")
    code, answer = prepare(copy, "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md")
    assert code == 0, answer
    assert answer["reader_copy"] is True and answer["commit"] is None
    assert RECORD in answer["changed"].split(",")
    assert not git_log.exists() or git_log.read_text(encoding="utf-8") == ""


# ------------------------------------------------------------------ the digest, never twice

def digest(vault, *extra):
    code, out = run("questions", "--vault", str(vault), "--digest", "--json", *extra)
    assert code == 0, out
    return json.loads(out)


def copies_of(answer):
    return [c for g in answer["groups"] for c in g["copies"]]


def test_digest_never_shows_a_line_twice(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    every = copies_of(digest(vault))
    first = digest(vault, "--session", f"{TODAY}-consent")
    second = digest(vault, "--session", f"{TODAY}-consent")
    assert len(first["groups"]) == 3 and first["held"] == len(digest(vault)["groups"]) - 3
    assert not set(copies_of(first)) & set(copies_of(second)), "a line shown once is not shown again"
    shown = []
    for _ in range(10):
        shown += copies_of(digest(vault, "--session", f"{TODAY}-consent"))
    assert sorted(copies_of(first) + copies_of(second) + shown) == sorted(every), "and none is lost"
    assert digest(vault, "--session", f"{TODAY}-consent")["groups"] == []


def test_digest_skips_a_copy_a_capture_already_took(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    top = digest(vault)["groups"][0]["copies"][0]
    code, out = run("record", "add", "--vault", str(vault), "--origin", "Priya", "--tag", "thought",
                    f"{top}: ruled out, the shop holds no customer data")
    assert code == 0, out
    assert top not in copies_of(digest(vault, "--session", f"{TODAY}-consent"))


def test_digest_shown_line_written_to_record(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    first = digest(vault, "--session", f"{TODAY}-consent")
    text = session_files.record_text(vault, RECORD_ID)
    line = f"Digest shown: {', '.join(copies_of(first))}"
    assert f"## Reviews\n\n{line}\n\n## Changes" in text
    second = digest(vault, "--session", f"{TODAY}-consent")
    text = session_files.record_text(vault, RECORD_ID)
    assert text.count("Digest shown:") == 1
    assert f"Digest shown: {', '.join(copies_of(first) + copies_of(second))}\n" in text
    # a second machine has only the record: the line is read back from it
    (vault / ".vela" / "session.json").unlink()
    assert not set(copies_of(digest(vault, "--session", f"{TODAY}-consent"))) & set(copies_of(first))


def test_digest_line_sits_above_the_checkpoints(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    session_files.edit_record(
        vault, RECORD_ID, "## Changes",
        "## Reviews\n\n### 1. after the pre-mortem, 2026-10-14\n\n- **Coverage:** x\n\n## Changes")
    digest(vault, "--session", f"{TODAY}-consent")
    text = session_files.record_text(vault, RECORD_ID)
    assert text.index("Digest shown:") < text.index("### 1. after the pre-mortem")
    code, answer = prepare(vault, "--checkpoint", "next", "--focus", "01-goals.md")
    assert answer["checkpoint"] == 2, "the bare line is not a checkpoint"


def test_digest_text_with_session_names_what_is_held(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    code, out = run("questions", "--vault", str(vault), "--digest", "--session", f"{TODAY}-consent")
    assert code == 0, out
    assert out.splitlines()[1].startswith("1. ") and "more are written down" in out


def test_digest_session_must_name_a_record(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    code, out = run("questions", "--vault", str(vault), "--digest", "--session", "no-such-session")
    assert code == 2 and "no-such-session" in out


def test_digest_without_session_unchanged(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    before = session_files.record_text(vault, RECORD_ID)
    plain = run("questions", "--vault", str(vault), "--digest")
    assert plain == run("questions", "--vault", str(vault), "--digest")
    assert "held" not in digest(vault)
    digest(vault, "--session", f"{TODAY}-consent")
    assert run("questions", "--vault", str(vault), "--digest") == plain, "a session's memory never filters the plain digest"
    assert session_files.record_text(vault, RECORD_ID) != before
