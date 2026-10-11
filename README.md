# proj-planner

A Claude Code toolkit for planning at the initiative level. It covers everything from a one-line ask to fully specified epics, written in Markdown that every reader can follow.

## Start here tomorrow

1. **Make a vault.** Copy `template/` into a new GitHub repo, then follow its `README.md` setup checklist, steps 1 to 12. Step 2 copies this repo's `plugin/` folder into the vault. You need Python 3.11+ and PyYAML: `python3 -m pip install pyyaml`. Your Mac's `python3` already has PyYAML 6.0.3. If pip refuses on another machine with "externally-managed-environment", install PyYAML into a venv (`python3 -m venv ~/.venvs/planner && ~/.venvs/planner/bin/pip install pyyaml`) and run planner with `~/.venvs/planner/bin/python3`.
2. **Start every session with `bin/claude-planner`**, from inside the vault. The skills only load through that launcher.
3. **Run your first session:**
   - `/planner:dump` gets everything out of your head. Ideas, worries, unknowns and wild ones all count. Claude doesn't push back. After the pre-mortem it runs a review checkpoint and shows you the questions nobody has asked yet. Take the ones you want; the rest wait.
   - `/planner:close` promotes what you keep, writes a question ledger row for each question you took, drafts the prose in the house voice, has a fresh reader review it, renders and checks the vault, and opens the PR.
4. **Next sessions, in roughly this order.** Every session starts by running `planner next`, which suggests one app and one mode. It is a suggestion, not a decision.
   - `/planner:discover` reads your sources and asks you to confirm what exists today.
   - `/planner:shape` offers 2–3 options to react to.
   - `/planner:requirements` writes each capability's functional requirements, naming no app, once the strategy is decided.
   - `/planner:boundary` turns a decided direction into apps: 2–3 ways to cut it, then one sheet per app (what it does and does not do, containers, contracts, failure, concerns), written at `assumption` line by line.
   - `/planner:allocate` divides each requirement among the apps and contracts that carry it, so every requirement has an owner before epics.
   - `/planner:releases` asks when anyone outside the team first gets the result, then which requirements (or which of their checks) each dated release delivers, and writes `04b-releases.md` the explorer's Releases lens reads.
   - `/planner:grill` is the only thing that can mark an item `decided`, and only after your explicit yes.
   - `/planner:ask` answers questions from the vault. It is read-only, and anything the vault doesn't hold comes back as `Not recorded:`.
   - `/planner:find` finds where something is, in seconds, mid-conversation: "how does coach talk to brightwater" gives the best place to look and the flows that cross it.
   - `/planner:explore` builds the explorer, one offline page of the whole initiative (map, flows played, who holds each answer), and opens it in your browser.
   - Discover, Shape and Grill each run a review checkpoint too. Between sessions, `python3 .claude/skills/planner/bin/planner questions --digest` shows what is still owed. See "What v3 adds" below.
5. **Before each PR,** run `python3 .claude/skills/planner/bin/planner check`. CI runs it too. If you make it a required check, a broken vault can't merge.
6. **For the CIO,** run `python3 .claude/skills/planner/bin/planner view --out ~/Desktop/<name>.html` and email the file. It works offline and can't run page script or make network calls. The viewer is the reading copy: every page rendered, stamped with the commit and the check counts. For a live conversation use the explorer instead, `/planner:explore`: the map, the flows played step by step, and what needs the lead. The two are kept apart on purpose, one a document you send and the other a surface you present from.

The kill rule you set: if it isn't faster than plain Markdown after five sessions, cut back to the conventions, `check` and the viewer.

## The planner CLI

Run each one as `python3 .claude/skills/planner/bin/planner <command>` from the vault root. Only `render`, `view`, `explore`, `handoff` and `export` write files.

| Command | What it tells you |
|---|---|
| `planner explore [<vault>]` | Builds the vault explorer, one offline page: the map, each flow played, who holds each open answer, why things were decided, where each app stands. Writes `.planner/explorer.html` and the fixed layout `.planner/explorer-pins.json` in the vault. `-o`, `--today`, `--theme`, `--design APP-x=<path>`, `--assets`. `/planner:explore` runs it and opens the page |
| `planner status` | Every app's stage, certainty mix and oldest open unknown |
| `planner style <page>...` | Where a page still reads as a log: history above `## History`, IDs or bare source IDs in prose, no opening prose |
| `planner ladder` | Each app's typed stage, the stage its pages already reach, and what the next stage needs |
| `planner upgrade` | Replace the vault's `CONVENTIONS.md` with the installed plugin's copy, after `planner check` warns W717 |
| `planner next` | The one app and mode to work on next, with the reason. `probe` means: ask the unknown's owner, or research it |
| `planner health` | Stale pages and sources, overdue unknowns, and days since the last closed session, as Markdown |
| `planner query get <ID>` | Where an ID lives and its state. `refs`, `find` and `status` too. Add `--json`. `/planner:ask` uses it |
| `planner query search <words>` | Plain-word search, ranked, with the flows that cross each place. `/planner:find` uses it |
| `planner questions` | The questions the catalogue says this vault owes, one copy per subject, and where each stands in the question ledger. `--open`, `--area`, `--subject` and `--json`; `--digest` ranks the pending ones, `--stats` counts how often each entry ends not-applicable |
| `planner findings merge <folder>` | Merges the focused reviewers' findings: keeps the union, removes duplicates, drops any finding whose quote is not on the page it cites, and says per area whether it found something, found nothing, or did not run |
| `planner handoff <APP-id>` | Writes `handoffs/<APP-id>.md`, the slice a senior accepts |
| `planner handoff verify <APP-id>` | What changed in that slice since handoff. Exits 1 when something accepted changed |
| `planner voicecheck <before> <after>` | Fails when a rewrite lost or moved an ID, number, date, link, code span, table cell or negation |
| `planner voicescore <page>` | Optional: whether each prose paragraph sits inside or outside your own voice's range. See "Optional: voicescore" below |
| `planner export jira-csv --out epics.csv` | One row per epic for Jira's CSV import. Export only: nothing is read back and no page carries a Jira field. A page's generic `links:` may point at its ticket, as at any other URL |

`planner render` fills every generated block, including the generated diagrams: the context map, system context, each app's context and the capability map. Never edit inside a block. Close runs `planner render` for you.

## What v3 adds: the questions the plan owes

v2 checks what you wrote. v3 also keeps track of what nobody has asked yet.

- **The question catalogue.** `plugin/catalog/questions.yaml` holds 29 entries in five focus areas: FIN finance and liabilities, DAT data and lawful basis, PTN partners and contracts, REG regulation and liability, OPS operations and people. The entries are generic, worded for any initiative, and each cites the regulation, practice or simulated miss that earned it a place. An entry is owed once per subject it fits: the initiative, each app, contract and capability, and each outside party (`PTY-nn`) and stored value (`SV-nn`) on `03-context-and-scope.md`. Type a new subject and its questions become owed, with nobody having to remember them. Each owed copy has an ID such as `Q-FIN-03@SV-01`.
- **`planner questions`** lists every owed copy and where it stands. `--open` keeps only what is pending: no row, an `open`, `asked` or invalid row. `--digest` groups them by entry, so one answer can serve several copies, and ranks them, high severity that blocks something first. `--stats` counts how often each entry ends `not-applicable` in your vault, so you can see which to prune. None of them ever says the questions are complete: the catalogue finds only what is written into it.
- **The question ledger** is a table under `## Question ledger` on `11-unknowns-and-risks.md`. Each row says where one copy stands: `open`, `asked`, `answered`, `assumed`, `unknown` or `not-applicable`. Every state but `open` carries evidence, and `planner check` verifies it. `answered` needs the item that holds the answer and a source, either an `SRC-nn` or a quote that must really be on the page it names. `assumed` needs the belief, whether it is load-bearing, and a signpost that would show it failing. `unknown` needs an open `UNK-nnn` with an owner. `not-applicable` needs a reason. A generated list above the table shows what is still pending. A row looks like this:

  ```
  | Q-FIN-03@SV-01 | answered | item: [[03-context-and-scope#SV-01 Loyalty points\|SV-01]]; source: SRC-04; answer: Finance carries the points | @you | 2026-11-19 |
  ```

- **Review checkpoints.** `/planner:dump` runs one after the pre-mortem, `/planner:discover` after the read-back, `/planner:shape` before the options, `/planner:boundary` once its app pages are written, and `/planner:grill` on the agenda. Each dispatches five `area-reviewer` subagents, one per focus area, each in a fresh context with only the written pages and its area's owed questions. That adds real time and tokens to every checkpoint, because five subagents read the vault each time. You see one ranked digest, not the reviewers, and you choose what to take now.
- **`planner findings merge`** combines the five replies. It keeps the union, removes duplicates, drops any finding whose quote is not on the page it cites, and never votes. An area that failed says "did not run" with the reason, never "checked, none". The session writes the result into the record's `## Reviews` section: the coverage line, the dropped findings, and a table of the kept ones, `F1.1` and on. Words in `## Reviews` never count as a quote, so a reviewer cannot cite itself.
- **Close writes the ledger and proposes catalogue entries.** It writes a row for every question you took and every finding the merge kept, and types each party or stored value you said exists. Then it asks "Did any other gap turn up late, or by luck?" Each gap you name becomes a draft catalogue entry, and the ones you approve go under `## Catalogue proposals` in the session record. Close never edits the catalogue itself.
- **The gates.** `planner check --gate shape` warns W806 for each row still `assumed`. `--gate grill --item <ID>` warns W807 for each pending question that blocks the item. You may decide anyway, and the session's capture records that. `--gate epics` fails with E805 for each high-severity question still pending. To call the epics complete anyway, override the gate: write `- **Override:** E805 by @you on <date>: <why>` under `## Question ledger`, and each E805 prints as W805 instead. A plain `planner check` never fails because a question is unanswered: you set the pace.
- **voicescore** is unchanged: the optional style hint at close, described under "Optional: voicescore" below.

## Your voice

- **`/planner:voice-seed`** stores 2 or 3 passages of your own writing per voice type, word for word, so drafts sound like you instead of the public seed. Committed examples go in `voice/examples/` and are pushed in a PR, where anyone with access to the repo can read them. Local examples go in `voice/local/`, which is gitignored and stays on your machine. If your employer owns the text, or you're not sure, keep it local.
- **At close,** a fresh subagent runs a voice review of the drafts. Close rewrites each flagged paragraph once, and `planner voicecheck` throws out any rewrite that changed a fact.
- **Harvest.** Only the vault's owner harvests, and only their own edits: close looks through your merged session PRs for paragraphs you rewrote after the draft, and asks before saving each one as an example.

## Optional: voicescore

`planner voicescore <page>` tells you, for each prose paragraph, whether it sits inside or outside your range, for example `outside your range (p96)`. Your range is how far each of your own `owner` and `owner-edit` examples sits from the rest. It uses StyleDistance, a small open style model, so it is a second opinion of a different kind from the voice reviewer. `planner voicescore --rank a.md b.md` orders drafts of the same paragraph. Close adds one line to the PR's Voice review when it can run. It is a hint, not a gate: it never blocks a PR and never rewrites anything.

- **Install:** `python3 -m pip install sentence-transformers`. It pulls in PyTorch, about 1–2 GB. Nothing else in planner needs it.
- **Setup, once:** `planner voicescore setup` is a one-off download of the pinned model, about 0.5 GB, into `~/.cache/planner-voicescore/`. It is the only planner command that touches the network, and it says so before it starts. If your network blocks Hugging Face, ask IT to fetch it.
- **After that it runs offline.** Scoring forces Hugging Face's offline mode, so it never fetches anything, and your text never leaves this machine. Vectors are cached in `.git/planner-voicescore/`, which is never committed.
- **Needs 5 of your examples.** With fewer it still answers but says the score is unreliable. It never falls back to the public seed; `--against seed` compares with the seed and says so.

## After handoff

- **When the first app nears handoff,** use `/planner:epics` and `planner check --gate epics`. Then `planner handoff <APP-id>` in the PR that sets `handed_off`.
- **A senior who disputes a boundary or contract** runs `/planner:challenge`. It writes an open unknown the senior owns and a `**Dissent:**` line, and opens a PR whose check stays red (E316) on purpose.
- **To answer it,** run `/planner:grill` and name the challenge PR or the challenged ID. START opens an answer session on the challenge's branch. Resolve the unknown or set the item back, then `/planner:close` pushes to that branch and comments on the challenge PR. It doesn't open a second PR. A reopened epic is decided again as `reopened → decided`.

## Later

- **Weekly "Vault health" issue.** `.github/workflows/planner-weekly.yml` posts `planner health` every Monday to one issue titled "Vault health". It needs Issues enabled on the repo. It has not been tested live yet, so check the first Monday's run.
- **Not yet run against a real GitHub repo:** the weekly issue, close's owner-only harvest (it reads merged PRs with `gh`), answering a challenge (it comments on the challenge PR with `gh pr comment`), and close's merge of a moved `main`. Each is tested on local git repos only, so watch the first real run of each.
- **Long-lived PRs.** If `main` moves while a long-lived PR is open, merge `origin/main` into the session branch, then run `planner render`. A conflict inside a generated block goes away when you re-render. Close does this before it renders.
- **Vault mode for your own grills:** `integrations/requirements-grill/INSTALL.md` and `integrations/tech-design-grill/INSTALL.md`. Each one backs up first and dry-runs before applying. Nothing has been applied to `~/.claude` yet.
- **Jira export details:** Owner team drops the leading `@` of the handle, so `@org/team` becomes `org/team`. The link points at the repository and commit from `git`, or pass `--repo-url` and `--commit`.
- **Evals:** these are paid runs, and you run them by hand. See `tests/evals/README.md`. Start with the $1 smoke run it describes.

## What's where

| Path | What it is |
|---|---|
| `template/` | The vault you copy, including `CONVENTIONS.md`, the one written format |
| `plugin/` | The `planner` CLI (`check`, `render`, `view`, `explore`, `status`, `next`, `health`, `query`, `questions`, `findings`, `handoff`, `export`, `voicecheck`, `voicescore`, `ladder`, `style`, `upgrade`), the question catalogue in `catalog/questions.yaml`, the format the skills follow in `vault/CONVENTIONS.md`, the session skills (dump, discover, shape, requirements, boundary, allocate, releases, grill, epics, explore, close, ask, challenge, voice-seed, house-voice), the `voice-reviewer` and `area-reviewer` agents, and START, MODES and REVIEW under `references/` |
| `examples/unified-booking/` | A complete made-up vault: a ferry operator's Unified Booking initiative |
| `integrations/` | Vault mode for `requirements-grill` and `tech-design-grill`, as patches |
| `docs/` | Spec, design-session logs, research, plans |
| `tests/` | `python3 -m pytest -q` |
