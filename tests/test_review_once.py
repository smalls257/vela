"""Below large, the second review checkpoint in a session skips every area, with the reason; --rerun still runs."""
import session_files
from test_review_prepare import RECORD_ID, packets, prepare, started
from vela import reviewprep, sizing

FIRST = "## Reviews\n\n### 1. after the boundary (2026-10-23)\n"


def at(band):
    return sizing.Sizing(band=band, measured=band, shape=band, signals=(), chosen=None, recorded="", kept_said="")


def test_the_first_checkpoint_is_always_due():
    assert reviewprep.session_skip("## Captures\n", at("small")) == ""


def test_a_second_one_is_skipped_below_large_and_due_at_large():
    assert reviewprep.session_skip(FIRST, at("medium")) == reviewprep.ONE_PER_SESSION
    assert reviewprep.session_skip(FIRST, at("large")) == ""


def test_prepare_lists_every_area_skipped_on_the_second_checkpoint(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)  # the mini vault: two apps, small
    assert prepare(vault, "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md")[0] == 0
    code, answer = prepare(vault, "--checkpoint", "after the boundary", "--focus", "01-goals.md")
    assert code == 0 and answer["packets"] == []
    assert {s["reason"] for s in answer["skipped"]} == {reviewprep.ONE_PER_SESSION}


def test_rerun_runs_an_area_anyway(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    prepare(vault, "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md")
    # the skill writes the checkpoint's heading once its findings are merged; --rerun names that checkpoint
    notes = session_files.record_text(vault, RECORD_ID)
    session_files.write_private(vault, RECORD_ID, notes.rstrip("\n") + "\n\n" + FIRST)
    code, answer = prepare(vault, "--checkpoint", "again", "--focus", "01-goals.md", "--rerun", "1", "--areas", "FIN")
    assert code == 0 and sorted(packets(answer)) == ["FIN"]
