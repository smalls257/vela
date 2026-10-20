# ADR-0001: The consumer runs inside the Message sender's deployment

**Status:** proposed
**Date:** 2026-11-27
**Slug:** notifications

## Context
The Message sender already looks up a customer's address from the customer ID and holds the email and SMS provider
credentials.

## Decision
The Booking event consumer is a second process in the Message sender's deployment, sharing its configuration and
credentials.

## Alternatives considered
- **A separate service** — a second set of provider credentials to rotate, for a consumer that only hands messages on.

## Consequences
- **Positive:** one deployment, one set of credentials.
- **Negative:** a bad consumer release redeploys the sender too.
- **Reversibility cost:** low; the consumer has no state of its own.
