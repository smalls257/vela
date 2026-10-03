---
id: constraints
type: initiative-section
title: What we can't change
initiative: INI-002
arc42: "§2"
state: fact
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-07-09 Discover", SRC-02, SRC-03]
---

# What we can't change

These came to us. Every design choice in this initiative has to live inside them.

| ID | Constraint | Where it comes from | What it forces |
|---|---|---|---|
| CST-1 | FERRYMASTER cannot be changed | Vendor contract runs to 2028; two people understand the COBOL | Booking works around the mainframe, never inside it. See [[ADR-0002-ferrymaster-ledger-of-record\|ADR-0002]] and [[ADR-0004-mq-not-screen-scraping\|ADR-0004]]. |
| CST-2 | Payment stays with Tidepay, and PCI scope must not grow | Security and the existing Tidepay contract | Card data never enters Booking. Tidepay reports the outcome by webhook. |
| CST-3 | Kiosks change only twice a year, in March and September | Locked-down kiosk image managed by Port Systems | Anything kiosks call must stay stable for at least six months. See [[ADR-0003-versioned-booking-api\|ADR-0003]]. |
| CST-4 | Every new application publishes events to the Harbourline event bus | Transformation programme standard | Booking publishes state changes; Notifications consumes them. |
| CST-5 | Mainframe processing stays inside the existing MIPS budget | Finance, via the mainframe team lead | We checked the MQ transaction volume before choosing it. See [[concern-cost\|Cost]]. |

CST-1 and CST-3 shaped the plan more than anything else. CST-1 is why Booking holds state but never owns the truth. CST-3 is why the kiosks are the last channel to move, and why the old Booking API version has to outlive at least one image cycle.
