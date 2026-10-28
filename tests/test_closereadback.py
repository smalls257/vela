"""`closereadback.owed`: close reads back only the quotes picked for the pull request, never what was settled."""
from vela.closereadback import DECISION, QUOTE, WHY, Sentence, owed


def test_only_picked_quotes_are_owed():
    found = [Sentence("CON-1", DECISION, "p.md", 2, "Yes."), Sentence("CON-1", WHY, "p.md", 3, "Because."),
             Sentence("^c04", QUOTE, "", 4, "We ship Monday.")]
    assert [s.line for s in owed(found)] == [QUOTE]


def test_nothing_settled_is_owed():
    assert owed([Sentence("CON-1", WHY, "p.md", 3, "Because.")]) == []
