---
id: capability-delta
type: initiative-section
title: Capability delta
initiative: INI-002
arc42: "§4"
c4: landscape
state: decided
owner: "@hl-solution-lead"
authored: mixed
sources: ["session 2026-07-14 Shape", "session 2026-08-12 Grill", "session 2026-11-18 Grill"]
---

# Capability delta

- **Decision:** [[2026-08-12-goals-and-data]]

Every capability this initiative changes, which software provides it before and after, and where the work lands. Anything not listed is unchanged.

Each capability page holds the change, what provides it today and after, its flows and its epics.

<!-- generated:capability-map sha=0503da3c: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

```mermaid
flowchart TB
  subgraph d_booking["Booking"]
    c_CAP_013["CAP-013 Reserve a crossing (replace)"]
    c_CAP_014["CAP-014 Hold a seat during payment (new)"]
    c_CAP_021["CAP-021 Amend or cancel a booking (extend)"]
    c_CAP_023["CAP-023 Fix failed bookings by hand (retire)"]
  end
  subgraph d_customer_contact["Customer contact"]
    c_CAP_022["CAP-022 Notify customer of changes (new)"]
  end
  subgraph d_payments["Payments"]
    c_CAP_015["CAP-015 Take payment (unchanged)"]
  end
  subgraph d_sales["Sales"]
    c_CAP_011["CAP-011 Find a crossing (unchanged)"]
    c_CAP_012["CAP-012 Quote a fare (narrow)"]
  end
  classDef changed fill:#fdf0d5,stroke:#a06400,color:#3a2600
  classDef new fill:#d9f2e3,stroke:#1e7a46,color:#10301d
  classDef retired fill:#f6e0de,stroke:#b3261e,color:#3a0d0a,stroke-dasharray:4 3
  classDef unchanged fill:#eef1f5,stroke:#7a8494,color:#19212d
  class c_CAP_012,c_CAP_013,c_CAP_021 changed
  class c_CAP_014,c_CAP_022 new
  class c_CAP_023 retired
  class c_CAP_011,c_CAP_015 unchanged
```

Key: green: new in this initiative · amber: changed by this initiative · gray: stays as it is · red, dashed: retired by this initiative.
<!-- /generated:capability-map -->

- [[CAP-013-reserve-a-crossing|Reserve a crossing]]
- [[CAP-014-hold-a-seat|Hold a seat during payment]]
- [[CAP-021-amend-or-cancel|Amend or cancel a booking]]
- [[CAP-022-notify-customer|Notify customer of changes]]
- [[CAP-012-quote-a-fare|Quote a fare]]
- [[CAP-023-fix-failed-bookings|Fix failed bookings by hand]]

## Notes on the trickier rows

**Hold a seat during payment.** Ten minutes came from Tidepay's own session timeout, which is nine. A hold that outlives the payment page by a minute covers slow webhooks without blocking the seat for long. It was an assumption until the Grill on 2026-08-12, when the Head of Contact Center confirmed that ten minutes matches what agents already do by hand.

**Fix failed bookings by hand.** Retiring a capability is a promise that nobody will need it. Booking makes that promise by retrying the ledger write and keeping the hold, so the failure the call center used to clean up can no longer reach a customer. If it does, it shows up in the hold expiry rate on [[concern-observability|Observability]] long before anyone phones.

**Reserve a crossing.** INI-004 Loyalty Revamp also touches this capability, because points are earned at reservation. Loyalty Revamp will consume Booking's state-changed event rather than adding a fourth caller.

## Capabilities checked and left alone

[[CAP-011-find-a-crossing|Find a crossing]] and [[CAP-015-take-payment|Take payment]] are in the flows but don't change. Take payment now reports its outcome to Booking instead of to each channel; Tidepay itself is untouched.

## Allocation

What each app carries of each functional requirement.

<!-- generated:allocation sha=8c6debdc: do not edit, run vela render -->
_Kept up to date by vela from the pages it reads._

**Who does what:** no requirement is firm enough to split between the apps yet.
<!-- /generated:allocation -->
