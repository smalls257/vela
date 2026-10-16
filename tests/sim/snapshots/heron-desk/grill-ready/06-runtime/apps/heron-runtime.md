---
id: RUN-heron
type: app-runtime
title: Heron runtime
state: assumption
owner: "@sim-lead"
authored: authored
sources: [2026-10-11-first-release-boundary]
---

# Heron runtime

Heron takes part in one journey, [[FLO-001-prep-note-before-a-client-call|a person gets a prep note before a client call]]. It runs on the person's own laptop and holds nothing off the device.

## On failure

When the calendar cannot be read, the folder is missing or the note is late, Heron shows no note and says why. It never shows a guessed note.

## History

- **Options considered:** One laptop app (picked); Collector and note builder: rejected, "I don't own anyone yet, and two apps means two ownership questions when I can't answer one."; Laptop agent and cloud summarizer: rejected, "No text off the device in release one, that's the line we hold for the pack."
