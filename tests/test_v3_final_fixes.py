"""The v3 final fix wave. Each test pins a rule whose loss would be silent: a quote laundered through a
record's own `## Reviews`, a yes that never reaches the ledger, an `asked` question hidden from the
views that list what holds the gates, or a warning the lead never hears about."""
import json
import shutil

from conftest import REPO, check, edit, findings, run

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
                  "copy": "new", "severity": "high", "question": "Who is liable?"}] if code == area else []
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
    close = text("skills/close/SKILL.md")
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
    close = text("skills/close/SKILL.md")
    two = close.split("## 2. Mark every capture", 1)[1].split("## 3.", 1)[0]
    assert "Write each mark into the line" not in two
    three = close.split("## 3. Write the promoted items", 1)[1].split("## 4.", 1)[0]
    assert three.index("Write each mark into the line") > three.index("### Gaps the catalogue missed")
