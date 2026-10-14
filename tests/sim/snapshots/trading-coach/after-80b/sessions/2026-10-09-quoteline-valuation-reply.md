---
id: 2026-10-09-quoteline-valuation-reply
type: session
title: "Discover: Quoteline valuation reply"
date: 2026-10-09
modes: [discover, dump]
status: closed
summary: Valued paper positions on Quoteline delayed quotes confirmed as display use (SRC-28); filling paper orders opened as UNK-069.
---

# 2026-10-09 Discover: Quoteline valuation reply

## Captures

- [decision] (Jordan Reyes, product lead) "Keep SRC-28, read with SRC-10." then "Yes to SRC-28 as exists". SRC-28 registered as `exists`; read with SRC-10. Other sources left unread: "Honestly not sure about others." → keep: [[sources#SRC-28|SRC-28]] (exists) ^c01
- [thought] (claude, from Quoteline) Valuing paper balances and positions on Quoteline's delayed quotes is display use, inside the license, with no addendum or fee (line 1, SRC-28). The reply does not speak to filling paper orders or to Signal. → keep: [[03-context-and-scope#PTY-02 Quoteline|PTY-02]] (fact) ^c02
- [decision] (Jordan Reyes, product lead) "Yes to ... line 1, and resolving UNK-038." UNK-038 resolved by SRC-28. → keep: [[11-unknowns-and-risks#UNK-038 Valuing paper trades on Quoteline quotes|UNK-038]] (resolved) ^c03
- [decision] (Jordan Reyes, product lead) "Leave those three open." R-PTN-11, R-FIN-14 and R-REG-13 are only partly answered by SRC-28 (valuing, not filling or Signal) and stay open. R-REG-25 stays open: the reply is not the license text. → park ^c04
- [unknown] (Jordan Reyes, product lead) "Open the fills question - budget and compliance depend on it." No source says whether filling a paper order at a delayed Quoteline price is display use; SRC-28 covers valuing only. Owner and ask-by are Claude's proposal (partnerships manager, 2026-10-16), not yet corrected by the lead. to fetch: Quoteline's written answer on fills, held by Quoteline, asked through the partnerships manager. → keep: [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] (open) ^c05
- [thought] (Jordan Reyes, product lead) waits on UNK-069: R-PTN-11, R-FIN-14, R-REG-13, F1.8, F1.13, F1.21 → keep: [[11-unknowns-and-risks#Question ledger|R-PTN-11]] (unknown) ^c06
- [thought] (Jordan Reyes, product lead) "Changed my mind: it's delayed quotes only, no options on the license." Already recorded from SRC-04 (display of US equity quotes delayed 15 minutes, no options data); nothing new written. → park ^c07
- [unknown] (Jordan Reyes, product lead) "Does Coach-as-app actually block anything real or is it semantics?" The license summary (SRC-04) says TickerTalk's own apps may display the quotes; the license text is not held and Quoteline has not been told Coach is a separate service. → keep: [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] (open) ^c08
- [decision] (Jordan Reyes, product lead) "Fold it in, yes." The Coach-as-app question joins UNK-069 as part of the one ask to Quoteline. → keep: [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] (open) ^c09
- [thought] (Jordan Reyes, product lead) "Data engineer probably has that reply—honestly not sure who at Quoteline." A belief, not a source: nobody is recorded as holding SRC-28's original or as knowing its sender. Held with the data engineer, per the lead; sender not known. → park ^c10
- [thought] (Jordan Reyes, product lead) "What's missing is the money part. If the paper engine needs an addendum, how much and who pays it, because that matters for March." Put into the UNK-069 question; no fee is in any source. → keep: [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] (open) ^c11
- [thought] (Jordan Reyes, product lead) "The fee is the blocker—if filling needs clause 9 and it's material, does it blow the 180k budget or go to the CFO? Honestly not sure if Quoteline even charges per-request." Vault: the CFO's 180,000 estimate includes Quoteline display fees (SRC-16) and spend over 50,000 dollars goes to the CFO (SRC-19); no fee or pricing basis is recorded, so neither question can be answered yet. → keep: [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] (open) ^c12
- [decision] (Jordan Reyes, product lead) "Keep them." Owner @partnerships-manager and ask-by 2026-10-16 on UNK-069 stand. "term and exit can wait." Nothing else blocking. → park ^c13
- [decision] (Jordan Reyes, product lead) "if either blows the budget or pushes past mid-February, I need to know before we commit to 2,000 beta readers." The fee answer (UNK-069) and the review-timeline answer (UNK-040), both due 2026-10-16, are to be read against the budget and mid-February before the 2,000-reader beta is scheduled. "Compliance consultant's the blocker—if I don't surface them by tomorrow, the whole 16th schedule slips." UNK-065 is due 2026-10-12; the lead aims to name the consultant by 2026-10-10. → keep: [[11-unknowns-and-risks#UNK-040 Does the March beta fit the review timeline|UNK-040]] (open) ^c14

## Reviews

### 1. After the read-back, 2026-10-09

- **Coverage:** FIN found 6; DAT found 6, 1 dropped; PTN found 7; REG found 4; OPS found 6
- **Dropped:** [DAT] the quote does not mention what the finding is about: who holds and has read the SRC-28 reply
- **Merged:** [OPS] into F1.13: Who will ask Quoteline whether filling paper orders at delayed prices is display use, and by what date, given that CON-004 and the paper-trading epic depend on it?; [OPS] into F1.14: Who at Quoteline sent the 9 October reply, who at Kestrel received it, and who keeps the original so the license reading can be checked?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | Q-FIN-04@SV-01 | If a reader later opens a real Brightwater account, does the paper balance stay separate, or is any of it converted or carried over? Who decides, and where is that recorded? | "expects that record to stay in Coach if a reader later opens a real account, which is an assumption" in [[03-context-and-scope]] |
| F1.2 | FIN | normal | Q-FIN-05@SV-01 | What happens to a Brightwater balance and to a Coach paper balance when a reader closes the account, opts out, or the coach is withdrawn? | "Brightwater holds the money customers put in, and TickerTalk holds none" in [[03-context-and-scope]] |
| F1.3 | FIN | normal | Q-FIN-06@SV-01 | Is any conversion of paper to real value planned in any release? If it is, who sets the rate and who approves it? If it is not, should the vault say so? | "paper balances are not money" in [[03-context-and-scope]] |
| F1.4 | FIN | high | new | Should UNK-038 stay resolved, and the 'no fee' line stand, before the license text or clause 9 wording is held? Where will the fee terms be recorded? | "needs no addendum and no fee. [[sources#SRC-10\|Its earlier reply]] still holds" in [[11-unknowns-and-risks]] |
| F1.5 | FIN | normal | R-FIN-14 | Does the paper-trading engine's use of Quoteline prices, including fills and Coach's server-side valuation, count as non-display use? If it does, who pays the addendum fees, and out of which budget? | "Its replies say nothing about filling paper orders at delayed prices, and the license text itself is not held." in [[03-context-and-scope]] |
| F1.6 | FIN | normal | new | Is any Quoteline or market-data fee inside the allocated budget? If fills or Signal need an addendum, who carries that cost? | "there is none for valuing" in [[11-unknowns-and-risks]] |
| F1.7 | DAT | high | R-DAT-18 | Who will read clause 9 in the full license text, and does it allow Coach to use Quoteline quotes to generate lessons or recommendations, or does that need an addendum? | "the license text itself is not held." in [[03-context-and-scope]] |
| F1.8 | DAT | high | Q-DAT-03@CON-004 | Is using Quoteline's delayed prices to fill paper orders display use under the license, who asks Quoteline, and should CON-004 stay unsettled until they answer? | "The reply does not speak to filling paper orders at delayed prices, and the license text is not in sources." in [[11-unknowns-and-risks]] |
| F1.9 | DAT | high | new | Which unknown or question now owns the non-display risk (paper-trading engine, Signal), and who is named to close it before CON-004 is relied on? | "Whether the paper-trading engine or Signal uses Quoteline prices as non-display use stays open in the reviewer questions and in" in [[11-unknowns-and-risks]] |
| F1.10 | DAT | high | R-DAT-08 | On what license and terms may Coach display and store Brightwater's quotes, are they delayed, do they cover options, and is Quoteline then needed for display at all? | "it does not say whether those quotes are delayed or cover options." in [[03-context-and-scope]] |
| F1.11 | DAT | normal | Q-DAT-03@CON-003 | Does reader data cross to Brightwater's sandbox, were its consumers named when the data was collected, and is a paper-only reader a Brightwater customer? | "Whether a reader who only paper-trades counts as a Brightwater customer for that review is not recorded." in [[03-context-and-scope]] |
| F1.12 | DAT | high | Q-DAT-02@APP-tickertalk | What customer data does TickerTalk hold today, and on what lawful basis may it use it and send the reader ID to Coach? | "What TickerTalk holds today, and the lawful basis it holds it on, is not recorded" in [[tickertalk-building-blocks]] |
| F1.13 | PTN, OPS | high | R-PTN-11 | Will Quoteline say in writing whether using delayed quotes to fill paper orders is display or non-display use? Who asks, and when? Does release one's fill logic need the addendum? | "The reply does not speak to filling paper orders at delayed prices, and the license text is not in sources." in [[11-unknowns-and-risks]] |
| F1.14 | PTN, OPS | high | new | Who at Quoteline signed the 9 October reply, and does it bind Quoteline as a reading of the license? Should UNK-038 stay resolved until the license text is read or the reply is confirmed in writing? | "\| SRC-28 \| Quoteline: reply on valuing paper balances and positions \| Quoteline \| 2026-10-09 \| exists \| local only \|" in [[sources]] |
| F1.15 | PTN | high | Q-PTN-02@PTY-02 | Does the Quoteline license let the Coach service and any new owner or user display and use the quotes, or only TickerTalk's own apps? | "it lets TickerTalk's own apps display US equity quotes delayed by 15 minutes" in [[03-context-and-scope]] |
| F1.16 | PTN | normal | Q-PTN-03@PTY-02 | Who holds the Quoteline license, what is its term and exit cost, and what do its assignment, change-of-control and notice clauses say? | "the Quoteline market data license, summarized by the data engineer in March 2026" in [[03-context-and-scope]] |
| F1.17 | PTN | normal | Q-PTN-03@PTY-03 | Is Outside Counsel engaged under any agreement? Who holds it, how long does it run, and what are its exit and notice terms? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.18 | PTN | normal | Q-PTN-05@PTY-03 | Do Outside Counsel's engagement terms allow assignment or a change of control, and does sharing Coach data with counsel need any consent? | "Outside Counsel is the legal adviser whose written reply on the first release is in sources." in [[03-context-and-scope]] |
| F1.19 | PTN | normal | R-PTN-04 | Which agreements and licenses does the coach rely on, and what limits does each put on it? Are the two Quoteline replies part of the license? | "[[sources#SRC-28\|its reply of 9 October]] on valuing paper positions; the license itself is not in sources" in [[03-context-and-scope]] |
| F1.20 | REG | high | R-REG-25 | Will someone get the license text, or a Quoteline statement that binds it, confirming that valuing paper positions on delayed quotes is display use under clause 9? Until then, should UNK-038 stay open or be marked resolved on an unverified reply? | "the license text is not in sources." in [[11-unknowns-and-risks]] |
| F1.21 | REG | high | new | Is filling paper orders at delayed prices display or non-display use under the Quoteline license? Who asks Quoteline, and does the answer have to be in hand before release one? | "The reply does not speak to filling paper orders at delayed prices" in [[11-unknowns-and-risks]] |
| F1.22 | REG | normal | new | Does the license's grant to TickerTalk's own apps cover the Coach service computing and serving paper valuations, and has Quoteline said so? | "under a license that lets TickerTalk's own apps display US equity quotes delayed by 15 minutes, with no options data" in [[03-context-and-scope]] |
| F1.23 | REG | normal | R-REG-19 | With UNK-038 resolved for valuing only, is CON-004 now decided for display use, and which open question holds the non-display classification of order filling and Signal before RUN-coach is accepted? | "- **Blocks:** [[coach-building-blocks#CON-004 Quoteline delayed quotes]]" in [[11-unknowns-and-risks]] |
| F1.24 | OPS | normal | Q-OPS-03@CAP-003 | Which team owns the ready track after the change, and who accepts the work: the product lead, the Coach team or Fieldnote Learning? | "What ”ready” means is not yet defined." in [[CAP-003-pass-the-ready-track]] |
| F1.25 | OPS | normal | Q-OPS-03@CAP-003 | Should CAP-003 be corrected to the recorded definition of ready, and who owns that definition and the track after launch? | "They say the product lead defines ”ready” for the paper track as three graded paper trades on different stocks from the list plus every lesson for them." in [[03-context-and-scope]] |
| F1.26 | OPS | normal | Q-OPS-04@INI-001 | Which price source values a reader's paper balance and positions, Quoteline or Brightwater, and does the plan keep both? | "it does not say whether those quotes are delayed or cover options" in [[03-context-and-scope]] |
| F1.27 | OPS | normal | Q-OPS-05@INI-001 | Is anything retired or replaced by this change, and who still depends on it? If nothing, should the vault say so? | "TickerTalk, the news app, changed to add the coach screens and to send Coach the reader ID" in [[03-context-and-scope]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| SRC-28 | - | exists | [[2026-10-09-quoteline-valuation-reply#^c01]] |
| PTY-02 | - | fact | [[2026-10-09-quoteline-valuation-reply#^c02]] |
| UNK-038 | open | resolved | [[2026-10-09-quoteline-valuation-reply#^c03]] |
| UNK-069 | - | open | [[2026-10-09-quoteline-valuation-reply#^c05]] |
| R-PTN-11 | open | unknown | [[2026-10-09-quoteline-valuation-reply#^c06]] |
| R-FIN-14 | open | unknown | [[2026-10-09-quoteline-valuation-reply#^c06]] |
| R-REG-13 | unknown | unknown | [[2026-10-09-quoteline-valuation-reply#^c06]] |
| Q-DAT-03@CON-004 | open | unknown | [[2026-10-09-quoteline-valuation-reply#^c06]] |
| R-REG-31 | - | unknown | [[2026-10-09-quoteline-valuation-reply#^c06]] |
| R-FIN-28 | - | open | [[2026-10-09-quoteline-valuation-reply#1. After the read-back, 2026-10-09]] |
| R-FIN-29 | - | open | [[2026-10-09-quoteline-valuation-reply#1. After the read-back, 2026-10-09]] |
| R-DAT-24 | - | open | [[2026-10-09-quoteline-valuation-reply#1. After the read-back, 2026-10-09]] |
| R-PTN-26 | - | open | [[2026-10-09-quoteline-valuation-reply#1. After the read-back, 2026-10-09]] |
| R-REG-32 | - | open | [[2026-10-09-quoteline-valuation-reply#1. After the read-back, 2026-10-09]] |
