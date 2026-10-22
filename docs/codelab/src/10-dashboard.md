---
title: Open the dashboard
minutes: 3
summary: The whole plan on one page you can present from
---
The dashboard is one offline HTML page drawn from the plan: the map of apps, each journey played step by step, who holds each open question, and where each app stands. It never changes a page.

::: type
```
/vela:explore
```
or by hand: `vela explore`
:::

::: asks
Nothing needed from you. Claude builds the page and opens it in your browser.
:::

::: see
The last line of `vela explore` on the Heron plan:

```
vela explore: wrote dashboard.html for INI-001 Heron: 4 apps, 6 contracts, 49 unknowns, 3 epics, 1 flows, as of 2026-10-22.
```

![The Heron dashboard map: four apps and the contracts between them](../method/dashboard-map.png)
:::

::: checkpoint
You have `dashboard.html` at the plan's root, and clicking an app in the map opens its detail. The top says when the page was built.
:::

::: fold Why this step
Under pressure, you need to find a topic and the apps it touches in about two clicks. The dashboard is for a live call; `vela view` builds the reading copy you email. See [the dashboard][m-dash].
:::

::: fold Stuck?
- The page says at the top when it was built. If it looks old, build it again; an unchanged plan rebuilds to the same bytes.
- The "Ask Claude" box needs the `claude` command, which `vela doctor` checks.
- `vela view --out ~/Desktop/<name>.html` builds the reading copy. It works offline and can't run page script.
:::
