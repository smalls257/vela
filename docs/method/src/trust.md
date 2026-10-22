---
title: Can I trust it
lede: Trust should rest on things you can check yourself. This page says what a passing check means, what it can't tell you, how the chain from goal to ticket holds together, and what hasn't been proven yet.
---

## What a passing check promises

When `vela check` passes with no errors, a reader can rely on these. They are things a script can see in the pages.

- **Every link resolves.** Each ID and wiki-link points at something that exists.
- **States are legal and decisions are earned.** A page marked decided links a session that was a grill, or an override says otherwise. A fact has a source.
- **The allocation table is honest about itself.** A row names a requirement and a contract that exist.
- **Questions have owners.** An `answered` ledger row names a registered source, or a quote really on the page it cites.
- **Overrides are well formed and current.** Even a typo like `**Overide:**` is caught.
- **Generated blocks are up to date,** and **every diagram parses,** or a warning or error says so.

At the stricter `--gate epics`, three more hold: every changed capability is in some epic, every new or changed contract is delivered by one, and every concern marked addressed has an epic criterion that does the work.

::: fold Where each is stated and enforced
Links: E105 ([`test_links.py`][t-links]). States and decisions: E303, E317 ([`test_items.py`][t-items]). Allocation: E330 to E333 ([`test_allocation.py`][t-allocation]). Ledger evidence: E801, E802 ([`test_ledger.py`][t-ledger]). Overrides: E321, E322, E398 ([`test_override_until.py`][t-override_until]). Generated blocks: W402 ([`test_render.py`][t-render]). Diagrams: E604 ([`test_diagram_parse.py`][t-diagram_parse]). Epics gate: T1 to T7, E805 ([`test_trace.py`][t-trace]). All codes are defined in [rules.py][rules] and listed in [schema.py][schema].
:::

## What it doesn't promise

Being honest about this matters more than any claim above.

- **It checks structure, not truth.** It can tell that a fact cites SRC-006, not that SRC-006 says so. The one exception is a quote in the question ledger.
- **It can't see a question nobody typed.** The question catalog (29 entries in five areas, counted in [`questions.yaml`][questions-yaml] on October 21, 2026) fires per subject someone has typed. If nobody types "the plan holds customer money," the money questions never fire. The review checkpoints exist to catch that, and can miss too.
- **A plain check is easy to pass.** On the demo plan, `vela check` reported "0 errors, 54 warnings" and `vela check --gate epics` reported 29 errors, mostly high-severity questions nobody had handled (October 21, 2026, commit `77940a68`). A green plain check means the plan is well formed, not finished.
- **It can't tell whether the person really said yes.** Where Claude Code's hooks run, `vela record add` can tell their words from the model's. Where they don't, the line is marked unverified. The command line refuses; the hooks are earlier feedback, "never the gate."
- **It doesn't read the team's design.** `vela check` skips `docs/`. `vela tickets check` holds those traces instead.
- **The flow check reads the plan, never the code,** and only what's written in the strict form.
- **It doesn't track build progress.** "Each team tracks it in its own tickets, not here."

When the plan doesn't know, it says so. Breakdown writes a release fit of "cannot tell" and why: "Sizes add to about 20 to 37 days for one engineer, and the design names four builders but not how many days each has."

::: fold Where this is stated
The catalog finds only what is written into it, and W809 is a partial net ([Questions and the ledger][c-q], [README][readme], [`test_untyped.py`][t-untyped]). Hooks are earlier feedback ([hooks.json][hooks], [`test_hooks.py`][t-hooks], [`test_said.py`][t-said], [`test_record_add.py`][t-record_add]). `vela check` skips `docs/` ([Layout][c-layout]). The flow check reads the plan only ([Flow check][c-fcheck]). Build progress is each team's own ([Generated blocks][c-gen]). Release fit "cannot tell" is in [the breakdown skill][s-breakdown], pinned by [`test_tickets.py`][t-tickets].
:::

## Every story traces back

Traceability means walking from any item to the reason for it and back. Click a link in the chain.

::: deck chain | The chain from goal to ticket

::: card goal | Goal | Why are we doing it? | link | Chain
A goal row carries a `Trace:` line pointing at the capabilities and unknowns it rests on.
::: end card

::: card capability | Capability | What can the business do? | link | Chain
Something the business can do after the change, such as "see what I owe after a client call." Its requirements live on its page.
::: end card

::: card requirement | Requirement | What must be true, no app named? | link | Chain
Written as `CAP-023.FR1`, with acceptance criteria as bullets. It names no app.
::: end card

::: card share | Allocated share | Which app does what? | link | Chain
A row on the app's page naming the requirement, the one-sentence share, the contract it goes through and a state. The format example reads `accepts the order, rejects fractions and shorting, records the fill | CON-006 | assumption`.
::: end card

::: card epic | Epic | One team's work | link | Chain
Its criteria end with a line such as `Trace: CAP-022.FR1, CON-025 · AC1`, naming the requirement and contract with a stable criterion number.
::: end card

::: card story | Story | In the team's breakdown | link | Chain
Names the requirements, contracts and epic criteria it covers, and its slice. It also traces to a design component, which traces to the allocated share.
::: end card

::: card ticket | Ticket | Copied from the story | link | Chain
Nothing is added on the way out. Each ticket traces back to its story, the story to the epic, the epic to the requirement.
::: end card

::: end deck

The dashboard walks the same chain from a capability down to its requirements, apps, epics and contracts, and points at the links that are missing.

::: fold The Requirements-to-epics view
![The Requirements to epics view: each requirement, the app that carries it, and the epic behind it, with missing links marked in red](dashboard-trace.png)
:::

::: fold Where this is stated and enforced
Stated in [Epics and traceability][c-epic] (rules T1 to T7), [Requirements and allocation][c-req] and [Generated blocks][c-gen]. Enforced by [trace.py][trace-py]. Pinned by [`test_trace.py`][t-trace], [`test_allocation.py`][t-allocation], [`test_trace_blocks.py`][t-trace_blocks].
:::

## How vela is tested

Trust should rest on things you can run.

- **One gate, run by hand, in CI and before a push.** `.githooks/gate` runs the semgrep rules, a ruff scan, a format-file sync check, `vela check` on the template and the worked example, and the pytest suite. About 230 test files hold about 3,200 test functions (counted October 21, 2026 with `ls` and `grep`: a count of tests, not proof they pass on your machine). Its full mode prints every skip and why.
- **Docs are held to the same standard.** Diagrams in Markdown under `docs/` must parse, and a test fails if this site's pages are out of date with their source.
- **The dashboard's self-test clicks every node of every diagram** and fails on an empty panel.

::: fold The session simulator, and how it avoids teaching to the test
A prompt that has quietly learned the test looks great and helps no one. So `tests/sim/` runs a simulated solution lead (another model) through real sessions, with a hidden brief of facts, wrong beliefs and gaps. Four guards against teaching to the test:

1. **Dev and holdout personas,** tuned against with generic failure descriptions only, never a key item or a persona's names.
2. **Holdouts are sealed:** scores only, unless `--reveal`.
3. **The plugin is scanned for leaks.** `test_sim_seal.py` fails if a persona's names or any six-word run of brief text appears under `plugin/`.
4. **A change counts only when the keep rule says so:** dev personas improve beyond the spread, no holdout or voice measure gets worse.

The verdict is recall and precision. "Recall up with precision down is never a GO." The judge is itself a model, so every score cites a turn, and the simulator "can't say whether it's faster than plain Markdown for the user. Only real sessions under the kill rule can." The design notes say these runs "found most of the gaps fixed so far" but give no dates, counts or scores, and this site hasn't re-measured them.
:::

::: fold Where this is stated and enforced
Stated in [.githooks/gate][gate], [CONVENTIONS.md][conventions] (its opening) and [tests/sim/README.md][simreadme]. Enforced by the gate and the plugin's CI workflow `vela-check.yml`. Pinned by [`test_diagram_parse.py`][t-diagram_parse], [`test_final_wave.py`][t-final_wave], [`test_explorer_browser.py`][t-explorer_browser], [`test_sim_seal.py`][t-sim_seal], [`test_sim_precision.py`][t-sim_precision], [`test_sim_compare.py`][t-sim_compare].
:::

## What hasn't been proven yet

Stated in the repository's own README and design notes. We haven't added to the list or smoothed it over.

- **No finished real initiative is on record.** The demo plan comes from the simulator. The README's kill rule is the honest test: "if it isn't faster than plain Markdown after five sessions, cut back to the conventions, `check` and the viewer."
- **No comparison with plain Claude Code** is recorded in the design notes yet.
- **Not yet run against a real GitHub repo:** the weekly health issue, close's owner-only harvest, answering a challenge, and close's merge of a moved `main`. "Each is tested on local git repos only."
- **Vault mode for the owner's own grills** hasn't been applied to anyone's `~/.claude` yet.
- **Cowork:** whether plugin hooks run, and whether only the working folder keeps files between sessions. `/vela:where` answers both on a given machine.
- **Open design questions:** how many questions to raise before they bury the lead, what "complete" should mean when a design has accepted gaps, and whether the tool should draft the pages or mainly interview you.
- **The question catalog is small** (29 entries), and finds only what has been written into it.

A reasonable way to adopt it is the README's own: run a few real sessions on a small initiative, keep the kill rule in mind, and watch the first real run of each item above.

::: fold Where this is stated and enforced
Stated in the [README][readme] ("Later"), "What is still open" in [PHILOSOPHY.md][phil], and [the guide][guide] (Cowork). A test keeps the README honest about what hasn't run against GitHub, [`test_final_wave.py`][t-final_wave].
:::
