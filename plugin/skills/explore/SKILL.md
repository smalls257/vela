---
name: explore
description: "Build the dashboard and open it in the browser: the map of apps, the journeys, who holds each open answer. Offer it when someone wants the whole picture or a journey shown; for one fact use /vela:find. Start it only on a yes."
argument-hint: "[console|graphite|daylight|vaporwave] [--today YYYY-MM-DD] [--design APP-x=<path to its tech design>]"
allowed-tools: Read Bash(sh *scripts/run-vela *) Bash(uname *) Bash(open *) Bash(xdg-open *)
---

# Explore the vault

Before you say anything to the lead, read `voice/VOICE.md` if the vault has one, then `${CLAUDE_PLUGIN_ROOT}/references/CONVERSATION-VOICE.md`, for how to talk.

The dashboard is one HTML page drawn from the plan: the map, each journey played step by step, who holds each open question, why things were decided, and each app's stage. It is for looking and presenting. It never changes a vault page.

Vela is `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela` (`START.md`, "Where vela runs from", covers a host that leaves the variable unexpanded). Run from the vault root.

## Asked for

$ARGUMENTS

## Steps

1. Build the page: `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela explore --for-lead`, with what the user asked for:
   - a theme word becomes `--theme <word>`. `console` is dark and the default; `graphite` is gray, for projectors that wash out blue; `daylight` is light, for screen-sharing and print; `vaporwave` is a 1990s sunset.
   - a date becomes `--today YYYY-MM-DD`. The status colors count from today's date, so a plan dated ahead of it, such as the example, wants this.
   - a team's tech design becomes `--design APP-x=<path>`, once per app. Without one the build looks for each app's design itself (`vela conventions "Team design docs"`) and says what it found. If the user says where a team's repo is cloned, offer to write `design:` on the app page rather than ask them to retype `--design` every build.
   - `--assets <assets.config.json>` or `-o <file>`, when the user names them.
2. Tell the user what it built, in your words, answer first: the page is ready, with how many apps, journeys and open questions it shows. Then anything that needs them, about four things at most, each with what you'd do. Leave out housekeeping, such as the pins file or the built-in pictures. Never describe an app as having a design when the build says it has none, or a design as complete when it says otherwise. If the command exits 2, say in a plain sentence what stopped it, that no page was built, and stop. Never open an old page as if it were new.
3. Open the page. Serving is the default: run `sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela explore --serve` in the background, with the same flags but without `--for-lead`, since it keeps running until the user stops it. It serves on this machine only (127.0.0.1), opens the browser, and turns on the search box's Ask Claude. Pass `--model` or `--port` when the user names one; the default model is haiku. vela opens the browser itself with the link, so don't open it a second time. Read its output for the `serving http://127.0.0.1:<port>/?k=…` line and give the user the whole link, key included, never shortened. If it says no browser could be opened, or claude isn't installed, say so plainly: the page works without claude, but asking will say it can't. Skip serving, for a file the user can email or open from disk, only when they ask for one: then run `uname`, and `open <file>` on Darwin or `xdg-open <file>` on Linux. On Windows, or when that fails, give the full path. Never say the page is open unless the command succeeded.
4. Close with how to use it, in a line or two: Enter in the search box asks Claude about the plan, and each answer shows its model and cost; Ctrl-C in the terminal, or stopping the background task, ends the server.

When a command can't do what the user wants, say so and stop.

## If the user asks how it works

Read `${CLAUDE_PLUGIN_ROOT}/skills/explore/ABOUT.md`. It covers where designs and plans live, where the files go, what the Ask Claude box does, what works offline, and how the dashboard differs from `vela view`. Say only what it holds.

## Rules

- Say only what the build printed and what the page shows. Don't read the HTML back to the user or describe views you haven't seen.
- Never edit a vault page, `CONVENTIONS.md` or the pins file. The dashboard reads the plan.
- Never delete `.vela/explorer-pins.json` unless the user asks to lay the map out afresh.
