"""`vela findings merge`: the focused reviewers' findings combined by code, not by the session.

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
            "question": "Who takes the points back when a booking is canceled?"}
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
    same = finding(question="Who takes the points back when a booking is canceled")
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
    assert "ignored: FINANCE.json is not <AREA>.json for an area of catalog v1" in out


def test_the_text_report(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding(), finding(quote="points expire after a year", question="Do points expire?")])
    (tmp_path / "f" / "OPS.json").unlink()
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE))
    lines = out.splitlines()
    assert code == 1
    assert lines[0] == "vela findings merge: 1 kept, 0 duplicates, 1 dropped, from 4 of 5 areas."
    assert lines[1] == ("coverage: FIN found 1, 1 dropped; DAT checked, none; PTN checked, none; REG checked, none; "
                        "OPS did not run (no findings file)")
    assert lines[3] == f'1. [FIN] high, Q-FIN-03@SV-01: Who takes the points back when a booking is canceled? | "{QUOTE}" in 04a-capability-delta.md'
    assert any(l.startswith("- [FIN] its quote ") and l.endswith(": Do points expire?") for l in lines)


def test_a_missing_folder_is_a_tool_failure(tmp_path):
    code, out = run("findings", "merge", str(tmp_path / "nope"), "--vault", str(FIXTURE))
    assert code == 2 and "is not a folder" in out


def test_a_quote_with_straight_double_quotes_is_kept(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding(page="01-goals", copy="new", quote='nobody agrees on what "confirmed" means',
                                         question="What does confirmed mean?")])
    code, result = merged(tmp_path / "f")
    assert code == 0 and len(result["kept"]) == 1


def test_dotfiles_in_the_folder_are_skipped(tmp_path):
    all_ran(tmp_path / "f")
    (tmp_path / "f" / ".DS_Store").write_bytes(b"\x00\x01")
    code, result = merged(tmp_path / "f")
    assert code == 0 and result["ignored"] == []


def test_questions_in_other_scripts_are_not_one_duplicate(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding(copy="new", question="¿Quién devuelve los puntos?"),
                                 finding(copy="new", question="Кто вернёт баллы?")])
    code, result = merged(tmp_path / "f")
    assert len(result["kept"]) == 2 and result["duplicates"] == []


def test_a_findings_file_with_a_byte_order_mark_is_read(tmp_path):
    all_ran(tmp_path / "f")
    (tmp_path / "f" / "FIN.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"area": "FIN", "findings": [finding()]}).encode())
    code, result = merged(tmp_path / "f")
    assert result["areas"][0]["status"] == "found 1"


def test_a_copy_id_in_lower_case_is_the_owed_copy(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding(copy="q-fin-03@sv-01")])
    code, result = merged(tmp_path / "f")
    assert code == 0 and result["kept"][0]["copy"] == "Q-FIN-03@SV-01"


def test_the_text_report_gives_the_finding_sentence(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding()])
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE))
    assert "   Points are earned when a crossing is reserved, so a cancellation may owe points back." in out.splitlines()


def test_merge_writes_nothing(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding()])
    before = {p: p.read_bytes() for p in (tmp_path / "f").iterdir()}
    merged(tmp_path / "f")
    assert {p: p.read_bytes() for p in (tmp_path / "f").iterdir()} == before


def test_a_finding_may_address_an_open_reviewer_question(tmp_path):
    all_ran(tmp_path / "f", FIN=[finding(copy="r-fin-01"), finding(copy="R-FIN-99", question="Another?")])
    code, result = merged(tmp_path / "f")
    assert [(k["copy"], k["area"]) for k in result["kept"]] == [("R-FIN-01", "FIN")]
    assert result["dropped"][0]["reason"].startswith("it names R-FIN-99, which this vault does not owe")
    assert code == 1


def test_areas_limits_a_rerun_to_the_listed_areas(tmp_path):
    folder = tmp_path / "f"
    write(folder, "REG", {"area": "REG", "findings": []})
    write(folder, "FIN", {"area": "FIN", "findings": [finding()]})
    code, out = run("findings", "merge", str(folder), "--vault", str(FIXTURE), "--areas", "reg")
    assert "coverage: REG checked, none" in out and "FIN found" not in out
    assert "ignored: FIN.json is not one of the areas asked for with --areas REG" in out
    assert code == 1
    code, result = merged_areas(folder, "REG")
    assert [a["area"] for a in result["areas"]] == ["REG"] and result["ignored"] == ["FIN.json"] and result["kept"] == []


def merged_areas(folder, areas):
    code, out = run("findings", "merge", str(folder), "--vault", str(FIXTURE), "--json", "--areas", areas)
    return code, json.loads(out)


def test_an_area_not_listed_is_not_reported_as_did_not_run(tmp_path):
    folder = tmp_path / "f"
    write(folder, "REG", {"area": "REG", "findings": []})
    code, result = merged_areas(folder, "REG")
    assert code == 0 and result["coverage"] == "coverage: REG checked, none"


def test_areas_names_only_codes_of_the_catalog(tmp_path):
    all_ran(tmp_path / "f")
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), "--areas", "FIN,XYZ")
    assert code == 2 and "XYZ" in out


def test_a_new_question_about_a_page_this_session_did_not_change_is_dropped(tmp_path):
    # High severity: the example vault is decided, and a normal new question on a decided page is dropped.
    new = finding(copy="new", severity="high", page="03-context-and-scope", quote="the vendor contract, which runs to 2028",
                  question="Can the vendor contract be ended early?")
    all_ran(tmp_path / "f", FIN=[finding()], PTN=[new])
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), "--json",
                    "--changed", "04a-capability-delta.md")
    result = json.loads(out)
    assert code == 1
    assert [k["copy"] for k in result["kept"]] == ["Q-FIN-03@SV-01"]  # an owed copy is kept whatever page it quotes
    assert result["dropped"] == [{"area": "PTN", "question": "Can the vendor contract be ended early?",
                                  "reason": "it is a new question about a page this session did not change"}]
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), "--json",
                    "--changed", "03-context-and-scope,04a-capability-delta.md")
    assert code == 0 and len(json.loads(out)["kept"]) == 2
    assert run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), "--changed", "no-such-page")[0] == 2


def test_changed_can_name_only_some_lines_of_a_page(tmp_path):
    # High severity: the example vault is decided, and a normal new question on a decided page is dropped.
    page = (FIXTURE / "03-context-and-scope.md").read_text(encoding="utf-8")
    line = next(n for n, text in enumerate(page.splitlines(), 1) if "the vendor contract, which runs to 2028" in text)
    new = finding(copy="new", severity="high", page="03-context-and-scope", quote="the vendor contract, which runs to 2028",
                  question="Can the vendor contract be ended early?")
    all_ran(tmp_path / "f", PTN=[new])
    inside = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), "--json",
                 "--changed", f"03-context-and-scope.md:{line - 1}-{line + 1}")
    outside = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), "--json",
                  "--changed", f"03-context-and-scope.md:1-{line - 1}+{line + 5}")
    assert len(json.loads(inside[1])["kept"]) == 1 and json.loads(outside[1])["kept"] == []
    assert run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), "--changed", "03-context-and-scope.md:9-2")[0] == 2


def test_a_new_question_about_a_decided_page_is_dropped_unless_it_is_high_severity(tmp_path):
    page = (FIXTURE / "05-building-blocks" / "booking-building-blocks.md").read_text(encoding="utf-8")
    assert "state: decided" in page
    quote = "Booking decides whether a booking is held, confirmed, amended or canceled"
    normal = finding(copy="new", severity="normal", page="05-building-blocks/booking-building-blocks.md", quote=quote,
                     question="Who decides whether a booking is held, confirmed, amended or canceled after a refund?")
    all_ran(tmp_path / "f", OPS=[normal])
    changed = ["--changed", "05-building-blocks/booking-building-blocks.md"]
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), "--json", *changed)
    result = json.loads(out)
    assert result["kept"] == [] and result["dropped"][0]["reason"] == (
        "it is a new question about something already decided, and it is not high severity")
    all_ran(tmp_path / "g", OPS=[dict(normal, severity="high")])
    out = run("findings", "merge", str(tmp_path / "g"), "--vault", str(FIXTURE), "--json", *changed)[1]
    assert len(json.loads(out)["kept"]) == 1
