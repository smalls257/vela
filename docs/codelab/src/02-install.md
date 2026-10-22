---
title: Install vela
minutes: 5
summary: Add the plugin to Claude Code and check the machine
---
Two commands in Claude Code add vela. Then you ask Claude to check that the machine has what vela needs.

::: type
In Claude Code:

```
/plugin marketplace add smalls257/vela
/plugin install vela@vela
```

Then ask Claude: "Run vela doctor."
:::

::: asks
Nothing yet. Claude doesn't ask you anything in this step.
:::

::: see
`vela doctor` prints one line per item, run in an empty folder on a Mac:

```
ok    Python 3.14.4 (/opt/homebrew/opt/python@3.14/bin/python3.14)
ok    PyYAML 6.0.3, bundled with the plugin (nothing to install)
ok    git version 2.50.1 (Apple Git-155)
ok    node v26.11.1: vela check parses the diagrams
ok    claude command found: the explorer's Ask Claude box works
info  vela plugin 0.5.0
vela doctor: ready.
```
:::

::: checkpoint
The last line reads `vela doctor: ready.` Your versions will differ. A line starting `optional` is fine: it says what that item would add.
:::

::: fold Why this step
Vela checks things (`vela check`) and writes pages. Both need a known setup on your machine, and the doctor is the one place that says what's missing. The idea behind the rest, that a claim should be checkable by something other than Claude's say-so, is on [the trust page][m-trust].
:::

::: fold Stuck?
- A line that says `optional` isn't a failure. It names what the item adds and the one command that gets it.
- `vela: <folder> has no .vela.yaml, so it is not a vault. Run vela from the vault root or pass --vault.` means you ran a plan command outside a plan. That's expected here. The next step makes the plan.
- The repo is public, so installing needs no access grant. Git should be signed in to GitHub, which `gh auth login` does.
:::
