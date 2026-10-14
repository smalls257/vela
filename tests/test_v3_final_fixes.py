"""The v3 final fix wave. Each test pins a rule whose loss would be silent: a quote laundered through a
record's own `## Reviews`, a yes that never reaches the ledger, an `asked` question hidden from the
views that list what holds the gates, or a warning the lead never hears about."""
import json
import shutil

from conftest import REPO, check, edit, findings, run, skill_text

FIXTURE = REPO / "examples" / "unified-booking"
PLUGIN = REPO / "plugin"

DROPPED = "customers are refunded within ten days always"
RECORD = f"""\
---
id: 2026-11-20-points-dump
type: session
title: "Dump: points"
date: 2026-11-20
modes: [dump]
status: open
summary: in progress
---

# 2026-11-20 Dump: points

## Captures

- [idea] (solution lead) Merge the two booking sites so customers keep their loyalty points across both brands. ^c01

## Reviews

### 1. after the pre-mortem, 2026-11-20

- **Coverage:** FIN found 1; DAT checked, none; PTN checked, none; REG found 0, 1 dropped; OPS checked, none
- **Dropped:** [REG] its quote "{DROPPED}" is not in the written text of [[2026-11-20-points-dump]]: Who is liable?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | new | Who carries the points as a liability once both brands merge? | "customers keep their loyalty points across both brands" in [[2026-11-20-points-dump]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
"""


def vault_with_record(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    (vault / "sessions" / "2026-11-20-points-dump.md").write_text(RECORD, encoding="utf-8")
    return vault


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# ------------------------------------------------------------------ 1. no quote is laundered through ## Reviews

def merge_one(tmp_path, vault, quote, area="REG"):
    folder = tmp_path / "f"
    folder.mkdir(exist_ok=True)
    for code in ("FIN", "DAT", "PTN", "REG", "OPS"):
        found = [{"finding": "Nobody has said who is liable.", "quote": quote, "page": "2026-11-20-points-dump",
                  "copy": "new", "severity": "high", "question": "Who is liable for the points?"}] if code == area else []
        (folder / f"{code}.json").write_text(json.dumps({"area": code, "findings": found}), encoding="utf-8")
    code, out = run("findings", "merge", str(folder), "--vault", str(vault), "--json")
    return json.loads(out)


def test_a_rerun_drops_a_quote_the_first_merge_dropped_even_though_the_record_now_holds_it(tmp_path):
    vault = vault_with_record(tmp_path)
    result = merge_one(tmp_path, vault, DROPPED)
    assert result["kept"] == []
    assert result["dropped"][0]["reason"] == (f'its quote "{DROPPED}" is not in the written text of '
                                              "[[2026-11-20-points-dump]]")


def test_a_capture_on_the_same_record_is_still_quotable(tmp_path):
    vault = vault_with_record(tmp_path)
    result = merge_one(tmp_path, vault, "customers keep their loyalty points across both brands")
    assert result["dropped"] == [] and len(result["kept"]) == 1


def test_a_ledger_row_cannot_quote_the_reviews_table_or_the_dropped_line(tmp_path):
    vault = vault_with_record(tmp_path)
    ledger = vault / "11-unknowns-and-risks.md"
    rows = [
        "| R-FIN-02 | open | question: Who carries the points?; quote: \"Who carries the points as a liability "
        "once both brands merge?\" in [[2026-11-20-points-dump]]; severity: high | @hl-solution-lead | 2026-11-20 |",
        f"| R-REG-02 | open | question: Who is liable?; quote: \"{DROPPED}\" in [[2026-11-20-points-dump]]; "
        "severity: high | @hl-solution-lead | 2026-11-20 |",
    ]
    ledger.write_text(ledger.read_text(encoding="utf-8").rstrip("\n") + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    run("render", "--vault", str(vault))
    code, out = check(vault, "2026-11-20")
    e802 = [l for l in out.splitlines() if " E802 " in l]
    assert any("R-FIN-02" in l and "is not in the written text" in l for l in e802), out
    assert any("R-REG-02" in l and "is not in the written text" in l for l in e802), out


def test_an_open_row_with_bad_evidence_is_not_told_to_set_itself_open(tmp_path):
    vault = vault_with_record(tmp_path)
    ledger = vault / "11-unknowns-and-risks.md"
    row = (f"| R-REG-02 | open | question: Who is liable?; quote: \"{DROPPED}\" in [[2026-11-20-points-dump]]; "
           "severity: high | @hl-solution-lead | 2026-11-20 |")
    ledger.write_text(ledger.read_text(encoding="utf-8").rstrip("\n") + "\n" + row + "\n", encoding="utf-8")
    line = next(l for l in check(vault, "2026-11-20")[1].splitlines() if " E802 " in l)
    assert line.endswith("Fix: Correct the evidence so check can verify it."), line


# ------------------------------------------------------------------ 2. a yes to an existence question is one flow

def test_dump_captures_a_yes_as_one_capture_that_starts_with_the_copy_id():
    dump = text("skills/dump/SKILL.md")
    assert "`- [thought] (<name>) Q-FIN-01@INI-001: yes, <what>. type at close: SV`" in dump
    review = text("references/REVIEW.md")
    assert "`type at close: PTY` or `type at close: SV`" in review


def test_close_gives_a_typed_capture_one_mark_and_writes_the_existence_row():
    close = skill_text("close")
    marks = close.split("## 2. Mark every capture", 1)[1].split("## 3.", 1)[0]
    assert "Any other capture whose words start with a copy ID or a finding ID is kept as its ledger row" in marks
    assert "It gets one mark, to the subject" in marks
    typing = close.split("### Type the subjects Dump named", 1)[1].split("### The question ledger", 1)[0]
    for rule in ("`answered`, `item:` linking the new subject", "first-hand", "the row is `unknown`",
                 "write no second row"):
        assert rule in typing, rule
    assert "give each copy a capture answers its row below" not in close
    assert "write its row below for each copy a capture answers" in typing


def test_close_allocates_ids_before_it_writes_the_marks():
    close = skill_text("close")
    two = close.split("## 2. Mark every capture", 1)[1].split("## 3.", 1)[0]
    assert "Write each mark into the line" not in two
    three = close.split("## 3. Write the promoted items", 1)[1].split("## 4.", 1)[0]
    assert three.index("Write each mark into the line") > three.index("### Subjects, the question ledger and catalog gaps")
    assert "### Gaps the catalog missed" in skill_text("close")  # the ledger part, read before the marks are written


# ------------------------------------------------------------------ asked copies hold the gates, so the views list them

ASKED = "Q-FIN-02@INI-002"  # the fixture's one asked row, a normal copy


def ub(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    return vault


def ask_reviewer(vault):
    """Turn the fixture's open reviewer question into an asked one, as a lead who asked it would."""
    edit(vault / "11-unknowns-and-risks.md", "| R-FIN-01 | open | question:",
         "| R-FIN-01 | asked | capture: [[2026-11-19-owed-questions#^c01]]; question:")


def test_open_lists_an_asked_copy_and_an_asked_reviewer_question(tmp_path):
    vault = ub(tmp_path)
    ask_reviewer(vault)
    answer = json.loads(run("questions", "--open", "--json", "--vault", str(vault))[1])
    assert [c["id"] for c in answer["copies"]] == [ASKED] and answer["copies"][0]["state"] == "asked"
    assert [r["id"] for r in answer["reviewer"]] == ["R-FIN-01"] and answer["reviewer"][0]["state"] == "asked"
    assert answer["undisposed"] == 0 and answer["asked"] == 2
    assert answer["coverage"] == "57 owed, 0 undisposed, 2 asked, against catalog v1"
    out = run("questions", "--open", "--vault", str(vault))[1]
    assert any(l.startswith(f"{ASKED} | FIN | normal | asked |") for l in out.splitlines()), out


def test_the_digest_and_the_block_show_asked_copies_labeled_asked(tmp_path):
    vault = ub(tmp_path)
    answer = json.loads(run("questions", "--digest", "--json", "--vault", str(vault))[1])
    fin = next(g for g in answer["groups"] if g["entry"] == "Q-FIN-02")
    assert fin["copies"] == [ASKED] and fin["why"] == {"asked": 1}
    assert answer["coverage"] == "57 owed, 0 undisposed, 1 asked, 1 open reviewer question, against catalog v1"
    out = run("questions", "--digest", "--vault", str(vault))[1]
    assert f"   (asked) {ASKED}" in out
    run("render", "--vault", str(vault))
    page = (vault / "11-unknowns-and-risks.md").read_text(encoding="utf-8")
    assert "**Questions:** 57 owed, 0 undisposed, 1 asked, 1 open reviewer question, against catalog v1." in page
    assert f"| {ASKED} | asked | Finance and liabilities | normal | INI-002 |" in page


def test_the_coverage_line_says_nothing_of_asked_when_none_are():
    vault = REPO / "template"
    assert "asked" not in json.loads(run("questions", "--json", "--vault", str(vault))[1])["coverage"]


def test_cli_help_for_open_matches_conventions():
    from planner import cli
    parser = cli.build_parser()
    ques = next(a for a in parser._subparsers._group_actions[0].choices["questions"]._actions if "--open" in a.option_strings)
    assert ques.help == "list only copies with no row, an open row, an invalid row or an asked row"
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "`--open` lists only the copies with no row, an `open` row, an invalid row or an `asked` row" in conventions


def test_epics_says_e805_holds_asked_questions_too():
    epics = text("skills/epics/SKILL.md")
    assert "nobody has disposed, or that was asked and still waits for its answer" in epics


# ------------------------------------------------------------------ the digest's wording and the epics gate's notes

def test_the_digest_counts_lines_and_never_doubles_its_brackets(tmp_path):
    vault = ub(tmp_path)
    edit(vault / "11-unknowns-and-risks.md", "| Q-FIN-04@SV-01 | not-applicable | reason:", "| Q-FIN-04@SV-01 | not-applicable | why:")
    out = run("questions", "--digest", "--vault", str(vault))[1]
    first = out.splitlines()[0]
    assert first.endswith(" 3 lines to take, most consequential first."), first
    assert "((" not in out and "))" not in out, out
    assert "   (invalid: not-applicable) Q-FIN-04@SV-01" in out, out


def test_w805_tells_how_to_end_the_override_without_suggesting_another(tmp_path):
    vault = ub(tmp_path)
    page = vault / "11-unknowns-and-risks.md"
    edit(page, "severity: normal | @hl-solution-lead | 2026-11-19 |", "severity: high | @hl-solution-lead | 2026-11-19 |")
    edit(page, "## Question ledger\n", "## Question ledger\n\n- **Override:** E805 by @hl-solution-lead on 2026-11-20: "
         "the cancellation rule is settled in the Grill after epics\n")
    out = run("check", "--gate", "epics", "--vault", str(vault), "--today", "2026-11-20")[1]
    w805 = next(l for l in out.splitlines() if " W805 " in l)
    fix = w805.split(" Fix: ", 1)[1]
    assert "override" not in fix.split("To end the override:", 1)[1].lower(), fix
    gate = run("check", "--gate", "epics", "--vault", str(FIXTURE), "--today", "2026-11-20")[1]
    assert "add - **Override:** E805" not in gate


def test_a_passing_epics_gate_names_the_load_bearing_assumptions_it_rests_on():
    code, out = run("check", "--gate", "epics", "--vault", str(FIXTURE), "--today", "2026-11-20")
    assert code == 0
    notes = [l for l in out.splitlines() if l.startswith("Note:")]
    assert len(notes) == 1, out
    assert notes[0].startswith("Note: the epics gate passed, and it rests on ")
    assert "Q-PTN-02@PTY-01" in notes[0] and "Q-PTN-03@PTY-01" not in notes[0], notes[0]  # load-bearing: no
    plain = run("check", "--vault", str(FIXTURE), "--today", "2026-11-20")[1]
    assert "Note:" not in plain


# ------------------------------------------------------------------ W813 and the W809 scan

def template_copy(tmp_path):
    vault = tmp_path / "t"
    shutil.copytree(REPO / "template", vault)
    return vault


def test_a_ledger_page_without_its_heading_warns_in_a_plain_check(tmp_path):
    vault = template_copy(tmp_path)
    page = vault / "11-unknowns-and-risks.md"
    text = page.read_text(encoding="utf-8")
    page.write_text(text.split("## Question ledger", 1)[0], encoding="utf-8")
    code, out = check(vault, "2026-11-20")
    assert code == 0
    w813 = [l for l in out.splitlines() if " W813 " in l]
    assert w813 == ["11-unknowns-and-risks.md:1: W813 11-unknowns-and-risks.md has no ## Question ledger heading; "
                    "12 owed copies have nowhere to be recorded. Fix: Add ## Question ledger after ## Risks, "
                    "as CONVENTIONS.md shows under \"Questions and the ledger\"."], out
    gate = run("check", "--gate", "epics", "--vault", str(vault), "--today", "2026-11-20")[1]
    assert any(" E805 " in l and "The page has no ## Question ledger heading." in l for l in gate.splitlines()), gate
    assert " W813 " not in check(REPO / "template", "2026-11-20")[1]


def test_sources_titles_never_raise_w809(tmp_path):
    vault = template_copy(tmp_path)
    edit(vault / "sources.md", "|---|---|---|---|---|---|\n",
         "|---|---|---|---|---|---|\n| SRC-01 | Loyalty points rules for 2026 | @solution-lead | 2026-11-20 | exists | shared drive |\n")
    assert [f for f in findings(check(vault, "2026-11-20")[1]) if f[0] == "W809"] == []
    edit(vault / "02-constraints.md", "|---|---|---|---|\n",
         "|---|---|---|---|\n| CST-1 | Customers keep their points | SRC-01 | one balance per customer |\n")
    assert ("W809", "02-constraints.md") in findings(check(vault, "2026-11-20")[1])


# ------------------------------------------------------------------ W809 and W804 reach the lead; W807 is described as it is

def test_close_lists_w809_and_w804_to_the_lead_and_carries_them_into_the_pr():
    close = skill_text("close")
    six = close.split("## 6. Render and check", 1)[1].split("## 7.", 1)[0]
    for said in ("W809", "W804", "possibly an untyped subject", "orphaned", "no longer owed",
                 "offer to type the subject", "fix the row"):
        assert said in six, said
    questions_line = next(l for l in close.splitlines() if l.strip().startswith("- **Questions:**"))
    assert "W809" in questions_line and "W804" in questions_line


def test_grill_says_w807_prints_only_under_its_gate_and_the_capture_is_the_record():
    grill = text("skills/grill/SKILL.md")
    assert "The W807 stays in the check output as the record." not in grill
    assert "W807 prints only under `--gate grill --item`" in grill and "the capture is the record" in grill


def test_w807_fix_text_points_at_the_capture(tmp_path):
    vault = ub(tmp_path)
    page = vault / "11-unknowns-and-risks.md"
    page.write_text("".join(l for l in page.read_text(encoding="utf-8").splitlines(keepends=True)
                            if not l.startswith("| Q-OPS-01@APP-kiosks | answered")), encoding="utf-8")
    out = run("check", "--gate", "grill", "--item", "APP-kiosks", "--vault", str(vault), "--today", "2026-11-20")[1]
    w807 = [l for l in out.splitlines() if " W807 " in l]
    assert w807 and all("stays in the check output" not in l for l in w807), out
    assert all("decided with <copy IDs> open (W807)" in l for l in w807), out


# ------------------------------------------------------------------ 3. the READMEs explain v3

def readme_section(title):
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert f"\n## {title}\n" in readme, title
    return readme.split(f"\n## {title}\n", 1)[1].split("\n## ", 1)[0]


def test_the_readme_has_a_v3_section_a_returning_user_can_follow():
    v3 = readme_section("What v3 adds: the questions the plan owes")
    for said in ("29 entries", "per subject", "generic", "`planner questions`", "`--digest`", "`--open`", "`--stats`",
                 "`11-unknowns-and-risks.md`", "`open`", "`asked`", "`answered`", "`assumed`", "`unknown`",
                 "`not-applicable`", "evidence", "five", "area-reviewer", "time and tokens", "`planner findings merge`",
                 "`## Reviews`", "catalog entries", "W806", "W807", "E805", "override", "voicescore"):
        assert said in v3, said
    for mode in ("dump", "discover", "shape", "grill"):
        assert f"/planner:{mode}" in v3, mode
    import yaml
    data = yaml.safe_load((PLUGIN / "catalog" / "questions.yaml").read_text(encoding="utf-8"))
    assert f"{len(data['entries'])} entries" in v3


def test_start_here_tomorrow_agrees_with_v3():
    start = readme_section("Start here tomorrow")
    assert "review checkpoint" in start and "question ledger" in start
    assert "planner questions --digest" in start


def test_the_template_checklist_renders_after_the_initiative_and_points_at_the_digest():
    checklist = (REPO / "template" / "README.md").read_text(encoding="utf-8").split("## Setup checklist", 1)[1]
    steps = [l for l in checklist.splitlines() if l[:1].isdigit()]
    initiative = next(i for i, l in enumerate(steps) if "set `initiative`" in l)
    assert "planner render" in steps[initiative + 1]
    assert sum("planner questions --digest" in l for l in steps) == 1
