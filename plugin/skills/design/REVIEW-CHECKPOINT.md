# Review checkpoint

Run this once the design's sections are written, before the self-audit. The interview only surfaces what someone in the room knows. Fresh reviewers, each reading one area with no memory of the session, find what nobody mentioned: a vendor limit, a license clause, a weekend freeze window.

## 1. Dispatch five reviewers

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela reviewers prepare --team --checkpoint "design review" --focus <the design doc> <CONTEXT.md> <each ADR> <the app's vault pages>`. The vault pages are the ones `TECH-DESIGN-FROM-VAULT.md` lists (standalone, the requirements doc). It writes five packets, one per area (vendors and integrations, data and licensing, failure and recovery, security, operations), each with the area's questions, the pages to read and the shape of a finding, and prints where each packet is.

Start five subagents in parallel, each with a fresh context, and give each only its packet: the subagent reads the packet and the pages it lists. Save each reply exactly as it came back, to the path its packet names. If a reviewer fails or can't be started, save what happened instead, and never an empty list: that would read as "checked, none". If the command fails, say in one plain sentence that the review couldn't be prepared, and why in your words.

## 2. Check and merge

- Drop a finding whose quote is not in the design doc word for word. A reviewer that misquotes is guessing.
- Merge findings that ask the same question; keep the higher severity and both areas.
- Drop a finding that an existing open question, deferral or ADR already answers, and say which.
- Rank: high first, then by how many components the scenario touches.

## 3. Dispose with the team lead

Say how many findings there are and how many are high, then take them in order, about four to a turn, each in a plain sentence with its scenario. Settle them one at a time, as `GRILL-LOOP.md` does, with your recommended disposition:

- **Answer now:** the team lead knows; update the design section and note the finding as resolved.
- **Open question:** write an `OQ-XXX` with the scenario, what would unblock it, and what it affects. While it is open the design can be at most `complete-with-gaps`, with a `gaps[]` entry naming the question.
- **Defer:** a `D-XXX`, when the answer is known and deliberately postponed.
- **Accept the gap:** the team lead goes ahead knowingly; it becomes a `gaps[]` entry and the status can be at most `complete-with-gaps`.
- **Not applicable:** with the reason, in one line.

Every high-severity finding ends with one of these five. Then go on to `${CLAUDE_PLUGIN_ROOT}/references/NEG-AUDIT.md`.
