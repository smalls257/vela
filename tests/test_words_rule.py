"""Whose words leave the machine: a receipt, a Why and a Dissent carry a person's words only with that person's own
yes. The lead's own words go on record; anyone else's are named and stay in the private notes unless that person gave
a `quote-yes` capture in this session. A relayed yes (the lead typing "Raj said it's fine") is the lead's capture, so
it never lets Raj's words out. The rule is pure over a record and the lead's handle, so it is tested without a machine."""
from conftest import run
from vela import closegate, decisions
from vela.decisions import consent, record
from test_decide import CAPTURES, RECORD_ID, STOCK, TODAY, filed, history_of, item, make_vault, opened, plan, rules, view

ANA_YES = '- [answer] (@cto-ana) "Yes, one booking API." ^c16'
ANA_QUOTE_YES = '- [quote-yes] (@cto-ana) "Yes, you can quote me." ^c17'
RELAYED = '- [quote-yes] (@priya) "Raj said by email it\'s fine" ^c17'
RAJ = '- [worry] (@raj) "This is too slow." ^c18'


def vault(tmp_path, *more):
    return make_vault(tmp_path, captures=CAPTURES + list(more))


def bullets_of(root, **more):
    return history_of(filed(root, [item(**more)])[STOCK], "CON-002")


def decision_line(root, **more):
    return next(b for b in bullets_of(root, **more) if b.startswith("- **Decision:**"))


def test_the_leads_yes_goes_on_record_in_their_words(tmp_path):
    assert decision_line(vault(tmp_path)) == '- **Decision:** [[%s]] c02, @priya: "Yes, as read."' % RECORD_ID


def test_someone_elses_yes_is_named_without_words(tmp_path):
    line = decision_line(vault(tmp_path, ANA_YES), yes="^c16")
    assert line == "- **Decision:** [[%s]] c16, @cto-ana" % RECORD_ID and "booking" not in line


def test_their_own_quote_yes_lets_their_words_out(tmp_path):
    line = decision_line(vault(tmp_path, ANA_YES, ANA_QUOTE_YES), yes="^c16")
    assert line == '- **Decision:** [[%s]] c16, @cto-ana: "Yes, one booking API."' % RECORD_ID


def test_a_relayed_yes_is_the_leads_capture_and_does_not_count(tmp_path):
    bullets = bullets_of(vault(tmp_path, RELAYED, RAJ), dissent="^c18")
    assert "- **Dissent:** @raj, 2026-10-20" in bullets and not any("too slow" in b for b in bullets)


def test_their_own_quote_yes_lets_a_dissent_speak(tmp_path):
    own = '- [quote-yes] (@raj) "Yes, quote me." ^c19'
    assert f'- **Dissent:** @raj, 2026-10-20: "This is too slow." (see [[{RECORD_ID}]])' in bullets_of(
        vault(tmp_path, RAJ, own), dissent="^c18")


def test_a_quoted_dissent_passes_the_receipt_check_after_decide(tmp_path):
    """The writer and E315 agree: words in a Dissent say where they came from, so vela check has nothing to flag."""
    root = vault(tmp_path, RAJ, '- [quote-yes] (@raj) "Yes, quote me." ^c19')
    for path, text in filed(root, [item(dissent="^c18")]).items():
        (root / path).write_text(text, encoding="utf-8")
    code, out = run("check", "--vault", str(root), "--today", TODAY)
    assert "too slow" in (root / STOCK).read_text(encoding="utf-8")
    assert "E315" not in out, out


def test_a_quote_yes_must_be_a_yes_from_a_person():
    for line in ('- [quote-yes] (@cto-ana) "ok" ^c16', '- [quote-yes] (claude) "Yes" ^c16',
                 '- [quote-yes] (@cto-ana) "Not sure" ^c16'):
        assert consent.quote_yes(parsed([line]), "@cto-ana") is None, line


def test_only_the_origins_own_quote_yes_counts_for_that_origin():
    rec = parsed(['- [quote-yes] (@cto-ana) "Yes, quote me." ^c16'])
    assert consent.quote_yes(rec, "@cto-ana").n == "16" and consent.quote_yes(rec, "cto-ana").n == "16"
    assert consent.quote_yes(rec, "@raj") is None


def test_the_why_is_the_leads_words_or_the_deciders_with_their_quote_yes(tmp_path):
    reason = '- [answer] (@cto-ana) "Because it is simpler." ^c16'
    _, refused = plan(vault(tmp_path / "a", reason), [item(why="^c16")])
    assert "consent-why-not-theirs" in rules(refused), "someone else's reason is not the lead's to publish"
    assert not plan(vault(tmp_path / "b", reason, ANA_QUOTE_YES), [item(why="^c16")])[1]
    assert not plan(vault(tmp_path / "c"), [item(why="^c03")])[1]


def test_an_unknown_lead_asks_for_the_handle_before_anything_is_written(tmp_path):
    root = vault(tmp_path)
    staged = view(root)
    staged.lead = None
    _, refusals = decisions.plan(decisions.Decision("decide", RECORD_ID, [item()], {}), staged, opened(root))
    found = [r for r in refusals if r.rule == "decide-lead-unknown"]
    assert found and found[0].plain.startswith("I don't know your GitHub handle yet, so I can't put your words on record")


def test_decide_without_a_known_handle_exits_3(tmp_path, monkeypatch):
    root = vault(tmp_path)
    monkeypatch.setattr("vela.edge.sessiongit.read_handle", lambda root: "")
    monkeypatch.setattr("vela.edge.sessiongit.gh", lambda *a, **k: type("Ran", (), {"how": "missing", "out": "", "first_line": lambda self: ""})())
    code, out = run("decide", "CON-002", "--vault", str(root), "--today", TODAY, "--readback", "^c01", "--yes", "^c02",
                    "--provider", "^c07", "--json")
    assert code == 3, out


def test_a_decision_with_no_yes_but_the_quoted_yes_override_gets_the_bare_link(tmp_path):
    one = {"id": "CON-002", "provider": "^c07", "by": "@priya", "reader": False,
           "overrides": [{"rules": [closegate.QUOTED_YES_RULE], "reason": "^c06"}]}
    assert "- **Decision:** [[%s]]" % RECORD_ID in history_of(filed(vault(tmp_path), [one])[STOCK], "CON-002")


def parsed(lines):
    text = "\n".join(["---", f"id: {RECORD_ID}", "type: session", "date: 2026-10-20", "status: open", "---", "",
                      "# x", "", "## Captures", "", *lines, ""])
    return record.from_text(RECORD_ID, "sessions/private/x.md", text)


def test_a_decided_adr_cites_the_yes_it_came_from(tmp_path):
    import test_apply_add as adds
    root = adds.make_vault(tmp_path)
    item = {"type": "adr", "title": "One booking app", "owner": "@priya", "state": "decided", "decision": RECORD_ID,
            "capture": "^c03"}
    writes = adds.filed(root, "add", [item])
    page = next(text for path, text in writes.items() if "ADR-" in path and path.endswith(".md"))
    assert '- **Decision:** [[%s]] c03, @priya: "Yes, as read."' % RECORD_ID in page
    _, refused = adds.plan(root, "add", [{k: v for k, v in item.items() if k != "capture"}])
    assert "add-adr-capture" in [r.rule for r in refused]


def adr(**more):
    return {"type": "adr", "title": "One booking app", "owner": "@priya", "state": "decided", "decision": RECORD_ID,
            "capture": "^c03", **more}


def adr_rules(root, item, lead=("priya", ())):
    import test_apply_add as adds
    staged = adds.staged_view(root)
    staged.lead = lead
    _, refused = decisions.plan(decisions.Decision("add", RECORD_ID, [item], {}), staged, adds.opened(root))
    return [r.rule for r in refused], refused


def test_an_adr_receipt_is_refused_for_another_session_a_non_yes_or_an_unknown_lead(tmp_path):
    import test_apply_add as adds
    root = adds.make_vault(tmp_path, captures=adds.CAPTURES + ['- [answer] (claude) "Yes" ^c04',
                                                              '- [answer] (@priya) "ok" ^c05'])
    assert "add-adr-session" in adr_rules(root, adr(decision="2026-01-01-other"))[0]
    assert "consent-not-a-person" in adr_rules(root, adr(capture="^c04"))[0]
    assert "consent-bare-non-yes" in adr_rules(root, adr(capture="^c05"))[0]
    assert "decide-lead-unknown" in adr_rules(root, adr(), lead=None)[0]
    assert adr_rules(root, adr())[0] == []


def test_a_yes_that_takes_the_quote_back_does_not_count():
    for words in ("Yes, but don't quote me", "Yes, do not publish this", "Yes, never in writing", "Yes, but not word for word"):
        rec = parsed([f'- [quote-yes] (@cto-ana) "{words}" ^c16'])
        assert consent.quote_yes(rec, "@cto-ana") is None, words
    assert consent.quote_yes(parsed(['- [quote-yes] (@cto-ana) "Yes, quote me on that." ^c16']), "@cto-ana")


def test_the_leads_display_name_never_becomes_their_handle_on_record(tmp_path):
    named = '- [answer] (Priya Shah) "Yes, one till API." ^c16'
    root = vault(tmp_path, named)
    staged = view(root)
    staged.lead = ("priya", ("priya shah",))
    writes, refused = decisions.plan(decisions.Decision("decide", RECORD_ID, [item(yes="^c16")], {}), staged, opened(root))
    assert not refused, refused
    page = {w.path: w.text for w in writes}[STOCK]
    assert '[[%s]] c16, @priya: "Yes, one till API."' % RECORD_ID in page and "@Priya" not in page
