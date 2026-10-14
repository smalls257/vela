"""mergeplan reads where conflict hunks sit, from text alone (no repo). When in doubt a hunk is outside: an outside hunk
costs the lead a look, a hunk wrongly called inside costs someone's writing."""
import pytest

from planner import mergeplan

OPEN = "<!-- generated:{name} sha={sha}: do not edit, run planner render -->"
CLOSE = "<!-- /generated:{name} -->"


def opened(name="summary", sha="aaaaaaaa"):
    return OPEN.format(name=name, sha=sha)


def closed(name="summary"):
    return CLOSE.format(name=name)


def conflict(ours, theirs, base=None):
    lines = ["<<<<<<< HEAD", *ours]
    if base is not None:
        lines += ["||||||| merged common ancestors", *base]
    return lines + ["=======", *theirs, ">>>>>>> origin/main"]


def text(*parts):
    lines = []
    for part in parts:
        lines += part if isinstance(part, list) else [part]
    return "\n".join(lines) + "\n"


CASES = [
    ("content inside an open block",
     text("intro", opened(), *conflict(["- ours"], ["- theirs"]), closed(), "outro"), [(3, 3, "summary")]),
    ("both sides re-rendered: the opening marker differs only in its sha",
     text("intro", *conflict([opened(sha="11111111"), "- ours"], [opened(sha="22222222"), "- theirs"]), closed()),
     [(2, 3, "summary")]),
    ("diff3 base side inside the block too",
     text(opened(), *conflict(["- ours"], ["- theirs"], base=["- base"]), closed()), [(2, 2, "summary")]),
    ("hand-written text outside any block",
     text("intro", *conflict(["ours para"], ["theirs para"]), "outro"), [(2, 2, None)]),
    ("straddles the closing marker",
     text(opened(), *conflict(["- ours", closed(), "ours para"], ["- theirs", closed(), "theirs para"])),
     [(2, 4, None)]),
    ("one side enters the block from hand-written text",
     text("intro", *conflict(["hand text", opened(), "- ours"], [opened(), "- theirs"]), closed()), [(2, 4, None)]),
    ("the two sides open different blocks",
     text(*conflict([opened("a"), "- ours"], [opened("b"), "- theirs"]), closed("a")), [(1, 2, None)]),
    ("a closing marker inside the hunk",
     text(opened(), *conflict(["- ours", closed()], ["- theirs", closed()])), [(2, 3, None)]),
    ("a marker-like line that does not parse",
     text(opened(), *conflict(["<!-- generated:summary hand edited -->"], ["- theirs"]), closed()), [(2, 2, None)]),
    ("a block that never closes",
     text("intro", opened(), *conflict(["- ours"], ["- theirs"]), "outro"), [(3, 3, None)]),
    ("our side empty: reported as after the line before",
     text(opened(), "- kept", *conflict([], ["- theirs"]), closed()), [(3, 2, "summary")]),
    ("a hunk with no end runs to the end and is outside",
     text(opened(), "<<<<<<< HEAD", "- ours", closed()), [(2, 3, None)]),
]


@pytest.mark.parametrize("name,content,expected", CASES, ids=[c[0] for c in CASES])
def test_hunk_table(name, content, expected):
    assert [(h.first, h.last, h.block) for h in mergeplan.hunks(content)] == expected


def test_line_numbers_are_in_our_copy_after_earlier_hunks():
    content = text("a", *conflict(["o1", "o2"], ["t1"]), "b", *conflict(["o3"], ["t3", "t4", "t5"]), "c")
    assert [(h.first, h.last) for h in mergeplan.hunks(content)] == [(2, 3), (5, 5)]
    assert [h.lines() for h in mergeplan.hunks(content)] == ["2-3", "5"]


def test_block_state_carries_past_a_hunk_inside_it():
    content = text(opened(), *conflict(["- o1"], ["- t1"]), "- same", *conflict(["- o2"], ["- t2"]), closed(),
                   *conflict(["hand"], ["other hand"]))
    assert [h.inside for h in mergeplan.hunks(content)] == [True, True, False]


def test_a_conflicted_file_with_no_hunks_counts_as_outside():
    """A modify/delete or binary conflict leaves no markers: nothing shows it is safe."""
    assert mergeplan.plan_file("gone.md", None).outside
    assert mergeplan.plan_file("plain.md", "no markers here\n").outside
    assert not mergeplan.generated_only([mergeplan.plan_file("gone.md", None)])
    assert not mergeplan.generated_only([])


def test_generated_only_needs_every_hunk_of_every_file_inside():
    inside = mergeplan.plan_file("a.md", text(opened(), *conflict(["- o"], ["- t"]), closed()))
    outside = mergeplan.plan_file("b.md", text(*conflict(["o"], ["t"])))
    assert mergeplan.generated_only([inside])
    assert not mergeplan.generated_only([inside, outside])


def test_title_is_read_from_our_side_even_when_the_frontmatter_conflicts():
    page = text("---", "id: goals", *conflict(["title: Our goals"], ["title: Their goals"]), "---", "body")
    assert mergeplan.title_of(page) == "Our goals"
    assert mergeplan.title_of("no frontmatter\n") is None
