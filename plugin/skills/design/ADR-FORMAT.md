# ADR format

Path: `docs/adr/NNNN-<slug>-<topic>.md`. NNNN is a four-digit counter that only goes up in this repository.

## When to write one

All three hold:

1. **Hard to reverse:** changing it later costs something real.
2. **Surprising without context:** a future reader will wonder why.
3. **A real trade-off:** there were genuine alternatives, and one was picked.

If one is missing, skip the ADR and keep the reasoning in the design doc. An ADR nobody needed is one more file to keep true.

## Template

~~~markdown
# ADR-NNNN: <Title>

**Status:** proposed | accepted | superseded by ADR-MMMM
**Date:** <ISO date>

## Context
<What forced this decision? Constraints in play.>

## Decision
<What we chose. One paragraph.>

## Alternatives considered
- **<Option A>**: why not.
- **<Option B>**: why not.

## Consequences
- **Positive:** <what becomes easier>
- **Negative:** <what becomes harder>
- **Reversibility cost:** <if we unwind this later, what does it cost?>
~~~

The design lists each ADR under `## ADRs` as a link, `[ADR-0001](../adr/0001-<slug>-<topic>.md)`. The vault numbers its own decisions the same way, so a team ADR is always linked, and a vault decision is cited with its initiative and commit, as `INI-002 ADR-0002 @ <sha>`.
