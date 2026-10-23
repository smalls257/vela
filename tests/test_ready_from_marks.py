"""E81: a lead's yes in a session that can't decide reaches the next grill without the model remembering to.

The Violation this guards is a Silent Fallback of consent. `vela decide` was the only thing that listed an item under
`## Ready to decide`, and in two paid runs the model said yes ~20 times in shape and requirements and never ran it, so
the next grill opened without any of them. The mark `vela apply` writes already names the item and its state, so the
list is filled there, in code. Each test is one rule: a lead's yes on an item kept at `assumption`, in a session that
can't decide, is listed; nothing else is.
"""
import json
import re

import pytest

from conftest import run
from test_apply_cli import apply, decision_file
from test_decide import RECORD, RECORD_ID, STOCK, TODAY, in_session_with_modes, make_vault
import session_files

YES = '- [thought] (@priya) "Yes, keep the existing read API." ^c01'


def lead_vault(tmp_path, captures, modes="shape"):
    root = make_vault(tmp_path, captures=captures)
    in_session_with_modes(root, modes)
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "handle").write_text("priya\n", encoding="utf-8")
    return root


def keep(root, state="assumption", ident="CON-002", capture="^c01"):
    path = decision_file(root, [{"capture": capture, "mark": "keep", "to": "assumption", "id": ident, "state": state}],
                         kind="marks")
    code, out = apply(root, path, "--json")
    assert code == 0, out


def record_text(root):
    return session_files.record_text(root, RECORD_ID)


def waiting(root):
    code, out = run("session", "brief", "--vault", str(root), "--today", TODAY, "--json")
    return [(e["id"], e["session"]) for e in json.loads(out)["ready_to_decide"]]


@pytest.mark.parametrize("mode", ["shape", "requirements", "boundary", "shape, boundary"])
def test_a_lead_yes_kept_at_assumption_is_listed_with_no_decide_call(tmp_path, mode):
    root = lead_vault(tmp_path, [YES], mode)
    keep(root)
    assert f"## Ready to decide\n\n- CON-002: the lead said yes in {RECORD_ID} (^c01)" in record_text(root)
    assert waiting(root) == [("CON-002", RECORD_ID)]


def test_marking_twice_lists_it_once(tmp_path):
    root = lead_vault(tmp_path, [YES, '- [thought] (@priya) "Yes, and the same for that." ^c02'])
    keep(root)
    keep(root, capture="^c02")
    assert record_text(root).count("- CON-002: the lead said yes") == 1


@pytest.mark.parametrize("captures", [
    ['- [thought] (@stock-team) "Yes, keep the existing read API." ^c01'],  # someone else's yes is not the lead's
    ['- [thought] (@priya) "Not sure yet." ^c01'],
    ['- [thought] (@priya) "No, a push feed." ^c01'],
    ['- [thought] (@priya) "ok" ^c01'],
    ['- [thought] (claude, from @priya) Yes, keep the existing read API ^c01'],
    ['- [thought] (claude) Yes, keep the existing read API ^c01'],
], ids=["not-the-lead", "not-sure", "no", "bare-ok", "claudes-summary", "claudes-own"])
def test_only_the_leads_own_yes_is_listed(tmp_path, captures):
    root = lead_vault(tmp_path, captures)
    keep(root)
    assert "Ready to decide" not in record_text(root)
    assert waiting(root) == []


def test_a_yes_kept_below_assumption_is_not_listed(tmp_path):
    root = lead_vault(tmp_path, [YES])
    keep(root, state="inkling", ident="CAP-001", capture="^c01")
    assert "Ready to decide" not in record_text(root)


def test_a_grill_session_lists_nothing(tmp_path):
    root = lead_vault(tmp_path, [YES], "grill")
    keep(root)
    assert "Ready to decide" not in record_text(root)


def test_an_item_decided_since_is_not_listed(tmp_path):
    root = lead_vault(tmp_path, [YES])
    keep(root)
    assert waiting(root) == [("CON-002", RECORD_ID)]
    page = (root / STOCK).read_text(encoding="utf-8")
    (root / STOCK).write_text(re.sub(r"(### CON-002[\s\S]*?- \*\*State:\*\* )assumption", r"\1decided", page, count=1),
                              encoding="utf-8")
    assert waiting(root) == []
