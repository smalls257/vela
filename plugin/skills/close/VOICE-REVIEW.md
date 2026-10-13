# Voice review

Read by close in section 4, after the prose is drafted and committed. Skip it if the session drafted no paragraph.

A fresh reader checks the drafts, because the drafter cannot judge its own voice. Skip this part if the session drafted no paragraph, and go on to the part "Harvest the owner's edits".

**Voicescore, optional.** `planner voicescore` places each paragraph against the owner's own range with a style embedding, a second reading of a different kind from the reviewer's. It is information, not a gate. It runs only when it is installed and the owner has at least 5 active `owner` and `owner-edit` examples. Run it after step 1 and before step 2:

- Write the paragraphs of step 1's list to `.planner/voicescore-input.md`, in list order, one blank line between them, so ¶n is entry n. It sits in `.planner/` is gitignored, so nothing in it is ever staged. It is not under `.git/`, because Claude Code will not write there without asking.
- Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner voicescore .planner/voicescore-input.md --json`, then `rm -f .planner/voicescore-input.md`.
- It did not run when it printed `"ran": false` (keep its `reason`), when `"reliable"` is false (the reason is "fewer than 5 owner examples"), when its paragraph count differs from the list (the reason is "its paragraphs did not match the list"), or when the command failed in any other way (the reason is what it printed). Then the PR body says "voicescore: not run (<reason>)" and the reviewer gets no labels.
- Otherwise add each paragraph's `label` to its entry, marked "voicescore hint", and keep the `summary` line for the PR body, such as "voicescore: 3 of 4 paragraphs inside your range; ¶2 outside (p96)".
- Never block, rewrite or skip a paragraph because of its voicescore. Only the reviewer's flags lead to a rewrite.

1. List only the prose paragraphs this section drafted, from the `draft: prose for <id>` commit. The word list the reviewer lints with is `${CLAUDE_PLUGIN_ROOT}/references/lint-words.txt`; give it that path, and do not copy the words into the list or into your own drafting. Leave out the bullets, table rows and headings section 3 wrote, even though the commit holds them. For each paragraph give a number, the page path, its voice type from house-voice's table, and the paragraph's text. Run `git status --porcelain` and keep the output.
2. Dispatch the `planner:voice-reviewer` subagent with the Agent tool, and give it the list. If the Agent tool lists no `planner:voice-reviewer`, dispatch a general-purpose subagent instead, and give it everything in `${CLAUDE_PLUGIN_ROOT}/agents/voice-reviewer.md` after the frontmatter as its instructions, then the list, then this: you must not change any file, and you must report any file you changed. Never review the drafts yourself in this conversation. If no subagent can be dispatched, write "**Voice review:** not run: <the reason>" in the PR body and go on to the part "Harvest the owner's edits". The harvest does not depend on the review.
3. Run `git status --porcelain` again. If the output differs from step 1 of this part, the reviewer changed a file: stop and show the user. If the reviewer errored, or returned anything but the table, treat the review as not run, write "**Voice review:** not run: <the reason>" in the PR body, and go on to the part "Harvest the owner's edits". If it flagged no paragraph, skip steps 4 and 5 of this part: there is nothing to rewrite and no commit, so go on to the part "Harvest the owner's edits".
4. Rewrite each paragraph the reviewer flags once, in the working tree, from what it says differs. The reviewer may also name a sentence as redundant, because its claim stands elsewhere in the paragraph. Drop only a sentence it named, in the rewrite of that paragraph, and keep its exact text for step 5. Do not send the rewrite back for review. A paragraph it did not flag stays as drafted. Note the pages you rewrote. Touch no other file. Before you rewrite a page, check it holds no uncommitted edit from sections 2 and 3, because a restore would discard that edit. For each `<page>`:

   ```
   git diff --quiet HEAD -- <page> || { git add -- <page> && git commit -qm "Checkpoint <id>" -- <page>; }
   ```

   This commits that page alone, with the message `Checkpoint <id>`, when it differs from HEAD. Then rewrite it, so `git restore -- <page>` returns the page to a state that already holds those edits.
5. Check only the pages you rewrote, one at a time, because the working tree also holds the work of sections 2 and 3 that is not committed. For each rewritten `<page>`:

   ```
   tmp=$(mktemp)
   git show HEAD:<page> > "$tmp"
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner voicecheck "$tmp" <page>; code=$?; rm -f "$tmp"; (exit $code)
   ```

   voicecheck fails if a rewrite lost, added or moved a wikilink, code span, date, ID, number (with its units or currency), table cell, version, frontmatter line or negation.

   For a page where the rewrite dropped sentences the reviewer named as redundant, add `--redundant "<the sentence exactly as it stood>"` for each: `planner voicecheck "$tmp" <page> --redundant "<sentence>"`. voicecheck then lets that sentence's own negation go, still fails if the sentence carried an ID, number, date or link that is now gone, and exits 2 if the sentence was not in the draft or is still in the rewrite. The PR body lists every such sentence under **Voice review**.
   - Exit 0: keep the rewrite.
   - Exit 1: run `git restore -- <page>`. That discards every rewrite on that page and keeps its earlier draft whole. Run it for no other file.
   - Exit 2: show the error, then run `git restore -- <page>` so the unchecked rewrite stays out of the work that section 7 stages. Never commit a rewrite voicecheck could not check.

   Then commit the rewrites that passed with the message `draft: voice rewrite for <id>`, staging each page by exact path.
