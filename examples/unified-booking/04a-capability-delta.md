---
id: capability-delta
type: initiative-section
title: Capability delta
initiative: INI-002
arc42: "§4"
c4: landscape
state: decided
owner: solution lead
authored: mixed
last_verified: 2026-11-20
sources: ["session 2026-07-14 Shape", "session 2026-08-12 Grill", "session 2026-11-18 Grill"]
---

# Capability delta

Every capability this initiative changes, which software provides it before and after, and where the work lands. Anything not listed is unchanged.

<!-- generated: do not edit -->
| Capability | Change | Provided by today | Provided by after | Flows | Epics | State |
|---|---|---|---|---|---|---|
| [[CAP-013-reserve-a-crossing\|Reserve a crossing]] | replace | Website, call centre and kiosks, each through its own FERRYMASTER adapter | [[booking-building-blocks\|Booking]] | [[FLO-001-hold-pay-confirm\|FLO-001]] | [[EPC-031-holds-and-confirms\|031]], [[EPC-033-website-to-booking\|033]], [[EPC-034-call-centre-to-booking\|034]], [[EPC-035-kiosks-to-booking\|035]] | decided |
| [[CAP-014-hold-a-seat\|Hold a seat during payment]] | new | Nothing; overbooking fixed by hand | Booking, 10-minute hold | [[FLO-001-hold-pay-confirm\|FLO-001]] | [[EPC-031-holds-and-confirms\|031]] | decided |
| [[CAP-021-amend-or-cancel\|Amend or cancel a booking]] | extend | Call centre only, through a mainframe screen | Booking, used by the website and call centre (kiosks show booking state only) | [[FLO-002-amend-or-cancel\|FLO-002]] | [[EPC-034-call-centre-to-booking\|034]], [[EPC-036-amend-cancel-online\|036]] | decided |
| [[CAP-022-notify-customer\|Notify customer of changes]] | new | Website emails only | [[notifications-building-blocks\|Notifications]], triggered by Booking events | [[FLO-003-notify-on-change\|FLO-003]] | [[EPC-037-events-and-notifications\|037]] | decided |
| [[CAP-012-quote-a-fare\|Quote a fare]] | narrow | [[pricing-building-blocks\|Pricing]], called by three front ends | Pricing, called by Booking only | [[FLO-001-hold-pay-confirm\|FLO-001]], [[FLO-002-amend-or-cancel\|FLO-002]] | [[EPC-038-pricing-serves-booking\|038]] | decided |
| [[CAP-023-fix-failed-bookings\|Fix failed bookings by hand]] | retire | Call centre, next-morning fixes | Nobody: Booking retries and keeps the hold | [[FLO-001-hold-pay-confirm\|FLO-001]] | [[EPC-031-holds-and-confirms\|031]], [[EPC-034-call-centre-to-booking\|034]] | decided |
<!-- /generated -->

## Notes on the trickier rows

**Hold a seat during payment.** Ten minutes came from Tidepay's own session timeout, which is nine. A hold that outlives the payment page by a minute covers slow webhooks without blocking the seat for long. It was an assumption until the Grill on 2026-08-12, when the Head of Contact Centre confirmed that ten minutes matches what agents already do by hand.

**Fix failed bookings by hand.** Retiring a capability is a promise that nobody will need it. Booking makes that promise by retrying the ledger write and keeping the hold, so the failure the call centre used to clean up can no longer reach a customer. If it does, it shows up in the hold expiry rate on [[concern-observability|Observability]] long before anyone phones.

**Reserve a crossing.** INI-004 Loyalty Revamp also touches this capability, because points are earned at reservation. INI-004 will consume Booking's state-changed event rather than adding a fourth caller.

## Capabilities checked and left alone

[[CAP-011-find-a-crossing|Find a crossing]] and [[CAP-015-take-payment|Take payment]] are in the flows but don't change. Take payment now reports its outcome to Booking instead of to each channel; Tidepay itself is untouched.
