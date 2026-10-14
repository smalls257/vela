---
id: ADR-0003
type: decision
title: Version the Booking API and keep each version at least 6 months
initiative: INI-002
arc42: "§9"
state: decided
owner: "@hl-solution-lead"
authored: authored
sources: ["session 2026-08-26 Grill", SRC-03]
---

# ADR-0003 Version the Booking API and keep each version at least 6 months

- **Decision:** [[2026-08-26-kiosks-and-rollout]]

## Status

Accepted, 2026-08-26, in a Grill session with the Booking senior, Port Systems senior and QA lead.

## Context

Kiosks run a locked-down image that changes only twice a year. Whatever the kiosk app calls must stay stable for at least six months. The website releases weekly and the call center desktop monthly, so they can follow API changes quickly. The kiosks cannot.

## Decision

Version the Booking API ([[booking-building-blocks#CON-001 Booking API|Booking API]]). Booking supports each version for at least six months after the next one ships. Kiosks ship the v1 client in the March 2027 image. Booking's pipeline verifies the consumer contracts of every live version.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| One unversioned API with a promise of backward compatibility | Nothing would stop a breaking change reaching kiosks that cannot update for six months. |
| A separate API for kiosks | Two APIs would drift apart and kiosks would disagree with the other channels again (G2). |
| Three-month support window | Shorter than the kiosk image cycle. A slipped image would leave kiosks calling a retired version. |

## Consequences

- Booking carries at least two versions whenever it ships a breaking change, with tests for both.
- If the March 2027 image slips, v1 must stay up until the September image ([[11-unknowns-and-risks#R-02 The March 2027 kiosk image slips|The March 2027 kiosk image slips]]).
- The website and call center can move to a new version as soon as it ships.

## Assumptions it depends on

- Kiosks can authenticate to a versioned API without a user: [[11-unknowns-and-risks#UNK-004 Kiosk authentication|Kiosk authentication]], resolved with device certificates.

Delivered by [[EPC-031-holds-and-confirms|Booking holds and confirms crossings]] and [[EPC-035-kiosks-to-booking|Kiosks move to Booking in the March image]].

See [[concern-rollout|Rollout]] and [[concern-testing|Testing]].
