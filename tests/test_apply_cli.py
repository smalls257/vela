"""`vela apply` (overhaul Task 4) against a real vault folder: all or nothing, a second apply is a no-op, a reader copy
runs no git, and `--schema` prints what a kind takes. Exercised with a test-only kind, never a shipped one."""
import json
import os
import shutil
import stat
import sys
import types

import pytest

from conftest import MINI, run
from vela import say
from vela.edge import sessiongit
from vela.decisions import consent, schema
import session_files

RECORD_ID = "2026-10-20-grill-stock"
STOCK = "05-building-blocks/stock-building-blocks.md"
SHOP = "05-building-blocks/shop-building-blocks.md"
CAPTURES = ["- [readback] (claude) I read back two notes for the stock and shop pages ^c30",
            '- [answer] (@priya) "Yes, file both as read." ^c31',
            '- [answer] (@priya) "ok" ^c32']


def note_validate(item, vault, record):
    found = []
    if vault.text(item["page"]) is None:
        found.append(say.Refusal("note-page", "I can't find that page.", "Point the note at a page that exists.",
                                 "none: a note needs a page"))
    refusal = consent.a_yes(item["yes"], record)
    return found + ([refusal] if refusal else [])


def note_apply(item, vault, record):
    text = vault.text(item["page"])
    return [schema.Write(item["page"], text.rstrip("\n") + "\n\n" + item["line"] + "\n")]


@pytest.fixture
def note_kind(monkeypatch):
    """A kind that appends a line to a page when the lead said yes: test-only, registered from the test."""
    kind = types.ModuleType("vela.decisions.note")
    kind.SCHEMA = schema.KindSchema(
        fields={"page": "the page to add the note to", "line": "the note, as it goes on the page",
                "yes": "the capture holding the lead's yes"},
        judgment=("yes",), required=("page", "line", "yes"),
        example={"page": STOCK, "line": "A note.", "yes": "^c31"})
    kind.validate, kind.apply = note_validate, note_apply
    monkeypatch.setitem(sys.modules, "vela.decisions.note", kind)
    monkeypatch.setattr(schema, "KINDS", schema.KINDS + ("note",))
    return kind


def vault_with_record(tmp_path, captures=CAPTURES):
    root = tmp_path / "vault"
    shutil.copytree(MINI, root)
    lines = ["---", f"id: {RECORD_ID}", "type: session", "date: 2026-10-20", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", "", "## Captures", "", *captures, ""]
    session_files.write_record(root, RECORD_ID, "\n".join(lines) + "\n")
    return root


def decision_file(root, items, kind="note", session=RECORD_ID):
    path = root / ".vela" / "decisions" / session / f"01-{kind}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "kind": kind, "session": session, "items": items}), encoding="utf-8")
    return path


def good(page=STOCK, line="Stores count stock nightly.", yes="^c31"):
    return {"page": page, "line": line, "yes": yes}


def snapshot(root):
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".vela" not in p.parts}


def apply(root, path, *flags):
    return run("apply", str(path), "--vault", str(root), *flags)


def test_a_valid_file_writes_every_page(tmp_path, note_kind):
    root = vault_with_record(tmp_path)
    path = decision_file(root, [good(), good(page=SHOP, line="Shop reads it.")])
    code, out = apply(root, path)
    assert code == 0, out
    assert "Stores count stock nightly." in (root / STOCK).read_text(encoding="utf-8")
    assert "Shop reads it." in (root / SHOP).read_text(encoding="utf-8")
    applied = json.loads(path.read_text(encoding="utf-8"))["applied"]
    assert len(applied["pages"]) == 64 and applied["captures"] == 3


def test_invalid_item_writes_nothing(tmp_path, note_kind):
    root = vault_with_record(tmp_path)
    path = decision_file(root, [good(), good(page=SHOP, yes="^c32")])  # the second is a bare "ok"
    before, file_before = snapshot(root), path.read_bytes()
    code, out = apply(root, path, "--json")
    assert code == 1, out
    assert snapshot(root) == before and path.read_bytes() == file_before
    refusals = json.loads(out)["refusals"]
    assert [r["plain"] for r in refusals] == ["You said 'ok'. Is that a yes?"]


def test_refusal_has_plain_fix_and_override(tmp_path, note_kind):
    root = vault_with_record(tmp_path)
    path = decision_file(root, [good(yes="^c99")])
    code, out = apply(root, path, "--json")
    assert code == 1
    (refusal,) = json.loads(out)["refusals"]
    assert set(refusal) == {"refused", "rule", "plain", "fix", "override", "audience", "recommend"}
    assert refusal["refused"] is True and refusal["audience"] == "lead"
    assert all(refusal[k] for k in ("rule", "plain", "fix", "override"))
    code, out = apply(root, path, "--for-lead")
    assert code == 1 and out.strip().splitlines() == ["I don't have your answer written down yet, so I haven't filed it.",
                                                consent.WAIVE_YES]


def test_reapply_is_noop(tmp_path, note_kind):
    root = vault_with_record(tmp_path)
    path = decision_file(root, [good()])
    assert apply(root, path)[0] == 0
    after, file_after = snapshot(root), path.read_bytes()
    code, out = apply(root, path)
    assert code == 0 and "already applied" in out
    assert snapshot(root) == after and path.read_bytes() == file_after


def test_capture_text_changed_since_draft_refused(tmp_path, note_kind):
    root = vault_with_record(tmp_path)
    rec, _ = sessiongit.open_record(root)
    path = decision_file(root, [schema.seal(good(), rec, ["^c31"])])
    session_files.edit_record(root, RECORD_ID, "file both as read", "file only stock")
    before = snapshot(root)
    code, out = apply(root, path, "--for-lead")
    assert code == 1 and "the answer changed since i wrote this down" in out.lower()
    assert snapshot(root) == before


def test_unknown_kind_refused_plainly(tmp_path):
    root = vault_with_record(tmp_path)
    path = decision_file(root, [{"to": "decided"}], kind="allocate")
    code, out = apply(root, path, "--for-lead")
    assert code == 1 and out.strip() == "I can't file that kind of decision yet."


def test_file_for_another_session_refused(tmp_path, note_kind):
    root = vault_with_record(tmp_path)
    path = decision_file(root, [good()], session="2026-10-01-other")
    before = snapshot(root)
    code, out = apply(root, path, "--json")
    assert code == 1 and json.loads(out)["refusals"][0]["rule"] == "decision-session"
    assert snapshot(root) == before


def test_no_open_session_refused(tmp_path, note_kind):
    root = tmp_path / "vault"
    shutil.copytree(MINI, root)
    path = decision_file(root, [good()])
    code, out = apply(root, path, "--for-lead")
    assert code == 1 and "No session is open" in out


def test_unreadable_file_is_a_tool_failure(tmp_path):
    root = vault_with_record(tmp_path)
    code, out = apply(root, root / ".vela" / "decisions" / "missing.json")
    assert code == 2 and "vela apply" in out


@pytest.fixture
def failing_git(tmp_path, monkeypatch):
    """A `git` on PATH that records any call and fails, so a test sees git was never run."""
    shim = tmp_path / "shim"
    shim.mkdir()
    marker = tmp_path / "git-was-called"
    script = shim / "git"
    script.write_text(f"#!/bin/sh\necho called >> {marker}\nexit 97\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{shim}{os.pathsep}{os.environ['PATH']}")
    return marker


def test_reader_copy_applies_without_git(tmp_path, note_kind, failing_git):
    root = vault_with_record(tmp_path)
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "workspace.json").write_text('{"author": "Sam"}', encoding="utf-8")
    path = decision_file(root, [good()])
    code, out = apply(root, path, "--for-lead")
    assert code == 0, out
    assert "Stores count stock nightly." in (root / STOCK).read_text(encoding="utf-8")
    assert not failing_git.exists()
    assert "your copy" in out.lower() and say.leak_in(out) is None


def test_for_lead_says_what_was_filed_with_no_codes(tmp_path, note_kind):
    root = vault_with_record(tmp_path)
    path = decision_file(root, [good(), good(page=SHOP, line="Shop reads it.")])
    code, out = apply(root, path, "--for-lead")
    assert code == 0 and "Stock" in out and "Shop" in out, out
    assert say.leak_in(out) is None


def test_a_write_outside_the_vault_is_refused(tmp_path, note_kind):
    root = vault_with_record(tmp_path)
    (tmp_path / "outside.md").write_text("x\n", encoding="utf-8")
    path = decision_file(root, [good(page="../outside.md")])
    code, out = apply(root, path)
    assert code == 1 and (tmp_path / "outside.md").read_text(encoding="utf-8") == "x\n"


def test_schema_prints_fields_and_example(note_kind):
    code, out = run("apply", "--schema", "note")
    assert code == 0, out
    assert "page" in out and "the capture holding the lead's yes" in out and "judgment" in out
    assert json.dumps(note_kind.SCHEMA.example, indent=2) in out
    code, out = run("apply", "--schema", "note", "--json")
    shaped = json.loads(out)
    assert shaped["schema"]["example"] == note_kind.SCHEMA.example and shaped["schema"]["judgment"] == ["yes"]


def test_schema_of_an_unbuilt_kind_refused():
    code, out = run("apply", "--schema", "allocate")
    assert code == 1 and "can't file that kind of decision yet" in out
