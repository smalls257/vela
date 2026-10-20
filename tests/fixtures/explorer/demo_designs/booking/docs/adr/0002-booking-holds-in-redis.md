# ADR-0002: Holds live in Redis with a TTL

**Status:** accepted
**Date:** 2026-11-21
**Slug:** booking

## Context
A hold must end by itself when its lifetime runs out (CAP-014.FR2), and the lifetime itself is disputed (OQ-001).

## Decision
Hold keeper stores each hold as a Redis key with a TTL equal to the configured lifetime, and listens for expiry to
write a release to the outbox.

## Alternatives considered
- **A sweeper over a Postgres holds table** — works, but a missed sweep keeps seats off sale, and the sweep load grows with traffic.

## Consequences
- **Positive:** changing the lifetime is configuration, so OQ-001 cannot force a redesign.
- **Negative:** Redis keyspace notifications are best effort; a nightly reconcile compares Redis with Postgres.
- **Reversibility cost:** low; holds live for minutes, so a move back to Postgres needs no migration.
