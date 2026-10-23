# Reader copy

Read by close when `vela role` says `reader`. Run close as written, but skip the pull request step under "The pull request, and what you tell the lead": say the "nothing leaves your machine" line instead of running `vela close pr`.

- Say once: "This is a read-only copy, so I'll save your notes here and stop. Nothing leaves your machine. To send your changes to the owner, run /vela:propose."
- An item this session decided or overrode keeps `decided` and gets `- **Pending approval:** @<handle>, <today>` beside it (`vela conventions "Pending approval"`): every decision here is a reader's.
- Skip the harvest: it reads the owner's merged pull requests.
- Never write a handoff manifest: handoff is the owner's. Never say a PR exists.
