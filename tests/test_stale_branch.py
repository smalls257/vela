"""A session must not start on a branch that lacks the shared plan (diagnosis 6B of the 2026-10-14 run).

S15 releases began on the last session's `dashboard/2026-10-14-close` branch. Allocation had merged to origin/main at
the end of S14, but `vela freshness` said only "this branch has no upstream", the skill read the stale working tree
and told the lead "nothing has been allocated yet", and no tracer was recorded. These tests rebuild that state: the
releases precondition now hears it (`freshness` exits 3 and names the fix), and `session start` brings it in.
"""
import json
import shutil

from conftest import REPO, run
from sharing import git
from test_releases import APP, CAP, FR, ROW

from vela import freshness

FIXTURE = REPO / "examples" / "unified-booking"
TODAY = "2026-10-14"
STALE = "dashboard/2026-10-14-close"


def releases_missing(vault):
    code, out = run("releases", "brief", "--vault", str(vault), "--json")
    assert code == 0, out
    return [m["offer"] for m in json.loads(out)["missing"]]


def teammate_commits(tmp_path, bare, rel, add, message):
    """Another clone appends to a page and pushes it to origin/main, as S14's merged pull request did."""
    other = tmp_path / "teammate"
    git(tmp_path, "clone", "-q", str(bare), str(other))
    page = other / rel
    page.write_text(page.read_text(encoding="utf-8").rstrip("\n") + "\n" + add, encoding="utf-8")
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", message)
    git(other, "push", "-q", "origin", "main")
    shutil.rmtree(other)


def s15(tmp_path):
    """The vault as S15 found it: requirements written, the clone on S14's close branch (no upstream), and the
    allocation on origin/main only."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURE, vault)
    page = vault / CAP
    page.write_text(page.read_text(encoding="utf-8").rstrip("\n") + "\n" + FR, encoding="utf-8")
    git(tmp_path, "init", "-q", "-b", "main", str(vault))
    for key, value in (("user.name", "Priya Nair"), ("user.email", "priya@example.com"), ("commit.gpgsign", "false")):
        git(vault, "config", key, value)
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "Requirements")
    bare = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    git(vault, "remote", "add", "origin", str(bare))
    git(vault, "push", "-q", "origin", "main")
    git(vault, "switch", "-q", "-c", STALE)
    teammate_commits(tmp_path, bare, APP, ROW, "Allocate the hold to Booking")
    return vault, bare


def test_releases_precondition_sees_the_allocation_waiting_on_origin_main(tmp_path):
    vault, _ = s15(tmp_path)
    assert "/vela:allocate" in releases_missing(vault)  # what S15 read and wrongly reported as the truth
    code, said = run("freshness", "--vault", str(vault))
    assert code == freshness.EXIT_BEHIND, said
    assert f"Your branch {STALE} is 1 commit behind the shared plan (origin/main); run `vela session start`" in said
    code, said = run("session", "start", "--vault", str(vault), "--today", TODAY, "--mode", "releases",
                     "--topic", "first release")
    assert code == 0, said
    assert git(vault, "rev-parse", "--abbrev-ref", "HEAD") == f"session/{TODAY}-first-release"
    assert "/vela:allocate" not in releases_missing(vault)
    assert run("freshness", "--vault", str(vault))[0] == 0


# ---- a resumed session's branch gets main through close sync-main's own merge


def resumable(tmp_path):
    """An open session on its own branch, then a teammate's change merged to origin/main."""
    vault, bare = s15(tmp_path)
    code, said = run("session", "start", "--vault", str(vault), "--today", TODAY, "--mode", "shape",
                     "--topic", "till options")
    assert code == 0, said
    git(vault, "switch", "-q", STALE)
    teammate_commits(tmp_path, bare, "01-goals.md", "\nA goal a teammate added.\n", "Teammate goal")
    return vault


def test_resume_merges_origin_main_into_the_session_branch_and_keeps_no_close_record(tmp_path):
    vault = resumable(tmp_path)
    code, said = run("session", "start", "--vault", str(vault), "--today", TODAY, "--resume", f"{TODAY}-till-options",
                     "--json")
    assert code == 0, said
    assert git(vault, "rev-parse", "--abbrev-ref", "HEAD") == f"session/{TODAY}-till-options"
    assert "A goal a teammate added." in (vault / "01-goals.md").read_text(encoding="utf-8")
    assert any("merged origin/main" in line for line in json.loads(said)["lines"])
    assert not (vault / ".vela" / "close").exists()  # close must still bring in what main gains during the session
    assert run("freshness", "--vault", str(vault))[0] == 0


def test_resume_over_uncommitted_edits_asks_for_a_checkpoint_first(tmp_path):
    vault = resumable(tmp_path)
    git(vault, "switch", "-q", f"session/{TODAY}-till-options")
    goals = vault / "01-goals.md"
    goals.write_text(goals.read_text(encoding="utf-8") + "\nmy edit\n", encoding="utf-8")
    code, said = run("session", "start", "--vault", str(vault), "--today", TODAY, "--resume", f"{TODAY}-till-options",
                     "--json")
    assert code == 3, said
    found = json.loads(said)
    assert found["wrote"] == [] and found["needs_lead"][0]["choice"] == "checkpoint"
    assert "my edit" in goals.read_text(encoding="utf-8")
    assert "A goal a teammate added." not in goals.read_text(encoding="utf-8")


def test_resume_with_an_unreachable_origin_says_so_and_goes_on(tmp_path):
    vault = resumable(tmp_path)
    git(vault, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    code, said = run("session", "start", "--vault", str(vault), "--today", TODAY, "--resume", f"{TODAY}-till-options")
    assert code == 0, said
    assert "git fetch origin failed:" in said and "starting from this machine's copy of the session's branch" in said
    assert "accept-not-compared" not in said  # a close choice has no place at the start
    code, said = run("session", "start", "--vault", str(vault), "--today", TODAY, "--resume", f"{TODAY}-till-options",
                     "--for-lead")
    assert "this session starts from this machine's copy of the session's branch, which may be behind" in said

