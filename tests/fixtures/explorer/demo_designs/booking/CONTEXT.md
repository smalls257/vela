# Project Context

> Domain glossary and shared mental model. Update when a term gets resolved or
> reframed.

## Glossary

### Hold
**Definition:** a seat kept for one customer while they pay, for the hold lifetime.
**Not to be confused with:** a reservation in FERRYMASTER, which is the ledger's own BKHOLD.
**Examples:** a website customer on Tidepay's page.

### Confirming
**Definition:** paid, but not yet accepted by the ledger of record. Channels show it as "confirming".
**Not to be confused with:** confirmed, which only FERRYMASTER's acceptance gives.
**Examples:** a BKCONF that timed out and is being retried.

## Boundaries

**This project owns:** booking state, holds, the outbox, the Booking API.
**This project consumes:** fares, capacity, customer records, payments, the ledger.
**This project does not concern itself with:** fare rules, card data, channel user interfaces.

## Conventions

- States are lower case in the API and in events: `held`, `confirming`, `confirmed`.
