# Frontmatter format

The design doc starts with this YAML block, and a build plan made from the design uses the same one. Downstream skills and the explorer read it, so the field names stay as written.

```yaml
---
slug: <kebab-case>             # required
status: in-progress | complete | complete-with-gaps   # required
deferred:                      # may be []
  - id: D-001
    section: "<section: part>"
    reason: <why it is put off, who owns it, what settles it>
    blocks: <trace targets it holds up, or "none">
gaps:                          # when status is complete-with-gaps, else left out
  - id: G-001
    what: <what is wrong, in plain words, in one line>
    acknowledged_by: <the handle of the person who accepted it>
    why: <their reason>
    revisit: <when, or the condition that reopens it>
    oq: <OQ-XXX, when the gap is an open question; else left out>
last_session: <ISO 8601 timestamp>   # stamped on every write
prereqs:
  - path: 05-building-blocks/<app>-building-blocks.md   # standalone: docs/requirements/<slug>.md
    expected_status: handed_off                          # standalone: complete
vault:                         # in a vault; left out standalone
  app: <APP-id>
  initiative: <INI-nnn>
  commit: <short sha the design read, from origin/main>
  origin: <vault remote URL, with no user:token@ part>
---
```

## Status

- `complete`: the self-audit (`NEG-AUDIT.md`) is clean, and every review finding (`REVIEW-CHECKPOINT.md`) was answered, deferred or ruled not applicable.
- `complete-with-gaps`: a finding is left as an open question, or the senior accepted a problem instead of fixing it. Each one is a `gaps[]` entry. A downstream skill reads `gaps[]` and carries it forward, so `complete` is never written over an accepted gap.
- `in-progress`: anything else.

## Writing a gap

`what` says the thing that is wrong, the way a developer would say it to a colleague. The audit's own names stay in the audit checklist, which goes in the pull request body.

| Instead of | Write |
|---|---|
| `Distributed Monolith: the seven components deploy and fail as one process` | `All seven components run as one process, so one bug in the core takes the agent down (ADR-0001)` |
| `acknowledged_by: team lead` | `acknowledged_by: "@agent-lead"` |

## IDs

- `D-`, `G-` and `OQ-` numbers are stable. Once given, an ID is never reused or renumbered: if D-002 is removed, the next is still D-004 after D-003. The gap in the numbers is the audit trail.
- A build plan's own gaps use `PG-`, so they never collide with the design's `G-`.

## Deferral or open question

| Type | Where | Means | Use it when |
|---|---|---|---|
| `D-XXX` | frontmatter `deferred[]` | the work or the decision is known and deliberately put off | you know what has to happen, and it waits |
| `OQ-XXX` | the doc's `## Open questions` | nobody here knows the answer yet | you don't know, and someone has to say |

An open question has this shape, with "what we know, what would unblock, affects":

```markdown
### OQ-001: Who approves expense claims above £500?
**What we know:** Claims below £500 auto-approve. Above is unclear.
**What would unblock:** The finance team confirms, or the approval policy says.
**Affects:** ApprovalFlow, Notifier; CAP-003.FR2@APP-claims
**Challenges:** CAP-003.FR2
```

Each open question ends up answered (the entry is removed and the design says the answer), deferred (it becomes a `D-XXX`), or accepted as a gap. A question that challenges the vault is never a `D-XXX`: that type means the answer is known.
