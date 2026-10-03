---
id: capability-delta
type: initiative-section
title: Capability delta
initiative: INI-002
arc42: "§4"
c4: landscape
state: decided
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-07-14 Shape", "session 2026-08-12 Grill", "session 2026-11-18 Grill"]
---

# Capability delta

- **Decision:** [[2026-08-12-goals-and-data]]

Every capability this initiative changes, which software provides it before and after, and where the work lands. Anything not listed is unchanged.

Each capability page holds the change, what provides it today and after, its flows and its epics.

- [[CAP-013-reserve-a-crossing|Reserve a crossing]]
- [[CAP-014-hold-a-seat|Hold a seat during payment]]
- [[CAP-021-amend-or-cancel|Amend or cancel a booking]]
- [[CAP-022-notify-customer|Notify customer of changes]]
- [[CAP-012-quote-a-fare|Quote a fare]]
- [[CAP-023-fix-failed-bookings|Fix failed bookings by hand]]

## Notes on the trickier rows

**Hold a seat during payment.** Ten minutes came from Tidepay's own session timeout, which is nine. A hold that outlives the payment page by a minute covers slow webhooks without blocking the seat for long. It was an assumption until the Grill on 2026-08-12, when the Head of Contact Centre confirmed that ten minutes matches what agents already do by hand.

**Fix failed bookings by hand.** Retiring a capability is a promise that nobody will need it. Booking makes that promise by retrying the ledger write and keeping the hold, so the failure the call centre used to clean up can no longer reach a customer. If it does, it shows up in the hold expiry rate on [[concern-observability|Observability]] long before anyone phones.

**Reserve a crossing.** INI-004 Loyalty Revamp also touches this capability, because points are earned at reservation. INI-004 will consume Booking's state-changed event rather than adding a fourth caller.

## Capabilities checked and left alone

[[CAP-011-find-a-crossing|Find a crossing]] and [[CAP-015-take-payment|Take payment]] are in the flows but don't change. Take payment now reports its outcome to Booking instead of to each channel; Tidepay itself is untouched.
