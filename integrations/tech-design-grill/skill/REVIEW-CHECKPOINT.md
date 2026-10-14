# Review Checkpoint

Run this once the design's sections are written, before `NEG-AUDIT.md`. The interview only surfaces what someone in the room knows. Fresh reviewers, each reading one area with no memory of the session, find what nobody mentioned: a vendor limit, a license clause, a nightly reset.

## 1. Dispatch five reviewers

Start five subagents in parallel, each with a fresh context and only these inputs: the design doc, `CONTEXT.md`, the ADRs, and the design's inputs (the requirements doc, or in vault mode the app's vault pages named in `TECH-DESIGN-FROM-VAULT.md`). Give each one area:

| Area | Asks |
|---|---|
| Vendors and integrations | What does each outside service, SDK and partner actually allow: rate limits, sandboxes and their resets, quotas, terms, what happens when it changes or is down? |
| Data and licensing | What may be stored, cached, shown, shared or used for training, under which license or consent, for how long, and who may see it? |
| Failure and recovery | What happens when each dependency is slow, wrong or gone, mid-operation; what is retried, what is lost, what does the user see, how is it repaired? |
| Security | Who can do what, how it is proven, where secrets live, what an attacker gains from each component. |
| Operations | How it is deployed, observed, paged, rolled back and paid for; what someone on call needs at 3am. |

Each reviewer returns at most 8 findings, each with: the area, a severity (`high`, `medium`, `low`), the design text it rests on quoted exactly with its section, what goes wrong in one concrete scenario, and the question the design must answer. A reviewer that finds nothing says so.

## 2. Check and merge

- Drop a finding whose quote is not in the design doc word for word. A reviewer that misquotes is guessing.
- Merge findings that ask the same question; keep the higher severity and both areas.
- Drop a finding that an existing `OQ-XXX`, `D-XXX` or ADR already answers, and say which.
- Rank: high first, then by how many components the scenario touches.

## 3. Dispose with the user

Show the merged list once, ranked, one line each. Then take them in order, one at a time, as `GRILL-LOOP.md` does, with your recommended disposition:

- **Answer now:** the user knows; update the design section and note the finding as resolved.
- **Open question:** write an `OQ-XXX` with the scenario, what would unblock it, and what it affects. While it is open the design can be at most `complete-with-gaps`, with a `gaps[]` entry naming the OQ.
- **Defer:** a `D-XXX`, when the answer is known and deliberately postponed.
- **Accept the gap:** the user goes ahead knowingly; it becomes a `gaps[]` entry and the status can be at most `complete-with-gaps`.
- **Not applicable:** with the reason, in one line.

Never drop a high-severity finding without one of these. Then go on to `NEG-AUDIT.md`.
