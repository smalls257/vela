---
id: solution-strategy
type: initiative-section
title: Solution strategy
arc42: "§4"
state: decided
owner: "@sim-lead"
authored: authored
---

# Solution strategy

- **Decision:** [[2026-10-08-first-instruments-signal]]
- **Override:** GATE-4 by @sim-lead on 2026-10-08: CEO wants the January demo, counsel cleared lessons and paper, unknowns to the team

## The core move

- **Education line:** "if we call this education not advice we don't need registration, but I could be wrong" (the product lead, no source). See [[11-unknowns-and-risks#UNK-010 Education line and counsel|UNK-010]].
- **Sequence:** read the Brightwater agreement this week, ask the consultant on Monday in general form, then take both answers to the CEO. The pitch waits for those answers (the product lead's plan, no source).

## First release

- **Scope:** release one for users is lessons and paper practice on individual US stocks, as counsel allows once the marketing and any shown results are reviewed (SRC-06; which counsel wrote it is open, [[11-unknowns-and-risks#UNK-023 Which counsel wrote the reply and when|UNK-023]]). The January board demo is a separate, private showing of the coach's trade ideas, which the user buys themselves; no customer can open it and it places no live trade (the CEO's words as the product lead gives them). Counsel is to clear that the demo does not trigger the recommendation rule, [[11-unknowns-and-risks#UNK-025 Recommendations at the January board demo|UNK-025]]. Release two is the stock order the coach prepares and the user confirms by hand, placed through Brightwater's API, pending [[11-unknowns-and-risks#UNK-022 Brightwater counsel sign-off on live trades|UNK-022]] and [[11-unknowns-and-risks#UNK-024 Brightwater owning the recommendation role|UNK-024]]. The board is to fund release two on the January demo, for live trading in March; which March is open, [[11-unknowns-and-risks#UNK-002 Which March|UNK-002]]. The account link waits on [[11-unknowns-and-risks#UNK-004 Brightwater agreement terms|UNK-004]]. Who runs the order path waits on [[11-unknowns-and-risks#UNK-019 Who runs the order path|UNK-019]].
- **Options considered:** A, teach on paper (release one, and the fallback if Brightwater says no); B, stocks with a hand confirm (release two, after Brightwater's sign-off); C, the CEO's ask as written: rejected, no team and no path to March

## First instruments

- **Scope:** Option A, stocks only. Release one teaches individual US-listed stocks, with lessons and paper practice on delayed quotes (SRC-02). The coach prepares or suggests no real order in release one. ETFs and options are not taught in release one: ETFs wait until Quoteline and Brightwater confirm they cover them, which is not recorded, and options wait on [[11-unknowns-and-risks#UNK-014 Options under the Brightwater agreement|UNK-014]]. Real stock orders through Brightwater's equity orders (SRC-01, SRC-05, first-hand, read in parts of the agreement) come in release two, after Brightwater's counsel signs off ([[11-unknowns-and-risks#UNK-022 Brightwater counsel sign-off on live trades|UNK-022]], February at the earliest) and Brightwater owns the recommendation role ([[11-unknowns-and-risks#UNK-024 Brightwater owning the recommendation role|UNK-024]]). Whether the license lets practice and lessons use the quotes waits on [[11-unknowns-and-risks#UNK-021 Clause 9 and the coach's lessons and practice|UNK-021]]. Whether the agreement also covers the account link is not recorded; [[11-unknowns-and-risks#UNK-004 Brightwater agreement terms|UNK-004]] stays open for it. The letters here name instrument options, not the First release options above.
- **Options considered:** A, stocks only (picked); B, stocks first with options as ideas only: rejected, "The clash kills B and C... I can't commit to two different things with the same letter" (the product lead); C, stocks and options together from day one: rejected, same reason
- **Rests on:** if Brightwater says no, everything pivots (the product lead's belief, load-bearing: yes). Signpost: the agreement says no, or is silent, on the account link and coach-prepared orders, or Brightwater's counsel refuses the sign-off in UNK-022. Read on 2026-10-08: the API takes live stock orders (SRC-05), so the first half has not tripped.
- **Rests on:** if the consultant cannot sign off in time, March is missed whatever A costs (the product lead's belief, load-bearing: yes). Signpost: the consultant's sign-off date falls after March. Which March is open, [[11-unknowns-and-risks#UNK-002 Which March|UNK-002]].
- **Rests on:** a clause 9 addendum would cost months (the product lead's belief, load-bearing: yes). Signpost: the data engineer says practice and lessons need an addendum, or gives no answer by 2026-10-16.

## For the pitch

- **Stepped first release (inkling):** to keep the March date without conceding the goal, lessons and paper trading go first (outside counsel allows them once marketing and any shown results are reviewed, SRC-06), Brightwater-owned recommendations next, and trading for customers later. This is the product lead's plan for the CEO conversation on 2026-10-09, an idea of claude's the product lead picked for that talk, not a choice. It waits on [[11-unknowns-and-risks#UNK-024 Brightwater owning the recommendation role|UNK-024]], [[11-unknowns-and-risks#UNK-001 Meaning of trades for them|UNK-001]] and [[11-unknowns-and-risks#UNK-023 Which counsel wrote the reply and when|UNK-023]].
