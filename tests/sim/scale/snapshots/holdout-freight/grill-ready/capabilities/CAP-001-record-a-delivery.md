---
id: CAP-001
type: capability
title: Record a delivery
state: assumption
owner: "@sim-lead"
authored: authored
origin: proposed
change: new
domain: Dispatch
sources: [2026-10-12-delivery-requirements]
---

# Record a delivery

A driver drops freight at a customer's dock and records that it arrived: who took it, what it looked like and when. The record is the proof Billing invoices on and the customer settles disputes with. Today it is a paper receipt carried back to the depot.

## Functional requirements

### CAP-001.FR1 Confirm the delivery

The person receiving the freight signs on the handheld's screen.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c01]]
- **Options considered:** The person receiving it signs on the screen (picked); The driver types the receiver's name: rejected, a signature is what a dispute is settled on.

- The receiver's printed name is taken with the signature.
- A delivery cannot be closed without a signature or a recorded reason there is none.

### CAP-001.FR2 Photo of the freight

The driver takes at least one photo of the freight as left at each delivery.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c02]]
- **Options considered:** At least one photo of the freight as left (picked); Only when something is wrong: rejected, the photo settles most arguments about what arrived.

- The photo carries the time it was taken.
- A delivery can hold up to ten photos.

### CAP-001.FR3 Damaged freight

The driver marks a damaged line with a photo and a note.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c03]]
- **Options considered:** Mark the damaged line with a photo and a note (picked); Phone dispatch to report it: rejected, a phone call leaves nothing on the record.

- The receiver sees the damage note before signing.
- Dispatch is told of the damage when the record arrives.

### CAP-001.FR4 Refused delivery

The driver records a refused delivery with a reason picked from a list.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c04]]
- **Options considered:** Pick a reason from a list (picked); Type the reason in free text: rejected, billing and the customer both need the same few reasons.

- The list includes "other", which asks for a note.
- A refused delivery tells dispatch at once, so the freight can be routed back.

### CAP-001.FR5 Nobody to sign

When there is nobody to sign, the driver records an attempted delivery with a photo and the time.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c05]]
- **Options considered:** The driver records an attempted delivery with a photo and the time (picked); The driver leaves the freight and notes it later: rejected, an attempted delivery is billable and needs proof.

- The photo shows the closed dock or the door.
- The record says whether the freight was left or taken back.

### CAP-001.FR6 Customer copy

The customer gets a copy of the delivery record by email at once.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c06]]
- **Options considered:** A copy by email at once (picked); They look it up in the portal: rejected, the receiver signs for someone else, who never sees the portal.

- The copy goes to the address on the customer's account.
- It holds the signature, the photos and the time.

### CAP-001.FR7 No signal at the stop

With no signal at the stop, the app keeps the record and sends it when a signal returns.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c07]]
- **Options considered:** The app keeps the record and sends it later (picked); The driver waits for a signal: rejected, rural stops often have no signal.

- The driver sees which records are still waiting to be sent.
- The record keeps the time of the delivery, not the time it was sent.

### CAP-001.FR8 Correct a record

Dispatch can correct a delivery record within 24 hours, with the reason logged.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c08]]
- **Options considered:** Dispatch can correct it within 24 hours, with the reason logged (picked); Never, once it is sent: rejected, drivers mistype, and a logged correction is better than a second record.

- The original record is kept beside the correction.
- The customer gets the corrected copy.

### CAP-001.FR9 Extra charges at the stop

The driver adds extra charges at the stop to the delivery record.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c09]]
- **Options considered:** The driver adds them on the delivery record (picked); Billing adds them from a phone call: rejected, the driver is the only one who saw the wait.

- Each charge has a type, an amount of time or money, and a note.
- How the charges reach the invoice is open as [[11-unknowns-and-risks#UNK-001 Extra charges and the invoice|extra charges and the invoice]].

### CAP-001.FR10 The app's language

The app is in French and English, and each driver picks one.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c10]]
- **Options considered:** French and English, the driver's choice (picked); English everywhere: rejected, part of the workforce works in French.

- The customer copy is in the language of the customer's account.
- Which language the Quebec drivers' app must be in is open as [[11-unknowns-and-risks#UNK-002 The language of the app in Quebec|the language of the app in Quebec]].

### CAP-001.FR11 When the delivery form opens

The delivery form opens by itself when the truck arrives at the stop.

- **State:** assumption
- **Source:** [[2026-10-12-delivery-requirements#^c11]]
- **Options considered:** By itself on arrival at the stop (picked); When the driver opens it after parking: rejected, drivers forget to open it.

- The form names the stop and the freight expected.
- What the driving rules allow is open as [[11-unknowns-and-risks#UNK-003 The app while the truck moves|the app while the truck moves]].
