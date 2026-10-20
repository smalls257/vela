"""`vela explore` with no --design: where each app's team design doc comes from (explorer/design_find.py).

Lookup order: --design, `design:` on the app page, `designs:` in .vela.yaml, then a local GitHub/Code link whose
repository holds docs/tech-design/*.md with `vault.app` naming the app. Local files only; a bad path is a warning
in the build report, never a failed build.
"""
import json
import re
import shutil

import pytest

from conftest import REPO, edit, run

EXAMPLE = REPO / "examples" / "unified-booking"
DEMO_DESIGNS = REPO / "tests" / "fixtures" / "explorer" / "demo_designs"
PRICING_PAGE = "05-building-blocks/pricing-building-blocks.md"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)
PRICING_DOC = "docs/tech-design/pricing.md"


@pytest.fixture
def world(tmp_path):
    """A vault and, beside it, a team repository with the Pricing design in it."""
    vault, team = tmp_path / "vault", tmp_path / "team"
    shutil.copytree(EXAMPLE, vault)
    (team / "docs/tech-design").mkdir(parents=True)
    shutil.copy(DEMO_DESIGNS / "pricing" / PRICING_DOC, team / PRICING_DOC)
    return vault, team


def explore(vault, *extra):
    return run("explore", str(vault), "--today", "2026-11-20", *extra)


def designs_on_the_page(vault):
    page = (vault / "dashboard.html").read_text(encoding="utf-8")
    return sorted(d["appId"] for d in json.loads(DATA.search(page).group(1))["designs"].values())


def say_vault_app(doc, app):
    """The doc in the inside-view format: a `vault:` block in its frontmatter naming the app."""
    edit(doc, "prereqs:\n", f"vault:\n  app: {app}\n  initiative: INI-002\nprereqs:\n")


def test_a_design_named_in_vela_yaml_is_found(world):
    vault, _ = world
    with open(vault / ".vela.yaml", "a", encoding="utf-8") as config:
        config.write(f"designs: {{APP-pricing: ../team/{PRICING_DOC}}}\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "(APP-pricing): using the design" in said and "designs: in .vela.yaml" in said, said
    assert designs_on_the_page(vault) == ["APP-pricing"]


def test_a_design_named_on_the_app_page_is_found(world):
    vault, _ = world
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", f"id: APP-pricing\ndesign: ../team/{PRICING_DOC}\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "(APP-pricing): using the design" in said and "design: on its page" in said, said
    assert designs_on_the_page(vault) == ["APP-pricing"]


@pytest.mark.parametrize("how", ["a file:// URL", "a bare path"])
def test_a_local_repo_link_finds_the_doc_whose_vault_app_names_the_app(world, how):
    vault, team = world
    say_vault_app(team / PRICING_DOC, "APP-pricing")
    shutil.copy(DEMO_DESIGNS / "booking" / "docs/tech-design/booking.md", team / "docs/tech-design/booking.md")
    say_vault_app(team / "docs/tech-design/booking.md", "APP-booking")
    link = team.as_uri() if how == "a file:// URL" else "../team"
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", f"id: APP-pricing\nlinks: {{GitHub: \"{link}\"}}\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "(APP-pricing): using the design" in said and "because it names this app" in said, said
    if how == "a file:// URL":  # a local clone is a link vela check accepts; a bare path is not a link
        assert run("check", "--vault", str(vault), "--today", "2026-11-20")[0] == 0
    assert designs_on_the_page(vault) == ["APP-pricing"]


def test_an_app_with_nothing_to_find_is_not_loaded_and_the_report_says_which(world):
    vault, _ = world
    code, said = explore(vault)
    assert code == 0, said
    assert "no design yet for" in said and "APP-pricing" in said, said
    assert designs_on_the_page(vault) == []


def test_a_repo_with_no_doc_for_the_app_is_said_not_assumed(world):
    vault, team = world
    say_vault_app(team / PRICING_DOC, "APP-booking")  # a doc, but for another app
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", f"id: APP-pricing\nlinks: {{Code: \"{team.as_uri()}\"}}\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "none has vault: app: APP-pricing" in said, said
    assert designs_on_the_page(vault) == []


def test_a_web_link_is_never_a_design_source(world):
    vault, _ = world
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", "id: APP-pricing\nlinks: {GitHub: \"https://github.example.com/harborline/pricing\"}\n")
    code, said = explore(vault)
    assert code == 0, said
    assert "warning: Pricing (APP-pricing)" not in said and designs_on_the_page(vault) == []


@pytest.mark.parametrize("where", ["page", "config", "link"])
def test_a_bad_path_is_a_visible_warning_and_the_page_still_builds(world, where):
    vault, _ = world
    if where == "page":
        edit(vault / PRICING_PAGE, "id: APP-pricing\n", "id: APP-pricing\ndesign: ../nowhere/pricing.md\n")
    elif where == "config":
        with open(vault / ".vela.yaml", "a", encoding="utf-8") as config:
            config.write("designs: {APP-pricing: ../nowhere/pricing.md}\n")
    else:
        edit(vault / PRICING_PAGE, "id: APP-pricing\n", "id: APP-pricing\nlinks: {GitHub: \"file:///nowhere/at/all\"}\n")
    code, said = explore(vault)
    assert code == 0, said
    assert re.search(r"warning: Pricing \(APP-pricing\): .*(is not a file|is not a folder)", said), said
    assert (vault / "dashboard.html").is_file() and designs_on_the_page(vault) == []


def test_a_design_flag_wins_and_the_app_is_not_looked_up(world):
    vault, _ = world
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", "id: APP-pricing\ndesign: ../nowhere/pricing.md\n")
    code, said = explore(vault, "--design", f"APP-pricing={DEMO_DESIGNS / 'pricing' / PRICING_DOC}")
    assert code == 0, said
    assert "warning: Pricing (APP-pricing)" not in said and "(APP-pricing): using the design" not in said, said
    assert designs_on_the_page(vault) == ["APP-pricing"]


def test_designs_that_is_not_a_map_is_a_warning(world):
    vault, _ = world
    with open(vault / ".vela.yaml", "a", encoding="utf-8") as config:
        config.write("designs: ../team/docs/tech-design/pricing.md\n")
    code, said = explore(vault)
    assert code == 0 and "designs: is not a map" in said, said


def test_check_wants_design_to_be_a_path(world):
    vault, _ = world
    edit(vault / PRICING_PAGE, "id: APP-pricing\n", "id: APP-pricing\ndesign: [1, 2]\n")
    code, out = run("check", "--vault", str(vault), "--today", "2026-11-20")
    assert code == 1 and "'design: [1, 2]' is not a path to a design doc" in out, out


# ---------------------------------------------------------------- the vault's own docs/tech-design: no configuration

def put_in_vault(vault, name="pricing"):
    (vault / "docs/tech-design").mkdir(parents=True, exist_ok=True)
    doc = vault / "docs/tech-design" / f"{name}.md"
    shutil.copy(DEMO_DESIGNS / "pricing" / PRICING_DOC, doc)
    return doc


def test_a_design_in_the_vaults_docs_folder_is_found_by_file_name_with_no_config(world):
    vault, _ = world
    put_in_vault(vault)
    code, said = explore(vault)
    assert code == 0, said
    assert "(APP-pricing): using the design docs/tech-design/pricing.md" in said and "in the plan's folder, because" in said, said
    assert designs_on_the_page(vault) == ["APP-pricing"]


def test_vault_app_wins_over_the_file_name(world):
    vault, _ = world
    edit(put_in_vault(vault, "pricing"), "../harborline-vault/05-building-blocks/pricing-building-blocks.md", "elsewhere.md")
    other = put_in_vault(vault, "zz-other")
    say_vault_app(other, "APP-pricing")
    code, said = explore(vault)
    assert code == 0 and "docs/tech-design/zz-other.md" in said and "because it names this app" in said, said


def test_a_design_whose_prereqs_name_the_app_page_is_found(world):
    vault, _ = world
    doc = put_in_vault(vault, "odd-name")
    edit(doc, "prereqs:\n", "prereqs:\n  - path: 05-building-blocks/pricing-building-blocks.md\n")
    code, said = explore(vault)
    assert code == 0 and "docs/tech-design/odd-name.md" in said and "it points to this app's page" in said, said


def test_a_vault_design_for_no_app_is_said_and_the_not_loaded_report_names_the_folder(world):
    vault, _ = world
    edit(put_in_vault(vault, "unrelated"), "../harborline-vault/05-building-blocks/pricing-building-blocks.md", "elsewhere.md")
    code, said = explore(vault)
    assert code == 0, said
    assert "none names it, points to its page or has its file name" in said and "docs/tech-design/<slug>.md" in said, said
    assert designs_on_the_page(vault) == []


def test_a_design_and_plan_in_the_vault_docs_are_found_together_and_check_ignores_docs(world):
    vault, team = world
    put_in_vault(vault)
    (vault / "docs/plan").mkdir()
    shutil.copy(team / "docs/tech-design/pricing.md", vault / "docs/adr-note.md") if False else None
    plan = (vault / "docs/plan/pricing-breakdown.md")
    plan.write_text((DEMO_DESIGNS / "booking/docs/plan/booking-breakdown.md").read_text(encoding="utf-8")
                    .replace("docs/tech-design/booking.md", PRICING_DOC), encoding="utf-8")
    (vault / "CONTEXT.md").write_text("# Context\n\nTerms the design uses.\n", encoding="utf-8")
    code, said = explore(vault)
    assert code == 0 and "(APP-pricing): using the build plan docs/plan/pricing-breakdown.md" in said, said
    page = (vault / "dashboard.html").read_text(encoding="utf-8")
    assert len(json.loads(DATA.search(page).group(1))["plans"]) == 1
    checked, out = run("check", "--vault", str(vault), "--today", "2026-11-20")
    assert checked == 0 and "docs/" not in out, out
