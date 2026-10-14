---
id: APP-shop
type: app-building-blocks
title: Shop
---

# Shop

## Contracts this app provides

### CON-310 Ship the order

- **Can time out:** no
- **Retries:** none

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| shipped | | 200 | the parcel is on its way | | parcel: waiting→shipped |
