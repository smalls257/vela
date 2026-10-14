"""Keeping up: `planner open <newer copy>` on a workspace that already has drafts replays them onto the new pages
(design session 15 section 8). Run end to end: publish v1, open, the reader drafts, the owner commits and publishes v2,
the reader re-opens. Each page lands in exactly one of: kept, took the owner's, merged, or conflict with the reader's
version beside it. Nothing the reader wrote is dropped."""
import json
import pathlib

import pytest
from conftest import run
from sharing import git, published_snapshot

from planner import replay, untrusted

V2_DAY = "2026-10-20"
READER_ONLY = "02-constraints.md"
MERGE = "01-goals.md"
CLASH = "03-context-and-scope.md"
OWNER_DELETES = "12-glossary.md"
READER_DELETES = "04b-releases.md"
OWNER_ONLY = "04-solution-strategy.md"
BOTH_ADD = "reader-notes.md"
PENDING_PAGE = "05-building-blocks/coach-building-blocks.md"
MARKER = "#### CON-001 Lessons and track\n\n"


def prose(text):
    """Indexes of plain paragraph lines in a page body, past the front matter: safe lines to change a word in."""
    lines = text.split("\n")
    start = lines.index("---", 1) + 1 if lines[0] == "---" else 0
    return [i for i, line in enumerate(lines) if i > start and line[:1].isalpha() and len(line) > 60]


def tweak(path, which, tag):
    """Append a tag to the `which`-th (negative counts from the end) plain line of a page."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    lines[prose(text)[which]] += f" {tag}"
    path.write_text("\n".join(lines), encoding="utf-8")


def notes(who):
    return f"---\nid: reader-notes\ntype: initiative-section\ntitle: Notes\nstate: inkling\nowner: \"@solution-lead\"\nauthored: mixed\n---\n\n# Notes\n\n{who}'s notes.\n"


def give_every_reason(workspace, tmp_path):
    """A --whys file with a reason for every group the proposal holds."""
    code, text = run("propose", "--vault", str(workspace), "--groups", "--json", "--today", "2026-10-18")
    assert code == 0, text
    path = tmp_path / "whys.json"
    path.write_text(json.dumps({g["group"]: "A reason." for g in json.loads(text)}), encoding="utf-8")
    return path


def read(path):
    return pathlib.Path(path).read_text(encoding="utf-8")


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file() and ".planner" not in p.relative_to(root).parts}


def open_into(source, workspace, today="2026-10-12", *extra):
    return run("open", str(source), "--into", str(workspace), "--author", "Sam Okoye", "--today", today, *extra)


def make_world(tmp_path):
    """(owner repo, published v1, workspace after the reader's drafts). The owner has not yet changed anything."""
    src, v1 = published_snapshot(tmp_path, "v1")
    workspace = tmp_path / "workspace"
    assert open_into(v1, workspace)[0] == 0
    tweak(workspace / READER_ONLY, -1, "(reader note)")
    tweak(workspace / MERGE, 0, "(reader, top)")
    tweak(workspace / CLASH, 0, "(reader wording)")
    (workspace / OWNER_DELETES).write_text(read(workspace / OWNER_DELETES) + "\nSam's own term.\n", encoding="utf-8")
    (workspace / READER_DELETES).unlink()
    page = workspace / PENDING_PAGE
    page.write_text(read(page).replace(MARKER, MARKER + "- **Pending approval:** @sam, 2026-10-12\n", 1), encoding="utf-8")
    (workspace / BOTH_ADD).write_text(notes("Sam"), encoding="utf-8")
    return src, v1, workspace


@pytest.fixture
def world(tmp_path):
    return make_world(tmp_path)


def conflicted_workspace(tmp_path):
    """A workspace after a re-open that left four conflicts, a merge, a kept page and a pending decision."""
    src, _, workspace = make_world(tmp_path)
    assert open_into(owner_publishes_v2(src, tmp_path), workspace, V2_DAY)[0] == 0
    return workspace


def owner_publishes_v2(src, tmp_path):
    """The owner edits some of the same pages, deletes one, adds one and publishes again to a new folder."""
    tweak(src / MERGE, -1, "(owner, bottom)")
    tweak(src / CLASH, 0, "(owner wording)")
    tweak(src / OWNER_ONLY, -1, "(owner update)")
    tweak(src / READER_DELETES, -1, "(owner edit of a page the reader deleted)")
    (src / OWNER_DELETES).unlink()
    (src / BOTH_ADD).write_text(notes("Priya"), encoding="utf-8")
    (src / "README.md").write_text(read(src / "README.md").replace("[[12-glossary|Glossary]]", "the glossary"), encoding="utf-8")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "second")
    v2 = tmp_path / "v2"
    assert run("publish", "--vault", str(src), "--out", str(v2), "--today", V2_DAY)[0] == 0
    return v2


@pytest.fixture
def replayed(world, tmp_path):
    src, v1, workspace = world
    mine_before = {p: read(workspace / p) for p in (READER_ONLY, MERGE, CLASH, OWNER_DELETES, BOTH_ADD)}
    v2 = owner_publishes_v2(src, tmp_path)
    code, text = open_into(v2, workspace, V2_DAY)
    assert code == 0, text
    return src, v2, workspace, mine_before, text


# ------------------------------------------------------------------ outcomes, page by page

def test_a_page_only_the_reader_changed_keeps_the_readers_version(replayed):
    _, _, workspace, before, _ = replayed
    assert read(workspace / READER_ONLY) == before[READER_ONLY] and "(reader note)" in read(workspace / READER_ONLY)


def test_a_page_only_the_owner_changed_takes_the_owners(replayed):
    _, v2, workspace, _, _ = replayed
    assert read(workspace / OWNER_ONLY) == read(v2 / OWNER_ONLY) and "(owner update)" in read(workspace / OWNER_ONLY)


def test_both_changing_different_lines_merges_and_keeps_both(replayed):
    _, v2, workspace, _, text = replayed
    merged = read(workspace / MERGE)
    assert "(reader, top)" in merged and "(owner, bottom)" in merged
    assert merged != read(v2 / MERGE) and "Merged" in text and MERGE in text
    backup = list((workspace / ".planner" / "replay-backup").rglob(MERGE))
    assert len(backup) == 1 and "(owner, bottom)" not in read(backup[0]) and "(reader, top)" in read(backup[0])


def test_both_changing_the_same_line_is_a_conflict_that_overwrites_nothing(replayed):
    _, v2, workspace, before, text = replayed
    assert read(workspace / CLASH) == read(v2 / CLASH) and "(owner wording)" in read(workspace / CLASH)
    assert read(workspace / "03-context-and-scope.mine.md") == before[CLASH] and "(reader wording)" in before[CLASH]
    assert "Conflicts, " in text and "03-context-and-scope.mine.md" in text and text.index("Conflicts, ") < text.index("Merged")


def test_a_page_the_owner_deleted_and_the_reader_edited_is_gone_with_the_readers_version_beside_it(replayed):
    _, _, workspace, before, _ = replayed
    assert not (workspace / OWNER_DELETES).exists()
    assert read(workspace / "12-glossary.mine.md") == before[OWNER_DELETES] and "Sam's own term." in before[OWNER_DELETES]


def test_a_page_the_reader_deleted_and_the_owner_edited_comes_back_with_a_note(replayed):
    _, v2, workspace, _, _ = replayed
    assert read(workspace / READER_DELETES) == read(v2 / READER_DELETES)
    assert "You deleted this page" in read(workspace / "04b-releases.mine.md")


def test_a_page_both_added_is_a_conflict_not_a_silent_choice(replayed):
    _, v2, workspace, before, _ = replayed
    assert read(workspace / BOTH_ADD) == read(v2 / BOTH_ADD) == notes("Priya")
    assert read(workspace / "reader-notes.mine.md") == before[BOTH_ADD]


def test_a_pending_decision_travels_with_its_page(replayed):
    _, _, workspace, _, _ = replayed
    assert "- **Pending approval:** @sam, 2026-10-12" in read(workspace / PENDING_PAGE)
    code, text = run("check", "--vault", str(workspace), "--today", V2_DAY)
    assert code == 0 and "W327" in text and "CON-001" in text, text


def test_nothing_the_reader_wrote_is_lost(replayed):
    _, _, workspace, before, _ = replayed
    everything = "\n".join(read(p) for p in workspace.rglob("*.md") if ".planner" not in p.relative_to(workspace).parts)
    for tag in ("(reader note)", "(reader, top)", "(reader wording)", "Sam's own term.", "Sam's notes."):
        assert tag in everything


# ------------------------------------------------------------------ the new baseline, freshness, the explorer

def test_the_baseline_becomes_the_new_copy_and_the_record_moves(replayed):
    _, v2, workspace, _, _ = replayed
    stamp = json.loads(read(v2 / ".planner" / "published.json"))
    published = {p.relative_to(v2).as_posix(): p.read_bytes() for p in v2.rglob("*") if p.is_file() and p.name != "dashboard.html"}
    published = {path: data for path, data in published.items() if untrusted.verdict(path)[0] == untrusted.OK}  # tool settings and hooks are left out of a reader copy
    assert {p.relative_to(workspace / ".planner" / "baseline").as_posix(): p.read_bytes() for p in (workspace / ".planner" / "baseline").rglob("*") if p.is_file()} == published
    record = json.loads(read(workspace / ".planner" / "workspace.json"))
    assert record["base_commit"] == stamp["commit"] and record["base_date"] == V2_DAY and record["base_tree_hash"] == stamp["tree_hash"]
    assert record["source_path"] == str(v2) and record["opened"] == "2026-10-12" and record["author"] == "Sam Okoye" and record["replayed"] == V2_DAY
    assert json.loads(read(workspace / ".planner" / "published.json")) == stamp
    assert not (workspace / ".planner" / "baseline.next").exists() and not (workspace / ".planner" / "baseline.previous").exists()
    assert not (workspace / ".git").exists()


def test_freshness_says_up_to_date_after_the_replay(replayed):
    _, v2, workspace, _, text = replayed
    code, said = run("freshness", "--vault", str(workspace), "--json")
    report = json.loads(said)
    assert code == 0 and report["state"] == "current" and report["have"]["date"] == V2_DAY
    assert "Your copy is the latest published" in text


def test_the_drafts_view_lists_conflicts_first_and_counts_them(replayed):
    _, _, workspace, _, _ = replayed
    assert run("explore", str(workspace), "--today", V2_DAY)[0] == 0
    from test_explorer_reader import page_data
    draft = page_data(workspace)[0]["draft"]
    conflicts = {c["path"]: c for c in draft["conflicts"]}
    assert sorted(conflicts) == sorted([CLASH, OWNER_DELETES, READER_DELETES, BOTH_ADD])
    clash = conflicts[CLASH]
    assert clash["status"] == "conflict" and clash["mine"] == "03-context-and-scope.mine.md" and clash["ranges"]
    assert ["add", next(row[1] for row in clash["lines"] if row[0] == "add" and "(reader wording)" in row[1])] in clash["lines"]
    assert draft["merged"] == [MERGE] and any(p["path"] == MERGE and p["merged"] for p in draft["pages"])
    assert not any(p["path"].endswith((".mine.md", ".mine")) for p in draft["pages"])


def test_propose_waits_until_every_conflict_is_settled(replayed):
    _, _, workspace, _, _ = replayed
    code, text = run("propose", "--vault", str(workspace), "--groups", "--today", V2_DAY)
    assert code == 2 and "still conflict" in text and "03-context-and-scope.mine.md" in text
    for mine in sorted(workspace.rglob("*.mine.md")):
        mine.unlink()
    code, text = run("propose", "--vault", str(workspace), "--groups", "--today", V2_DAY)
    assert code == 0, text
    from test_explorer_reader import page_data
    assert run("explore", str(workspace), "--today", V2_DAY)[0] == 0
    assert page_data(workspace)[0]["draft"]["conflicts"] == []


def test_check_ignores_the_saved_sides_of_conflicts(replayed):
    _, _, workspace, _, _ = replayed
    code, text = run("check", "--vault", str(workspace), "--today", V2_DAY)
    assert code == 0 and ".mine" not in text


# ------------------------------------------------------------------ proposals, refusals, repeats

def test_a_proposal_written_against_the_old_copy_is_called_stale_and_how_to_redo_it_is_said(world, tmp_path):
    src, _, workspace = world
    whys = give_every_reason(workspace, tmp_path)
    code, text = run("propose", "--vault", str(workspace), "--title", "Early thoughts", "--whys", str(whys), "--today", "2026-10-14")
    assert code == 0, text
    v2 = owner_publishes_v2(src, tmp_path)
    code, text = open_into(v2, workspace, V2_DAY)
    assert code == 0 and "Stale proposal" in text and "2026-10-14-early-thoughts" in text and "planner propose" in text
    assert (tmp_path / "proposals" / "2026-10-14-early-thoughts" / "changes.patch").is_file()


def test_the_same_copy_again_changes_nothing(replayed):
    _, v2, workspace, _, _ = replayed
    before = tree(workspace)
    code, text = open_into(v2, workspace, "2026-10-21")
    assert code == 0 and "nothing to replay" in text and tree(workspace) == before


def test_an_older_copy_is_refused_and_nothing_moves(world, tmp_path):
    src, v1, workspace = world
    v2 = owner_publishes_v2(src, tmp_path)
    assert open_into(v2, workspace, V2_DAY)[0] == 0
    before = tree(workspace)
    code, text = open_into(v1, workspace, "2026-10-22")
    assert code == 2 and "before the one" in text
    assert tree(workspace) == before


def test_a_second_replay_keeps_an_unsettled_conflict_listed(world, tmp_path):
    src, _, workspace = world
    v2 = owner_publishes_v2(src, tmp_path)
    assert open_into(v2, workspace, V2_DAY)[0] == 0
    tweak(src / OWNER_ONLY, 0, "(owner, third publish)")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "third")
    v3 = tmp_path / "v3"
    assert run("publish", "--vault", str(src), "--out", str(v3), "--today", "2026-10-25")[0] == 0
    code, text = open_into(v3, workspace, "2026-10-25")
    assert code == 0, text
    assert "(owner, third publish)" in read(workspace / OWNER_ONLY)
    assert (workspace / "03-context-and-scope.mine.md").is_file()
    assert run("propose", "--vault", str(workspace), "--groups", "--today", "2026-10-25")[0] == 2


def test_the_owner_accepting_a_readers_pending_decision_wins_and_the_marker_goes(world, tmp_path):
    """The reader proposes a decision; the owner reviews it with `proposals accept`, merges, publishes; the reader's
    re-open takes the owner's page (which already holds the change) and the marker does not come back."""
    src, _, workspace = world
    page = workspace / PENDING_PAGE
    page.write_text(read(page).replace("so no real order ever crosses.", "so no real order ever crosses, and a cap is a must.", 1), encoding="utf-8")
    whys = give_every_reason(workspace, tmp_path)
    code, text = run("propose", "--vault", str(workspace), "--title", "Cap rule", "--whys", str(whys), "--today", "2026-10-18")
    assert code == 0, text
    code, text = run("proposals", "review", str(tmp_path / "proposals" / "2026-10-18-cap-rule"), "--vault", str(src), "--today", "2026-10-18")
    assert code == 0, text
    wt = src.parent / f"{src.name}-proposal-cap-rule"
    assert run("proposals", "accept", "--vault", str(wt), "--item", "CON-001", "--by", "@priya")[0] == 0
    git(src, "merge", "-q", "--ff-only", "proposal/cap-rule")
    v2 = tmp_path / "v2"
    assert run("publish", "--vault", str(src), "--out", str(v2), "--today", V2_DAY)[0] == 0
    code, text = open_into(v2, workspace, V2_DAY)
    assert code == 0, text
    assert read(workspace / PENDING_PAGE) == read(v2 / PENDING_PAGE)
    assert "Pending approval" not in read(workspace / PENDING_PAGE) and "Decided by:** @priya" in read(workspace / PENDING_PAGE)


# ------------------------------------------------------------------ the merge itself

def lines(text):
    return text.splitlines(keepends=True)


def test_merge3_joins_hunks_that_do_not_touch():
    base = lines("a\nb\nc\nd\ne\n")
    merged, clashes = replay.merge3(base, lines("A\nb\nc\nd\ne\n"), lines("a\nb\nc\nd\nE\n"))
    assert "".join(merged) == "A\nb\nc\nd\nE\n" and clashes == []


def test_merge3_treats_adjacent_edits_as_a_clash_like_git_does():
    base = lines("a\nb\nc\n")
    merged, clashes = replay.merge3(base, lines("A\nb\nc\n"), lines("a\nB\nc\n"))
    assert merged is None and clashes


def test_merge3_agrees_when_both_made_the_same_change():
    base = lines("a\nb\nc\n")
    merged, clashes = replay.merge3(base, lines("a\nX\nc\n"), lines("a\nX\nc\n"))
    assert "".join(merged) == "a\nX\nc\n" and clashes == []


def test_merge3_keeps_line_endings_and_a_missing_final_newline():
    base = lines("a\r\nb\r\nc\r\nd\r\ne")
    merged, _ = replay.merge3(base, lines("A\r\nb\r\nc\r\nd\r\ne"), lines("a\r\nb\r\nc\r\nd\r\nE"))
    assert "".join(merged) == "A\r\nb\r\nc\r\nd\r\nE"


def test_two_conflicts_on_one_page_never_share_a_saved_file():
    taken = {"p.mine.md"}
    assert replay.mine_path("p.md", taken) == "p.mine-2.md" and replay.mine_path("data.csv", set()) == "data.csv.mine"
    assert replay.is_mine_file("a/p.mine.md") and replay.is_mine_file("p.mine-2.md") and replay.is_mine_file("data.csv.mine") and not replay.is_mine_file("mine.md")


def test_a_binary_file_both_changed_is_a_conflict_with_the_readers_bytes_kept():
    result = replay.plan({"x.pdf": b"%PDF\x00base"}, {"x.pdf": b"%PDF\x00mine"}, {"x.pdf": b"%PDF\x00theirs"})
    assert [c.kind for c in result.conflicts] == ["binary"] and result.mine == {"x.pdf.mine": b"%PDF\x00mine"} and result.write == {"x.pdf": b"%PDF\x00theirs"}


def test_a_replay_that_cannot_write_leaves_the_old_baseline_standing(world, tmp_path, monkeypatch):
    src, _, workspace = world
    v2 = owner_publishes_v2(src, tmp_path)
    from planner.edge import copies
    before = tree(workspace / ".planner" / "baseline")
    real = copies.write_folder
    monkeypatch.setattr(copies, "write_folder", lambda *a, **k: (_ for _ in ()).throw(OSError(28, "No space left on device")))
    code, text = open_into(v2, workspace, V2_DAY)
    monkeypatch.setattr(copies, "write_folder", real)
    assert code == 2 and "stopped while writing the new baseline" in text and "No space left" in text
    assert tree(workspace / ".planner" / "baseline") == before
    assert json.loads(read(workspace / ".planner" / "workspace.json"))["base_date"] == "2026-10-11"
