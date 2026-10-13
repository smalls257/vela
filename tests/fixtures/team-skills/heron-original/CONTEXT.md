# Project Context

> Domain glossary and shared mental model for the Desktop agent design. Terms come from the initiative vault (INI-001 @ 051d15a); the vault's glossary owns them.

## Glossary

### Consent grant
**Definition:** What Consent and identity says a person has agreed to at the moment of a read: calendar entries, Teams transcripts, both or neither. The agent holds it for one run only.
**Not to be confused with:** The stored record of who agreed to what, which Consent and identity keeps.
**Examples:** A person who agreed to calendar entries only has a grant with no transcripts.

### Held note
**Definition:** A digest or prep note that has arrived and waits on the laptop to be shown. It is deleted when the person withdraws.
**Not to be confused with:** The calendar entries and transcript text it was written from, which the agent never writes to disk.

### Outbox
**Definition:** The agent's durable list of consent events (switch-on, per-source choices, withdrawal) not yet confirmed by Consent and identity. It is retried until confirmed and survives a withdrawal purge.

### Calendar-only note
**Definition:** A digest or prep note written from a meeting's calendar entry alone (vault glossary).

## Boundaries

**This project owns:** the Desktop agent on each laptop: reading calendar entries, asking for notes, showing them, recording consent choices.
**This project consumes:** Microsoft 365 (CON-001), the Summariser (CON-002), Consent and identity (CON-003, CON-004).
**This project does not concern itself with:** writing the digest or prep note (Summariser), keeping the consent record (Consent and identity), pushing the package to laptops (the endpoint team's Intune and Jamf).

## Conventions

- Vault items are cited by ID and commit, never copied.
