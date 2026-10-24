"""Close drafts says whether a fresh reader should check the voice: from five paragraphs, or always from medium."""
import pytest

import sizing_vault
from test_close_drafts import drafts, drafts_json, resolve_till_rig, session
from vela import closedrafts, sizing


def at(band):
    return sizing.Sizing(band=band, measured=band, shape=band, signals=(), chosen=None, recorded="", kept_said="")


@pytest.mark.parametrize("band, paragraphs, due", [("small", 4, False), ("small", 5, True), ("medium", 4, True),
                                                   ("large", 1, True)])
def test_the_review_is_due_from_five_paragraphs_or_always_from_medium(band, paragraphs, due):
    assert closedrafts.voice_review(at(band), paragraphs)["due"] is due


def test_the_drafts_result_carries_the_verdict(tmp_path):
    vault = session(tmp_path)
    resolve_till_rig(vault)
    data = drafts_json(vault)
    assert data["voice_review"]["due"] is (data["count"] >= 5)
    assert data["voice_review"]["why"]


def test_a_short_close_tells_the_lead_it_was_read_back_not_sent_to_a_reviewer(tmp_path):
    vault = session(tmp_path)
    resolve_till_rig(vault)
    count = drafts_json(vault)["count"]
    assert 0 < count < 5, "the fixture drafts a few paragraphs"
    text = drafts(vault, "--for-lead")[1]
    assert "back to you with the rest instead of sending" in text and "to a reviewer" in text
    assert "I've read" not in text, "the read-back comes later, in the close, so it is not claimed as done"


def test_a_medium_plan_always_sends_the_drafts(tmp_path):
    vault = session(tmp_path)
    resolve_till_rig(vault)
    with (vault / ".vela.yaml").open("a", encoding="utf-8") as fh:
        fh.write(sizing_vault.choose("medium"))
    assert drafts_json(vault)["voice_review"]["due"] is True
    assert "to a reviewer" not in drafts(vault, "--for-lead")[1]
