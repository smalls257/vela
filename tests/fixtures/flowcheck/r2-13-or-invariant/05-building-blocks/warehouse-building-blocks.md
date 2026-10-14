---
id: APP-warehouse
type: app-building-blocks
title: Warehouse
---

# Warehouse

## Contracts this app provides

### CON-330 Ship the order

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| shipped | | 200 | the parcel is on its way | | order: new→shipped |
