---
title: What's next
minutes: 2
summary: Where to go from here
---
You've followed one sentence to tickets. A real plan keeps going: new questions arrive, answers change pages, and teams challenge boundaries.

- **Ask the plan:** `/vela:ask` answers from the pages alone and says "Not recorded" when they're silent. `/vela:find` points to where something is.
- **Fill the gap this demo left:** `/vela:allocate` gives each requirement an owning app. `vela next` suggests it first on the Heron plan.
- **Keep it honest:** `vela check` before each pull request, `vela health` for stale pages, `vela upgrade` after a `W717` warning.
- **Read why it works this way:** [How vela thinks][m-home] and the [user guide][guide].

::: see
`vela next` on the Heron copy still says:

```
vela next: for the whole plan: decide which app owns List my open follow-ups (CAP-022.FR1), with /vela:allocate. It is not decided yet and no app has taken it, so no team owns it yet.
```
:::

::: checkpoint
You can name the next session you'd run on your own plan, and why `vela next` suggests it.
:::

::: fold Stuck?
- `W717` means the plan's rule book differs from the installed vela's. Run `vela upgrade`, check `git diff CONVENTIONS.md` and commit.
- A challenge to a boundary: a team lead runs `/vela:challenge`. It opens a pull request that stays red on purpose until you answer.
:::
