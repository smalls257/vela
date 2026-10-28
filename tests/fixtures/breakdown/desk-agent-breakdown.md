---
type: work-breakdown
slug: desk-agent
status: complete-with-gaps
prereqs:
  - docs/tech-design/desk-agent.md
gaps:
  - id: GAP-1
    note: Legal has not answered the retention question.
---
# Desk Agent work breakdown

This plan covers the desktop agent for the pilot. Its input is `docs/tech-design/desk-agent.md` at status
complete-with-gaps. Sizes are S (up to about 2 days), M (3 to 5 days) and L (1 to 2 weeks) for one engineer; they are for
ordering, not commitments.

## Summary

| Story | Traces to | Size total | Blocked by |
|---|---|---|---|
| S-01 Signed installer | CAP-001.FR1@APP-desktop-agent | M+S | none |
| S-02 Capture a meeting locally | CAP-002.FR2@APP-desktop-agent, EPC-003.AC1 | L+M | S-01 |
| S-03 Send the digest | CON-004, EPC-003.AC2 | M | S-02, Q-7 |

### S-01 Signed installer

Traces to: CAP-001.FR1@APP-desktop-agent; components: Installer, Updater
Summary: This story gives people one signed installer for the desk agent. A Mac user installs it from a single package and sees no warning from the operating system. Updates arrive the same way and keep each person's settings. It's the first story in the plan, so nothing has to come before it.

- A Mac user installs the agent from one signed package with no warning from the OS.
- An update replaces the installed version without losing settings.
Ticket criteria (from d7bdbf):
Installing and updating:
- A Mac user installs the agent from one signed package, with no warning from the operating system. (covers AC1)
- An update replaces the installed version and keeps the person's settings. (covers AC2)

| Task | Size | Component |
|---|---|---|
| Sign and notarize the Mac build | M | Installer |
| Windows MSI package | S | Installer |

Blocked by: none

### S-02 Capture a meeting locally

Traces to: CAP-002.FR2@APP-desktop-agent, EPC-003.AC1; components: Audio Capture, Local Store
Summary: This story captures a meeting's audio on the laptop and turns it into a transcript there. The transcript is stored encrypted on the same laptop. Nothing leaves the laptop until the security review passes. It comes after the signed installer, since it ships inside it.

- Audio is transcribed on the laptop and never leaves it before the security review passes.
Ticket criteria (from d21b64):
Keeping the meeting on the laptop:
- Audio is transcribed on the laptop, and nothing leaves it before the security review passes. (covers AC1)

| Task | Size | Component |
|---|---|---|
| Capture system audio | L | Audio Capture |
| Store transcripts encrypted | M | Local Store |

Blocked by: S-01

### S-03 Send the digest

Traces to: CON-004, EPC-003.AC2; components: Digest Sender
Summary: This story builds the digest from a meeting's transcript and sends it. A digest names only the people who were in the meeting. It says nothing about anyone's mood. It comes after the meeting capture, and it also waits on who a digest may name and on the security review.

- A digest names only people who were in the meeting.
- A digest carries no remark about anyone's mood.
Ticket criteria (from b0c809):
What a digest says:
- A digest names only people who were in the meeting, and makes no remark about anyone's mood. (covers AC1, AC2)

| Task | Size | Component |
|---|---|---|
| Build the digest from a transcript | M | Digest Sender |

Blocked by: S-02, Q-7 (open question: who may a digest name), the CISO review (outside party)

## Build order

1. S-01: everything installs through it.
2. S-02: the digest needs a transcript.
3. S-03: last, behind the CISO review.

## Coverage

| Target | Stories |
|---|---|
| CAP-001.FR1@APP-desktop-agent | S-01 |
| CAP-002.FR2@APP-desktop-agent | S-02 |
| CON-004 | S-03 |

## Not planned

- GAP-1: retention of transcripts, until Legal answers.
- DEF-2: a Linux build, deferred past the pilot.
