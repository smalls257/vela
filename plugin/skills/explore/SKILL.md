---
name: explore
description: Build the vault explorer and open it in the browser. One offline page for a live conversation, showing the map of apps and contracts, each flow played across them, who holds each open answer, why things were decided, and where each app stands. Use when the user wants to look at the whole initiative, present a flow to a senior, or see what needs them. For one fact, use /planner:find or /planner:ask.
argument-hint: "[console|graphite|daylight|vaporwave] [--today YYYY-MM-DD] [--design APP-x=<path to its tech design>]"
disable-model-invocation: true
allowed-tools: Read Bash(python3 .claude/skills/planner/bin/planner explore *) Bash(python3 .claude/skills/planner/bin/planner check *) Bash(uname *) Bash(open *) Bash(xdg-open *)
---

# Explore the vault

The explorer is one HTML page drawn from the vault: the map, each flow played step by step, who holds each open question, why things were decided, and each app's stage. It is for looking and presenting. It never changes a vault page.

The planner is `python3 .claude/skills/planner/bin/planner`. Run from the vault root.

## Asked for

$ARGUMENTS

## Steps

1. Build the page. Run `python3 .claude/skills/planner/bin/planner explore`, and add what the user asked for:
   - a theme word becomes `--theme <word>`. `console` is dark and the default; `graphite` is grey, for projectors that wash out blue; `daylight` is light, for screen-sharing and print; `vaporwave` is a 1990s sunset.
   - a date becomes `--today YYYY-MM-DD`. The lights count from the system date, so a vault dated ahead of it, such as the example, wants this.
   - a team's tech design becomes `--design APP-x=<path>`, once per app. Inside this app then goes down to that team's components. Without one it stops at the app page's containers.
   - `--assets <assets.config.json>` only if the user hands you one. It inlines generated art and sound. Without it the page uses its own drawing, which is complete.
   - `-o <file>` only if the user names a place for the page.
2. Read what it printed, line by line, before you open anything. Step 4 says what each kind of line means. If the command exits 2, show its message in full, say no page was built, and stop. Never open an old page as if it were new.
3. Open the page. The command's last line names the file. By default it is `.planner/explorer.html` in the vault. Run `uname`, then `open <file>` on Darwin or `xdg-open <file>` on Linux. On Windows, or when the command fails, give the user the full path and say so. Never say the page is open unless the command succeeded.
4. Tell the user in a few lines what you did: where the page is, how many apps, flows and unknowns it shows (the last line says), and anything from step 2 that needs them.

## What the build reports

- `first build: wrote the pinned positions ... to .planner/explorer-pins.json`. The first build fixes where every app sits and keeps it in the vault, so the map never rearranges between builds. Say that this file was written, once. Later builds add a cell only for a new app, and say so (`pinned new positions in ...`). Deleting the file lays the map out afresh.
- `a link was left out, <page>: <reason> (planner check reports it as E105)`. A link in a page's `links:` or an item's `**Links:**` could not be read, so the page has no chip for it. List them to the user and offer `planner check`. Do not fix the page unless they ask.
- `<APP> design <path>: <status>, N components, M things it could not read`. The lines under it give the line number and what was skipped. Tell the user which designs are incomplete; the page shows the same count on the design's chip. Never describe a design as complete when its status says otherwise.
- `<key> asks for icon: <name>, which is not in the built-in set`. The page drew that app by keyword instead. Harmless. Mention it only if the user cares about the picture.
- `no Open the file links, the vault and the page sit apart under the home folder`. The page was written somewhere its relative links to the vault cannot reach without naming the home folder, so it leaves them out rather than writing an absolute path. Build again without `-o` to get them.
- `this vault's .gitignore does not list .planner/`. The page and the pinned layout would be committed. Offer to add the line `.planner/` to `.gitignore`, and do it only if the user says yes.
- `assets from ..., N fell back to builtin`. Each fallback is listed with its reason. Say which slots fell back.

## Where the files go

- The page goes to `.planner/explorer.html` in the vault. `.planner/` is the vault's folder for the tool's own files and the template gitignores it, so the page, 3 MB and rebuilt on demand, is never committed by accident. It sits inside the vault so the page's "Open the file" links, which are relative, still reach the Markdown. A page in the system temp folder would lose those links and be cleaned away.
- The pinned layout goes to `.planner/explorer-pins.json` in the vault. It is a small JSON map of ID to column and row, listed in `CONVENTIONS.md`.
- Nothing is written into the plugin folder. A plugin update replaces that folder, and the layout would go with it.

## Offline

The page makes no network request. It draws with its own SVG, canvas and Web Audio, uses system fonts, and carries the vault's text as escaped data, so a page that says `<script>` shows those characters and runs nothing. Sound is off until the user presses `S`. A link chip to a tracker or wiki opens in a new tab only when clicked, and the page never fetches it. The file can be emailed or opened from a USB stick.

## Explorer or viewer

`planner view` builds a different page, for a different reader. The viewer is the vault's documents as a reading copy: every page rendered, diagrams drawn, stamped with the commit and the check counts, locked down by a content-security policy. Send that to someone who will read. The explorer is the vault's structure as a working surface for a conversation: lights, map, played flows. It shows no commit stamp and it is rebuilt on the spot. If the user wants a document to email, offer `planner view --out <file>`; for a call, run this.

## Rules

- Say only what the build printed and what the page shows. Do not read the HTML back to the user or describe views you have not seen.
- Never edit a vault page, `CONVENTIONS.md` or the pins file. The explorer reads the vault.
- Never delete `.planner/explorer-pins.json` unless the user asks to lay the map out afresh.
