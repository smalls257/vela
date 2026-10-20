# ADR-0001: A transactional outbox for ledger writes and events

**Status:** accepted
**Date:** 2026-11-21
**Slug:** booking

## Context
A booking may be reported `confirmed` only once FERRYMASTER has it (EPC-031.AC2), and every state change must be
published once (EPC-037.AC1). FERRYMASTER answers in about 2.1 s at p95 and sometimes not at all (UNK-001). Writing to
Postgres, MQ and Kafka in one request cannot be atomic.

## Decision
Booking lifecycle writes the new state and an outbox row in one Postgres transaction. The Ledger adapter and the Event
publisher each drain the outbox in order, with an idempotency key per row, and mark the row sent.

## Alternatives considered
- **Call FERRYMASTER inside the request** — a slow ledger holds a channel's HTTP call open for seconds, and a lost reply leaves the state unknown.
- **Two-phase commit across Postgres and MQ** — the MQ manager on the mainframe side does not take part in XA from outside.
- **Publish first, write the ledger from the event** — the event would say `confirmed` before the ledger has it.

## Consequences
- **Positive:** a crash between the write and the send loses nothing; retries are safe.
- **Negative:** a state change reaches FERRYMASTER and the bus after a short delay; outbox depth must be watched.
- **Reversibility cost:** high once channels rely on `confirming`; the state would have to disappear from CON-001.
