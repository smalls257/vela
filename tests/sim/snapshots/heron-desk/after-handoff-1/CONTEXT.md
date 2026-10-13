# Project Context

> Domain glossary and shared mental model for the Heron desktop agent design. The initiative's own terms live in the vault's `12-glossary.md`; this file holds only the design's terms.

## Glossary

### Floor
**Definition:** The deterministic part of the Note builder (`NoteAssembler`). It builds a complete, checked note from the calendar entry, call tool records and chosen-folder files with no model.
**Not to be confused with:** the Rewriter, which is optional and only polishes text the floor has already checked.
**Examples:** With no model on the laptop, the person sees the floor note.

### Rewriter
**Definition:** The optional on-device model that turns the floor's extracted text into a short account. It never decides which points exist.
**Not to be confused with:** a hosted model. None is allowed (CST-3).

### Surfaced note
**Definition:** A note built for a client call and kept in the encrypted store with its state (built, shown, dismissed, late) for 30 days.
**Not to be confused with:** a note on screen; the stored row outlives the window.

### Active rule
**Definition:** The provisional rule, set by managed settings, that decides which calls are client calls and which earlier call is the same client. The Note view shows it.
**Not to be confused with:** a requirement; the rule is an assumption until UNK-021 and UNK-022 close.

### Withheld count
**Definition:** The number of extracted sentences the content check dropped from a note, shown with the reason.

## Boundaries

**This project owns:** the on-laptop app: sign-in, polling, building and showing notes, the local store, the content check, local diagnostics.
**This project consumes:** Microsoft calendar entries (CON-001), the chosen folder (CON-002), call tool records (CON-003), IT-pushed managed settings.
**This project does not concern itself with:** a mailbox, general document search, a morning digest, an adoption dashboard, anything hosted.

## Conventions

- Vault items are cited by ID and commit, never copied.
