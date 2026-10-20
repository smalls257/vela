"""W373: a concern page says what is not looked at once, on its "Not looked at yet:" line, and nowhere else.

The Violation this prevents is padding (a Paper Tiger of a page: every cell filled, nothing added). The model filled the
Why cell of an `unexamined` row with "Nobody has looked at this yet." and a Strategy with "No ownership strategy is set
yet", which the precision judge counts as padding. The rule is in code, so the skill line is not the only defense.
"""
from conftest import REPO, check

CONCERN = """---
id: concern-ownership
type: concern
title: Ownership
arc42: "§8"
owner: "@solution-lead"
authored: authored
---

# Ownership

Which team owns each app.

## Strategy
{strategy}

## Per app

Not looked at yet: [[desk-building-blocks|Desk]]

| App | State | Why |
|---|---|---|
{row}
"""


def findings(vault, today="2026-10-19"):
    code, out = check(vault, today)
    return [l for l in out.splitlines() if " W373 " in l]


def make(tmp_path, strategy="", row=""):
    import shutil
    vault = tmp_path / "v"
    shutil.copytree(REPO / "tests" / "sim" / "scale" / "snapshots" / "civic-permits" / "empty", vault)
    page = next(vault.rglob("concern-ownership.md"))
    apps = sorted(vault.rglob("*-building-blocks.md"))
    (page.parent / page.name).write_text(CONCERN.format(strategy=strategy, row=row).replace("desk-building-blocks|Desk", apps[0].stem + "|App"), encoding="utf-8")
    return vault, apps[0].stem


def test_blank_why_and_empty_strategy_are_accepted(tmp_path):
    vault, app = make(tmp_path, row="")
    assert findings(vault) == []


def test_a_sentence_in_an_unexamined_why_cell_is_padding(tmp_path):
    vault, app = make(tmp_path, row="| [[%s|App]] | unexamined | Nobody has looked at this yet. |" % "X")
    page = next(vault.rglob("concern-ownership.md"))
    page.write_text(page.read_text().replace("[[X|App]]", f"[[{app}|App]]"), encoding="utf-8")
    assert len(findings(vault)) == 1


def test_a_placeholder_strategy_is_padding_and_a_real_one_is_not(tmp_path):
    vault, _ = make(tmp_path, strategy="No ownership strategy is set yet.")
    assert len(findings(vault)) == 1
    vault2, _ = make(tmp_path / "b", strategy="Each app is owned by the team that runs it today, until the pilot ends.")
    assert findings(vault2) == []
