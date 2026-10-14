# About the explorer

Read by explore when the user asks how the page works: where the files go, what the box does, whether it works offline, how it differs from the viewer, or where designs and plans live.

## Where designs and plans live

Both live in the vault: `docs/tech-design/<slug>.md` (with `docs/adr/` and `CONTEXT.md`) from `/vela:design` (or the user's own tech-design-grill) and `docs/plan/<slug>-breakdown.md` from `/vela:breakdown`, when the team runs them from the vault root. The build finds them with no flag. The design and the plan write their own `docs/` files in the vault and never edit a vela page, so say so if a senior asks. `vela check` does not read `docs/`.

## Where the files go

- The page goes to `dashboard.html` at the vault root. The template does not ignore it: it is committed so a colleague can pull the repo or open the OneDrive folder and just open it, with nothing to build. The page says at the top when it was built and from which commit. It sits at the root so the page's "Open the file" links, which are relative, still reach the Markdown. A page in the system temp folder would lose those links and be cleaned away.
- The pinned layout goes to `.vela/explorer-pins.json` in the vault. It is a small JSON map of ID to column and row, listed in `CONVENTIONS.md`. The template's `.gitignore` tracks it, so commit it and the team shares one map layout; `vela publish` carries it into read copies.
- Nothing is written into the plugin folder. A plugin update replaces that folder, and the layout would go with it.

## Ask Claude

Served, the search box can also put a question to Claude. Claude runs headless in the vault with Read, Grep and Glob only, so it reads pages and cannot change one. Every claim in its answer cites a vault ID or page path, which the page turns into a link, and an ID the vault does not hold is flagged. Each answer shows its model and cost. The helper listens on 127.0.0.1 only and turns away requests from any other origin. If `claude` is missing, times out or fails, the page shows the reason. Say all of this plainly if the user asks what the box does; do not describe an answer you have not seen.

## Offline

A built file makes no network request. It draws with its own SVG, canvas and Web Audio, uses system fonts, and carries the vault's text as escaped data, so a page that says `<script>` shows those characters and runs nothing. Sound is off until the user presses `S`. A link chip to a tracker or wiki opens in a new tab only when clicked, and the page never fetches it. The file can be emailed or opened from a USB stick. Opened that way, the box stays search-only and offers the question as a prompt to copy into Claude Code. Served (`--serve`), the page asks its own helper on this machine and nothing else.

## Explorer or viewer

`vela view` builds a different page, for a different reader. The viewer is the vault's documents as a reading copy: every page rendered, diagrams drawn, stamped with the commit and the check counts, locked down by a content-security policy. Send that to someone who will read. The explorer is the vault's structure as a working surface for a conversation: lights, map, played flows. It shows no commit stamp and it is rebuilt on the spot. If the user wants a document to email, offer `vela view --out <file>`; for a call, run this.
