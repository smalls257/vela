# Voice review

Read by close in section 4, after `vela close stage --draft`. A fresh reader checks the drafts, because the drafter can't judge its own voice.

1. List every prose paragraph this session touched (`done` and `paragraphs` in `vela close drafts --json`): for each, a number, the page, its voice type from house-voice's table, and its text. Leave out the bullets, table rows and headings. Give the reviewer the path `${CLAUDE_PLUGIN_ROOT}/references/lint-words.txt`; don't copy its words into the list or into your own drafting.
2. Dispatch the `vela:voice-reviewer` subagent with the Agent tool, and give it the list. If the Agent tool lists no `vela:voice-reviewer`, dispatch a general-purpose subagent, and give it everything in `${CLAUDE_PLUGIN_ROOT}/agents/voice-reviewer.md` after the frontmatter, then the list, then this: you must not change any file, and you must report any file you changed. Never review the drafts yourself in this conversation.
3. If no subagent could run, it failed, it returned anything but its table, or it changed a file, the review didn't run: stop and show the lead any file it changed, keep the reason for the pull request, and go on to the harvest. If it flagged nothing, go on to the harvest.
4. Run `vela voice settle --checkpoint <each page you'll rewrite>`. Then rewrite each paragraph it flagged once, from what it says differs. Drop only a sentence it named as redundant, and keep that sentence's exact text. Don't send the rewrite back for review; a paragraph it didn't flag stays as drafted.
5. Run `vela voice settle --rewrites <the pages> --score --for-lead`, adding `--redundant <page> "<the sentence exactly as it stood>"` for each sentence you dropped. Say in a line what it kept and what it put back.
