---
id: CAP-001
type: capability
title: Apply for a residential permit
state: assumption
owner: "@sim-lead"
authored: authored
origin: proposed
change: new
domain: Building and Planning
sources: [2026-10-12-permit-requirements]
---

# Apply for a residential permit

A homeowner or a contractor gets a permit for work on a house: they send the application and the plans, a plans examiner reviews them, the city issues the permit, and inspectors check the work. Today it is a paper application handed in at the permit counter.

## Functional requirements

### CAP-001.FR1 Hand in the plans

An applicant hands in the plan set as PDFs uploaded with the application.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c01]]
- **Options considered:** Upload the plan set as PDFs in the portal (picked); Drop paper at the counter to be scanned: rejected, the counter is closing to walk-ins and scanning is the work the portal removes.

- An application without its plans cannot be sent.
- Each sheet keeps its sheet number, so a correction can replace one sheet.

### CAP-001.FR2 Check before sending

An applicant ticks the checklist for their permit type before the application can be sent.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c02]]
- **Options considered:** A checklist for each permit type, ticked before it can be sent (picked); Staff check it after it arrives: rejected, most applications bounce today for a missing document.

- The checklist names each document the permit type needs.
- An item the applicant marks as not needed asks them to say why.

### CAP-001.FR3 Answer corrections

An applicant answers a reviewer's corrections by uploading only the changed sheets against the list of corrections.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c03]]
- **Options considered:** Upload only the changed sheets against the list of corrections (picked); Send the whole plan set again: rejected, the reviewer would start over.

- Each changed sheet is tied to the correction it answers.
- The reviewer sees which corrections are still unanswered.

### CAP-001.FR4 Book an inspection

An applicant books an inspection slot online, from the next business day.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c04]]
- **Options considered:** The applicant books a slot online, from the next business day (picked); They phone the inspections line: rejected, it is the second busiest phone in the department.

- Only the inspections the permit needs are offered, in the order the code sets.
- The applicant can move a booking up to the day before.

### CAP-001.FR5 Where my application is

An applicant sees each step of their application, and gets an email each time it moves.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c05]]
- **Options considered:** Each step, with an email when it moves (picked); A status page they check themselves: rejected, most counter questions today ask where a permit is.

- The steps are: sent, in review, corrections asked, approved, issued, inspections, and closed.
- An email names the address and the step it moved to.

### CAP-001.FR6 Expiry warning

A permit with no passed inspection gets a warning at 150 days and expires at 180.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c06]]
- **Options considered:** A warning at 150 days, and it expires at 180 (picked); It expires at 180 days with no warning: rejected, the warning saves the argument.

- The days are counted from the issue date or the last passed inspection.
- The warning goes to the applicant and the property owner.

### CAP-001.FR7 Tell the owner

When a permit is issued, both the applicant and the property owner are told.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c07]]
- **Options considered:** The applicant and the property owner (picked); The applicant only: rejected, an owner should know when work on their house is permitted.

- The owner is told at the owner's address of record.
- The message names the work and the contractor.

### CAP-001.FR8 Renew an expired permit

An applicant can renew an expired permit once online, for half the fee.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c08]]
- **Options considered:** Renew it once online for half the fee (picked); Apply again from the start: rejected, the fee schedule already allows one renewal at half the fee.

- A permit already renewed once cannot be renewed again.
- The renewal keeps the plans and the inspections already passed.

### CAP-001.FR9 When the review clock starts

The review clock starts when the applicant sends the application.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c09]]
- **Options considered:** When the applicant sends the application (picked); When a permit tech accepts it as complete: rejected, it is the slower reading of the ten business days.

- The applicant sees the date the clock started.
- Whether an online application starts the state's clock by itself is open as [[11-unknowns-and-risks#UNK-001 When the state's review clock starts|when the state's review clock starts]].

### CAP-001.FR10 Pay the fee

An applicant pays the whole fee by card when they send the application.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c10]]
- **Options considered:** By card, in full when they send the application (picked); At issue, by card or check: rejected, unpaid applications would fill the queue.

- The applicant gets a receipt for the fee.
- Who pays the card charge is open as [[11-unknowns-and-risks#UNK-002 Who pays the card charge|who pays the card charge]].

### CAP-001.FR11 Show a contractor is licensed

A contractor's license number is checked against the state register when they sign up.

- **State:** assumption
- **Source:** [[2026-10-12-permit-requirements#^c11]]
- **Options considered:** Their license number is checked against the state register when they sign up (picked); They upload a photo of their license: rejected, a photo is the paper check again and can be faked.

- A contractor whose license has lapsed cannot send an application.
- Whether the city may use the register's lookup is open as [[11-unknowns-and-risks#UNK-003 Checking licenses online|checking licenses online]].
