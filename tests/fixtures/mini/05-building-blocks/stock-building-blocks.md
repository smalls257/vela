---
id: APP-stock
type: app-building-blocks
title: Stock
initiative: INI-900
state: fact
change: unchanged
owner: "@stock-team"
authored: authored
sources: [SRC-01]
---

# Stock

Stock knows how many of each product are left. It is unchanged, so this page is slim.

## Contracts this app provides

### CON-002 Stock level

- **Crosses the boundary:** a product ID in; the count left out.
- **Consumers:** [[shop-building-blocks|Shop]]
- **Change policy:** the existing read API, no change.
- **Change:** unchanged
- **State:** fact
- **Source:** SRC-01

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| count | | ok | the count left | | |
