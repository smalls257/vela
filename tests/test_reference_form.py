"""Committed pages cite a capture as `[[<session>]] c07` (`2.c07` from the second part), never as an anchor into the
notes (private-sessions Task 7).

The Violation these tests guard is an Infected Core of the plan's links: a `[[<id>#^c07]]` on a committed page points
into notes that stay on the lead's machine, so on every clone it was a dead link and a check error. The writers, the
readers and the fixtures move together; a writer left on the old form fails the first tests, a reader left on the old
form fails the next ones."""
import json
import shutil

import pytest

from conftest import MINI, REPO, edit, findings, run
from test_apply_add import RECORD_ID, filed, make_vault
from test_session_cli import TODAY as SESSION_DAY, owner, start
from vela import cli, questions, rules, say
import session_files

EXAMPLE = REPO / "examples" / "unified-booking"
HERON = REPO / "tests" / "fixtures" / "team-skills" / "heron"
LEDGER = "11-unknowns-and-risks.md"
CAPABILITY = ("---\nid: CAP-001\ntype: capability\ntitle: Sell\nstate: assumption\nowner: \"@priya\"\n"
              "authored: authored\norigin: proposed\nchange: new\n---\n\n# CAP-001 Sell\n\n"
              "## Functional requirements\n\n")
CONSTRAINTS = ("---\nid: constraints\ntype: initiative-section\ntitle: Constraints\nstate: inkling\n"
               "owner: \"@priya\"\nauthored: authored\n---\n\n# Constraints\n\n"
               "| ID | Constraint | Where it comes from | What it forces |\n|---|---|---|---|\n")


def test_an_fr_from_part_two_cites_the_part(tmp_path):
    root = make_vault(tmp_path)
    session_files.edit_record(root, RECORD_ID, "part: 1", "part: 2")
    (root / "capabilities").mkdir()
    (root / "capabilities" / "CAP-001-sell.md").write_text(CAPABILITY, encoding="utf-8")
    writes = filed(root, "add", [{"type": "fr", "capability": "CAP-001", "name": "Print a receipt",
                                  "need": "A shopper leaves with a receipt.", "capture": "^c03"}])
    page = writes["capabilities/CAP-001-sell.md"]
    assert f"- **Source:** [[{RECORD_ID}]] 2.c03" in page and "#^" not in page
    assert f"[[{RECORD_ID}#^c03]]" in writes[f"sessions/private/{RECORD_ID}.md"], "the notes keep their anchors"


def test_a_constraint_cites_the_capture_without_an_alias(tmp_path):
    root = make_vault(tmp_path)
    (root / "02-constraints.md").write_text(CONSTRAINTS, encoding="utf-8")
    writes = filed(root, "add", [{"type": "constraint", "capture": "^c02", "forces": "the till work lands first"}])
    assert f"| [[{RECORD_ID}]] c02 |" in writes["02-constraints.md"]
    assert "#^" not in writes["02-constraints.md"] and "the lead's account" not in writes["02-constraints.md"]


@pytest.fixture
def example(tmp_path):
    dest = tmp_path / "example"
    shutil.copytree(EXAMPLE, dest)
    return dest


def broken(vault):
    return [f for f in findings(run("check", "--vault", str(vault), "--today", "2026-11-20")[1])]


def test_asked_row_needs_the_reference_form(example):
    old = "capture: [[2026-11-19-owed-questions]] c01"
    edit(example / LEDGER, old, "capture: [[2026-11-19-owed-questions#^c01]]")
    assert ("E802", LEDGER) in broken(example)
    edit(example / LEDGER, "capture: [[2026-11-19-owed-questions#^c01]]", old)
    assert ("E802", LEDGER) not in broken(example)
    edit(example / LEDGER, old, "capture: [[no-such-session]] c01")
    assert ("E802", LEDGER) in broken(example), "the reference must name a session page in the plan"


def test_a_quote_from_a_session_says_why():
    vault = cli.load_vault(MINI)
    problem = questions.quote_problem(vault, '"we sell from one till" in [[2026-01-10-shop-api]]', "source")
    assert "stay on the lead's machine" in problem and problem.startswith("source quotes a session record")


def test_a_reference_in_a_lead_line_is_caught():
    assert say.leak_in("I filed it from 2.c07.") is not None
    assert say.leak_in("from [[x]] c07") is not None
    assert say.leak_in("I filed it from ^c07.") is not None
    assert say.leak_in("We shipped in 2.5 weeks, the c07 build.") is None


def test_a_voiced_page_needs_a_session_in_the_reference_form(example):
    page = example / "03-context-and-scope.md"

    def verdict(yes):
        text = page.read_text(encoding="utf-8").replace(
            "\n---\n", f"\nsource-wording: voice\nsource-wording-yes: \"{yes}\"\n---\n", 1)
        page.write_text(text, encoding="utf-8")
        found = [f for f in broken(example) if f[0] == "E361"]
        page.write_text(text.replace(f"source-wording: voice\nsource-wording-yes: \"{yes}\"\n", ""), encoding="utf-8")
        return found

    assert verdict("[[2026-11-19-owed-questions]] c01") == []
    assert verdict("[[2026-11-19-owed-questions]] 2.c01") == []
    assert verdict("[[2026-11-19-owed-questions#^c01]]") != []
    assert verdict("[[concern-data]] c01") != [], "a page that is not a session is not a record"


def test_converted_fixtures_check_clean():
    for vault, today in ((EXAMPLE, "2026-11-20"), (MINI, "2026-01-15"), (HERON, "2026-10-20")):
        errors = [f for f in rules.check(cli.load_vault(vault), cli.parse_today(today)[0]) if f.is_error]
        assert not errors, (vault.name, [(f.code, f.path, f.message) for f in errors][:5])


def test_a_findings_quote_from_a_session_is_refused_with_the_reason(tmp_path):
    folder = tmp_path / "f"
    folder.mkdir()
    bad = {"finding": "Nobody said who owns the till.", "quote": "we sell everything from one till",
           "page": "2026-11-19-owed-questions", "copy": "new", "severity": "high",
           "question": "Who owns the till?"}
    for code in ("FIN", "DAT", "PTN", "REG", "OPS"):
        (folder / f"{code}.json").write_text(json.dumps({"area": code, "findings": [bad] if code == "FIN" else []}),
                                             encoding="utf-8")
    code, out = run("findings", "merge", str(folder), "--vault", str(EXAMPLE), "--json")
    result = json.loads(out)
    assert result["kept"] == [] and "stay on the lead's machine" in result["dropped"][0]["reason"], result


def test_a_real_session_writes_links_check_accepts(tmp_path, monkeypatch):
    """No test helpers: the session is started by `vela session start`, the captures are added by `vela record add`,
    and decide, add slice and add constraint write their links. The stub holds no anchors, so an anchor link or a
    quote of a session would be E202 or E361 on every clone."""
    vault = owner(tmp_path, monkeypatch)
    stock = vault / "05-building-blocks" / "stock-building-blocks.md"
    edit(stock, "- **State:** fact\n", "- **State:** assumption\n- **Options considered:** the existing read API "
                                       "(picked); a new push feed: rejected, Stock is unchanged\n")
    edit(stock, "- **Change:** unchanged\n", "- **Change:** unchanged\n- **Tested by:** consumer tests in the shop pipeline.\n")
    edit(stock, "| count | | ok | the count left | | |\n",
         "| count | | ok | the count left | | |\n| unknown_product | | error | refused: no such product | | |\n")
    (vault / "02-constraints.md").write_text(CONSTRAINTS, encoding="utf-8")
    (vault / "flows").mkdir()
    (vault / "flows" / "FLO-001-buy.md").write_text(
        "---\nid: FLO-001\ntype: flow\ntitle: Buy\nstate: assumption\nowner: \"@priya\"\nauthored: authored\n---\n\n"
        "# FLO-001 Buy\n", encoding="utf-8")
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "handle").write_text("priya\n", encoding="utf-8")
    assert start(vault, "--mode", "grill", "--topic", "stock")[0] == 0
    record_id = f"{SESSION_DAY}-stock"
    for origin, tag, words in (("claude", "thought", "Read back: the stock level, the count left for a product ID"),
                               ("@priya", "answer", "Yes, as read."),
                               ("claude, from Stock team", "thought", "Stock team present and agreed"),
                               ("@priya", "thought", "Selling from the till is the first slice."),
                               ("@priya", "thought", "The till work lands before November.")):
        code, out = run("record", "add", "--vault", str(vault), "--origin", origin, "--tag", tag, words)
        assert code == 0, out
    notes = session_files.record_text(vault, record_id)
    assert "^c05" in notes
    steps = [("decide", "CON-002", "--readback", "^c01", "--yes", "^c02", "--provider", "^c03"),
             ("add", "slice", "--title", "The till sells", "--flows", "FLO-001", "--capture", "^c04"),
             ("add", "constraint", "--capture", "^c05", "--forces", "the till work lands first")]
    for argv in steps:
        code, out = run(*argv, "--vault", str(vault), "--today", SESSION_DAY)
        assert code == 0, (argv, out)
    committed = "".join(
        p.read_text(encoding="utf-8") for p in vault.rglob("*.md")
        if not {"private", ".vela", ".claude"} & set(p.relative_to(vault).parts))
    assert f"[[{record_id}]] c04" in committed and f"[[{record_id}]] c05" in committed
    assert "#^c" not in committed
    code, out = run("check", "--vault", str(vault), "--today", SESSION_DAY)
    codes = {f[0] for f in findings(out)}
    assert not codes & {"E202", "E361"}, out
