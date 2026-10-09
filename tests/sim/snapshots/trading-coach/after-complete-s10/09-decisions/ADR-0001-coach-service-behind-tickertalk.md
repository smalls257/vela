---
id: ADR-0001
type: decision
title: Coach service behind TickerTalk
state: decided
owner: "@sim-lead"
authored: authored
sources: [SRC-12, SRC-16, 2026-10-09-first-instruments, 2026-10-09-first-release-apps]
---

# Coach service behind TickerTalk

## Context

TickerTalk is the news app readers already use, and the product lead wants it to stay the news app. The coach needs lessons, a stock list, paper trades and delayed prices, and a January demo is the date that forces the shape. The first release is paper only, with no real orders.

## Decision

The coach runs as a new service, [[coach-building-blocks|Coach]], that sits behind [[tickertalk-building-blocks|TickerTalk]]. TickerTalk gains the coach screens, sends Coach an opaque reader ID for each reader who has opted in, and sends nothing else of its own data. TickerTalk shows Coach's copy exactly as Coach sends it, and hides the coach whenever Coach cannot be reached or the release switch is off.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Coach inside TickerTalk | the product lead says the news app stays the news app |
| Coach plus a paper-trading gateway | two new services for a January demo, and a seam that only pays off once real orders exist |

## Consequences

The mobile team builds the coach screens and the identity send, and a Coach team builds and runs the new service. Both sides own a contract test for the reader identity contract. Three answers from the mobile lead are still open for 14 October: whether the reader ID stays stable, whether the opt-in check fits mobile's plan, and who covers TickerTalk out of hours. The decision stands on the product lead's override of those open unknowns.

## History

- **Decision:** [[2026-10-09-tickertalk-reader-identity]]
