"""`vela decide` and the `decide` apply kind (overhaul Task 16): grill section 4's nine writes per decision, made by code.

Each test is a rule the grill skill's prose held before (state, Decision, Why verbatim, Dissent, Override, Decided by,
Pending approval, the Changes row, the capture's mark, the agenda line, the commit); a deleted rule fails here by name.
The vault is the mini fixture with one item of each target kind added, so every kind is decided against the same pages.
"""
import json
import shutil
import subprocess

import pytest

from conftest import MINI, edit, run
from vela import cli, closegate, decisions, parse
from vela.decisions import decide, record as records, textedit
from vela.edge import apply as disk
from vela.flowcheck import standing

RECORD_ID = "2026-10-20-grill-stock"
RECORD = f"sessions/{RECORD_ID}.md"
TODAY = "2026-10-20"
WHY = 'Because the till | can\'t wait **long** for [[01-goals|the goal]]'
CAPTURES = [
    '- [thought] (claude) Read back: the stock level contract, the count left for a product ID ^c01',
    '- [answer] (@priya) "Yes, as read." ^c02',
    f'- [answer] (@priya) "{WHY}" ^c03',
    '- [answer] (@priya) "ok" ^c04',
    '- [worry] (@stock-team) "The count can lag by a minute." ^c05',
    '- [answer] (@priya) "Go ahead; the owner answers by Friday." ^c06',
    '- [thought] (claude, from Stock team) Stock team present and agreed ^c07',
    '- [answer] (claude) "Yes" ^c08',
    '- [thought] (claude) Read back: criteria one and two of selling a basket ^c09',
    '- [answer] (@priya) "Yes to those two." ^c10',
    '- [thought] (claude) Read back: criterion three of selling a basket ^c11',
    '- [answer] (@priya) "Yes to that one too." ^c12',
    '- [thought] (claude) Read back: Shop carries selling a basket, through the sale API ^c13',
    '- [answer] (@priya) "Changed my mind: the count must be live." ^c14',
    '- [answer] (@priya) "Yes, Shop carries that." ^c15',
]
STOCK = "05-building-blocks/stock-building-blocks.md"
SHOP = "05-building-blocks/shop-building-blocks.md"
UNKNOWNS = "11-unknowns-and-risks.md"
CAPABILITY = "capabilities/CAP-001-sell-a-basket.md"
EPIC = "13-epics/EPC-001-till-sells-through-shop.md"
SLICE = "slices/SLC-001-a-till-sells.md"
RELEASES = "04b-releases.md"
STRATEGY = "04-solution-strategy.md"

CON_002_OPEN = """- **Change:** unchanged
- **State:** assumption
- **Options considered:** the existing read API (picked); a new push feed: rejected, Stock is unchanged
- **Tested by:** consumer tests in the shop pipeline.
"""
ERROR_CASE = "| count | | ok | the count left | | |\n| unknown_product | | error | refused: no such product | | |\n"
BLOCKER = """
### UNK-003 Count freshness

- **Question:** How old may the stock count be?
- **Owner:** @stock-team
- **Opened:** 2026-10-19
- **State:** open
- **Ask by:** 2026-11-01
- **Blocks:** [[stock-building-blocks#CON-002 Stock level|CON-002]]
"""
PAGES = {
    CAPABILITY: """---
id: CAP-001
type: capability
title: Sell a basket
state: assumption
owner: "@mini-lead"
authored: authored
---

# Sell a basket

The till sells a basket of products.

## Functional requirements

### CAP-001.FR1 Sell a basket

The till sells every product in a basket in one sale.

- **State:** assumption
- **Options considered:** one sale per basket (picked); one sale per product: rejected, receipts multiply

- A basket of products is sold in one sale.
""",
    EPIC: """---
id: EPC-001
type: epic
title: Till sells through Shop
initiative: INI-900
state: draft
owner: "@mini/till-team"
authored: authored
apps: [APP-till, APP-shop]
---

# EPC-001 Till sells through Shop

The till sells through the Shop's sale API.

## Done when

### A basket sells in one sale

A basket of products is sold in one sale.

- Trace: CAP-001.FR1  ·  AC1

### A refused basket is said so

An empty basket is refused and the till says why.

- Trace: CON-001  ·  AC2

### The receipt has a VAT line

Every receipt carries one VAT line.

- Trace: AC3
""",
    SLICE: """---
id: SLC-001
type: slice
title: A till sells
initiative: INI-900
authored: authored
---

# A till sells

The tracer: a till sells a basket through the Shop.

- **Flows:** [[FLO-001-buy|FLO-001]]
- **Owner:** @mini-lead

## History

- 2026-10-19: written. Not planned yet.
""",
    RELEASES: """---
id: releases
type: initiative-section
title: Releases
initiative: INI-900
state: assumption
owner: "@mini-lead"
authored: authored
---

# Releases

One release, for the pilot shop.

## Release one: pilot shop

- **Target:** 2026-12-01
- **State:** assumption
""",
    STRATEGY: """---
id: solution-strategy
type: initiative-section
title: Solution strategy
initiative: INI-900
arc42: "§4"
state: assumption
owner: "@mini-lead"
authored: authored
---

# Solution strategy

The till sells through one Shop API.

- **Options considered:** one Shop API (picked); the till calls Stock itself: rejected, two places to change
""",
}
ALLOCATION = """
## Requirements allocated

| Requirement | Share | Through | State |
|---|---|---|---|
| [[CAP-001-sell-a-basket#CAP-001.FR1 Sell a basket\\|CAP-001.FR1]] | takes the basket and returns one receipt | CON-001 | assumption |
"""


def make_vault(tmp_path, captures=CAPTURES, agenda=()):
    root = tmp_path / "vault"
    shutil.copytree(MINI, root)
    edit(root / STOCK, "- **Change:** unchanged\n- **State:** fact\n", CON_002_OPEN)
    edit(root / STOCK, "| count | | ok | the count left | | |\n", ERROR_CASE)
    for path, text in PAGES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    shop = (root / SHOP).read_text(encoding="utf-8")
    (root / SHOP).write_text(shop.replace("\n## Contracts this app consumes", ALLOCATION + "\n## Contracts this app consumes"),
                             encoding="utf-8")
    lines = ["---", f"id: {RECORD_ID}", "type: session", "date: 2026-10-20", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", ""]
    if agenda:
        lines += ["## Agenda", "", *agenda, ""]
    lines += ["## Captures", "", *captures, ""]
    (root / RECORD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def block_con_002(root):
    text = (root / UNKNOWNS).read_text(encoding="utf-8")
    (root / UNKNOWNS).write_text(text.replace("\n### UNK-001 ", BLOCKER + "\n### UNK-001 ", 1), encoding="utf-8")


def opened(root):
    found, problem = records.open_record([("", RECORD, (root / RECORD).read_text(encoding="utf-8"))])
    assert problem is None, problem
    return found


def view(root, flows=None):
    staged = textedit.attach(decisions.Staged(cli.load_vault(root), disk.reader(root)), TODAY, [])
    staged.flows = flows
    return staged


def plan(root, items, flows=None):
    decision = decisions.Decision("decide", RECORD_ID, items, {})
    writes, refusals = decisions.plan(decision, view(root, flows), opened(root))
    return {w.path: w.text for w in writes}, refusals


def filed(root, items, flows=None):
    writes, refusals = plan(root, items, flows)
    assert not refusals, [r.rule + ": " + r.plain + " / " + r.fix for r in refusals]
    return writes


def item(ident="CON-002", **more):
    base = {"id": ident, "readback": "^c01", "yes": "^c02", "by": "@priya", "reader": False}
    if ident == "CON-002":
        base["provider"] = "^c07"
    base.update(more)
    return base


def rules(refusals):
    return [r.rule for r in refusals]


def history_of(text, ident=""):
    """The bullets under `## History` (under `#### <ident>` for an item)."""
    body = text.split("\n## History", 1)[1]
    if ident:
        body = body.split(f"#### {ident}", 1)[1].split("\n#### ", 1)[0]
    return [line for line in body.split("\n") if line.startswith("- ")]


def git_init(root):
    for args in (["init", "-q", "-b", "session/x"], ["add", "-A"], ["commit", "-q", "-m", "start"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def git_log(root):
    return subprocess.run(["git", "log", "--format=%s"], cwd=root, check=True, capture_output=True,
                          text=True).stdout.splitlines()


# ------------------------------------------------------------------ first callers

def test_gate4_fail_refused_without_override(tmp_path):
    root = make_vault(tmp_path)
    block_con_002(root)
    writes, refusals = plan(root, [item()])
    assert writes == {} and "GATE-4" in rules(refusals), refusals
    said = next(r for r in refusals if r.rule == "GATE-4")
    assert "How old may the stock count be" in said.plain and "UNK-003" not in said.plain
    assert "GATE-4" in said.override and "until" in said.override, "the route carries a suggested end date"
    overridden = filed(root, [item(overrides=[{"rules": ["GATE-4"], "reason": "^c06", "until": "2026-11-01"}])])
    bullets = history_of(overridden[STOCK], "CON-002")
    assert "- **Override:** GATE-4 by @priya on 2026-10-20 until 2026-11-01: Go ahead; the owner answers by Friday." \
        in bullets, bullets
    _, undated = plan(root, [item(overrides=[{"rules": ["GATE-4"], "reason": "^c06"}])])
    assert "override-until" in rules(undated), "a standing override with no end is refused, a date offered"


def test_why_copied_verbatim(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, [item(why="^c03")])
    bullets = history_of(writes[STOCK], "CON-002")
    assert bullets[0] == f"- **Decision:** [[{RECORD_ID}]]"
    why = next(b for b in bullets if b.startswith("- **Why:** "))
    assert textedit.unescape(why[len("- **Why:** "):]) == WHY, why
    assert parse.BULLET.match(why), "the escaped words still read as one fact bullet"
    _, claude_why = plan(root, [item(why="^c01")])
    assert "consent-why-not-theirs" in rules(claude_why), "a reason in Claude's words is not the lead's reason"


def test_reader_adds_pending_approval(tmp_path):
    root = make_vault(tmp_path)
    owner = filed(root, [item()])
    assert not any("Pending approval" in b for b in history_of(owner[STOCK], "CON-002"))
    reader = filed(root, [item(reader=True)])
    assert "- **Pending approval:** @priya, 2026-10-20" in history_of(reader[STOCK], "CON-002")
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "workspace.json").write_text('{"author": "Priya"}', encoding="utf-8")
    (root / ".vela" / "handle").write_text("priya\n", encoding="utf-8")
    code, out = run("decide", "CON-002", "--vault", str(root), "--today", TODAY, "--readback", "^c01", "--yes", "^c02",
                    "--provider", "^c07", "--json")
    assert code == 0, out
    data = json.loads(out)
    assert data["reader"] is True and data["commit"] is None, data
    assert "- **Pending approval:** @priya, 2026-10-20" in (root / STOCK).read_text(encoding="utf-8")


def test_epic_needs_yes_per_criterion_group(tmp_path):
    root = make_vault(tmp_path)
    one_group = [{"criteria": "AC1-AC2", "readback": "^c09", "yes": "^c10"}]
    _, refusals = plan(root, [item("EPC-001", groups=one_group)])
    assert "decide-epic-criteria" in rules(refusals), refusals
    assert "third" not in refusals[0].plain and "AC3" not in refusals[0].plain
    both = one_group + [{"criteria": "AC3", "readback": "^c11", "yes": "^c12"}]
    writes = filed(root, [item("EPC-001", groups=both)])
    assert "\nstate: decided\n" in writes[EPIC]
    assert history_of(writes[EPIC])[0] == f"- **Decision:** [[{RECORD_ID}]]"
    assert f"| EPC-001 | draft | decided | [[{RECORD_ID}#^c02]] |" in writes[RECORD]
    _, early = plan(root, [item("EPC-001", groups=[{"criteria": "AC1-AC3", "readback": "^c11", "yes": "^c10"}])])
    assert "consent-yes-before-readback" in rules(early), "a group's yes comes after its own read-back"
    waived = filed(root, [item("EPC-001", overrides=[{"rules": ["GATE-3"], "reason": "^c06"}])])
    assert "\nstate: decided\n" in waived[EPIC], "GATE-3 overridden lets the epic through with no group yeses"


def test_slice_planned_requires_flowcheck_or_dated_override(tmp_path):
    root = make_vault(tmp_path)
    _, unchecked = plan(root, [item("SLC-001")])
    assert "flow check" in rules(unchecked), "no recorded check is never a pass"
    partial = {"SLC-001": standing.Standing(standing.NOT_FULLY, "not fully checked", "2026-10-19")}
    _, still = plan(root, [item("SLC-001", overrides=[{"rules": ['"flow check"'], "reason": "^c06"}])], partial)
    assert "flow check" in rules(still), "no override covers a check that did not finish"
    findings = {"SLC-001": standing.Standing(standing.FINDINGS, "1 finding", "2026-10-19", ("invariant broken",))}
    _, found = plan(root, [item("SLC-001")], findings)
    said = next(r for r in found if r.rule == "flow check")
    assert "dated override" in said.fix, "a finding is set aside by the dated flow-check override, which its standing reads"
    # The checker's standing applies a dated override that covers every finding, so the slice then stands as passed.
    passed = {"SLC-001": standing.Standing(standing.PASSED, "passed", "2026-10-19")}
    writes = filed(root, [item("SLC-001")], passed)
    page = writes[SLICE]
    assert "- **Status:** planned" in page and "**Decision:**" not in page, "a slice is planned, not decided"
    assert "- 2026-10-20: planned by @priya, in [[2026-10-20-grill-stock]]" in history_of(page)
    assert f"| SLC-001 | - | planned | [[{RECORD_ID}#^c02]] |" in writes[RECORD]


def test_agenda_line_updated(tmp_path):
    root = make_vault(tmp_path, agenda=["- CON-002: GATE-3 confirmed yes, status open, override: GATE-5",
                                        "- CON-001: GATE-3 confirmed yes, status decided"])
    writes = filed(root, [item()])
    assert "- CON-002: GATE-3 confirmed yes, status decided, override: GATE-5" in writes[RECORD]
    assert writes[RECORD].count("- CON-002: ") == 1


def test_commit_message_grill_id_decided(tmp_path):
    root = make_vault(tmp_path)
    git_init(root)
    code, out = run("decide", "CON-002", "--vault", str(root), "--today", TODAY, "--readback", "^c01", "--yes", "^c02",
                    "--provider", "^c07", "--json")
    assert code == 0, out
    assert git_log(root)[0] == "grill: CON-002 decided"
    shown = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=root, check=True,
                           capture_output=True, text=True).stdout.split()
    assert sorted(shown) == sorted([RECORD, STOCK]), "only the record and the changed page, by exact path"
    assert json.loads(out)["commit"], out


def test_decide_writes_the_changes_row_the_gate_reads(tmp_path):
    root = make_vault(tmp_path)
    before = cli.load_vault(root)
    writes = filed(root, [item(why="^c03")])
    for path, text in writes.items():
        (root / path).write_text(text, encoding="utf-8")
    after = cli.load_vault(root)
    changes = closegate.consent_changes(closegate.states(before), closegate.states(after), after)
    assert [(c.item, c.before, c.after) for c in changes] == [("CON-002", "assumption", "decided")]
    problems, consent = closegate.judge(changes, writes[RECORD], RECORD_ID, after)
    assert problems == [], problems
    assert [c.words for c in consent] == ["Yes, as read."]
    said = closegate.captures(writes[RECORD])
    mark = "keep: [[stock-building-blocks#CON-002 Stock level|CON-002]] (decided)"
    assert [said[n].mark for n in ("02", "03", "01", "07")] == [mark] * 4, "every capture the decision filed is kept"
    assert said["04"].mark == "", "a capture the decision didn't use is left for close"


def test_decided_item_exits_3_offering_reopen(tmp_path):
    root = make_vault(tmp_path)
    git_init(root)
    before = (root / SHOP).read_text(encoding="utf-8")
    code, out = run("decide", "CON-001", "--vault", str(root), "--today", TODAY, "--readback", "^c01", "--yes", "^c02",
                    "--json")
    assert code == 3, out
    data = json.loads(out)
    assert data["wrote"] == [] and any("--reopen" in c["command"] for c in data["needs_lead"]), data
    assert (root / SHOP).read_text(encoding="utf-8") == before and git_log(root) == ["start"]
    code, said = run("decide", "CON-001", "--vault", str(root), "--today", TODAY, "--readback", "^c01", "--yes",
                     "^c02", "--for-lead")
    assert code == 3 and "Sale API" in said and "reopen" in said, said


def test_reopen_writes_changes_row(tmp_path):
    root = make_vault(tmp_path, agenda=["- CON-001: GATE-3 confirmed yes, status decided"])
    git_init(root)
    before = cli.load_vault(root)
    code, out = run("decide", "--reopen", "CON-001", "--why", "^c14", "--vault", str(root), "--today", TODAY, "--json")
    assert code == 0, out
    record = (root / RECORD).read_text(encoding="utf-8")
    assert f"| CON-001 | decided | assumption | [[{RECORD_ID}#^c14]] |" in record
    assert "- CON-001: GATE-3 confirmed yes, status open" in record
    assert "\n- **State:** assumption\n" in (root / SHOP).read_text(encoding="utf-8")
    assert git_log(root)[0] == "grill: CON-001 reopened"
    after = cli.load_vault(root)
    changes = closegate.consent_changes(closegate.states(before), closegate.states(after), after)
    assert closegate.judge(changes, record, RECORD_ID, after)[0] == [], "the change of mind is on record"
    code, out = run("decide", "--reopen", "CON-001", "--why", "^c04", "--vault", str(root), "--today", TODAY)
    assert code == 1, "a bare 'ok' is no reason to reopen, and the item isn't decided any more anyway"


def test_contract_needs_provider_capture(tmp_path):
    root = make_vault(tmp_path)
    _, refusals = plan(root, [item(provider=None)])
    assert "decide-provider-stands" in rules(refusals), refusals
    _, missing = plan(root, [item(provider="^c99")])
    assert "consent-capture-missing" in rules(missing)
    reason = [{"rules": ['"a decided contract records where the provider stands"'], "reason": "^c06"}]
    filed(root, [item(provider=None, overrides=reason)])


def test_allocation_row_decided(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, [item("CAP-001.FR1@APP-shop", readback="^c13", yes="^c15")])
    row = next(line for line in writes[SHOP].split("\n") if line.startswith("| [[CAP-001-sell-a-basket"))
    assert parse.split_row(row)[3] == "decided", row
    assert "| CAP-001.FR1@APP-shop | assumption | decided |" in writes[RECORD]
    assert "**Decision:**" not in writes[SHOP].split("## Requirements allocated")[1], "the page's Decision answers"
    _, unread = plan(root, [item("CAP-001.FR1@APP-shop", readback="^c01", yes="^c15")])
    assert "decide-row-readback" in rules(unread), "a row is read back with its app"


def test_yes_before_readback_refused(tmp_path):
    root = make_vault(tmp_path)
    _, refusals = plan(root, [item(readback="^c03", yes="^c02")])
    assert "consent-yes-before-readback" in rules(refusals)
    assert refusals[0].plain == "Your yes came before I read the final wording back, so I'll read it again."
    code, out = run("decide", "CON-002", "--vault", str(root), "--today", TODAY, "--readback", "^c03", "--yes", "^c02",
                    "--provider", "^c07", "--for-lead")
    assert code == 1 and "read the final wording back" in out, out


# ------------------------------------------------------------------ the rest of section 4

def test_bare_ok_and_claudes_yes_are_refused(tmp_path):
    root = make_vault(tmp_path)
    assert "consent-bare-non-yes" in rules(plan(root, [item(yes="^c04")])[1])
    assert "consent-not-a-person" in rules(plan(root, [item(yes="^c08")])[1])


def test_dissent_decided_by_and_override_bullets(tmp_path):
    root = make_vault(tmp_path)
    writes = filed(root, [item(dissent="^c05", on_behalf_of="@stock-team",
                               overrides=[{"rules": ["GATE-5"], "reason": "^c06"}])])
    bullets = history_of(writes[STOCK], "CON-002")
    assert "- **Dissent:** @stock-team, 2026-10-20: The count can lag by a minute." in bullets
    assert "- **Override:** GATE-5 by @priya on 2026-10-20: Go ahead; the owner answers by Friday." in bullets
    assert "- **Decided by:** @priya, on behalf of @stock-team" in bullets
    _, refusals = plan(root, [item(on_behalf_of="@stock-team")])
    assert "decide-on-behalf-needs-gate-5" in rules(refusals), "deciding for an absent owner goes with GATE-5"


def test_fr_page_and_release_kinds(tmp_path):
    root = make_vault(tmp_path)
    fr = filed(root, [item("CAP-001.FR1")])
    assert "- **State:** decided" in fr[CAPABILITY].split("### CAP-001.FR1")[1].split("\n## ")[0]
    assert f"- **Decision:** [[{RECORD_ID}]]" in history_of(fr[CAPABILITY], "CAP-001.FR1")
    page = filed(root, [item("solution-strategy")])
    assert "\nstate: decided\n" in page[STRATEGY] and history_of(page[STRATEGY])[0].startswith("- **Decision:**")
    release = filed(root, [item("Release one: pilot shop")])
    section = release[RELEASES].split("## Release one: pilot shop")[1].split("\n## ")[0]
    assert "- **State:** decided" in section
    assert f"- **Decision:** [[{RECORD_ID}]]" in history_of(release[RELEASES])


def test_a_flag_another_kind_takes_is_refused(tmp_path):
    root = make_vault(tmp_path)
    _, refusals = plan(root, [item("CAP-001.FR1", provider="^c07")])
    assert "decide-field-not-for-kind" in rules(refusals), "a provider capture on a requirement is a lost answer"
    _, missing = plan(root, [item("CON-404")])
    assert "decide-missing" in rules(missing)


def test_for_lead_says_names_not_ids(tmp_path):
    root = make_vault(tmp_path)
    git_init(root)
    code, out = run("decide", "CON-002", "--vault", str(root), "--today", TODAY, "--readback", "^c01", "--yes", "^c02",
                    "--provider", "^c07", "--for-lead")
    assert code == 0 and "Stock level" in out, out
    block_con_002(root)
    code, out = run("decide", "SLC-001", "--vault", str(root), "--today", TODAY, "--readback", "^c01", "--yes", "^c02",
                    "--for-lead")
    assert code == 1 and "flow check" in out, out


def test_the_decide_kind_files_through_vela_apply(tmp_path):
    root = make_vault(tmp_path)
    path = root / ".vela" / "decisions" / RECORD_ID / "01-decide.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"version": 1, "kind": "decide", "session": RECORD_ID, "items": [item(why="^c03")]}),
                    encoding="utf-8")
    code, out = run("apply", str(path), "--vault", str(root), "--today", TODAY, "--json")
    assert code == 0, out
    assert f"| CON-002 | assumption | decided | [[{RECORD_ID}#^c02]] |" in (root / RECORD).read_text(encoding="utf-8")
    assert run("apply", "--schema", "decide", "--json")[0] == 0


def test_dispatch_names_one_module_per_kind():
    assert decide.KINDS == ("allocation_row", "slice", "epic", "contract", "fr", "release", "page")
    for kind in decide.KINDS:
        module = decide.kind_module(kind)
        assert module.KIND and callable(module.target) and callable(module.set_state), kind
