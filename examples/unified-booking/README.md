---
id: readme
type: index
title: Unified Booking vault
authored: authored
last_verified: 2026-11-20
---

# Unified Booking vault

This is a mock. Harbourline, its systems, teams and numbers are all made up. The vault holds one initiative, INI-002 Unified Booking, as it looks once every area has reached stage 6 and the epics are in Jira.

Start at [[01-goals|Unified Booking: Goals]].

## Status

<!-- status:start -->
<!-- generated: do not edit -->
**Stage:** every area is at Epics · 9 of 9 apps at Epics · 1 open unknown · oldest verification 2026-11-20

| | Progress | Notes |
|---|---|---|
| **Apps through the ladder** | ▰▰▰▰▰▰▰▰▰▰ 9/9 | slowest area: Epics |
| Goals to strategy (§1–4) | ▰▰▰▰▰▰▰▰▰▰ 5/5 | 5 pages |
| Building blocks (§5) | ▰▰▰▰▰▰▰▰▰▰ 9/9 | 9 pages |
| Runtime (§6) | ▰▰▰▰▰▰▰▰▰▰ 12/12 | 12 pages |
| Concerns (§8) | ▰▰▰▰▰▰▰▰▰▰ 8/8 | 8 pages |
| Decisions (§9) | ▰▰▰▰▰▰▰▰▰▰ 4/4 | 4 pages |
| Epics | ▰▰▰▰▰▰▰▰▰▰ 9/9 | 9 of 9 have a Jira key |
| Capabilities | ▱▱▱▱▱▱▱▱▱▱ 0/8 | 0 of 8 reconciled with an official capability map; the rest are proposed |

| Decisions and open questions | Progress | Notes |
|---|---|---|
| ADRs decided | ▰▰▰▰▰▰▰▰▰▰ 4/4 | |
| Contracts decided | ▰▰▰▰▰▰▰▰▰▰ 7/7 | |
| Capability changes decided | ▰▰▰▰▰▰▰▰▰▰ 6/6 | |
| Concerns addressed | ▰▰▰▰▰▰▰▰▰▰ 8/8 | unexamined: none |
| Unknowns resolved | ▰▰▰▰▰▰▰▰▰▱ 6/7 | open: [[11-unknowns-and-risks#UNK-006\|UNK-006]] |
| Risks mitigated | ▰▰▰▰▰▰▰▰▰▰ 2/2 | |

**Sessions:** Dump & Diverge 1 · Discover 2 · Shape 5 · Probe 1 · Grill 11 · 20 in total, see [[session-history|Session history]]
<!-- /generated -->
<!-- status:end -->

## How the vault is laid out

The whole vault is one initiative. Pages and folders are numbered by arc42 section.

- Root pages: Goals (§1), Constraints (§2), Context & scope (§3), Solution strategy and Capability delta (§4), Unknowns & risks (§11), Glossary (§12), Session history.
- `05-building-blocks/`: the overview, context map and contract list, then one page per application in scope with its containers and contracts.
- `06-runtime/`: the cross-app flows, then one runtime page per application in `apps/`.
- `08-concerns/`, `09-decisions/`, `13-epics/`: an index page plus one page per concern, ADR or epic.
- `capabilities/`: one page per capability this initiative touches.

## Reading paths

| Reader | Pages, in order |
|---|---|
| CIO / CTO | [[01-goals\|Goals]] → [[03-context-and-scope\|Context & scope]] → [[11-unknowns-and-risks\|Unknowns & risks]] |
| Product | [[01-goals\|Goals]] → [[04a-capability-delta\|Capability delta]] → [[06-flows\|Flows]] |
| Architects | [[03-context-and-scope\|Context & scope]] → [[04-solution-strategy\|Strategy]] → [[05-building-blocks\|Building blocks]] → [[09-decisions\|Decisions]] |
| Team seniors | Your app's building-blocks page → its runtime page → [[13-epics\|Epics]] |
| QA | [[concern-testing\|Testing strategy]] → [[06-flows\|Flows]] → [[13-epics\|Epics]] |

Open this folder in Obsidian to get the graph view. Run `python3 build-viewer.py` from `examples/` to rebuild the HTML viewer.
