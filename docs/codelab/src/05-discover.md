---
title: Discover or import
minutes: 20
summary: Read what already exists, and write down only what a source says
---
Pick one. If you have documents (a brief, a tenant note, a survey), run Discover. If an initiative is already under way in documents, code and tickets, run Import, which shows a map of what it found before writing anything.

::: type
Put the documents in the plan folder, then:

```
/vela:discover
```

or, for work already under way: `/vela:import`
:::

::: asks
Claude asks you to rank the documents, then reads back what it thinks exists, in groups of about five, naming each source and saying whether it describes today or a plan:

> 1. Partners get a nightly file of changed bookings (the partner guide, what runs today).
> 2. Guests can rebook on their phones by Q4 (the 2026 roadmap deck, a plan, so not decided yet).
>
> Do these hold?

If two lines disagree, it says so aloud and offers one open question naming both sides.
:::

::: see
Two Heron sources in the Library, one that exists today and one that is only intended:

```
| SRC-006 | Microsoft 365 tenant note | IT endpoint lead | 2026-10-02 | exists | document | ...
| SRC-007 | CIO brief on Heron | CIO | 2026-09-30 | intends | document | ...
```

They disagreed, and discover didn't pick a side:

```
- [unknown] (claude) The CIO brief says staff install the helper themselves, while the tenant note says staff cannot install software and everything is pushed from Intune or Jamf. Two sources disagree; the CIO and the IT endpoint lead are asked. → keep: UNK-086 (open) ^c06
```
:::

::: checkpoint
Every fact the session wrote cites a source in `sources.md`. A line from an `intends` source is an assumption, not a fact. Any clash is an open question with an owner.
:::

::: fold Why this step
Nobody designs anything before finding out what exists. A fact needs a source, and Claude's general knowledge is never a source: see [Discover and Import][m-discover] and [a fact needs a source][m-fact].
:::

::: fold Stuck?
- `E304` means a fact has no source. Add the source row to `sources.md`, or set the line back to an assumption.
- `E307` and `E309` mean a Library row has a bad type, or neither a stored file nor a location.
- Documents in `.inbox/` stay on your machine. Git ignores that folder, so company files aren't committed unless you agree to keep one.
:::
