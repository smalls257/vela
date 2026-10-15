"""`vela proposals commit`: the owner's own commits in a proposal's worktree go through vela, by exact path (Task 24
left no skill line that stages by hand). Runs against the same real repo the proposals tests build."""
import json

from conftest import run
from sharing import git
from test_proposals import OLD_LINE, PAGE, commit_in, proposed, read, review_it, world, wt_of  # noqa: F401 (fixtures)


def commit(wt, *extra):
    return run("proposals", "commit", "--vault", str(wt), *extra)


def test_an_owner_edit_is_committed_as_its_group_and_prints_the_hash(proposed):
    src, _, folder = proposed
    review_it(src, folder)
    wt = wt_of(src)
    page = wt / PAGE
    page.write_text(read(page).replace("a reader's cap is a must", "a reader's cap is a must, said Finance"),
                    encoding="utf-8")
    code, text = commit(wt, "--step", "edit", "--group", "CON-002", "--json")
    assert code == 0, text
    data = json.loads(text)["data"] if "data" in json.loads(text) else json.loads(text)
    assert git(wt, "log", "-1", "--format=%s").strip() == "Edit CON-002 from the proposal"
    assert data["commit"] == git(wt, "rev-parse", "--short", "HEAD").strip()
    assert git(wt, "status", "--porcelain").strip() == ""


def test_conflicts_with_markers_left_are_refused_and_nothing_is_committed(proposed):
    src, _, folder = proposed
    commit_in(src, PAGE, OLD_LINE, "so no real order ever crosses; the owner rewrote this.")
    review_it(src, folder)
    wt = wt_of(src)
    head = git(wt, "rev-parse", "HEAD")
    code, text = commit(wt, "--step", "conflicts")
    assert code == 1 and "coach-building-blocks" in text
    assert git(wt, "rev-parse", "HEAD") == head
    page = wt / PAGE
    lines = [line for line in read(page).splitlines(keepends=True)
             if not line.startswith(("<<<<<<<", "=======", ">>>>>>>", "|||||||"))]
    page.write_text("".join(lines), encoding="utf-8")
    code, text = commit(wt, "--step", "conflicts")
    assert code == 0, text
    assert git(wt, "log", "-1", "--format=%s").strip() == "Resolve proposal conflicts"
    assert git(wt, "diff", "--name-only", "--diff-filter=U").strip() == ""


def test_nothing_changed_is_refused_plainly(proposed):
    src, _, folder = proposed
    review_it(src, folder)
    code, text = commit(wt_of(src), "--step", "render", "--for-lead")
    assert code == 1 and "nothing to save" in text


def test_it_runs_only_in_a_proposal_worktree_and_an_edit_names_its_group(proposed):
    src, _, folder = proposed
    review_it(src, folder)
    assert commit(src, "--step", "render")[0] == 2  # the owner's own checkout, not a proposal/ branch
    code, text = commit(wt_of(src), "--step", "edit")
    assert code == 2 and "--group" in text
