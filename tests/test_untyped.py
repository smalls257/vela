"""W809, possibly an untyped subject.

A catalog question only fires on a subject someone typed. If Discover writes "loyalty points"
into a contract and never types the scheme as stored value, Q-FIN-03 is never owed and the ledger
looks clean. The warning is the safety net: it stays until the subject is typed and linked, or the
existence question that would create it is answered."""
import shutil

import pytest

from conftest import REPO, edit, findings, run

FIXTURE = REPO / "examples" / "unified-booking"
LEDGER = "11-unknowns-and-risks.md"
COST = "08-concerns/concern-cost.md"
TODAY = "2026-11-20"
REG_02 = ("| Q-REG-02@INI-002 | unknown | unknown: [[#UNK-008 Review of the customer data Booking holds\\|UNK-008]] "
          "| @hl-solution-lead | 2026-11-19 |\n")
REG_02_NA = "| Q-REG-02@INI-002 | not-applicable | reason: no new product, activity or license, and card data stays with Tidepay | @hl-solution-lead | 2026-11-19 |\n"
FIN_01 = ("| Q-FIN-01@INI-002 | answered | item: [[03-context-and-scope#SV-01 Loyalty points\\|SV-01]]; source: \"the loyalty scheme, "
          "which reads FERRYMASTER directly and stays out of scope until INI-004\" in [[03-context-and-scope]]; answer: Yes, the loyalty "
          "scheme holds customers' points, and it reads FERRYMASTER directly until INI-004 | @hl-solution-lead | 2026-11-19 |\n")
BOOKING = "05-building-blocks/booking-building-blocks.md"
CROSSES = "- **Crosses the boundary:** "


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    return dest


def checked(vault):
    run("render", "--vault", str(vault))
    return run("check", "--vault", str(vault), "--today", TODAY)


def test_a_license_in_a_table_row_warns_while_its_existence_question_is_unanswered(ub):
    edit(ub / LEDGER, REG_02, "")
    code, out = checked(ub)
    assert code == 0, "a warning, never an error"
    assert findings(out) == [("W809", COST)]
    assert "'licenses' may be an untyped subject: this page holds or links no party, and Q-REG-02@INI-002 has no answer yet" in out
    assert "Type it as ### PTY-nn on 03-context-and-scope.md" in out


def test_the_british_spelling_of_licence_still_warns(ub):
    """Vaults written before the American-spelling pass say "licences"; the matcher reads both, so the net stays up (Silent Fallback)."""
    edit(ub / LEDGER, REG_02, "")
    cost = ub / COST
    cost.write_text(cost.read_text(encoding="utf-8").replace("licenses", "licences"), encoding="utf-8")
    assert "licences" in cost.read_text(encoding="utf-8")
    assert findings(checked(ub)[1]) == [("W809", COST)]


def test_an_open_existence_row_still_warns(ub):
    edit(ub / LEDGER, REG_02, "| Q-REG-02@INI-002 | open |  |  |  |\n")
    assert findings(checked(ub)[1]) == [("W809", COST)]


def test_points_in_a_contract_bullet_warn_and_typing_the_subject_clears_it(ub):
    edit(ub / LEDGER, FIN_01, "")
    text = (ub / BOOKING).read_text(encoding="utf-8")
    first = text.index(CROSSES)
    (ub / BOOKING).write_text(text[:first] + CROSSES + "loyalty points earned on the booking, " + text[first + len(CROSSES):],
                              encoding="utf-8")
    out = checked(ub)[1]
    assert findings(out) == [("W809", BOOKING)]
    assert "'points' may be an untyped subject: this page holds or links no stored value" in out
    text = (ub / BOOKING).read_text(encoding="utf-8")
    edit(ub / BOOKING, "loyalty points earned on the booking, ",
         "loyalty points ([[03-context-and-scope#SV-01 Loyalty points|SV-01]]) earned on the booking, ")
    assert findings(checked(ub)[1]) == []


def test_answering_the_existence_question_clears_it(ub):
    edit(ub / LEDGER, REG_02, "")
    assert findings(checked(ub)[1]) == [("W809", COST)]
    edit(ub / LEDGER, "| Q-REG-01@INI-002 |", REG_02_NA + "| Q-REG-01@INI-002 |")
    assert findings(checked(ub)[1]) == []


def test_an_invalid_row_answers_nothing_so_the_warning_stays(ub):
    edit(ub / LEDGER, REG_02, "| Q-REG-02@INI-002 | not-applicable |  | @hl-solution-lead | 2026-11-19 |\n")
    code, out = checked(ub)
    assert code == 1 and "E802" in out
    assert ("W809", COST) in findings(out)


def test_prose_sessions_code_and_the_ledger_are_not_read(ub):
    edit(ub / LEDGER, FIN_01, "")
    edit(ub / LEDGER, REG_02, "")
    edit(ub / COST, "no work (@hl-solution-lead, review 2027-03-01): standard service footprint, no new licenses",
         "no work (@hl-solution-lead, review 2027-03-01): standard service footprint, no new `licenses`")
    (ub / "sessions" / "2026-11-19-owed-questions.md").write_text(
        (ub / "sessions" / "2026-11-19-owed-questions.md").read_text(encoding="utf-8")
        + "| SV-99 | points | balances | vouchers |\n", encoding="utf-8")
    out = checked(ub)[1]
    assert [f for f in findings(out) if f[0] == "W809"] == [], out


def test_it_warns_once_per_page_and_question(ub):
    edit(ub / LEDGER, REG_02, "")
    edit(ub / COST, "## Per app", "- **Notes:** a license review, licenses renewed, license fees\n\n## Per app")
    assert findings(checked(ub)[1]) == [("W809", COST)]


def test_the_template_and_the_fixture_are_quiet():
    for vault, today in ((FIXTURE, TODAY), (REPO / "template", "2026-10-03")):
        code, out = run("check", "--vault", str(vault), "--today", today)
        assert code == 0 and "W809" not in out


def _unanswered(ub):
    """Drop the three existence rows, so any mention on a page is owed a type."""
    path = ub / LEDGER
    keep = [l for l in path.read_text(encoding="utf-8").split("\n")
            if not l.startswith(("| Q-FIN-01@INI-002 |", "| Q-PTN-01@INI-002 |", "| Q-REG-02@INI-002 |"))]
    path.write_text("\n".join(keep), encoding="utf-8")


def _w809(ub, fact):
    """The W809 lines reported on the one bullet this test adds. The page's own table row says
    "no new licenses", so it warns too once Q-REG-02 has no answer; only the added line counts."""
    _unanswered(ub)
    edit(ub / COST, "## Per app", f"- **Notes:** {fact}\n\n## Per app")
    line = next(n for n, l in enumerate((ub / COST).read_text(encoding="utf-8").split("\n"), 1) if l == f"- **Notes:** {fact}")
    out = checked(ub)[1]
    return [l for l in out.splitlines() if f"concern-cost.md:{line}: W809" in l]


@pytest.mark.parametrize("fact", [
    "a point per crossing", "ten points", "the balance", "customer balances", "a credit", "credits", "credited back",
    "a voucher", "vouchers", "a deposit", "deposits", "deposited at booking", "the clause", "clauses", "a license",
    "licenses", "a license", "licensed", "licensing", "a licensed route",
])
def test_every_inflection_the_catalog_lists_is_caught(ub, fact):
    assert len(_w809(ub, fact)) >= 1, fact


@pytest.mark.parametrize("fact", [
    "pay by credit card", "pay by credit cards", "balance the load across nodes", "load balancing across nodes",
    "a load balancer", "story points per sprint", "five story point estimates", "a touch point with the crew",
    "touch points", "data point", "data points", "a pointer to the page", "a licensee", "creditor",
])
def test_known_false_hits_stay_quiet(ub, fact):
    assert _w809(ub, fact) == [], fact


def test_the_first_word_written_is_the_one_named_not_the_first_alphabetically(ub):
    _unanswered(ub)
    edit(ub / COST, "## Per app", "- **Notes:** vouchers, then balances and a credit\n\n## Per app")
    out = checked(ub)[1]
    assert "'vouchers' may be an untyped subject" in out and "'balances' may be" not in out


def test_a_wikilink_target_or_alias_is_not_scanned(ub):
    assert _w809(ub, "see [[booking-building-blocks|loyalty points]] and [[03-context-and-scope#SV-01 Loyalty points]]") == []


def test_a_word_outside_the_link_still_counts_beside_one_inside(ub):
    lines = _w809(ub, "[[booking-building-blocks|points]] and a voucher")
    assert lines


def test_the_catalog_gives_every_mention_a_reason():
    import yaml
    from planner import catalog
    cat = catalog.parse_catalog(yaml.safe_load((REPO / "plugin" / "catalog" / "questions.yaml").read_text(encoding="utf-8")))
    for entry in cat.entries:
        if entry.mentions:
            assert {f for f, _ in entry.mention_why} == set(entry.mentions), entry.id
    assert "credit card*" in cat.entry("Q-FIN-01").mention_except
