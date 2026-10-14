"""The output layer every new command relays through (overhaul Task 2): `--for-lead` resolves IDs to names and raises
on a leak, so a line meant for the lead can't carry a code or an ID (Leaky Narrative, fixed at the interface)."""
import argparse
import io
import re

import pytest

from conftest import REPO, run
from vela import cli, commands, model, say

HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"


def test_for_lead_never_prints_a_code_or_id():
    code, out = run("check", "--vault", str(HERON), "--today", "2026-10-14", "--for-lead")
    assert code in (0, 1), out
    assert "vela bug" not in out
    for kind, pattern in say.LEAD_PATTERNS.items():
        assert not pattern.search(out), (kind, pattern.search(out).group(0))
    assert not re.search(r"\b[EWT]\d{3}\b|\bUNK-\d|\bCON-\d|\bFLO-\d|Fix:", out)
    assert "Calendar entries doesn't list what it returns when a call fails" in out  # the name, not "(CON-001)"


def test_for_lead_formatter_raises_on_a_leak(monkeypatch):
    """A leak is a vela bug: exit 2, naming the command, never a quiet code in front of the lead."""
    monkeypatch.setattr(cli, "check_lead_header", lambda *a: "E316 is open on UNK-001")
    code, out = run("check", "--vault", str(HERON), "--today", "2026-10-14", "--for-lead")
    assert code == 2
    assert "vela bug: a line meant for the lead held an ID" in out and "`vela check --for-lead`" in out


def test_emit_raises_on_an_explicit_plain_line_that_leaks():
    result = say.Result("demo", lines=[say.Line("UNK-001 open", plain="UNK-001 is still open")])
    with pytest.raises(say.LeadLeak) as caught:
        commands.emit(result, argparse.Namespace(for_lead=True, json=False), io.StringIO())
    assert caught.value.command == "demo" and caught.value.kind == "item"


def test_finding_id_prints_area_and_question():
    from vela.catalog import Catalog
    vault = model.Vault(config={}, pages=[], catalog=Catalog(1, (("DAT", "Data and lawful basis"),), ()))
    resolver = say.Resolver(vault, findings={"F1.4": ("DAT", "how long consent records are kept")})
    assert resolver.plain("F1.4 is still open") == "the data reviewer asked how long consent records are kept is still open"
    assert "F2.1" not in resolver.plain("F2.1 waits") and "reviewer" in resolver.plain("F2.1 waits")


def test_ids_with_no_name_are_said_by_their_kind_and_captures_by_what_they_are():
    resolver = say.Resolver()
    said = resolver.plain("UNK-009 blocks CON-004, from ^c12; copy Q-FIN-03@SV-01; row R-DAT-10; GATE-4 overridden")
    assert say.leak_in(said) is None, said
    assert "an open question" in said and "a contract" in said and "a note in the session record" in said
    assert "the open-question check" in said


def test_refusal_carries_plain_fix_and_override_and_for_lead_prints_only_plain():
    refusal = say.Refusal("GATE-4", "Nobody has said who owns the consent records yet.", "Ask the lead.",
                          "vela apply ... (rule GATE-4)")
    result = say.Result("demo", exit=say.REFUSED, refusals=[refusal])
    assert refusal.as_json() == {"refused": True, "rule": "GATE-4", "plain": refusal.plain, "fix": "Ask the lead.",
                                 "override": "vela apply ... (rule GATE-4)"}
    assert say.render(result, "for-lead") == "Nobody has said who owns the consent records yet."
    assert "Override: vela apply" in say.render(result, "default")


def test_exit_3_means_nothing_changed():
    """Exit 3 promises the lead that nothing changed and that the choices are listed; `render` holds both promises."""
    asked = say.Result("demo", exit=say.NEEDS_LEAD, needs_lead=[{"choose": "which session"}])
    assert '"needs_lead"' in say.render(asked, "json")
    with pytest.raises(ValueError, match="nothing changed"):
        say.render(say.Result("demo", exit=say.NEEDS_LEAD, needs_lead=[{"x": 1}], wrote=["sessions/a.md"]), "json")
    with pytest.raises(ValueError, match="without saying what the lead must choose"):
        say.render(say.Result("demo", exit=say.NEEDS_LEAD), "default")


def test_main_says_what_each_exit_code_means():
    doc = cli.main.__doc__
    for line in ("0  done.", "1  refused", "2  the tool failed", "3  needs the lead: nothing changed"):
        assert line in doc
