---
id: solution-strategy
type: initiative-section
title: Solution strategy
arc42: "§4"
state: assumption
owner: "@solution-lead"
authored: authored
---

# Solution strategy

The first release is a coach that teaches on paper. A reader learns one stock at a time through lessons and simulated trades on Brightwater's sandbox accounts, and "ready" is a track the reader passes. The stocks come from a short list of about 50 large US equities that we choose. The release places no real order and covers equities only.

## The core move

The coach ships without real orders. That costs the least of the shapes weighed, because it stays clear of the ban on live trading, though the product lead only believes that and [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|compliance has not confirmed it in writing]]. If compliance says simulated trades on the sandbox fall inside the ban, this release does not ship. The sandbox also has to be allowed in a consumer product, and [[11-unknowns-and-risks#UNK-009 Signed broker agreement terms|the signed Brightwater agreement]] has not been read for that. Nothing regulated goes live before counsel and Brightwater sign off, which [[02-constraints|the constraints page]] records.

The CEO asked for trades, and this release delivers paper trading with no options and no real orders. The product lead will take that to her once Brightwater and compliance have signed off, and [[11-unknowns-and-risks#UNK-017 CEO and a paper-only release|whether she accepts it]] is open. Options stay out because [[sources#SRC-03|the agreement summary]] and [[sources#SRC-04|the license summary]] cover none.

The list holds only if counsel clears it as not investment advice, which [[11-unknowns-and-risks#UNK-021 Legal clearance of the stock list|is not yet ruled on]]. It also needs [[11-unknowns-and-risks#UNK-022 Owner and budget for the stock list|an owner and a budget]], and [[11-unknowns-and-risks#UNK-023 Coverage of every stock on the list|Brightwater and Quoteline must confirm coverage]] of every stock on it. The product lead believes [[11-unknowns-and-risks#UNK-024 Quoteline and teaching use|Quoteline's license covers teaching]] but has no source, and says that if it does not, the list does not ship. If counsel will not clear the list, the fallback is any US stock the reader picks.

## History

- **Options considered:** Teach on paper (picked); Recommend, reader taps: rejected, it needs a compliance ruling nobody has written; Automatic for the ready: rejected, it needs a compliance ruling nobody has written
- **Options considered:** A short list of big US stocks (picked, on condition that counsel clears the list as not investment advice); Any US stock the reader picks: rejected for now, kept as the fallback if legal will not clear the list; Stocks first, options as reading only: rejected, the CEO's acceptance is open and the options content is too much to run in parallel
