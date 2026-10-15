"""The `agenda`, `override`, `defer` and `resolve` apply kinds (overhaul Task 15): grill's agenda lines, the lead's
override in their own words with an end date for a standing rule, an owed question deferred to an owner, and an
unknown resolved from a source."""
from test_apply_add import RECORD, filed, make_vault, plan, write
from vela import override as overrides
from vela.decisions import override as override_kind

UNKNOWNS = "11-unknowns-and-risks.md"
STOCK = "05-building-blocks/stock-building-blocks.md"
CAPTURES = ['- [readback] (claude) The agenda: the stock level contract ^c01',
            '- [answer] (@priya) "Yes, that agenda." ^c02',
            '- [why] (@priya) "Stores need it | now, and **today**." ^c03',
            '- [why] (claude) It is simpler ^c04',
            '- [answer] (@priya) "The CFO answers that; ask by 2026-11-05." ^c05',
            '- [answer] (@priya) "The rig is in the Leeds store." ^c06']


def test_agenda_writes_and_updates_lines(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES)
    writes = filed(root, "agenda", [{"id": "CON-002", "readback": "^c01", "yes": "^c02", "status": "open"},
                                    {"id": "CON-001", "status": "off-agenda: GATE-2"}])
    record = writes[RECORD]
    assert "## Agenda\n\n- CON-002: GATE-3 confirmed yes, status open\n- CON-001: GATE-3 confirmed no, status " \
           "off-agenda: GATE-2\n" in record
    assert record.index("## Agenda") < record.index("## Captures")
    (root / RECORD).write_text(record, encoding="utf-8")
    writes = filed(root, "agenda", [{"id": "CON-002", "readback": "^c01", "yes": "^c02", "status": "open",
                                     "override": ["GATE-5"]}])
    assert "- CON-002: GATE-3 confirmed yes, status open, override: GATE-5\n- CON-001:" in writes[RECORD]
    assert writes[RECORD].count("## Agenda") == 1


def test_agenda_refuses_a_bad_status_and_a_bare_yes(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES + ['- [answer] (@priya) "ok" ^c07'])
    _, refusals = plan(root, "agenda", [{"id": "CON-002", "status": "maybe"}])
    assert [r.rule for r in refusals] == ["agenda-status"]
    _, refusals = plan(root, "agenda", [{"id": "CON-002", "readback": "^c01", "yes": "^c07", "status": "open"}])
    assert [r.rule for r in refusals] == ["consent-bare-non-yes"]


def test_override_standing_without_until_refused_with_suggested_date(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES)
    _, refusals = plan(root, "override", [{"on": "CON-002", "rules": ["GATE-4"], "reason": "^c03"}])
    assert [r.rule for r in refusals] == ["override-until"]
    assert "2026-11-19" in refusals[0].fix  # 30 days on: the item feeds no release with a target ahead
    assert "date" in refusals[0].plain


def test_override_writes_the_leads_words_verbatim(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES)
    writes = filed(root, "override", [{"on": "CON-002", "rules": ["GATE-4"], "reason": "^c03",
                                       "until": "2026-11-30"}])
    page = writes[STOCK]
    bullet = next(line for line in page.split("\n") if line.startswith("- **Override:**"))
    assert page.index("## History") < page.index("#### CON-002") < page.index(bullet)
    parsed = overrides.parse(bullet[len("- **Override:** "):])
    assert not parsed.problem, parsed.problem
    assert parsed.rules == ("GATE-4",) and parsed.by == "@priya" and parsed.date == "2026-10-20"
    assert parsed.until == "2026-11-30"
    assert override_kind.words_of(parsed.reason) == "Stores need it | now, and **today**."
    event = filed(root, "override", [{"on": "CON-002", "rules": ["GATE-5"], "reason": "^c03"}])
    assert " until " not in next(l for l in event[STOCK].split("\n") if l.startswith("- **Override:**"))


def test_override_reason_must_be_the_leads(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES)
    _, refusals = plan(root, "override", [{"on": "CON-002", "rules": ["GATE-5"], "reason": "^c04"}])
    assert [r.rule for r in refusals] == ["consent-why-not-theirs"]
    _, refusals = plan(root, "override", [{"on": "CON-002", "rules": ["GATE-9"], "reason": "^c03"}])
    assert [r.rule for r in refusals] == ["override-rule"]


def test_defer_writes_an_unknown_blocking_the_copy(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES)
    writes = filed(root, "defer", [{"copy": "Q-FIN-02@INI-900", "name": "Stored value liability", "owner": "@cfo",
                                    "capture": "^c05", "question": "Who carries the vouchers as money owed?"}])
    page = writes[UNKNOWNS]
    assert "### UNK-003 Stored value liability" in page
    assert "- **Blocks:** Q-FIN-02@INI-900" in page and "- **Ask by:** 2026-11-05" in page
    assert "(open) ^c05" in writes[RECORD]


def test_resolve_sets_the_unknown_resolved(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES)
    write(root, "sources.md", (root / "sources.md").read_text(encoding="utf-8").rstrip("\n")
          + "\n| SRC-02 | Priya, first-hand | @priya | 2026-10-20 | exists | first-hand: @priya |\n")
    writes = filed(root, "resolve", [{"id": "UNK-001", "answer": "^c06", "source": "SRC-02"}])
    page = writes[UNKNOWNS]
    block = page[page.index("### UNK-001"):page.index("### UNK-002")]
    assert "- **State:** resolved" in block and "**Ask by:**" not in block
    assert "- **Outcome:** The rig is in the Leeds store, as [[sources#SRC-02|Priya, first-hand]] says." in block
    assert "- **Resolved in:** [[2026-10-20-grill-stock]]" in block
    assert "| UNK-001 | open | resolved | [[2026-10-20-grill-stock#^c06]] |" in writes[RECORD]
    assert "(resolved) ^c06" in writes[RECORD]
    _, refusals = plan(root, "resolve", [{"id": "UNK-002", "answer": "^c06", "source": "SRC-02"}])
    assert [r.rule for r in refusals] == ["resolve-not-open"]
