# Tech Design Doc Format

Output path: `docs/tech-design/<slug>.md`

## Template

~~~markdown
---
slug: <slug>
status: in-progress
deferred: []
last_session: <ISO timestamp>
prereqs:
  - path: docs/requirements/<slug>.md
    expected_status: complete
vault:                     # vault mode only, else omitted
  app: <APP-id>
  initiative: <INI-nnn>
  commit: <short sha the design read>
  origin: <vault remote URL>
---

# Tech Design — <Title>

## Architecture overview
<one paragraph + a mermaid component diagram>

## Context boundaries
**Inside the app:** <what we build>
**Outside the app:** <what we integrate with or rely on>

## Components
### <ComponentName>
- Responsibility: <one sentence>
- Owns: <data / decisions>
- Depends on: <other components>
- Exposes: <surface>
- Container: <the container it runs in; in vault mode, a Container name from the app page's main containers table>

## Responsibility matrix
| Component | Owns | Reads from | Writes to |
|-----------|------|------------|-----------|

## Data model
<entities and relationships as a mermaid erDiagram, then:>
- **Persistence:** <store per entity>

## API contracts
### <Component> public surface
<methods, payload shapes, errors>

## Integration points
| System | Direction | Protocol | Auth |
|--------|-----------|----------|------|

## Key flows
~~~mermaid
sequenceDiagram
...
~~~

## Supporting diagrams
~~~mermaid
...
~~~

## Tech stack
| Layer | Choice | Rationale |
|-------|--------|-----------|

## NFRs
| Concern | Target | How enforced |
|---------|--------|--------------|

## Constraints register
| ID | Constraint | Source | Impact |
|----|-----------|--------|--------|

## Risks & mitigations
| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|

## ADRs
- [ADR-0001](../adr/0001-<slug>-<topic>.md) — <title>

## Operations
- **Deploy:** <how>
- **Monitor:** <metrics, logs, traces>
- **Scale:** <scaling axis, limits>

## Trace
| Target | Component |
|--------|-----------|
| <FR-XXX; in vault mode CAP-nnn.FRn@APP-id, CON-nnn or EPC-nnn.ACn> | <ComponentName, or Operations> |

## Open questions
### OQ-001: <question>
**What we know:** <...>
**What would unblock:** <...>
**Affects:** <components, trace targets>
**Challenges:** <vault ID; vault mode only, when the vault is wrong or silent>
~~~

## Rules

- Every Component has a Responsibility-matrix row.
- Every FR-XXX from requirements is traced to at least one Component, by a row of the Trace table. In vault
  mode the targets are those `TECH-DESIGN-FROM-VAULT.md` lists, one row per target; a criterion met by running the
  service rather than by a component names `Operations`. IDs mentioned elsewhere in the doc are not traces.
- In vault mode every Component names its Container, so a reader can zoom from the vault's containers to the
  components inside them.
- Team ADRs are linked, never cited bare: `ADR-NNNN` is also the vault's own pattern. A vault ADR is cited with its
  initiative and commit, as `INI-002 ADR-0002 @ <sha>`.
- `Open questions` is omitted when there are none. Each open OQ is named by a `gaps[]` entry's `oq:` field.
- ADRs are lazy — only when hard-to-reverse + surprising + real trade-off.
- Glossary from requirements doc gets promoted to root `CONTEXT.md`
  (lazy creation, see `CONTEXT-FORMAT.md`).
