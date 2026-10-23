---
id: solution-strategy
type: initiative-section
title: Solution strategy
arc42: "§4"
state: decided
owner: "@solution-lead"
authored: authored
---

# Solution strategy

The first release is assumed to be a laptop-only morning note. The agent on each laptop reads the person's own calendar entries, and an on-device model writes the 7:30 digest and the prep note, so no text leaves the device. The solution lead picked it because it keeps the February 2, 2027 pilot and the morning digest, which a cloud-written digest cannot do while the security officer refuses a pack that sends text off the device. Nothing here is checked yet: whether the on-device model writes a digest worth reading, who writes the list of data Heron reads, and whether the laptop agent needs a tenant app registration are all still open, and a Grill has to decide the choice.

> Replaces the paragraph above after 2026-10-12-privacy-m365-on-device; delete one.

The first release is a laptop-only morning note. The agent on each laptop reads the person's calendar entries and existing Teams transcripts, and an on-device model writes the 7:30 digest and the prep note, so no text leaves the device. [[11-unknowns-and-risks#UNK-066 Consent sees what agent read|Consent and identity]] is told only when a person switches Heron on or off, not what was read, and the agent provides no contract for its reads; the cloud-written digest, the calendar-first prep note and an agent that reports receipts are set aside. The cost is that nothing in the shared service shows what was read, so the works council's data list is a document the product owner writes and nobody checks against use, and the plan rests on the council accepting that list at its December meeting.

The hunches below are the earlier material from the two ends of the argument and are not decisions.

## The core move

- (product owner, one-pager of 2026-10-05) "a cloud service writes the summaries with a hosted language model, because the on-device model is poor"
- (solution lead) "I was wrong about consent—opt-in clicks don't cover it."
- (claude, taken up by the solution lead) What if the product owner and the CISO judged the on-device digest together, blind, on a dozen real mornings, before either side's position was argued?

## History

- **Decision:** [[2026-10-12-privacy-m365-on-device]]
- **Why:** The cloud-written digest was rejected because it rules out a February 2, 2027 pilot unless the CISO changes their line, and the calendar-first prep note because it drops the 7:30 morning digest.
- **Dissent:** @product-owner, 2026-10-05
- **Override:** "Boundary only on a decided direction" by @sim-lead on 2026-10-12: "text call in parallel works"
- **Override:** "Reopen a decided item at any time" by @sim-lead on 2026-10-12: the product owner can reopen this if the answer on whether Consent and identity sees what the agent read flips, but not before the lock
- **Options considered:** Laptop-only morning note (picked); Cloud-written digest: rejected, it rules out a February 2, 2027 pilot unless the CISO changes their line; Calendar-first prep note: rejected, it drops the 7:30 morning digest.
