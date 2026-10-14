---
name: explore
description: Build the vault explorer and open it in the browser, so one page shows the map, the flows, who holds each open answer and where each app stands. Use to look at the whole initiative or present a flow; for one fact use /planner:find or /planner:ask.
argument-hint: "[console|graphite|daylight|vaporwave] [--today YYYY-MM-DD] [--design APP-x=<path to its tech design>]"
disable-model-invocation: true
allowed-tools: Read Bash(python3 *scripts/planner *) Bash(uname *) Bash(open *) Bash(xdg-open *)
---

# Explore the vault

The explorer is one HTML page drawn from the vault: the map, each flow played step by step, who holds each open question, why things were decided, and each app's stage. It is for looking and presenting. It never changes a vault page.

The planner is `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner` (`START.md`, "Where the planner runs from", covers a host that leaves the variable unexpanded). Run from the vault root.

## Asked for

$ARGUMENTS

## Steps

1. Build the page and serve it. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner explore --serve` in the background, since it keeps running until the user stops it, and add what the user asked for:
   - `--serve` is the default here: it serves the page on this machine only (127.0.0.1) and opens the browser, and the search box can then ask Claude. Leave it off, for a static build the user can email or open from disk, only when the user says so, or asks for a file.
   - If the user names `--model`, `--port`, `--assets <assets.config.json>` or `-o <file>`, pass it. The default model is haiku (the page has its own Think harder toggle), the port is the vault's usual one, and without assets the page uses its own drawing, which is complete.
   - a theme word becomes `--theme <word>`. `console` is dark and the default; `graphite` is gray, for projectors that wash out blue; `daylight` is light, for screen-sharing and print; `vaporwave` is a 1990s sunset.
   - a date becomes `--today YYYY-MM-DD`. The lights count from the system date, so a vault dated ahead of it, such as the example, wants this.
   - a team's tech design becomes `--design APP-x=<path>`, once per app. Inside this app then goes down to that team's components. Without one it stops at the app page's containers, unless the build finds the design itself: with no `--design`, it looks for each app's doc from `design:` on the app page, `designs:` in `.planner.yaml`, then the vault's own `docs/tech-design/*.md` (matched to an app by `vault.app`, then by the prereq naming its page, then by file name), then a `file://` GitHub or Code link to a local clone whose `docs/tech-design/*.md` names the app in its `vault.app` (CONVENTIONS.md, Team design docs). It reads local files only. If the user says where a team's repo is cloned, offer to write `design:` on the app page; do not ask them to retype `--design` every build.
2. Read what it printed, line by line, before you open anything. Step 4 says what each kind of line means. If the command exits 2, show its message in full, say no page was built, and stop. Never open an old page as if it were new.
3. Open the page. With `--serve` the command opens the browser itself and prints `serving http://127.0.0.1:<port>/`. Read the background output for that line and give the user the address. If it printed `no browser could be opened`, or `claude is not on PATH`, say so: the page works without claude, but asking will report that it cannot. A static build (no `--serve`) names the file on its last line; run `uname`, then `open <file>` on Darwin or `xdg-open <file>` on Linux. On Windows, or when the command fails, give the user the full path and say so. Never say the page is open unless the command succeeded.
4. Tell the user in a few lines what you did: the address or the file, how many apps, flows and unknowns it shows (the build line says), that Enter in the search box asks Claude about the vault and an answer shows its model and cost, and that Ctrl-C in the terminal, or stopping the background task, ends the server. Add anything from step 2 that needs them.

## What the build reports

- `first build: wrote the pinned positions ... to .planner/explorer-pins.json`. The first build fixes where every app sits and keeps it in the vault, so the map never rearranges between builds. Say that this file was written, once. Later builds add a cell only for a new app, and say so (`pinned new positions in ...`). Deleting the file lays the map out afresh.
- `a link was left out, <page>: <reason> (planner check reports it as E105)`. A link in a page's `links:` or an item's `**Links:**` could not be read, so the page has no chip for it. List them to the user and offer `planner check`. Do not fix the page unless they ask.
- `<APP> design found at <path>, from <how>`. The build found that app's design itself: `design:` on its page, `designs:` in `.planner.yaml`, or its local GitHub or Code link, by `vault.app`. Say which, so the user knows where it came from.
- `no design doc found for <APPs>`. Those apps show as "not loaded" under Inside this app. The lines under it say what was looked at, such as a clone that holds no doc naming the app. Offer to set `design:` on an app page when the user knows where the doc is. Never describe an app as having a design when it is on this list.
- `warning: <APP>: <path> is not a file` (or `is not a folder`, or a doc whose frontmatter cannot be read, or `designs:` that is not a map). A path the vault gives for a design leads nowhere. Show the line, name the page or config that holds it, and offer to fix the path; the build went on and the app shows as not loaded.
- `<APP> design <path>: <status>, N components, M things it could not read`. The lines under it give the line number and what was skipped. Tell the user which designs are incomplete; the page shows the same count on the design's chip. Never describe a design as complete when its status says otherwise.
- `<key> asks for icon: <name>, which is not in the built-in set`. The page drew that app by keyword instead. Harmless. Mention it only if the user cares about the picture.
- `no Open the file links, the vault and the page sit apart under the home folder`. The page was written somewhere its relative links to the vault cannot reach without naming the home folder, so it leaves them out rather than writing an absolute path. Build again without `-o` to get them.
- `this vault's .gitignore lists dashboard.html`. Colleagues who pull the repo would not get the page. Offer to remove that line from `.gitignore`, and do it only if the user says yes.
- `assets from ..., N fell back to builtin`. Each fallback is listed with its reason. Say which slots fell back.

## If the user asks how it works

Read `${CLAUDE_PLUGIN_ROOT}/skills/explore/ABOUT.md`. It covers where designs and plans live, where the files go, what the Ask Claude box does, what works offline, and how the explorer differs from `planner view`. Say only what it holds, and do not describe an answer you have not seen.

## Rules

- Say only what the build printed and what the page shows. Do not read the HTML back to the user or describe views you have not seen.
- Never edit a vault page, `CONVENTIONS.md` or the pins file. The explorer reads the vault.
- Never delete `.planner/explorer-pins.json` unless the user asks to lay the map out afresh.
