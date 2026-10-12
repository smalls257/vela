---
id: RUN-seabook
type: app-runtime
title: SeaBook runtime
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-02, 2026-10-07-login-owner-and-offer]
---

# SeaBook runtime

## On failure

If Northway ID is down, ferry customers cannot sign in. Not recorded: whether SeaBook lets a customer book without signing in. Ask Ferry Ops.

If the Account link service is down, SeaBook shows the ferry account alone and keeps taking bookings.

SeaBook's own availability target of 99.9% from May to September stays (SRC-02).

- **Options considered:** Login with a link service (picked); Login only, no new app: rejected, it holds the link in two places, leaves the rail-side link with no owner and puts the link step on SeaBook, which Ferry Ops says is frozen; Ferry sign-in adapter: rejected, its adapter has no named owner and the link step still has no app
