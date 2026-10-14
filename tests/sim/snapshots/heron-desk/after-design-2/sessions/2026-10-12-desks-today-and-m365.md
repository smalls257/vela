---
id: 2026-10-12-desks-today-and-m365
type: session
title: "Discover: desks today and M365"
date: 2026-10-12
modes: [discover, dump]
status: closed
summary: "Discover: desks today and M365. Recorded the tenant facts and the CISO's booking, typed Microsoft, Clients and Zoom, resolved UNK-053 (Intune and Jamf push, not self-install), and opened UNK-061 to UNK-065. Five reviewer questions are now open."
---

# 2026-10-12 Discover: desks today and M365

## Captures

- [thought] (IT endpoint lead, tenant note of 2026-10-02) "One tenant, about 4,200 users." → keep: [[03-context-and-scope#Today|Today]] (fact) ^c01
- [thought] (IT endpoint lead, tenant note of 2026-10-02) "3,100 Windows managed by Intune, 1,100 Macs managed by Jamf." → keep: [[03-context-and-scope#Today|Today]] (fact) ^c02
- [thought] (IT endpoint lead, tenant note of 2026-10-02) "Staff cannot install software. Everything is pushed from Intune or Jamf." → keep: [[03-context-and-scope#Today|Today]] (fact) ^c03
- [thought] (IT endpoint lead, tenant note of 2026-10-02) Teams transcripts exist only where the organizer turned them on, in the organizer's OneDrive. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c04
- [thought] (IT endpoint lead, tenant note of 2026-10-02) A Graph app registration goes through the identity team; calendar and mail are readable with each user's own consent; transcripts need tenant admin approval. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c05
- [thought] (IT endpoint lead, tenant note of 2026-10-02) "Frankfurt (about 600 staff) has a works council." → keep: [[03-context-and-scope#Today|Today]] (fact) ^c06
- [thought] (CISO, position of 2026-10-06) Any new app registration on the tenant needs "my security review first, which takes about six weeks." → keep: [[03-context-and-scope#Today|Today]] (fact) ^c07
- [thought] (CISO, booking of 2026-10-06) "Submit the pack by 10 November", review in the week of 16 November, outcome due 4 December. → keep: [[03-context-and-scope#Today|Today]] (fact) ^c08
- [thought] (solution lead) "The pilot start is fact though—2 February, not a plan." Claude said a future date is an assumption by default; the lead overrode that. → keep: [[02-constraints#Constraints|CST-009]] (fact) ^c09
- [thought] (solution lead) Microsoft is a party; Jamf is "their tool, not a gate". → keep: [[03-context-and-scope#PTY-01 Microsoft|PTY-01]] (subject) ^c10
- [unknown] (claude, from CIO brief of 2026-09-30 and tenant note) The CIO brief says Heron needs only each person's own Microsoft 365 sign-in, but transcripts need tenant admin approval and a registration needs the CISO's review. → keep: [[11-unknowns-and-risks#UNK-059 Transcripts and admin approval|UNK-059]] (open) ^c11
- [unknown] (claude, from CIO brief and product one-pager) The CIO brief says the data never leaves the machine; the one-pager has a cloud service writing the summaries. → keep: [[11-unknowns-and-risks#UNK-051 Text call|UNK-051]] (open) ^c12
- [thought] (solution lead) "I had that backwards—Intune and Jamf push it, not users. The two-minute install story doesn't hold." → keep: [[11-unknowns-and-risks#UNK-053 Install or push|UNK-053]] (resolved) ^c13
- [thought] (solution lead) Review timing first: "if that doesn't work, February fails." And on sharpening the question: "that's what sharpens it for the CIO call—if the six weeks is on top, February dies." This is the lead's reading, not a finding; the CISO holds the answer. → keep: [[11-unknowns-and-risks#UNK-058 Security review pack|UNK-058]] (open) ^c14
- [thought] (solution lead) "Honestly not sure. The product owner owns Heron so I'd expect them to write it, but nobody's asked them directly on this yet." This is a belief with no source. Asked to sharpen the question, with @product-owner and @legal-counsel on the ask: "legal will have constraints on what goes in." → keep: [[11-unknowns-and-risks#UNK-057 Full list of data Heron reads|UNK-057]] (open) ^c15
- [unknown] (solution lead) "How we resolve the CISO and product owner lock." The documents say each side's position but not how the two get settled or who calls it. to fetch: the route to a decision between the CISO's no-text-off-the-laptop rule and the product owner's cloud design, held by nobody recorded; who calls it, and when? → keep: [[11-unknowns-and-risks#UNK-061 Who settles the lock|UNK-061]] (open) ^c16
- [unknown] (solution lead) "any actual design—user research, testing". No document describes any design, research with the people who would use Heron, or a test of it. to fetch: any design, user research or trial results, held by the product owner; does any exist? → keep: [[11-unknowns-and-risks#UNK-062 Design, research and trial|UNK-062]] (open) ^c17
- [unknown] (solution lead) "testing on Zoom, which is 70 percent of Client Delivery's day." This is the lead's figure with no document behind it. The one-pager says Heron reads Zoom, but the tenant note covers only what Microsoft 365 gives, so nothing recorded says how Heron would read Zoom meetings. to fetch: what Heron can read from Zoom meetings and how, and a count of how much of Client Delivery's meeting time is on Zoom, held by the pilot lead (Sam), who knows how the team uses it; the lead says the product owner is building Heron, not running Client Delivery. → keep: [[11-unknowns-and-risks#UNK-063 Heron on Zoom|UNK-063]] (open) ^c18
- [thought] (solution lead) "the works council in December is locked." Already recorded as a constraint; nothing new. And "CISO's the review", which the booking already records. → drop: both the works council date and the CISO review are already recorded ^c19
- [unknown] (solution lead) "Legal needs to answer whether a digest of a client call is a client record under our engagement terms, and if it is, we're sunk until we know." to fetch: whether a digest of a client call is a client record under the engagement terms, held by legal counsel; who asks them, and by when? → keep: [[11-unknowns-and-risks#UNK-064 Digest as client record|UNK-064]] (open) ^c20
- [worry] (solution lead) "Honestly not sure if we've told the Client Delivery team itself what we're surfacing about them yet—they're the pilot but they haven't been asked to sign off." to fetch: whether the Client Delivery team has been told what Heron surfaces about them, held by the pilot lead; who tells them, and do they sign off? → keep: [[11-unknowns-and-risks#UNK-065 Client Delivery told what Heron surfaces|UNK-065]] (open) ^c21
- [unknown] (solution lead) "if we're pulling transcript text from client-side Zooms, do their T's and C's let us?" to fetch: the terms of each client whose calls would be read, held by legal counsel; which clients' terms are in play? Subject: the clients, a customer group Marlowe holds engagement terms with. → keep: [[03-context-and-scope#PTY-02 Clients|PTY-02]] (subject) ^c22
- [thought] (solution lead) "Type Zoom—client T&Cs matter if we're reading them." And on the design question: "Product owner for the design is right." → keep: [[03-context-and-scope#PTY-03 Zoom|PTY-03]] (subject) ^c23

## Reviews

### 1. After the read-back, 2026-10-12

- **Coverage:** FIN skipped (nothing in scope); DAT found 4, 2 dropped; PTN found 7, 2 dropped; REG found 3, 4 dropped; OPS found 3, 4 dropped
- **Dropped:** 12 findings were dropped by the merge: nine named a reviewer question this vault does not owe, two had a quote under four words, and one had a quote that did not mention its subject. Each was about something the kept lines already cover or is raised again as a kept finding.
- **Merged:** none

| Finding | Area | Severity | Copy | Question | Quote |
|---|---|---|---|---|---|
| F1.1 | DAT | high | R-DAT-03 | Who writes the full list of data Heron reads, and by what date, so the works council has it before its December meeting? | "The works council wants the full list of data Heron reads before it agrees, and no one is recorded as holding or writing it." in [[11-unknowns-and-risks]] |
| F1.2 | DAT | high | Q-DAT-01@INI-001 | If the cloud design is chosen, which outside party would receive meeting, mail and document text, and under what agreement and lawful basis? | "The CISO allows nothing off the laptop and the product owner's design has a cloud service writing the summaries." in [[11-unknowns-and-risks]] |
| F1.3 | DAT | high | Q-DAT-05@INI-001 | Is using the organizer's transcripts, and one user's mail and calendar that include other people's content, a new purpose? Do other attendees have a say, and who decides on tenant admin approval? | "Teams transcripts exist only where the organizer turned them on, and they sit in the organizer's OneDrive, and reading them needs tenant admin approval." in [[03-context-and-scope]] |
| F1.4 | DAT | normal | Q-DAT-05@INI-001 | Which document sources will Heron read, who collected them and for what, and are they on the full data list? | "quietly watches meetings, email and documents, and tells you what matters each morning" in [[01-goals]] |
| F1.5 | PTN | high | Q-PTN-02@PTY-01 | Does the Microsoft agreement or the Graph terms let data read from Microsoft 365 go to a new party, such as a cloud summarizing service? Who would check? | "- **Agreements:** none known" in [[03-context-and-scope]] |
| F1.6 | PTN | high | Q-PTN-05@PTY-01 | Can the Microsoft agreement or the app registration be assigned, or change control, if Heron moves to another team or owner? | "so what Heron may see depends on what Microsoft 365 exposes and what the tenant admins approve." in [[03-context-and-scope]] |
| F1.7 | PTN | normal | Q-PTN-06@PTY-01 | What notice does a change to the Microsoft terms need, and who gives it? | "Microsoft supplies the tenant, Teams, Outlook and the Graph interface that Heron would read through" in [[03-context-and-scope]] |
| F1.8 | PTN | high | R-PTN-02 | What agreement does the works council need to give for the pilot, who holds it, and what is the fallback if December does not produce it before packaging in January? | "The works council takes Heron at its December meeting and will not agree before it has read the full list of data Heron reads." in [[02-constraints]] |
| F1.9 | PTN | high | Q-PTN-01@INI-001 | Who owns and runs the Intune and Jamf pushes, and does Heron need any agreement, change slot or payment with them? Is Jamf a gate or not? | "Heron must be packaged for Intune and for Jamf, and a person can only switch it on." in [[02-constraints]] |
| F1.10 | PTN | high | new | Is the six-week app-registration review inside the 10 November to 4 December window or after it? Does the 2 February date still hold if it is after? | "The registration Heron needs cannot be raised until the review is requested, so the six weeks sit on the critical path." in [[02-constraints]] |
| F1.11 | PTN | normal | new | Who in the identity team approves the Graph registration and the transcript consent, and by what date? | "The CIO's brief says Heron needs only each person's own Microsoft 365 sign-in." in [[11-unknowns-and-risks]] |
| F1.12 | REG | high | new | What lawful basis and notice cover transcript text from meeting attendees who are not the person who switched Heron on, including Frankfurt staff and external guests? | "Teams transcripts exist only where the organizer turned them on, and they sit in the organizer's OneDrive" in [[03-context-and-scope]] |
| F1.13 | REG | high | new | Which date is right for the CISO outcome: 4 December, or six weeks after the pack or the review? Does the six-week app-registration review run after the 4 December outcome? | "The security review pack goes in by 10 November 2026 and the outcome is due 4 December 2026." in [[02-constraints]] |
| F1.14 | REG | high | Q-REG-02@INI-001 | Is workplace monitoring of staff regulated or licensed here, and what notice, council agreement or DPO sign-off does a helper that quietly watches require? | "quietly watches meetings, email and documents" in [[01-goals]] |
| F1.15 | OPS | normal | new | Should G1 be reworded to match the push-from-Intune-and-Jamf reality, and what does 'set up' now mean for a person on the pilot? | "sets up in two minutes" in [[01-goals]] |
| F1.16 | OPS | normal | Q-OPS-06@INI-001 | Have the identity team, tenant admins, Teams organizers, Mac users and Frankfurt staff been told or asked, and who speaks for each? | "A Graph app registration is raised through the identity team, per [[sources#SRC-013\|the tenant note]]." in [[03-context-and-scope]] |
| F1.17 | OPS | high | Q-OPS-07@INI-001 | Which of these beliefs, if wrong, would change the plan most, and who can confirm that the CIO has the authority to settle the text call? | "The solution lead believes the CIO settles it as budget holder, with no source named, so this is a belief and not a finding." in [[11-unknowns-and-risks]] |

## Changes

| ID | From | To | Source |
|---|---|---|---|
| Today | - | fact | [[2026-10-12-desks-today-and-m365#^c01]] |
| Today | - | fact | [[2026-10-12-desks-today-and-m365#^c02]] |
| Today | - | fact | [[2026-10-12-desks-today-and-m365#^c03]] |
| Today | - | fact | [[2026-10-12-desks-today-and-m365#^c04]] |
| Today | - | fact | [[2026-10-12-desks-today-and-m365#^c05]] |
| Today | - | fact | [[2026-10-12-desks-today-and-m365#^c06]] |
| Today | - | fact | [[2026-10-12-desks-today-and-m365#^c07]] |
| Today | - | fact | [[2026-10-12-desks-today-and-m365#^c08]] |
| CST-009 | fact | fact | [[2026-10-12-desks-today-and-m365#^c09]] |
| PTY-01 | - | subject | [[2026-10-12-desks-today-and-m365#^c10]] |
| UNK-059 | open | open | [[2026-10-12-desks-today-and-m365#^c11]] |
| UNK-051 | open | open | [[2026-10-12-desks-today-and-m365#^c12]] |
| UNK-053 | open | resolved | [[2026-10-12-desks-today-and-m365#^c13]] |
| UNK-058 | open | open | [[2026-10-12-desks-today-and-m365#^c14]] |
| UNK-057 | open | open | [[2026-10-12-desks-today-and-m365#^c15]] |
| PTY-02 | - | subject | [[2026-10-12-desks-today-and-m365#^c22]] |
| PTY-03 | - | subject | [[2026-10-12-desks-today-and-m365#^c23]] |
| UNK-061 | - | open | [[2026-10-12-desks-today-and-m365#^c16]] |
| UNK-062 | - | open | [[2026-10-12-desks-today-and-m365#^c17]] |
| UNK-063 | - | open | [[2026-10-12-desks-today-and-m365#^c18]] |
| UNK-064 | - | open | [[2026-10-12-desks-today-and-m365#^c20]] |
| UNK-065 | - | open | [[2026-10-12-desks-today-and-m365#^c21]] |
| R-PTN-03 | - | open | [[2026-10-12-desks-today-and-m365#1. After the read-back, 2026-10-12]] |
| R-PTN-04 | - | open | [[2026-10-12-desks-today-and-m365#1. After the read-back, 2026-10-12]] |
| R-REG-03 | - | open | [[2026-10-12-desks-today-and-m365#1. After the read-back, 2026-10-12]] |
| R-REG-04 | - | open | [[2026-10-12-desks-today-and-m365#1. After the read-back, 2026-10-12]] |
| R-OPS-04 | - | open | [[2026-10-12-desks-today-and-m365#1. After the read-back, 2026-10-12]] |
