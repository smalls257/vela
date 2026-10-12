# ADR-0001: Build the note in two layers, a deterministic floor with an optional on-device rewriter

**Status:** accepted
**Date:** 2026-10-12
**Slug:** desktop-agent

## Context
The note has hard content rules: it uses only call tool records and chosen-folder files, adds no open point of its own, names no remark on mood, tone or performance, and never reaches back past the most recent earlier call (CAP-001.FR3, EPC-003.AC1-AC5 @ c410421). No text may leave the laptop (CST-3), so there is no hosted model. The app has a 500 MB memory budget (user's figure, not in the vault), and the pilot laptops are unmeasured (UNK-027). The vault already says that if no model on the laptop writes a good enough note, the note is plainer.

## Decision
`NoteAssembler` builds a complete, checked note with no model. It picks the people, the earlier call and the open points, and runs the content check on every note. An optional `Rewriter` running a bundled on-device model turns the checked text into a short account only when it can finish before T-10. Its output goes through the same check. When the model is absent, too slow or declined, the person sees the floor note. The content check lives in the floor, not in the rewriter.

## Alternatives considered
- **A model writes the whole note** — "no invented open points" would rest on prompting, and the note would fail whenever the model is missing, too slow or over the memory budget.
- **A hosted model with redaction** — ruled out by CST-3 with or without redaction.
- **Rewriter first, with a floor as a fallback only** — the checks would then live in code that may not run.

## Consequences
- **Positive:** the content rules are code the tests can enforce; the app works offline with no model; the first iteration can ship without the model if memory is tight.
- **Negative:** more Rust work up front; floor notes read as extracts, so "short account" (EPC-003.AC1) needs the product owner's acceptance; a word list for mood and tone is incomplete (OQ-006).
- **Reversibility cost:** adding the model later is small. Dropping the floor and trusting a model with the content rules means rewriting the checks and re-testing every criterion.
