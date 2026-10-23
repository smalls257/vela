"""`vela close drafts` (overhaul Task 21a): the paragraphs a session owes, found from what changed since the branch
point (or, in a reader copy, since its baseline), `query refs` for each item resolved or decided, and the record."""
import json
import shutil

from conftest import run
from vela import say
from vela.edge import vaultgit
from sharing import git, make_vault
import session_files

RECORD = "2026-10-20-grill-stock"
STOCK = "05-building-blocks/stock-building-blocks.md"
TILL = "05-building-blocks/till-building-blocks.md"
UNKNOWNS = "11-unknowns-and-risks.md"
TESTING = "08-concerns/concern-testing.md"


def record_text(modes="grill"):
    lines = ["---", f"id: {RECORD}", "type: session", "date: 2026-10-20", f"modes: [{modes}]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", "", "## Captures", "",
             "## Changes", "", "| ID | From | To | Source |", "|---|---|---|---|"]
    return "\n".join(lines) + "\n"


def session(tmp_path, modes="grill"):
    vault = make_vault(tmp_path)
    git(vault, "switch", "-q", "-c", f"session/{RECORD}")
    session_files.write_record(vault, RECORD, record_text(modes))
    git(vault, "add", "sessions")
    git(vault, "commit", "-q", "-m", f"Open session {RECORD}")
    return vault


def edit(vault, path, old, new):
    page = vault / path
    text = page.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path}"
    page.write_text(text.replace(old, new, 1), encoding="utf-8")


def decide_stock(vault):
    edit(vault, STOCK, "- **State:** fact", "- **State:** decided")


def resolve_till_rig(vault):
    edit(vault, UNKNOWNS, "- **State:** open\n- **Ask by:** 2026-02-01",
         "- **State:** resolved\n- **Outcome:** Yes, the old till.\n- **Resolved in:** [[2026-10-20-grill-stock]]")


def drafts(vault, *flags):
    code, out = run("close", "drafts", "--vault", str(vault), *flags)
    return code, out


def drafts_json(vault):
    code, out = drafts(vault, "--json")
    assert code == 0, out
    return json.loads(out)


def owed_at(data, page):
    return [p for p in data["paragraphs"] if p["page"] == page]


def test_drafts_lists_refs_of_decided_items(tmp_path):
    vault = session(tmp_path)
    resolve_till_rig(vault)
    data = drafts_json(vault)
    testing = owed_at(data, TESTING)
    assert any(p["kind"] == "ref" and p["heading"] == "Per app" and "UNK-001" in p["items"] for p in testing), testing
    # the record of the session itself and the item's own page section are not paragraphs that owe a rewrite
    assert not owed_at(data, f"sessions/{RECORD}.md")


def test_ref_inside_a_generated_block_or_history_owes_nothing(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault)
    data = drafts_json(vault)
    # the shop page names the stock level only in its rendered contracts table, which render rewrites
    assert not [p for p in owed_at(data, "05-building-blocks/shop-building-blocks.md") if p["kind"] == "ref"]


def test_changed_page_owes_its_paragraph(tmp_path):
    vault = session(tmp_path)
    edit(vault, TILL, "\n## ", "\nThe till now reads one more thing.\n\n## ")
    data = drafts_json(vault)
    till = owed_at(data, TILL)
    assert any(p["kind"] == "opening" for p in till), till
    assert all(not p["page"].startswith("sessions/") and p["page"] != "sources.md" for p in data["paragraphs"])


def test_changed_item_owes_its_opening_sentence(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault)
    stock = owed_at(drafts_json(vault), STOCK)
    assert any(p["kind"] == "item" and p["heading"] == "CON-002 Stock level" for p in stock), stock


def test_decided_this_session_listed_for_readback(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault)
    data = drafts_json(vault)
    assert [(r["item"], r["name"], r["before"], r["page"]) for r in data["readback"]] == \
        [("CON-002", "Stock level", "fact", STOCK)]
    code, out = drafts(vault, "--for-lead")
    assert code == 0 and "Stock level" in out, out


def test_lists_over_seven_are_named(tmp_path):
    vault = session(tmp_path)
    more = "".join(f"\n### UNK-{n:03d} Question {n}\n\n- **Question:** Is {n} enough?\n- **Owner:** @mini-qa\n"
                   f"- **Opened:** 2026-10-20\n- **State:** open\n- **Ask by:** 2026-11-01\n"
                   for n in range(3, 10))
    edit(vault, UNKNOWNS, "\n## Risks", more + "\n## Risks")
    data = drafts_json(vault)
    assert {"page": UNKNOWNS, "heading": "Unknowns", "count": 9} in data["long_lists"], data["long_lists"]
    _, out = drafts(vault)
    assert "Also open (n)" in out


def test_over_twenty_paragraphs_prints_split_facts(tmp_path):
    vault = session(tmp_path)
    more = "".join(f"\n### R-{n:02d} Risk {n}\n\nRisk {n} is real.\n\n- **Owner:** @mini/till-team\n"
                   f"- **State:** open\n- **Mitigation:** watch it.\n" for n in range(2, 24))
    edit(vault, UNKNOWNS, "- **Mitigation:** keep the old till for a month.\n",
         "- **Mitigation:** keep the old till for a month.\n" + more)
    data = drafts_json(vault)
    assert data["count"] > 20
    assert data["split"]["paragraphs"] == data["count"]
    assert data["split"]["groups"]
    _, out = drafts(vault)
    assert f'{data["count"]} paragraphs changed, which is a lot to review at once.' in out and 'OK, or one review?' in out


def test_under_twenty_paragraphs_asks_nothing(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault)
    data = drafts_json(vault)
    assert data["split"] is None
    assert "a lot to review at once" not in drafts(vault)[1]


def test_reader_copy_runs_no_git(tmp_path, monkeypatch):
    vault = session(tmp_path)
    shutil.rmtree(vault / ".git")
    baseline = tmp_path / "baseline"
    shutil.copytree(vault, baseline)
    shutil.copytree(baseline, vault / ".vela" / "baseline")
    (vault / ".vela" / "workspace.json").write_text('{"role": "reader", "author": "Sam"}', encoding="utf-8")
    decide_stock(vault)

    def no_git(*args, **kwargs):
        raise AssertionError(f"a reader copy ran git: {args}")
    monkeypatch.setattr(vaultgit, "run_git", no_git)
    data = drafts_json(vault)
    assert any(p["kind"] == "item" for p in owed_at(data, STOCK)), data
    assert [r["item"] for r in data["readback"]] == ["CON-002"]
    assert data["reader_copy"] is True


def test_reader_copy_with_no_baseline_is_a_tool_failure(tmp_path):
    vault = session(tmp_path)
    shutil.rmtree(vault / ".git")
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "workspace.json").write_text('{"role": "reader"}', encoding="utf-8")
    code, out = drafts(vault)
    assert code == 2 and "baseline" in out


def test_epics_session_owes_each_epic_its_sections(tmp_path):
    vault = session(tmp_path, modes="epics")
    (vault / "13-epics").mkdir()
    (vault / "13-epics" / "EPC-001-sell.md").write_text(
        "---\nid: EPC-001\ntype: epic\ntitle: Sell at the till\nstate: draft\nowner: \"@mini-lead\"\nauthored: authored\n"
        "apps: [APP-till]\ndelivers: [CON-001]\n---\n\n# Sell at the till\n", encoding="utf-8")
    kinds = {p["heading"] for p in owed_at(drafts_json(vault), "13-epics/EPC-001-sell.md")}
    assert {"summary", "Still open", "Who this is for and what changes"} <= kinds, kinds


def test_for_lead_passes_the_leak_check(tmp_path):
    vault = session(tmp_path)
    decide_stock(vault)
    resolve_till_rig(vault)
    edit(vault, TILL, "\n## ", "\nThe till now reads one more thing.\n\n## ")
    code, out = drafts(vault, "--for-lead")
    assert code == 0, out
    assert out.strip()
    for line in out.splitlines():
        assert say.leak_in(line) is None, line


def test_no_open_session_is_refused(tmp_path):
    vault = make_vault(tmp_path)
    code, out = drafts(vault)
    assert code == 1 and "No session is open" in out
