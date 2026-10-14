# The build plan file

`docs/plan/<slug>-breakdown.md`. The explorer's Build plan, `vela tickets` and `/vela:tickets` all read it with one reader (`vela/breakdown.py`), so a line it cannot place is reported, never guessed. Write the lines as shown.

## Frontmatter

```yaml
---
slug: desktop-agent
status: in-progress | complete | complete-with-gaps
vault:
  app: APP-desktop-agent          # which app of the vault the plan is for; tickets checks against it
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
  - path: docs/tech-design/desktop-agent.md
    expected_status: complete-with-gaps
---
```

`complete-with-gaps` needs a `gaps[]` entry for each target left uncovered and each audit finding the person accepted. A gap's `what` names the target's ID (or its epic, as in "EPC-035.AC1 to AC5") so the tickets check can tell an accepted gap from a missed one.

## Body, in this order

1. A title, then an opening of two or three sentences: what the plan covers, what it rests on, what the sizes mean, and the audit pointer line.
2. `## Summary`: a table `| Story | Traces to | Size total | Blocked by |`, one row per story, deferred and merged ones too. Size total is a count: `3 M, 2 S`. A deferred or merged story says `not planned`. The row may shorten a run (`EPC-032.AC1-4`) but names no target the story section lacks.
3. `## Stories`: one `### S-NN <name>` section per story, in the shape below.
4. `## Build order`: a numbered list, `1. S-01 (tracer): why it sits here`, tracer stories first. Stories not built are named in a closing line.
5. `## Critical path` (optional), `## Ticket waves` (which tickets to create now and which to hold).
6. `## Coverage`: a table `| Target | Stories |`, one row per trace target (one ID per row, `EPC-032.AC1`, not `AC1 to AC4`), then one row per design component. An empty Stories cell fails the plan, unless a `PG-nnn` accepts it.
7. `## Not planned`: each gap, deferral or open question the plan does not cover, with its ID and why.

## A story

```markdown
### S-02 Switch on, with consent recorded
- **Tracer:** yes
Traces to: CAP-005.FR1@APP-desktop-agent, CON-003, CON-004, EPC-032.AC1, EPC-032.AC2
Components: ConsentGate, ConsentRecorder, NoteView
Slice: tracer
Done when: a person who switches Heron on has each choice recorded, and a choice that is not confirmed leaves Heron reading nothing for them.
Acceptance criteria:
- When a person switches Heron on, they choose separately whether Heron may read their calendar entries and whether it may read their Teams transcripts. Each choice is kept.
- When a person switches Heron on, they are offered calendar entries and Teams transcripts as two separate choices, and cannot choose transcripts without calendar entries.
- A choice not confirmed by Consent and identity counts as not kept (design, Failure behavior).

| Task | Size | Component |
|---|---|---|
| `Grant` type constructible only inside the module, and the Consent check | S | ConsentGate |
| Durable outbox with confirmed and unconfirmed state | M | ConsentRecorder |

Blocked by: S-01 (store). The wording shown when Consent and identity is down waits on OQ-005.
Release fit: cannot tell for 2027-02-02. Sizes add to at most 14 days for one engineer, and the design names two Rust engineers but not how many days each has before 2027-02-02.
```

- `Traces to:` holds IDs only, one per target, each from the vault (`CAP-nnn.FRn@APP-x`, `CON-nnn`, `EPC-nnn.ACn`, `CST-nnn`). A story that rests on the design alone says `design only:` and names the design section. The quoted criteria come first, in the order of the IDs; criteria from the design or the team follow, written as the design states them.
- `- **Tracer:** yes` marks the team's tracer story; `Slice:` starts with `tracer`, `vertical` or `layer`, then any reason. A layer is flagged and folded into the slice that needs it, or says why it stays apart.
- The vault slice a story is part of goes on the same line, by ID: `Slice: vertical, SLC-002 The digest reaches a pilot user`. `vela tickets check` flags an ID the vault has no slice page for, or a slice this app takes part in nowhere; a story naming the tracer slice counts as a tracer story. Tickets come out grouped by it, the tracer first.
- `Release fit:` starts with the release date from `04b-releases.md` when the story's requirements are on a release, and says `cannot tell` with the missing number, or a rough sum "from your numbers". A story on no release names no date.
- `Blocked by:` is `none` (with an optional note after it), or story IDs, design questions (`OQ-nnn`), deferrals (`D-nnn`), vault unknowns (`UNK-nnn`) and outside parties.
- `Status:` is absent for a story that will be built. `Status: deferred (date). reason` keeps every other field, with tasks when they were sized. `Status: held` keeps tasks and appears in Ticket waves. `Status: merged into S-05 on <date>. reason` is the whole section of a story folded into another; its ID is retired, not reused. A split story is `S-07a` and `S-07b`, each with its own fields, in the summary and the order.
- A task row is three filled cells. Sizes are `S`, `M` or `L`.
- Keep prose under a story to the lines above. A free sentence the reader cannot place is reported as unread.
