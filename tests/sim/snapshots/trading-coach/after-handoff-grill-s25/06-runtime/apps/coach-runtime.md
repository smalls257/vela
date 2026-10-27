---
id: RUN-coach
type: app-runtime
title: Coach runtime
state: decided
owner: "@sim-lead"
authored: authored
sources: [2026-10-08-first-release-boundary]
---

# Coach runtime

- **Decision:** [[2026-10-08-coach-team-handoff]]
- **Override:** E316 by @sim-lead on 2026-10-08: same pattern as the rest, risk owned by me, Coach team knows day one they own the support job
- **Options considered:** Coach app behind TickerTalk (picked); Coach built into TickerTalk: rejected, "B drowns mobile, they're already maxed" (the product lead); Coach, a separate board-demo app and Signal as idea source: rejected, "C's too many apps before we know what Brightwater allows" (the product lead)

Coach runs as its own app behind TickerTalk. A signed-in TickerTalk user opens it through [[coach-building-blocks#CON-001 Coach entry|CON-001]], and Coach takes the quotes for practice trades, delayed by 15 minutes, from Quoteline through [[coach-building-blocks#CON-002 Delayed quotes|CON-002]]. The Coach team runs it, in business hours only in release one. If Coach cannot answer, TickerTalk hides the entry and the news carries on, so an outage at 2am puts no one's money at risk. Who leads the Coach team is not named yet, and that is open in [[11-unknowns-and-risks#UNK-035 Who is the Coach lead and owns Coach's runtime|UNK-035]].

## On failure

- **Quoteline down, slow or stale:** practice pauses and lessons go on. A quote older than its stated 15-minute delay counts as no quote. The tolerance is not decided: the Coach team sets it with Quoteline once they have the agreement.
- **Coach down:** TickerTalk hides the entry, and the news app is unaffected.
- **Coach slow or failing while a user is inside it:** the user sees a plain "Coach is unavailable" message. Their lessons and recorded practice stay as they were, and an unfinished trade is not filled.

## Who runs it

- **Support:** the Coach team, business hours only in release one, from day one. There is no out-of-hours cover. A night-time outage is contained because the entry hides and the news carries on ([[2026-10-08-coach-team-handoff#^c03]]).
- **Detection:** the Coach team detects its own outages. TickerTalk and mobile have no new duty beyond hiding the entry ([[2026-10-08-coach-team-handoff#^c06]]).
- **Owner:** the coach lead, not yet named ([[11-unknowns-and-risks#UNK-035 Who is the Coach lead and owns Coach's runtime|UNK-035]]). The coach lead owns the runtime, the support and the approval of any change to the user ID. Until they are named, @sim-lead holds the approval. @sim-lead keeps UNK-027, UNK-028, UNK-029 and UNK-033 ([[2026-10-08-coach-team-handoff#^c10]]).
- **Funding:** who pays for running Coach is not decided; it waits on [[11-unknowns-and-risks#UNK-007 CFO 2.5 million budget|UNK-007]] and [[11-unknowns-and-risks#UNK-009 Build team new or pulled|UNK-009]] ([[2026-10-08-coach-team-handoff#^c09]]).
