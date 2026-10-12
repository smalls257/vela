"""Four fixes from the v3 full run (2026-10-06-144750-coastal-merger). Each test pins a rule whose loss
would be silent: the same gap raised by three areas reaching the lead three times, a deferral recorded as
a ruling-out, a quote that is on its page but says nothing about its finding, a long digest that buries
what is consequential, and a skipped area that would read as never considered."""
import json
import shutil

import pytest

from conftest import REPO, check, edit, findings, run

FIXTURE = REPO / "examples" / "unified-booking"
PLUGIN = REPO / "plugin"

# The run's three hotel questions: one gap, three focus areas, three ledger rows (R-DAT-07, R-PTN-07, R-REG-09).
HOTEL_DAT = ("What personal data does the hotel feed carry, and what terms or data-sharing agreement cover it, "
             "given the changes to identity and ownership?")
HOTEL_PTN = ("Do the hotel agreements exist, and do they cover the nightly feed? Is it safe to treat them as out "
             "of scope when ownership and identity change?")
HOTEL_REG = ("What do the hotel package terms and the feed's data-sharing basis say, and does a cross-party "
             "package create liability toward customers that the identity change affects?")
HOTEL_QUOTE = "- **Agreements:** none known"

# The run's F1.2: a budget question whose quote is about who has a stake in the date.
F12_QUESTION = ("Who pays to build the one-customer capability, and which budget carries the running cost of the "
                "shared layer and of both ferry and rail systems running in parallel?")
F12_QUOTE = ("Who else in the merged company has a stake in the date, such as finance, marketing or the CIO's "
             "sponsor, and what does the date mean to them?")


def vault_copy(tmp_path):
    dest = tmp_path / "v"
    shutil.copytree(FIXTURE, dest, ignore=shutil.ignore_patterns(".git"))
    return dest


def with_hotels(tmp_path):
    """The fixture plus a partner-hotels party whose agreements nobody knows, as the run's vault had."""
    vault = vault_copy(tmp_path)
    edit(vault / "03-context-and-scope.md", "## Value held for customers",
         "### PTY-03 Partner hotels\n\n- **Relationship:** partner\n"
         f"{HOTEL_QUOTE}\n\n## Value held for customers")
    edit(vault / "01-goals.md", "## Why now", f"## Notes\n\n{F12_QUOTE}\n\n## Why now")
    return vault


def finding(question, quote, page, copy="new", severity="normal"):
    return {"finding": "The pages say nothing more.", "quote": quote, "page": page, "copy": copy,
            "severity": severity, "question": question}


def write_all(folder, **areas):
    folder.mkdir(exist_ok=True)
    for code in ("FIN", "DAT", "PTN", "REG", "OPS"):
        (folder / f"{code}.json").write_text(json.dumps({"area": code, "findings": areas.get(code, [])}), encoding="utf-8")


def merged(folder, vault, *extra):
    code, out = run("findings", "merge", str(folder), "--vault", str(vault), "--json", *extra)
    return code, json.loads(out)


# ------------------------------------------------------------------ 2. cross-area near-duplicates

def test_the_run_hotel_questions_are_near_duplicates_only_with_their_shared_quote():
    from planner import reviews
    pairs = [(HOTEL_DAT, HOTEL_PTN), (HOTEL_DAT, HOTEL_REG), (HOTEL_PTN, HOTEL_REG)]
    # Jaccard >= 0.6 alone merges none of them: three areas ask about one gap in their own words.
    assert all(reviews.similarity(a, b) < reviews.NEAR for a, b in pairs)
    assert all(reviews.similarity(HOTEL_DAT, b) >= reviews.NEAR_SAME_QUOTE for b in (HOTEL_PTN, HOTEL_REG))


def test_similarity_reads_content_words_with_a_crude_stem():
    from planner import reviews
    assert reviews.content_words("Who carries the balances?") == reviews.content_words("who carry the balance")
    assert reviews.similarity("Who owns the ferry database?", "Who is the owner of the ferry database?") >= 0.6
    assert reviews.similarity("Who pays for the change?", "Which regulator licenses the kiosks?") == 0


def test_three_areas_raising_the_hotel_gap_become_one_finding_listing_all_three(tmp_path):
    vault = with_hotels(tmp_path)
    page = "03-context-and-scope.md"
    write_all(tmp_path / "f", DAT=[finding(HOTEL_DAT, HOTEL_QUOTE, page, severity="high")],
              PTN=[finding(HOTEL_PTN, HOTEL_QUOTE, page)], REG=[finding(HOTEL_REG, HOTEL_QUOTE, page)])
    code, result = merged(tmp_path / "f", vault)
    assert code == 0, result["dropped"]
    assert [(k["n"], k["areas"], k["copy"], k["question"]) for k in result["kept"]] == [
        (1, ["DAT", "PTN", "REG"], "new", HOTEL_DAT)]
    assert [(d["area"], d["question"], d["same_as"]) for d in result["duplicates"]] == [
        ("PTN", HOTEL_PTN, 1), ("REG", HOTEL_REG, 1)], "every area's own wording stays in the merge's output"
    assert result["coverage"] == ("coverage: FIN checked, none; DAT found 1; PTN found 1; REG found 1; "
                                  "OPS checked, none")


def test_a_near_duplicate_of_an_open_reviewer_question_takes_its_id(tmp_path):
    question = "Does a cancelled booking take its points back, and who tells the loyalty scheme?"
    quote, page = "because points are earned at reservation", "04a-capability-delta.md"
    write_all(tmp_path / "f", FIN=[finding(question, quote, page)],
              OPS=[finding(question.replace("Does", "So does"), quote, page, copy="R-FIN-01")])
    code, result = merged(tmp_path / "f", FIXTURE)
    assert [(k["areas"], k["copy"]) for k in result["kept"]] == [(["FIN", "OPS"], "R-FIN-01")]


def test_findings_about_different_owed_copies_never_merge(tmp_path):
    quote, page = "because points are earned at reservation", "04a-capability-delta.md"
    question = "Who takes the points back when a booking is cancelled?"
    write_all(tmp_path / "f", FIN=[finding(question, quote, page, copy="Q-FIN-03@SV-01")],
              DAT=[finding(question, quote, page, copy="new")])
    code, result = merged(tmp_path / "f", FIXTURE)
    assert [k["copy"] for k in result["kept"]] == ["Q-FIN-03@SV-01", "new"]


def test_the_same_quote_with_a_different_question_stays_two_findings(tmp_path):
    quote, page = "because points are earned at reservation", "04a-capability-delta.md"
    write_all(tmp_path / "f", FIN=[finding("Who carries the points as a liability on the books?", quote, page)],
              OPS=[finding("Which team answers the phone when points go missing at reservation?", quote, page)])
    code, result = merged(tmp_path / "f", FIXTURE)
    assert [k["areas"] for k in result["kept"]] == [["FIN"], ["OPS"]]


def test_the_text_report_lists_every_area_of_a_merged_finding(tmp_path):
    vault = with_hotels(tmp_path)
    page = "03-context-and-scope.md"
    write_all(tmp_path / "f", DAT=[finding(HOTEL_DAT, HOTEL_QUOTE, page)], PTN=[finding(HOTEL_PTN, HOTEL_QUOTE, page)])
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(vault))
    assert f"1. [DAT, PTN] normal, new: {HOTEL_DAT} | \"{HOTEL_QUOTE}\" in {page}" in out.splitlines()
    assert f"- [PTN] same as 1: {HOTEL_PTN}" in out.splitlines()


# ------------------------------------------------------------------ 4. a quote must be about its finding

def test_the_run_f1_2_budget_question_quoting_a_stake_in_the_date_is_dropped(tmp_path):
    vault = with_hotels(tmp_path)
    write_all(tmp_path / "f", FIN=[finding(F12_QUESTION, F12_QUOTE, "01-goals.md", copy="Q-FIN-02@INI-002",
                                           severity="high")])
    code, result = merged(tmp_path / "f", vault)
    assert code == 1 and result["kept"] == []
    assert result["dropped"] == [{"area": "FIN", "question": F12_QUESTION,
                                  "reason": "the quote does not mention what the finding is about"}]
    assert result["areas"][0]["status"] == "found 0, 1 dropped"


def test_a_quote_sharing_a_content_word_with_the_question_is_kept(tmp_path):
    write_all(tmp_path / "f", PTN=[finding("Can the vendor contract be ended early?",
                                           "the vendor contract, which runs to 2028", "03-context-and-scope.md")])
    code, result = merged(tmp_path / "f", FIXTURE)
    assert code == 0 and len(result["kept"]) == 1


def test_the_subject_name_counts_as_what_the_finding_is_about(tmp_path):
    # SV-01 is "Loyalty points": the quote names points, the question does not.
    write_all(tmp_path / "f", FIN=[finding("Who owes them back after a cancellation?",
                                           "because points are earned at reservation", "04a-capability-delta.md",
                                           copy="Q-FIN-03@SV-01")])
    code, result = merged(tmp_path / "f", FIXTURE)
    assert code == 0 and len(result["kept"]) == 1


def test_a_gap_quote_is_read_with_its_heading_and_bullet_label(tmp_path):
    # A gap is quoted where the answer belongs: "- **Agreements:** none known" under "PTY-03 Partner hotels".
    vault = with_hotels(tmp_path)
    write_all(tmp_path / "f", REG=[finding(HOTEL_REG, HOTEL_QUOTE, "03-context-and-scope.md")],
              PTN=[finding("Who signed for the partners, and can it be ended?", HOTEL_QUOTE, "03-context-and-scope.md")])
    code, result = merged(tmp_path / "f", vault)
    assert code == 0, result["dropped"]
    assert len(result["kept"]) == 2


def test_a_reviewer_question_s_own_words_count_for_a_finding_that_addresses_it(tmp_path):
    write_all(tmp_path / "f", FIN=[finding("Who tells them?", "because points are earned at reservation",
                                           "04a-capability-delta.md", copy="R-FIN-01")])
    code, result = merged(tmp_path / "f", FIXTURE)
    assert code == 0 and result["kept"][0]["copy"] == "R-FIN-01"


# ------------------------------------------------------------------ 1. a checkpoint reviews only the areas in scope

def test_a_skipped_area_is_in_the_coverage_line_and_keeps_the_merge_clean(tmp_path):
    folder = tmp_path / "f"
    folder.mkdir()
    (folder / "FIN.json").write_text(json.dumps({"area": "FIN", "findings": []}), encoding="utf-8")
    (folder / "DAT.json").write_text(json.dumps({"area": "DAT", "findings": []}), encoding="utf-8")
    code, result = merged(folder, FIXTURE, "--areas", "FIN,DAT", "--skipped", "PTN,REG,OPS")
    assert code == 0
    assert result["coverage"] == ("coverage: FIN checked, none; DAT checked, none; PTN skipped (nothing in scope); "
                                  "REG skipped (nothing in scope); OPS skipped (nothing in scope)")
    assert [(a["area"], a["ran"], a["skipped"]) for a in result["areas"]][2] == ("PTN", False, True)


def test_a_skipped_area_with_a_file_has_its_file_ignored_and_said(tmp_path):
    folder = tmp_path / "f"
    write_all(folder)
    code, out = run("findings", "merge", str(folder), "--vault", str(FIXTURE), "--areas", "FIN,DAT,PTN,REG",
                    "--skipped", "OPS")
    assert "OPS skipped (nothing in scope)" in out
    assert "ignored: OPS.json is for an area skipped with --skipped OPS" in out
    assert code == 1


@pytest.mark.parametrize("argv, message", [
    (["--skipped", "OPS"], "--skipped goes with --areas"),
    (["--areas", "FIN,OPS", "--skipped", "OPS"], "OPS is in both --areas and --skipped"),
    (["--areas", "FIN", "--skipped", "XYZ"], "XYZ"),
])
def test_skipped_names_areas_that_did_not_run(tmp_path, argv, message):
    write_all(tmp_path / "f")
    code, out = run("findings", "merge", str(tmp_path / "f"), "--vault", str(FIXTURE), *argv)
    assert code == 2 and message in out


def test_questions_json_gives_each_copy_its_subject_page():
    code, out = run("questions", "--vault", str(FIXTURE), "--area", "FIN", "--json")
    copies = {c["id"]: c for c in json.loads(out)["copies"]}
    assert copies["Q-FIN-03@SV-01"]["subject_page"] == "03-context-and-scope.md"
    assert copies["Q-FIN-02@INI-002"]["subject_page"] is None


def test_the_area_reviewer_runs_on_a_named_model():
    text = (PLUGIN / "agents" / "area-reviewer.md").read_text(encoding="utf-8")
    front = text.split("---")[1]
    assert "\nmodel: sonnet\n" in front


def test_review_md_dispatches_on_that_model_and_skips_areas_out_of_scope():
    text = (PLUGIN / "references" / "REVIEW.md").read_text(encoding="utf-8")
    assert "model: sonnet" in text and text.count("sonnet") >= 2, "the subagent and the general-purpose fallback"
    assert "skipped (nothing in scope)" in text and "--skipped" in text
    assert "## Question ledger" in text, "reviewers read the ledger page only above its ledger section"


# ------------------------------------------------------------------ 3. a deferral is not a ruling-out

RUN_DEFERRAL = "ruled out for now, the pick depends on UNK-011 and UNK-024 (Monday)"


def na_row(copy, reason):
    return f"| {copy} | not-applicable | reason: {reason} | @hl-solution-lead | 2026-11-19 |"


@pytest.mark.parametrize("reason", [
    RUN_DEFERRAL,
    "second-order, the lead ruled out the partner agreements for now",
    "TBD with legal",
    "pending legal review",
    "revisit later",
    "we will decide after Monday's call",
    "not yet decided",
    "until we hear from the vendor",
    "parked until after the pilot",
    "deferred to phase 2",
    "waiting on the CFO",
    "once the CFO confirms the budget",
    "to be confirmed by Finance",
])
def test_a_not_applicable_reason_that_defers_is_e802_pointing_at_unknown_or_assumed(tmp_path, reason):
    from planner import questions
    assert questions.deferral_cue(reason), reason
    vault = vault_copy(tmp_path)
    page = vault / "11-unknowns-and-risks.md"
    text = page.read_text(encoding="utf-8")
    old = next(line for line in text.split("\n") if line.startswith("| Q-FIN-04@SV-01 | not-applicable |"))
    edit(page, old, na_row("Q-FIN-04@SV-01", reason))
    code, out = check(vault, "2026-11-20")
    line = next(l for l in out.splitlines() if " E802 " in l and "Q-FIN-04@SV-01" in l)
    assert "not-applicable means it does not apply, never not yet" in line
    assert "unknown" in line and "UNK-" in line and "assumed" in line


@pytest.mark.parametrize("reason", [
    "Booking sells single ferry crossings, and nothing is sold with another party",
    "the loyalty scheme holds the balances and stays out of scope until INI-004, so INI-002 sets no expiry or closure rule",
    "payment stays with Tidepay under its existing contract (CST-2), so INI-002 asks for no change to the agreement",
    "There are no pending refunds or held deposits in this app",
    "The scheme closed in 2019, two years later than planned, and holds no balances",
    "Closed in 2019, and the contract ended three months later",
    "Ruled out after reading the vendor contract: it has no change-of-control clause",
    "The lead decided after the workshop that no partner is involved",
    "The app does not depend on any outside party",
    "Tidepay holds the card data until 2030 under its own contract, and Booking never sees it",
    "No data leaves the ferry company once the booking is made",
])
def test_a_reason_that_rules_out_is_not_a_deferral(reason):
    from planner import questions
    assert questions.deferral_cue(reason) == "", reason


def test_the_run_hotel_rows_are_e802(tmp_path):
    vault = vault_copy(tmp_path)
    page = vault / "11-unknowns-and-risks.md"
    rows = "\n".join(
        f"| {rid} | not-applicable | question: {q}; quote: \"because points are earned at reservation\" in "
        f"[[04a-capability-delta]]; reason: {RUN_DEFERRAL} | @sim-lead | 2026-10-06 |"
        for rid, q in (("R-DAT-07", HOTEL_DAT), ("R-PTN-07", HOTEL_PTN), ("R-REG-09", HOTEL_REG)))
    text = page.read_text(encoding="utf-8")
    last = next(line for line in text.split("\n") if line.startswith("| R-FIN-01 | open | question:"))
    edit(page, last, last + "\n" + rows)
    code, out = check(vault, "2026-11-20")
    flagged = sorted(l.split(" E802 ")[1].split(" ")[0] for l in out.splitlines() if " E802 " in l)
    assert flagged == ["R-DAT-07", "R-PTN-07", "R-REG-09"]


def test_conventions_says_not_applicable_is_never_not_yet():
    for copy in (REPO / "template", REPO / "tests" / "stub-conventions", FIXTURE):
        assert "not-applicable means it does not apply, never not yet" in (copy / "CONVENTIONS.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ 2. the digest: consequential lines first, the rest counted

def long_digest_vault(tmp_path):
    """The fixture with six normal reviewer questions open in FIN and two in OPS, and one high one."""
    vault = vault_copy(tmp_path)
    page = vault / "11-unknowns-and-risks.md"
    quote = '"because points are earned at reservation" in [[04a-capability-delta]]'
    extra = [f"| R-FIN-{n:02d} | open | question: Normal question {n} about points?; quote: {quote} | @x | 2026-11-19 |"
             for n in range(2, 8)]
    extra += [f"| R-OPS-{n:02d} | open | question: Ops question {n} about points?; quote: {quote} | @x | 2026-11-19 |"
              for n in range(1, 3)]
    extra += [f"| R-REG-01 | open | question: High question about points?; quote: {quote}; severity: high | @x | 2026-11-19 |"]
    text = page.read_text(encoding="utf-8")
    last = next(line for line in text.split("\n") if line.startswith("| R-FIN-01 | open | question:"))
    edit(page, last, last + "\n" + "\n".join(extra))
    return vault


def test_the_digest_shows_consequential_lines_in_full_and_counts_the_rest_by_area(tmp_path):
    vault = long_digest_vault(tmp_path)
    code, out = run("questions", "--vault", str(vault), "--open", "--digest")
    lines = out.splitlines()
    assert code == 0
    assert lines[0].endswith("11 lines to take, most consequential first: 1 in full, 10 more counted by area.")
    assert lines[1] == "1. [REG] high: High question about points?"
    assert "FIN: 8 more (normal). List them: planner questions --open --digest --all --area FIN" in lines
    assert "OPS: 2 more (normal). List them: planner questions --open --digest --all --area OPS" in lines
    assert lines[-1] == "Every line in full: planner questions --open --digest --all"


def test_digest_all_prints_every_line_in_full(tmp_path):
    vault = long_digest_vault(tmp_path)
    code, out = run("questions", "--vault", str(vault), "--open", "--digest", "--all")
    lines = out.splitlines()
    assert lines[0].endswith("11 lines to take, most consequential first.")
    assert sum(1 for l in lines if l[:1].isdigit()) == 11
    assert not any("more (normal)" in l for l in lines)


def test_the_digest_hides_nothing_from_open_or_json(tmp_path):
    vault = long_digest_vault(tmp_path)
    code, out = run("questions", "--vault", str(vault), "--open", "--digest", "--json")
    assert len(json.loads(out)["groups"]) == 11
    code, out = run("questions", "--vault", str(vault), "--open")
    assert sum(1 for l in out.splitlines() if l.startswith("R-")) == 10


def test_all_goes_only_with_digest():
    code, out = run("questions", "--vault", str(FIXTURE), "--all")
    assert code == 2 and "--all goes with --digest" in out


def test_review_md_and_skills_describe_the_short_digest():
    review = (PLUGIN / "references" / "REVIEW.md").read_text(encoding="utf-8")
    section = review.split("## 5. The digest")[1].split("## 6.")[0]
    assert "--all" in section and "more (normal)" in section
    conventions = (FIXTURE / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "--all" in conventions and "counted by area" in conventions


def test_the_fixture_stays_clean():
    code, out = check(FIXTURE, "2026-11-20")
    assert code == 0, out
    code, out = run("check", "--vault", str(FIXTURE), "--today", "2026-11-20", "--gate", "epics")
    assert not [f for f in findings(out) if f[0].startswith("E")], out
