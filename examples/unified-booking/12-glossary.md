---
id: glossary
type: initiative-section
title: Glossary
initiative: INI-002
arc42: "§12"
state: decided
owner: "@hl-solution-lead"
authored: authored
sources: ["sessions 2026-07-06 to 2026-11-18"]
---

# Glossary

- **Decision:** [[2026-11-18-epics]]

**Booking.** The new application that decides a booking's state. Not to be confused with a booking, the thing a customer has.

**Booking reference.** The six-character code a customer sees. FERRYMASTER issues it; Booking never makes one up.

**Hold.** A seat reserved but not yet paid for. Released automatically after ten minutes.

**Confirmed.** Paid for and written to the ledger. The only state a customer should ever be told is final.

**Confirming.** Paid for, ledger write still in progress or being retried. What the customer and the call centre both see while Booking retries.

**Ledger.** FERRYMASTER, for as long as the Mainframe Exit initiative hasn't replaced it. The record of what has been sold.

**Ledger transactions.** FERRYMASTER's existing MQ transactions: BKHOLD, BKCONF, BKAMND and BKCANC. See [[ferrymaster-building-blocks#CON-006 Ledger transactions|Ledger transactions]].

**Channel.** A front end customers or agents use to book: the public website, the call centre desktop, or a port kiosk.

**Adapter (old).** The screen-scraping code each channel used to talk to FERRYMASTER. Every one is retired by this initiative.

**Image cycle.** The kiosk software release, twice a year in March and September. Nothing on a kiosk changes in between.
