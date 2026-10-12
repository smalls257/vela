---
id: RUN-account-link-service
type: app-runtime
title: Account link service runtime
state: assumption
owner: "@sim-lead"
authored: authored
sources: [SRC-06, 2026-10-07-login-owner-and-offer]
---

# Account link service runtime

## On failure

If the service is down or slow, sign-in still works, because Northway ID is separate. Nobody can make or change a link. SeaBook and FERRYMASTER show the ferry account on its own and keep taking bookings.

- **Options considered:** Login with a link service (picked); Login only, no new app: rejected, it holds the link in two places, leaves the rail-side link with no owner and puts the link step on SeaBook, which Ferry Ops says is frozen; Ferry sign-in adapter: rejected, its adapter has no named owner and the link step still has no app
