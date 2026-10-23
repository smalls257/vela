---
name: onboard
description: "Set up a path through the plan for your role, shown in the dashboard. Offer it when someone says they are new or need to get up to speed; start it only on a yes. For one fact use /vela:find."
argument-hint: "[your role, if you know it]"
allowed-tools: Read Bash(sh *scripts/run-vela *) Bash(uname *) Bash(open *) Bash(xdg-open *)
---

# Get up to speed

Before you say anything, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`, for how to talk.

The person joined a plan already under way. Your job is to get them ready for a useful first conversation with the people who will hand them work. You never assign work or a first task, and you never quiz them. Everything you say comes from what `vela onboard` prints, so nothing here is yours to add or guess.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded, as Cowork does). Run it from the vault root. Nothing here uses git, so it works in a reader copy too.

## Asked for

$ARGUMENTS

## Steps

1. Their role: lead, exec, product, qa, eng or mgr. Run `vela onboard show --json` first. Its `roleSource` says where the role came from: the lead's own record of them, their earlier choice, or their path; when it is `none`, ask once, with your guess from what they said ("Which is closest: exec sponsor, product owner, engineer, QA lead, delivery manager or solution lead?"), and keep it with `vela whoami --role <role>`. If they say a role while one is recorded, use what they say for this path. Never ask twice.
2. Run `vela onboard check`. If it lists mistakes on the lead's page, say so in one sentence (it is the lead's page to fix) and go on; the path still works. Then run `vela onboard show --role <role> --for-lead` and say it in your words, answer first: the stage the plan is at, how many parts, about how many minutes, then the first four parts by name. Offer the rest ("want the other five?"; `--more` prints them). If it carries a note from the lead, say it as the lead's.
3. Ask what they most need, one question with your recommendation: "What would help most before you talk to people: what exists today, how it fits together, who decides what, something else?" Then how they like to learn, one question: diagrams, explanations or both. Recommend one.
4. Choose from the plan's modules and nothing else. `vela onboard modules --json` lists every name, what it is for and which roles it suits. Keep the first five parts (Goal, Approach, Where things stand, Where you fit, Who to talk to) first unless they ask otherwise, then add or reorder up to four that fit what they said. Pick the depth: `gist` if they are short on time, `normal` otherwise, `everything` if they ask for the detail. Diagrams are `yes` for diagrams or both, `no` for explanations.
5. Read the path back as names, about five at a time, and wait for a yes. If what they need is not a module (for example "the vendors"), say so, name the nearest one, and offer `/vela:ask` for the rest. Never invent a module or a fact to fill the gap.
6. Write it: `vela onboard path set --role <role> --modules "<name>, <name>" --depth <depth> --diagrams <yes|no> --json`. It saves their choices under their handle and rebuilds their page. If it exits 3, ask for their GitHub handle once and run `vela whoami --set <handle>`, then run it again. If it stops because the lead hid a module they asked for, say the lead hid it, that it is theirs to ask for, and run it again with `--bring-back "<name>"`; it is recorded.
7. Open their page, read `file` from the output. Run `uname`, then `open <file>` on Darwin or `xdg-open <file>` on Linux. When that is not possible (Cowork, Windows, a failure), say the page is ready and give the file's path. Never say it is open unless the command succeeded.
8. Close in two lines: they can change the path any time by telling you what to add or drop (`vela onboard path clear` goes back to the standard path), and the dashboard's "Get up to speed" door shows the standard path to anyone without a path of their own.

## Rules

- Say only what the commands printed. Never add a fact, an owner, a date or a reason, and never say who to talk to unless a module says it.
- Names, never IDs or module codes. Say "the Contracts part", not an identifier.
- The only thing you write is `vela onboard path set` or `clear`. Never edit a plan page, the lead's onboarding page or the dashboard.
- A part the plan is silent on is on their path with "Not recorded yet" and who to ask. Say that plainly; it is the plan's gap, not yours.
