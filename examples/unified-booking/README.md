---
id: readme
type: index
title: Unified Booking vault
authored: authored
---

# Unified Booking vault

This is a mock. Harbourline, its systems, teams and numbers are all made up. The vault holds one initiative, INI-002 Unified Booking, as it looks once every area has reached stage 6 and its epics are written.

Start at [[01-goals|Unified Booking: Goals]].

## How the vault is laid out

The whole vault is one initiative. Pages and folders are numbered by arc42 section.

- Root pages: Goals (§1), Constraints (§2), Context & scope (§3), Solution strategy and Capability delta (§4), Unknowns & risks (§11), Glossary (§12), and the source register `sources.md`.
- `05-building-blocks/`: the overview, context map and contract list, then one page per application in scope with its containers and contracts.
- `06-runtime/`: the cross-app flows, then one runtime page per application in `apps/`.
- `08-concerns/`, `09-decisions/`, `13-epics/`: an index page plus one page per concern, architecture decision record (ADR) or epic.
- `capabilities/`: one page per capability this initiative touches.
- `sessions/`: one record per Grill session that decided something. They are working notes, not the plan.

## Reading paths

| Reader | Pages, in order |
|---|---|
| CIO / CTO | [[01-goals\|Goals]] → [[03-context-and-scope\|Context & scope]] → [[11-unknowns-and-risks\|Unknowns & risks]] |
| Product | [[01-goals\|Goals]] → [[04a-capability-delta\|Capability delta]] → [[06-flows\|Flows]] |
| Architects | [[03-context-and-scope\|Context & scope]] → [[04-solution-strategy\|Strategy]] → [[05-building-blocks\|Building blocks]] → [[09-decisions\|Decisions]] |
| Team seniors | Your app's building-blocks page → its runtime page → [[13-epics\|Epics]] |
| QA | [[concern-testing\|Testing strategy]] → [[06-flows\|Flows]] → [[13-epics\|Epics]] |

Open this folder in Obsidian to get the graph view. Run `python3 build-viewer.py` from `examples/` to rebuild the HTML viewer.
