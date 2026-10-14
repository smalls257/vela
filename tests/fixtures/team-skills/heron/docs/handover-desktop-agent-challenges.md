# Handover: items to raise with /planner:challenge

For the senior. Design `docs/tech-design/desktop-agent.md` (complete-with-gaps), vault INI-001 @ 051d15a. Each item below is an open question in the design that challenges a vault item; raise it with `/planner:challenge <ID>`. The design never edits the vault. Ordered by urgency: the first two are tied to the January freeze (CST-010) and S-07 must be built before the 4 December outcome. Text is as written in the design.

## 1. OQ-007: What does the Summarizer keep, log and train on, and does withdrawal reach it?
Raise: `/planner:challenge CON-002`
**What we know:** The agent sends calendar entries, and later transcript text, over CON-002. The vault records the shape of the request and no authentication, retention, logging, no-training rule or transport. CON-002 has no deletion call. Scenario: a person withdraws and the agent purges the laptop, but the Summarizer still holds their meeting text. CST-003 forbids meeting text leaving a laptop until the 4 December outcome, and the text call is open as UNK-051. The design adds three controls on its own side: an audience-scoped token, TLS with no text in logs, and a gate that refuses a remote Summarizer endpoint until a managed setting says the text call is settled.
**What would unblock:** The Summarizer's owner and the product owner record in CON-002 who authenticates callers, what is kept, logged and trained on and for how long, and whether withdrawal reaches it, before the January freeze (CST-010). The endpoint lead and CISO also say whether a configuration profile may change the gate after the freeze.
**Affects:** NoteClient, Integration points, CON-002, EPC-033, EPC-034.
**Challenges:** CON-002

## 2. OQ-009: Can the endpoint team stage the package in rings and recall a bad build, and who holds the signing keys?
Raise: `/planner:challenge CST-010`
**What we know:** The agent ships through Intune and Jamf in the endpoint lead's one slot on 18 January 2027, and he will not raise an earlier one (CST-010). The vault does not say whether Intune and Jamf stage the pilot group in rings, how a build is pulled or superseded, who holds the signing certificates and Apple notarization credentials, who renews them, or how WebView2 and macOS updates are tracked after the slot. The pilot is Client Delivery London, so a bad build reaches that group, not the whole firm. Without rings the only rollback is the kill switch, and the agent lead cannot absorb a second build with the team available.
**What would unblock:** The endpoint lead answers on rings and recall, and names the key holders. The agent lead needs a yes on ring support before the freeze.
**Affects:** Operations (Deploy), Tech stack, ADR-0001.
**Challenges:** CST-010

## 3. OQ-001: Is the Mac in the first release?
Raise: `/planner:challenge UNK-054`
**What we know:** The team has chosen Tauri for one codebase and signed Mac pkg plus Windows MSIX by the pilot. The vault lists UNK-054 (Mac in the first release) as open, owned by the product owner; the CIO brief says Windows only, the tenant note counts about 1,100 Macs.
**What would unblock:** Product owner's answer to UNK-054.
**Affects:** Tech stack, Operations (packaging), Trace for CST-007 and CST-010.
**Challenges:** UNK-054

## 4. OQ-002: How stale may a moved or canceled meeting be before the prep note follows it?
Raise: `/planner:challenge EPC-034.AC4`
**What we know:** EPC-034 criterion 4 says a moved meeting's note follows the new time and a canceled one shows no note, with no time bound. Scenario: a meeting moves from 10:00 to 11:00 at 09:40. The note is ready for 09:50; the display-time re-read at 09:50 catches the move, but a move at 09:49 and a 15-minute delta pass could leave the ask or the early timers wrong.
**What would unblock:** A bound from the product owner. Design proposal: 15 minutes, with the display-time re-read as the backstop so a moved or canceled meeting is never shown stale.
**Affects:** Scheduler; EPC-034.AC4.
**Challenges:** EPC-034.AC4

## 5. OQ-003: Is mail read in the first release?
Raise: `/planner:challenge CAP-001.FR2`
**What we know:** The team lead's brief lists `Mail.Read` as a required scope with `Calendars.Read`, and cites a ruling for mail text read on the laptop. The vault says the opposite: CAP-001 "Heron reads no mail and no documents in the first release", CAP-001.FR2 ("for no mail or documents"), EPC-033 AC1. CAP-005.FR1 offers only two sources, calendar entries and transcripts, so there is no consent choice for mail. Mail would also widen the data list (UNK-057), the lawful-basis question (UNK-071) and the works council's review. The design reads calendar entries only, and the pilot registration requests `Calendars.Read` only, until the vault changes.
**What would unblock:** The solution lead records mail as a requirement (a capability, a consent source, a contract change) or confirms it is out. The brief and ruling cited were not in the vault, so I could not read them.
**Affects:** Integration points (scope), ConsentGate, SourceReader, NoteClient, CON-001, CAP-005.FR1.
**Challenges:** CAP-001.FR2

## 6. OQ-005: Is the person told when Consent and identity is down, or their sign-in has expired?
Raise: `/planner:challenge EPC-033`
**What we know:** The runtime page (RUN-desktop-agent, On failure) says that if the Summarizer is down or slow the agent "shows nothing that morning and says so", but that if Consent and identity is down the agent "reads nothing and shows no note", with no mention of telling the person. EPC-033 puts this out of scope ("the runtime page holds it, and no requirement does"). Scenario: at 7:30 the Consent check times out, the person sees nothing and gets no reason. The design shows nothing and writes a local log entry. The team lead suggests a generic "your digest couldn't be prepared" covers both failures safely; that wording is not in the vault.
**Second case:** A person's Microsoft sign-in expires, or Conditional Access blocks it, so the agent cannot read. EPC-032 AC3 covers a choice not confirmed at switch-on, not a sign-in that stops working later, so the vault is silent on telling the person to sign in again.
**What would unblock:** The solution lead says whether silence on a Consent outage or an expired sign-in is the intent or a gap to close, and if a gap, owns the wording and which requirement carries it.
**Affects:** ConsentGate, NoteView, EPC-033 (digest), EPC-034 (prep note says nothing by AC5).
**Challenges:** EPC-033

## 7. OQ-004: May the agent send per-user event counts for adoption metrics?
Raise: `/planner:challenge UNK-057`
**What we know:** The team lead says the CIO wants adoption metrics (C2) and that K9 opens the door to Datadog; neither is in the vault. The vault says the agent reports no adoption by team in this release (APP-desktop-agent), `concern-data` is unknown for it, UNK-057 asks whether the data list includes the team adoption dashboard, and no vendor or agreement for Datadog is recorded. Scenario: a "prep note shown" event at 09:50 for a named person reveals a meeting at 10:00 that the calendar then identifies; a "withdrew" event is consent data. The design keeps a local-only `EventSink` and sends nothing.
**What would unblock:** A decision by the solution lead and product owner with the DPO and works council, recorded as a contract from the agent to the provider and on the data list; and the CISO's view on the off-laptop send.
**Affects:** Operations (Monitor), EventSink, new contract if approved. An aggregate health signal (failures per day, no person or meeting) is one option to decide with it.
**Challenges:** UNK-057

## 8. OQ-008: Does the lawful basis cover other attendees in a calendar entry?
Raise: `/planner:challenge UNK-071`
**What we know:** UNK-071 asks the DPO for the lawful basis for each source, which is about the person who switched Heron on. A calendar entry also names other attendees, who have not agreed and may be outside the pilot. Scenario: a London pilot user's meeting has a Frankfurt colleague as an invitee; the entry, with that name, goes to the Summarizer. Frankfurt stays out of the pilot (CST-006). The design reads only subject, start, end and attendees. Whether the pilot group is set by office or by team is open as UNK-055. If the DPO says attendees outside the pilot may not be sent, the contingency is a local roster filter before sending, which needs a roster source the vault does not record and the answer before the request freezes.
**What would unblock:** The DPO answers for attendees as well as the person, and the pilot lead says how the pilot group is set (UNK-055).
**Affects:** SourceReader, NoteClient, CST-004, CST-006, CAP-003.FR2.
**Challenges:** UNK-071

## 9. OQ-006: Does the business want shown digests to be reviewable later?
Raise: `/planner:challenge CAP-002.FR1`
**What we know:** CAP-002 and EPC-033 ask only that the digest is shown. The vault names no review or history, and nobody is recorded as deciding it. The design keeps note text until the person dismisses it or it expires (end of the local day for a digest), then deletes it, with no archive. An archive would be new retention on the laptop and a change to the data list for the works council and DPO (UNK-057).
**What would unblock:** The product owner says whether the pilot needs review of past digests.
**Affects:** LocalStore, NoteView, data list.
**Challenges:** CAP-002.FR1

## Not a vault challenge: OQ-010
What does "purged" mean on disk after withdrawal?
The team decides this with the DPO; it is not raised with /planner:challenge. See OQ-010 in the design.
