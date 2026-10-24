# Handoff record: Booking

- **App:** APP-booking
- **Commit:** example
- **Written:** 2026-11-20
- **Items:** 21

Made by `vela handoff APP-booking`; don't edit it by hand. To see what changed since the app's team accepted it, run `vela handoff verify APP-booking`. The Hash column is a fingerprint of each item's text, used to spot changes.

| ID | Kind | Page | State | Hash |
|---|---|---|---|---|
| APP-booking | app | 05-building-blocks/booking-building-blocks.md | decided | ce640b2a5171 |
| RUN-booking | runtime | 06-runtime/apps/booking-runtime.md | decided | 5811578d3af2 |
| CON-001 | provides | 05-building-blocks/booking-building-blocks.md | decided | 0ff1c634d33e |
| CON-002 | provides | 05-building-blocks/booking-building-blocks.md | decided | c802cfa780e6 |
| CON-003 | consumes | 05-building-blocks/pricing-building-blocks.md | decided | a8768b661c22 |
| CON-004 | consumes | 05-building-blocks/vessel-schedule-building-blocks.md | fact | b79b583063a9 |
| CON-005 | consumes | 05-building-blocks/customer-identity-building-blocks.md | fact | 4440f710ad85 |
| CON-006 | consumes | 05-building-blocks/ferrymaster-building-blocks.md | fact | ca63bf290f42 |
| CON-007 | consumes | 05-building-blocks/booking-building-blocks.md | fact | 1e31b72f0319 |
| EPC-031 | epic | 13-epics/EPC-031-holds-and-confirms.md | decided | 168e90b1957c |
| EPC-032 | epic | 13-epics/EPC-032-ledger-adapter.md | decided | d19b3d8db69a |
| EPC-033 | epic | 13-epics/EPC-033-website-to-booking.md | decided | 8e185aa86aa3 |
| EPC-034 | epic | 13-epics/EPC-034-call-center-to-booking.md | decided | 2a25355074ab |
| EPC-035 | epic | 13-epics/EPC-035-kiosks-to-booking.md | decided | 8d5d4cd18feb |
| EPC-036 | epic | 13-epics/EPC-036-amend-cancel-online.md | decided | 7860d541ca93 |
| EPC-037 | epic | 13-epics/EPC-037-events-and-notifications.md | decided | b369fae92a31 |
| EPC-038 | epic | 13-epics/EPC-038-pricing-serves-booking.md | decided | e9d139538092 |
| EPC-039 | epic | 13-epics/EPC-039-run-booking.md | decided | 7cd21cad2663 |
| SLC-001 | slice | slices/SLC-001-website-books-through-booking.md | - | b3017b4def47 |
| SLC-002 | slice | slices/SLC-002-call-center-moves-to-booking.md | - | 5ec665e7c8a2 |
| SLC-003 | slice | slices/SLC-003-kiosks-book-in-the-march-image.md | - | ff9fec219740 |

## Flow checks when written

Where each slice's flow check stood, as recorded by vela check-slice:

- SLC-001 A customer books on the website through Booking: Nobody has run the flow check on it yet.
- SLC-002 The call center books, amends and cancels through Booking: Nobody has run the flow check on it yet.
- SLC-003 Kiosks book through Booking in the March image: Nobody has run the flow check on it yet.
