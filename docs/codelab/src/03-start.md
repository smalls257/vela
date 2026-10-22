---
title: Start a plan
minutes: 3
summary: Make a folder, open Claude Code in it, and let vela start the plan
---
A plan is a git repository of Markdown pages, one folder per initiative. You make an empty folder and ask for a first session. If there's no plan yet, Claude offers to start one, and that runs `vela new`.

::: sequence
skills: dump, references/START
You > Claude: /vela:dump in an empty folder
Claude > You: Offers a plan, asks its name
You > Claude: "Heron Desk"
Claude > vela: `vela new --title`
vela > plan: Writes 48 files and commits them
:::

::: type
In a terminal:

```
mkdir heron-desk
cd heron-desk
claude
```

Then in Claude Code: `/vela:dump`. If you'd rather start the plan by hand: `vela new --title "Heron Desk"`.
:::

::: asks
Claude asks two things:

> There's no plan in this folder yet. Want me to start one? What short name should the initiative go by, a few words as you'd say it to a colleague?

If vela can't find your GitHub handle, Claude asks for it once.
:::

::: see
`vela new`, run for real with the handle `@solution-lead`:

```
vela new: started INI-001 'Heron Desk' for @solution-lead in .../heron-desk: 48 files, committed 2dae834: Start the plan.
vela check: 0 errors, 0 warnings.
Left for a person: a GitHub repository, the required check, Obsidian (see README.md).
```

Then `vela next`, which suggests what to do:

```
vela next: for the whole plan: no app page exists yet, so start by getting everything known written down (/vela:dump, a brainstorm), or by reading the existing sources (/vela:discover).
```
:::

::: checkpoint
The folder holds `01-goals.md`, `11-unknowns-and-risks.md`, a `README.md` and about 45 more files, and `vela check` reports 0 errors. `git log` shows one commit, "Start the plan".
:::

::: fold Why this step
Everything vela knows lives in plain files in git, so you can read, review and undo it. Starting with `vela new` instead of copying a template means the first commit holds only the plan's own files. More on why plans are files with checks, not documents: [the problem page][m-problem].
:::

::: fold Stuck?
- `vela new` refuses a folder that already holds a plan, a folder inside another plan, and a folder with plans below it. Pick an empty one.
- To put a plan inside a repository that already holds others: `vela new --vault projects/heron --title "Heron rollout"`.
- If it asks for your GitHub handle, give it once: `vela new --title "Heron Desk" --handle @your-handle`.
- The README the new plan carries lists what's left for a person: a GitHub repository, the required check, and Obsidian if you use it. None of it blocks the next step.
:::
