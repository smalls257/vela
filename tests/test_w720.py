"""W720: a session's private notes are committed (private-sessions Task 13).

The Violation this guards is an Infected Core of the plan's history, caught after the fact: the ignore line and the
guard stop the usual routes, and W720 is the Sensor for the unusual ones (`git add -f`, a record never split)."""
from conftest import run
from sharing import git, make_vault
from vela import privaterecord

TODAY = "2026-10-14"
RECORD_ID = "2026-10-14-consent"
NOTES = "---\nid: 2026-10-14-consent\npart: 1\n---\n\n## Captures\n\n- [idea] (@lead) Words. ^c01\n"
FULL = "---\nid: {id}\ntype: session\ndate: 2026-10-14\nmodes: [dump]\nstatus: closed\n---\n\n## Captures\n\n- [idea] (@mini-lead) Words. ^c01\n"


def w720(vault, path="sessions/"):
    """W720 lines about `path`. The mini fixture still holds two whole records until Task 7 splits it, and those
    draw W720 of their own; the tests here look at the file they made."""
    return [line for line in run("check", "--vault", str(vault), "--today", TODAY)[1].splitlines()
            if "W720" in line and line.startswith(path)]


def test_w720_on_a_tracked_private_file(tmp_path):
    vault = make_vault(tmp_path)
    private = vault / "sessions" / "private" / f"{RECORD_ID}.md"
    private.parent.mkdir(parents=True)
    private.write_text(NOTES, encoding="utf-8")
    assert w720(vault, "sessions/private/") == [], "an untracked, ignored file is the normal case"
    git(vault, "add", "-f", f"sessions/private/{RECORD_ID}.md")
    git(vault, "commit", "-qm", "oops")
    found = w720(vault, "sessions/private/")
    assert len(found) == 1 and found[0].startswith(f"sessions/private/{RECORD_ID}.md:1: W720"), found
    assert "git rm --cached" in found[0]


def test_w720_on_an_unsplit_record_and_not_on_a_stub(mini):
    whole = mini / "sessions" / f"{RECORD_ID}.md"
    whole.write_text(FULL.format(id=RECORD_ID), encoding="utf-8")
    found = w720(mini, f"sessions/{RECORD_ID}.md")
    assert any(line.startswith(f"sessions/{RECORD_ID}.md:") and "vela records split" in line
               and "shared with everyone who clones the plan" in line for line in found), found
    whole.write_text(privaterecord.split_record(FULL.format(id=RECORD_ID)).stub, encoding="utf-8")
    assert not any(RECORD_ID in line for line in w720(mini, f"sessions/{RECORD_ID}.md"))


def test_w720_stays_out_of_the_toolkit_repo(tmp_path):
    vault = make_vault(tmp_path)
    (vault / ".vela-toolkit").write_text("", encoding="utf-8")
    private = vault / "sessions" / "private" / f"{RECORD_ID}.md"
    private.parent.mkdir(parents=True)
    private.write_text(NOTES, encoding="utf-8")
    git(vault, "add", "-f", "sessions/private", ".vela-toolkit")
    assert w720(vault, "sessions/private/") == []


def test_w720_says_when_git_cannot_answer(tmp_path, monkeypatch):
    from vela.edge import vaultgit

    def broken(root):
        raise vaultgit.GitUnavailable("no git here")
    vault = make_vault(tmp_path)
    monkeypatch.setattr(vaultgit, "tracked_paths", broken)
    from vela import cli
    found = cli.tracked_private_findings(vault)
    assert [f.code for f in found] == ["W720"] and "couldn't ask git" in found[0].message
