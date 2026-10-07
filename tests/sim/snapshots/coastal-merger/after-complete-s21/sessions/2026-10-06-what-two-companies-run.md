---
id: 2026-10-06-what-two-companies-run
type: session
title: "Discover: what the two companies run"
date: 2026-10-06
modes: [discover, dump]
status: closed
summary: Mapped ferry and rail systems today and wrote 7 new unknowns, among them the FERRYMASTER contract date and the cutover method. Confirmed two loyalty schemes held for customers, whose one-for-one merge is an open unknown.
---

# 2026-10-06 Discover: what the two companies run

## Captures

- [thought] (solution lead) "The counts and the runbook haven't come in yet, so I'll chase them when I call this afternoon." → keep: [[11-unknowns-and-risks#UNK-013 Customer counts per system|UNK-013]] (open) ^c01
- [thought] (solution lead) "The counts and the runbook haven't come in yet, so I'll chase them when I call this afternoon." → keep: [[11-unknowns-and-risks#UNK-014 FERRYMASTER people and docs|UNK-014]] (open) ^c02
- [thought] (claude, from SRC-02) SeaBook is the web booking engine, with a 99.9% availability target from May to September and round-the-clock on-call (SRC-02). → keep: [[03-context-and-scope#Ferry side today|context-and-scope]] (fact) ^c03
- [thought] (claude, from SRC-02) FERRYMASTER is a mainframe reservation system and the ledger of record (SRC-02). → keep: [[03-context-and-scope#Ferry side today|context-and-scope]] (fact) ^c04
- [thought] (claude, from SRC-02) The FERRYMASTER vendor contract needs 18 months' notice (SRC-02); its end date is UNK-021, not a fact. → keep: [[03-context-and-scope#Ferry side today|context-and-scope]] (fact) ^c05
- [thought] (claude, from SRC-02) Halyard CRM is used by the Kestrel Bay contact centre (SRC-02). → keep: [[03-context-and-scope#Ferry side today|context-and-scope]] (fact) ^c06
- [thought] (claude, from SRC-02) Tidepay takes card payments for web, contact centre and port kiosks (SRC-02). → keep: [[03-context-and-scope#Ferry side today|context-and-scope]] (fact) ^c07
- [thought] (claude, from SRC-02) Tidemiles earns 1 point per pound and 100 points redeem for 1 pound (SRC-02). → keep: [[03-context-and-scope#Ferry side today|context-and-scope]] (fact) ^c08
- [thought] (claude, from SRC-02) The ferry customer database holds about 1.2 million records, owner to be confirmed after the reorganisation (SRC-02). → keep: [[03-context-and-scope#Ferry side today|context-and-scope]] (fact) ^c09
- [thought] (claude, from SRC-02) A nightly file of package bookings goes to about 40 partner hotels (SRC-02). → keep: [[03-context-and-scope#Ferry side today|context-and-scope]] (fact) ^c10
- [thought] (claude, from SRC-04) RailCore is the vendor-hosted booking engine, vendor SLA 99.5%, support 08:00 to 18:00 on weekdays (SRC-04). → keep: [[03-context-and-scope#Rail side today|context-and-scope]] (assumption) ^c11
- [thought] (claude, from SRC-04) Northway ID is the login for every rail customer, emails unique (SRC-04). → keep: [[03-context-and-scope#Rail side today|context-and-scope]] (assumption) ^c12
- [thought] (claude, from SRC-04) Signal CRM is used in the Dunmere contact centre (SRC-04). → keep: [[03-context-and-scope#Rail side today|context-and-scope]] (assumption) ^c13
- [thought] (claude, from SRC-04) Northway Plus earns 5 points per pound (SRC-04). → keep: [[03-context-and-scope#Rail side today|context-and-scope]] (assumption) ^c14
- [thought] (claude, from SRC-04) Northway Assist handles assisted travel bookings (SRC-04). → keep: [[03-context-and-scope#Rail side today|context-and-scope]] (assumption) ^c15
- [thought] (claude, from SRC-04) Payments run through the RailCore gateway today, with a move to Tidepay planned for 2027 (SRC-04). → keep: [[03-context-and-scope#Rail side today|context-and-scope]] (assumption) ^c16
- [thought] (claude, from SRC-01) The CIO wants Northway ID to be the single identity for every group customer by next summer (SRC-01). → keep: [[03-context-and-scope#After|context-and-scope]] (assumption) ^c17
- [thought] (claude, from SRC-01) The CIO wants Tidemiles and Northway Plus combined (SRC-01). → keep: [[03-context-and-scope#After|context-and-scope]] (assumption) ^c18
- [thought] (solution lead) "that's Clash A and it's D4 for me, I need procurement to confirm which date is real because it changes the whole exit plan." → keep: [[11-unknowns-and-risks#UNK-021 FERRYMASTER contract end date|UNK-021]] (open) ^c19
- [thought] (solution lead) "Clash B is actually impossible. You can't merge schemes one for one when one earns 1 point per pound and the other earns 5." → keep: [[11-unknowns-and-risks#UNK-022 Loyalty points one for one|UNK-022]] (open) ^c20
- [thought] (solution lead) "Finance owns Clash B, not Marketing, because the redemption values are completely different and the money doesn't add up." → keep: [[11-unknowns-and-risks#UNK-022 Loyalty points one for one|UNK-022]] (open) ^c21
- [unknown] (solution lead) "15 honestly not sure without the appendix." → keep: [[11-unknowns-and-risks#UNK-023 Rail capability map appendix|UNK-023]] (open) ^c22
- [unknown] (solution lead) "are Halyard and Signal really different, or did I get wrong that the two call centres already share a CRM?" → keep: [[11-unknowns-and-risks#UNK-024 Halyard and Signal CRM overlap|UNK-024]] (open) ^c23
- [thought] (solution lead) Q-PTN-03@PTY-02, F1.24: "the FERRYMASTER contract date is already D4, so that one's non-negotiable" → keep: [[11-unknowns-and-risks#UNK-021 FERRYMASTER contract end date|UNK-021]] (open) ^c24
- [thought] (solution lead) R-DAT-01, F1.40: "I need the DPO named before we promise customers anything on the loyalty piece." → keep: [[11-unknowns-and-risks#UNK-010 Data Protection Officer|UNK-010]] (open) ^c25
- [thought] (solution lead) "I can't take all of these right now — I need the CIO and Ferry Ops answers first or I'm just working blind." → park: a deferral, the other review lines stay open in the ledger ^c26
- [thought] (solution lead) "Yes, add Ferry Ops to UNK-021 — they'll know the contract dates better than Procurement anyway, and I'm calling them this afternoon anyway. Better to ask once than twice." → keep: [[11-unknowns-and-risks#UNK-021 FERRYMASTER contract end date|UNK-021]] (open) ^c27
- [worry] (solution lead) "the four documents read like they were written by procurement and IT people, not by anyone who actually runs ferry or rail day to day." → keep: [[11-unknowns-and-risks#UNK-020 Others affected not in room|UNK-020]] (open) ^c28
- [worry] (solution lead) "The Kestrel Bay team, the port kiosks, the two FERRYMASTER people — nobody speaks for them. There's no voice saying "here's what we'd actually need to make this work"." → keep: [[11-unknowns-and-risks#UNK-020 Others affected not in room|UNK-020]] (open) ^c29
- [thought] (solution lead) "The systems list is all hardware and code, nothing on the staff who run it or know how to fix it when it breaks." → keep: [[11-unknowns-and-risks#UNK-025 Who runs each system|UNK-025]] (open) ^c30
- [unknown] (solution lead) "does anyone from Kestrel Bay move, does anyone at the mainframe shop have a job afterward?" → keep: [[11-unknowns-and-risks#UNK-026 People affected by retirements|UNK-026]] (open) ^c31
- [unknown] (solution lead) "If we're linking accounts next summer, how do we tell a million ferry customers to come and link, or do we do it silently at the back?" → keep: [[11-unknowns-and-risks#UNK-027 Customer cutover method|UNK-027]] (open) ^c32
- [worry] (solution lead) "the only people who know how to read FERRYMASTER are on their way out. That should be screaming from the page, but it's barely a line." → keep: [[11-unknowns-and-risks#UNK-014 FERRYMASTER people and docs|UNK-014]] (open) ^c33
- [idea] (claude) Ask one person each from Kestrel Bay, a port, Dunmere and the FERRYMASTER pair to write half a page on what they would need to make the link work, so the plan has the voices the documents lack. → park ^c34
- [idea] (claude) Add two columns to the systems list: who runs each system day to day, and who can fix it when it breaks, with how many people each. → park ^c35
- [idea] (claude) For each thing that retires, add one line on what happens to its people, with a named owner in each business. → park ^c36
- [idea] (claude) Treat cutover as three choices to compare: ask the customer at their next booking, match quietly and ask them to confirm, or have the contact centre link on a call. → park ^c37
- [wild] (claude) What if the two FERRYMASTER people walked through the system on video this month, as the first deliverable of the whole programme? → park ^c38
- [wild] (claude) What if Kestrel Bay staff did the first hundred links by hand, as a pilot that also shows what they would need? → park ^c39
- [thought] (solution lead) "The cutover piece can wait until we know what "one account" actually means." → keep: [[11-unknowns-and-risks#UNK-027 Customer cutover method|UNK-027]] (open) ^c40
- [thought] (solution lead) Q-FIN-01@INI-001: "Line 11 confirmed, the two schemes are held." → keep: [[11-unknowns-and-risks#Question ledger|Q-FIN-01@INI-001]] (answered) ^c41

## Reviews

### 1. After the read-back, 2026-10-06

- **Coverage:** FIN found 12, 3 dropped; DAT found 11, 1 dropped; PTN found 12, 4 dropped; REG found 9, 1 dropped; OPS found 7, 3 dropped
- **Dropped:** [FIN] the quote does not mention what the finding is about: Who funds the build and who carries the run cost? Which budget, and which company or business unit pays?; [FIN] the quote does not mention what the finding is about: What are the Northway Plus expiry and closure terms?; [FIN] the quote does not mention what the finding is about: Who sets and approves the Northway Plus conversion rate?; [DAT] it names R-DAT-04, which this vault does not owe and has no open reviewer question for; write new for a question of your own: Who is the controller of the ferry customer database now, and who can approve a change in its use?; [PTN] its quote "**Agreements:** none known" has fewer than 4 words, too few to show where it came from: Is there any agreement with the partner hotels covering the nightly booking file, and may that data be shared with a new owner or for a new purpose?; [PTN] its quote "- **Relationship:** partner" has fewer than 4 words, too few to show where it came from: Who holds the hotel arrangement, what notice does a change need, and who must give it?; [PTN] its quote "## Outside parties" has fewer than 4 words, too few to show where it came from: Are SeaBook, Northway ID, Tidepay, Halyard and Signal run under vendor or licence contracts, and what do they say on change of control, notice and data use?; [PTN] the quote does not mention what the finding is about: What do the Tidemiles and Northway Plus scheme terms say about changing earn and redeem rates, and who is the contracting party with the members?; [REG] its quote "## In scope" has fewer than 4 words, too few to show where it came from: Is any product, activity, data set or system in scope regulated or licensed, for example payments, loyalty balances held as money owed, or personal data, and by which regulator?; [OPS] the quote does not mention what the finding is about: Which unsupported beliefs does the plan rest on, and which one would change it most if it were wrong?; [OPS] it names R-OPS-01, which this vault does not owe and has no open reviewer question for; write new for a question of your own: What are the May freeze dates and scope, and does any build or cutover fit before 'next summer'?; [OPS] it names R-OPS-03, which this vault does not owe and has no open reviewer question for; write new for a question of your own: Is this one goal or three (CIO, CFO, Rail Product), who gains and loses under each, and who decides?
- **Merged:** [PTN] into F1.20: Are Halyard and Signal separate products under separate licences, or one shared contract?; [OPS] into F1.9: Who are the two FERRYMASTER experts, when do they leave, and what is documented or handed over?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | FIN | high | Q-FIN-01@INI-001 | Does anyone hold value for customers beyond the two loyalty schemes, such as wallets, vouchers or deposits? Which system or company holds each balance? | "**Holder:** not recorded: SRC-02 names Tidemiles as a ferry scheme but not which system keeps the balances" in [[03-context-and-scope]] |
| F1.2 | FIN | high | Q-FIN-03@SV-01 | Which entity carries the Tidemiles liability on its books, and how large is it? | "who carries the balances as money owed to customers?" in [[11-unknowns-and-risks]] |
| F1.3 | FIN | high | Q-FIN-03@SV-02 | Who carries the Northway Plus balances as money owed, and what is a point worth when redeemed? | "The Northway Plus redemption value is not recorded in any source." in [[11-unknowns-and-risks]] |
| F1.4 | FIN | normal | Q-FIN-04@SV-01 | How will a Tidemiles balance convert into the combined scheme, and what has already been promised to customers in the draft FAQ? | "The marketing draft (SRC-03) promises a one-for-one merge into a single balance." in [[11-unknowns-and-risks]] |
| F1.5 | FIN | normal | Q-FIN-04@SV-02 | How does a Northway Plus balance convert, given that its redemption value is unknown? | "**Northway Plus** (assumption, SRC-04): the rail loyalty scheme, 5 points per pound spent." in [[03-context-and-scope]] |
| F1.6 | FIN | normal | Q-FIN-05@SV-01 | What are the Tidemiles expiry and closure terms, and what happens to unspent balances if the scheme closes? | "**Owner:** not known yet: [[11-unknowns-and-risks#UNK-022 Loyalty points one for one\|UNK-022]]" in [[03-context-and-scope]] |
| F1.7 | FIN | normal | Q-FIN-06@SV-01 | Who sets the conversion rate, and who in Finance, Marketing or the CIO's office approves it? | "The solution lead holds that one for one cannot work on those rates and puts the question with Finance, not Marketing." in [[11-unknowns-and-risks]] |
| F1.8 | FIN | normal | R-FIN-02 | Who owns revenue and the customer database in each business after the reorganisation, and who signs off financial commitments? | "The solution lead believes Finance owns it. No source (c64, c84)." in [[11-unknowns-and-risks]] |
| F1.9 | FIN, OPS | high | R-FIN-03 | Who funds retention or documentation for the FERRYMASTER staff, and what does it cost if they leave before the link is built? | "Worry: they leave before anyone else can read the code, in a window of about three months." in [[11-unknowns-and-risks]] |
| F1.10 | FIN | high | new | Which contract end date is real, and what does it cost to exit or overlap? Has notice already been given or has it passed? | "March 2029 with 18 months' notice (the Harbourline systems list, SRC-02), or December 2027 (the CIO memo, SRC-01)" in [[11-unknowns-and-risks]] |
| F1.11 | FIN | normal | new | What is the rail redemption value, and can Finance size the combined liability before any one-for-one promise is made to customers? | "Finance owns Clash B, not Marketing, because the redemption values are completely different and the money doesn't add up." in [[2026-10-06-what-two-companies-run]] |
| F1.12 | FIN | normal | new | Who funds and carries the 2027 payments move, and does it overlap the identity and loyalty work? | "through the RailCore gateway today, with a move to Tidepay planned for 2027" in [[03-context-and-scope]] |
| F1.13 | DAT | high | Q-DAT-01@INI-001 | Will ferry customer data reach Northway Rail, the group identity service or any other new party, and which fields would go? | "Northway ID becomes the single identity for every group customer by next summer." in [[03-context-and-scope]] |
| F1.14 | DAT | high | Q-DAT-05@INI-001 | What was each kind of data collected for, and will the link or the combined scheme use it for anything else? | "What customer data do SeaBook and RailCore each hold, and what did their customers agree to?" in [[11-unknowns-and-risks]] |
| F1.15 | DAT | normal | Q-DAT-04@SV-01 | Which single system holds each customer's Tidemiles balance? | "not recorded: SRC-02 names Tidemiles as a ferry scheme but not which system keeps the balances" in [[03-context-and-scope]] |
| F1.16 | DAT | normal | Q-DAT-04@SV-02 | Which single system holds each customer's Northway Plus balance? | "not recorded: SRC-04 names Northway Plus as a rail scheme but not which system keeps the balances" in [[03-context-and-scope]] |
| F1.17 | DAT | high | R-DAT-01 | Who is the DPO, when will they be asked, and what must they see to approve the family-email handling? | "Who is the Data Protection Officer, have they been asked, and what do they need to see before they let the link go live given the family-email handling?" in [[11-unknowns-and-risks]] |
| F1.18 | DAT | high | R-DAT-02 | How will the link match the right person when emails are shared, and how will consent and marketing preferences follow each person? | "Ferry families share one email and every rail account needs a unique one: how are the two linked without asking a very large number of customers to change anything?" in [[11-unknowns-and-risks]] |
| F1.19 | DAT | normal | R-DAT-03 | Will the link hold a copy or use a third service, and who holds it, on what basis, and for how long? | "Does anything in the customer link need to read from or write to FERRYMASTER, or can it stay outside it?" in [[11-unknowns-and-risks]] |
| F1.20 | DAT, PTN | normal | new | Do Halyard and Signal share any customer data today, and if so under what basis? | "are Halyard and Signal really different, or did I get wrong that the two call centres already share a CRM?" in [[2026-10-06-what-two-companies-run]] |
| F1.21 | DAT | high | new | What personal data goes to the partner hotels in the nightly file, and under what agreement or lawful basis? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.22 | DAT | normal | new | Can the rail data claims (unique emails, Northway ID covering all rail customers) be confirmed from a record before matching is designed? | "Northway ID** (assumption, SRC-04): the login for every rail customer, and emails are unique." in [[03-context-and-scope]] |
| F1.23 | DAT | normal | new | Does the Tidepay move send rail customers' payment data to a new processor, and is it covered by their consent and contract? | "through the RailCore gateway today, with a move to Tidepay planned for 2027" in [[03-context-and-scope]] |
| F1.24 | PTN | high | Q-PTN-03@PTY-02 | Which end date is real, has notice been given or missed, who holds the contract, and what does exit or early termination cost? | "Which date is real for the end of the FERRYMASTER vendor contract: March 2029 with 18 months' notice (the Harbourline systems list, SRC-02), or December 2027 (the CIO memo, SRC-01)?" in [[11-unknowns-and-risks]] |
| F1.25 | PTN | high | Q-PTN-05@PTY-02 | Does the FERRYMASTER contract permit assignment or a change of control, and does the merger or any new owner trigger consent? | "the FERRYMASTER vendor contract, with 18 months' notice (SRC-02)." in [[03-context-and-scope]] |
| F1.26 | PTN | high | Q-PTN-05@PTY-03 | What does the RailCore vendor agreement say on assignment, change of control, term and notice, and is there an actual contract behind the slide? | "a vendor SLA for RailCore (SRC-04, assumption), and no other agreement known." in [[03-context-and-scope]] |
| F1.27 | PTN | high | Q-PTN-02@PTY-02 | May the vendors' systems and data be used for the cross-company link, and do the contracts limit use of the data for a new purpose? | "What customer data do SeaBook and RailCore each hold, and what did their customers agree to?" in [[11-unknowns-and-risks]] |
| F1.28 | PTN | high | Q-PTN-06@PTY-03 | How will the RailCore 99.5% weekday-hours SLA be reconciled with SeaBook's 99.9% round-the-clock target, and can the vendor contract change to match? | "The vendor SLA is 99.5%, and support runs 08:00 to 18:00 on weekdays." in [[03-context-and-scope]] |
| F1.29 | PTN | high | Q-PTN-01@INI-001 | Which systems, agreements, teams or payment flows change owner, operator or payer, and what happens to the RailCore gateway contract when payments move to Tidepay? | "Payments** (assumption, SRC-04): through the RailCore gateway today, with a move to Tidepay planned for 2027." in [[03-context-and-scope]] |
| F1.30 | PTN | high | R-PTN-02 | Are the two FERRYMASTER people employees or contractors, what notice binds them, and does the vendor provide any support for handover? | "Who are the two people who understand FERRYMASTER, are they leaving and when, and is any of it written down?" in [[11-unknowns-and-risks]] |
| F1.31 | PTN | normal | R-PTN-03 | Where does the Ferry Ops freeze come from, who can lift it, and which date is next summer? | "Does the May freeze start in May and end on a date, or end in May?" in [[11-unknowns-and-risks]] |
| F1.32 | PTN | high | R-PTN-04 | What do ferry and rail customer terms permit, and which legal entity is the contracting party on each side? | "The CIO wants Northway ID to be the single identity for every group customer by next summer (SRC-01)." in [[2026-10-06-what-two-companies-run]] |
| F1.33 | PTN | normal | R-PTN-05 | Who may approve changes to agreements, ownership or payment while the CIO is unreachable? | "who can decide in the CIO's place while they are unreachable?" in [[11-unknowns-and-risks]] |
| F1.34 | PTN | normal | new | Who can supply the actual RailCore contract and the appendix, to replace the slide as the source for the vendor terms? | "The appendix has not been read, so the rail side is incomplete." in [[11-unknowns-and-risks]] |
| F1.35 | REG | normal | Q-REG-01@INI-001 | Will any bundle, joint offer or package be sold across ferry and rail, and does the hotel package feed count as one? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.36 | REG | normal | Q-REG-05@INI-001 | If a journey spanning SeaBook and RailCore fails, who is liable to the customer, and how do the 99.9% round-the-clock and 99.5% weekday-hours service levels fit together? | "a vendor SLA for RailCore (SRC-04, assumption), and no other agreement known." in [[03-context-and-scope]] |
| F1.37 | REG | high | R-REG-01 | What consent or lawful basis covers the ferry data (about 1.2 million records) and the rail data, and does it allow linking or merging across the two businesses? | "What customer data do SeaBook and RailCore each hold, and what did their customers agree to?" in [[11-unknowns-and-risks]] |
| F1.38 | REG | high | R-REG-02 | Are Harbourline and Northway Rail one legal entity or two, and which is the controller for each customer data set? | "Its owner is to be confirmed after the reorganisation" in [[03-context-and-scope]] |
| F1.39 | REG | normal | R-REG-03 | Must the DPO review each linking option before one is chosen, rather than only before go-live? | "Who is the Data Protection Officer, have they been asked, and what do they need to see before they let the link go live" in [[11-unknowns-and-risks]] |
| F1.40 | REG | high | new | Is the one-for-one loyalty promise in the draft FAQ held back until Finance and Legal have settled the points value, the balance holder and the customers' liability position? | "The marketing draft (SRC-03) promises a one-for-one merge into a single balance." in [[11-unknowns-and-risks]] |
| F1.41 | REG | high | new | On what agreement and lawful basis does customer data go to the partner hotels, and would linking accounts change what they receive? | "a nightly file of package bookings goes to about 40 partner hotels." in [[03-context-and-scope]] |
| F1.42 | REG | high | new | Has notice on the FERRYMASTER contract been given or missed, and which end date is binding? | "Has notice already been given, or has it passed?" in [[11-unknowns-and-risks]] |
| F1.43 | REG | normal | new | Who is the payment processor and who is accountable for card data on each side before and after the 2027 move to Tidepay? | "with a move to Tidepay planned for 2027" in [[03-context-and-scope]] |
| F1.44 | OPS | normal | Q-OPS-04@INI-001 | Which systems, schemes, maps and teams do the same job on the ferry and rail sides, and are Halyard and Signal separate CRMs? | "are Halyard and Signal really different, or did I get wrong that the two call centres already share a CRM?" in [[2026-10-06-what-two-companies-run]] |
| F1.45 | OPS | high | Q-OPS-05@INI-001 | Which systems are being retired (FERRYMASTER, SeaBook, Halyard, Signal, the RailCore gateway), and who and what still depends on each? | "Its end date is disputed, so it is held in [[11-unknowns-and-risks#UNK-021 FERRYMASTER contract end date\|UNK-021]] and not stated here." in [[03-context-and-scope]] |
| F1.46 | OPS | normal | Q-OPS-06@INI-001 | Who are the Kestrel Bay, Dunmere, port, hotel-partner and Finance teams affected, and who speaks for each? | "Who else is affected by this and not yet in the room?" in [[11-unknowns-and-risks]] |
| F1.47 | OPS | high | new | Who covers out-of-hours support and failures for a linked ferry and rail journey during the May to September peak, given the SLA mismatch? | "The vendor SLA is 99.5%, and support runs 08:00 to 18:00 on weekdays." in [[03-context-and-scope]] |
| F1.48 | OPS | high | R-OPS-02 | Who is the Data Protection Officer, who owns the sign-off, and how do identity and consent follow a customer when the email rules conflict? | "Who is the Data Protection Officer, have they been asked, and what do they need to see before they let the link go live given the family-email handling?" in [[11-unknowns-and-risks]] |
| F1.49 | OPS | normal | new | Who confirms what actually runs on the rail side, and who owns Northway ID? | "The appendix has not been read, so the rail side is incomplete." in [[11-unknowns-and-risks]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| context-and-scope | - | fact | [[2026-10-06-what-two-companies-run#^c03]] |
| context-and-scope | - | fact | [[2026-10-06-what-two-companies-run#^c04]] |
| context-and-scope | - | fact | [[2026-10-06-what-two-companies-run#^c05]] |
| context-and-scope | - | fact | [[2026-10-06-what-two-companies-run#^c06]] |
| context-and-scope | - | fact | [[2026-10-06-what-two-companies-run#^c07]] |
| context-and-scope | - | fact | [[2026-10-06-what-two-companies-run#^c08]] |
| context-and-scope | - | fact | [[2026-10-06-what-two-companies-run#^c09]] |
| context-and-scope | - | fact | [[2026-10-06-what-two-companies-run#^c10]] |
| context-and-scope | - | assumption | [[2026-10-06-what-two-companies-run#^c11]] |
| context-and-scope | - | assumption | [[2026-10-06-what-two-companies-run#^c12]] |
| context-and-scope | - | assumption | [[2026-10-06-what-two-companies-run#^c13]] |
| context-and-scope | - | assumption | [[2026-10-06-what-two-companies-run#^c14]] |
| context-and-scope | - | assumption | [[2026-10-06-what-two-companies-run#^c15]] |
| context-and-scope | - | assumption | [[2026-10-06-what-two-companies-run#^c16]] |
| context-and-scope | - | assumption | [[2026-10-06-what-two-companies-run#^c17]] |
| context-and-scope | - | assumption | [[2026-10-06-what-two-companies-run#^c18]] |
| UNK-021 | - | open | [[2026-10-06-what-two-companies-run#^c19]] |
| UNK-022 | - | open | [[2026-10-06-what-two-companies-run#^c20]] |
| UNK-023 | - | open | [[2026-10-06-what-two-companies-run#^c22]] |
| PTY-01 | - | subject | [[2026-10-06-what-two-companies-run#^c10]] |
| PTY-02 | - | subject | [[2026-10-06-what-two-companies-run#^c05]] |
| PTY-03 | - | subject | [[2026-10-06-what-two-companies-run#^c11]] |
| SV-01 | - | subject | [[2026-10-06-what-two-companies-run#^c08]] |
| SV-02 | - | subject | [[2026-10-06-what-two-companies-run#^c14]] |
| UNK-024 | - | open | [[2026-10-06-what-two-companies-run#^c23]] |
| UNK-025 | - | open | [[2026-10-06-what-two-companies-run#^c30]] |
| UNK-026 | - | open | [[2026-10-06-what-two-companies-run#^c31]] |
| UNK-027 | - | open | [[2026-10-06-what-two-companies-run#^c32]] |
| Q-PTN-03@PTY-02 | - | unknown | [[2026-10-06-what-two-companies-run#^c24]] |
| Q-FIN-01@INI-001 | - | answered | [[2026-10-06-what-two-companies-run#^c41]] |
| R-DAT-01 | open | unknown | [[2026-10-06-what-two-companies-run#^c25]] |
| R-FIN-04 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-FIN-05 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-FIN-06 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-DAT-05 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-DAT-06 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-DAT-07 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-DAT-08 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-PTN-06 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-REG-04 | - | unknown | [[2026-10-06-what-two-companies-run#^c25]] |
| R-REG-05 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-REG-06 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-REG-07 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-OPS-04 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
| R-OPS-05 | - | open | [[2026-10-06-what-two-companies-run#1. After the read-back, 2026-10-06]] |
