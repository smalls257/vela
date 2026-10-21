"""Which diagrams the dashboard steps through and which Mermaid draws (design_data.stepper_reads). A diagram is never shown
with its steps missing: anything the step-through reader can't read to the end goes to the bundled renderer."""
from vela.explorer import design_data

PLAIN = "sequenceDiagram\n    participant A\n    participant B as Billing\n    A->>B: charge\n    Note over A,B: settled\n    loop retry\n    B-->>A: ok\n    end"


def test_a_plain_sequence_is_stepped_through():
    assert design_data.stepper_reads(PLAIN)


def test_autonumber_quoted_names_and_rect_go_to_mermaid():
    assert not design_data.stepper_reads('sequenceDiagram\n    participant U as "Web shopper"\n    U->>A: hi')
    assert not design_data.stepper_reads("sequenceDiagram\n    A->>B: hi\n    rect rgb(1,2,3)\n    B-->>A: ok\n    end")
    assert not design_data.stepper_reads("sequenceDiagram\n    A->>B: hi\n    activate B")


def test_other_diagram_kinds_and_empty_sequences_go_to_mermaid():
    assert not design_data.stepper_reads("flowchart LR\n    A --> B")
    assert not design_data.stepper_reads("stateDiagram-v2\n    [*] --> A")
    assert not design_data.stepper_reads("sequenceDiagram\n    participant A")


def test_the_library_is_carried_only_when_a_diagram_needs_it():
    plain = {"flows": [{"stepper": True}], "diagrams": []}
    odd = {"flows": [], "diagrams": [{"stepper": False}]}
    assert not design_data.needs_drawing_library({"a": plain})
    assert design_data.needs_drawing_library({"a": plain, "b": odd})
