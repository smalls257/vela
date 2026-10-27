"""Below medium GATE-2 asks one question; vela decide --options-none records the lead's answer and decides."""
from conftest import edit
from sizing_vault import choose
from test_decide import CAPTURES, RECORD_ID, STOCK, STRATEGY, filed, history_of, item, make_vault
from vela import cli, gates

ONLY = '- [answer] (@priya) "No, everyone calls us over HTTP already." ^c20'
OPTIONS = "- **Options considered:** the existing read API (picked); a new push feed: rejected, Stock is unchanged\n"
STRATEGY_OPTIONS = "- **Options considered:** one Shop API (picked); the till calls Stock itself: rejected, two places to change\n"


def without_options(root):
    """The solution strategy with nobody having laid options out for it: the case GATE-2 is about."""
    edit(root / STRATEGY, STRATEGY_OPTIONS, "")
    return root


def gate_two(root):
    found = gates.verdict(cli.load_vault(root), None, "solution-strategy", "2026-10-20")
    return next(r for r in found.reasons if r.rule == "GATE-2")


def test_small_gate_two_asks_one_question(tmp_path):
    two = gate_two(without_options(make_vault(tmp_path)))  # the mini vault: two apps, small
    assert two.ask.startswith("Was anything other than") and "--options-none" in two.next


def test_large_gate_two_still_points_to_shape(tmp_path):
    root = without_options(make_vault(tmp_path))
    with (root / ".vela.yaml").open("a", encoding="utf-8") as fh:
        fh.write(choose("large"))
    two = gate_two(root)
    assert two.ask == "" and two.next.startswith("/vela:shape")


def test_options_none_writes_the_leads_words_only_when_quotable(tmp_path):
    root = without_options(make_vault(tmp_path, captures=CAPTURES + [ONLY]))
    # the lead's own words are covered by their read-back at close (CONVENTIONS, "Whose words go on a page")
    writes = filed(root, [item("solution-strategy", options_none="^c20")])
    bullets = history_of(writes[STRATEGY])
    assert f"- **Options considered:** only this one: No, everyone calls us over HTTP already. ([[{RECORD_ID}]] c20)" in bullets
    # someone else's words are quoted only with their own yes
    other = without_options(make_vault(tmp_path / "other", captures=CAPTURES + [ONLY.replace("@priya", "@stock-team")]))
    bullets = history_of(filed(other, [item("solution-strategy", options_none="^c20")])[STRATEGY])
    assert f"- **Options considered:** only this one ([[{RECORD_ID}]] c20)" in bullets
