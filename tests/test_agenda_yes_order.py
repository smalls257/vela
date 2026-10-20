"""The agenda's yes is not refused for capture order.

The Violation this prevents is a Silent Fallback in reverse: a check that fires on a true yes. The agenda is shown in
the chat and the lead answers it; the model then captures both. Capture numbers say when the model wrote them down,
not when the lead spoke, so "yes came before the read-back" refused agendas the lead had agreed to (full3 F115),
costing two turns each time. A decision's yes keeps the order check; it answers a wording read back for it.
"""
from test_apply_add import filed, make_vault, plan

YES_FIRST = ['- [answer] (@priya) "Yes, that agenda." ^c01',
             '- [readback] (claude) The agenda: the stock level contract ^c02',
             '- [answer] (@priya) "ok" ^c03']


def test_an_agenda_yes_captured_before_its_readback_is_accepted(tmp_path):
    root = make_vault(tmp_path, captures=YES_FIRST)
    writes = filed(root, "agenda", [{"id": "CON-002", "readback": "^c02", "yes": "^c01", "status": "open"}])
    assert any("GATE-3 confirmed yes" in text for text in writes.values())


def test_an_agenda_still_needs_a_real_yes_and_a_readback_that_exists(tmp_path):
    root = make_vault(tmp_path, captures=YES_FIRST)
    _, refusals = plan(root, "agenda", [{"id": "CON-002", "readback": "^c02", "yes": "^c03", "status": "open"}])
    assert [r.rule for r in refusals] == ["consent-bare-non-yes"]
    _, refusals = plan(root, "agenda", [{"id": "CON-002", "readback": "^c09", "yes": "^c01", "status": "open"}])
    assert [r.rule for r in refusals] == ["consent-capture-missing"]
