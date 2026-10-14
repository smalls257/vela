# proj-planner

Vela is a Claude Code toolkit for planning at the initiative level. It takes you from a one-line ask to fully specified epics, written in Markdown that every reader can follow. It was called "planner" before 2026-10-14, and the design records in `docs/` dated before then use that name.

## Install

Three steps, in Claude Code:

1. Add the marketplace: `/plugin marketplace add smalls257/vela`
2. Install the plugin: `/plugin install vela@vela`
3. Ask Claude to run `vela doctor`. It prints one line per item and ends with `vela doctor: ready.` when the machine has what vela needs. Anything optional that's missing says what it adds and the one command that gets it.

The repo is private, so your colleague needs access to it on GitHub first, and git on their machine signed in to that account (`gh auth login` does it). There is nothing to pip install. Vela runs on Python 3.9 or later, which comes with a Mac's developer tools, and it brings its own copy of PyYAML.

## Start here tomorrow

1. **Make a vault.** Copy `template/` into a new GitHub repo, then follow its `README.md` setup checklist, steps 1 to 12. Step 2 copies this repo's `plugin/` folder into the vault. Run `vela doctor` from the vault to check the machine and the vault together.
2. **Start every session with `bin/claude-vela`**, from inside the vault. The skills only load through that launcher.
3. **Run your first session:**
   - `/vela:dump` gets everything out of your head. Ideas, worries, unknowns and wild ones all count. Claude doesn't push back. After the pre-mortem it runs a review checkpoint and shows you the questions nobody has asked yet. Take the ones you want; the rest wait.
   - `/vela:close` promotes what you keep and writes a question ledger row for each question you took. It drafts the prose in the house voice and has a fresh reader review it. Then it renders and checks the vault, and opens the PR.
4. **Next sessions, in roughly this order.** Every session starts by running `vela next`, which suggests one app and one mode. It is a suggestion, not a decision.
   - `/vela:discover` reads your sources and asks you to confirm what exists today.
   - `/vela:import` turns an initiative already under way (documents, code, wikis, tickets) into a vault, with an import map you correct before anything is written.
   - `/vela:shape` offers 2–3 options to react to.
   - `/vela:requirements` writes each capability's functional requirements, naming no app, once the strategy is decided.
   - `/vela:boundary` turns a decided direction into apps: 2–3 ways to cut it, then one sheet per app (what it does and does not do, containers, contracts, failure, concerns), written at `assumption` line by line.
   - `/vela:allocate` divides each requirement among the apps and contracts that carry it, so every requirement has an owner before epics.
   - `/vela:releases` asks when anyone outside the team first gets the result, then which requirements (or which of their checks) each dated release delivers, and writes `04b-releases.md`, which the dashboard's Releases view reads.
   - Only `/vela:grill` can mark an item `decided`, and only after your explicit yes.
   - `/vela:ask` answers questions from the vault. It is read-only, and anything the vault doesn't hold comes back as `Not recorded:`.
   - `/vela:find` finds where something is, in seconds, mid-conversation: "how does coach talk to brightwater" gives the best place to look and the flows that cross it.
   - `/vela:explore` builds the dashboard, one offline page of the whole initiative (map, flows played, who holds each answer), and opens it in your browser.
   - Discover, Shape and Grill each run a review checkpoint too. Between sessions, `python3 .claude/skills/vela/scripts/vela questions --digest` shows what is still owed. See "What v3 adds" below.
5. **Before each PR,** run `python3 .claude/skills/vela/scripts/vela check`. CI runs it too. If you make it a required check, a broken vault can't merge.
6. **For the CIO,** run `python3 .claude/skills/vela/scripts/vela view --out ~/Desktop/<name>.html` and email the file. It works offline and can't run page script or make network calls. The viewer is the reading copy: every page rendered, stamped with the commit and the check counts. For a live conversation use the dashboard instead, `/vela:explore`: the map, the flows played step by step, and what needs the lead. The two are kept apart on purpose, one a document you send and the other a surface you present from.

The kill rule you set: if it isn't faster than plain Markdown after five sessions, cut back to the conventions, `check` and the viewer.

## The vela CLI

Run each one as `python3 .claude/skills/vela/scripts/vela <command>` from the vault root. Only `render`, `view`, `explore`, `handoff` and `export` write files.

| Command | What it tells you |
|---|---|
| `vela explore [<vault>]` | Builds the dashboard, one offline page: the map, each flow played, who holds each open answer, why things were decided, where each app stands. Writes `dashboard.html` at the vault root (committed, so colleagues open it from git or OneDrive without building) and the fixed layout `.vela/explorer-pins.json`. The page says at the top when it was built; an unchanged vault rebuilds to the same bytes. `vela publish` rebuilds it into the read copy. `-o`, `--today`, `--theme`, `--design APP-x=<path>`, `--assets`. `/vela:explore` runs it and opens the page |
| `vela status` | Every app's stage, certainty mix and oldest open unknown |
| `vela style <page>...` | Where a page still reads as a log: history above `## History`, IDs or bare source IDs in prose, no opening prose |
| `vela ladder` | Each app's typed stage, the stage its pages already reach, and what the next stage needs |
| `vela upgrade` | Replace the vault's `CONVENTIONS.md` with the installed plugin's copy, after `vela check` warns W717 |
| `vela next` | The one app and mode to work on next, with the reason. `probe` means: ask the unknown's owner, or research it |
| `vela health` | Stale pages and sources, overdue unknowns, and days since the last closed session, as Markdown |
| `vela query get <ID>` | Where an ID lives and its state. `refs`, `find` and `status` too. Add `--json`. `/vela:ask` uses it |
| `vela query search <words>` | Plain-word search, ranked, with the flows that cross each place. `/vela:find` uses it |
| `vela questions` | The questions the catalog says this vault owes, one copy per subject, and where each stands in the question ledger. `--open`, `--area`, `--subject` and `--json`; `--digest` ranks the pending ones, `--stats` counts how often each entry ends not-applicable |
| `vela findings merge <folder>` | Merges the focused reviewers' findings: keeps the union, removes duplicates, drops any finding whose quote is not on the page it cites, and says per area whether it found something, found nothing, or did not run |
| `vela handoff <APP-id>` | Writes `handoffs/<APP-id>.md`, the app's handoff list: everything its team's lead accepts |
| `vela handoff verify <APP-id>` | What changed in that slice since handoff. Exits 1 when something accepted changed |
| `vela voicecheck <before> <after>` | Fails when a rewrite lost or moved an ID, number, date, link, code span, table cell or negation |
| `vela doctor` | What this machine has for vela, one line per item: Python, the bundled PyYAML, git, and the optional node, `claude` and voice-scoring packages, each missing one with what it adds and the command that gets it. Also whether the folder is a vault, whether the vault's pre-commit hook finds the installed vela (if not, the one command that wires it: `git config vela.path <launcher>`), and the plugin version. Exit 0 when nothing required is missing |
| `vela voicescore <page>` | Optional: whether each prose paragraph sits inside or outside your own voice's range. See "Optional: voicescore" below |
| `vela export jira-csv --out epics.csv` | One row per epic for Jira's CSV import. Export only: nothing is read back and no page carries a Jira field. A page's generic `links:` may point at its ticket, as at any other URL |

`vela render` fills every generated block, including the generated diagrams: the context map, system context, each app's context and the capability map. Never edit inside a block. Close runs `vela render` for you.

## What v3 adds: the questions the plan owes

v2 checks what you wrote. v3 also keeps track of what nobody has asked yet.

- **The question catalog.** `plugin/catalog/questions.yaml` holds 29 entries in five focus areas: FIN finance and liabilities, DAT data and lawful basis, PTN partners and contracts, REG regulation and liability, OPS operations and people. The entries are generic, worded for any initiative, and each cites the regulation, practice or simulated miss that earned it a place. An entry is owed once per subject it fits: the initiative, each app, contract and capability, and each outside party (`PTY-nn`) and stored value (`SV-nn`) on `03-context-and-scope.md`. Type a new subject and its questions become owed, with nobody having to remember them. Each owed copy has an ID such as `Q-FIN-03@SV-01`.
- **`vela questions`** lists every owed copy and where it stands. `--open` keeps only what is pending: no row, an `open`, `asked` or invalid row. `--digest` groups them by entry, so one answer can serve several copies, and ranks them, high severity that blocks something first. `--stats` counts how often each entry ends `not-applicable` in your vault, so you can see which to prune. None of these options claims the questions are complete, because the catalog finds only what is written into it.
- **The question ledger** is a table under `## Question ledger` on `11-unknowns-and-risks.md`. Each row says where one copy stands: `open`, `asked`, `answered`, `assumed`, `unknown` or `not-applicable`. Every state but `open` carries evidence, and `vela check` verifies it. `answered` needs the item that holds the answer and a source, either an `SRC-nn` or a quote that must really be on the page it names. `assumed` needs the belief, whether it is load-bearing, and a signpost that would show it failing. `unknown` needs an open `UNK-nnn` with an owner. `not-applicable` needs a reason. A generated list above the table shows what is still pending. A row looks like this:

  ```
  | Q-FIN-03@SV-01 | answered | item: [[03-context-and-scope#SV-01 Loyalty points\|SV-01]]; source: SRC-04; answer: Finance carries the points | @you | 2026-11-19 |
  ```

- **Review checkpoints.** `/vela:dump` runs one after the pre-mortem, `/vela:discover` after the read-back, `/vela:shape` before the options, `/vela:boundary` once its app pages are written, and `/vela:grill` on the agenda. Each dispatches five `area-reviewer` subagents, one per focus area, each in a fresh context with only the written pages and its area's owed questions. That adds real time and tokens to every checkpoint, because five subagents read the vault each time. You see one ranked digest, not the reviewers, and you choose what to take now.
- **`vela findings merge`** combines the five replies. It keeps the union, removes duplicates, drops any finding whose quote is not on the page it cites, and never votes. An area that failed says "did not run" with the reason, never "checked, none". The session writes the result into the record's `## Reviews` section: the coverage line, the dropped findings, and a table of the kept ones, `F1.1` and on. Words in `## Reviews` never count as a quote, so a reviewer cannot cite itself.
- **Close writes the ledger and proposes catalog entries.** It writes a row for every question you took and every finding the merge kept, and types each party or stored value you said exists. Then it asks "Did any other gap turn up late, or by luck?" Each gap you name becomes a draft catalog entry, and the ones you approve go under `## Catalog proposals` in the session record. Close never edits the catalog itself.
- **The gates.** `vela check --gate shape` warns W806 for each row still `assumed`. `--gate grill --item <ID>` warns W807 for each pending question that blocks the item. You may decide anyway, and the session's capture records that. `--gate epics` fails with E805 for each high-severity question still pending. To call the epics complete anyway, override the gate: write `- **Override:** E805 by @you on <date>: <why>` under `## Question ledger`, and each E805 prints as W805 instead. A plain `vela check` never fails because a question is unanswered: you set the pace.
- **voicescore** is unchanged: the optional style hint at close, described under "Optional: voicescore" below.

## Your voice

- **`/vela:voice-seed`** stores 2 or 3 passages of your own writing per voice type, word for word, so drafts sound like you instead of the public seed. Committed examples go in `voice/examples/` and are pushed in a PR, where anyone with access to the repo can read them. Local examples go in `voice/local/`, which is gitignored and stays on your machine. If your employer owns the text, or you're not sure, keep it local.
- **At close,** a fresh subagent runs a voice review of the drafts. Close rewrites each flagged paragraph once, and `vela voicecheck` throws out any rewrite that changed a fact.
- **Harvest.** Only the vault's owner harvests, and only their own edits: close looks through your merged session PRs for paragraphs you rewrote after the draft, and asks before saving each one as an example.

## Optional: voicescore

`vela voicescore <page>` tells you, for each prose paragraph, whether it sits inside or outside your range, for example `outside your range (p96)`. Your range is how far each of your own `owner` and `owner-edit` examples sits from the rest. It uses StyleDistance, a small open style model, so it is a second opinion of a different kind from the voice reviewer. `vela voicescore --rank a.md b.md` orders drafts of the same paragraph. Close adds one line to the PR's Voice review when it can run. It is a hint, not a gate: it never blocks a PR and never rewrites anything.

- **Install:** `python3 -m pip install sentence-transformers`. It pulls in PyTorch, about 1–2 GB. Nothing else in vela needs it.
- **Setup, once:** `vela voicescore setup` is a one-off download of the pinned model, about 0.5 GB, into `~/.cache/vela-voicescore/`. It is the only vela command that touches the network, and it says so before it starts. If your network blocks Hugging Face, ask IT to fetch it.
- **After that it runs offline.** Scoring forces Hugging Face's offline mode, so it never fetches anything, and your text never leaves this machine. Vectors are cached in `.git/vela-voicescore/`, which is never committed.
- **Needs 5 of your examples.** With fewer it still answers but says the score is unreliable. It never falls back to the public seed; `--against seed` compares with the seed and says so.

## After handoff

- **When the first app nears handoff,** grill its handoff, then `/vela:close` writes `vela handoff <APP-id>` in the PR that sets `handed_off`. Epics come after: `/vela:epics` writes them against the accepted boundary, and `vela check --gate epics --app <APP-id>` says when that app's epics are complete.
- **A team lead who disputes a boundary or contract** runs `/vela:challenge`. It writes an open question the lead owns and a `**Dissent:**` line, and opens a PR whose check stays red (E316) on purpose.
- **To answer it,** run `/vela:grill` and name the challenge PR or the challenged ID. START opens an answer session on the challenge's branch. Resolve the unknown or set the item back, then `/vela:close` pushes to that branch and comments on the challenge PR. It doesn't open a second PR. A reopened epic is decided again as `reopened → decided`.

## Later

- **Weekly "Vault health" issue.** `.github/workflows/vela-weekly.yml` posts `vela health` every Monday to one issue titled "Vault health". It needs Issues enabled on the repo. It has not been tested live yet, so watch the first Monday's run.
- **Not yet run against a real GitHub repo:** the weekly issue, close's owner-only harvest (it reads merged PRs with `gh`), answering a challenge (it comments on the challenge PR with `gh pr comment`), and close's merge of a moved `main`. Each is tested on local git repos only, so watch the first real run of each.
- **Long-lived PRs.** If `main` moves while a long-lived PR is open, merge `origin/main` into the session branch, then run `vela render`. A conflict inside a generated block goes away when you re-render. Close does this before it renders.
- **Vault mode for your own grills:** `integrations/requirements-grill/INSTALL.md` and `integrations/tech-design-grill/INSTALL.md`. Each one backs up first and dry-runs before applying. Nothing has been applied to `~/.claude` yet.
- **Jira export details:** Owner team drops the leading `@` of the handle, so `@org/team` becomes `org/team`. The link points at the repository and commit from `git`, or pass `--repo-url` and `--commit`.
- **Evals:** these are paid runs, and you run them by hand. See `tests/evals/README.md`. Start with the $1 smoke run it describes.

## What's where

| Path | What it is |
|---|---|
| `template/` | The vault you copy, including `CONVENTIONS.md`, the one written format |
| `plugin/` | The `vela` CLI (`check`, `check-slice`, `check-diagrams`, `terms`, `render`, `view`, `explore`, `status`, `next`, `tickets`, `capture`, `health`, `query`, `questions`, `findings`, `handoff`, `next-id`, `export`, `voicecheck`, `voicescore`, `ladder`, `style`, `upgrade`, `conventions`, `session`, `close`, `guard`, `apply`, `epics`, `releases`, `boundary`, `prose`, `hook`, `role`, `publish`, `freshness`, `open`, `propose`, `proposals`, `where`, `doctor`), the question catalog in `catalog/questions.yaml`, the format the skills follow in `vault/CONVENTIONS.md`, the session skills (dump, discover, import, shape, requirements, boundary, allocate, releases, grill, epics, explore, close, ask, challenge, open, propose, proposals, where, voice-seed, house-voice), the `voice-reviewer` and `area-reviewer` agents, and START, MODES and REVIEW under `references/` |
| `examples/unified-booking/` | A complete made-up vault: a ferry operator's Unified Booking initiative |
| `integrations/` | Vault mode for `requirements-grill` and `tech-design-grill`, as patches |
| `docs/` | Spec, design-session logs, research, plans |
| `tests/` | `python3 -m pytest -q` |
