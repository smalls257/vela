---
id: 2026-10-05-mandate-meaning
type: session
title: "Dump & Diverge: mandate meaning"
date: 2026-10-05
modes: [dump]
status: closed
summary: Mandate "one account" has no definition; April go-live, the DPO gate, and the CIO question captured as seven unknowns.
---

# 2026-10-05 Dump & Diverge: mandate meaning

## Captures

- [worry] (solution lead) "I'm three months into a merger, the CIO hands me one sentence with no definition, tells me to deliver it by next summer, and disappears." → keep: [[11-unknowns-and-risks#UNK-001 What one account means|UNK-001]] (unknown) ^c01
- [unknown] (solution lead) "So I'm guessing at what "one customer" even means. Is it one login? One record? One view?" → keep: [[11-unknowns-and-risks#UNK-001 What one account means|UNK-001]] (unknown) ^c02
- [idea] (claude) What if "one customer" starts as one view, a lookup that shows a person's ferry and rail trips side by side, and the single login and single record come later or never? → park ^c03
- [wild] (claude) What if "one account" is a link the customer makes themselves between the accounts they already have, the way a bank lets you add an external account, and nothing is merged behind it? → park ^c04
- [thought] (solution lead) "The CFO wants one platform and cost cuts—switch off the other thing inside two years." → keep: [[01-goals|G1]] (inkling) ^c05
- [thought] (solution lead) "The Rail Product director wants rail first, everything else bolts on." → keep: [[01-goals|G2]] (inkling) ^c06
- [thought] (solution lead) "The Ferry Ops director says nothing touches their systems before May or during the season." → keep: [[02-constraints|CST-1]] (inkling) ^c07
- [unknown] (solution lead) "Honestly not sure how those three things fit together." → keep: [[11-unknowns-and-risks#UNK-006 Competing director demands|UNK-006]] (unknown) ^c08
- [idea] (claude) What if the three demands are put on one timeline: rail work in the months before May, ferry connected by a read-only feed that never changes their systems, and the CFO's switch-off date counted from when the single view is live? → park ^c09
- [wild] (claude) What if the CFO's saving came from sharing the back office and keeping both front doors, so nothing has to be switched off? → park ^c10
- [thought] (solution lead) "Ferry customers share email addresses, rail customers don't." → keep: [[11-unknowns-and-risks#UNK-002 Overlap and shared emails|UNK-002]] (unknown) ^c11
- [idea] (claude) What if a shared ferry email is treated as a household, with a traveller under it for each person, the way a family booking works? → park ^c12
- [unknown] (solution lead) "We don't even know how many customers travel both ways." → keep: [[11-unknowns-and-risks#UNK-002 Overlap and shared emails|UNK-002]] (unknown) ^c13
- [idea] (claude) What if the overlap were estimated from a small sample of customers matched on name and a booking reference, so there is a rough number before any full data work? → park ^c14
- [worry] (solution lead) "Nobody named owns the ferry customer database anymore." → keep: [[11-unknowns-and-risks#UNK-003 Ferry customer data owner|UNK-003]] (unknown) ^c15
- [idea] (claude) What if the first deliverable were an owner for the ferry customer data, an interim custodian named before any design starts? → park ^c16
- [thought] (solution lead) "Ferry season freeze is May to September, so we've got until April to go live, not next summer. Four months tops." → drop: miscount, corrected in ^c22 ^c17
- [unknown] (claude) What starts the "four months"? Today is 5 October, which is about six months before April, so is the four a build window inside that, or a freeze date earlier than May? → drop: answered by ^c22 ^c18
- [unknown] (claude) The CIO said "by next summer" and the freeze covers the summer, so does the CIO know that April is the real date? → keep: [[11-unknowns-and-risks#UNK-007 CIO aware of April date|UNK-007]] (unknown) ^c19
- [idea] (claude) What if "live by April" meant only the ferry-side connection, and the customer-facing parts that rail owns went live earlier or after the freeze? → park ^c20
- [wild] (claude) What if the freeze were the plan: go live in April on one ferry route as a pilot, and let the whole season be the test? → park ^c21
- [thought] (solution lead) "April's six months away. End of April is when we have to be live, before the ferry freeze kicks in." → keep: [[02-constraints|CST-1]] (inkling) ^c22
- [idea] (claude) What if the work were counted backwards from end of April, with the last month kept for a freeze-in rehearsal, so the real build window is what is left? → park ^c23
- [worry] (solution lead) "I'm most worried we'll pick the wrong direction because nobody has actually defined what 'one account' means—not even the CIO." → keep: [[11-unknowns-and-risks#UNK-001 What one account means|UNK-001]] (unknown) ^c24
- [idea] (claude) What if the CIO were asked to choose between three short sentences, "one view", "one login" and "one record", and the answer became the definition? → keep: [[11-unknowns-and-risks#UNK-001 What one account means|UNK-001]] (unknown) ^c25
- [worry] (solution lead) "The ferry freeze is the hard stop. We miss end of April, we're locked out for five months." → keep: [[11-unknowns-and-risks#R-01 Miss the April go-live|R-01]] (open) ^c26
- [worry] (solution lead) "The three directors are impossible. CFO wants rail to win, Ferry Ops won't allow changes, Rail Product wants ferry on RailCore—we can't make all three happy." → keep: [[11-unknowns-and-risks#UNK-006 Competing director demands|UNK-006]] (unknown) ^c27
- [worry] (solution lead) "We pick the wrong thing because the CIO hasn't defined 'one account'. Build for two months, someone says that's not what they meant, we burn time." → keep: [[11-unknowns-and-risks#UNK-001 What one account means|UNK-001]] (unknown) ^c28
- [worry] (solution lead) "The data side will kill us. Ferry customers share emails, rail doesn't, we don't know the overlap, the ferry database has no owner. Honestly not sure we can merge without breaking it." → keep: [[11-unknowns-and-risks#UNK-002 Overlap and shared emails|UNK-002]] (unknown) ^c29
- [idea] (claude) What if the April deadline came with an agreed fallback, a smaller version that can still go live before the freeze, decided in advance so missing the full scope does not mean missing the date? → park ^c30
- [idea] (claude) What if the three directors each wrote down in one sentence what "done" looks like for them, and the overlap and the gaps were looked at side by side before any option is picked? → park ^c31
- [wild] (claude) What if the first two months were spent only on showing the CIO a sketch of each meaning of "one account", so that the wrong build is the sketch and not the product? → park ^c32
- [idea] (claude) What if merging were never the aim for the data, and ferry and rail records stayed where they are and were only matched, so nothing in the ferry database can be broken? → park ^c33
- [unknown] (solution lead) "Honestly not sure on the privacy terms" → keep: [[11-unknowns-and-risks#UNK-004 DPO proposal before data|UNK-004]] (unknown) ^c34
- [worry] (solution lead) "the Data Protection Officer said they want to see a proposal before we decide anything about customer data, so that's going to block us anyway." → keep: [[11-unknowns-and-risks#UNK-004 DPO proposal before data|UNK-004]] (unknown) ^c35
- [idea] (claude) What if the proposal for the Data Protection Officer were the first thing written, even as a rough one-pager on the options for "one account", so their questions arrive while the definition is still open? → park ^c36
- [unknown] (solution lead) "I have no idea who supports it during the freeze." → keep: [[11-unknowns-and-risks#UNK-005 Support during the freeze|UNK-005]] (unknown) ^c37
- [worry] (solution lead) "Ferry Ops will go mad if we ask them to babysit something that's live but they can't touch." → keep: [[11-unknowns-and-risks#UNK-005 Support during the freeze|UNK-005]] (unknown) ^c38
- [wild] (claude) What if support during the freeze sat with a named rail-side team, with a runbook and a single phone line, so Ferry Ops is only ever told and never asked? → park ^c39
- [thought] (solution lead) "The DPO's going to be the first gate anyway—won't let us touch customer data until they've seen a proposal." → keep: [[11-unknowns-and-risks#UNK-004 DPO proposal before data|UNK-004]] (unknown) ^c40
- [thought] (solution lead) "DPO's first gate anyway. Then we need the CIO to actually say what one account means—everything else is guessing." → keep: [[11-unknowns-and-risks#UNK-001 What one account means|UNK-001]] (unknown) ^c41

## Changes

| ID | From | To | Source |
|---|---|---|---|
| UNK-001 | - | open | [[2026-10-05-mandate-meaning#^c02]] |
| UNK-002 | - | open | [[2026-10-05-mandate-meaning#^c13]] |
| UNK-003 | - | open | [[2026-10-05-mandate-meaning#^c15]] |
| UNK-004 | - | open | [[2026-10-05-mandate-meaning#^c35]] |
| UNK-005 | - | open | [[2026-10-05-mandate-meaning#^c37]] |
| UNK-006 | - | open | [[2026-10-05-mandate-meaning#^c27]] |
| UNK-007 | - | open | [[2026-10-05-mandate-meaning#^c19]] |
| R-01 | - | open | [[2026-10-05-mandate-meaning#^c26]] |
| G1 | - | inkling | [[2026-10-05-mandate-meaning#^c05]] |
| G2 | - | inkling | [[2026-10-05-mandate-meaning#^c06]] |
| CST-1 | - | inkling | [[2026-10-05-mandate-meaning#^c22]] |
