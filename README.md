# proj-planner

A Claude Code toolkit for planning at the initiative level. It covers everything from a one-line ask to fully specified epics, written in Markdown that every reader can follow.

## Start here tomorrow

1. **Make a vault.** Copy `template/` into a new GitHub repo, then follow its `README.md` setup checklist, steps 1 to 10. Step 2 copies this repo's `plugin/` folder into the vault. You need Python 3.11+ and PyYAML: `python3 -m pip install pyyaml`. Your Mac's `python3` already has PyYAML 6.0.3. If pip refuses on another machine with "externally-managed-environment", install PyYAML into a venv (`python3 -m venv ~/.venvs/planner && ~/.venvs/planner/bin/pip install pyyaml`) and run planner with `~/.venvs/planner/bin/python3`.
2. **Start every session with `bin/claude-planner`**, from inside the vault. The skills only load through that launcher.
3. **Run your first session:**
   - `/planner:dump` gets everything out of your head. Ideas, worries, unknowns and wild ones all count. Claude doesn't push back.
   - `/planner:close` promotes what you keep, drafts the prose in the house voice, has a fresh reader review it, renders and checks the vault, and opens the PR.
4. **Next sessions, in roughly this order.** Every session starts by running `planner next`, which suggests one app and one mode. It is a suggestion, not a decision.
   - `/planner:discover` reads your sources and asks you to confirm what exists today.
   - `/planner:shape` offers 2–3 options to react to.
   - `/planner:grill` is the only thing that can mark an item `decided`, and only after your explicit yes.
   - `/planner:ask` answers questions from the vault. It is read-only, and anything the vault doesn't hold comes back as `Not recorded:`.
5. **Before each PR,** run `python3 .claude/skills/planner/bin/planner check`. CI runs it too. If you make it a required check, a broken vault can't merge.
6. **For the CIO,** run `python3 .claude/skills/planner/bin/planner view --out ~/Desktop/<name>.html` and email the file. It works offline and can't run page script or make network calls.

The kill rule you set: if it isn't faster than plain Markdown after five sessions, cut back to the conventions, `check` and the viewer.

## The planner CLI

Run each one as `python3 .claude/skills/planner/bin/planner <command>` from the vault root. Only `render`, `view`, `handoff` and `export` write files.

| Command | What it tells you |
|---|---|
| `planner status` | Every app's stage, certainty mix and oldest open unknown |
| `planner next` | The one app and mode to work on next, with the reason. `probe` means: ask the unknown's owner, or research it |
| `planner health` | Stale pages and sources, overdue unknowns, and days since the last closed session, as Markdown |
| `planner query get <ID>` | Where an ID lives and its state. `refs`, `find` and `status` too. Add `--json`. `/planner:ask` uses it |
| `planner questions` | The questions the catalogue says this vault owes, one copy per subject, and where each stands in the question ledger. `--open`, `--area`, `--subject` and `--json`; `--digest` ranks the undisposed ones, `--stats` counts how often each entry ends not-applicable |
| `planner findings merge <folder>` | Merges the focused reviewers' findings: keeps the union, removes duplicates, drops any finding whose quote is not on the page it cites, and says per area whether it found something, found nothing, or did not run |
| `planner handoff <APP-id>` | Writes `handoffs/<APP-id>.md`, the slice a senior accepts |
| `planner handoff verify <APP-id>` | What changed in that slice since handoff. Exits 1 when something accepted changed |
| `planner voicecheck <before> <after>` | Fails when a rewrite lost or moved an ID, number, date, link, code span, table cell or negation |
| `planner voicescore <page>` | Optional: whether each prose paragraph sits inside or outside your own voice's range. See "Optional: voicescore" below |
| `planner export jira-csv --out epics.csv` | One row per epic for Jira's CSV import. Export only: nothing is read back and no page carries a Jira field |

`planner render` fills every generated block, including the generated diagrams: the context map, system context, each app's context and the capability map. Never edit inside a block. Close runs `planner render` for you.

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
| `plugin/` | The `planner` CLI (`check`, `render`, `view`, `status`, `next`, `health`, `query`, `questions`, `findings`, `handoff`, `export`, `voicecheck`, `voicescore`), the question catalogue in `catalog/questions.yaml`, the session skills (dump, discover, shape, grill, epics, close, ask, challenge, voice-seed, house-voice), the `voice-reviewer` and `area-reviewer` agents, and START, MODES and REVIEW under `references/` |
| `examples/unified-booking/` | A complete made-up vault: a ferry operator's Unified Booking initiative |
| `integrations/` | Vault mode for `requirements-grill` and `tech-design-grill`, as patches |
| `docs/` | Spec, design-session logs, research, plans |
| `tests/` | `python3 -m pytest -q` |
