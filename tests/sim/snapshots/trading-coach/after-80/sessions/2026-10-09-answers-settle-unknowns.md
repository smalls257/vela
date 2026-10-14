---
id: 2026-10-09-answers-settle-unknowns
type: session
title: "Discover: answers settle unknowns"
date: 2026-10-09
modes: [discover, dump]
status: closed
summary: "Discover/dump: answers settled 17 unknowns and registered SRC-19 to SRC-23. Ledger rows were written for the compliance ruling, the CEO equities call and the partner document texts. New unknowns are UNK-055 to UNK-058."
---

# 2026-10-09 Discover: answers settle unknowns

## Captures

- [decision] (Jordan Reyes, product lead) "Yes to ranking and kinds, all exists." SRC-19, SRC-20 and SRC-21 registered as `exists`; read SRC-16 and SRC-19 first, then SRC-20 and SRC-21. → keep: [[sources#SRC-19|SRC-19]] (exists) ^c01
- [unknown] (Jordan Reyes, product lead) "November 3 Brightwater date—honestly not sure, check with @partnerships-lead." The Brightwater reply file (SRC-13) is headed 3 November but registered as 2026-10-09, and today is 9 October. to fetch: the real date of the reply, held by the partnerships manager (the user wrote @partnerships-lead; the vault's handle is @partnerships-manager). → keep: [[11-unknowns-and-risks#UNK-055 Date of Brightwater's written reply|UNK-055]] (open) ^c02
- [unknown] (Jordan Reyes, product lead) "counsel ruled but I don't have the written ruling". The compliance consultant's 2 October ruling is still second-hand. to fetch: the written ruling, held by the compliance consultant (name not recorded). Stays on UNK-003. → keep: [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|UNK-003]] (open) ^c03
- [unknown] (Jordan Reyes, product lead) "no full texts from Brightwater, Quoteline, or Fieldnote". to fetch: the Brightwater agreement, the Quoteline license and the Fieldnote Learning contract in full. Stays on UNK-015 and UNK-041. → keep: [[11-unknowns-and-risks#UNK-056 Full texts of the three partner documents|UNK-056]] (open) ^c04
- [thought] (Jordan Reyes, product lead) "mobile confirmed on the 7th". Disagrees with SRC-12, which says the mobile lead confirmed capacity on 14 October. Not yet a fact: it needs its own first-hand row and the user's yes on the line. Bears on UNK-019. → keep: [[11-unknowns-and-risks#UNK-019 Mobile capacity for March|UNK-019]] (open) ^c05

- [thought] (claude, from product lead) Fieldnote Learning's contract, held by the product lead: Kestrel owns the lessons, either side may end it on 30 days' notice, the consultant checks each lesson before it is paid for (line 1, SRC-19). → keep: [[03-context-and-scope#PTY-04 Fieldnote Learning|PTY-04]] (fact) ^c06
- [thought] (claude, from Coach lead) The on-call rota goes live on 1 March, before the first beta reader (line 2, SRC-19, SRC-20). A plan. → park ^c07
- [thought] (claude, from Coach lead) Calls to Coach time out after 3 seconds and calls to Quoteline after 2 (line 3, SRC-20). Not built yet. → park ^c08
- [thought] (claude, from Coach lead) A paper order may stay pending 15 minutes, then Coach marks it failed and asks the sandbox for its status once (line 4, SRC-20). → park ^c09
- [thought] (claude, from Coach lead) Coach opens a reader's sandbox paper account at their first practice trade; on failure the reader sees 'practice is unavailable, try again later' and lessons carry on (line 5, SRC-19). → park ^c10
- [thought] (claude, from product lead) A paper trade passes when the reader states why they entered it, sets a stop and closes it within the lesson's rules; three passes on different stocks pass the ready track (line 6, SRC-19). → keep: [[03-context-and-scope#Today|SRC-19]] (fact) ^c11
- [thought] (claude, from Coach lead) The Coach lead owns the review of Coach's failure cases during the build (line 7, SRC-19). → keep: [[concern-ownership#Strategy|SRC-19]] (fact) ^c12
- [thought] (claude, from privacy lead) The privacy lead who approved the opt-in wording is @privacy-lead (line 8, SRC-19, SRC-21). → keep: [[concern-data#Strategy|SRC-19]] (fact) ^c13
- [thought] (claude, from privacy lead) On withdrawal Coach keeps the record 30 days so the reader can undo it, then deletes it (line 9, SRC-19). A plan. → park ^c14
- [thought] (claude, from mobile lead) A reader's ID stays the same for the life of their account, across a change of email or a new device, and is never reused (line 10, SRC-19). → keep: [[concern-data#Strategy|SRC-19]] (fact) ^c15
- [thought] (claude, from mobile lead) Mobile's plan has TickerTalk check each reader's opt-in before sending the ID and hide the coach screens for readers who have not opted in (line 11, SRC-19). A plan; says nothing on Coach receiving only the ID. → park ^c16
- [thought] (claude, from platform engineer) The on-call rota covers TickerTalk's backend, including the reader lookup, 24/7, and now lists Coach's dependence on it (line 12, SRC-19). → keep: [[concern-operations#Strategy|SRC-19]] (fact) ^c17
- [thought] (claude, from CFO) The CFO is the named holder of the 2.5 million dollar budget and signs off spend over 50,000 dollars (line 13, SRC-19). → keep: [[concern-cost#Strategy|SRC-19]] (fact) ^c18
- [thought] (Jordan Reyes, product lead) "the budget's clearly for the coach, first year." First-hand; registered as SRC-23. → keep: [[concern-cost#Strategy|SRC-23]] (fact) ^c19
- [thought] (claude, from compliance consultant) The consultant signs off two lessons a week and Brightwater reviews in ten business days, so the 24 beta lessons clear by 15 February (line 14, SRC-19). A forecast. → park ^c20
- [thought] (claude, from partnerships manager) Brightwater replied that it will not act as recommender or supervisor for trade ideas in year one (line 15, SRC-19). → keep: [[03-context-and-scope#PTY-01 Brightwater|PTY-01]] (fact) ^c21
- [thought] (claude, from ML lead) The ML lead owns Signal, and Signal stays out of release one (line 19, SRC-16). → keep: [[03-context-and-scope#Out of scope|SRC-16]] (fact) ^c22
- [thought] (claude, from mobile lead) TickerTalk's existing security, cost, testing and observability practice holds unchanged except the new contract tests on the coach entry; its rollout is the opt-in beta, owned by the mobile team (line 20, SRC-19). A plan. → park ^c23
- [thought] (Jordan Reyes, product lead) "Oct 7's right on mobile, not 14th—that's when @mobile-lead said two can build it by March. The 14th reference I'm honestly not sure what you're seeing." First-hand; registered as SRC-22. SRC-12's title still says 14 October; SRC-22 states 7 October. A plan, so an assumption. → keep: [[11-unknowns-and-risks#UNK-019 Mobile capacity for March|UNK-019]] (open) ^c24
- [unknown] (Jordan Reyes, product lead) "Container names are clashing though; Coach lead's got Paper practice and Quote display, our page has the other names. That's the real conflict." The page owns the names; UNK-046 stays open and nothing is written as a fact. → keep: [[11-unknowns-and-risks#UNK-046 Coach lead's names for the containers|UNK-046]] (open) ^c25

- [thought] (Jordan Reyes, product lead) "two engineers, @partnerships-manager." Two engineers can build it by March (SRC-22); the Brightwater reply date goes to @partnerships-manager. → keep: [[11-unknowns-and-risks#UNK-019 Mobile capacity for March|UNK-019]] (open) ^c26
- [thought] (Jordan Reyes, product lead) "Yes to all the unknowns ... UNK-031 and UNK-016 work fine, leave the rest open." Seventeen unknowns resolved; UNK-002, 013, 015, 040, 046 and 048 stay open. → keep: [[11-unknowns-and-risks#UNK-041 Terms of the Fieldnote Learning contract|UNK-041]] (resolved) ^c27
- [unknown] (Jordan Reyes, product lead) "Can't brief the CEO until we have the written ruling from counsel." Stays on UNK-003; the written ruling is still to fetch from the compliance consultant (name not recorded). → keep: [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|UNK-003]] (open) ^c28
- [unknown] (claude, from Jordan Reyes) What the real date of Brightwater's written reply is. to fetch: the date, held by the partnerships manager. → keep: [[11-unknowns-and-risks#UNK-055 Date of Brightwater's written reply|UNK-055]] (open) ^c29

- [decision] (Jordan Reyes, product lead) "Leave UNK-041 resolved with the note." Note added on UNK-041: the contract text is not held. → keep: [[11-unknowns-and-risks#UNK-041 Terms of the Fieldnote Learning contract|UNK-041]] (resolved) ^c30
- [unknown] (Jordan Reyes, product lead) "The compliance consultant's name and the written ruling are my blocker—I need those by the 13th to brief the CEO, honestly not sure who holds that right now." waits on UNK-003: R-OPS-17, F1.38. to fetch: the consultant's name and the written ruling, held by an unknown compliance person. → keep: [[11-unknowns-and-risks#UNK-003 Compliance ruling in writing|UNK-003]] (open) ^c31
- [unknown] (Jordan Reyes, product lead) "I need to know if she'll accept equities-only before I walk in with the plan." waits on UNK-017: R-REG-11. to fetch: the CEO's answer, held by the CEO. → keep: [[11-unknowns-and-risks#UNK-017 CEO and a paper-only release|UNK-017]] (open) ^c32
- [thought] (Jordan Reyes, product lead) "Wave through the Brightwater, Quoteline and Fieldnote text questions; they all wait on the documents I'm going to ask partners for anyway." waits on UNK-056: Q-PTN-02@PTY-01, Q-PTN-02@PTY-02, Q-PTN-02@PTY-04, Q-PTN-03@PTY-01, Q-PTN-03@PTY-02, Q-PTN-03@PTY-04, Q-PTN-05@PTY-02, Q-PTN-05@PTY-04, Q-PTN-06@PTY-01, Q-PTN-06@PTY-02, Q-PTN-06@PTY-04, R-FIN-10, R-DAT-09, F1.8. The Outside Counsel copies (the PTY-03 ones) are not documents the product lead is asking for, so they stay open. → keep: [[11-unknowns-and-risks#UNK-056 Full texts of the three partner documents|UNK-056]] (open) ^c33
- [thought] (Jordan Reyes, product lead) "Same with the sandbox-account limit." waits on UNK-040, whose question already asks whether the ten sandbox accounts limit the beta: F1.39, F1.65. → keep: [[11-unknowns-and-risks#UNK-040 Does the March beta fit the review timeline|UNK-040]] (open) ^c34
- [thought] (Jordan Reyes, product lead) "7 October came from the CEO's written notes, 14 October from me relaying what @mobile-lead said." Disagrees with SRC-22, which records the 7 October date as the product lead's first-hand account of the mobile lead. Not yet written to any page; the product lead is asked which is right. → keep: [[11-unknowns-and-risks#UNK-019 Mobile capacity for March|UNK-019]] (open) ^c35

- [decision] (Jordan Reyes, product lead) "You're right, I'm mixed up on the dates—just have @mobile-lead confirm in writing what they said and by when. That settles it and clears the capacity risk at once." UNK-019 set back to open, owner @mobile-lead, ask by 2026-10-14. waits on UNK-019: F1.59, R-OPS-03. to fetch: the mobile lead's written confirmation of what they said and by when, held by @mobile-lead. → keep: [[11-unknowns-and-risks#UNK-019 Mobile capacity for March|UNK-019]] (open) ^c36
- [decision] (Jordan Reyes, product lead) "Push UNK-017 to 10 October for the equities call; if she won't accept it, the whole plan shifts and I need to know before board prep starts." UNK-017 ask-by moved from 2026-11-13 to 2026-10-10. → keep: [[11-unknowns-and-risks#UNK-017 CEO and a paper-only release|UNK-017]] (open) ^c37

- [thought] (Jordan Reyes, product lead) "Wave them through because they either depend on the three blockers I named or they're build-team detail once those three are settled. Nobody's shipping anything until compliance signs off and the CEO backs the plan anyway." Ruled out, reason as given: Q-DAT-04@SV-01, Q-FIN-04@SV-01, Q-FIN-05@SV-01, Q-FIN-06@SV-01, Q-OPS-05@INI-001, Q-PTN-03@PTY-03, Q-PTN-06@PTY-03, R-DAT-04, R-DAT-06, R-DAT-11, R-DAT-12, R-DAT-13, R-FIN-03, R-FIN-04, R-FIN-11, R-FIN-15, R-FIN-18, R-FIN-20, R-FIN-21, R-OPS-06, R-OPS-07, R-OPS-13, R-OPS-16, R-OPS-19, R-OPS-20, R-PTN-02, R-PTN-04, R-PTN-15, R-PTN-17, R-REG-08, R-REG-12, R-REG-14, R-REG-20, R-REG-21, F1.16, F1.41, F1.61, F1.63, F1.64, F1.79. The stale-page notes among them (F1.16, F1.61, F1.63) leave the pages as they are. → park ^c38
- [thought] (Jordan Reyes, product lead) "Q-DAT-03 goes once mobile confirms the data flow". waits on UNK-048: Q-DAT-03@CON-001, Q-DAT-03@CON-002, Q-DAT-03@CON-003, Q-DAT-03@CON-004, Q-DAT-03@CON-005 → keep: [[11-unknowns-and-risks#UNK-048 Does mobile's plan cover sending the ID only for opted-in readers|UNK-048]] (open) ^c39
- [thought] (Jordan Reyes, product lead) "Q-OPS-03 goes when the teams form." waits on UNK-057: Q-OPS-03@CAP-001, Q-OPS-03@CAP-002, Q-OPS-03@CAP-003, Q-OPS-03@CAP-004 → keep: [[11-unknowns-and-risks#UNK-057 Which team owns each capability after the change|UNK-057]] (open) ^c40
- [thought] (Jordan Reyes, product lead) "Leave Q-OPS-04 open though; that container clash is exactly what'll trip up the board if the names aren't straight. The liability ones (Q-REG-01 and Q-REG-05) can stay open for now." Q-OPS-04@INI-001, Q-REG-01@INI-001 and Q-REG-05@INI-001 stay open. → keep: [[11-unknowns-and-risks#Question ledger|Q-OPS-04@INI-001]] (open) ^c41
- [unknown] (Jordan Reyes, product lead) "nobody's said what 'ready to ship' looks like in January. We've got the board demo criteria but not what the actual launch gate is in March, or who decides if something slips." to fetch: the March launch gate and who decides a slip, held by the product lead with the CEO (not recorded); the board demo criteria are not in the vault. → keep: [[11-unknowns-and-risks#UNK-058 March launch gate and who decides a slip|UNK-058]] (open) ^c42
- [unknown] (claude, from Jordan Reyes) Which team owns CAP-001 to CAP-004 once the teams form. → keep: [[11-unknowns-and-risks#UNK-057 Which team owns each capability after the change|UNK-057]] (open) ^c43

## Reviews

### 1. After the read-back, 2026-10-09

- **Coverage:** FIN found 16, 4 dropped; DAT found 11; PTN found 17, 5 dropped; REG found 16, 1 dropped; OPS found 21, 1 dropped
- **Dropped:** [FIN] the quote does not mention what the finding is about: Who carries liability if readers lose money following lessons or paper results, and is any legal, registration or insurance cost in the 2.5 million?; [FIN] the quote does not mention what the finding is about: Would the coach need any registration or license, what would it cost, and is it inside the 2.5 million?; [FIN] the quote does not mention what the finding is about: What reader volume and release scope does the 180,000 assume, and what would it cost if the coach is offered to every reader?; [FIN] the quote does not mention what the finding is about: Is Coach or the Brightwater sandbox the record of each reader's paper balance? Should the data page and the Coach page be aligned, and who carries the storage cost?; [PTN] its quote "none known" has fewer than 4 words, too few to show where it came from: Is there any engagement terms with Outside Counsel, and do they or Fieldnote Learning receive any reader or product data?; [PTN] its quote "none known" has fewer than 4 words, too few to show where it came from: Is there an engagement with Outside Counsel, who holds it, and what does it cost to keep or end it?; [PTN] its quote "none known" has fewer than 4 words, too few to show where it came from: Is there any written engagement with Outside Counsel, and does it allow assignment?; [PTN] its quote "Agreements:** none known" has fewer than 4 words, too few to show where it came from: What notice terms govern the Outside Counsel engagement?; [PTN] it names R-PTN-11, which this vault does not owe and has no open reviewer question for; write new for a question of your own: Is a Quoteline addendum fee for valuing paper trades inside the 180,000 dollar estimate? If not, who asks for it and who pays from the 2.5 million?; [REG] the quote does not mention what the finding is about: Who in legal or compliance approves what 'ready' means and how it is worded to readers?; [OPS] its quote "3 (2 by override)" is not in the written text of [[01-goals]]: Who authorized the gate override on the TickerTalk and Coach decisions, and which blocking unknowns must close before the strategy is treated as decided?
- **Merged:** [PTN] into F1.8: Does the product lead hold the Fieldnote contract or not? If so, will they read out or supply the clauses on ownership, notice, assignment and payment so UNK-041 can be resolved on the text?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | normal | Q-FIN-03@SV-01 | Is the partnerships manager's account enough to record who carries the balances, or does the product lead need the signed agreement's wording before this is treated as a fact? | "which carries the balances as money owed to its own customers, per" in [[03-context-and-scope]] |
| F1.2 | FIN | normal | Q-FIN-04@SV-01 | When a reader moves from paper to a real Brightwater account, does any balance convert or carry over, or is it a clean start with only the history kept? | "expects that record to stay in Coach if a reader later opens a real account" in [[03-context-and-scope]] |
| F1.3 | FIN | normal | Q-FIN-05@SV-01 | What happens to a reader's Brightwater balance, and to the paper balance, if the reader closes the account, the account expires or the coach is withdrawn? | "Brightwater holds the money customers put in, and TickerTalk holds none" in [[03-context-and-scope]] |
| F1.4 | FIN | normal | Q-FIN-06@SV-01 | Is there any conversion rate at all? If there is none, record that. If there is one, who sets it and who approves it? | "paper balances are not money" in [[03-context-and-scope]] |
| F1.5 | FIN | high | R-FIN-07 | If a later release lets readers fund Brightwater accounts, who handles deposits and withdrawals, and what becomes of a balance if the account closes or the coach is withdrawn? | "It says trading for customers waits for a later release, after counsel and Brightwater sign off" in [[01-goals]] |
| F1.6 | FIN | normal | R-FIN-04 | Does the 2.5 million assume any live trading through Brightwater? If a later release adds it, who pays for the integration and the fees? | "the budget is for the coach's first year" in [[concern-cost]] |
| F1.7 | FIN | normal | R-FIN-10 | Once the Brightwater agreement is in hand, does it charge for sandbox or paper-trading use, and what does leaving on 90 days' notice cost? | "no full texts from Brightwater, Quoteline, or Fieldnote" in [[2026-10-09-answers-settle-unknowns]] |
| F1.8 | FIN, PTN | high | new | Should UNK-041 be resolved while the full agreement and contract texts are still not held, and where will their fee and termination clauses be recorded? | "Stays on UNK-015 and UNK-041." in [[2026-10-09-answers-settle-unknowns]] |
| F1.9 | FIN | normal | R-FIN-11 | What is the true date of Brightwater's reply, and does the date change which terms the plan may rely on? | "is headed 3 November, but the source is dated 9 October and today is 9 October" in [[11-unknowns-and-risks]] |
| F1.10 | FIN | high | R-FIN-12 | Does a written clearance of the stock list exist? Who owns the list and which budget pays for it, before the decision is taken? | "The override at the foot of this page says it was cleared in writing; no clearance is recorded in any source." in [[11-unknowns-and-risks]] |
| F1.11 | FIN | normal | R-FIN-15 | Does the review apply to paper-only readers, who bears the cost of reviewing every lesson and screen, and is there an options agreement fee? | "Whether a reader who only paper-trades counts as a Brightwater customer for that review is not recorded." in [[03-context-and-scope]] |
| F1.12 | FIN | high | R-FIN-16 | Are Brightwater's quotes free and licensed for display to non-customers, and does using them avoid Quoteline's non-display fees or add a second license cost? | "it does not say whether those quotes are delayed or cover options" in [[03-context-and-scope]] |
| F1.13 | FIN | high | R-FIN-17 | Is the SRC-12 date of 14 October superseded by SRC-22, and who hosts, runs and pays for the Coach service? | "Jordan Reyes's first-hand account that the mobile lead confirmed capacity on 14 October" in [[sources]] |
| F1.14 | FIN | normal | R-FIN-20 | When will the cost cell be settled? Will it say that the CFO's 2.5 million pays for Coach, the stock list and the lessons, and who carries Coach's running cost? | "Owner and budget for the stock list" in [[concern-cost]] |
| F1.15 | FIN | normal | R-FIN-21 | Who pays to build TickerTalk's side of CON-005 and the coach screens, and will the data page be updated for the resolved reader ID? | "TickerTalk's cost for the coach screens has not been examined." in [[concern-cost]] |
| F1.16 | FIN | normal | new | Should the context page be updated to the CFO's 2.5 million, and does that budget cover the stock list and lessons as well as Coach? | "A budget has been allocated, but its size, holder and scope are not recorded" in [[03-context-and-scope]] |
| F1.17 | DAT | high | Q-DAT-03@CON-003 | What reader data is sent to Brightwater when the sandbox account is opened and when paper orders are placed? Was Brightwater named in the opt-in, and which clause of the signed agreement allows it? | "Coach opens a reader's sandbox paper account at their first practice trade." in [[11-unknowns-and-risks]] |
| F1.18 | DAT | high | Q-DAT-01@INI-001 | Is Brightwater, or any other party, going to use reader data (identity, picks, paper trades)? If so, who records the lawful basis, and is it Brightwater's or Kestrel's? | "Coach opens a reader's sandbox paper account at their first practice trade." in [[11-unknowns-and-risks]] |
| F1.19 | DAT | high | Q-DAT-03@CON-005 | Will TickerTalk send Coach only the opaque reader ID, and does the mobile team confirm it? Until then, what else might cross, and under what basis? | "it does not say that Coach receives nothing but the ID" in [[concern-data]] |
| F1.20 | DAT | high | Q-DAT-02@APP-coach | Does the opt-in, as the privacy lead approved it, cover picks and the paper balance and trades? Who confirms this in writing, and what is the lawful basis for each kind of Coach data? | "the wording does not name stock picks or the paper balance in words" in [[11-unknowns-and-risks]] |
| F1.21 | DAT | normal | Q-DAT-02@APP-tickertalk | What reader data does TickerTalk hold (email, reader ID, watchlists, consent), who collected it for what, and what is the lawful basis for sending the ID to Coach? | "TickerTalk's own data is not recorded either" in [[concern-data]] |
| F1.22 | DAT | normal | Q-DAT-04@SV-01 | Is Coach the single record of each reader's paper balance and trades, as UNK-029 says? Should the concern page and the building-block pages be updated to match? | "the vault does not yet say which" in [[concern-data]] |
| F1.23 | DAT | high | R-DAT-15 | How does a withdrawal reach Coach, who starts the 30-day clock, and what is the lawful basis for holding the record during those 30 days? Is the privacy lead's rule confirmed in writing? | "Coach keeps their record for 30 days so they can undo it, then deletes it" in [[11-unknowns-and-risks]] |
| F1.24 | DAT | high | new | Will any reader data (watchlists, picks, practice trades) ever train Signal? If so, who gets fresh consent, and does the opt-in promise 'Nothing is used to train any model' bind that? | "The ML team wants to train on TickerTalk users' watchlists next" in [[01-goals]] |
| F1.25 | DAT | high | R-DAT-09 | Who gets the full Brightwater agreement, Quoteline license and Fieldnote contract, and by when? Is UNK-041 really resolved while the capture says it stays open? | "no full texts from Brightwater, Quoteline, or Fieldnote" in [[2026-10-09-answers-settle-unknowns]] |
| F1.26 | DAT | high | R-DAT-09 | Does SRC-13 or the full agreement say anything about customer consent or about which data each side may collect, share and reuse? If not, who asks Brightwater, and by when? | "the terms on consent, data and live trading are still open" in [[03-context-and-scope]] |
| F1.27 | DAT | normal | R-DAT-06 | What are the real dates of the Brightwater reply and the mobile confirmation? Which page owns each date, and should UNK-048 and the SRC-12 title change? | "fit their plan for the 14 October sign-off" in [[11-unknowns-and-risks]] |
| F1.28 | PTN | high | Q-PTN-02@PTY-01 | What does the signed Brightwater agreement say on data sharing and consent, and does it cover per-reader sandbox accounts in a public consumer app? | "It is silent on consent, data, live trading and section 7.2" in [[11-unknowns-and-risks]] |
| F1.29 | PTN | high | Q-PTN-02@PTY-02 | Does the Quoteline license let the Coach service display and use quotes as one of 'TickerTalk's own apps', and can it share them with a new user or owner? | "lets TickerTalk's own apps display US equity quotes delayed by 15 minutes" in [[03-context-and-scope]] |
| F1.30 | PTN | normal | Q-PTN-03@PTY-01 | What year was the Brightwater agreement signed, when does it end, and what does leaving or varying it cost? | "the signed broker agreement, June (year not recorded), held by the partnerships manager" in [[03-context-and-scope]] |
| F1.31 | PTN | normal | Q-PTN-03@PTY-02 | Who holds the Quoteline license, when does it end, and what does leaving or changing it cost? | "summarized by the data engineer in March 2026" in [[03-context-and-scope]] |
| F1.32 | PTN | normal | Q-PTN-03@PTY-04 | What would ending the Fieldnote contract cost for lessons in progress, and what is its end date? | "either side may end it on 30 days' notice" in [[03-context-and-scope]] |
| F1.33 | PTN | high | Q-PTN-05@PTY-02 | Does the Quoteline license allow assignment or a change of control of Kestrel or Coach? | "the license itself is not in sources" in [[03-context-and-scope]] |
| F1.34 | PTN | high | Q-PTN-05@PTY-04 | Does the Fieldnote contract allow assignment or change of control, and what does the full text say on lesson ownership? | "the contract itself is not in sources" in [[03-context-and-scope]] |
| F1.35 | PTN | normal | Q-PTN-06@PTY-01 | What notice does a change to the Brightwater agreement need, and who must give it? | "that either side may leave with 90 days' notice" in [[03-context-and-scope]] |
| F1.36 | PTN | normal | Q-PTN-06@PTY-02 | What notice does a change to, or an addendum of, the Quoteline license need, and who gives it? | "the license itself is not in sources" in [[03-context-and-scope]] |
| F1.37 | PTN | normal | Q-PTN-06@PTY-04 | What notice does a change to the Fieldnote contract need, and who gives it? | "the contract itself is not in sources" in [[03-context-and-scope]] |
| F1.38 | PTN | high | new | Who is the compliance consultant, what agreement do they work under, and is a two-lessons-a-week sign-off rate committed in it? | "held by the compliance consultant (name not recorded)" in [[2026-10-09-answers-settle-unknowns]] |
| F1.39 | PTN | high | new | Does Brightwater's agreement allow 2,000 or more sandbox paper accounts for the beta, or only the ten test accounts? Is a higher limit agreed in writing? | "the limit of ten sandbox test accounts" in [[concern-rollout]] |
| F1.40 | PTN | high | new | Has partnerships or the consultant confirmed the 15 February clearance against the five-weeks-per-lesson estimate, rejection restarts and the Fieldnote start date? | "so the 24 beta lessons would be cleared by 15 February" in [[concern-rollout]] |
| F1.41 | PTN | normal | new | Is there a written Brightwater statement on the supervisor role, and what is its date and signatory? | "that Brightwater has replied that it will not act as recommender or supervisor for trade ideas in year one" in [[03-context-and-scope]] |
| F1.42 | PTN | high | R-PTN-13 | What is the real date of the reply and who at Brightwater signed it? Does it count as a variation or permission under the signed agreement, and so does UNK-055 block CON-003? | "nothing yet, since no plan item rests on the reply's date" in [[11-unknowns-and-risks]] |
| F1.43 | PTN | high | R-PTN-12 | Does the signed agreement let the sandbox be used for paper accounts in a public app, and does paper-only use fall under Brightwater's content review? | "Whether a reader who only paper-trades counts as a Brightwater customer for that review is not recorded." in [[03-context-and-scope]] |
| F1.44 | REG | normal | Q-REG-01@INI-001 | Will compliance and counsel rule on whether the coach, Brightwater and Quoteline together count as a product sold or promised across parties? Who asks them, and before which decision? | "Whether the coach, Brightwater and Quoteline together make a product sold or promised across parties, and who is liable to the customer when one part fails, are still open" in [[11-unknowns-and-risks]] |
| F1.45 | REG | normal | Q-REG-05@INI-001 | When Coach, Brightwater or Quoteline fails a reader, who answers to the reader? Who in compliance or counsel will say so, and by when? | "who is liable to the customer when one part fails, are still open" in [[11-unknowns-and-risks]] |
| F1.46 | REG | high | R-REG-06 | Who in legal will rule in writing on whether the stock list and any suggested trades are investment advice, and by when, given the Fieldnote start on 12 October and the March date? | "no clearance is recorded in any source." in [[11-unknowns-and-risks]] |
| F1.47 | REG | high | R-REG-07 | Is TickerTalk or Brightwater licensed to place orders on a customer's behalf, and what must the opt-in and audit trail satisfy before any later release? | "automatic orders placed through a partner broker" in [[11-unknowns-and-risks]] |
| F1.48 | REG | normal | R-REG-08 | Who approves any customer-facing or board-facing statement of Signal's results? Do legal or compliance require hypothetical-performance disclosures? | "Who reviews the marketing and the shown results is not recorded." in [[03-context-and-scope]] |
| F1.49 | REG | high | R-REG-10 | Does the signed agreement itself allow sandbox accounts in a consumer product? Will compliance confirm in writing that paper trading is outside the live-trading ban? | "if Brightwater says no on the consumer product, the Coach plan is rewritten before the board demo" in [[11-unknowns-and-risks]] |
| F1.50 | REG | high | R-REG-11 | Will the CEO accept equities-only, or equities plus options explained in words? Who confirms from the signed agreement that options are excluded? | "Whether she accepts an equities-only paper release is not recorded" in [[11-unknowns-and-risks]] |
| F1.51 | REG | normal | R-REG-12 | Does the partnerships manager's statement close UNK-011 without the agreement text? What is TickerTalk's exposure if Brightwater fails? | "Brightwater carries every customer balance as money it owes its own customers, Kestrel carries none" in [[03-context-and-scope]] |
| F1.52 | REG | high | R-REG-16 | Has the partnerships manager confirmed in writing that an internal demo including the board is exempt? Does the review also apply to paper-only readers and to every lesson update? | "so a demo shown to outsiders is the case between the two and is not yet settled" in [[03-context-and-scope]] |
| F1.53 | REG | high | R-REG-17 | Is counsel's statement that lessons are education in writing? Who does the marketing review of promotions and shown results? | "Who reviews the marketing and the shown results is not recorded." in [[03-context-and-scope]] |
| F1.54 | REG | high | R-REG-18 | If Board demo is outside the runtime scope, who is responsible for the content review, the counsel review of shown results and the data used in the demo? | "calls Board demo the January build, outside the runtime scope" in [[11-unknowns-and-risks]] |
| F1.55 | REG | normal | R-REG-20 | Should CON-005 stay unsettled until the privacy lead rules on the opt-in and on what crosses to Coach? | "Until the mobile lead confirms, it is an assumption in CON-005." in [[11-unknowns-and-risks]] |
| F1.56 | REG | normal | R-REG-21 | Which regulatory answers (stock-list ruling, opt-in wording, content review, compliance ruling) gate FLO-001 and the release switch, and who owns each? | "How a release rolls back, and in what order readers get the coach, is not recorded." in [[concern-rollout]] |
| F1.57 | REG | high | new | Do the 24 lessons clear the consultant and Brightwater's review by March once a rejected item restarts the ten-day clock and two rounds are allowed? Who confirms the 15 February figure? | "so the 24 beta lessons would be cleared by 15 February, in time for the March beta" in [[concern-rollout]] |
| F1.58 | REG | high | new | With Brightwater declining the recommender role, is there any permitted route for customer-specific trade ideas? Who enforces that release one suggests none, and is the unknown really resolved? | "Staying out of release one is a plan." in [[11-unknowns-and-risks]] |
| F1.59 | REG | normal | new | Which dates are right: the mobile confirmation on 7 or 14 October, and Brightwater's reply on 9 October or 3 November? Who corrects SRC-12 and records the real date? | "Jordan Reyes's first-hand account that the mobile lead confirmed capacity on 14 October" in [[sources]] |
| F1.60 | OPS | normal | Q-OPS-03@CAP-001 | Does @coach-lead (not @sim-lead) own CAP-001, CAP-002 and CAP-004 after the change? If so, can the owner field and this page be corrected, with the Coach lead's own confirmation recorded? | "Coach's page names the product lead as owner for now, and no team is recorded to run it." in [[concern-ownership]] |
| F1.61 | OPS | normal | new | Should the ownership page be corrected to name Fieldnote Learning as lesson writer and the product lead as owner of the definition of ready, and then who owns the ready track after launch? | "Nobody is named yet for" in [[concern-ownership]] |
| F1.62 | OPS | normal | Q-OPS-03@CAP-003 | Which team owns the ready track and its grading rule after the change (product lead or Coach lead)? Should CAP-003 be updated to the agreed definition? | "What ”ready” means is not yet defined." in [[CAP-003-pass-the-ready-track]] |
| F1.63 | OPS | normal | new | Should the operations page be rewritten to state who runs Coach and TickerTalk out of hours, now that UNK-028, UNK-043 and UNK-049 are resolved? | "TickerTalk's own operations have not been examined." in [[concern-operations]] |
| F1.64 | OPS | normal | new | Who covers Coach, and the Brightwater sandbox it depends on, between now and 1 March, including the January demo? What are the sandbox's support hours? | "they will run Coach in business hours with an on-call rota from March" in [[concern-operations]] |
| F1.65 | OPS | high | new | How can 2,000 beta readers each get a sandbox account when Brightwater gives ten test accounts? Who at Brightwater (the integration QA engineer) can provide more, and by when? | "Coach opens a reader's sandbox paper account at their first practice trade." in [[11-unknowns-and-risks]] |
| F1.66 | OPS | high | R-OPS-17 | Who is the compliance consultant, what is their real sign-off throughput from 12 October to the March beta, and which forecast (two lessons a week, or five weeks per lesson) does the plan use? | "The product lead's own estimate is about five weeks per lesson" in [[11-unknowns-and-risks]] |
| F1.67 | OPS | high | R-OPS-17 | Who is the compliance consultant, who can get the written ruling by 13 October, and who in compliance owns the live-trading ruling? | "the written ruling, held by the compliance consultant (name not recorded)" in [[2026-10-09-answers-settle-unknowns]] |
| F1.68 | OPS | high | R-OPS-03 | Will the mobile lead confirm in writing, with a date, that two named engineers cover the coach screens, the opt-in check, contract tests and the beta rollout alongside TickerTalk itself? Which of 7 and 14 October is right? | "The mobile lead said on 7 October that two engineers can build it by March" in [[11-unknowns-and-risks]] |
| F1.69 | OPS | normal | R-OPS-03 | Is 14 October mobile's sign-off date, a confirmation date, or neither? Should the stale UNK-019 notes and SRC-12 be marked superseded? | "The product lead names @mobile-lead as the mobile lead and gives 14 October as the date it is done" in [[11-unknowns-and-risks]] |
| F1.70 | OPS | normal | R-OPS-16 | Who decides to start the March beta, who can switch it off or roll it back (mobile or Coach), and must the 1 March rota be confirmed live first? | "How a release rolls back, and in what order readers get the coach, is not recorded." in [[concern-rollout]] |
| F1.71 | OPS | normal | R-OPS-15 | Does the mobile team own any backend, or does the Coach team alone run Coach and the release switch? Who runs the release switch out of hours? | "its rollout is the coach's opt-in beta, owned by the mobile team" in [[concern-rollout]] |
| F1.72 | OPS | normal | R-OPS-19 | Who takes over Coach's running from the platform engineer after month one, and who reviews the observability, testing and security cells before the January demo? | "the Coach team runs it with the platform engineer's help for the first month" in [[11-unknowns-and-risks]] |
| F1.73 | OPS | high | Q-OPS-04@INI-001 | Which of the page's containers does each of the Coach lead's names mean, and who runs the Stock list and release switch? | "The page owns the container names, so the page's four stand and the mapping is not settled." in [[11-unknowns-and-risks]] |
| F1.74 | OPS | normal | Q-OPS-05@INI-001 | Is anything retired or replaced by this change? If not, should the plan say so explicitly? | "TickerTalk, the news app, changed to add the coach screens and to send Coach the reader ID" in [[03-context-and-scope]] |
| F1.75 | OPS | high | R-OPS-04 | Who is the final decider between the CEO and compliance, by what date, and does the year-one ban cover the March launch? | "where compliance and the CEO disagree the CEO decides once counsel has ruled" in [[01-goals]] |
| F1.76 | OPS | normal | R-OPS-13 | Which open unknowns and risks should move to named build-team people, and which stay with the product lead? | "The product lead owns most unknowns and every risk for now, because the compliance holder is not yet named." in [[11-unknowns-and-risks]] |
| F1.77 | OPS | normal | R-OPS-06 | Is training on watchlists planned at all, and who (the ML lead, privacy lead or product lead) would approve and run it? | "the product lead says that is a wish and not a committed step" in [[01-goals]] |
| F1.78 | OPS | normal | R-OPS-07 | Who decided that options are reading only in release one, who writes those lessons (Fieldnote?), and what is the route to Brightwater's per-customer options approval? | "Options are taught in release one as reading only, never paper-traded and with no trade screen" in [[11-unknowns-and-risks]] |
| F1.79 | OPS | normal | new | Is the lesson writer locked in or can either side leave on 30 days' notice, and what is the fallback if Fieldnote leaves before the 24 beta lessons are done? | "a contractor, now locked in, writes the lessons" in [[03-context-and-scope]] |
| F1.80 | OPS | normal | R-OPS-20 | Does the Coach lead confirm the grading rule and the first-practice-trade timing, and should the stale notes be removed? | "Claude's assumption, not confirmed: the account is opened at the reader's first paper order." in [[11-unknowns-and-risks]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| SRC-19 | - | exists | [[2026-10-09-answers-settle-unknowns#^c01]] |
| SRC-20 | - | exists | [[2026-10-09-answers-settle-unknowns#^c01]] |
| SRC-21 | - | exists | [[2026-10-09-answers-settle-unknowns#^c01]] |
| PTY-04 | - | fact | [[2026-10-09-answers-settle-unknowns#^c06]] |
| SRC-19 | - | fact | [[2026-10-09-answers-settle-unknowns#^c11]] |
| SRC-19 | - | fact | [[2026-10-09-answers-settle-unknowns#^c12]] |
| SRC-19 | - | fact | [[2026-10-09-answers-settle-unknowns#^c13]] |
| SRC-19 | - | fact | [[2026-10-09-answers-settle-unknowns#^c15]] |
| SRC-19 | - | fact | [[2026-10-09-answers-settle-unknowns#^c17]] |
| SRC-19 | - | fact | [[2026-10-09-answers-settle-unknowns#^c18]] |
| SRC-23 | - | exists | [[2026-10-09-answers-settle-unknowns#^c19]] |
| SRC-23 | - | fact | [[2026-10-09-answers-settle-unknowns#^c19]] |
| PTY-01 | - | fact | [[2026-10-09-answers-settle-unknowns#^c21]] |
| SRC-16 | - | fact | [[2026-10-09-answers-settle-unknowns#^c22]] |
| SRC-22 | - | exists | [[2026-10-09-answers-settle-unknowns#^c24]] |
| UNK-041 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-043 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-044 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-045 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-047 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-049 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-050 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-051 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-052 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-053 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-054 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-027 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-020 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-005 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-019 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-031 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-016 | open | resolved | [[2026-10-09-answers-settle-unknowns#^c27]] |
| UNK-055 | - | open | [[2026-10-09-answers-settle-unknowns#^c29]] |
| UNK-056 | - | open | [[2026-10-09-answers-settle-unknowns#^c33]] |
| UNK-019 | resolved | open | [[2026-10-09-answers-settle-unknowns#^c36]] |
| UNK-057 | - | open | [[2026-10-09-answers-settle-unknowns#^c43]] |
| UNK-058 | - | open | [[2026-10-09-answers-settle-unknowns#^c42]] |
| R-OPS-17 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c31]] |
| R-PTN-18 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c31]] |
| R-REG-11 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c32]] |
| Q-PTN-02@PTY-01 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-02@PTY-02 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-02@PTY-04 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-03@PTY-01 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-03@PTY-02 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-03@PTY-04 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-05@PTY-02 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-05@PTY-04 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-06@PTY-01 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-06@PTY-02 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| Q-PTN-06@PTY-04 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| R-FIN-10 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| R-DAT-09 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| R-FIN-22 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c33]] |
| R-PTN-19 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c34]] |
| R-OPS-21 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c34]] |
| R-REG-22 | - | unknown | [[2026-10-09-answers-settle-unknowns#^c36]] |
| R-OPS-03 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c36]] |
| Q-DAT-03@CON-001 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c39]] |
| Q-DAT-03@CON-002 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c39]] |
| Q-DAT-03@CON-003 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c39]] |
| Q-DAT-03@CON-004 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c39]] |
| Q-DAT-03@CON-005 | open | unknown | [[2026-10-09-answers-settle-unknowns#^c39]] |
| Q-OPS-03@CAP-* | - | unknown | [[2026-10-09-answers-settle-unknowns#^c40]] |
| Q-OPS-04@INI-001 | - | open | [[2026-10-09-answers-settle-unknowns#^c41]] |
| Q-REG-01@INI-001 | - | open | [[2026-10-09-answers-settle-unknowns#^c41]] |
| Q-REG-05@INI-001 | - | open | [[2026-10-09-answers-settle-unknowns#^c41]] |
| R-FIN-23 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-DAT-16 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-PTN-20 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-PTN-21 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-REG-23 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-REG-24 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-OPS-22 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-OPS-23 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-OPS-24 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
| R-OPS-25 | - | open | [[2026-10-09-answers-settle-unknowns#1. After the read-back, 2026-10-09]] |
