# Reader copy: no git, no PR

Read by close when `vela role` says `reader`.

Run `vela role` first. If it says `reader` (a published copy: `.vela/workspace.json`, no `.git`), say once, plainly: "This is a read copy, so close writes your session record and stops. Nothing is committed, pushed or sent." Then run the sections below with these changes, and no other:

- **Section 1:** find the open record with `grep -l '^status: open' sessions/*.md`. There are no branches; run no `git` or `gh` command.
- **Section 3:** an item the session decided or overrode keeps `decided` and gets `- **Pending approval:** @<handle>, <today>` beside it (`vela conventions "Pending approval"`). Use the handle START.md asked for. An owner's decision never gets the marker; here every decision is a reader's.
- **Section 4:** the changed pages are the ones the session's `## Changes` table and captures name, not `git diff`. Skip the examples harvest (it needs `gh` and `git`). Skip the `git restore` and checkpoint-commit lines of the voice review: write the rewrite to the page only after `vela voicecheck` passes, and keep the earlier draft in a copy beside it until then.
- **Section 6:** run only the render and the check. Skip the fetch and the merge of `main`.
- **Section 7:** write `summary:` and set `status: closed`, render and check; stage nothing. Never write a handoff manifest: handoff is the owner's.
- **Section 9:** runs as written; it needs neither git nor `gh`.
- **Section 8:** skip it. Say: "Nothing was committed, pushed or sent. Your changes are in this folder; to send them to the owner as a proposal, run `/vela:propose`." Never say a PR exists.

Write the session record as usual: it is the one record of what you did.
