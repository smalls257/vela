"""Owed copies: each catalogue entry applied once per subject its trigger matches.

The copies are computed by code, so the same vault always owes the same questions in the same
order, and a copy keeps its ID while its subject keeps its ID."""
import random
import shutil

from conftest import REPO, edit
from planner import catalog, cli, model, parse, questions

FIXTURE = REPO / "examples" / "unified-booking"


def owed_ids(vault):
    return [c.id for c in questions.owed(vault)]


def load(root):
    return cli.load_vault(root)


def test_the_fixture_owes_fifty_seven_copies_in_copy_id_order():
    vault = load(FIXTURE)
    ids = owed_ids(vault)
    assert len(ids) == 57 and ids == sorted(ids)
    by_scope = {}
    for copy in questions.owed(vault):
        by_scope[copy.entry.scope] = by_scope.get(copy.entry.scope, 0) + 1
    assert by_scope == {"initiative": 12, "app": 12, "contract": 14, "capability": 6, "party": 8, "stored-value": 5}
    for expected in ("Q-FIN-01@INI-002", "Q-DAT-02@APP-booking", "Q-OPS-02@CON-006",
                     "Q-OPS-03@CAP-023", "Q-PTN-02@PTY-02", "Q-FIN-03@SV-01"):
        assert expected in ids


def test_only_new_and_changed_apps_owe_app_questions():
    vault = load(FIXTURE)
    apps = sorted({c.subject.id for c in questions.owed(vault) if c.entry.scope == "app"})
    assert apps == ["APP-booking", "APP-call-centre", "APP-kiosks", "APP-notifications", "APP-pricing", "APP-website"]
    assert not any(c.subject.id == "APP-ferrymaster" for c in questions.owed(vault))


def test_q_ptn_04_is_owed_only_for_a_new_or_changed_contract_with_an_external_provider(tmp_path):
    # CON-007 has an external provider but its change is "new consumers", so the fixture owes none
    assert not [c for c in questions.owed(load(FIXTURE)) if c.entry.id == "Q-PTN-04"]
    root = tmp_path / "vault"
    shutil.copytree(FIXTURE, root)
    page = next(p for p in root.rglob("*.md") if "### CON-007" in p.read_text(encoding="utf-8"))
    text = page.read_text(encoding="utf-8")
    head, tail = text.split("### CON-007", 1)
    page.write_text(head + "### CON-007" + tail.replace("- **Change:** new consumers", "- **Change:** new", 1), encoding="utf-8")
    assert [c.id for c in questions.owed(load(root)) if c.entry.id == "Q-PTN-04"] == ["Q-PTN-04@CON-007"]


def test_the_same_vault_in_any_page_order_owes_the_same_copies():
    pages = [parse.parse_page(p.relative_to(FIXTURE).as_posix(), p.read_text(encoding="utf-8"))
             for p in sorted(FIXTURE.rglob("*.md")) if "voice" not in p.parts and p.name not in ("CLAUDE.md", "CONVENTIONS.md")]
    config = {"initiative": "INI-002", "title": "Unified Booking"}
    first = model.build(pages, config, catalogue=cli.load_catalogue())
    random.Random(7).shuffle(pages)
    second = model.build(pages, config, catalogue=cli.load_catalogue())
    assert owed_ids(first) == owed_ids(second)
    assert [questions.blocks(first, c) for c in questions.owed(first)] == \
        [questions.blocks(second, c) for c in questions.owed(second)]


def test_a_copy_keeps_its_id_when_its_file_is_renamed(mini):
    before = owed_ids(load(mini))
    (mini / "05-building-blocks" / "shop-building-blocks.md").rename(mini / "05-building-blocks" / "shop-renamed.md")
    assert owed_ids(load(mini)) == before  # the id is APP-shop either way; E107 reports the file name


def test_a_removed_subject_takes_its_copies_with_it(mini):
    assert any(i.endswith("@APP-till") for i in owed_ids(load(mini)))
    (mini / "05-building-blocks" / "till-building-blocks.md").unlink()
    assert not any(i.endswith("@APP-till") for i in owed_ids(load(mini)))


def test_a_change_that_is_not_text_owes_nothing_and_never_crashes(mini):
    edit(mini / "05-building-blocks" / "shop-building-blocks.md", "change: new\n", "change: [new]\n")
    assert not any(i.endswith("@APP-shop") for i in owed_ids(load(mini)))


def test_a_regulator_owes_the_regulator_question_and_not_the_partner_ones(mini):
    (mini / "03-context-and-scope.md").write_text(
        "---\nid: context-and-scope\ntype: index\ntitle: Context\nauthored: authored\n---\n\n## Outside parties\n\n"
        "### PTY-01 Trading Standards\n\n- **Relationship:** Regulator\n- **Agreements:** none known\n", encoding="utf-8")
    ids = [i for i in owed_ids(load(mini)) if i.endswith("@PTY-01")]
    assert ids == ["Q-REG-03@PTY-01"]


def test_with_no_catalogue_nothing_is_owed(mini):
    pages = [parse.parse_page(p.relative_to(mini).as_posix(), p.read_text(encoding="utf-8")) for p in mini.rglob("*.md")]
    vault = model.build(pages, {"initiative": "INI-900", "title": "Mini"})
    assert vault.catalogue is catalog.EMPTY and questions.owed(vault) == ()


def test_what_an_open_copy_blocks():
    vault = load(FIXTURE)
    copies = {c.id: c for c in questions.owed(vault)}
    initiative = questions.blocks(vault, copies["Q-OPS-04@INI-002"])
    assert initiative == ("ADR-0001", "ADR-0002", "ADR-0003", "ADR-0004")
    assert questions.blocks(vault, copies["Q-OPS-02@CON-003"]) == ("CON-003",)
    assert questions.blocks(vault, copies["Q-DAT-02@APP-pricing"]) == ("APP-pricing", "CON-003", "EPC-038")
    assert questions.blocks(vault, copies["Q-OPS-03@CAP-014"]) == ("CAP-014", "EPC-031")
    assert questions.blocks(vault, copies["Q-PTN-02@PTY-02"]) == ("ADR-0002", "CON-006")
    assert questions.blocks(vault, copies["Q-OPS-05@INI-002"]) == ()


def test_subjects_know_their_kind_title_and_facts():
    vault = load(FIXTURE)
    found = {s.id: s for s in questions.subjects(vault)}
    assert found["INI-002"].kind == "initiative" and found["INI-002"].title == "Unified Booking"
    assert found["CON-007"].fact_map() == {"change": "new consumers", "state": "fact", "provider": "external"}
    assert found["PTY-01"].fact_map() == {"relationship": "supplier"} and found["PTY-01"].title == "Tidepay"
    assert found["SV-01"].page.path == "03-context-and-scope.md"
    assert [s.kind for s in questions.subjects(vault)] == sorted(
        (s.kind for s in questions.subjects(vault)), key=catalog.SCOPES.index)
