---
name: discover
description: Discover session for an initiative vault. Registers documents and code repositories in sources.md, reads the ranked ones, shows "here's what I think exists" for correction, then writes facts that each cite a SRC-nn. Use when nobody is sure what exists today.
argument-hint: "[area, app or question]"
disable-model-invocation: true
---

# Discover

Find out what exists before anyone designs anything. Every fact this session writes cites a source in `sources.md`.

1. Run the steps in `.claude/skills/planner/references/START.md` with mode `discover`. Read the Discover row of `.claude/skills/planner/references/MODES.md`.
2. List the files in `.inbox/` and the rows in `sources.md`. Also grep earlier session records for `to fetch:` captures, and ask the user whether each document has arrived: one that has goes in the register below, and one that has not stays an unknown. Add a row for each new document: `ID | Title | Owner | Date | Kind | Location`. `Kind` is `exists` for a document that describes what runs today, and `intends` for a plan, deck or roadmap. A local clone of a code repository is `Kind: repo`, with Location `<url>@<sha>` from `git -C <clone> remote get-url origin` and `git -C <clone> rev-parse HEAD`. A file that lives only in `.inbox/` has Location `local only`.
3. Show the register and ask the user to rank it and cut what is not worth reading. Propose a `Kind` for each source it keeps, and the user says yes or corrects it. Do not move on until every kept source has a confirmed `Kind`, unless the user says to: then say once that an unconfirmed `Kind` can turn a plan into a fact, write the source's `Kind` as you proposed it, and record the override as `START.md` says. Read only the top-ranked sources. Before the user cuts a source, say which other sources cover the same area: sources that describe the same systems, teams or plans are worth reading together, because a clash between them only shows when both are read.
4. Show "Here's what I think exists" as a numbered list. Label every line with its source `SRC-nn` and that source's `Kind`. Write nothing to a page yet. Write only the lines the user confirmed with an explicit yes for that line. Silence, or "looks fine" with no yes per line, does not count: ask again.
   Under every such list, the first one included, add **What these sources imply**. Compare the lines with each other and with what the user has said. Name each of these you find, one bullet each, as a question that cites the line numbers:
   - two systems, schemes or teams doing the same job, and what that means for anything that must span both;
   - service levels, hours, targets or limits that differ between things that will have to work together;
   - dates, terms or numbers that disagree between sources, or with what the user believes;
   - two maps, models or standards of the same thing, and which one wins;
   - a plan in an `intends` source that a fact from an `exists` source contradicts;
   - something every line depends on that no line names an owner for;
   - something that must follow a customer, booking or case across two systems, such as a need, a consent, an entitlement or a balance, where only one side has a place for it;
   - a belief the user has stated that no line supports, or that a line contradicts. Name the claim and say which line, or that no source covers it.

   Listing two lines side by side is not flagging them: say what clashes and why it matters. Ask the user which ones are worth an unknown.
5. After each correction round, write what was confirmed and commit a checkpoint:
   - A line from an `exists` or `repo` source is a `fact`, with `sources: [SRC-nn]` on the page or `- **Source:** SRC-nn` on a contract.
   - A line from an `intends` source is an `assumption`, however sure it sounds. "Ready in Q4" in a deck is a plan, not a fact.
   - A line about the future ("will", "planned", "by Q4", "ready in") is an `assumption`, whatever its source's `Kind`.
   - A line the user knows first-hand is a `fact` only once it has its own row in `sources.md`, with the user's handle as Owner and today's date. `first-hand` is not a registered `Kind`, so give the row `Kind: exists` and Location `first-hand: <handle>`. That row is the source the fact cites.
   - Each fact written also gets a capture line and a `## Changes` row. Mark that capture at once: `→ keep: [[<page>#<heading>|<ID>]] (fact)`. This is an exception to leaving marks off until close. Close leaves facts already written alone.
   - Say it in your own words. Never copy document text into the vault.
   - Claude's general knowledge is never a source.
   - Two sources that disagree become one unknown naming both, with an owner handle and an ask-by date, per `MODES.md`.
6. Finish with a short Dump & Diverge segment: ask "What do these documents not say?" and capture the answers. Add `dump` to the record's `modes`.
7. Run `git status` and confirm nothing under `.inbox/` is staged. Tell the user: "Run `/planner:close` to finish the session and open the PR."
