"""The import queue's wording answer keeps the citation its page will write, so paging never reads the notes."""
from vela import importqueue


def test_wording_keeps_its_citation():
    state = importqueue.new_state("s")
    importqueue.set_wording(state, importqueue.KEEP, "^c07", cite="[[s]] 2.c07")
    assert importqueue.wording_for(state, ["SRC-01"]) == (importqueue.KEEP, "^c07", "[[s]] 2.c07")
