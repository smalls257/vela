---
id: 2026-10-12-desk-agent-epics
type: session
title: "Epics: Desk Agent team"
date: 2026-10-12
modes: [epics, shape, grill, requirements]
status: closed
summary: Cut the Desk Agent team's work into four epics. Confirmed 9 criteria across the switch-on and digest epics, and wrote the rule for an unconfirmed withdrawal. All four epics stay draft.
---

# 2026-10-12 Epics: Desk Agent team

## Captures

- [decision-input] (@sim-lead, Sim Lead) "Cut C. Keeps the pilot clean and the gated work in one place, and you're right that it maps to the release page. Four epics is fine." The Desk Agent team's epics are cut by flow with transcripts separate: switch on and withdraw, the morning digest, the prep note, and reading existing Teams transcripts. → keep: [[EPC-032-switch-on-and-withdraw|EPC-032]] (draft) ^c01

- [thought] (claude) Rejected cut A, two epics by capability: the showing epic would carry about 15 behaviours plus the agent's shares of writing and consent, far past seven criteria, so it would be split anyway. → park ^c02

- [thought] (claude) Rejected cut B, three epics by flow: reading existing Teams transcripts would be spread across the digest and prep epics, and transcripts are on no release, gated by the CISO review of 4 December, so the pilot epics would carry a gated piece. → park ^c03

- [decision-input] (@sim-lead, Sim Lead) "Agenda confirmed. Take 1 and 4 as you said. Leave the others in the ledger—3's waiting on the DPO, and 2, 5 are blocker-level items the leads own." Agenda for EPC-032 confirmed: six criteria one at a time, then the read-back. Taken now: whether the consent choice leaves the laptop (R-OPS-14) and what happens when a withdrawal is not confirmed (F1.13). The other review questions stay open in the ledger. → park ^c04

- [decision-input] (@sim-lead, Sim Lead) "Yes. The choice and withdrawal carry identity and consent state, not text—that squares with CST-003. Add the sentence so a tester can check it." R-OPS-14: the consent choice and the withdrawal leave the laptop for Consent and identity and hold no meeting text, so CST-003 does not bar them. Criterion 2 of EPC-032 gains the sentence "What is sent holds the person's sign-in, the source and the date, and no meeting text." The agent page's line that it sends nothing off the laptop is left for the Grill on that app. → keep: [[11-unknowns-and-risks#Question ledger|R-OPS-14]] (answered) ^c05

- [decision-input] (@sim-lead, Sim Lead) "Option 1. A person believing they've withdrawn when they haven't is a real failure—it needs to be a requirement with a test. Write it once and cite it." F1.13: the behaviour when a withdrawal is not confirmed is written once as a requirement on CAP-005, then allocated, and EPC-032 criterion 5 cites it. Claude's recommended wording, not yet agreed: Heron stops reading for that person at once, deletes what it holds for them, tells them the withdrawal is not yet recorded, and keeps trying to send it. → keep: [[CAP-005-record-persons-consent#CAP-005.FR2 Stop reading when a withdrawal is not confirmed|CAP-005.FR2]] (assumption) ^c06

- [decision-input] (@sim-lead, Sim Lead) "Yes. It matches what I decided on the UI—both choices now so transcripts have no friction when they land. F1.1 stays in the ledger and the pilot will show whether consent taken in February is still valid when reading starts later. Criterion 1 is right." EPC-032 criterion 1 confirmed as written. F1.1 stays open in the ledger. → keep: [[EPC-032-switch-on-and-withdraw|EPC-032]] (draft) ^c07

- [decision-input] (@sim-lead, Sim Lead) "Yes. Per-source question's in the contract's Grill—doesn't change this. Criterion 2 is right." EPC-032 criterion 2 confirmed as written, with the sentence added in ^c05. Whether the record-consent contract carries a per-source choice stays for that contract's Grill. → keep: [[EPC-032-switch-on-and-withdraw|EPC-032]] (draft) ^c08

- [decision-input] (@sim-lead, Sim Lead) "Yes. Switch-on's clear—if the choice doesn't stick, read nothing and tell them. When they come back online or Consent and identity's working, they can try again. Criterion 3 is right." EPC-032 criterion 3 confirmed as written. The person trying again later is not written into the criterion, because no requirement holds it. → keep: [[EPC-032-switch-on-and-withdraw|EPC-032]] (draft) ^c09

- [decision-input] (@sim-lead, Sim Lead) "Yes. Default-safe—if they haven't switched it on, nothing happens. Criterion 4 is right." EPC-032 criterion 4 confirmed as written. → keep: [[EPC-032-switch-on-and-withdraw|EPC-032]] (draft) ^c10

- [decision-input] (@sim-lead, Sim Lead) "Yes. Deletion's the core—once they withdraw, they see nothing and we hold nothing. Legal answers whether it's a client record. Criterion 6 is right." EPC-032 criterion 6 confirmed as written. F1.7 (deleting a digest that may be a client record) stays open with legal counsel. → keep: [[EPC-032-switch-on-and-withdraw|EPC-032]] (draft) ^c11

- [decision-input] (@sim-lead, Sim Lead) "Agenda confirmed. Leave F1.4 in the ledger—it's about whether the Summariser's live in February and whether CST-003 blocks sending calendar entries, which is a gate the CISO and operations own. The criterion itself is clear; whether it runs on the pilot date is a different question." Agenda for EPC-033 confirmed: five criteria one at a time, then the read-back. F1.4 stays open in the ledger. → park ^c12

- [decision-input] (@sim-lead, Sim Lead) "Yes. No mail, no documents—that's the line we hold. Criterion 1 is right." EPC-033 criterion 1 confirmed as written. → keep: [[EPC-033-morning-digest|EPC-033]] (draft) ^c13

- [decision-input] (@sim-lead, Sim Lead) "Yes. Agent sends raw data and attendees, Summariser does the work. F1.4's the gate question, not this one. Criterion 2 is right." EPC-033 criterion 2 confirmed as written. F1.4 stays open in the ledger. → keep: [[EPC-033-morning-digest|EPC-033]] (draft) ^c14

- [decision-input] (@sim-lead, Sim Lead) "Yes. Most people see it late because the laptop's asleep—that's the real behaviour. Product owner answers by 29 October whether they meant something else. Criterion 3 is right." EPC-033 criterion 3 confirmed as written. It rests on UNK-073, which stays open with the product owner, ask by 2026-10-29. → keep: [[EPC-033-morning-digest|EPC-033]] (draft) ^c15

- [decision-input] (@sim-lead, Sim Lead) "Yes. By noon a morning digest is stale. Criterion 4 is right." EPC-033 criterion 4 confirmed as written. It rests on UNK-073, which stays open. → keep: [[EPC-033-morning-digest|EPC-033]] (draft) ^c16

## Agenda

- EPC-032: GATE-3 confirmed yes, status open
- EPC-033: GATE-3 confirmed yes, status open

## Reviews

### 1. On the agenda: EPC-032, 2026-10-12

- **Coverage:** FIN skipped (nothing in scope); DAT found 4, 8 dropped; PTN skipped (nothing in scope); REG found 4, 1 dropped; OPS found 6
- **Dropped:** DAT: eight findings named R-DAT-13, R-DAT-15, R-DAT-11, R-DAT-02, R-DAT-12, R-DAT-08, R-DAT-14 and R-DAT-07, which this vault does not owe and has no open reviewer question for; REG: one finding whose quote does not mention what it is about (what stops a Frankfurt person from being offered the switch-on)
- **Merged:** [REG] into F1.2: Can a person withdraw one source (transcripts) and keep the other, and which criterion says how that is sent to Consent and identity?

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | DAT | high | new | Should the February pilot offer the transcripts choice at all? If it does, will a consent given then be valid for reading that starts in a later release under a notice that is not yet written? | "they are offered calendar entries and Teams transcripts as two separate choices" in [[EPC-032-switch-on-and-withdraw]] |
| F1.2 | DAT, REG | normal | new | Can a person withdraw one source only? If so, what happens to the other source, and does withdrawing calendar entries also end transcript consent? | "When a person switches Heron off, the withdrawal is sent to Consent and identity over the record-consent contract" in [[EPC-032-switch-on-and-withdraw]] |
| F1.3 | DAT | normal | new | Which team and epic keeps the consent record, including what is kept after a withdrawal, given that nobody is yet recorded as building Consent and identity? | "Keeping the record of who agreed to what: Consent and identity's epic, not this team's." in [[EPC-032-switch-on-and-withdraw]] |
| F1.4 | DAT | high | new | Does the Summariser run on the laptop or off it? If off it, does the pilot's sending of calendar entries wait on the CISO outcome of 4 December and on the data list? | "sends the entries with each meeting's attendees and names no one itself" in [[EPC-033-morning-digest]] |
| F1.5 | REG | normal | R-REG-12 | Who asks the works council whether it votes in December, by what date, and what is the fallback pilot date if it declines or defers? | "The solution lead is not sure which it is and has not asked the council. If it votes, that is another gate on 2 February 2027." in [[11-unknowns-and-risks]] |
| F1.6 | REG | high | new | Should EPC-032's rollout notes list every gate on the February date (CISO outcome, registration review, works council, impact assessment, lawful basis), and which of them blocks switching Heron on? | "The date still waits on the lawful basis for each source, asked of the DPO by 10 November." in [[EPC-032-switch-on-and-withdraw]] |
| F1.7 | REG | high | new | If a digest is a client record (UNK-064), may it be deleted on withdrawal, and what happens to data already read or sent on before the person withdrew? | "any digest or prep note held for them on the laptop is deleted." in [[EPC-032-switch-on-and-withdraw]] |
| F1.8 | OPS | high | R-OPS-14 | Do the consent choice and the withdrawal leave the laptop for Consent and identity, and does CST-003 (no meeting text off a laptop before 4 December) cover that or exempt it? | "It sends nothing off the laptop itself." in [[desktop-agent-building-blocks]] |
| F1.9 | OPS | high | R-OPS-15 | Should the February pilot be recorded as blocked by UNK-051, UNK-056 and UNK-069 as well as UNK-071, and who owns the order of the gates and the pilot date? | "The date still waits on the lawful basis for each source, asked of the DPO by 10 November." in [[EPC-032-switch-on-and-withdraw]] |
| F1.10 | OPS | normal | R-OPS-17 | Does the February pilot include Macs as well as Windows PCs, and who checks that no Frankfurt staff are in the Client Delivery London group? | "Part of the February pilot for Client Delivery London, 2 February 2027." in [[EPC-032-switch-on-and-withdraw]] |
| F1.11 | OPS | normal | R-OPS-16 | What supports the 70 percent Zoom figure, who confirms it, and does the pilot lead accept calendar-only notes as the expected case? | "The solution lead puts Zoom at 70 percent of Client Delivery's day, a figure with no document behind it." in [[11-unknowns-and-risks]] |
| F1.12 | OPS | high | new | Which team builds and runs Consent and identity, so EPC-032 can depend on its epic? What does a person see at switch-on if it is slow or down, and how long does Heron wait before it treats a choice as not kept? | "Nothing in this team." in [[EPC-032-switch-on-and-withdraw]] |
| F1.13 | OPS | high | new | If a withdrawal is not confirmed by Consent and identity, does Heron stop reading and delete held notes locally anyway, and does it tell the person? | "the withdrawal is sent to Consent and identity over the record-consent contract, and later consent checks answer no, so nothing more is read for them." in [[EPC-032-switch-on-and-withdraw]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| EPC-032 | - | draft | [[2026-10-12-desk-agent-epics#^c01]] |
| EPC-033 | - | draft | [[2026-10-12-desk-agent-epics#^c01]] |
| EPC-034 | - | draft | [[2026-10-12-desk-agent-epics#^c01]] |
| EPC-035 | - | draft | [[2026-10-12-desk-agent-epics#^c01]] |
| CAP-005.FR2 | - | assumption | [[2026-10-12-desk-agent-epics#^c06]] |
| R-OPS-14 | open | answered | [[2026-10-12-desk-agent-epics#^c05]] |
| R-OPS-19 | - | answered | [[2026-10-12-desk-agent-epics#^c06]] |
| R-DAT-16 | - | open | [[2026-10-12-desk-agent-epics#1. On the agenda: EPC-032, 2026-10-12]] |
| R-DAT-17 | - | open | [[2026-10-12-desk-agent-epics#1. On the agenda: EPC-032, 2026-10-12]] |
| R-DAT-18 | - | open | [[2026-10-12-desk-agent-epics#1. On the agenda: EPC-032, 2026-10-12]] |
| R-DAT-19 | - | open | [[2026-10-12-desk-agent-epics#1. On the agenda: EPC-032, 2026-10-12]] |
| R-REG-13 | - | open | [[2026-10-12-desk-agent-epics#1. On the agenda: EPC-032, 2026-10-12]] |
| R-REG-14 | - | open | [[2026-10-12-desk-agent-epics#1. On the agenda: EPC-032, 2026-10-12]] |
| R-OPS-18 | - | open | [[2026-10-12-desk-agent-epics#1. On the agenda: EPC-032, 2026-10-12]] |
