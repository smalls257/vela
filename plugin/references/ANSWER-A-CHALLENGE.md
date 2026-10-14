# Answer a challenge

Read by START when the user names a challenge to answer, and by `grill` for the answer session.

The solution lead answers a challenge on the challenge's own branch, so the red E316 check and its answer land in the same PR.

1. Find the open challenge PR: `gh pr list --search "Challenge: <ID>" --state open --json number,headRefName,title`, then keep only the PRs whose title ends with exactly `Challenge: <ID>`, because the search also matches longer IDs such as `CON-0010` for `CON-001`. If the user gave a PR number, run `gh pr view <number> --json number,headRefName,title,state` and confirm its title starts with the date and `Challenge:` and its state is `OPEN`. If none is open, or more than one, stop and show what `gh` returned. If `gh` fails, show the error and stop: an answer never starts on a guessed branch.
2. Check out that `session/...` branch instead of `git switch main`: `git switch <headRefName>`, then `git pull --ff-only`. If either fails, show the error and stop.
3. Run steps 2 to 4 as usual. Step 4's check shows the E316 the challenge left; that is the work.
4. Open the record as step 5 says, with two changes. Do not run `git switch -c`: the record goes on the branch you are on. The id is `<date>-answer-<id-lowercased>`, for example `2026-11-24-answer-con-001`, with `-2` and so on if that file exists. Write `modes: [answer]` and the title `Answer: <ID>`. Commit it with the message `Open session <id>`.

In the answer session, a Grill works on that branch and adds `grill` to `modes`. It resolves `UNK-nnn` with the senior, or decides the item again. Or the lead sets the item back, a contract to `assumption` or an epic to `reopened`, with a `## Changes` row such as `| CON-nnn | decided | assumption | [[<id>#^cNN]] |`. `/vela:close` then pushes to the same branch and comments on the challenge PR.
