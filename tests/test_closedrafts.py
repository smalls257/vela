"""`closedrafts.Drafts`: the drafts list holds paragraphs, never a read-back of what was decided."""
import dataclasses

from vela import closedrafts


def test_drafts_list_no_read_back_of_decided_items():
    assert "readback" not in {f.name for f in dataclasses.fields(closedrafts.Drafts)}
    assert not hasattr(closedrafts, "ReadBack") and not hasattr(closedrafts, "readback")
