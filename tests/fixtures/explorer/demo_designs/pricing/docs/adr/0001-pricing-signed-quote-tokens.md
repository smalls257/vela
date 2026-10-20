# ADR-0001: Quotes are signed tokens, not stored rows

**Status:** accepted
**Date:** 2026-11-25
**Slug:** pricing

## Context
A quoted fare must hold for as long as Booking holds the seat (CAP-012.FR1), but Pricing has no store of its own for
quotes and the Fare rules store is the Revenue team's.

## Decision
The Quote API returns a quote token signed with a key from the Platform key service. Booking keeps the token and
Pricing verifies it on request; nothing about a quote is stored.

## Alternatives considered
- **A quotes table in the Fare rules store** — adds writes to a store that has only ever been read, owned by another team.
- **Booking caches the fare** — Booking could not prove the fare was Pricing's.

## Consequences
- **Positive:** no new store; a quote can be checked by anyone with the public key.
- **Negative:** a key rotation must keep the old key for the longest hold lifetime.
- **Reversibility cost:** medium; Booking would have to stop sending tokens.
