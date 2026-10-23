"""A second machine takes its own part of a session before it captures anything, a lost claim takes the next part,
close fingerprints each part, and `vela records verify` and `seal` check and fill this machine's key only."""
import pathlib

from conftest import run
from sharing import git
from test_session_cli import TODAY, owner, start
from vela import privaterecord
import session_files

SUMMARY = "Looked at till options."


def machine_a(tmp_path, monkeypatch):
    """Machine A starts a session on its own branch and sends it. Returns (vault, bare origin, id, branch)."""
    from sharing import with_remote
    vault = owner(tmp_path, monkeypatch)
    bare = with_remote(tmp_path, vault)
    with open(vault / ".git" / "info" / "exclude", "a", encoding="utf-8") as ignore:
        ignore.write(".vela/*\n")  # as a real vault's .gitignore does: tool state never shows as a change
    assert start(vault, "--mode", "shape", "--topic", "till options", "--new-branch")[0] == 0
    rid = f"{TODAY}-till-options"
    branch = f"session/{rid}"
    git(vault, "push", "-q", "-u", "origin", branch)
    return vault, bare, rid, branch


def clone(tmp_path, bare, name):
    path = tmp_path / name
    git(tmp_path, "clone", "-q", str(bare), str(path))
    for key, value in (("user.name", name), ("user.email", f"{name}@example.com"), ("commit.gpgsign", "false")):
        git(path, "config", key, value)
    return path


def resume(vault, rid, *flags):
    return run("session", "start", "--vault", str(vault), "--today", TODAY, "--resume", rid, *flags)


def on_origin(vault, branch, rid):
    git(vault, "fetch", "-q", "origin")
    return privaterecord.stub_meta(git(vault, "show", f"origin/{branch}:sessions/{rid}.md"))


def private_of(vault, rid):
    return pathlib.Path(vault, privaterecord.private_path(rid))


def test_resume_elsewhere_claims_part_two_before_any_capture(tmp_path, monkeypatch):
    vault_a, bare, rid, branch = machine_a(tmp_path, monkeypatch)
    vault_b = clone(tmp_path, bare, "bea")
    code, out = resume(vault_b, rid, "--for-lead")
    assert code == 0, out
    assert "This session's notes are on the other machine and stay there. I'll keep new notes here as part 2." in out
    meta = on_origin(vault_a, branch, rid)
    assert privaterecord.parts(meta) == {1: "pending", 2: "pending"}
    assert privaterecord.part_of(private_of(vault_b, rid).read_text(encoding="utf-8")) == 2
    assert git(vault_b, "log", "-1", "--format=%s") == f"Take part 2 of {rid}"
    assert not private_of(vault_a, rid).read_text(encoding="utf-8").startswith("part: 2")


def test_a_lost_claim_takes_the_next_part(tmp_path, monkeypatch):
    vault_a, bare, rid, branch = machine_a(tmp_path, monkeypatch)
    vault_b, vault_c = clone(tmp_path, bare, "bea"), clone(tmp_path, bare, "cal")
    assert resume(vault_c, rid)[0] == 0  # C's claim of 2 reaches origin first
    # B's checkout of the branch is made before C's push is known to it, so its push of 2 is rejected
    git(vault_b, "fetch", "-q", "origin")
    git(vault_b, "switch", "-q", "-c", branch, "--track", f"origin/{branch}")
    git(vault_b, "reset", "-q", "--hard", f"origin/{branch}~1")  # B has only seen A's first push
    git(vault_b, "branch", "-q", "-u", f"origin/{branch}")
    code, out = resume(vault_b, rid)
    assert code == 0, out
    assert privaterecord.part_of(private_of(vault_b, rid).read_text(encoding="utf-8")) == 3
    assert privaterecord.parts(on_origin(vault_a, branch, rid)) == {1: "pending", 2: "pending", 3: "pending"}


def test_an_unreachable_origin_stops_the_start_and_claims_nothing(tmp_path, monkeypatch):
    vault_a, bare, rid, branch = machine_a(tmp_path, monkeypatch)
    vault_b = clone(tmp_path, bare, "bea")
    git(vault_b, "remote", "set-url", "--push", "origin", str(tmp_path / "nowhere.git"))
    code, out = resume(vault_b, rid, "--for-lead")
    assert code == 2 and "I haven't started" in out
    assert not private_of(vault_b, rid).exists()
    assert privaterecord.parts(on_origin(vault_a, branch, rid)) == {1: "pending"}


def test_verify_after_close_and_after_an_edit(tmp_path, monkeypatch):
    vault, _, rid, _ = machine_a(tmp_path, monkeypatch)
    code, out = run("close", "stage", "--close", "--session", rid, "--vault", str(vault), "--summary", SUMMARY)
    assert code == 0, out
    meta = privaterecord.stub_meta(session_files.stub_text(vault, rid))
    private = private_of(vault, rid)
    assert meta["status"] == "closed" and privaterecord.parts(meta) == {1: privaterecord.fingerprint(
        private.read_text(encoding="utf-8"))}
    assert git(vault, "log", "-1", "--format=%s") == f"Close session {rid}"
    code, out = run("records", "verify", rid, "--vault", str(vault))
    assert code == 0 and f"Part 1 matches what was committed on {git(vault, 'log', '-1', '--format=%cd', '--date=format:%B %-d, %Y')}." in out
    private.write_text(private.read_text(encoding="utf-8") + "x\n", encoding="utf-8")
    code, out = run("records", "verify", rid, "--vault", str(vault))
    assert code == 1 and "changed since" in out
    private.unlink()
    assert run("records", "verify", rid, "--vault", str(vault))[0] == 2


def test_verify_says_a_part_is_not_fingerprinted_yet(tmp_path, monkeypatch):
    vault, _, rid, _ = machine_a(tmp_path, monkeypatch)
    code, out = run("records", "verify", rid, "--vault", str(vault))
    assert code == 1 and "isn't fingerprinted yet" in out


def test_seal_fills_only_its_own_key(tmp_path, monkeypatch):
    vault_a, bare, rid, branch = machine_a(tmp_path, monkeypatch)
    vault_b = clone(tmp_path, bare, "bea")
    assert resume(vault_b, rid)[0] == 0
    private_a = private_of(vault_a, rid)
    code, out = run("records", "seal", rid, "--vault", str(vault_a))
    assert code == 0, out
    assert git(vault_a, "log", "-1", "--format=%s") == f"Seal part 1 of {rid}"
    assert git(vault_a, "show", "--name-only", "--format=", "HEAD") == f"sessions/{rid}.md"
    meta = privaterecord.stub_meta(session_files.stub_text(vault_a, rid))
    assert privaterecord.parts(meta)[1] == privaterecord.fingerprint(private_a.read_text(encoding="utf-8"))
    head = git(vault_a, "rev-parse", "HEAD")
    assert run("records", "seal", rid, "--vault", str(vault_a))[0] == 0 and git(vault_a, "rev-parse", "HEAD") == head
    private_a.write_text(private_a.read_text(encoding="utf-8") + "x\n", encoding="utf-8")
    code, out = run("records", "seal", rid, "--vault", str(vault_a))
    assert code == 1 and "different fingerprint" in out and git(vault_a, "rev-parse", "HEAD") == head


def test_seal_leaves_another_machines_pending_key_alone(tmp_path, monkeypatch):
    vault_a, bare, rid, branch = machine_a(tmp_path, monkeypatch)
    vault_b = clone(tmp_path, bare, "bea")
    assert resume(vault_b, rid)[0] == 0
    assert run("records", "seal", rid, "--vault", str(vault_b))[0] == 0
    meta = privaterecord.stub_meta(session_files.stub_text(vault_b, rid))
    held = privaterecord.parts(meta)
    assert held[1] == "pending" and held[2] == privaterecord.fingerprint(
        private_of(vault_b, rid).read_text(encoding="utf-8"))


def test_close_stage_summary_needs_close(tmp_path, monkeypatch):
    vault, _, rid, _ = machine_a(tmp_path, monkeypatch)
    code, out = run("close", "stage", "--checkpoint", "--session", rid, "--vault", str(vault), "--summary", SUMMARY)
    assert code != 0 and "--summary goes with --close" in out
