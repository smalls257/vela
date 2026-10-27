# The build plan file

`docs/plan/<slug>-breakdown.md`. The explorer's Build plan, `vela tickets` and `/vela:tickets` all read it with one reader (`vela/breakdown.py`), so a line it cannot place is reported, never guessed. Write the lines as shown.

## Frontmatter

```yaml
---
slug: rider-app
status: in-progress | complete | complete-with-gaps
vault:
  app: APP-rider-app              # which app of the vault the plan is for; tickets checks against it
  initiative: INI-001
deferred: []
gaps:                             # plan gaps are PG-nnn, never the design's G-nnn
  - id: PG-001
    what: "EPC-035.AC1 to AC5 have no story to build: S-11 is deferred"
    acknowledged_by: team lead
    why: "..."
    revisit: "..."
last_session: 2026-10-12T00:00:00Z
prereqs:
  - path: docs/tech-design/rider-app.md
    expected_status: complete-with-gaps
---
```

`complete-with-gaps` needs a `gaps[]` entry for each target left uncovered and each audit finding the person accepted. A gap's `what` names the target's ID (or its epic, as in "EPC-035.AC1 to AC5") so the tickets check can tell an accepted gap from a missed one.

## Body, in this order

1. A title, then an opening of two or three sentences: what the plan covers, what it rests on, what the sizes mean, and the audit line: "Checked against the design self-check on October 12; see the audit file beside this plan."
2. `## Summary`: a table `| Story | Traces to | Size total | Blocked by |`, one row per story, deferred and merged ones too. Size total is a count: `3 M, 2 S`. A deferred or merged story says `not planned`. The row may shorten a run (`EPC-032.AC1-4`) but names no target the story section lacks.
3. `## Stories`: one `### S-NN <name>` section per story, in the shape below.
4. `## Build order`: a numbered list, `1. S-01 (tracer): why it sits here`, tracer stories first. Stories not built are named in a closing line.
5. `## Critical path` (optional), `## Ticket waves` (which tickets to create now and which to hold).
6. `## Coverage`: a table `| Target | Stories |`, one row per trace target (one ID per row, `EPC-032.AC1`, not `AC1 to AC4`), then one row per design component. An empty Stories cell fails the plan, unless a `PG-nnn` accepts it.
7. `## Not planned`: each gap, deferral or open question the plan does not cover, with its ID and why.

## A story

```markdown
### S-02 Unlock a bike, with the payment checked
- **Tracer:** yes
Summary: When a rider scans a dock, the Rider app checks their payment before it asks the dock to unlock the bike. The rider picks the card on file or a new card, and can't unlock without one. The app records which check it used, and a check the payment service doesn't confirm counts as declined, so the bike stays locked. This is the rider's part of the tracer, and it comes after the store.
Traces to: CAP-005.FR1@APP-rider-app, CON-003, CON-004, EPC-032.AC1, EPC-032.AC2
Components: PaymentGate, UnlockRequester, TripView
Slice: tracer
Done when: a rider who scans a dock has the payment checked, and a payment that is not confirmed leaves the bike locked.
Acceptance criteria:
- When a rider scans a dock, the app checks their card before it asks for the unlock, and records which check it used.
- When a rider scans a dock, they are offered the card on file or a new card as two separate choices, and cannot unlock without one.
- A check not confirmed by the payment service counts as declined (design, Failure behavior).
Ticket criteria (from 0cf812):
Paying before the unlock:
- Scanning a dock offers the card on file or a new card, and the bike unlocks only with one of them. (covers AC2)
- The app checks the card before it asks for the unlock, and records which check it used. (covers AC1)
When the check doesn't go through:
- If the payment service doesn't confirm the check, it counts as declined and the bike stays locked. (covers AC3)

| Task | Size | Component |
|---|---|---|
| `Approval` type constructible only inside the module, and the Card check | S | PaymentGate |
| Durable outbox with confirmed and unconfirmed state | M | UnlockRequester |

Blocked by: S-01 (store). The wording shown when the payment service is down waits on OQ-005; until then the app shows nothing and logs.
Release fit: cannot tell for 2027-02-02. Sizes add to at most 14 days for one engineer, and the design names two app engineers but not how many days each has before 2027-02-02.
```

- `Traces to:` holds IDs only, one per target, each from the vault (`CAP-nnn.FRn@APP-x`, `CON-nnn`, `EPC-nnn.ACn`, `CST-nnn`). A story that rests on the design alone says `design only:` and names the design section. The quoted criteria come first, in the order of the IDs; criteria from the design or the team follow, written as the design states them.
- `- **Tracer:** yes` marks the team's tracer story; `Slice:` starts with `tracer`, `vertical` or `layer`, then any reason. A layer is flagged and folded into the slice that needs it, or says why it stays apart.
- The vault slice a story is part of goes on the same line, by ID: `Slice: vertical, SLC-002 A pilot rider returns a bike`. `vela tickets check` flags an ID the vault has no slice page for, or a slice this app takes part in nowhere; a story naming the tracer slice counts as a tracer story. Tickets come out grouped by it, the tracer first.
- `Release fit:` starts with the release date from `04b-releases.md` when the story's requirements are on a release, and says `cannot tell` with the missing number, or a rough sum "from your numbers". A story on no release names no date.
- `Blocked by:` is `none` (with an optional note after it), or story IDs, design questions (`OQ-nnn`), deferrals (`D-nnn`), vault unknowns (`UNK-nnn`) and outside parties.
- `Status:` is absent for a story that will be built. `Status: deferred (date). reason` keeps every other field, with tasks when they were sized. `Status: held` keeps tasks and appears in Ticket waves. `Status: merged into S-05 on <date>. reason` is the whole section of a story folded into another; its ID is retired, not reused. A split story is `S-07a` and `S-07b`, each with its own fields, in the summary and the order.
- `Summary:` is one line of 4 or 5 plain sentences, written through `house-voice`: what the story delivers, for whom, and where it fits (its slice, what comes before it). It has no IDs; vela adds them as suffixes and labels.
- `Ticket criteria (from <stamp>):` is the ticket's copy of the acceptance criteria. It has short headings, each ending in a colon, with bullets under them. Merge criteria that overlap, split one that says two things, and reword them in the house voice, with no IDs. Each bullet ends `(covers AC1, AC3)`: ACn is the nth bullet under `Acceptance criteria:`, counted from 1, and every criterion is covered at least once. The acceptance criteria above it stay word for word; only this copy is reworded.
- `vela tickets check` prints the stamp to write. The stamp changes whenever an acceptance criterion changes, and the check then flags the copy as out of date: rewrite the lines, then write the new stamp.
- A story with no ticket copy still gets a ticket, with its criteria as a flat list, and the check flags it.
- When `Blocked by:` names an open question (`OQ-nnn`, `UNK-nnn`), the same sentence says what the story does until then: "waits on OQ-005; until then the app shows nothing and logs". The ticket shows it under "Still open".
- A task row is three filled cells. Sizes are `S`, `M` or `L`.
- Keep prose under a story to the lines above, including the ticket copy. A free sentence the reader can't place is reported as unread.
