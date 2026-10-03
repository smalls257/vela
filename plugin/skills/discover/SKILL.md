---
name: discover
description: Discover session for an initiative vault. Registers documents and code repositories in sources.md, reads the ranked ones, shows "here's what I think exists" for correction, then writes facts that each cite a SRC-nn. Use when nobody is sure what exists today.
argument-hint: "[area, app or question]"
disable-model-invocation: true
---

# Discover

Find out what exists before anyone designs anything. Every fact this session writes cites a source in `sources.md`.

1. Run the steps in `.claude/skills/planner/references/START.md` with mode `discover`. Read the Discover row of `.claude/skills/planner/references/MODES.md`.
2. List the files in `.inbox/` and the rows in `sources.md`. Add a row for each new document: `ID | Title | Owner | Date | Kind | Location`. `Kind` is `exists` for a document that describes what runs today, and `intends` for a plan, deck or roadmap. A local clone of a code repository is `Kind: repo`, with Location `<url>@<sha>` from `git -C <clone> remote get-url origin` and `git -C <clone> rev-parse HEAD`. A file that lives only in `.inbox/` has Location `local only`.
3. Show the register and ask the user to rank it and cut what is not worth reading. Read only the top-ranked sources.
4. Show "Here's what I think exists" as a numbered list, each line with its `SRC-nn`. Write nothing to a page yet. The user corrects the list.
5. After each correction round, write what was confirmed and commit a checkpoint:
   - A line from an `exists` or `repo` source is a `fact`, with `sources: [SRC-nn]` on the page or `- **Source:** SRC-nn` on a contract.
   - A line from an `intends` source is an `assumption`, however sure it sounds. "Ready in Q4" in a deck is a plan, not a fact.
   - A line the user knows first-hand is a `fact` only once it has its own row, with the user as owner.
   - Say it in your own words. Never copy document text into the vault.
   - Claude's general knowledge is never a source.
   - Two sources that disagree become one unknown naming both.
6. Finish with a short Dump & Diverge segment: ask "What do these documents not say?" and capture the answers. Add `dump` to the record's `modes`.
7. Run `git status` and confirm nothing under `.inbox/` is staged. Tell the user: "Run `/planner:close` to finish the session and open the PR."
