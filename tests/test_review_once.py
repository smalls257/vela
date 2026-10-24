"""Below large, the second review checkpoint in a session skips every area, with the reason; --rerun still runs."""
import session_files
from test_review_prepare import RECORD_ID, packets, prepare, started
from vela import questions, reviewprep, sizing

FIRST = "## Reviews\n\n### 1. after the boundary (2026-10-23)\n"


def at(band):
    return sizing.Sizing(band=band, measured=band, shape=band, signals=(), chosen=None, recorded="", kept_said="")


def test_the_first_checkpoint_is_always_due():
    assert not reviewprep.earlier_checkpoint_covers("## Captures\n", at("small"))


def test_an_earlier_one_covers_below_large_and_not_at_large():
    assert reviewprep.earlier_checkpoint_covers(FIRST, at("medium"))
    assert not reviewprep.earlier_checkpoint_covers(FIRST, at("large"))


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


def test_a_checkpoint_that_skipped_every_area_is_not_the_sessions_review(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    real = reviewprep.skip_reason
    monkeypatch.setattr(reviewprep, "skip_reason", lambda answer, close: reviewprep.NOTHING_OWED)
    code, first = prepare(vault, "--checkpoint", "after the discover", "--focus", "01-goals.md")
    assert code == 0 and first["packets"] == []
    monkeypatch.setattr(reviewprep, "skip_reason", real)
    code, second = prepare(vault, "--checkpoint", "after the boundary", "--focus", "01-goals.md")
    assert code == 0 and sorted(packets(second)) == ["DAT", "FIN", "OPS", "REG"], "the first reviewed nothing"


def test_a_new_copy_after_the_first_checkpoint_runs_its_area_again(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    assert prepare(vault, "--checkpoint", "after the pre-mortem", "--focus", "01-goals.md")[0] == 0
    real = questions.listing
    copy = {"pending": True, "subject_page": "05-building-blocks/supplier-building-blocks.md", "id": "Q-DAT-01@APP-supplier"}

    def with_a_supplier(vault, code, *a, **k):
        answer = real(vault, code, *a, **k)
        if code == "DAT":
            answer = {**answer, "copies": [*answer["copies"], copy]}
        return answer
    monkeypatch.setattr(questions, "listing", with_a_supplier)
    code, answer = prepare(vault, "--checkpoint", "after the boundary", "--focus", "01-goals.md")
    assert code == 0 and sorted(packets(answer)) == ["DAT"], "personal data to a new party is reviewed again"
    assert {s["reason"] for s in answer["skipped"]} == {reviewprep.ONE_PER_SESSION}, "the rest are unchanged"
