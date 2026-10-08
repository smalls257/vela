"""History at the end of a page, under "## History": the page opens with what is true now, and every rule still
reads an item's Decision, Override and Options considered from "#### <ID>" there."""
import shutil

from conftest import REPO, run

FIXTURE = REPO / "examples" / "unified-booking"
PAGE = "05-building-blocks/booking-building-blocks.md"
DECISION = "- **Decision:** [[2026-08-26-kiosks-and-rollout]]\n"


def moved(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    path = vault / PAGE
    text = path.read_text(encoding="utf-8")
    assert text.count(DECISION) == 1
    path.write_text(text.replace(DECISION, "", 1).rstrip("\n") + "\n\n## History\n\n#### CON-001\n\n" + DECISION,
                    encoding="utf-8")
    return vault


def test_an_items_decision_under_history_still_counts(tmp_path):
    vault = moved(tmp_path)
    code, out = run("check", "--vault", str(vault), "--today", "2026-11-20")
    assert code == 0, out
    assert "CON-001" not in out or "W415" in out


def test_without_the_history_decision_check_fails(tmp_path):
    vault = moved(tmp_path)
    path = vault / PAGE
    path.write_text(path.read_text(encoding="utf-8").replace(DECISION, ""), encoding="utf-8")
    code, out = run("check", "--vault", str(vault), "--today", "2026-11-20")
    assert code == 1 and "CON-001" in out


import sys
sys.path.insert(0, str(REPO / "plugin" / "lib"))
from planner import reading  # noqa: E402

PAGE_TEXT = """# Coach

- **Decision:** [[2026-10-08-grill]]
- **Override:** GATE-4 by @lead on 2026-10-08: the demo date

Coach teaches one stock at a time (SRC-02; [[04-solution-strategy#First instruments|First instruments]], decided).

<!-- generated:app-context sha=12345678: do not edit, run planner render -->
diagram
<!-- /generated:app-context -->

### CON-001 Coach entry

- **Change:** new
- **Decision:** [[2026-10-08-grill]]
- **Consumers:** [[tickertalk-building-blocks|TickerTalk]], blocked by [[11-unknowns-and-risks#UNK-027 Brightwater review|UNK-027]]
"""


def test_the_reading_layout_puts_what_is_true_first_and_history_last():
    out = reading.arrange(PAGE_TEXT)
    assert out.index("Coach teaches") < out.index("## Diagram") < out.index("<details><summary>History</summary>")
    assert "### Coach entry" in out and "CON-001 Coach entry" not in out.split("<details>")[0]
    assert "(SRC-02" not in out and "<sup>[[04-solution-strategy#First instruments|First instruments]], [[sources|source]]</sup>" in out
    assert "|Brightwater review]]" in out and "|UNK-027]]" not in out
    history = out.split("<details><summary>History</summary>")[1]
    assert "GATE-4 by @lead" in history and "#### Coach entry" in history
    assert out.count("**Decision:**") == 2 and "**Change:** new" in out.split("<details>")[0]
    assert "generated:" not in out


def test_a_page_with_only_its_template_is_not_started():
    assert reading.not_started("# Constraints\n\nWhat this initiative cannot change.\n\n| ID | Constraint |\n|---|---|\n",
                               "initiative-section", "inkling")
    assert reading.not_started("# Cost\n\nRunning cost.\n\n## Per app\n\n| App | State | Why |\n|---|---|---|\n"
                               "| [[coach-building-blocks\\|Coach]] | unexamined | |\n", "concern", "")
    assert not reading.not_started("# Constraints\n\nOne line.\n\n| ID | Constraint |\n|---|---|\n| CST-1 | March | \n",
                                   "initiative-section", "inkling")


def test_style_names_what_reads_as_a_log():
    problems = [why for _, why in reading.style_problems(PAGE_TEXT, "app-building-blocks")]
    assert sum("above ## History" in p for p in problems) == 3
    assert any("bare source ID" in p for p in problems)
    clean = "# Coach\n\nCoach teaches one stock at a time, on [[sources#SRC-02|delayed quotes]].\n\n## History\n\n- **Decision:** [[g]]\n"
    assert reading.style_problems(clean, "app-building-blocks") == []
    assert any("no opening prose" in why for _, why in reading.style_problems("# Coach\n\n## Containers\n", "app-building-blocks"))


def test_an_empty_section_is_left_out_of_the_reading_view():
    out = reading.arrange("# Cost\n\nRunning cost.\n\n## Strategy\n\n## Per app\n\n| App | State |\n|---|---|\n| A | unknown |\n")
    assert "## Strategy" not in out and "## Per app" in out


def test_a_source_row_is_a_valid_anchor(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    page = vault / "03-context-and-scope.md"
    page.write_text(page.read_text(encoding="utf-8") + "\nAs [[sources#SRC-04|the latency measurement]] shows.\n",
                    encoding="utf-8")
    assert "E202" not in run("check", "--vault", str(vault), "--today", "2026-11-20")[1]


def test_history_under_an_id_with_no_item_on_the_page_is_an_error(tmp_path):
    vault = moved(tmp_path)
    path = vault / PAGE
    path.write_text(path.read_text(encoding="utf-8") + "\n#### CON-999\n\n- **Override:** GATE-4 by @a on 2026-11-20: x\n",
                    encoding="utf-8")
    code, out = run("check", "--vault", str(vault), "--today", "2026-11-20")
    assert code == 1 and "E323" in out and "CON-999" in out


def test_a_party_under_history_is_not_a_mistyped_heading(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault)
    page = vault / "03-context-and-scope.md"
    text = page.read_text(encoding="utf-8")
    first = next(l for l in text.splitlines() if l.startswith("### PTY-"))
    page.write_text(text + f"\n## History\n\n#### {first.split()[1]}\n\n- **Dissent:** @a, 2026-11-20: no\n", encoding="utf-8")
    assert "E810" not in run("check", "--vault", str(vault), "--today", "2026-11-20")[1]


def test_rewriting_never_crosses_a_code_span():
    hostile = "x (SRC-01 `) <a href=\"https://evil.example\">y</a> <details> ` z `f(SRC-01)`"
    out = reading.arrange(hostile)
    assert "`) <a href=\"https://evil.example\">y</a> <details> `" in out and "`f(SRC-01)`" in out


def test_only_template_pages_at_inkling_are_hidden():
    one_line = "# Teach a stock trade\n\nA reader learns to place one stock trade.\n"
    assert not reading.not_started(one_line, "capability", "assumption")
    assert not reading.not_started(one_line, "", "")
    assert reading.not_started("# Glossary\n\nTerms.\n", "initiative-section", "inkling")


def test_planner_style_prints_each_problem_with_its_file_line(tmp_path):
    vault = moved(tmp_path)
    code, out = run("style", "05-building-blocks/booking-building-blocks.md", "--vault", str(vault))
    lines = (vault / PAGE).read_text(encoding="utf-8").splitlines()
    for row in out.splitlines()[1:]:
        n = int(row.split(":")[1])
        if "bullet sits above" in row:
            assert lines[n - 1].lstrip().startswith("- **"), row
    assert code in (0, 1) and out.startswith("planner style:")
    assert run("style", "no-such-page", "--vault", str(vault))[0] == 2
