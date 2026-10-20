---
type: work-breakdown
slug: booking
status: complete-with-gaps
prereqs:
  - docs/tech-design/booking.md
gaps:
  - id: GAP-1
    note: EPC-036.AC4 (an amendment that costs more) has no story; it needs Tidepay's extra-payment flow, which D-001 leaves for Booking API v2.
  - id: GAP-2
    note: S-04 builds the hold lifetime as configuration because OQ-001 (10 or 15 minutes) is still open.
---

# Booking work breakdown

Demo data, written by hand in the work-breakdown skill's format for the booking demo vault, not part of the example.

This plan covers the Booking service for the website cutover. Its inputs are `docs/tech-design/booking.md` at status
complete-with-gaps and the vault's allocated rows, contracts and epic criteria for APP-booking. Sizes are S (up to about
2 days), M (3 to 5 days) and L (1 to 2 weeks) for one engineer; they are for ordering, not commitments.

## Summary

| Story | Traces to | Size total | Blocked by |
|---|---|---|---|
| S-01 Confirm a booking over the website's surface | CAP-013.FR1@APP-booking, CAP-015.FR1@APP-booking, CON-001, EPC-031.AC5, EPC-031.AC6 | M+M+S | none |
| S-02 Read fares, capacity and customers | CAP-012.FR1@APP-booking, CON-003, CON-004, CON-005, EPC-038.AC1, EPC-038.AC2 | M+M+S | UNK-010, UNK-011 |
| S-03 Write confirmed bookings to FERRYMASTER | CON-006, EPC-031.AC2, EPC-031.AC3, EPC-032.AC1, EPC-032.AC2, EPC-032.AC3, EPC-032.AC4, EPC-032.AC5, EPC-032.AC6 | L+M+M+S | S-01, the mainframe team's test region |
| S-04 Hold a seat and release it when it runs out | CAP-014.FR1@APP-booking, CAP-014.FR2@APP-booking, EPC-031.AC1, EPC-031.AC4, EPC-037.AC2 | M+M | S-01, S-02, OQ-001 |
| S-05 Take Tidepay's payment outcome | CON-007, EPC-031.AC7 | M+S | S-01, S-03, UNK-009 |
| S-06 Book at the call center and the kiosks | CAP-013.FR2@APP-booking, CAP-013.FR3@APP-booking, EPC-033.AC3, EPC-034.AC2, EPC-034.AC3, EPC-034.AC5, EPC-035.AC1, EPC-035.AC3, EPC-035.AC5 | M+S+S | S-01, S-02 |
| S-07 Publish booking state changes | CON-002, CAP-022.FR1@APP-booking, EPC-037.AC1, EPC-037.AC4, EPC-037.AC5 | M+S | S-03 |
| S-08 Amend and cancel online | CAP-021.FR1@APP-booking, CAP-021.FR2@APP-booking, EPC-036.AC1, EPC-036.AC2, EPC-036.AC3 | L+M | S-03, S-07, D-001 |

### S-01 Confirm a booking over the website's surface

Traces to: CAP-013.FR1@APP-booking, CAP-015.FR1@APP-booking, CON-001, EPC-031.AC5, EPC-031.AC6; components: Booking API, Booking lifecycle

- The website shows a booking as confirmed only after the ledger has recorded it.
- A confirmation the ledger rejects shows as failed, never as confirmed.
- Two channels asking about the same booking reference at the same moment get the same state.
- A call to CON-001 without a valid service token is refused at the Platform gateway.

| Task | Size | Component |
|---|---|---|
| Booking state machine: held, confirming, confirmed, released | M | Booking lifecycle |
| Versioned HTTP surface for hold, confirm and get | M | Booking API |
| Error codes a channel can show a customer | S | Booking API |

Blocked by: none

### S-02 Read fares, capacity and customers

Traces to: CAP-012.FR1@APP-booking, CON-003, CON-004, CON-005, EPC-038.AC1, EPC-038.AC2; components: Upstream readers

- Booking's contract test for CON-003 passes against Pricing's provider verification, in both teams' pipelines.
- For the same crossing and fare rules, Booking gets the same quote the front ends get today.

| Task | Size | Component |
|---|---|---|
| Quote client with timeout and circuit breaker | M | Upstream readers |
| Capacity and customer lookup clients | M | Upstream readers |
| Contract tests against the three providers | S | Upstream readers |

Blocked by: UNK-010 (open question: capacity checks at the kiosk peak), UNK-011 (open question: guest bookings in the customer lookup)

### S-03 Write confirmed bookings to FERRYMASTER

Traces to: CON-006, EPC-031.AC2, EPC-031.AC3, EPC-032.AC1, EPC-032.AC2, EPC-032.AC3, EPC-032.AC4, EPC-032.AC5, EPC-032.AC6; components: Ledger adapter, Booking lifecycle

- Booking sends BKHOLD, BKCONF, BKAMND and BKCANC in the format CON-006 documents, and the FERRYMASTER test region accepts each one in the weekly end-to-end run.
- When FERRYMASTER rejects a write or does not answer, Booking retries and the booking keeps its hold. No channel sees `confirmed` until FERRYMASTER has accepted.
- The same write sent twice is applied once in FERRYMASTER.
- p95 ledger write latency in the weekly end-to-end run is no worse than the 2.1 s measured for UNK-001.
- Booking's contract tests run against the ledger simulator with no connection to FERRYMASTER.

| Task | Size | Component |
|---|---|---|
| Outbox table written in the same transaction as each state change | M | Booking lifecycle |
| MQ mapping for the four ledger transactions | L | Ledger adapter |
| Idempotency keys on every write | S | Ledger adapter |
| Ledger simulator for contract tests | M | Ledger adapter |

Blocked by: S-01, the mainframe team's test region slot for the weekly run (outside party)

### S-04 Hold a seat and release it when it runs out

Traces to: CAP-014.FR1@APP-booking, CAP-014.FR2@APP-booking, EPC-031.AC1, EPC-031.AC4, EPC-037.AC2; components: Hold keeper

Acceptance criteria:
- A channel that asks to hold a seat through CON-001 gets back a booking reference and an expiry time, and no other channel can sell that seat until the hold ends.
- A failed or abandoned payment releases the hold, and the seat is available to every channel again.
- A hold that isn't confirmed in time is released, and Booking publishes a state-changed event.

| Task | Size | Component |
|---|---|---|
| Redis holds with a TTL, lifetime read from configuration | M | Hold keeper |
| Extend a hold while its booking is confirming | M | Hold keeper |

Blocked by: S-01, S-02, OQ-001 (open question in the design: is a hold 10 minutes or 15?)

Open for `tech-design-grill`: whether a hold survives a restart of the Hold keeper. The design says only that holds live in Redis.

Conflict with an epic criterion: EPC-031.AC4 says a hold ends when payment fails; the design lets a hold run to its expiry. The story follows the design and the conflict goes upstream.

### S-05 Take Tidepay's payment outcome

Traces to: CON-007, EPC-031.AC7; components: Booking API

- No request or response on CON-001 or CON-007 carries card data.

| Task | Size | Component |
|---|---|---|
| Signed webhook endpoint answering 204 | M | Booking API |
| Log scrubber test for card data | S | Booking API |

Blocked by: S-01, S-03, UNK-009

### S-06 Book at the call center and the kiosks

Traces to: CAP-013.FR2@APP-booking, CAP-013.FR3@APP-booking, EPC-033.AC3, EPC-034.AC2, EPC-034.AC3, EPC-034.AC5, EPC-035.AC1, EPC-035.AC3, EPC-035.AC5; components: Booking API, Booking lifecycle

- An agent confirms a held crossing and reads the booking reference back to the caller.
- For any booking reference, the desktop shows the same state as the website and the kiosks.
- Booking API v1 answers kiosk requests unchanged for at least 6 months after the March 2027 image ships, whatever later versions add.
- The consumer-driven contract tests of the website, the desktop and the kiosks pass in Booking's provider verification.

| Task | Size | Component |
|---|---|---|
| Provider verification for the three channels' contract tests | M | Booking API |
| Keep v1 answering unchanged behind the version path | S | Booking API |
| Show an amendment's re-quoted fare before it is committed | S | Booking lifecycle |

Blocked by: S-01, S-02

### S-07 Publish booking state changes

Traces to: CON-002, CAP-022.FR1@APP-booking, EPC-037.AC1, EPC-037.AC4, EPC-037.AC5; components: Event publisher

- Every change of booking state produces one Booking state changed event on the bus, carrying the booking reference, the new state and the time of the change.
- An event carries the customer ID and no card data or other personal data.
- A change to the event schema that removes or renames a field fails Booking's pipeline.

| Task | Size | Component |
|---|---|---|
| Drain the outbox to the bus topic | M | Event publisher |
| Additive-only schema check in the pipeline | S | Event publisher |

Blocked by: S-03

### S-08 Amend and cancel online

Traces to: CAP-021.FR1@APP-booking, CAP-021.FR2@APP-booking, EPC-036.AC1, EPC-036.AC2, EPC-036.AC3; components: Booking lifecycle, Booking API

- A customer can change the date or time of a crossing on the website and sees the re-quoted fare before they accept it.
- A customer can cancel a booking on the website, and every channel shows it as `canceled` once FERRYMASTER has accepted the cancellation.
- A change that is not allowed is refused with a reason the channel can show the customer, and nothing reaches FERRYMASTER.

| Task | Size | Component |
|---|---|---|
| Amend and cancel transitions with the rules that refuse a change | L | Booking lifecycle |
| Amend and cancel on the HTTP surface | M | Booking API |

Blocked by: S-03, S-07, D-001 (deferred: Booking API v2 is designed when EPC-036 starts)

## Build order

1. S-01: every other story calls the lifecycle and the surface.
2. S-02: reading fares and capacity has no dependency on the others, and the holds need it.
3. S-03: confirm is not real until the ledger accepts it, and the outbox it builds feeds the events.
4. S-04: holds wait on the readers and on the answer to OQ-001, so they sit behind a configuration switch.
5. S-05: the webhook needs a ledger to confirm against.
6. S-06: the other channels cut over once the website's surface is steady.
7. S-07: events drain the same outbox as the ledger writes.
8. S-08: last, behind the Booking API v2 design.

## Coverage

| Target | Stories |
|---|---|
| CAP-012.FR1@APP-booking | S-02 |
| CAP-013.FR1@APP-booking | S-01 |
| CAP-013.FR2@APP-booking | S-06 |
| CAP-013.FR3@APP-booking | S-06 |
| CAP-014.FR1@APP-booking | S-04 |
| CAP-014.FR2@APP-booking | S-04 |
| CAP-015.FR1@APP-booking | S-01 |
| CAP-021.FR1@APP-booking | S-08 |
| CAP-021.FR2@APP-booking | S-08 |
| CAP-022.FR1@APP-booking | S-07 |
| CON-001 | S-01 |
| CON-002 | S-07 |
| CON-003 | S-02 |
| CON-004 | S-02 |
| CON-005 | S-02 |
| CON-006 | S-03 |
| CON-007 | S-05 |
| EPC-031.AC1 | S-04 |
| EPC-031.AC2 | S-03 |
| EPC-031.AC3 | S-03 |
| EPC-031.AC4 | S-04 |
| EPC-031.AC5 | S-01 |
| EPC-031.AC6 | S-01 |
| EPC-031.AC7 | S-05 |
| EPC-032.AC1 | S-03 |
| EPC-032.AC2 | S-03 |
| EPC-032.AC3 | S-03 |
| EPC-032.AC4 | S-03 |
| EPC-032.AC5 | S-03 |
| EPC-032.AC6 | S-03 |
| EPC-033.AC3 | S-06 |
| EPC-034.AC2 | S-06 |
| EPC-034.AC3 | S-06 |
| EPC-034.AC5 | S-06 |
| EPC-035.AC1 | S-06 |
| EPC-035.AC3 | S-06 |
| EPC-035.AC5 | S-06 |
| EPC-036.AC1 | S-08 |
| EPC-036.AC2 | S-08 |
| EPC-036.AC3 | S-08 |
| EPC-036.AC4 | |
| EPC-037.AC1 | S-07 |
| EPC-037.AC2 | S-04 |
| EPC-037.AC4 | S-07 |
| EPC-037.AC5 | S-07 |
| EPC-038.AC1 | S-02 |
| EPC-038.AC2 | S-02 |

| Component | Stories |
|---|---|
| Booking API | S-01, S-05, S-06, S-08 |
| Booking lifecycle | S-01, S-03, S-06, S-08 |
| Hold keeper | S-04 |
| Upstream readers | S-02 |
| Ledger adapter | S-03 |
| Event publisher | S-07 |

## Not planned

- GAP-1: EPC-036.AC4 has no story; Tidepay's extra-payment flow waits for Booking API v2 (D-001).
- D-001: Booking API v2 (amend with a vehicle change), designed when EPC-036 starts.
- G-002: other teams' criteria of EPC-033, EPC-034, EPC-035, EPC-037 and EPC-038; each owning team plans its own.
- G-003: EPC-039 and EPC-036.AC5 are met under Operations (on-call, dashboards, the monthly report), not by a story.
