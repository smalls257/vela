"""The flow as colored characters: lanes, arrows, labels without the lane prefix, and widths counted by cell."""
import pytest

from companion_flow import STEPS
from vela import companionchart as chart

GOLDEN_60 = """\
╭Public w…╮ ╭ Booking ╮ ╭Call cen…╮ ╭Port kio…╮ ╭Notifica…╮
╰────┬────╯ ╰────┬────╯ ╰────┬────╯ ╰────┬────╯ ╰────┬────╯
     │asks to ho…│           │           │           │
     ├──────────▶│           │           │           │
     │           │           │           │           │
     │           │asks to ho…│           │           │
     │           │◀──────────┤           │           │
     │           │           │           │           │
     │           │asks to hold a seat, o…│           │
     │           │◀──────────────────────┤           │
     │           │           │           │           │
     │           ◆ 4. Hold the seat.     │           │
     │           │           │           │           │
     │           ◆ 5. Take payment.      │           │
     │           │           │           │           │
     │           ◆ 6. Confirm booking.   │           │
     │           │           │           │           │
     │           │publishes the state change, over B…│
     │           ├──────────────────────────────────▶│"""


def text(steps, columns):
    return chart.flatten(chart.drawing(steps, columns))


def wide(line):
    return chart.width_of(line)


def message(n, sender, receiver, words="does a thing."):
    return {"n": n, "from": sender, "to": receiver, "text": f"{sender} → {receiver}: {words} More words."}


def test_flo_001_at_60_columns_is_the_golden_drawing():
    assert "\n".join(text(STEPS, 60)) == GOLDEN_60


def test_a_label_drops_the_sender_receiver_prefix_that_the_step_text_carries():
    """E133: every label used to repeat the lanes."""
    for width in chart.WIDTHS:
        shown = "\n".join(text(STEPS, width))
        assert "→" not in shown and "Public website →" not in shown


def test_a_message_is_an_info_arrow_and_a_one_lane_step_is_a_strong_diamond():
    lines = chart.drawing(STEPS, 60)
    tones = {span["t"][:1]: span["tone"] for line in lines for span in line if span["t"][:1] in "├◆╭"}
    assert tones == {"├": "info", "◆": "strong", "╭": "dim"}


def test_a_leftward_arrow_points_left_and_ends_on_the_sender():
    assert any("│◀──────────┤" in line for line in text(STEPS, 60))


@pytest.mark.parametrize("columns", chart.WIDTHS)
def test_no_line_is_wider_than_the_columns_even_with_24_lanes_and_wide_characters(columns):
    steps = [message(n, f"App {n % 24} 日本語の名前", f"App {(n + 7) % 24} 😀") for n in range(1, 15)]
    steps.append({"n": 15, "from": "", "to": "", "text": "全角の文章がとても長い。" * 6})
    for sample in (steps, STEPS):
        assert all(wide(line) <= columns for line in text(sample, columns))


def test_24_lanes_at_48_columns_keep_the_most_connected_and_fold_the_rest_into_others():
    steps = [message(n, "Hub", f"Spoke {n}") for n in range(1, 13)]
    shown = text(steps, 48)
    assert shown[0].count("╭") == 4 and "others" in shown[0] and "Hub" in shown[0]
    assert chart.folded_lanes(steps, 48) == [f"Spoke {n}" for n in range(3, 13)]  # Hub and the first two spokes stay


def test_lanes_that_fit_are_not_folded():
    assert chart.folded_lanes(STEPS, 60) == [] and chart.folded_lanes(STEPS, 48) == ["Port kiosks", "Notifications"]


def test_more_than_twelve_steps_end_in_a_dim_count():
    steps = [message(n, "A", "B") for n in range(1, 16)]
    lines = chart.drawing(steps, 60)
    assert lines[-1] == [{"t": "+ 3 more steps", "tone": "dim"}]


def test_a_flow_with_one_lane_draws_its_steps_on_that_lane():
    steps = [{"n": 1, "from": "Booking", "to": "Booking", "text": "Booking → Booking: checks itself. Then more."},
             {"n": 2, "from": "", "to": "", "text": "Done."}]
    shown = text(steps, 48)
    assert shown[0].startswith("╭") and sum("◆" in line for line in shown) == 2


def test_a_flow_with_no_lanes_is_a_plain_list_of_steps():
    steps = [{"n": 1, "from": "", "to": "", "text": "[[CAP-1|Find a crossing]]. Then."}, {"n": 2, "from": "", "to": "", "text": "**Pay.**"}]
    assert text(steps, 48) == ["◆ 1. Find a crossing.", "◆ 2. Pay."]


def test_a_lane_name_longer_than_its_lane_is_cut_with_an_ellipsis_and_stays_in_its_box():
    steps = [message(1, "A very long application name indeed", "B")]
    top = text(steps, 48)[0]
    assert "…" in top and wide(top) <= 48


def test_markdown_and_wikilinks_in_a_step_read_as_plain_words():
    steps = [{"n": 1, "from": "", "to": "", "text": "**Hold** the [[CAP-014-hold-a-seat|seat]] with `BKHOLD`. After."}]
    assert text(steps, 48) == ["◆ 1. Hold the seat with BKHOLD."]


def test_the_drawing_is_deterministic_and_empty_for_no_steps():
    assert chart.drawing(STEPS, 72) == chart.drawing(STEPS, 72) and chart.drawing([], 60) == []
