# Without a vault

When the folder holds no `.vela.yaml`, there is no vault to answer to, and the design starts from a requirements doc instead. Everything in SKILL.md holds except where this file says otherwise.

## The prereq

- Ask for the slug if it wasn't given (kebab-case, such as `payment-gateway`).
- The input is `docs/requirements/<slug>.md` with `status: complete` in its frontmatter. If it is missing or not complete, say so and stop: the design would be settling what the product must do, which the requirements session does (the user's requirements-grill skill, or `/vela:requirements` in a vault).
- Record it in the design's `prereqs[]` with `expected_status: complete`, and leave out the `vault:` block.
- Scan quietly before the first question: `CONTEXT.md`, `docs/adr/*.md`, the last twenty commits and any `AGENTS.md`. Mention what you find only when it conflicts with something the team lead says.

## What changes

- **Trace targets** are the requirements doc's `FR-XXX` IDs, one Trace-table row each. Every one needs an owning component.
- **The walking skeleton** comes from the requirements doc's first release, or its first user journey when it names no release. If it names neither, propose one in a sentence and ask.
- **The glossary.** Offer to seed `CONTEXT.md` from the requirements doc's glossary on the first run; it is then the whole glossary.
- **A gap in the requirements** is an open question with `**Affects:**` naming the `FR-XXX` and no `**Challenges:**` line, because there is no vault to challenge. Tell the team lead the requirements doc's owner settles it, and carry on with the branches it doesn't touch, as SKILL.md does in a vault.
- **Where the work lands.** The same as in a vault: a `design/<slug>` branch, a commit per section through `vela team commit --about "<the section>"`, a pull request at the end. If the team has no review rule, say you are committing to a branch and let the team lead decide.
