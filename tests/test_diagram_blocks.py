"""Diagrams drawn from the model: context-map, system-context and app-context.

Every node is an app page or an external provider, every edge is a contract, and
a diagram over the 20-element budget lists what it left out in a table under it.
"""
import random

from conftest import check, edit, findings, run
from vela import diagrams, render, schema
from vela.model import build
from vela.parse import parse_page
from vela.rules import flowchart_elements

CONFIG = {"initiative": "INI-900", "title": "Mini shop"}
INDEX = """---
id: building-blocks
type: index
title: Building blocks
authored: generated
---

# Building blocks

<!-- generated:context-map sha=00000000: do not edit, run vela render -->
<!-- /generated:context-map -->
"""


def app_page(name, change="changed", body=""):
    stage = "stage: baseline\n" if change in ("new", "changed") else ""
    return (f"---\nid: APP-{name}\ntype: app-building-blocks\ntitle: {name.capitalize()}\nstate: assumption\n"
            f"owner: \"@t\"\nauthored: authored\nchange: {change}\n{stage}---\n\n# {name}\n\n{body}")


def contract(cid, consumers, provider="", name="Thing"):
    links = ", ".join(f"[[{c}-building-blocks|{c}]]" for c in consumers) or "none"
    extra = f"- **Provider:** {provider}\n" if provider else ""
    return (f"### {cid} {name}\n\n{extra}- **Crosses the boundary:** x\n- **Consumers:** {links}\n"
            "- **Change policy:** versioned.\n- **Change:** new\n- **State:** assumption\n\n")


def vault_of(pages):
    return build([parse_page(path, text) for path, text in pages.items()], CONFIG)


def mermaid_lines(text):
    """The lines of every mermaid fence in a block, one list per fence."""
    fences, current = [], None
    for line in text.split("\n"):
        if line == "```mermaid":
            current = []
        elif line == "```" and current is not None:
            fences.append(current)
            current = None
        elif current is not None:
            current.append(line)
    return fences


SHOP = {
    "05-building-blocks/shop-building-blocks.md": app_page("shop", "new", contract("CON-001", ["till"])
                                                           + contract("CON-009", ["shop"], provider="Payco (external)")),
    "05-building-blocks/till-building-blocks.md": app_page("till", "changed"),
    "05-building-blocks/stock-building-blocks.md": app_page("stock", "unchanged", contract("CON-002", ["shop"])),
    "05-building-blocks/old-building-blocks.md": app_page("old", "retired", contract("CON-003", ["shop"])),
}


def test_context_map_has_one_node_per_app_and_external_and_one_edge_per_contract():
    vault = vault_of(SHOP)
    text = render.context_map(vault, None)
    [lines] = mermaid_lines(text)
    assert lines[0] == "flowchart LR"
    assert '  n_APP_shop["Shop (new)"]' in lines
    assert '  n_APP_old["Old (retired)"]' in lines
    assert '  x_payco__external_["Payco (external)"]' in lines
    assert '  n_APP_shop -->|"Thing"| n_APP_till' in lines
    assert '  n_APP_stock -->|"Thing"| n_APP_shop' in lines
    assert '  x_payco__external_ -->|"Thing"| n_APP_shop' in lines
    assert "  class n_APP_shop new" in lines and "  class n_APP_till changed" in lines
    assert "  class n_APP_stock unchanged" in lines and "  class n_APP_old retired" in lines


def test_system_context_is_the_after_view_and_lists_retired_apps():
    vault = vault_of(SHOP)
    text = render.system_context(vault, None)
    [lines] = mermaid_lines(text)
    assert '  subgraph scope["Mini shop"]' in lines
    assert '    n_APP_shop["Shop"]' in lines
    assert not [l for l in lines if "n_APP_old" in l]
    assert '  x_payco__external_["Payco (external)"]' in lines
    assert text.endswith("**Retired, not drawn:** [[old-building-blocks|Old]]")


def test_app_context_draws_only_direct_neighbors():
    pages = dict(SHOP)
    pages["05-building-blocks/far-building-blocks.md"] = app_page("far", "changed", contract("CON-004", ["till"]))
    vault = vault_of(pages)
    stock = vault.page("stock-building-blocks")
    [lines] = mermaid_lines(render.app_context(vault, stock))
    assert '  n_APP_stock["Stock (unchanged)"]' in lines and "  class n_APP_stock focus" in lines
    assert '  n_APP_stock -->|"Thing"| n_APP_shop' in lines
    assert not [l for l in lines if "n_APP_till" in l or "n_APP_far" in l]


def test_consumer_app_draws_its_provider():
    vault = vault_of(SHOP)
    [lines] = mermaid_lines(render.app_context(vault, vault.page("till-building-blocks")))
    assert '  n_APP_till["Till (changed)"]' in lines
    assert '  n_APP_shop -->|"Thing"| n_APP_till' in lines


def big_vault(count):
    hub = app_page("hub", "new", contract("CON-001", [f"a{i:02d}" for i in range(count)]))
    pages = {"05-building-blocks/hub-building-blocks.md": hub}
    for i in range(count):
        pages[f"05-building-blocks/a{i:02d}-building-blocks.md"] = app_page(f"a{i:02d}", "unchanged")
    return vault_of(pages)


def test_over_budget_draws_twenty_and_lists_every_other_node():
    vault = big_vault(25)
    text = render.context_map(vault, None)
    [lines] = mermaid_lines(text)
    assert flowchart_elements(lines) == schema.FLOWCHART_BUDGET
    assert f"**Not drawn, to keep the diagram readable (at most {schema.FLOWCHART_BUDGET} boxes, keeping the most connected):** 7" in text
    assert "| Not drawn | Contracts |" in text
    for i in range(25):
        name = f"a{i:02d}"
        assert f"n_APP_{name}[" in text or f"[[{name}-building-blocks\\|" in text, f"{name} was dropped"
    assert "| [[a24-building-blocks\\|A24]] | Thing from Hub to A24 |" in text
    assert '  others_box["7 others<br/>A18<br/>A19<br/>A20<br/>A21<br/>A22<br/>A23<br/>A24"]' in lines
    assert '  n_APP_hub -->|"Thing"| others_box' in lines
    assert '  n_APP_hub["Hub (new)"]' in lines  # the new app is drawn before unchanged ones


def test_system_context_counts_its_subgraph_against_the_budget():
    [lines] = mermaid_lines(render.system_context(big_vault(25), None))
    assert flowchart_elements(lines) == schema.FLOWCHART_BUDGET


def test_output_does_not_depend_on_page_order():
    vault = big_vault(25)
    pages = list(vault.pages)
    random.Random(7).shuffle(pages)
    shuffled = build(pages, CONFIG)
    for generator in (render.context_map, render.system_context):
        assert generator(vault, None) == generator(shuffled, None)
    hub = vault.page("hub-building-blocks")
    assert render.app_context(vault, hub) == render.app_context(shuffled, shuffled.page("hub-building-blocks"))


def test_labels_cannot_break_out_of_the_diagram():
    hostile = app_page("evil", "new", contract("CON-001", ["evil"], provider='Pay"] --> X[[%%{init}]];#9;'))
    hostile = hostile.replace("title: Evil", 'title: "Evil\\"] --> y{{x}} %%{init: {}}%% <b>|pipe|"')
    text = render.context_map(vault_of({"05-building-blocks/evil-building-blocks.md": hostile}), None)
    [lines] = mermaid_lines(text)
    assert "%%" not in text and "[[" not in text and "<" not in text and ";" not in text
    for line in lines[1:]:
        assert not line.lstrip().startswith("---")
        if '["' in line:
            label = line.split('["', 1)[1].rsplit('"]', 1)[0]
            assert not set(label) & set('"[]{}|#<>;`'), label


def test_safe_label_falls_back_when_nothing_is_left():
    assert diagrams.safe_label('"[]"', "APP-x") == "APP-x"
    assert diagrams.safe_label("  Call   center ", "x") == "Call center"


def test_malformed_change_and_title_do_not_crash():
    page = app_page("odd", "changed").replace("change: changed", "change: [a, b]").replace("title: Odd", "title: [x]")
    text = render.context_map(vault_of({"05-building-blocks/odd-building-blocks.md": page}), None)
    assert '  n_APP_odd["odd-building-blocks"]' in text


# Through the CLI, on the mini vault: render writes them, check budgets them, and only on their page.

def test_render_fills_the_blocks_and_check_budgets_them(mini):
    (mini / "05-building-blocks" / "05-building-blocks.md").write_text(INDEX, encoding="utf-8")
    code, out = run("render", "--vault", str(mini))
    assert code == 0 and "05-building-blocks/05-building-blocks.md: context-map" in out, out
    text = (mini / "05-building-blocks" / "05-building-blocks.md").read_text(encoding="utf-8")
    assert '  n_APP_shop -->|"Sale API"| n_APP_till' in text
    code, out = check(mini)
    assert code == 0 and findings(out) == [], out
    code, out = run("render", "--vault", str(mini))
    assert "0 blocks changed" in out


def test_generated_diagram_over_budget_never_trips_e601(mini):
    for i in range(30):
        (mini / "05-building-blocks" / f"z{i:02d}-building-blocks.md").write_text(
            app_page(f"z{i:02d}", "unchanged").replace('"@t"', '"@mini-lead"'), encoding="utf-8")
    (mini / "05-building-blocks" / "05-building-blocks.md").write_text(INDEX, encoding="utf-8")
    run("render", "--vault", str(mini))
    _, out = check(mini)
    assert "E601" not in out, out
    text = (mini / "05-building-blocks" / "05-building-blocks.md").read_text(encoding="utf-8")
    assert "| Not drawn | Contracts |" in text, "the diagram never went over budget, so E601 was not tested"


def test_context_map_is_refused_on_another_page(mini):
    edit(mini / "01-goals.md", "## Goals\n", "## Goals\n\n<!-- generated:context-map sha=00000000: do not edit, "
         "run vela render -->\n<!-- /generated:context-map -->\n")
    _, out = check(mini)
    assert ("E403", "01-goals.md") in findings(out)


def test_a_contract_an_app_consumes_from_itself_draws_a_loop():
    vault = vault_of({"05-building-blocks/shop-building-blocks.md": app_page("shop", "new", contract("CON-001", ["shop"]))})
    [lines] = mermaid_lines(render.app_context(vault, vault.page("shop-building-blocks")))
    assert '  n_APP_shop -->|"Thing"| n_APP_shop' in lines


def test_an_external_provider_spelled_two_ways_is_two_nodes_not_a_guess():
    body = contract("CON-001", ["shop"], provider="Payco") + contract("CON-002", ["shop"], provider="Payco (external)")
    vault = vault_of({"05-building-blocks/shop-building-blocks.md": app_page("shop", "new", body)})
    [lines] = mermaid_lines(render.context_map(vault, None))
    assert '  x_payco["Payco"]' in lines and '  x_payco__external_["Payco (external)"]' in lines


# Fix round 1: collisions, skipped contracts, all-retired, over-budget app context, hostile table text.

def node_lines(lines):
    return [l for l in lines if '["' in l and "-->" not in l]


def test_names_that_share_a_key_stay_two_nodes():
    pages = {"05-building-blocks/a-b-building-blocks.md": app_page("a-b", "new", contract("CON-001", ["a_b"])),
             "05-building-blocks/a_b-building-blocks.md": app_page("a_b", "new")}
    [lines] = mermaid_lines(render.context_map(vault_of(pages), None))
    assert len(node_lines(lines)) == 2
    keys = {l.split("[", 1)[0].strip() for l in node_lines(lines)}
    assert len(keys) == 2 and all(k.startswith("n_APP_a_b") for k in keys)


def test_externals_that_differ_only_by_case_stay_two_nodes_and_keep_their_edges():
    body = contract("CON-001", ["shop"], provider="Payco") + contract("CON-002", ["shop"], provider="PAYCO")
    vault = vault_of({"05-building-blocks/shop-building-blocks.md": app_page("shop", "new", body)})
    [lines] = mermaid_lines(render.context_map(vault, None))
    externals = [l for l in node_lines(lines) if l.strip().startswith("x_")]
    assert len(externals) == 2
    edges = [l for l in lines if "-->" in l]
    assert len({l.split("-->")[0] for l in edges}) == 2
    assert render.context_map(vault, None) == render.context_map(vault, None)


NOTE = "---\nid: note\ntype: concept\ntitle: Note\nauthored: authored\n---\n\n# Note\n\n"


def test_a_contract_on_a_non_app_page_is_listed_with_its_reason():
    pages = dict(SHOP)
    pages["05-building-blocks/note.md"] = NOTE + contract("CON-005", ["shop"])
    vault = vault_of(pages)
    for generator in (render.context_map, render.system_context):
        text = generator(vault, None)
        assert "| CON-005 | provider is not an app page |" in text, generator.__name__
        assert "**Contracts not drawn:** " in text


def test_the_after_view_names_retired_contracts_and_retired_apps():
    pages = dict(SHOP)
    pages["05-building-blocks/stock-building-blocks.md"] = app_page(
        "stock", "unchanged", contract("CON-002", ["shop", "old"]))
    text = render.system_context(vault_of(pages), None)
    assert "| CON-003 | provider APP-old is retired |" in text
    assert "| CON-002 | consumer APP-old is retired |" in text
    assert text.endswith("**Retired, not drawn:** [[old-building-blocks|Old]]")


def test_system_context_keeps_the_retired_list_when_every_app_is_retired():
    pages = {"05-building-blocks/old-building-blocks.md": app_page("old", "retired", contract("CON-003", ["old"]))}
    text = render.system_context(vault_of(pages), None)
    assert text != "none"
    assert text.endswith("**Retired, not drawn:** [[old-building-blocks|Old]]")
    assert "| CON-003 | provider APP-old is retired |" in text
    assert "```mermaid" not in text


def test_app_context_over_budget_lists_what_it_left_out():
    vault = big_vault(25)
    text = render.app_context(vault, vault.page("hub-building-blocks"))
    [lines] = mermaid_lines(text)
    assert flowchart_elements(lines) == schema.FLOWCHART_BUDGET
    assert f"**Not drawn, to keep the diagram readable (at most {schema.FLOWCHART_BUDGET} boxes, keeping the most connected):** 7" in text
    assert '  n_APP_hub["Hub (new)"]' in lines and "  class n_APP_hub focus" in lines
    for i in range(25):
        name = f"a{i:02d}"
        assert f"n_APP_{name}[" in text or f"[[{name}-building-blocks\\|" in text, f"{name} was dropped"


def test_hostile_external_names_cannot_break_the_tables():
    hostile = "Pay [[x|y]] | z"
    pages = {"05-building-blocks/hub-building-blocks.md": app_page(
        "hub", "new", contract("CON-001", [f"a{i:02d}" for i in range(25)]) + contract("CON-002", ["hub"], provider=hostile))}
    for i in range(25):
        pages[f"05-building-blocks/a{i:02d}-building-blocks.md"] = app_page(f"a{i:02d}", "unchanged")
    text = render.context_map(vault_of(pages), None)
    table = text.split("| Not drawn | Contracts |", 1)[1]
    assert "[[x" not in table and "y]]" not in table
    assert all(line.count("|") - line.count("\\|") == 3 for line in table.split("\n") if line.startswith("| ["))


# The cut keeps the most connected boxes, folds the rest into one "others" box, and never loses the focus app.

def ranked_vault(leaf_names):
    """Zeta provides one contract to five apps; Alpha provides one to a single app; the leaves have none of their own."""
    pages = {"05-building-blocks/zeta-building-blocks.md":
             app_page("zeta", "unchanged", contract("CON-001", ["m0", "m1", "m2", "m3", "m4"], name="Feed")),
             "05-building-blocks/alpha-building-blocks.md": app_page("alpha", "unchanged", contract("CON-002", ["m0"], name="Ping"))}
    for name in ["m0", "m1", "m2", "m3", "m4", *leaf_names]:
        pages[f"05-building-blocks/{name}-building-blocks.md"] = app_page(name, "unchanged")
    return vault_of(pages)


def test_an_unconnected_app_is_cut_before_any_connected_one():
    graph = diagrams.context_graph(ranked_vault(["a_loose", "b_loose"]))
    drawn, left_out = diagrams.fit(graph, 7)
    assert {n.ref for n in left_out} == {"APP-a_loose", "APP-b_loose"}
    assert "APP-zeta" in {n.ref for n in drawn.nodes} and "APP-alpha" in {n.ref for n in drawn.nodes}


def test_the_hub_is_kept_before_a_one_contract_app_when_only_two_fit():
    drawn, left_out = diagrams.fit(diagrams.context_graph(ranked_vault([])), 2)
    assert [n.ref for n in drawn.nodes] == ["APP-m0", "APP-zeta"]  # m0 has two contracts, zeta five; alpha has one
    assert "APP-alpha" in {n.ref for n in left_out}


def test_the_focus_app_stays_even_with_the_fewest_connections():
    vault = ranked_vault([])
    graph = diagrams.app_graph(vault, vault.page("m1-building-blocks"))
    drawn, _ = diagrams.fit(graph, 1)
    assert [n.style for n in drawn.nodes] == ["focus"]
    wide = diagrams.app_graph(vault, vault.page("zeta-building-blocks"))
    drawn, left_out = diagrams.fit(wide, 3)
    assert "focus" in {n.style for n in drawn.nodes} and len(left_out) == 3


def test_the_others_box_exists_only_when_something_is_left_out():
    small = render.context_map(vault_of(SHOP), None)
    assert "others_box" not in small and "Not drawn" not in small
    assert "others_box" in render.context_map(big_vault(25), None)


def test_the_others_box_edges_are_rolled_up_and_keep_provider_to_consumer_direction():
    leaves = [f"a{i:02d}" for i in range(30)]
    pages = {"05-building-blocks/hub-building-blocks.md": app_page("hub", "new", contract("CON-001", leaves, name="Feed")
                                                                  + contract("CON-002", leaves, name="Audit")),
             "05-building-blocks/zlate-building-blocks.md": app_page("zlate", "unchanged", contract("CON-003", ["hub"], name="Report"))}
    for name in leaves:
        pages[f"05-building-blocks/{name}-building-blocks.md"] = app_page(name, "unchanged")
    [lines] = mermaid_lines(render.context_map(vault_of(pages), None))
    edges = [l for l in lines if "others_box" in l and "-->" in l]
    assert sorted(edges) == ['  n_APP_hub -->|"2 contracts"| others_box', '  others_box -->|"Report"| n_APP_hub']
    assert flowchart_elements(lines) == schema.FLOWCHART_BUDGET


def test_a_long_others_list_stops_at_a_cap_and_points_to_the_table():
    [lines] = mermaid_lines(render.context_map(big_vault(40), None))
    [box] = [l for l in lines if l.startswith("  others_box[")]
    assert box.count("<br/>") == diagrams.OTHERS_NAMES_SHOWN + 1
    assert box.endswith('and 14 more, listed below"]')


def test_the_cut_is_deterministic():
    assert render.context_map(big_vault(30), None) == render.context_map(big_vault(30), None)
    assert render.system_context(big_vault(30), None) == render.system_context(big_vault(30), None)


def test_the_others_box_is_in_the_key():
    assert "dashed outline: the boxes left out" in render.context_map(big_vault(25), None)


def test_the_others_label_breaks_lines_with_a_plain_br_slash_tag_inside_the_quotes():
    """Mermaid (the viewer's strict, no-HTML-labels mode, and GitHub's preview) turns <br/> into a line break.
    An escaped tag (&lt;br/&gt;) or a bare <br> would show as text, and a quote or bracket would end the label early."""
    text = render.context_map(big_vault(25), None)
    [lines] = mermaid_lines(text)
    [box] = [l for l in lines if l.startswith("  others_box[")]
    assert box == '  others_box["7 others<br/>A18<br/>A19<br/>A20<br/>A21<br/>A22<br/>A23<br/>A24"]'
    assert "&lt;" not in text and "&amp;" not in text and "<br>" not in text


def test_two_contracts_with_one_name_are_counted_as_two_contracts_by_id():
    leaves = [f"a{i:02d}" for i in range(30)]
    pages = {"05-building-blocks/hub-building-blocks.md": app_page("hub", "new", contract("CON-001", leaves, name="Feed")
                                                                  + contract("CON-002", leaves, name="Feed"))}
    for name in leaves:
        pages[f"05-building-blocks/{name}-building-blocks.md"] = app_page(name, "unchanged")
    [lines] = mermaid_lines(render.context_map(vault_of(pages), None))
    assert [l for l in lines if "others_box" in l and "-->" in l] == ['  n_APP_hub -->|"2 contracts"| others_box']


def test_a_title_cannot_smuggle_a_tag_into_the_others_box_only_the_line_break_is_allowed():
    pages = {}
    for i in range(25):
        title = "<b>Bold</b><script>x</script><br/>" if i == 24 else f"A{i:02d}"
        pages[f"05-building-blocks/a{i:02d}-building-blocks.md"] = app_page(f"a{i:02d}", "unchanged").replace(f"title: A{i:02d}", f"title: {title}")
    text = render.context_map(vault_of(pages), None)
    [lines] = mermaid_lines(text)
    [box] = [l for l in lines if l.startswith("  others_box[")]
    assert "Bold" in box and "script" in box  # the words stay; the tags are gone
    assert box.count("<") == box.count("<br/>")
    assert "<b>" not in box and "<script" not in box and "</" not in box
