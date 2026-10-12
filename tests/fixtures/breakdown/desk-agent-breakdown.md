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

- A Mac user installs the agent from one signed package with no warning from the OS.
- An update replaces the installed version without losing settings.

| Task | Size | Component |
|---|---|---|
| Sign and notarise the Mac build | M | Installer |
| Windows MSI package | S | Installer |

Blocked by: none

### S-02 Capture a meeting locally

Traces to: CAP-002.FR2@APP-desktop-agent, EPC-003.AC1; components: Audio Capture, Local Store

- Audio is transcribed on the laptop and never leaves it before the security review passes.

| Task | Size | Component |
|---|---|---|
| Capture system audio | L | Audio Capture |
| Store transcripts encrypted | M | Local Store |

Blocked by: S-01

### S-03 Send the digest

Traces to: CON-004, EPC-003.AC2; components: Digest Sender

- A digest names only people who were in the meeting.
- A digest carries no remark about anyone's mood.

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
