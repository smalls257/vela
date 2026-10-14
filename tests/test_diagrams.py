import pytest

from conftest import check, edit, findings
from planner.rules import flowchart_elements, sequence_participants

FLOW = "06-runtime/flows/FLO-001-buy.md"


@pytest.mark.parametrize("lines, expected", [
    (["flowchart LR", "  a --> b", "  b --> c"], 3),
    (['flowchart LR', '  Web[Public website] -- screen-scrape --> FM[(FERRYMASTER)]', '  Web -- quote --> P[Pricing]'], 3),
    (['flowchart LR', '  bk -->|"CON-003"| gw --> pr', '  web -.->|"retired"| gw'], 4),
    (['flowchart LR', '  B -. state changed .-> EB{{Event bus}}', '  EB -.-> N[Notifications]'], 3),
    (['flowchart LR', '  web & cc & kio -->|"CON-001"| api', '  subgraph booking["Booking"]', '    api["Booking API"]', '  end'], 5),
    (['flowchart LR', '  bk["<b>Booking</b><br/>new"]', '  classDef focus fill:#1f4e79,color:#fff', '  class bk focus'], 1),
    (['flowchart TB', '  CH -- "customer of" --> B', '  B -- "anticorruption layer, owned by Booking" --> FM'], 3),
])
def test_flowchart_elements(lines, expected):
    assert flowchart_elements(lines) == expected


def test_sequence_participants_counts_declared_and_implicit():
    lines = ["sequenceDiagram", "  participant A as Alpha", "  participant B", "  A->>B: hi", "  B-->>C: reply", "  C-)A: async"]
    assert sequence_participants(lines) == 3


def test_flowchart_over_budget(mini):
    nodes = "\n".join(f"  n{i} --> n{i + 1}" for i in range(20))
    edit(mini / "05-building-blocks/shop-building-blocks.md", '  shop -->|"CON-002"| stock["Stock"]\n',
         '  shop -->|"CON-002"| stock["Stock"]\n' + nodes + "\n")
    _, out = check(mini)
    assert findings(out) == [("E601", "05-building-blocks/shop-building-blocks.md")]
    assert "24 elements" in out


def test_sequence_over_budget(mini):
    extra = "".join(f"  participant P{i}\n" for i in range(6))
    edit(mini / FLOW, "  participant K as Stock\n", "  participant K as Stock\n" + extra)
    _, out = check(mini)
    assert findings(out) == [("E602", FLOW)]


def test_unsupported_diagram(mini):
    edit(mini / FLOW, "sequenceDiagram\n", "C4Context\n")
    _, out = check(mini)
    assert sorted(findings(out)) == [("E603", FLOW), ("E604", FLOW)]  # its sequence lines are not C4 either


@pytest.mark.parametrize("lines, expected", [
    (["flowchart LR", "  api-gw --> x"], 2),
    (["flowchart LR", "  svc.v2 --> x"], 2),
    (["flowchart LR", "  a-->b", "  c --> d"], 4),
    (["flowchart LR", "  a-.->b"], 2),
    (["flowchart LR", "  a --> b; b --> c"], 3),
    (["flowchart LR", '  a["x;y"] --> b'], 2),
    (["flowchart LR", "  a -->|label| b"], 2),
    (["flowchart LR", "  a -->|my-label.x| b"], 2),
    (["flowchart LR", "  a[Some text] --> b"], 2),
    (["flowchart LR", "  a(Some-text) --> b"], 2),
    (["flowchart LR", "  a -- my-label --> b"], 2),
])
def test_flowchart_ids_and_separators(lines, expected):
    assert flowchart_elements(lines) == expected


@pytest.mark.parametrize("lines, expected", [
    (["sequenceDiagram", "  Web-App->>API: x"], 2),
    (["sequenceDiagram", "  A.b-->>C: x"], 2),
    (["sequenceDiagram", "  create participant X", "  create actor Y"], 2),
    (["sequenceDiagram", "  A<<->>B: x", "  B<<-->>C: y"], 3),
])
def test_sequence_ids_create_and_bidirectional(lines, expected):
    assert sequence_participants(lines) == expected


def test_a_linked_provider_is_named_by_its_link_label():
    from planner.diagrams import external_name
    assert external_name("[[03-context-and-scope#PTY-01 Brightwater|Brightwater]]") == "Brightwater"
    assert external_name("[[03-context-and-scope#PTY-01 Brightwater]]") == "PTY-01 Brightwater"
    assert external_name("Tidepay") == "Tidepay"
