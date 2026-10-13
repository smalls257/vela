---
slug: desktop-agent
status: complete-with-gaps
vault:
  app: APP-desktop-agent
  initiative: INI-001
deferred: []
gaps:
  - id: PG-001
    what: "EPC-035.AC1 to AC5 and CAP-001.FR1 (transcripts) have no story to build: S-11 (transcript calls, built but off) is deferred"
    acknowledged_by: team lead
    why: "It would take half the Rust capacity for something that does not ship while EPC-035 is on no release; both engineers are needed on S-08, S-09 and S-10"
    revisit: "When the second registration review date is known (UNK-059), or EPC-035 joins a release"
last_session: 2026-10-12T00:00:00Z
prereqs:
  - path: docs/tech-design/desktop-agent.md
    expected_status: complete-with-gaps
---

# Work breakdown: Desktop agent

This plan covers APP-desktop-agent (INI-001 @ 051d15a). It rests on the design `docs/tech-design/desktop-agent.md` at `complete-with-gaps`, the vault's allocated requirements, contracts and epic criteria, and ADR-0001. Sizes are S (up to about 2 days), M (3 to 5 days) and L (1 to 2 weeks) for one engineer. They are for ordering, not commitments. Each story's acceptance criteria are written out word for word from the epic criterion or requirement on its Traces to line; a criterion that comes from the design or the team says so.

Audited on 2026-10-12 against `NEG-AUDIT.md`, after S-04 was merged into S-05; the result is in `docs/plan/desktop-agent-audit.md`. The plan stands as `complete-with-gaps` for PG-001 only.

## Summary
| Story | Traces to | Size total | Blocked by |
|---|---|---|---|
| S-01 Walking skeleton | design only | 3 M, 3 S | D-001 |
| S-02 Switch on, with consent recorded | CAP-005.FR1, CON-003, CON-004, EPC-032.AC1-4 | 2 M, 2 S | S-01, OQ-005 |
| S-03 Withdraw | CAP-005.FR2, CON-004, EPC-032.AC5-6 | 1 L, 2 M, 2 S | S-02, OQ-010 |
| S-04 Read calendar entries | merged into S-05 | not planned | none |
| S-05 Morning digest, from calendar to screen | CAP-001.FR2, CAP-002.FR1, CAP-003.FR1, CAP-003.FR2, CON-001, CON-002, EPC-033.AC1-5, EPC-034.AC1 | 5 M, 6 S | S-02, UNK-069, D-002, UNK-067, OQ-005, S-07b |
| S-06 Prep note before a meeting | CAP-002.FR2, CAP-004.FR1, CON-002, EPC-034.AC2-5 | 3 M, 2 S | S-05, OQ-002, D-002, UNK-067 |
| S-07a Managed-setting gate for the remote Summariser path | CON-002, CST-003 | 1 M, 1 S | S-01, S-05, OQ-007, UNK-051, OQ-009 |
| S-07b Remote Summariser transport and both-paths tests | CON-002, CST-003 | not planned | OQ-007, UNK-051, OQ-009 |
| S-08 Windows MSIX through Intune | CST-007, CST-010 | 2 M, 1 S | S-01, OQ-009, UNK-069 |
| S-09 Mac pkg through Jamf | CST-007, CST-010 | 1 M, 2 S | OQ-001, UNK-054, OQ-009, S-08 |
| S-10 Operations hardening | design only: Operations (Monitor, Restart, Tunables); K-1, K-8 | 2 M, 1 S | OQ-009, D-004 |
| S-11 Transcripts calls, built but off | CAP-001.FR1, EPC-035.AC1-5 | not planned | PG-001, UNK-059 |

## Stories

### S-01 Walking skeleton
- **Tracer:** yes
Traces to: design only: LocalStore, NoteView and Scheduler (shell only); Operations (kill switch, schema version)
Components: LocalStore, NoteView, Scheduler
Slice: tracer. The design names this the walking skeleton: the smallest path through its components that the pilot flow runs through. On its own it shows a tray state and nothing else, so S-02 and S-05 finish the tracer.
Done when: the signed agent starts, opens its encrypted store and shows a tray state, and reads nothing while the managed kill switch is off.
Acceptance criteria:
- The signed agent starts, opens the encrypted store, shows a tray icon that tells stopped or disabled from "no digest today", and reads and shows nothing when the managed kill switch is off.
- A binary that finds a newer schema than it knows reads nothing and does not reset the store.

| Task | Size | Component |
|---|---|---|
| Store behind a small backend interface, with schema version and launch sweep | M | LocalStore |
| Key-store binding (Keychain on Mac, DPAPI on Windows) | M | LocalStore |
| Tauri shell with the command allow-list and strict content security policy | S | NoteView |
| Tray icon with stopped and disabled states | S | NoteView |
| Read the managed kill switch | S | Scheduler |
| D-001 spike: SQLCipher in a signed Rust core, installed through Intune and Jamf. Done when it builds, signs, installs and opens the store under the key store on both platforms; otherwise take field-level AES-GCM. Decided before S-05 stores real notes and before the S-08 pilot build. Owner: Intune expert with one Rust engineer | M | LocalStore |

Blocked by: none. D-001 is a measured call run in parallel, not a gate; the backend interface keeps the AES-GCM fallback inside LocalStore.
Release fit: cannot tell. It traces to no requirement on a release; sizes add to at most 21 days for one engineer, and the design names two Rust engineers but not how many days each has.

### S-02 Switch on, with consent recorded
- **Tracer:** yes
Traces to: CAP-005.FR1@APP-desktop-agent, CON-003, CON-004, EPC-032.AC1, EPC-032.AC2, EPC-032.AC3, EPC-032.AC4
Components: ConsentGate, ConsentRecorder, NoteView
Slice: tracer
Done when: a person who switches Heron on has each choice recorded by Consent and identity, and a choice that is not confirmed leaves Heron reading nothing for them.
Acceptance criteria:
- When a person switches Heron on, they choose separately whether Heron may read their calendar entries and whether it may read their Teams transcripts. Each choice is kept.
- When a person switches Heron on, they are offered calendar entries and Teams transcripts as two separate choices, and cannot choose transcripts without calendar entries.
- Each choice is sent to Consent and identity with the person's sign-in over the record-consent contract, and Heron treats it as kept only when Consent and identity confirms it. What is sent holds the person's sign-in, the source and the date, and no meeting text.
- When a choice is not confirmed as kept, Heron reads nothing for that person and tells them.
- For a person who has not switched Heron on, Heron records no agreement and reads nothing.
- A choice not confirmed by Consent and identity counts as not kept (design, Failure behaviour).

| Task | Size | Component |
|---|---|---|
| `Grant` type constructible only inside the module, and the Consent check with its 5 s placeholder timeout, never a cached yes | S | ConsentGate |
| Durable outbox with confirmed and unconfirmed state, retried until confirmed, with its own tests (Consent down, restart mid-send, duplicate confirmation) | M | ConsentRecorder |
| Switch-on screen with per-source choices and an unconfirmed-state display, built against a stub of `switchOn`, `withdraw`, `state` | M | NoteView |
| Wire the screen to the real outbox once its tests pass | S | NoteView, ConsentRecorder |

Blocked by: S-01 (store). The wording shown when Consent and identity is down waits on OQ-005; until then the agent shows nothing and logs.
Release fit: cannot tell for 2027-02-02. Sizes add to at most 14 days for one engineer, and the design names two Rust engineers but not how many days each has before 2027-02-02.

### S-03 Withdraw
Traces to: CAP-005.FR2@APP-desktop-agent, CON-004, EPC-032.AC5, EPC-032.AC6
Components: LocalStore, ConsentRecorder, Scheduler, NoteView
Slice: vertical
Done when: a person who withdraws sees nothing more, what Heron held for them is deleted before anything is sent, and switching on again is blocked until the withdrawal is confirmed.
Acceptance criteria:
- When a person switches Heron off and Consent and identity does not confirm the withdrawal, Heron stops reading for that person at once, so a person never believes they have withdrawn while Heron still reads.
- When a person switches Heron off, the withdrawal is sent to Consent and identity over the record-consent contract, and later consent checks answer no, so nothing more is read for them.
- After a person withdraws, no digest or prep note is shown to them, and any digest or prep note held for them on the laptop is deleted.
- Local effect first, network second; switch-on is blocked while a withdrawal is unconfirmed (design, Key flows: withdrawal).

| Task | Size | Component |
|---|---|---|
| Outbox write and `purgeAll` (notes, delta token, logs) in one SQLite transaction where the data is rows; idempotent; rerun on every launch while a withdrawal is unconfirmed | M | LocalStore, ConsentRecorder |
| Stop the Scheduler and cancel in-flight reads and requests, discarding late results | S | Scheduler |
| Withdraw control with "not yet recorded" and "withdrawal recorded" states; switch-on blocked while unconfirmed | S | NoteView |
| Lost-key or corrupt-store path: fresh store, safety withdrawal, re-consent notice (D-003 measures how often) | M | LocalStore, ConsentRecorder |
| Fault-injection harness and crash tests at five points: before commit, during commit (kill loop on the real store), after commit before the network call, during the log-file purge, after the network call before the confirmation is stored. Also withdrawal while a request is in flight, and Consent down for a long time. Check whether deleted text lingers in free pages or the journal | L | LocalStore, ConsentRecorder, Scheduler |

Blocked by: S-02 (outbox). Assumes CON-004 tolerates a duplicate withdrawal; not recorded in the vault, so confirm with Consent and identity's owner. OQ-010: the residual-text check is a note for the design, not decided here.
Release fit: cannot tell for 2027-02-02. Sizes add to at most 24 days for one engineer, and the design names two Rust engineers but not how many days each has before 2027-02-02.

### S-04 Read calendar entries
Status: merged into S-05 on 2026-10-12. Reading calendar entries shows nothing a person can see, so it is not a story of its own. The ID is retired, not reused; its targets and tasks are in S-05.

### S-05 Morning digest, from calendar to screen
- **Tracer:** yes
Traces to: CAP-001.FR2@APP-desktop-agent, CAP-002.FR1@APP-desktop-agent, CAP-003.FR1@APP-desktop-agent, CAP-003.FR2@APP-desktop-agent, CON-001, CON-002, EPC-033.AC1, EPC-033.AC2, EPC-033.AC3, EPC-033.AC4, EPC-033.AC5, EPC-034.AC1
Components: ConsentGate, SourceReader, Scheduler, NoteClient, NoteView, LocalStore
Slice: tracer. The team's thin path through the pilot flow ends here: a granted person sees their digest on screen, from a mocked Graph and the on-device Summariser path.
Done when: a person who has switched Heron on sees their digest on screen, from a mocked Graph and the on-device Summariser path.
Acceptance criteria:
- Heron reads the signed-in person's own calendar entries for the day, and for each meeting the title, time and attendees that the entry holds.
- Each morning a person who has switched Heron on sees that day's digest on their own laptop. If the laptop was not available at 7:30, they see it the first time they are back at it that morning. A digest shown after 7:30 says that it is late.
- Each working morning, a person who has switched Heron on gets a digest written from their own calendar entries and any existing Teams transcripts. On a day with no meetings the digest says so.
- A digest names a person only if they were in the meeting. It leaves out any remark about anyone's mood, tone or performance.
- The agent reads a day's calendar entries only once the consent check says the person agreed to calendar entries, and reads only the signed-in person's own entries (title, time and attendees), with no mail and no documents.
- The agent reads the day's calendar entries before it asks the Summariser for the digest, sends the entries with each meeting's attendees and names no one itself, and sends the request even on a day with no meetings.
- The person sees the digest at 7:30. If the laptop was off or asleep, they see it the first time they are back at it that morning, marked late with the time it arrived.
- A digest not seen by 12:00 is not shown, and the person is told that this morning's digest was missed.
- When the Summariser returns no digest, the person is told there is none that morning, and an old digest is never shown as new.
- Before a meeting on the person's own calendar, the agent checks the consent check, reads that meeting's calendar entry, and asks the Summariser for a note, sending only that meeting's entry, with no transcript and no earlier meeting.
- Reads subject, start, end and attendees only (`$select`); never a body or notes; no `Mail.Read`; no read without a grant.
- A digest not shown by 12:00 is deleted and a missed notice shown on the first wake after it; a late result is marked late, never dropped before the deadline; an old note is never shown as new.
- Target (team, not in the vault): ready within 1 minute of the Summariser reply, Note view opens in under 2 seconds; idle CPU at most 5 percent of one core.

| Task | Size | Component |
|---|---|---|
| Graph sign-in through the OS broker, delegated public client, `Calendars.Read` only | M | SourceReader |
| `calendarDay` and `calendarEntry` with `$select`, and no body | S | SourceReader |
| Delta token held in LocalStore; an invalid token triggers a full re-read of the day | S | SourceReader, LocalStore |
| `Retry-After` on 429 and 5xx; expired sign-in or Conditional Access path logs and shows nothing | S | SourceReader |
| Tests: no read without a grant; no body field ever requested | S | SourceReader, ConsentGate |
| Scheduler: 7:30 and on-wake catch-up, 15-minute delta pass in working hours, idempotent; cadence as one policy object | M | Scheduler |
| `requestDigest` behind a transport interface (on-device first): the person's own entries and attendees only, audience-scoped token, no meeting text in logs | M | NoteClient |
| The deadline guarantee as one unit: Consent retry with backoff and jitter, request kept alive to 12:00, late marking, give-up and log, missed notice. One test suite covers them together | M | Scheduler |
| Show the digest, marked late or missed; dismiss, or expire at end of day | M | NoteView, LocalStore |
| Expiry sweep, shown marker so a note is never pushed twice, seven-day marker deletion | S | LocalStore |
| Measure idle CPU and the two latency targets in test | S | Scheduler, NoteView |

Blocked by: S-02 (Grant). Against a real tenant, also blocked by the app registration approval (CST-002, UNK-069, K-4); status and approval date not confirmed, so build and test against a mocked Graph meanwhile. D-002 (timeouts are config placeholders; final values wait on measurement) and UNK-067 (Summariser budget). OQ-005 (telling the person about an expired sign-in) is not planned: the agent shows nothing and logs. Uses the on-device Summariser path; the remote path is S-07b (deferred).
Release fit: cannot tell for 2027-02-02. Sizes add to at most 37 days for one engineer, and the design names two Rust engineers but not how many days each has before 2027-02-02.

### S-06 Prep note before a meeting
Traces to: CAP-002.FR2@APP-desktop-agent, CAP-004.FR1@APP-desktop-agent, CON-002, EPC-034.AC2, EPC-034.AC3, EPC-034.AC4, EPC-034.AC5
Components: Scheduler, NoteClient, SourceReader, NoteView, LocalStore
Slice: vertical
Done when: a prep note shows ten minutes before a meeting, follows a move, and is never shown for a cancelled meeting.
Acceptance criteria:
- The person sees a prep note for a meeting on their own calendar ten minutes before it starts. If the note is ready late, they still see it until the meeting starts, marked late.
- For a meeting on their own calendar, a person who has switched Heron on gets a short prep note written from that meeting's calendar entry, ready ten minutes before it starts.
- The agent asks early enough for the note to be ready, and shows it ten minutes before the meeting starts.
- A note that is ready after that time is shown as soon as it is ready, marked late, until the meeting starts, and not after.
- If a meeting moves, the note follows the new time. If it is cancelled, no note is shown. A note already shown is not shown again.
- When no note comes, nothing is shown and nothing is said.
- A moved meeting's note follows the new time; a cancelled one shows no note; a slow or empty Summariser reply shows nothing and says nothing; a prep note not shown by the meeting start is deleted.
- The entry is re-read at ten minutes before the meeting, immediately before showing, so a moved or cancelled meeting is never shown stale whatever the staleness bound turns out to be.

| Task | Size | Component |
|---|---|---|
| Ask for a prep note ahead of each meeting, and re-read the entry ten minutes before showing | M | Scheduler |
| `requestPrep`: one entry; nothing shown or said on a slow or empty reply | S | NoteClient |
| Moved and cancelled meetings handled together with the re-read: the note follows the new time, a cancelled note is deleted and never shown | M | Scheduler, SourceReader, LocalStore |
| Show the prep note, marked late; delete it at the meeting start | S | NoteView |
| Tests on the whole mechanism: a move at 09:49, a cancellation after the note is ready, a move during the prep window, a slow Summariser | M | Scheduler, NoteClient |

Blocked by: S-05. OQ-002 (staleness bound; the 15-minute figure is a config proposal, only the value waits), D-002 (timeouts), UNK-067.
Release fit: cannot tell for 2027-02-02. Sizes add to at most 19 days for one engineer, and the design names two Rust engineers but not how many days each has before 2027-02-02.

### S-07a Managed-setting gate for the remote Summariser path
Traces to: CON-002, CST-003
Components: NoteClient
Slice: layer. A gate nobody sees; the original plan's own audit calls it "a gate, not a feature". Flagged, not folded: the team lead says whether it folds into S-05 or stays apart so the CST-003 guarantee has its own test.
Done when: with the managed setting off, no meeting text can leave the laptop for a remote Summariser.
Acceptance criteria:
- No vault epic criterion covers the remote path; the criteria are CST-003 and the design's Gate rule: no meeting text goes to a remote endpoint unless a machine-level managed setting (default off, not user-writable) says the text call is settled.

| Task | Size | Component |
|---|---|---|
| Read the managed setting; refuse the remote endpoint while it is off | M | NoteClient |
| Test, against a fake remote transport that only records that a send was attempted, that no meeting text leaves the laptop while the setting is off. The fake models no authentication, protocol or reply, so no CON-002 answer can invalidate it | S | NoteClient |

Blocked by: S-01 (setting reader pattern) and the S-05 transport interface. Not blocked by OQ-007, UNK-051 or OQ-009: nothing here depends on what the Summariser keeps or how it authenticates callers.
Release fit: cannot tell. It traces to no requirement on a release, and the design names two Rust engineers but not their days.

### S-07b Remote Summariser transport and both-paths tests
Traces to: CON-002, CST-003
Components: NoteClient
Slice: layer
Done when: the remote transport sends only through the gate, with an audience-scoped token and TLS, and both paths pass in CI.
Status: deferred (2026-10-12). The pilot runs on-device only, and the remote path cannot be used until OQ-007, UNK-051 and OQ-009 are answered. Restart it when the blockers clear; the token design assumes a separate token with the Summariser as its own audience, to be confirmed by OQ-007.
Acceptance criteria:
- Remote transport: audience-scoped token, TLS, no meeting text in logs.
- CI covers both paths, with a test-tenant run before 4 December.

| Task | Size | Component |
|---|---|---|
| Remote transport: audience-scoped token, TLS, no meeting text in logs | M | NoteClient |
| CI for both paths, plus a test-tenant run before 4 December | M | NoteClient |

Blocked by: OQ-007, UNK-051, OQ-009.
Release fit: not planned, so nothing to fit.

### S-08 Windows MSIX through Intune
Traces to: CST-007, CST-010
Components: LocalStore (key binding), Scheduler (startup task)
Slice: vertical
Done when: a signed MSIX installs through Intune on a test device and the agent starts, reading the managed profile keys.
Acceptance criteria:
- A signed MSIX installs through Intune on a test device and the agent starts; the managed profile keys (Summariser gate, kill switch, tunables) are read.

| Task | Size | Component |
|---|---|---|
| Signing and pipeline prep with a placeholder Tauri app: certificate, MSIX identity, test-device enrolment, push through Intune. Needs no S-01 code | M | LocalStore |
| Full pipeline with the real binary and the managed profile keys | M | LocalStore |
| Startup task and relaunch backoff | S | Scheduler |

Blocked by: S-01 for the real binary only; certificate holders and ring support (OQ-009). Start the CI runner now and hold the signing-key and certificate ceremony until OQ-009 is answered; use a throwaway certificate on a placeholder build meanwhile (if the certificate subject changes later, earlier feedback from the pipeline is lost, which the team accepted). The only slot is 18 January 2027 (CST-010); UNK-069 says the registration review may end after it.
Release fit: cannot tell. The fixed slot is 18 January 2027 (CST-010); sizes add to at most 12 days for one engineer, and the design names a team Intune expert but not their days.

### S-09 Mac pkg through Jamf
Traces to: CST-007, CST-010
Components: LocalStore (Keychain binding), Scheduler (launch agent)
Slice: vertical
Done when: a signed, notarised pkg installs through Jamf on a test device and the Keychain access control binds the store key to the signed app.
Acceptance criteria:
- A signed, notarised pkg installs through Jamf on a test device; the Keychain access control binds the store key to the signed app.

| Task | Size | Component |
|---|---|---|
| Jamf pkg, signed and notarised | M | LocalStore |
| Launch agent with the same relaunch behaviour as Windows | S | Scheduler |
| Keychain access control check on a test device | S | LocalStore |

Blocked by: OQ-001 (UNK-054, Mac in the first release), OQ-009. The shared code is not blocked; only this story. Runs beside S-08 if OQ-001 is yes; drops from the plan if no.
Release fit: cannot tell. It shares the 18 January 2027 slot (CST-010) with S-08, and the design does not say who builds the Mac package or in how many days.

### S-10 Operations hardening
Traces to: design only: Operations (Monitor, Restart, Tunables); K-1, K-8
Components: Scheduler, LocalStore, NoteView
Slice: vertical
Done when: after three crashes in ten minutes the agent stops relaunching and shows one notice.
Acceptance criteria:
- Every tunable comes from the managed profile with a compiled default and a hard clamp; logs hold no meeting titles, attendees or note text; after three crashes in ten minutes the agent stops relaunching and shows one notice.

| Task | Size | Component |
|---|---|---|
| Tunables from the profile, with defaults and clamps | M | Scheduler |
| Local logs, daily usage counters with no meeting ID, seven-day sweep, `EventSink`, diagnostic export screen | M | LocalStore, NoteView |
| Crash-loop notice and tray state | S | NoteView |

Blocked by: OQ-009 for pushes after the freeze. D-004 (is seven days right) is a pilot measurement, not planned here. The notice wording is a design placeholder.
Release fit: cannot tell. It traces to no requirement on a release; sizes add to at most 12 days for one engineer, and the design names two Rust engineers but not how many days each has.

### S-11 Transcripts calls, built but off
Traces to: CAP-001.FR1@APP-desktop-agent, EPC-035.AC1, EPC-035.AC2, EPC-035.AC3, EPC-035.AC4, EPC-035.AC5
Components: ConsentGate, SourceReader, Scheduler
Slice: vertical
Done when: a person who agreed to transcripts has them read where Microsoft allows it, and a person who agreed to calendar entries only never does.
Status: deferred by the team lead (2026-10-12). It would take half the Rust capacity for something that does not ship while EPC-035 is on no release, and both engineers are needed on S-08, S-09 and S-10. Not sized yet.
Acceptance criteria:
- Where a meeting has a Teams transcript that Heron is allowed to read, Heron reads it for a person who was in that meeting. Where there is none, Heron has the calendar entry only, and the person is told when a note is thin for that reason.
- The agent asks Microsoft for a meeting's transcript only where the consent check says the person agreed to transcripts, and reads one only where the organiser turned transcripts on and the tenant administrators approved reading them.
- The agent reads a transcript only for a person who was in that meeting, and none for a meeting they were not in.
- A person who agreed to calendar entries only never has a transcript read.
- A meeting with no readable transcript gives no error, and the agent works from the calendar entry.
- Once a person withdraws, the agent reads no more transcripts for them.

Blocked by: PG-001. No date for the second registration review is recorded in the vault (UNK-059 open, due 2026-11-06).
Release fit: not planned, so nothing to fit.

## Build order
1. S-01 (tracer), with the D-001 spike and the S-08 placeholder signing prep in parallel: the store, key binding and signing are the earliest failures.
2. S-02 (tracer): ConsentGate unlocks every read.
3. S-05 (tracer, the merged S-04): the first thing a person can see ships here. The Grant is all it needs from S-02.
4. S-03, beside S-05 once S-02's outbox exists.
5. S-06, after S-05: it rides the same Scheduler and NoteClient.
6. S-07a once S-05 fixes the transport interface, off behind the gate. S-07a does not wait on CON-002.
7. S-08 full pipeline, then S-10.
8. S-09 runs beside S-08 if OQ-001 answers yes (same pipeline, same slot, CST-010). If OQ-001 answers no, S-09 moves to Not planned. It stays out of the plan's count until then.

Not in the order, because they are not built: S-04 (merged into S-05), S-07b and S-11 (deferred).

## Critical path
Two things can be critical, and they are different stories.
- Longest chain of work: S-01, S-02, S-05, S-06, all through the two Rust engineers the design names. S-05 is its largest piece. S-03 and S-07a hang off it; S-10 follows packaging.
- Fixed date: S-08. The 18 January 2027 slot (CST-010) does not move. S-08's own work is short; its risk is OQ-009 (signing-key holders, rings and recall) and the certificate ceremony held until it is answered.
- Not decided: whether the Rust chain fits before the slot. Sizes are not dates, so the team measures S-01 and S-02 first. If the chain does not fit, the NoteView task in S-05 ("Show the digest") is the first task to move to someone outside the Rust chain. The design and the vault name no such person, so the team lead names one if it comes to that. Owner: team lead.
- Not decided: if OQ-001 answers yes, S-09 needs someone for the Mac package, and the design names no one for it. Owner: team lead, decided when the answer lands. If OQ-001 answers no, S-09 drops. OQ-009 answered releases the S-08 certificate ceremony at once; that work does not touch the Rust chain.

## Ticket waves
First wave (tickets created this week): all S-01 tasks, all S-02 tasks, and the first S-08 task (signing and pipeline prep with a placeholder app). Held until the first two sprints land and the critical path is seen: S-03, S-05, S-07a and S-10, and S-06 and S-09 behind them, so no tickets exist for work that may shift. The team measures the Rust chain on S-01 and S-02 first. Each ticket title carries the story ID; the plan stays the source of truth and is edited in the same pass as any ticket.

## Coverage
| Target | Stories |
|---|---|
| CAP-005.FR1@APP-desktop-agent | S-02 |
| CON-003 | S-02 |
| CON-004 | S-02, S-03 |
| EPC-032.AC1 | S-02 |
| EPC-032.AC2 | S-02 |
| EPC-032.AC3 | S-02 |
| EPC-032.AC4 | S-02 |
| CAP-005.FR2@APP-desktop-agent | S-03 |
| EPC-032.AC5 | S-03 |
| EPC-032.AC6 | S-03 |
| CAP-001.FR2@APP-desktop-agent | S-05 |
| CAP-002.FR1@APP-desktop-agent | S-05 |
| CAP-003.FR1@APP-desktop-agent | S-05 |
| CAP-003.FR2@APP-desktop-agent | S-05 |
| CON-001 | S-05 |
| CON-002 | S-05, S-06, S-07a, S-07b (deferred) |
| EPC-033.AC1 | S-05 |
| EPC-033.AC2 | S-05 |
| EPC-033.AC3 | S-05 |
| EPC-033.AC4 | S-05 |
| EPC-033.AC5 | S-05 |
| EPC-034.AC1 | S-05 |
| CAP-002.FR2@APP-desktop-agent | S-06 |
| CAP-004.FR1@APP-desktop-agent | S-06 |
| EPC-034.AC2 | S-06 |
| EPC-034.AC3 | S-06 |
| EPC-034.AC4 | S-06 |
| EPC-034.AC5 | S-06 |
| CST-003 | S-07a, S-07b (deferred) |
| CST-007 | S-08, S-09 |
| CST-010 | S-08, S-09 |
| design only: Operations (Monitor, Restart, Tunables); K-1, K-8 | S-10 |
| CAP-001.FR1@APP-desktop-agent | S-11 (deferred, PG-001) |
| EPC-035.AC1 | S-11 (deferred, PG-001) |
| EPC-035.AC2 | S-11 (deferred, PG-001) |
| EPC-035.AC3 | S-11 (deferred, PG-001) |
| EPC-035.AC4 | S-11 (deferred, PG-001) |
| EPC-035.AC5 | S-11 (deferred, PG-001) |
| ConsentGate | S-02, S-05 |
| SourceReader | S-05, S-06 |
| NoteClient | S-05, S-06, S-07a, S-07b |
| ConsentRecorder | S-02, S-03 |
| Scheduler | S-01, S-03, S-05, S-06, S-08, S-09, S-10 |
| LocalStore | S-01, S-03, S-05, S-06, S-08, S-09, S-10 |
| NoteView | S-01, S-02, S-03, S-05, S-06, S-10 |

## Not planned
- S-07b (remote Summariser transport and both-paths tests): deferred by the team lead. Blocked by OQ-007 (what the Summariser keeps and how it authenticates callers), UNK-051 (the text call) and OQ-009 (profile pushes after the freeze). The pilot runs on-device only; S-07a keeps the gate in place.
- PG-001, S-11, CAP-001.FR1 and EPC-035.AC1 to AC5: deferred by the team lead; no review date recorded (UNK-059).
- D-003, D-004: pilot measurements, not build work.
- OQ-003 (mail), OQ-004 (off-laptop events), OQ-005 (telling the person), OQ-006 (reviewable digests), OQ-008 (attendee lawful basis): vault answers owed; the design's default behaviour is what is planned.
- OQ-010 (what "purged" means on disk; design G-011): S-03 tests check for lingering text, the decision with the DPO is not planned.
- Design G-001 (single process): accepted trade-off; its mitigations are in S-10 and the kill switch in S-01.
- Design G-002 (no fleet-wide detection): waits on OQ-004; local logs only (S-10).
