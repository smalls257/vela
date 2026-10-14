# Tech design doc format

Path: `docs/tech-design/<slug>.md`, in the vault, so the explorer's Inside this app finds it with no flag. Its frontmatter is in `FRONTMATTER-FORMAT.md`.

Contents: [The page](#the-page) · [Template](#template) · [Rules the explorer reads by](#rules-the-explorer-reads-by) · [A good summary](#a-good-summary)

## The page

A reader opens the doc to learn what the app does and what shapes it, in under a minute. So the summary comes first, then the walking skeleton, then the full detail in the sections below, which keep everything a builder needs.

- **Summary:** what the app does for people in two or three sentences; the three to five decisions that shape it, one line each; the walking skeleton in a sentence; what is still open, with who settles it. About 200 words in all.
- **Every section** keeps to house-voice's limits: one topic a paragraph, under about 120 words, tables for facts, prose for reasons. Detail that runs longer goes into a `###` under the section, or into a table.
- **A section with nothing to say** keeps its heading and holds `None.` with the reason in a few words ("None. One process, so the component diagram above is the whole picture."). The explorer names a missing heading as something it could not read.
- The doc has every template section below, in this order. `## Open questions` is left out when there are none.

## Template

~~~markdown
---
<frontmatter, as FRONTMATTER-FORMAT.md>
---

# Tech Design — <Title>

## Summary
<What the app does for people, and for whom, in two or three sentences.>

**Decisions that shape it:**
- <decision, one line, naming the section or ADR that holds it>

**Walking skeleton:** <one sentence: the release-one path, and what is stubbed>

**Still open:** <the few questions that matter most, who settles each and by when, in words; then "n more under Open questions">

## Walking skeleton
<The release-one flow this app serves, in a sentence, and the smallest path through the components that carries it.>
- **Flow:** <the vault flow or release-one requirement it serves, by name, with its ID>
- **Path:** <Component → Component → Component>
- **Stubbed:** <each other app's side, at the contract it meets, until that team's piece lands>
- **Carries:** <the trace targets it covers first>
- **Override:** <only when the senior set the skeleton aside: their words, their handle, the date>

## Architecture overview
<one paragraph, then a mermaid component diagram>

### Decisions
- <each decision that shapes the app, one bullet each>

## Context boundaries
**Inside the app:** <what we build>
**Outside the app:** <what we integrate with or rely on>

## Components
### <ComponentName>
- Responsibility: <one sentence>
- Owns: <data / decisions>
- Depends on: <components and integration points, by the names they have here>
- Exposes: <surface>
- Container: <the container it runs in; in a vault, a Container name from the app page's containers table>

## Responsibility matrix
| Component | Owns | Reads from | Writes to |
|-----------|------|------------|-----------|

## Data model
<entities and relationships as a mermaid erDiagram, then:>
- **Persistence:** <store per entity>

## API contracts
<one line on the rule every call shares, such as how it fails>

### <Component> public surface
- <operation: payload shape, errors>
- On failure: <what the component does when its call fails or is slow>

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
<one line: the vault commit read, and what `vela handoff verify` said>

| Target | Component |
|--------|-----------|
| <CAP-nnn.FRn@APP-id, CON-nnn or EPC-nnn.ACn; standalone FR-XXX> | <ComponentName, or Operations> |

## Open questions
### OQ-001: <question>
**What we know:** <...>
**What would unblock:** <...>
**Affects:** <components, trace targets>
**Challenges:** <vault ID; only when the vault is wrong or silent>
~~~

## Rules the explorer reads by

The explorer reads this doc by its headings, bullets and tables, and lists anything it can't read on the app's page. These rules keep that list empty.

- The title is `# Tech Design — <Title>`, with the dash.
- Each `###` under `## Components` is a component and has all five bullets. A note about several components, such as how a rule is enforced inside one process, goes under `## Architecture overview` as its own `###`.
- Every component has a Responsibility-matrix row, and every matrix row names a component.
- `Depends on` names other components, or systems exactly as the Integration points table names them in its System column, such as "Consent and identity (CON-003)". An operating-system facility the app relies on, such as a key store, is an integration point too.
- Each `###` under `## API contracts` is `<Component> public surface` for a component of this design. A rule every call shares is the line above the first `###`; what one call does on failure is an `On failure:` bullet under its component.
- Every trace target has a row of the Trace table, one row per target. In a vault the targets are those `TECH-DESIGN-FROM-VAULT.md` lists; a criterion met by running the service rather than by a component names `Operations`. IDs mentioned elsewhere in the doc are not traces.
- In a vault every component names its Container, so a reader can zoom from the vault's containers to the components inside them.
- Team ADRs are linked, never cited bare: `ADR-NNNN` is also the vault's own pattern. A vault ADR is cited with its initiative and commit, as `INI-002 ADR-0002 @ <sha>`.
- An open question's `**Challenges:**` line names a vault ID, and is left out when the question challenges nothing in the vault. Who settles a question that isn't the vault's goes in `**What would unblock:**`.
- Each open question is named by a `gaps[]` entry's `oq:` field.

## A good summary

The Heron Desktop agent's, re-shaped from its design run:

> The Desktop agent runs on each person's laptop in the Client Delivery London pilot. With the person's consent it reads their own calendar entries, asks the Summarizer for a 7:30 digest and a prep note ten minutes before each meeting, and shows them. It keeps nothing it doesn't need: a withdrawal deletes everything the agent holds for that person.
>
> **Decisions that shape it:**
> - One signed Tauri process for Mac and Windows, with a Rust core ([ADR-0001](../adr/0001-desktop-agent-tauri-single-process.md)).
> - The consent check is the only door to Microsoft and the Summarizer, and every failed or slow call reads and shows nothing.
> - Calendar entries only in the first release: no mail.
>
> **Still open:** the Summarizer's owner hasn't said what it keeps, logs and trains on, and the endpoint lead hasn't said whether a bad build can be recalled; both are needed before the January packaging slot. Eight more are under Open questions.
