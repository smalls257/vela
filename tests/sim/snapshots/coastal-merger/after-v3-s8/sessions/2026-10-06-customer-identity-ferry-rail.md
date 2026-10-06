---
id: 2026-10-06-customer-identity-ferry-rail
type: session
title: "Discover: customer identity ferry rail"
date: 2026-10-06
modes: [discover]
status: closed
summary: Took the ferry database owner and FERRYMASTER end date questions, ruled out vendor and hotel contract questions until Monday, and recorded the missing rail systems list as UNK-025.
---

# 2026-10-06 Discover: customer identity ferry rail

## Captures

- [thought] (claude, from SRC-01, confirmed by @sim-lead) The memo says nothing new should be built on FERRYMASTER. The retirement date that goes with it is not written: December 2027 clashes with March 2029 from SRC-02, held in UNK-019, and the lead rejected that date as an assumption in the earlier Discover. → keep: [[03-context-and-scope#Today|Today]] (assumption) ^c01
- [thought] (@sim-lead) "Yes—that's the critical gap." On line 6, the customer database owner being "to be confirmed". The lead needs the owner once they pick between A, B or C on Monday. → keep: [[11-unknowns-and-risks#UNK-022 Customer database owner|UNK-022]] (open) ^c02
- [worry] (@sim-lead) "'nothing lost' doesn't square with 1 vs 5 earning rates. That's the conversion problem." On the FAQ's one-for-one line. → keep: [[11-unknowns-and-risks#UNK-020 Loyalty combining rates|UNK-020]] (open) ^c03
- [unknown] (@sim-lead) "We need what they actually run today, not just a slide of where they're headed." There is no current rail systems list, and SRC-04 is a target. → keep: [[11-unknowns-and-risks#UNK-025 Current rail systems list|UNK-025]] (open) ^c04
- [thought] (@sim-lead) Lines 1 to 10 and 12 to 19 each confirmed with a yes; they are already on 03-context-and-scope from the earlier Discover. → drop: confirmation only, the lines are already on 03-context-and-scope ^c05
- [thought] (@sim-lead) R-DAT-06, R-REG-06: "I'll take the ferry database owner questions ... because that's the critical gap I need before anything else." Taken now: which legal entity controls the ferry customer database, and whether sharing it with rail needs new notice or consent. Held with UNK-022. → keep: [[11-unknowns-and-risks#Question ledger|R-DAT-06]] (unknown) ^c06
- [thought] (@sim-lead) R-OPS-04: "Take the FERRYMASTER contract date too ... since that changes the cost picture." Taken now: which end date governs, March 2029 with 18 months' notice or December 2027. Held with UNK-019. → keep: [[11-unknowns-and-risks#Question ledger|R-OPS-04]] (unknown) ^c07
- [thought] (@sim-lead) Ruled out for now: "Rule out everything that assumes we know whether ferry or rail are authorized to be moving. The vendor contracts and the rest of the partner stuff can wait until we know whether anybody's actually told them to hold off." Reason: the pick depends on UNK-011 and UNK-024, which the lead learns on Monday. Claude reads this as the vendor contract and partner questions (Q-PTN-02, Q-PTN-03, Q-PTN-05, Q-PTN-06, R-PTN-02, R-PTN-03, R-PTN-04, R-PTN-06, R-DAT-07, R-DAT-09 and the hotel feed lines); the lead is to confirm that list. → keep: [[11-unknowns-and-risks#Question ledger|Q-PTN-02@PTY-02]] (not-applicable) ^c08
- [worry] (@sim-lead) "if Monday shows ferry's got five people on this and nobody owns it, then all these contract questions become academic—I'm fire-fighting an unauthorized project, not designing options." Related to UNK-011 and UNK-024. → keep: [[11-unknowns-and-risks#UNK-011 Parallel builds by ferry and rail|UNK-011]] (open) ^c09
- [thought] (@sim-lead) "Record the missing rail systems list as UNK-025 if you haven't already." Already written as UNK-025 earlier in this session, ^c04. → drop: already written as UNK-025 from c04 ^c10

## Reviews

### 1. after the read-back, 2026-10-06

- **Coverage:** FIN found 16, 2 dropped; DAT found 17; PTN found 17, 1 dropped; REG found 11; OPS found 9, 2 dropped
- **Dropped:** FIN: its quote "### SV-01 Tidemiles" has fewer than 4 words, too few to show where it came from: What are the Tidemiles expiry and closure terms, and do the scheme terms allow them to change?; FIN: it names R-FIN-03, which this vault does not owe and has no open reviewer question for; write new for a question of your own: What are ferry and rail spending on account work now, and who would stop it or absorb the sunk cost?; PTN: it names R-PTN-01, which this vault does not owe and has no open reviewer question for; write new for a question of your own: Is the freeze written in a policy or agreement, who can waive it, and does it bind the vendor or contractors?; OPS: it names R-OPS-01, which this vault does not owe and has no open reviewer question for; write new for a question of your own: Is the May to September freeze written policy or a request, who set it, can it be waived, and does next summer fall inside it?; OPS: it names R-OPS-02, which this vault does not owe and has no open reviewer question for; write new for a question of your own: Who owns the initiative, who tells ferry and rail to stop their own builds, and who is on call for the new shared layer?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-02@INI-001 | Which budget holder funds the build, who funds the running cost afterwards, and does that cost sit with ferry (Kestrel Bay), rail (Dunmere) or the group? | "Running cost, licences and shared budgets such as mainframe processing." in [[concern-cost]] |
| F1.2 | FIN | high | Q-FIN-03@SV-01 | Which legal entity owes Tidemiles balances to customers, and what is the total outstanding in points and in pounds? | "- **Holder:** not known yet, see [[11-unknowns-and-risks#UNK-018 Loyalty balance holder\|UNK-018]]" in [[03-context-and-scope]] |
| F1.3 | FIN | high | Q-FIN-03@SV-02 | Which legal entity owes Northway Plus balances, and where is the balance actually held today? | "- **Owner:** not known yet, see [[11-unknowns-and-risks#UNK-018 Loyalty balance holder\|UNK-018]]" in [[03-context-and-scope]] |
| F1.4 | FIN | high | Q-FIN-04@SV-01 | What is a Northway Plus point worth on redemption, and how does each existing balance convert into the single balance without loss to either side or to customers? | "Tidemiles and Northway Plus are combined, one for one into a single balance. Assumption, SRC-01 and SRC-03" in [[03-context-and-scope]] |
| F1.5 | FIN | high | Q-FIN-04@SV-02 | If group Marketing's FAQ has promised customers nothing is lost, who bears the cost of the gap when the rates differ? | "'nothing lost' doesn't square with 1 vs 5 earning rates. That's the conversion problem." in [[2026-10-06-customer-identity-ferry-rail]] |
| F1.6 | FIN | normal | Q-FIN-05@SV-02 | Do the points expire, and what happens to a balance when a linked account closes or the schemes merge? | "### SV-02 Northway Plus" in [[03-context-and-scope]] |
| F1.7 | FIN | normal | Q-FIN-06@SV-01 | Who sets the Tidemiles to single-balance rate, and has finance or the CFO approved one for one? | "Tidemiles and Northway Plus points are combined one for one into a single balance next summer." in [[2026-10-06-what-two-companies-run]] |
| F1.8 | FIN | normal | Q-FIN-06@SV-02 | Who approves the Northway Plus conversion rate, and who funds the difference if one for one is wrong? | "What is a Northway Plus point worth on redemption, which rate wins, and who owes the difference to customers?" in [[11-unknowns-and-risks]] |
| F1.9 | FIN | high | R-FIN-05 | What does early exit from the FERRYMASTER contract cost, who pays it, and by what date must notice be given if the 18-month period holds? | "If the contract runs to March 2029, retiring in December 2027 means leaving early, and the notice date matters." in [[11-unknowns-and-risks]] |
| F1.10 | FIN | high | R-FIN-01 | What does each want, who holds the budget, and which of the options does each gain or lose from? | "What do the CFO and the Rail Product director each want from this, and how do they differ?" in [[11-unknowns-and-risks]] |
| F1.11 | FIN | normal | R-FIN-02 | What does parallel running cost per month, and does the mandate's case rest on savings or on revenue? | "If the CIO moves on or next summer slips to autumn, how long do both systems run in parallel, and who carries that?" in [[11-unknowns-and-risks]] |
| F1.12 | FIN | normal | R-FIN-04 | What would a pilot that leaves FERRYMASTER untouched cost and who pays, compared with a delay past the freeze? | "No change inside FERRYMASTER in that window" in [[02-constraints]] |
| F1.13 | FIN | normal | R-FIN-06 | Who funds the rail payments move to Tidepay, and is it inside or outside this initiative's budget? | "RailCore's own gateway takes payments today, with a move to Tidepay planned for 2027." in [[03-context-and-scope]] |
| F1.14 | FIN | high | Q-FIN-01@INI-001 | Which system holds each scheme's balance, and does anyone hold vouchers, credits or deposits for customers? | "Which system holds their balances: FERRYMASTER, a separate CRM, or the loyalty platform itself? Who owes the balances to customers, and what happens to them if accounts are linked?" in [[11-unknowns-and-risks]] |
| F1.15 | FIN | normal | new | What are the RailCore contract term, exit cost and the cost of out-of-hours support, and who holds the contract? | "- **Agreements:** the RailCore vendor service level (SRC-04)." in [[03-context-and-scope]] |
| F1.16 | FIN | normal | new | Can a current rail systems list and scheme terms be obtained before any liability is sized? | "every rail line is a plan, not a fact" in [[11-unknowns-and-risks]] |
| F1.17 | DAT | high | Q-DAT-01@INI-001 | Will ferry customer data (and loyalty and assisted-travel data) go to Northway ID, rail or group Marketing, and who has authority to allow that? | "Northway ID becomes the single identity for every customer of the group." in [[03-context-and-scope]] |
| F1.18 | DAT | high | Q-DAT-05@INI-001 | Is cross-brand matching and a combined loyalty balance a purpose beyond the original collection, and what lawful basis or consent covers it? | "What did they agree to when they signed up? Nobody has asked them." in [[11-unknowns-and-risks]] |
| F1.19 | DAT | normal | Q-DAT-04@SV-01 | Which single system is the record of each customer's Tidemiles balance? | "- **Holder:** not known yet, see [[11-unknowns-and-risks#UNK-018 Loyalty balance holder\|UNK-018]]" in [[03-context-and-scope]] |
| F1.20 | DAT | normal | Q-DAT-04@SV-02 | Which single system is the record of each customer's Northway Plus balance, and can a current rail systems list be obtained? | "Which system holds the balances is not known." in [[03-context-and-scope]] |
| F1.21 | DAT | high | R-DAT-02 | For each system, what personal data, consents and preferences does it hold, and which is the record? | "which holds customer records, logins or payment details? Who owns each?" in [[11-unknowns-and-risks]] |
| F1.22 | DAT | high | R-DAT-01 | What is the matching key between ferry and rail customers, what lawful basis allows matching, and must customers opt in? | "Northway ID is used for every customer login, and emails are unique. Assumption, SRC-04" in [[03-context-and-scope]] |
| F1.23 | DAT | normal | R-DAT-03 | What notice or consent did each customer base receive, and will customers be told or asked before linking? | "How many ferry and rail customers want their accounts merged, and what did they agree to when they signed up? Nobody has asked them." in [[11-unknowns-and-risks]] |
| F1.24 | DAT | high | R-DAT-06 | Which legal entity is the controller of the ferry customer database, and who can authorise sharing it with rail? | "Who owns the ferry customer database after the reorganisation? SRC-02 says to be confirmed." in [[11-unknowns-and-risks]] |
| F1.25 | DAT | high | R-DAT-07 | What personal data is in the hotel feed, under what terms, and does it survive the change of owner and of identity? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.26 | DAT | high | R-DAT-10 | Does Northway Assist hold health or accessibility data, and may it be linked to a shared identity? | "Northway Assist handles assisted travel bookings. Assumption, SRC-04" in [[03-context-and-scope]] |
| F1.27 | DAT | normal | R-DAT-08 | Will stored card or payment data move between the RailCore gateway and Tidepay, and who is accountable? | "RailCore's own gateway takes payments today, with a move to Tidepay planned for 2027." in [[03-context-and-scope]] |
| F1.28 | DAT | normal | R-DAT-09 | Do the RailCore and FERRYMASTER contracts carry data-processing terms, and do they permit a new party or purpose? | "- **Agreements:** the RailCore vendor service level (SRC-04)." in [[03-context-and-scope]] |
| F1.29 | DAT | normal | R-DAT-11 | What member data moves in the loyalty merger, and do the scheme terms allow it? | "Tidemiles and Northway Plus are combined, one for one into a single balance." in [[03-context-and-scope]] |
| F1.30 | DAT | normal | R-DAT-05 | Who will fill in the data concern, and by when? | "\| App \| State \| Why \|" in [[concern-data]] |
| F1.31 | DAT | normal | R-DAT-04 | May live or copied FERRYMASTER data be used for design or test, and under what controls? | "Does ”one account” need any change inside FERRYMASTER, or can it be done from outside by reading from it or sitting in front of it?" in [[11-unknowns-and-risks]] |
| F1.32 | DAT | normal | new | What customer data do Halyard and Signal hold, and will it be linked, moved or migrated under the single identity? | "The rail side runs a different CRM, Signal, see below" in [[03-context-and-scope]] |
| F1.33 | DAT | normal | new | Can a current rail systems list be obtained showing what personal data rail holds and where? | "The only rail source is SRC-04, a slide of the target architecture, so every rail line is a plan, not a fact." in [[11-unknowns-and-risks]] |
| F1.34 | PTN | high | Q-PTN-01@INI-001 | Which system, agreement, team or payment arrangement changes owner, operator or payer under this initiative, and which stays as it is? | "Who owns it after the reorganisation is not known" in [[03-context-and-scope]] |
| F1.35 | PTN | high | Q-PTN-02@PTY-02 | Does the FERRYMASTER vendor contract allow its data to be shared with, or used by, rail or a new customer layer? | "the FERRYMASTER vendor contract. Its end date and notice period are in dispute" in [[03-context-and-scope]] |
| F1.36 | PTN | high | Q-PTN-02@PTY-03 | Does the RailCore vendor contract allow data sharing with a new owner or user? Who holds the contract and can the lead obtain it? | "the RailCore vendor service level (SRC-04)" in [[03-context-and-scope]] |
| F1.37 | PTN | normal | Q-PTN-03@PTY-03 | Who holds the RailCore contract, what is its term, and what would changing or leaving it cost? | "the RailCore vendor service level (SRC-04)" in [[03-context-and-scope]] |
| F1.38 | PTN | high | Q-PTN-05@PTY-02 | Do the FERRYMASTER and RailCore contracts allow assignment, or need consent or notice, on the merger or a reorganisation of the contracting entity? | "Kestrel Bay and Dunmere merged three months ago, and ferry and rail operations are still separate." in [[03-context-and-scope]] |
| F1.39 | PTN | high | Q-PTN-05@PTY-03 | Can the RailCore contract be assigned or change control, and who must consent? | "RailCore is the booking engine, hosted by its vendor, with a vendor service level and support on weekdays in office hours. Assumption, SRC-04 (a slide)" in [[03-context-and-scope]] |
| F1.40 | PTN | high | Q-PTN-06@PTY-02 | Which end date governs the FERRYMASTER contract? Who gives notice, and what is the last date for notice to meet a December 2027 retirement? | "March 2029 with an 18-month notice period (SRC-02, Harbourline systems list), or December 2027 (SRC-01, CIO memo)" in [[11-unknowns-and-risks]] |
| F1.41 | PTN | normal | Q-PTN-06@PTY-03 | What notice does RailCore's vendor need for a change to the contract or gateway, and who gives it? | "RailCore's own gateway takes payments today, with a move to Tidepay planned for 2027." in [[03-context-and-scope]] |
| F1.42 | PTN | high | R-PTN-02 | Who supplies and owns SeaBook, Tidepay, Halyard and Signal, and what do their contracts say about access, change, notice and exit? Should each be added as an outside party? | "**Systems:** Ferry runs SeaBook and FERRYMASTER and rail runs RailCore, with separate customer databases and logins." in [[03-context-and-scope]] |
| F1.43 | PTN | normal | R-PTN-03 | Do the FERRYMASTER and SeaBook contracts permit read access, a copy of data or a front layer without the supplier's consent? | "Does ”one account” need any change inside FERRYMASTER, or can it be done from outside by reading from it or sitting in front of it?" in [[11-unknowns-and-risks]] |
| F1.44 | PTN | normal | R-PTN-04 | Which legal entity holds each system contract and customer relationship, and do any intercompany arrangements need to change? | "Which of Kestrel Bay and Dunmere is the ferry company and which the rail company, and who leads each?" in [[11-unknowns-and-risks]] |
| F1.45 | PTN | normal | R-PTN-06 | Is 'next summer' tied to any contract or external commitment, and where is the mandate in writing? | "To fetch: the CIO's mandate in writing, held by the CIO's office." in [[11-unknowns-and-risks]] |
| F1.46 | PTN | normal | new | Do the hotel agreements exist, and do they cover the nightly feed? Is it safe to treat them as out of scope when ownership and identity change? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.47 | PTN | high | new | Who will confirm the contract term with the vendor, and what is the cost of early exit or of running to 2029? | "If the contract runs to March 2029, retiring in December 2027 means leaving early, and the notice date matters." in [[11-unknowns-and-risks]] |
| F1.48 | PTN | normal | new | What contracts govern the RailCore gateway and Tidepay, and what consent or notice does the move to Tidepay need? | "RailCore's own gateway takes payments today, with a move to Tidepay planned for 2027." in [[03-context-and-scope]] |
| F1.49 | PTN | high | new | What does the RailCore vendor service level commit to, and would the vendor extend it to out-of-hours support? | "What service level applies to a joint ferry and rail journey, when SeaBook has round-the-clock on-call and RailCore support runs only in weekday office hours?" in [[11-unknowns-and-risks]] |
| F1.50 | PTN | normal | new | Can the lead get a current rail systems and contracts list before the PTN questions are treated as answered? | "so every rail line is a plan, not a fact" in [[11-unknowns-and-risks]] |
| F1.51 | REG | normal | Q-REG-01@INI-001 | Will customers buy a single ticket, bundle or joint offer that spans ferry and rail, or only see a combined view? | "What does ”one journey” mean: one ticket for a ferry leg plus a rail leg, one booking flow, or one trip view after the fact?" in [[11-unknowns-and-risks]] |
| F1.52 | REG | normal | Q-REG-02@INI-001 | Which regulators or licences apply to ferry operations, rail operations, payments, loyalty value and assisted travel, and does the change touch any of them? | "Northway Assist handles assisted travel bookings. Assumption, SRC-04" in [[03-context-and-scope]] |
| F1.53 | REG | normal | Q-REG-05@INI-001 | If a joint journey fails on one leg, which company and which contract terms make it liable to the customer, and does the vendor service level back that up? | "What service level applies to a joint ferry and rail journey, when SeaBook has round-the-clock on-call and RailCore support runs only in weekday office hours?" in [[11-unknowns-and-risks]] |
| F1.54 | REG | high | R-REG-01 | Is the customer's contract for a combined account or journey with one legal entity or two, and which entity is it? | "Which of Kestrel Bay and Dunmere is the ferry company and which the rail company, and who leads each?" in [[11-unknowns-and-risks]] |
| F1.55 | REG | high | R-REG-02 | What do the current ferry and rail terms and privacy notices allow, and must customers be told or asked before their accounts are linked under Northway ID? | "How many ferry and rail customers want their accounts merged, and what did they agree to when they signed up? Nobody has asked them." in [[11-unknowns-and-risks]] |
| F1.56 | REG | high | R-REG-04 | Which entity owes each balance, what do the scheme terms say about changes, and who bears the cost of the conversion difference? | "Tidemiles and Northway Plus are combined, one for one into a single balance. Assumption, SRC-01 and SRC-03" in [[03-context-and-scope]] |
| F1.57 | REG | high | R-REG-05 | What does the FERRYMASTER contract say about early exit, notice and liability, which end date is right, and has the notice window already closed? | "If the contract runs to March 2029, retiring in December 2027 means leaving early, and the notice date matters." in [[11-unknowns-and-risks]] |
| F1.58 | REG | high | R-REG-06 | Which legal entity is the data controller of the ferry database, and does sharing it with rail or matching it to Northway ID need new notice or consent? | "Who owns it after the reorganisation is not known" in [[03-context-and-scope]] |
| F1.59 | REG | normal | R-REG-07 | Do payment rules or assisted-travel duties constrain the Tidepay move or the shared identity, and who is accountable for them? | "RailCore's own gateway takes payments today, with a move to Tidepay planned for 2027." in [[03-context-and-scope]] |
| F1.60 | REG | normal | new | Can a current rail systems and obligations list be obtained before any regulatory conclusion is drawn about rail? | "so every rail line is a plan, not a fact" in [[11-unknowns-and-risks]] |
| F1.61 | REG | normal | new | What do the hotel package terms and the feed's data-sharing basis say, and does a cross-party package create liability toward customers that the identity change affects? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.62 | OPS | normal | Q-OPS-04@INI-001 | Which of the duplicated systems, schemes and CRMs (SeaBook and FERRYMASTER, Halyard and Signal, Tidemiles and Northway Plus, Tidepay and the RailCore gateway, the two logins) will survive, and who decides? | "The rail side runs a different CRM, Signal, see below" in [[03-context-and-scope]] |
| F1.63 | OPS | high | Q-OPS-05@INI-001 | What depends on FERRYMASTER today (ledger, balances, hotel feed, SeaBook, contact centres), and what has to move before it is retired? | "nothing new should be built on it." in [[03-context-and-scope]] |
| F1.64 | OPS | normal | Q-OPS-06@INI-001 | Who is affected but not yet in the room (contact centres, Northway Assist, kiosk staff, hotels, Harbourline IT operations), and who speaks for each? | "Northway Assist handles assisted travel bookings. Assumption, SRC-04" in [[03-context-and-scope]] |
| F1.65 | OPS | high | R-OPS-03 | What identity, balance and preferences must follow a customer across SeaBook, FERRYMASTER and RailCore, and who covers failures when one side is frozen or down or RailCore support is closed? | "How this fits SeaBook's round-the-clock cover is in" in [[03-context-and-scope]] |
| F1.66 | OPS | high | R-OPS-04 | Which end date governs, who confirms it with the vendor, and by when must notice be given? | "SRC-02 owns the contract term; SRC-01 states the retirement date. Neither is picked." in [[11-unknowns-and-risks]] |
| F1.67 | OPS | high | R-OPS-05 | Who runs the matching of ferry records to Northway IDs, how are shared or missing emails handled, and who owns the ferry database meanwhile? | "Who owns it after the reorganisation is not known" in [[03-context-and-scope]] |
| F1.68 | OPS | high | R-OPS-06 | Which team runs the combined balance and the Tidepay move, and is the 2027 move inside this initiative's scope? | "RailCore's own gateway takes payments today, with a move to Tidepay planned for 2027." in [[03-context-and-scope]] |
| F1.69 | OPS | normal | new | Can a current rail systems list be obtained before any operating plan is made, and who owns it? | "Rail booking:** RailCore is the booking engine, hosted by its vendor" in [[03-context-and-scope]] |
| F1.70 | OPS | normal | Q-OPS-07@INI-001 | Which other unsupported beliefs (parallel builds, a blocking director, source currency after the merger) does the plan rest on, and which would change it most if wrong? | "Defer everything else until we know what 'one account' means" in [[2026-10-06-what-two-companies-run]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| context-and-scope | - | assumption | [[2026-10-06-customer-identity-ferry-rail#^c01]] |
| UNK-025 | - | open | [[2026-10-06-customer-identity-ferry-rail#^c04]] |
| R-DAT-06 | open | unknown | [[2026-10-06-customer-identity-ferry-rail#^c06]] |
| R-REG-06 | open | unknown | [[2026-10-06-customer-identity-ferry-rail#^c06]] |
| R-OPS-04 | open | unknown | [[2026-10-06-customer-identity-ferry-rail#^c07]] |
| Q-PTN-06@PTY-02 | - | unknown | [[2026-10-06-customer-identity-ferry-rail#^c07]] |
| Q-PTN-02@PTY-02 | - | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| Q-PTN-02@PTY-03 | - | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| Q-PTN-03@PTY-03 | - | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| Q-PTN-05@PTY-02 | - | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| Q-PTN-05@PTY-03 | - | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| Q-PTN-06@PTY-03 | - | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-PTN-02 | open | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-PTN-03 | open | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-PTN-04 | open | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-PTN-06 | open | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-DAT-07 | open | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-DAT-09 | open | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-FIN-07 | - | open | [[2026-10-06-customer-identity-ferry-rail#1. after the read-back, 2026-10-06]] |
| R-FIN-08 | - | unknown | [[2026-10-06-customer-identity-ferry-rail#^c04]] |
| R-DAT-12 | - | open | [[2026-10-06-customer-identity-ferry-rail#1. after the read-back, 2026-10-06]] |
| R-DAT-13 | - | unknown | [[2026-10-06-customer-identity-ferry-rail#^c04]] |
| R-PTN-07 | - | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-PTN-08 | - | unknown | [[2026-10-06-customer-identity-ferry-rail#^c07]] |
| R-PTN-09 | - | open | [[2026-10-06-customer-identity-ferry-rail#1. after the read-back, 2026-10-06]] |
| R-PTN-10 | - | open | [[2026-10-06-customer-identity-ferry-rail#1. after the read-back, 2026-10-06]] |
| R-PTN-11 | - | unknown | [[2026-10-06-customer-identity-ferry-rail#^c04]] |
| R-REG-08 | - | unknown | [[2026-10-06-customer-identity-ferry-rail#^c04]] |
| R-REG-09 | - | not-applicable | [[2026-10-06-customer-identity-ferry-rail#^c08]] |
| R-OPS-07 | - | unknown | [[2026-10-06-customer-identity-ferry-rail#^c04]] |
