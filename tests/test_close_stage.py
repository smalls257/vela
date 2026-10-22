"""`vela close stage` (overhaul Task 9): an allow-list by exact path, never a sweep, and the close skill's commits."""
import json
import shutil
import subprocess

import pytest

from conftest import REPO, run
from vela import say
from vela.edge import vaultgit
import session_files

TEMPLATE = REPO / "plugin" / "template"
SESSION = "2026-10-14-close-test"
RECORD = f"""---
id: {SESSION}
type: session
date: 2026-10-14
modes: [grill]
status: open
---

# 2026-10-14 Grill: close test

## Captures
"""


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=false", *args], capture_output=True,
                          text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return done.stdout


def staged(root):
    return sorted(p for p in git(root, "diff", "--cached", "--name-only", "-z").split("\0") if p)


def committed(root):
    return sorted(p for p in git(root, "show", "--name-only", "-z", "--format=", "HEAD").split("\0") if p)


@pytest.fixture
def vault(tmp_path):
    """The template as a committed vault with one open session record."""
    root = tmp_path / "vault"
    shutil.copytree(TEMPLATE, root)
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test Lead")
    git(root, "config", "user.email", "lead@example.com")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Start")
    session_files.write_record(root, SESSION, RECORD)
    return root


def change(root, rel, text="changed\n"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((path.read_text(encoding="utf-8") if path.exists() else "") + text, encoding="utf-8")


def stage(root, *flags):
    return run("close", "stage", "--vault", str(root), *flags)


def test_inbox_voice_local_corpus_never_staged(vault):
    (vault / ".gitignore").unlink()  # a vault whose ignore file was lost still keeps them out
    git(vault, "commit", "-q", "-am", "drop ignore")
    for rel in (".inbox/call.md", "voice/local/mine.md", "voice/corpus/essay.txt", ".vela/session.json"):
        change(vault, rel)
    change(vault, "01-goals.md")
    code, out = stage(vault, "--json")
    assert code == 1, out
    data = json.loads(out)
    assert {n["rule"] for n in data["never"]} == {"inbox", "voice-local", "voice-corpus", "tool-state"}
    assert staged(vault) == ["01-goals.md", f"sessions/{SESSION}.md"]
    code, out = stage(vault, "--for-lead")
    assert "The meeting notes in the inbox stay on this machine; I've left them out." in out.splitlines()


def test_pins_file_is_staged(vault):
    change(vault, ".vela/explorer-pins.json", "{}\n")
    change(vault, ".vela/workspace-notes.json", "{}\n")  # ignored by the template, so git never offers it
    code, out = stage(vault)
    assert code == 0, out
    assert staged(vault) == [".vela/explorer-pins.json", f"sessions/{SESSION}.md"]


def test_only_allow_listed_paths_are_staged(vault):
    for rel in ("01-goals.md", "voice/examples/decision/new.md", ".vela.yaml", "sources.md", "CONVENTIONS.md",
                "scratch.txt", "handoffs/APP-till.md", "dashboard.html"):
        change(vault, rel)
    code, out = stage(vault)
    assert code == 1, out
    assert staged(vault) == sorted([".vela.yaml", "01-goals.md", f"sessions/{SESSION}.md", "sources.md",
                                    "voice/examples/decision/new.md"])
    for rel in ("CONVENTIONS.md", "scratch.txt", "handoffs/APP-till.md", "dashboard.html"):
        assert f"left out: {rel} (" in out, rel


def test_paths_with_spaces_and_unicode(vault):
    page = "05-building-blocks/Café notes [draft].md"
    change(vault, page, "---\nid: cafe\ntype: note\ntitle: Café\n---\n")
    change(vault, "stray notes é.txt")
    code, out = stage(vault, "--json")
    assert code == 1, out
    assert page in staged(vault) and "stray notes é.txt" not in staged(vault)
    assert [x["path"] for x in json.loads(out)["left"]] == ["stray notes é.txt"]


def commits_with(vault, flag, message):
    change(vault, "01-goals.md")
    change(vault, "scratch.txt")
    git(vault, "add", "--", "scratch.txt")  # something else in the index must not ride along
    code, out = stage(vault, flag)
    assert code == 1, out
    assert git(vault, "log", "-1", "--format=%s").strip() == message
    assert committed(vault) == ["01-goals.md", f"sessions/{SESSION}.md"]
    assert "left out: scratch.txt (" in out and f": {message}" in out


def test_draft_commits_with_the_prose_message(vault):
    commits_with(vault, "--draft", f"draft: prose for {SESSION}")


def test_checkpoint_commits_with_the_checkpoint_message(vault):
    commits_with(vault, "--checkpoint", f"Checkpoint {SESSION}")


def test_close_commits_with_the_close_message(vault):
    commits_with(vault, "--close", f"Close session {SESSION}")


def test_commit_flags_are_one_at_a_time(vault):
    code, _ = stage(vault, "--draft", "--close")
    assert code == 2
    assert git(vault, "rev-list", "--count", "HEAD").strip() == "1"


def test_the_session_must_be_clear(vault):
    session_files.write_record(vault, "2026-10-13-other", RECORD.replace(SESSION, "2026-10-13-other"))
    code, out = stage(vault, "--json")
    assert code == 3 and json.loads(out)["needs_lead"] == ["2026-10-13-other", SESSION]
    assert staged(vault) == []
    code, out = stage(vault, "--session", SESSION)
    assert code == 1 and staged(vault) == [f"sessions/{SESSION}.md"]  # the other record is named and left


def test_paths_from_render_refuses_a_stale_render(vault):
    """The new open record moves the goals page's status block, so until render runs the page is not render's output."""
    code, out = stage(vault, "--paths-from-render")
    assert code == 1 and "render would still rewrite 01-goals.md" in out, out
    assert staged(vault) == []
    assert run("render", "--vault", str(vault))[0] == 0
    code, out = stage(vault, "--paths-from-render")
    assert code == 0, out
    assert "01-goals.md" in staged(vault)


def test_reader_copy_stages_nothing_and_runs_no_git(tmp_path, monkeypatch):
    copy = tmp_path / "copy"
    shutil.copytree(TEMPLATE, copy)
    (copy / ".vela").mkdir()
    (copy / ".vela" / "workspace.json").write_text("{}", encoding="utf-8")

    def no_git(*args, **kwargs):
        raise AssertionError(f"git ran in a reader copy: {args}")
    monkeypatch.setattr(vaultgit, "run_git", no_git)
    monkeypatch.setattr(subprocess, "run", no_git)
    code, out = stage(copy, "--draft", "--for-lead")
    assert code == 0, out
    assert out.strip() == "This is your copy, so nothing is staged or committed here."


def test_for_lead_lines_pass_the_leak_check(vault):
    change(vault, "09-decisions/ADR-0001-till.md", "---\nid: ADR-0001\ntype: decision\ntitle: Till\n---\n")
    change(vault, "notes/UNK-004 scratch.txt")
    change(vault, "11-unknowns-and-risks.md")
    change(vault, ".inbox/call.md")
    git(vault, "add", "-f", "--", ".inbox/call.md")
    code, out = stage(vault, "--for-lead", "--checkpoint")
    assert code == 1, out
    assert "vela bug" not in out
    for line in out.splitlines():
        assert say.leak_in(line) is None, line
    assert out.splitlines()[-2].startswith("I've saved two changed pages and the session record.")
    assert "a file in notes" in out
    assert ".inbox/call.md" not in committed(vault)
