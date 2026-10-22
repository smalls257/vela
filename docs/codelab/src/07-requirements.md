---
title: Requirements and boundary
minutes: 30
summary: What the business needs with no app named, then where the apps divide
---
Two sessions, in order. Requirements says what the business needs, once, naming no app, screen or technology. Boundary then turns a direction into apps: two or three ways to cut it, then one page per app.

::: sequence
skills: requirements, boundary
Claude > You: One requirement and a suggested answer
You > Claude: A yes, or what's missing
Claude > vela: `vela add fr` for each yes
vela > plan: Requirement page written
Claude > You: Boundary: two or three cuts
You > Claude: Your cut
:::

::: type
```
/vela:requirements
/vela:boundary
```
:::

::: asks
Requirements takes one requirement at a time, with its recommended answer, and pushes on the edge cases:

> What should happen when a call has one person on it who hasn't opted in? I'd say no summary at all, for anyone. Does that hold?

Boundary asks you to pick between its cuts, and says what each rules out.
:::

::: see
A requirement from the Heron plan. It names no app:

```
### CAP-023.FR1 Summarize only fully opted-in calls

- **State:** assumption
- Heron summarizes a call only when every participant on it has opted in to Heron.
  - Trace: UNK-093
- A call with even one participant who hasn't opted in gets no summary.
```

The boundary cut it to four apps, and the decision keeps the cuts it rejected:

```
| Three apps, with the admin view inside the Heron service | The works council's view and the reading service would ship and fail together. |
| Two apps, with consent inside the Heron service | The consent record is lost with the service, and the identity team's registration review has no seam. |
```
:::

::: checkpoint
There's a capability page with numbered requirements, each with criteria and a trace to what it depends on. There's a page for each app saying what it does and doesn't do. `vela status` lists the apps at the stage `boundaries`.
:::

::: fold Why this step
Naming apps too early freezes a guess. Requirements come first so the cut can be argued against something. See [Requirements][m-req] and [Boundary][m-boundary]. Allocation, the step that gives each requirement an owning app, comes next in a full run: see What's next. The Heron demo plan stopped before it, and `vela check` says so for each requirement.
:::

::: fold Stuck?
- `W505`: a requirement is not decided yet and no app has taken it. Real output: `Fix: Run /vela:allocate CAP-022, or add a row for CAP-022.FR1 to the app page that delivers it.` The Heron plan shows nine of these.
- `E350` means a flow step names a sender or receiver its contract doesn't join.
- `E103` means a page is missing a required frontmatter field.
:::
