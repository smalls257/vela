"""`vela voice settle` (overhaul Task 19): close/VOICE-REVIEW.md's git dance, done by the command.

Each test names the rule it holds. The vault is the template, committed, with a `draft: prose for <id>` commit holding
two drafted paragraphs; the rewrites are written into the working tree the way close's "Write the items and the prose" writes them.
"""
import hashlib
import json
import shutil
import subprocess

import pytest

from conftest import REPO, run
from vela import cli
import session_files

TEMPLATE = REPO / "plugin" / "template"
SESSION = "2026-10-14-voice-settle"
RECORD = f"""---
id: {SESSION}
type: session
date: 2026-10-14
modes: [grill]
status: open
---

# 2026-10-14 Grill: voice settle

## Captures
"""
A, B = "03-context-and-scope.md", "04-solution-strategy.md"
A_DRAFT = "The booking service answers in 200 ms, and the old desk never did.\n"
A_LOSES_NUMBER = "The booking service answers quickly, and the old desk never did.\n"
B_DRAFT = "Requests reach the desk through one queue. It never ran on weekends. The queue never ran on weekends.\n"
B_REWRITE = "Every request reaches the desk through one queue. The queue never ran on weekends.\n"
B_SAME_FACTS = "Every request reaches the desk through a single queue. It never ran on weekends. " \
               "The queue never ran on weekends.\n"
REDUNDANT = "It never ran on weekends."


def git(root, *args):
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return done.stdout


def text(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def head_text(root, rel):
    return git(root, "show", f"HEAD:{rel}")


@pytest.fixture
def vault(tmp_path):
    """The template committed, then the session's draft commit holding a paragraph on each of two pages."""
    root = tmp_path / "vault"
    shutil.copytree(TEMPLATE, root)
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test Lead")
    git(root, "config", "user.email", "lead@example.com")
    session_files.write_record(root, SESSION, RECORD)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Start")
    for rel, draft in ((A, A_DRAFT), (B, B_DRAFT)):
        (root / rel).write_text(text(root, rel) + "\n" + draft, encoding="utf-8")
    git(root, "commit", "-q", "-am", f"draft: prose for {SESSION}")
    return root


def rewrite(root, rel, old, new):
    body = text(root, rel)
    assert body.count(old) == 1
    (root / rel).write_text(body.replace(old, new), encoding="utf-8")


def settle(root, *flags):
    return run("voice", "settle", "--vault", str(root), *flags)


def outcome(root):
    return json.loads((root / ".vela" / "close" / f"{SESSION}.voice.json").read_text(encoding="utf-8"))


def subjects(root, n):
    return git(root, "log", f"-{n}", "--format=%s").splitlines()


def test_failed_voicecheck_restores_only_that_page(vault):
    """VOICE-REVIEW step 5: exit 1 restores that page alone; the passes are committed as `draft: voice rewrite`."""
    assert settle(vault, "--checkpoint", A, B)[0] == 0
    rewrite(vault, A, A_DRAFT, A_LOSES_NUMBER)
    rewrite(vault, B, B_DRAFT, B_SAME_FACTS)
    code, out = settle(vault, "--rewrites", A, B)
    assert code == 1, out
    assert text(vault, A) == head_text(vault, A) and A_DRAFT in text(vault, A)
    assert subjects(vault, 1) == [f"draft: voice rewrite for {SESSION}"]
    assert git(vault, "show", "--name-only", "--format=", "HEAD").split() == [B]
    assert B_SAME_FACTS in head_text(vault, B)
    assert "200 ms" in out and f"restored {A}" in out
    code, out = settle(vault, "--rewrites", A, "--for-lead")
    assert code == 0, out  # nothing left to check: the restored page equals HEAD


def test_uncommitted_section3_edit_survives_restore(vault):
    """VOICE-REVIEW step 4: a page holding an uncommitted section-3 edit is checkpointed first, so the restore keeps
    it; an uncommitted edit on a page nobody rewrote is neither touched nor committed."""
    section3 = "Section 3 wrote this line and has not committed it.\n"
    (vault / A).write_text(text(vault, A) + section3, encoding="utf-8")
    elsewhere = "12-glossary.md"
    (vault / elsewhere).write_text(text(vault, elsewhere) + "An uncommitted glossary edit.\n", encoding="utf-8")
    glossary = text(vault, elsewhere)
    code, out = settle(vault, "--checkpoint", A, B)
    assert code == 0, out
    assert subjects(vault, 1) == [f"Checkpoint {SESSION}"]
    assert git(vault, "show", "--name-only", "--format=", "HEAD").split() == [A]  # B equalled HEAD: no commit for it
    rewrite(vault, A, A_DRAFT, A_LOSES_NUMBER)
    code, out = settle(vault, "--rewrites", A, "--for-lead")
    assert code == 1, out
    assert "I put back the earlier draft of" in out and "changed a number" in out
    assert section3 in text(vault, A) and A_DRAFT in text(vault, A)
    assert text(vault, elsewhere) == glossary
    assert elsewhere in git(vault, "status", "--porcelain")


def test_settle_refuses_a_page_that_was_not_checkpointed(vault):
    """Without the checkpoint a restore would discard the page's uncommitted edits, so nothing runs at all."""
    rewrite(vault, A, A_DRAFT, A_LOSES_NUMBER)
    code, out = settle(vault, "--rewrites", A)
    assert code == 1, out
    assert "refused (voice-not-checkpointed)" in out
    assert A_LOSES_NUMBER in text(vault, A)  # nothing restored
    assert subjects(vault, 1) == [f"draft: prose for {SESSION}"]


def test_settle_refuses_when_a_commit_since_the_checkpoint_touched_the_page(vault):
    """voicecheck compares against HEAD; a page committed after its checkpoint may already hold the rewrite."""
    settle(vault, "--checkpoint", A)
    rewrite(vault, A, A_DRAFT, A_LOSES_NUMBER)
    git(vault, "commit", "-q", "-am", "someone committed the rewrite")
    code, out = settle(vault, "--rewrites", A)
    assert code == 1 and "refused (voice-checkpoint-moved)" in out, out


def test_redundant_sentence_passed_to_voicecheck(vault):
    """VOICE-REVIEW step 5: a sentence the reviewer named redundant may take its negation with it, and only on its page."""
    settle(vault, "--checkpoint", B)
    rewrite(vault, B, B_DRAFT, B_REWRITE)
    code, out = settle(vault, "--rewrites", B)
    assert code == 1 and "negation" in out, out  # without the name, the dropped "never" fails the page
    settle(vault, "--checkpoint", B)
    rewrite(vault, B, B_DRAFT, B_REWRITE)
    code, out = settle(vault, "--rewrites", B, "--redundant", B, REDUNDANT)
    assert code == 0, out
    assert B_REWRITE in head_text(vault, B)
    assert outcome(vault)["redundant"] == [{"page": B, "sentence": REDUNDANT}]


def test_a_redundant_sentence_still_in_the_rewrite_restores_the_page(vault):
    """voicecheck's exit 2: a named sentence that was not removed is never committed unchecked."""
    settle(vault, "--checkpoint", B)
    rewrite(vault, B, B_DRAFT, B_SAME_FACTS)
    code, out = settle(vault, "--rewrites", B, "--redundant", B, REDUNDANT)
    assert code == 1, out
    assert text(vault, B) == head_text(vault, B)
    assert outcome(vault)["restored"][0]["page"] == B and "still in the text" in outcome(vault)["restored"][0]["why"]


def test_outcome_file_written_for_close_pr(vault):
    """Task 12's `close pr` reads `.vela/close/<id>.voice.json` for the PR body's **Voice review**."""
    settle(vault, "--checkpoint", A, B)
    rewrite(vault, A, A_DRAFT, A_LOSES_NUMBER)
    rewrite(vault, B, B_DRAFT, B_REWRITE)
    code, out = settle(vault, "--rewrites", A, B, "--redundant", B, REDUNDANT, "--json")
    assert code == 1, out
    found = outcome(vault)
    assert set(found) == {"version", "redundant", "restored", "kept"}
    assert found["version"] == 1
    assert found["kept"] == [B]
    assert found["redundant"] == [{"page": B, "sentence": REDUNDANT}]
    assert [r["page"] for r in found["restored"]] == [A] and "200 ms" in found["restored"][0]["why"]
    assert git(vault, "status", "--porcelain", "--", ".vela").strip() == ""  # tool state, never staged
    assert json.loads(out)["outcome"] == f".vela/close/{SESSION}.voice.json"


def fake_embed(texts):
    """A vector per text that is fixed by the text, so the owner examples form a range the paragraphs fall in or out."""
    return [[1.0, int(hashlib.sha1(t.encode()).hexdigest()[:2], 16) / 2550.0, 0.0] for t in texts]


def test_score_adds_voicescore_line(vault, monkeypatch, tmp_path):
    """REF: `--score` adds the voicescore summary line for the PR body; without it, or when it cannot run, it is a
    hint and never a gate: the exit code is the voicecheck verdict's alone."""
    settle(vault, "--checkpoint", B)
    rewrite(vault, B, B_DRAFT, B_SAME_FACTS)
    monkeypatch.setenv("VELA_VOICESCORE_HOME", str(tmp_path / "no-models"))
    code, out = settle(vault, "--rewrites", B, "--score")
    assert code == 0, out
    assert "voicescore: not run (" in out
    settle(vault, "--checkpoint", B)
    rewrite(vault, B, B_SAME_FACTS, B_DRAFT)
    assert "voicescore" not in settle(vault, "--rewrites", B)[1]
    for n in range(1, 6):
        path = vault / "voice" / "local" / "how-it-works" / f"VX-how-it-works-00{n}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nid: VX-how-it-works-00{n}\nvoice_type: how-it-works\nsource: owner\nauthor: \"@owner\"\n"
                        f"state: active\nadded: 2026-10-06\n---\n\nOwner paragraph number {n}.\n", encoding="utf-8")
    monkeypatch.setattr(cli, "missing_dependencies", lambda: [])
    monkeypatch.setattr(cli, "load_styledistance", lambda path: fake_embed)
    cli.model_dir().mkdir(parents=True)
    (cli.model_dir() / cli.MODEL_MARKER).write_text("{}", encoding="utf-8")
    settle(vault, "--checkpoint", B)
    rewrite(vault, B, B_DRAFT, B_SAME_FACTS)
    code, out = settle(vault, "--rewrites", B, "--score")
    assert code == 0, out
    line = next(l for l in out.splitlines() if l.startswith("voicescore: "))
    assert "paragraphs inside your range" in line
    code, out = settle(vault, "--rewrites", B, "--score", "--for-lead")
    assert code == 0 and "The style reading puts" in out, out


def test_reader_copy_runs_no_git_and_says_so(tmp_path):
    root = tmp_path / "reader"
    (root / ".vela").mkdir(parents=True)
    (root / ".vela" / "workspace.json").write_text("{}", encoding="utf-8")
    code, out = settle(root, "--rewrites", A)
    assert code == 1 and "reader copy" in out, out
