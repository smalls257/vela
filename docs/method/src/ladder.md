---
title: From idea to tickets
lede: Vela breaks the journey into rungs. Each rung is one kind of working session with Claude. It answers one question, writes one kind of thing, and makes the next question easier to ask.
---

## The ladder: click a step

Three stretches: find out what you're dealing with, cut it into apps and releases, then let each team build. The rounded gold steps are grills, the only sessions that can mark something decided.

::: deck ladder | The steps from idea to tickets

::: card dump | Dump | What is on your mind? | rung | 1. Find out
**Writes.** Notes only, each in the person's own words with their name beside it. Nothing reaches a plan page until the session closes.

**Why first.** Early on, people hold back risks they think are impolite to raise. Dump asks no one to defend an idea. Claude builds on each one with a "what if", marked as Claude's, then runs a pre-mortem [3]: "it's six months on and this failed; what went wrong?"

**What stops you skipping it.** Little does, on purpose. But a dump can't write `decided` or `fact`, or edit a page outside the session record.

::: fold Where this is stated and enforced
Stated in [the dump skill][s-dump] and [MODES.md][modes]. Enforced by the skill's "Never" list and the hook that guards generated blocks and hand-moved states ([hooks.json][hooks]). Pinned by [`test_apply_marks.py`][t-apply_marks] and [`test_hooks.py`][t-hooks].
:::
::: end card

::: card discover | Discover and Import | What exists today? | rung | 1. Find out
**Writes.** Facts, each linked to a source registered in `sources.md` (the Library). Import does the same for an initiative already under way, and writes nothing until the lead corrects its map.

**Why here.** You can't design around a system you haven't described, and this is where guesses get sorted from facts. A source either `exists` (describes what runs today) or `intends` (a plan or roadmap). A line from an `intends` source is an assumption, "however sure it sounds". When two sources disagree, vela writes a question naming both.

**What stops you skipping it.** Every fact must cite a source, and Claude's general knowledge is never one. `vela apply` refuses a fact from a plan or an unregistered source.

::: fold Where this is stated and enforced
Stated in [the discover skill][s-discover], [the import skill][s-import] and [Certainty and sources][c-cert]. Enforced by `vela apply` and E307, E308, E313 ([rules.py][rules]). Pinned by [`test_apply_marks.py`][t-apply_marks] and [`test_library_register.py`][t-library_register].
:::
::: end card

::: card shape | Shape | What could we do? | rung | 1. Find out
**Writes.** The option you pick, at `assumption`, and each rejected option with its reason.

**Why here.** The lead gets something concrete to react to: two or three options, never one and never more than three, each with what it does, costs and rules out. First, a review checkpoint asks what would have to be true for each to work, so a lead sees "holds only if the card processor certifies the dock readers" before choosing.

**What stops you skipping it.** Shape can't decide. At its end `vela check --gate shape` lists every assumed answer still unresolved (W806).

::: fold Where this is stated and enforced
Stated in [the shape skill][s-shape] and [Questions and the ledger][c-q]. Enforced by W806 ([questions.py][questions-py]). Pinned by [`test_question_gates.py`][t-question_gates].
:::
::: end card

::: card grill | Grill | Are we sure enough to decide? | grill | 1. Find out
**Writes.** The item set to `decided`, who decided it, when, and why, in the lead's own words.

**Why it sits here.** A grill is where certainty gets earned. One question at a time, with a recommended answer kept under pushback. Edge cases, because the happy path never forces a precise answer ("it's 8:58, the call starts at nine, the calendar doesn't answer; what does the person see?"). Then a read-back and an explicit yes. "ok", "next" and silence don't count.

**What stops you skipping it.** `vela check` reports E303 for a decision with no grill, E316 when an open question blocks it, and W390 when no reason is recorded. You may decide past a block, as an override, but the check shows it.

::: fold Where this is stated and enforced
Stated in [the grill skill][s-grill], [Certainty and sources][c-cert] and [Overrides][c-over]. Enforced by E303, E316, E317, W390 ([rules.py][rules]) and `vela decide`, which re-runs the gate before it writes. Pinned by [`test_gates.py`][t-gates], [`test_decide.py`][t-decide], [`test_why.py`][t-why].
:::
::: end card

::: card requirements | Requirements | What does the business need? | rung | 2. Cut it up
**Writes.** For each capability, requirements with acceptance criteria, such as "a person has a separate switch for meetings, for email and for calendar." No app, screen or technology is named.

**Why before boundary.** If you cut the apps first, the cut decides what the requirements can say. Written first, they give each cut something to be tested against: which it carries whole, which it splits (each split needs a contract), and which it leaves with no app.

**What stops you skipping it.** Boundary offers to write them first. If the strategy isn't decided, the session warns they may be rewritten, and you can go on as an override. The demo lead did: "requirements will show us what questions the grill needs to ask anyway."

::: fold Where this is stated and enforced
Stated in [the requirements skill][s-req] and [Requirements and allocation][c-req]. Enforced by the session's "Never" list and `vela boundary cover` ([boundarycover.py][cover-py]). Pinned by [`test_boundary_cover.py`][t-boundary_cover] and [`test_next_requirements.py`][t-next_requirements].
:::
::: end card

::: card boundary | Boundary | Which apps, and where does each end? | rung | 2. Cut it up
**Writes.** One page per app: what it does and doesn't do, the contracts it offers and needs, what happens when something fails, and its journeys. Each contract gets a case table.

**Why here.** Claude asks how the product comes apart before offering any cut, because "one helper" hides separate lifecycles. Then two or three cuts, with what each makes easy and hard. The demo plan compared four apps, three and two, and recorded why it rejected the others.

**What stops you skipping it.** An app with only a stub page goes back to Boundary in `vela next`. Pages are written line by line after a yes and never above `assumption`.

::: fold Where this is stated and enforced
Stated in [the boundary skill][s-boundary], [Fact bullets][c-facts] and [Areas and stages][c-stages]. Enforced by `vela next`, `vela ladder` and W380 for a contract with no case table. Pinned by [`test_ladder.py`][t-ladder] and [`test_cases.py`][t-cases].
:::
::: end card

::: card allocate | Allocate | Who carries which part? | rung | 2. Cut it up
**Writes.** A row per requirement on each app's page: a share of 40 words or fewer, the contract it goes through, and a state.

**Why here.** This is where "work that falls between teams" is caught. A requirement no app carries is a trace gap: a blank row, a warning (W505), and an error under the epics check.

**What stops you skipping it.** In the demo plan, which skipped allocation, `vela check` says so for each one: "Run /vela:allocate CAP-023, or add a row for CAP-023.FR3 to the app page that delivers it."

::: fold Where this is stated and enforced
Stated in [the allocate skill][s-allocate] and [Requirements and allocation][c-req]. Enforced by E330 to E333, W366 and trace rule T7 ([trace.py][trace-py]). Pinned by [`test_allocation.py`][t-allocation] and [`test_trace.py`][t-trace].
:::
::: end card

::: card releases | Releases | What goes live first, and when? | rung | 2. Cut it up
**Writes.** The slices, starting with the tracer, and the release milestones that point at them. A release has a real date, or none. Never an invented one.

**Why here.** You can't say what is "first" until you know what exists and who carries it. Date first, then must, should and later, requirement by requirement. A requirement can split across releases by acceptance criterion.

**What stops you skipping it.** `vela check` warns when a requirement is on no release (W343), when release one has no end-to-end path (W345), or when a path crosses an app release one delivers nothing of (W347). A dated-release rule is an error (E344).

::: fold Where this is stated and enforced
Stated in [the releases skill][s-releases], [Releases][c-rel] and [Slices][c-slice]. Enforced by W343, W345, W347, E344 ([rules.py][rules]). Pinned by [`test_releases.py`][t-releases] and [`test_tracer.py`][t-tracer].
:::
::: end card

::: card handoff | Handoff | Is an app ready for its team? | grill | 2. Cut it up
**Writes.** `handed_off` on the app page, the senior's name and the date, and a record of everything accepted, each item with a fingerprint.

**Why here.** The team lead takes the boundary as given and designs inside it. Before handing over, Claude reads back everything that isn't firm: assumptions, contracts with no case table, providers nobody has designed. Handing over anyway is your call, recorded as an override.

**What stops you skipping it.** The checklist, and the fact that design starts only on a handed-off app. `vela handoff verify` later shows exactly what changed.

::: fold Where this is stated and enforced
Stated in [the grill skill's handoff steps][s-handoff] and [Handoff][c-hand]. Enforced by `vela handoff`, `vela handoff verify` and W386 to W388. Pinned by [`test_handoff.py`][t-handoff] and [`test_handoff_warnings.py`][t-handoff_warnings].
:::
::: end card

::: card epics | Epics | What does each team build? | rung | 3. Let teams build
**Writes.** Epic pages with acceptance criteria a tester can see at a contract or flow boundary, never inside a component, each with a line saying which requirement and contract it traces to.

**Why after handoff.** The lead writes and decides epics against the boundary while the senior designs. Criteria come from the allocated rows, so no behavior is invented. If one needs behavior no requirement holds, the session sends you back to requirements.

**What stops you skipping it.** `vela check --gate epics` turns trace gaps into errors and fails on every high-severity question nobody has handled (E805).

::: fold Where this is stated and enforced
Stated in [the epics skill][s-epics] and [Epics and traceability][c-epic]. Enforced by `vela check --gate epics` ([questions.py][questions-py]). Pinned by [`test_epics_cli.py`][t-epics_cli] and [`test_question_gates.py`][t-question_gates].
:::
::: end card

::: card design | Design | How will the team build it? | rung | 3. Let teams build
**Writes.** `docs/tech-design/<slug>.md` and decision records, by the team's lead engineer, ending in a pull request.

**Why here.** "Solution design is mine; app design is theirs." Design interviews the lead engineer one question at a time, starts from the app's piece of the tracer, and traces every component back to the requirements allocated to it.

**What stops you skipping it.** Design checks the app is handed off, runs `vela handoff verify`, and warns before designing against a slice that isn't fully checked.

::: fold Where this is stated and enforced
Stated in [the design skill][s-design] and [TECH-DESIGN-FROM-VAULT.md][tdv]. Enforced by the design session itself; `vela check` doesn't read `docs/` ([Layout][c-layout]). Pinned by [`test_design_skill.py`][t-design_skill].
:::
::: end card

::: card tickets | Breakdown and Tickets | Which stories, and what goes to the tracker? | rung | 3. Let teams build
**Writes.** `docs/plan/<slug>-breakdown.md`: stories traced to requirements and design components, tracer stories first, tasks sized small, medium or large. Then tickets as Markdown, a CSV for Jira, or through Jira tools you already have.

**Why here.** The plan is the shared model translated into one team's terms, not a new plan. Breakdown builds a coverage table first, and "an empty cell is work left out." `vela tickets check` reports stories with no trace, requirements with no story, and quoted criteria that don't match word for word.

**What stops you skipping it.** Breakdown won't start on an incomplete design. Tickets won't write from a plan that's still moving, and never create anything in Jira without an explicit yes. A wrong criterion is a challenge back to the vault, never a quiet reword.

::: fold Where this is stated and enforced
Stated in [the breakdown skill][s-breakdown] and [the tickets skill][s-tickets]. Enforced by `vela tickets check` and `vela tickets write`, which use no model. Pinned by [`test_tickets.py`][t-tickets] and [`test_breakdown_to_tickets.py`][t-breakdown_to_tickets].
:::
::: end card

::: end deck

## Why this order

Each rung reduces what the next has to guess. Requirements without apps can't be bent to fit an app. Apps without contracts leave the joins to chance. Allocation without releases doesn't say what comes first. Epics without allocation invent behavior. Design without a handoff designs against a boundary that may still move.

Read it upside down and it explains itself: a ticket that can't name its epic, a story that can't name its requirement, a requirement that can't name the need it served. That is the "no traceable reason" failure, caught at the rung where it starts. This is vela's own design reasoning, with no outside source.

## Two details that are easy to miss

1. **Requirements come before boundary.** The README lists boundary first, but the format says requirements are written once the strategy is decided, "so boundary can test each cut against them." `vela next` suggests them in that order.
2. **A grill isn't one rung.** It is the way anything becomes decided, so it sits between rungs: on the strategy, on each app and its contracts, and to hand an app over.

::: fold Where this is stated and enforced
Stated in [Requirements and allocation][c-req], [Releases][c-rel] and [Areas and stages][c-stages]. Enforced by `vela next` and `vela ladder` ([Progress and next step][c-progress]). Pinned by [`test_next_requirements.py`][t-next_requirements] and [`test_ladder.py`][t-ladder].
:::

## You don't have to follow the order

`vela next` suggests a step from the state of the plan, and you may skip any stage you already have. What the order gives you is a reason for each question coming when it does. Skip a rung that something later needs, and the checks on its card say so, with the command to run. Each session's start, end, must and must-not are in [MODES.md][modes] and [START.md][start].
