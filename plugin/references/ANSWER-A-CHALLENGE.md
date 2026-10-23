# Answer a challenge

Read by START when the user names a challenge to answer, and by `grill` for the answer session.

Run `vela session start --mode answer --answer <PR number or the challenged ID> --for-lead`. It finds the one open challenge PR, switches to its branch, brings `main` in, and opens the answer session there (its stub is committed, its notes stay on this machine), so the challenge and its answer land in the same PR. If it finds none or several, say so in one plain sentence and stop: an answer never starts on a guessed branch.

In the answer session, a grill works on that branch and adds `grill` to the session's modes. It settles the team lead's question with them, or decides the item again. Or the lead sets the item back (a contract to not decided yet, an epic to reopened), with a row under `## Changes` in the session's notes, such as `| CON-nnn | decided | assumption | [[<id>#^cNN]] |`. A page or the pull request cites the same capture as `[[<id>]] c07`, never as `#^c07`. The answer carries the lead's words only if they pick them at the read-back, and a team lead's words go in the reply only with their own yes to being quoted. `/vela:close` then pushes to the same branch and comments on the challenge PR, never opening a new one.
