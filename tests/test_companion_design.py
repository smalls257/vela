"""The session companion on a design branch: the yes record, open questions, gaps and the next section."""
import json

import pytest

from companion_vault import SESSION, TODAY, git, grill_session, run_companion
from vela import privaterecord

DOC = """---
slug: booking
status: in-progress
last_session: 2026-10-24
gaps:
  - id: G-1
    what: Nobody has named who rotates the Tidepay key
---

# Tech Design — Booking

## Summary
Booking holds a seat, takes payment and confirms the crossing.

**Decisions that shape it:**
- Keep the hold in Booking
- Use the outbox for notifications

## Architecture overview
One service with a small outbox.

### Decisions
- Keep the hold in Booking
- Use the outbox for notifications
- Store prices in cents

## Open questions
### OQ-001: Who rotates the Tidepay key?
- **What we know:** Tidepay issues one key per merchant.
"""

RECORD_CAPTURES = ('- [decision] (@hl-booking-senior) "Yes, keep the hold in Booking" ^c01\n'
                   '- [decision] (@hl-booking-senior) "Yes, use the outbox for notifications" ^c02\n')


@pytest.fixture
def design(tmp_path):
    root = grill_session(tmp_path)
    (root / "sessions" / f"{SESSION}.md").unlink()
    (root / privaterecord.private_path(SESSION)).unlink()
    git(root, "checkout", "-q", "-b", "design/booking")
    (root / ".vela" / "design").mkdir(parents=True)
    record = privaterecord.new_private("booking", "Design: booking", TODAY, 1)
    (root / ".vela" / "design" / "booking.md").write_text(record.replace("## Captures\n", "## Captures\n\n" + RECORD_CAPTURES), encoding="utf-8")
    (root / "docs" / "tech-design").mkdir(parents=True)
    (root / "docs" / "tech-design" / "booking.md").write_text(DOC, encoding="utf-8")
    return root


def session_json(root):
    code, out = run_companion(root, "session", "--json")
    assert code == 0, out
    return json.loads(out)


def test_decided_holds_the_bullets_a_capture_names_and_not_the_third(design):
    got = session_json(design)
    assert [d["name"] for d in got["decided"]] == ["Keep the hold in Booking", "Use the outbox for notifications"]
    assert {d["label"] for d in got["decided"]} == {"decided today"}


def test_open_holds_the_question_and_the_gap_by_their_words(design):
    names = [o["name"] for o in session_json(design)["open"]]
    assert "Who rotates the Tidepay key?" in names and "Nobody has named who rotates the Tidepay key" in names


def test_next_is_the_first_template_section_not_yet_written(design):
    assert session_json(design)["next"] == {"text": "Context boundaries", "id": "", "source": "design order",
                                            "left_after": 13}


def test_the_session_is_named_for_the_app_and_the_summary_is_the_docs(design):
    got = session_json(design)
    assert got["session"]["title"] == "Design: Booking" and got["session"]["modes"] == ["design"]
    assert got["about"].startswith("Booking holds a seat")
    assert got["touched"] and got["touched"][0]["page"] == "docs/tech-design/booking.md"


def test_on_main_with_no_session_it_is_nothing_to_draw_as_before(tmp_path):
    root = grill_session(tmp_path)
    (root / "sessions" / f"{SESSION}.md").unlink()
    code, out = run_companion(root, "session", "--json")
    assert code == 1 and "No session is open in this folder." in out
