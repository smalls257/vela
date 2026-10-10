# requirements-grill in an initiative vault

In a vault, `/planner:requirements` is the way to write a capability's requirements: it runs after the strategy is decided, and `/planner:allocate` then divides them among the apps. This file is for a team that still runs its own `requirements-grill` against a vault; it writes in the same format, so either way the requirements land on the capability page.

The user's `requirements-grill` skill reads this file when it runs in a repository with `.planner.yaml` at its root. It keeps its own interview: one question at a time, a recommended answer with each, edge-case scenarios, and keeping to the "what" rather than the "how". This file changes only where the answers go and what certainty they carry.

## Scope

Vault mode always runs on one capability, `CAP-NNN`. If the user gave none, ask: "Which capability? For example CAP-021." Stop until there is one, and stop if `capabilities/CAP-NNN-*.md` does not exist.

It is called from two places:

- while shaping the capability delta, when a capability's "after" is too vague to draw a flow or name an epic;
- from the `epics` skill, when an acceptance criterion needs behaviour the vault does not hold. Then the scope is the capability that epic delivers.

Out of scope: behaviour inside one app (that is the app team's own requirements work), flows (grill the capability instead), and non-functional requirements (they are concerns).

## Session

If a session record is already open in this conversation, add `requirements` to its `modes` and capture into it; otherwise run START. The session record is the vault's; there is no `docs/requirements/<slug>.md` and no `slug`, `status` or `deferred` frontmatter.

Capture every answer in the session record. The user's own words take their name as origin. A recommended answer the user accepts as it stands has origin `claude, from <name>`.

## Where each section goes

| requirements-grill section | Vault mode writes | Where |
|---|---|---|
| Problem, Users | Nothing new. Link the goal the capability serves. If no goal fits, a `[worry]` capture: "CAP-NNN serves no goal". | session record |
| Scope In and Out | `- **In:** ...` and `- **Out:** ...` lines | the capability page, under `## Scope` |
| Functional requirements | `### CAP-NNN.FRn <short name>` (at most six words), one paragraph of what it does, `- **State:** assumption`, `- **Source:** [[<session id>#^cNN]]` | the capability page, under `## Functional requirements` |
| Acceptance criteria | Plain bullets under each FR, stated at a boundary the vault knows: a flow, a contract or an actor in the glossary | under the FR |
| Constraints | A link to an existing `CST-n`. A new constraint becomes a capture for `02-constraints.md`. | session record |
| Open questions | An unknown with `**Question:**`, `**Owner:**`, `**State:** open`, `**Ask by:**` and a `**Blocks:**` link to the FR, as shown below | `11-unknowns-and-risks.md` |
| Deferred items | A capture with the reason. Close parks it. | session record |
| Glossary | A new term with `assumption` beside it | `12-glossary.md` |
| A tech or NFR detour | The skill's redirect stays. Also write a `[worry]` capture naming the concern page, or a note for the app's senior. | session record |

An unknown that blocks an FR links the FR's heading:

```
- **Blocks:** [[CAP-021-amend-or-cancel#CAP-021.FR2 Partial cancel|CAP-021.FR2]]
```

FR numbers are never reused. A removed FR stays, struck through, with the reason.

## Certainty

- Vault mode is a Shape, not a Grill. It writes at most `assumption`.
- It never writes `fact`. Requirements state intent.
- If the user says "decide FR1", say once: "Requirements are recorded as assumptions, so a Grill can test them before anyone builds to them." Offer `/planner:grill CAP-NNN.FRn`. If they still want it decided here, that is an override of `grill`: write it `decided`, with `- **Decision:** [[<session id>]]` and `- **Override:** grill by @<handle> on <today>: <their reason>` under its heading, as `START.md` says. The check then reports W317 instead of E317 for it.
- The check enforces this: a session whose `modes` include only `requirements` cannot be the `**Decision:**` behind a `decided` item.
- If the capability page is already `decided`, an open unknown that blocks one of its FRs makes the check fail with E316, because the capability was decided before the question was answered. Say so before writing the unknown, and let the user choose: keep the unknown and take the capability back to `assumption` in a Grill, or record the question as not blocking (`**Blocks:** nothing`) with the reason in `**Notes:**`.

## Completion

When every section has content and every branch is closed or is an unknown, run the skill's `NEG-AUDIT.md`. Then do not set any `status: complete`. Tell the user: "Run `/planner:close` to mark the captures, check the vault and open the PR."
