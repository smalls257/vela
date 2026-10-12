"""The capability-map block: capabilities grouped by `domain`, coloured by `change`,
split into one diagram per domain when the whole map is over budget."""
from conftest import check, findings, run
from planner import render, schema
from planner.model import build
from planner.parse import parse_page
from planner.rules import flowchart_elements

CONFIG = {"initiative": "INI-900", "title": "Mini shop"}


def capability(number, change="new", domain=None, title=None):
    extra = f"domain: {domain}\n" if domain is not None else ""
    return (f"capabilities/CAP-{number:03d}-thing.md",
            f"---\nid: CAP-{number:03d}\ntype: capability\ntitle: {title or f'Thing {number}'}\nstate: assumption\n"
            f"owner: \"@t\"\nauthored: authored\norigin: proposed\nchange: {change}\n{extra}---\n\n# Thing\n")


def vault_of(*pages):
    return build([parse_page(path, text) for path, text in pages], CONFIG)


def fences(text):
    out, current = [], None
    for line in text.split("\n"):
        if line == "```mermaid":
            current = []
        elif line == "```" and current is not None:
            out.append(current)
            current = None
        elif current is not None:
            current.append(line)
    return out


def test_groups_by_domain_and_colours_by_change():
    vault = vault_of(capability(1, "new", "Booking"), capability(2, "narrow", "Pricing"),
                     capability(3, "retire", "Booking"), capability(4, "unchanged"))
    [lines] = fences(render.capability_map(vault, None))
    assert lines[0] == "flowchart TB"
    assert lines[1:5] == ['  subgraph d_booking["Booking"]', '    c_CAP_001["CAP-001 Thing 1 (new)"]',
                          '    c_CAP_003["CAP-003 Thing 3 (retire)"]', "  end"]
    assert '  subgraph d_no_domain["No domain"]' in lines
    assert lines.index('  subgraph d_pricing["Pricing"]') < lines.index('  subgraph d_no_domain["No domain"]')
    assert "  class c_CAP_002 changed" in lines and "  class c_CAP_003 retired" in lines
    assert "  class c_CAP_001 new" in lines and "  class c_CAP_004 unchanged" in lines


def test_extend_replace_and_narrow_all_read_as_changed():
    vault = vault_of(capability(1, "extend"), capability(2, "replace"), capability(3, "narrow"))
    assert "  class c_CAP_001,c_CAP_002,c_CAP_003 changed" in fences(render.capability_map(vault, None))[0]


def test_over_budget_splits_by_domain():
    pages = [capability(i, "new", "Booking") for i in range(1, 13)] + [capability(i, "new", "Pricing") for i in range(13, 25)]
    text = render.capability_map(vault_of(*pages), None)
    diagrams = fences(text)
    assert len(diagrams) == 2
    assert text.startswith("**Booking**\n\n```mermaid")
    assert "\n**Pricing**\n\n```mermaid" in text
    for lines in diagrams:
        assert flowchart_elements(lines) == 13
    for i in range(1, 25):
        assert f"c_CAP_{i:03d}[" in text


def test_one_domain_over_budget_lists_the_rest():
    pages = [capability(i, "new", "Booking") for i in range(1, 26)] + [capability(30, "new", "Pricing")]
    text = render.capability_map(vault_of(*pages), None)
    first = fences(text)[0]
    assert flowchart_elements(first) == schema.FLOWCHART_BUDGET
    assert f"**Not drawn, over the {schema.FLOWCHART_BUDGET}-element budget:** 6" in text
    assert "| Not drawn | Change |" in text
    for i in range(1, 26):
        assert f"c_CAP_{i:03d}[" in text or f"[[CAP-{i:03d}-thing\\|" in text, f"CAP-{i:03d} was dropped"


def test_no_capability_renders_none():
    assert render.capability_map(vault_of(), None) == "none"


def test_bad_domain_is_e105_and_the_map_still_renders(mini):
    path, text = capability(7, "new", "[a, b]")
    (mini / "capabilities").mkdir()
    (mini / path).write_text(text.replace('"@t"', '"@mini-lead"'), encoding="utf-8")
    _, out = check(mini)
    assert ("E105", path) in findings(out)
    vault = vault_of((path, text))
    assert '  subgraph d_no_domain["No domain"]' in fences(render.capability_map(vault, None))[0]


def test_capability_map_renders_on_the_delta_page(mini):
    (mini / "capabilities").mkdir()
    path, text = capability(7, "new", "Shop")
    (mini / path).write_text(text.replace('"@t"', '"@mini-lead"'), encoding="utf-8")
    (mini / "04a-capability-delta.md").write_text(
        "---\nid: capability-delta\ntype: initiative-section\ntitle: Capability delta\nstate: assumption\n"
        "owner: \"@mini-lead\"\nauthored: mixed\n---\n\n# Capability delta\n\n"
        "<!-- generated:capability-map sha=00000000: do not edit, run planner render -->\n"
        "<!-- /generated:capability-map -->\n", encoding="utf-8")
    code, out = run("render", "--vault", str(mini))
    assert code == 0 and "04a-capability-delta.md: capability-map" in out, out
    assert 'c_CAP_007["CAP-007 Thing 7 (new)"]' in (mini / "04a-capability-delta.md").read_text(encoding="utf-8")
    _, out = check(mini)
    assert [f for f in findings(out) if f[0] not in ("W501", "W358")] == []  # W358: the mini flow names no capability; not this test's subject, out


def test_capabilities_whose_ids_share_a_key_stay_two_nodes():
    vault = vault_of(capability(1), ("capabilities/CAP-001-copy.md", capability(1)[1].replace("Thing 1", "Copy")))
    text = render.capability_map(vault, None)
    assert text.count("Thing 1 (new)") == 1 and text.count("Copy (new)") == 1
    keys = [line.split("[")[0].strip() for line in text.split("\n") if "(new)" in line]
    assert len(keys) == 2 and len(set(keys)) == 2


def test_domains_that_differ_only_in_case_stay_two_boxes():
    vault = vault_of(capability(1, "new", "Booking"), capability(2, "new", "booking"))
    lines = fences(render.capability_map(vault, None))[0]
    boxes = [line for line in lines if line.startswith("  subgraph ")]
    assert len(boxes) == 2 and len({b.split("[")[0] for b in boxes}) == 2


def test_a_capability_with_no_id_does_not_crash_the_map():
    page = ("capabilities/loose.md", "---\ntype: capability\ntitle: Loose\n---\n\n# Loose\n")
    assert "Loose" in render.capability_map(vault_of(page), None)

