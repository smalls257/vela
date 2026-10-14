---
id: APP-shop
type: app-building-blocks
title: Shop
initiative: INI-900
state: decided
change: new
stage: contracts
owner: "@mini/shop-team"
authored: mixed
---

# Shop

- **Decision:** [[2026-01-10-shop-api]]

Shop sells products to the till.

```mermaid
flowchart LR
  till["Till"] -->|"CON-001"| shop["Shop"]
  shop -->|"CON-002"| stock["Stock"]
```

## Contracts this app provides

### CON-001 Sale API

- **Crosses the boundary:** a basket in; a receipt out.
- **Consumers:** [[till-building-blocks|Till]]
- **Change policy:** versioned.
- **Change:** new
- **Tested by:** consumer tests in the till pipeline.
- **State:** decided
- **Decision:** [[2026-01-10-shop-api]]

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| sold | | 200 | the receipt | | |
| basket_refused | | 422 | the basket is empty or holds an unknown product | | |

## Contracts this app consumes

<!-- generated:contracts-consumed sha=0dca45ce: do not edit, run planner render -->
| Contract | Provider | Change policy | State |
|---|---|---|---|
| [[stock-building-blocks#CON-002 Stock level\|CON-002 Stock level]] | [[stock-building-blocks\|Stock]] | the existing read API, no change. | fact |
<!-- /generated:contracts-consumed -->
