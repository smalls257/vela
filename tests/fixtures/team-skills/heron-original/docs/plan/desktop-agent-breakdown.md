---
slug: desktop-agent
status: complete-with-gaps
deferred: []
gaps:
  - id: PG-001
    what: "EPC-035.AC1 to AC5 have no story: S-11 (transcript calls, built but off) is deferred"
    acknowledged_by: team lead
    why: "It would take half the Rust capacity for something that does not ship while EPC-035 is on no release; both engineers are needed on S-08, S-09 and S-10"
    revisit: "When the second registration review date is known (UNK-059), or EPC-035 joins a release"
last_session: 2026-10-12T00:00:00Z
prereqs:
  - path: docs/tech-design/desktop-agent.md
    expected_status: complete-with-gaps
---

# Work breakdown — Desktop agent

Covers APP-desktop-agent (INI-001 @ 051d15a). Inputs: the design `docs/tech-design/desktop-agent.md` at `complete-with-gaps`, the vault's allocated requirements, contracts and epic criteria, ADR-0001. Sizes are S (up to about 2 days), M (3 to 5 days), L (1 to 2 weeks) for one engineer. They are for ordering, not commitments.

## Summary
| Story | Traces to | Size total | Blocked by |
|---|---|---|---|
| S-01 Walking skeleton | LocalStore, NoteView, Scheduler; D-001 | M, M, S, S, S, M | none |
| S-02 Switch on | CAP-005.FR1, CON-003, CON-004, EPC-032.AC1-4 | S, M, M, S | S-01; OQ-005 (wording) |
| S-03 Withdraw | CAP-005.FR2, EPC-032.AC5-6, CON-004 | M, S, S, M, L | S-02; OQ-010 |
| S-05 Morning digest (merged S-04) | CAP-001.FR1-2, CAP-002.FR1, CAP-003.FR1-2, CON-001, CON-002, EPC-033.AC1-5, EPC-034.AC1 | M, S, S, S, S, M, M, M, M, S, S | S-02; CST-002/UNK-069 for real tenant; D-002, UNK-067 |
| S-06 Prep note | CAP-002.FR2, CAP-004.FR1, EPC-034.AC2-5 | M, S, M, S, M | S-05; OQ-002, D-002, UNK-067 |
| S-07a Remote gate | CON-002, CST-003 | M, S | S-01, S-05 |
| S-07b Remote transport (deferred) | CON-002, CST-003 | not planned | OQ-007, UNK-051, OQ-009 |
| S-08 Windows MSIX | CST-007, CST-010 | M, M, S | S-01 (real binary); OQ-009 |
| S-09 Mac pkg | CST-007, CST-010 | M, S, S | OQ-001, OQ-009 |
| S-10 Operations hardening | Operations, K-1, K-8 | M, M, S | OQ-009 |
| S-11 Transcripts (deferred) | EPC-035.AC1-5 | not planned | PG-001 |

## Stories

### S-01 Walking skeleton
Traces to: LocalStore, NoteView, Scheduler (shell only); Operations (kill switch, schema version).
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

### S-02 Switch on, with consent recorded
Traces to: CAP-005.FR1@APP-desktop-agent, CON-003, CON-004, EPC-032.AC1 to AC4. Components: ConsentGate, ConsentRecorder, NoteView.
- Acceptance criteria are those of EPC-032 AC1 to AC4 and CAP-005.FR1 in the vault, read there at INI-001 @ 051d15a, not copied here.
- A choice not confirmed by Consent and identity counts as not kept (design, Failure behavior).

| Task | Size | Component |
|---|---|---|
| `Grant` type constructible only inside the module, and the Consent check with its 5 s placeholder timeout, never a cached yes | S | ConsentGate |
| Durable outbox with confirmed and unconfirmed state, retried until confirmed, with its own tests (Consent down, restart mid-send, duplicate confirmation) | M | ConsentRecorder |
| Switch-on screen with per-source choices and an unconfirmed-state display, built against a stub of `switchOn`, `withdraw`, `state` | M | NoteView |
| Wire the screen to the real outbox once its tests pass | S | NoteView, ConsentRecorder |

Blocked by: S-01 (store). The wording shown when Consent and identity is down waits on OQ-005; until then the agent shows nothing and logs.

### S-03 Withdraw
Traces to: CAP-005.FR2@APP-desktop-agent, EPC-032.AC5, EPC-032.AC6, CON-004. Components: LocalStore, ConsentRecorder, Scheduler, NoteView.
- Acceptance criteria are those of EPC-032 AC5, AC6 and CAP-005.FR2 in the vault, not copied here.
- Local effect first, network second; switch-on is blocked while a withdrawal is unconfirmed (design, Key flows: withdrawal).

| Task | Size | Component |
|---|---|---|
| Outbox write and `purgeAll` (notes, delta token, logs) in one SQLite transaction where the data is rows; idempotent; rerun on every launch while a withdrawal is unconfirmed | M | LocalStore, ConsentRecorder |
| Stop the Scheduler and cancel in-flight reads and requests, discarding late results | S | Scheduler |
| Withdraw control with "not yet recorded" and "withdrawal recorded" states; switch-on blocked while unconfirmed | S | NoteView |
| Lost-key or corrupt-store path: fresh store, safety withdrawal, re-consent notice (D-003 measures how often) | M | LocalStore, ConsentRecorder |
| Fault-injection harness and crash tests at five points: before commit, during commit (kill loop on the real store), after commit before the network call, during the log-file purge, after the network call before the confirmation is stored. Also withdrawal while a request is in flight, and Consent down for a long time. Check whether deleted text lingers in free pages or the journal | L | LocalStore, ConsentRecorder, Scheduler |

Blocked by: S-02 (outbox). Assumes CON-004 tolerates a duplicate withdrawal; not recorded in the vault, so confirm with Consent and identity's owner. Residual-text check: a note for `tech-design-grill`, not decided here.

### S-04 (merged into S-05)
Merged into S-05 on 2026-10-12: reading calendar entries shows nothing a person can see, so it is not a story of its own (NEG-AUDIT, Distributed Monolith). The ID is retired, not reused. Its targets and tasks are in S-05.

### S-05 Morning digest, from calendar to screen
Traces to: CAP-001.FR1@APP-desktop-agent, CAP-001.FR2@APP-desktop-agent, CAP-002.FR1@APP-desktop-agent, CAP-003.FR1@APP-desktop-agent, CAP-003.FR2@APP-desktop-agent, CON-001, CON-002, EPC-033.AC1 to AC5, EPC-034.AC1. Components: ConsentGate, SourceReader, Scheduler, NoteClient, NoteView, LocalStore.
- Acceptance criteria are those of CAP-001.FR1, FR2, CAP-002.FR1, CAP-003.FR1, FR2, EPC-033 AC1 to AC5 and EPC-034 AC1 in the vault, not copied here.
- Reads subject, start, end and attendees only (`$select`); never a body or notes; no `Mail.Read`; no read without a grant.
- A digest not shown by 12:00 is deleted and a missed notice shown on the first wake after it; a late result is marked late, never dropped before the deadline; an old note is never shown as new.
- Target (team, not in the vault): ready within 1 minute of the Summarizer reply, Note view opens in under 2 seconds; idle CPU at most 5 percent of one core.
- Demo: a granted person sees their digest on screen, from a mocked Graph and the on-device Summarizer path.

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

Blocked by: S-02 (Grant). Against a real tenant, also blocked by the app registration approval (CST-002, UNK-069, K-4); status and approval date not confirmed, so build and test against a mocked Graph meanwhile. D-002 (timeouts are config placeholders; final values wait on measurement) and UNK-067 (Summarizer budget). OQ-005 (telling the person about an expired sign-in) is not planned: the agent shows nothing and logs. Uses the on-device Summarizer path; the remote path is S-07b (deferred).

### S-06 Prep note before a meeting
Traces to: CAP-002.FR2@APP-desktop-agent, CAP-004.FR1@APP-desktop-agent, CON-002, EPC-034.AC2 to AC5. Components: Scheduler, NoteClient, SourceReader, NoteView, LocalStore.
- Acceptance criteria are those of CAP-002.FR2, CAP-004.FR1 and EPC-034 AC2 to AC5 in the vault, not copied here.
- A moved meeting's note follows the new time; a canceled one shows no note; a slow or empty Summarizer reply shows nothing and says nothing; a prep note not shown by the meeting start is deleted.
- The entry is re-read at ten minutes before the meeting, immediately before showing, so a moved or canceled meeting is never shown stale whatever the staleness bound turns out to be.

| Task | Size | Component |
|---|---|---|
| Ask for a prep note ahead of each meeting, and re-read the entry ten minutes before showing | M | Scheduler |
| `requestPrep`: one entry; nothing shown or said on a slow or empty reply | S | NoteClient |
| Moved and canceled meetings handled together with the re-read: the note follows the new time, a canceled note is deleted and never shown | M | Scheduler, SourceReader, LocalStore |
| Show the prep note, marked late; delete it at the meeting start | S | NoteView |
| Tests on the whole mechanism: a move at 09:49, a cancellation after the note is ready, a move during the prep window, a slow Summarizer | M | Scheduler, NoteClient |

Blocked by: S-05. OQ-002 (staleness bound; the 15-minute figure is a config proposal, only the value waits), D-002 (timeouts), UNK-067.

### S-07a Managed-setting gate for the remote Summarizer path
Traces to: CON-002, CST-003; NoteClient gate (design, Components). Components: NoteClient.
- No vault epic criterion covers the remote path; the criteria are CST-003 and the design's Gate rule: no meeting text goes to a remote endpoint unless a machine-level managed setting (default off, not user-writable) says the text call is settled.

| Task | Size | Component |
|---|---|---|
| Read the managed setting; refuse the remote endpoint while it is off | M | NoteClient |
| Test, against a fake remote transport that only records that a send was attempted, that no meeting text leaves the laptop while the setting is off. The fake models no authentication, protocol or reply, so no CON-002 answer can invalidate it | S | NoteClient |

Blocked by: S-01 (setting reader pattern) and the S-05 transport interface. Not blocked by OQ-007, UNK-051 or OQ-009: nothing here depends on what the Summarizer keeps or how it authenticates callers.

### S-07b Remote Summarizer transport and both-paths tests (deferred)
Traces to: CON-002, CST-003. Components: NoteClient.
Deferred (2026-10-12): the pilot runs on-device only, and the remote path cannot be used until OQ-007, UNK-051 and OQ-009 are answered. Two tasks were sized: the remote transport (M: audience-scoped token, TLS, no meeting text in logs) and CI for both paths plus a test-tenant run before 4 December (M). Restart it when the blockers clear; the token design assumes a separate token with the Summarizer as its own audience, to be confirmed by OQ-007. Not planned; see Not planned.

### S-08 Windows MSIX through Intune
Traces to: CST-007, CST-010; design Operations (Deploy). Components: LocalStore (key binding), Scheduler (startup task).
- A signed MSIX installs through Intune on a test device and the agent starts; the managed profile keys (Summarizer gate, kill switch, tunables) are read.

| Task | Size | Component |
|---|---|---|
| Signing and pipeline prep with a placeholder Tauri app: certificate, MSIX identity, test-device enrollment, push through Intune. Needs no S-01 code | M | LocalStore |
| Full pipeline with the real binary and the managed profile keys | M | LocalStore |
| Startup task and relaunch backoff | S | Scheduler |

Note: start the CI runner now; hold the signing-key and certificate ceremony until OQ-009 is answered. Use a throwaway certificate on a placeholder build meanwhile; if the certificate subject changes later, earlier feedback from the pipeline is lost, which the team accepted.

Blocked by: S-01 for the real binary only; certificate holders and ring support (OQ-009). The only slot is 18 January 2027 (CST-010); UNK-069 says the registration review may end after it.

### S-09 Mac pkg through Jamf
Traces to: CST-007, CST-010. Components: LocalStore (Keychain binding), Scheduler (launch agent).
- A signed, notarized pkg installs through Jamf on a test device; the Keychain access control binds the store key to the signed app.

| Task | Size | Component |
|---|---|---|
| Jamf pkg, signed and notarized | M | LocalStore |
| Launch agent with the same relaunch behavior as Windows | S | Scheduler |
| Keychain access control check on a test device | S | LocalStore |

Blocked by: OQ-001 (UNK-054, Mac in the first release), OQ-009. The shared code is not blocked; only this story. Runs beside S-08 if OQ-001 is yes; drops from the plan if no.

### S-10 Operations hardening
Traces to: design Operations (Monitor, Restart, Tunables), K-1, K-8. Components: Scheduler, LocalStore, NoteView.
- Every tunable comes from the managed profile with a compiled default and a hard clamp; logs hold no meeting titles, attendees or note text; after three crashes in ten minutes the agent stops relaunching and shows one notice.

| Task | Size | Component |
|---|---|---|
| Tunables from the profile, with defaults and clamps | M | Scheduler |
| Local logs, daily usage counters with no meeting ID, seven-day sweep, `EventSink`, diagnostic export screen | M | LocalStore, NoteView |
| Crash-loop notice and tray state | S | NoteView |

Blocked by: OQ-009 for pushes after the freeze. D-004 (is seven days right) is a pilot measurement, not planned here. The notice wording is a design placeholder.

### S-11 Transcripts calls, built but off (deferred)
Traces to: EPC-035.AC1 to AC5. Components: ConsentGate, SourceReader, Scheduler.
Deferred by the team lead (2026-10-12): it would take half the Rust capacity for something that does not ship while EPC-035 is on no release, and both engineers are needed on S-08, S-09 and S-10. No date for the second registration review is recorded in the vault (UNK-059 open, due 2026-11-06). Not planned; see Not planned.

## Build order
1. S-01, with the D-001 spike and the S-08 placeholder signing prep in parallel: the store, key binding and signing are the earliest failures.
2. S-02: ConsentGate unlocks every read.
3. S-05 (the merged S-04), and S-03 beside it: the Grant is all S-05 needs, and S-03 needs the outbox. The first thing a person can see ships here.
4. S-06, after S-05: it rides the same Scheduler and NoteClient.
5. S-07a once S-05 fixes the transport interface, off behind the gate. S-07a does not wait on CON-002. S-07b is deferred.
6. S-08 full pipeline (S-09 beside it, if Mac is in), then S-10.
7. S-09 runs beside S-08 if OQ-001 answers yes (same pipeline, same slot, CST-010). If OQ-001 answers no, S-09 moves to Not planned. It stays out of the plan's count until then.

## Critical path
Two things can be critical, and they are different stories.
- Longest chain of work: S-01, S-02, S-05, S-06, all through the two Rust engineers. S-05 is its largest piece. S-03 and S-07a hang off it; S-10 follows packaging.
- Fixed date: S-08. The 18 January 2027 slot (CST-010) does not move. S-08's own work is short; its risk is OQ-009 (signing-key holders, rings and recall) and the certificate ceremony held until it is answered.
- Not decided: whether the Rust chain fits before the slot. Sizes are not dates, so the team measures S-01 and S-02 first. If the chain does not fit, the NoteView task in S-05 ("Show the digest") is the first task to move to the Swift person. The Intune person stays on packaging. Owner: team lead.
- Not decided: if OQ-001 answers yes, the Swift person is wanted on S-09 and is also the first choice for the NoteView task in S-05. The plan does not settle this. Owner: team lead, decided when the answer lands. If OQ-001 answers no, S-09 drops and the Swift person is free. OQ-009 answered releases the S-08 certificate ceremony at once; that work does not touch the Rust chain.


## Ticket waves
First wave (tickets created this week): all S-01 tasks, all S-02 tasks, and the first S-08 task (signing and pipeline prep with a placeholder app). Held until the first two sprints land and the critical path is seen: S-03, S-05, S-07a and S-10, and S-06 and S-09 behind them, so no tickets exist for work that may shift. The team measures the Rust chain on S-01 and S-02 first. Script: `docs/plan/desktop-agent-tickets.sh`. Each ticket title carries the story ID; the plan stays the source of truth and is edited in the same pass as any ticket.

## Coverage
| Target | Stories |
|---|---|
| CAP-001.FR1@APP-desktop-agent, CAP-001.FR2@APP-desktop-agent | S-05 |
| CAP-002.FR1@APP-desktop-agent | S-05 |
| CAP-002.FR2@APP-desktop-agent | S-06 |
| CAP-003.FR1@APP-desktop-agent, CAP-003.FR2@APP-desktop-agent | S-05 |
| CAP-004.FR1@APP-desktop-agent | S-06 |
| CAP-005.FR1@APP-desktop-agent | S-02 |
| CAP-005.FR2@APP-desktop-agent | S-03 |
| CON-001 | S-05 |
| CON-002 | S-05, S-07a (S-07b deferred) |
| CON-003 | S-02 |
| CON-004 | S-02, S-03 |
| EPC-032.AC1 to AC4 | S-02 |
| EPC-032.AC5, AC6 | S-03 |
| EPC-033.AC1 to AC5 | S-05 |
| EPC-034.AC1 | S-05 |
| EPC-034.AC2 to AC5 | S-06 |
| EPC-035.AC1 to AC5 | none: S-11 deferred (gap) |
| ConsentGate | S-02 |
| SourceReader | S-05, S-06 |
| NoteClient | S-05, S-07a |
| ConsentRecorder | S-02, S-03 |
| Scheduler | S-01, S-03, S-05, S-06 |
| LocalStore | S-01, S-03, S-05, S-06 |
| NoteView | S-01, S-02, S-03, S-05, S-06 |

## Not planned
- S-07b (remote Summarizer transport and both-paths tests): deferred by the team lead. Blocked by OQ-007 (what the Summarizer keeps and how it authenticates callers), UNK-051 (the text call) and OQ-009 (profile pushes after the freeze). The pilot runs on-device only; S-07a keeps the gate in place.
- PG-001, S-11 and EPC-035.AC1 to AC5: deferred by the team lead; no review date recorded (UNK-059).
- D-003, D-004: pilot measurements, not build work.
- OQ-003 (mail), OQ-004 (off-laptop events), OQ-005 (telling the person), OQ-006 (reviewable digests), OQ-008 (attendee lawful basis): vault answers owed; the design's default behavior is what is planned.
- OQ-010 (what "purged" means on disk; design G-011): S-03 tests check for lingering text, the decision with the DPO is not planned.
- Design G-001 (single process): accepted trade-off; its mitigations are in S-10 and the kill switch in S-01.
- Design G-002 (no fleet-wide detection): waits on OQ-004; local logs only (S-10).

## NEG-AUDIT (2026-10-12, after the S-04 merge)
- Paper Tiger: yes. Every allocated row, contract and epic criterion except EPC-035.AC1 to AC5 has a story; that one is PG-001. CAP-001.FR2 is calendar entries, so S-05 delivers it; mail is OQ-003, not a missing story.
- Distributed Monolith: yes after the merge. S-05 is the first story with behavior a person can see; S-08 and S-09 ship on their own pipelines; S-07a is a gate, not a feature. S-01 and S-02 still chain, and the single process is the acknowledged design G-001.
- Black Box: yes, acknowledged (design G-002). Silent Fallback: yes, acknowledged (design G-006, OQ-005): shows nothing and logs by design.
- Leaky Narrative, Infected Core, Computational Friction, Forensic Coding, God Class, Fossil Comments: yes.
- Result: `complete-with-gaps` stands, for PG-001 only.
