"""Flow pages with more than one way in, for the Flows view's starts, pin and fold checks. They are written into a copy of
examples/unified-booking (the example itself stays as it is): FLO-010 names its two starts in an opening alt, FLO-011 has
the same steps and no alt, FLO-012 has one way in, FLO-013 has two ways in that no step says who sends.

    from starts_flows import add_flows
"""

HEAD = """---
id: {id}
type: flow
title: {title}
state: assumption
owner: "@hl-solution-lead"
authored: authored
---

# {title}

{lead}

## Steps

"""

WEB = "[[website-building-blocks|Public website]]"
DESK = "[[call-center-building-blocks|Call center desktop]]"
BOOKING = "[[booking-building-blocks|Booking]]"
PRICING = "[[pricing-building-blocks|Pricing]]"
NOTIFY = "[[notifications-building-blocks|Notifications]]"
HOLD = "[[booking-building-blocks#CON-001 Booking API|Booking API]]"
FARE = "[[pricing-building-blocks#CON-003 Quote a fare|Quote a fare]]"
SCHEDULE = "[[vessel-schedule-building-blocks|Vessel schedule]]"
TIDEPAY = "Tidepay"
CAPACITY = "[[vessel-schedule-building-blocks#CON-004 Capacity check|Capacity check]]"
PAID = "[[booking-building-blocks#CON-007 Tidepay payment outcome|Tidepay payment outcome]]"
STATE = "[[booking-building-blocks#CON-002 Booking state changed|Booking state changed]]"

TWO_WAYS = f"""1. A customer picks a sailing on the {WEB}.
2. {WEB} → {BOOKING}: asks to hold a seat, over {HOLD}.
3. An agent on the {DESK} takes the caller's sailing.
4. {DESK} → {BOOKING}: asks to hold a seat, over {HOLD}.
5. {BOOKING} → {PRICING}: asks for the fare, over {FARE}.
6. {PRICING} → {BOOKING}: gets the fare back, over {FARE}.
7. {BOOKING} → {NOTIFY}: tells it the seat is held, over {STATE}.
"""

ALT = """
```mermaid
sequenceDiagram
    participant W as Public website
    participant D as Call center desktop
    participant B as Booking
    participant P as Pricing
    alt A customer books on the website
        W->>B: CON-001 hold a seat
    else A customer calls in
        D->>B: CON-001 hold a seat
    end
    B->>P: CON-003 quote the fare
```
"""

ONE_WAY = f"""1. A customer picks a sailing on the {WEB}.
2. {WEB} → {BOOKING}: asks to hold a seat, over {HOLD}.
3. {BOOKING} → {PRICING}: asks for the fare, over {FARE}.
4. {PRICING} → {BOOKING}: gets the fare back, over {FARE}.
"""

# no sender named: a request goes from its consumer to its provider, and only the lane the step names is a consumer here, so the
# direction is a guess
UNSAID = f"""1. The customer holds a seat on the {WEB}, over {HOLD}.
2. An agent holds a seat on the {DESK}, over {HOLD}.
3. {BOOKING} → {NOTIFY}: tells it the seat is held, over {STATE}.
"""

PAGES = {
    "FLO-010-book-two-ways.md": (HEAD.format(id="FLO-010", title="Book a seat two ways", lead="A seat is held from the website or from a phone call.") + TWO_WAYS + ALT),
    "FLO-011-book-two-ways-no-alt.md": (HEAD.format(id="FLO-011", title="Book a seat two ways, no alt", lead="The same steps with no diagram.") + TWO_WAYS),
    "FLO-012-book-one-way.md": (HEAD.format(id="FLO-012", title="Book a seat one way", lead="Only the website holds a seat.") + ONE_WAY),
    "FLO-013-two-reports-sender-unsaid.md": (HEAD.format(id="FLO-013", title="Two channels hold a seat, sender unsaid", lead="The steps never say who sends.") + UNSAID),
}


def add_flows(vault, names=None):
    """Writes the flow pages into vault/06-runtime/flows (all of them, or the named files)."""
    folder = vault / "06-runtime" / "flows"
    for name, text in PAGES.items():
        if names is None or name in names:
            (folder / name).write_text(text, encoding="utf-8")
