"""`planner findings merge`: the focused reviewers' findings combined by code, not by the session.

Union, then remove exact duplicates. Never vote. A finding whose quote is not on the page it cites
is dropped and listed. An area that failed says "did not run" and why, so it never reads as
"checked, none"."""
import json

import pytest

from conftest import REPO, run

FIXTURE = REPO / "examples" / "unified-booking"
QUOTE = "because points are earned at reservation"


def finding(**over):
    base = {"finding": "Points are earned when a crossing is reserved, so a cancellation may owe points back.",
            "quote": QUOTE, "page": "04a-capability-delta.md", "copy": "Q-FIN-03@SV-01", "severity": "high",
            "question": "Who takes the points back when a booking is cancelled?"}
    base.update(over)
    return base


def write(folder, area, data):
    folder.mkdir(exist_ok=True)
    (folder / f"{area}.json").write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def all_ran(folder, **areas):
    for code in ("FIN", "DAT", "PTN", "REG", "OPS"):
        write(folder, code, {"area": code, "findings": areas.get(code, [])})


def merged(folder):
    code, out = run("findings", "merge", str(folder), "--vault", str(FIXTURE), "--json")
    return code, json.loads(out)


def test_every_area_ran_and_every_quote_is_on_its_page(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding()], PTN=[finding(copy="new", severity="Normal", page="03-context-and-scope",
                                                         quote="the vendor contract, which runs to 2028",
                                                         question="Can the vendor contract be ended early?")])
    code, result = merged(tmp_path / "f")
    assert code == 0
    assert result["coverage"] == "coverage: FIN found 1; DAT checked, none; PTN found 1; REG checked, none; OPS checked, none"
    assert [(k["n"], k["area"], k["severity"], k["copy"], k["page"]) for k in result["kept"]] == [
        (1, "FIN", "high", "Q-FIN-03@SV-01", "04a-capability-delta.md"),
        (2, "PTN", "normal", "new", "03-context-and-scope.md")]
    assert result["dropped"] == [] and result["duplicates"] == [] and result["ignored"] == []


def test_a_quote_not_on_its_page_is_dropped_and_listed(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding(), finding(quote="points expire after a year", question="Do points expire?")])
    code, result = merged(tmp_path / "f")
    assert code == 1
    assert result["dropped"] == [{"area": "FIN", "question": "Do points expire?",
                                  "reason": 'its quote "points expire after a year" is not in the written text of [[04a-capability-delta]]'}]
    assert result["areas"][0]["status"] == "found 1, 1 dropped"


def test_whitespace_and_curly_quotes_do_not_drop_a_true_quote(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding(quote="because  points\nare earned at reservation"),
                                 finding(page="04a-capability-delta.md", copy="new",
                                         quote="Booking’s state-changed event rather than", question="Whose events are these?")])
    code, result = merged(tmp_path / "f")
    assert [d["reason"] for d in result["dropped"]] == []
    assert len(result["kept"]) == 2


@pytest.mark.parametrize("over, reason", [
    ({"page": "nowhere.md"}, "it cites nowhere.md, which is not a page in this vault"),
    ({"copy": "Q-FIN-03@SV-09"}, "it names Q-FIN-03@SV-09, which this vault does not owe"),
    ({"severity": "urgent"}, "severity 'urgent' is not high or normal"),
    ({"quote": ""}, "it has no quote"),
    ({"quote": "too few words"}, "has fewer than 4 words"),
    ({"question": 7}, "it has no question"),
])
def test_a_finding_that_cannot_be_checked_is_dropped_with_its_reason(tmp_path, over, reason):
    all_ran(tmp_path / "f", FIN=[finding(**over)])
    code, result = merged(tmp_path / "f")
    assert code == 1 and result["kept"] == []
    assert reason in result["dropped"][0]["reason"]


def test_duplicates_across_areas_are_removed_without_a_vote(tmp_path):
    same = finding(question="Who takes the points back when a booking is cancelled")
    all_ran(tmp_path / "f", FIN=[finding()], DAT=[same], OPS=[finding(copy="new")])
    code, result = merged(tmp_path / "f")
    assert code == 0
    assert [k["area"] for k in result["kept"]] == ["FIN", "OPS"], "the same question about a new copy is its own finding"
    assert result["duplicates"] == [{"area": "DAT", "question": same["question"], "same_as": 1}]
    assert result["areas"][1]["status"] == "found 1"


@pytest.mark.parametrize("content, status", [
    (None, "did not run (no findings file)"),
    ("{not json", "did not run (REG.json is not JSON: "),
    ({"area": "REG", "error": "the subagent hit its turn limit"}, "did not run (the reviewer reported: the subagent hit its turn limit)"),
    ({"area": "OPS", "findings": []}, "did not run (its output says area 'OPS')"),
    ({"area": "REG"}, "did not run (its output has no findings list)"),
    ([], "did not run (its output is not a findings object)"),
    ({"area": "reg", "findings": []}, "checked, none"),
])
def test_an_area_that_failed_never_reads_as_checked(tmp_path, content, status):
    folder = tmp_path / "f"
    all_ran(folder)
    (folder / "REG.json").unlink()
    if content is not None:
        write(folder, "REG", content)
    code, result = merged(folder)
    reg = next(a for a in result["areas"] if a["area"] == "REG")
    assert reg["status"].startswith(status)
    assert code == (0 if status == "checked, none" else 1)


def test_a_reply_in_one_code_fence_is_read_and_prose_around_it_is_not(tmp_path):
    folder = tmp_path / "f"
    all_ran(folder)
    write(folder, "FIN", "```json\n" + json.dumps({"area": "FIN", "findings": [finding()]}) + "\n```\n")
    write(folder, "DAT", "Here is what I found:\n" + json.dumps({"area": "DAT", "findings": []}))
    code, result = merged(folder)
    statuses = {a["area"]: a["status"] for a in result["areas"]}
    assert statuses["FIN"] == "found 1"
    assert statuses["DAT"].startswith("did not run (DAT.json is not JSON")
    assert code == 1


def test_a_file_for_no_area_is_ignored_and_said(tmp_path):
    folder = tmp_path / "f"
    all_ran(folder)
    write(folder, "FINANCE", {"area": "FIN", "findings": [finding()]})
    code, out = run("findings", "merge", str(folder), "--vault", str(FIXTURE))
    assert code == 1
    assert "ignored: FINANCE.json is not <AREA>.json for an area of catalogue v1" in out


def test_the_text_report(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding(), finding(quote="points expire after a year", question="Do points expire?")])
    (tmp_path / "f" / "OPS.json").unlink()
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE))
    lines = out.splitlines()
    assert code == 1
    assert lines[0] == "planner findings merge: 1 kept, 0 duplicates, 1 dropped, from 4 of 5 areas."
    assert lines[1] == ("coverage: FIN found 1, 1 dropped; DAT checked, none; PTN checked, none; REG checked, none; "
                        "OPS did not run (no findings file)")
    assert lines[3] == f'1. [FIN] high, Q-FIN-03@SV-01: Who takes the points back when a booking is cancelled? | "{QUOTE}" in 04a-capability-delta.md'
    assert any(l.startswith("- [FIN] its quote ") and l.endswith(": Do points expire?") for l in lines)


def test_a_missing_folder_is_a_tool_failure(tmp_path):
    code, out = run("findings", "merge", str(tmp_path / "nope"), "--vault", str(FIXTURE))
    assert code == 2 and "is not a folder" in out


def test_merge_writes_nothing(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding()])
    before = {p: p.read_bytes() for p in (tmp_path / "f").iterdir()}
    merged(tmp_path / "f")
    assert {p: p.read_bytes() for p in (tmp_path / "f").iterdir()} == before
