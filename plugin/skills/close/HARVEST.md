# Harvest the owner's edits

Read by close in section 4, after the voice review. Harvest does not depend on the review.

Only the vault's owner harvests, and only their own edits. The owner is the `author` of the `source: owner` examples in `voice/examples/` and `voice/local/`. If there are none, say "No owner examples yet, so nothing to harvest. `/vela:voice-seed` adds them." and go on to section 5, Read back decided wording. Harvest does not depend on the voice review: run it even when the review did not run.

Each command runs in its own shell call, and no shell variable survives from one call to the next. So each paragraph's text is kept in a file with a fixed path every later step names: `.vela/harvest/<pr>-<n>.txt`, where `<pr>` is the PR number and `<n>` is the paragraph's order in this harvest, from 1. It sits in `.vela/`, which is gitignored, so it never shows in `git status` and is never staged. When harvest ends, by any route, run `rm -rf .vela/harvest`.

Every `gh` or `git` call below can fail. When one does, say which call failed and what it left unchecked. Never read a failure as "no edits found". Say "no edits found" only when every merged PR was checked.

1. Get the user's handle with `gh api user -q .login`. If `gh` fails, say "gh could not read your handle, so nothing was harvested." and go on to section 5, Read back decided wording. If the handle is not the owner's handle without the `@`, say "Harvest is owner-only." and go on to section 5, Read back decided wording.
2. List the user's merged session PRs: `gh pr list --state merged --search "head:session/" --author @me --json number,headRefName --limit 10`. If `gh` fails, say "gh could not list merged PRs, so nothing was harvested." and go on to section 5, Read back decided wording. If it returns 10 PRs, say "10 merged PRs came back, so older PRs were not checked."
3. Take one PR at a time, because `FETCH_HEAD` holds only the last fetch. Run `gh pr view <number> --json commits`, which lists each commit's `oid`, `messageHeadline` and `messageBody`, and `git fetch origin pull/<number>/head`. If `gh` fails, say "gh could not read the commits of PR <number>, so its edits were not checked." and go to the next PR. If the fetch fails, say "git could not fetch PR <number>, so it was not checked." and go to the next PR. Then:
   - Keep the commits whose `messageHeadline` starts `draft: `, both `draft: prose for` and `draft: voice rewrite for`. Skip the PR if there are none.
   - For each, list its pages with `git diff-tree --no-commit-id --name-only -r <oid>`. For each page, the baseline is the last draft commit in the PR's list that touched it.
4. For each page of the PR:
   - Run `git log --format=%H <baseline>..FETCH_HEAD -- <page>` and keep the commits that are in the PR's list. Drop each one whose `messageHeadline` starts with `draft: `, `Checkpoint ` or `Close session `, and each one whose `messageBody` carries a `Co-Authored-By: Claude` trailer or a `Claude-Session:` trailer. Those are the skill's own commits. Drop a merge commit too. If none remain, the owner did not edit the page, so skip it.
   - For each remaining commit, run `git diff -U0 <oid>^ <oid> -- <page>`. Never compare the baseline with the tip, because the tip also holds section 3's content. The added lines are the owner's edit. Find the paragraph of `git show FETCH_HEAD:<page>` that holds them. If a later commit removed them, skip. The draft paragraph is the one in its place in `git show <oid>^:<page>`. Read the merged text from `FETCH_HEAD`, never from `origin/main`.
   - Extract the merged paragraph into its file, and hash it, in one call:

     ```
     mkdir -p .vela/harvest
     git show FETCH_HEAD:<page> | sed -n '<first>,<last>p' > .vela/harvest/<pr>-<n>.txt
     shasum < .vela/harvest/<pr>-<n>.txt | cut -c1-12
     ```

   - Skip a paragraph that is already saved or declined, and run `rm -f .vela/harvest/<pr>-<n>.txt`. It is saved when an example in either folder has the same `page`, a `harvested_from` equal to the baseline's full hash, and a body equal to the merged paragraph. It is declined when `grep -rh '^Harvest declined: ' sessions/` has its line: `Harvest declined: PR <number> <page> <hash>`.
5. Offer each remaining paragraph, one at a time. Show the draft paragraph, the file `.vela/harvest/<pr>-<n>.txt` and the voice type from house-voice's table, so the text is never retyped. Harvest offers and never saves by itself. Ask "Did you write this change?" The owner's answer is the check that the edit is theirs. If the answer is unclear, ask once more. If it is no, or still unclear, record a decline, run `rm -f .vela/harvest/<pr>-<n>.txt`, and do not ask the save question. Otherwise ask "Save the merged paragraph as a <type> example?" Save it only on an explicit yes. On any other answer, record a decline and run `rm -f .vela/harvest/<pr>-<n>.txt`. To record a decline, insert one bare line `Harvest declined: PR <number> <page> <hash>` directly under `## Captures` in the session record. It is never a bullet.
6. Ask where it goes, and say plainly that a committed example is pushed in this PR, where everyone with access to the repository can read it:
   - committed: `voice/examples/<type>/`. Ask "May this text be committed to the vault?" and wait for an explicit yes.
   - local only: `voice/local/<type>/`. It stays on this machine and no step below stages it.

   If the owner's employer owns the text, or the owner is not sure, recommend local only. If the answer is not an explicit choice, do not save, and run `rm -f .vela/harvest/<pr>-<n>.txt`.
7. Plan the room before you save, and change no example yet. A type keeps at most 5 active examples. Count both folders together, with the new one. If that makes 6, plan to retire one: the oldest `public-seed` example first, then the oldest `owner-edit`, then the oldest `owner`, by `added` and then file name. A local example never retires a committed seed, and in a local-only save only local examples may retire. If the cap blocks a local-only save, store nothing, run `rm -f .vela/harvest/<pr>-<n>.txt`, and say "The cap blocks a local save: <type> holds 5 active examples and none in voice/local/ may retire." Show the owner each planned retirement and ask. If they refuse, store nothing for that type, and run `rm -f .vela/harvest/<pr>-<n>.txt`.
8. Save the merged paragraph word for word as `<folder>/<type>/VX-<type>-NNN.md`, NNN one higher than the highest in that type in both folders, retired files included. First write the frontmatter with the Write tool, quoting every free value, ending with the closing `---` and one blank line:

   ```
   ---
   id: VX-<type>-NNN
   voice_type: <type>
   source: owner-edit
   author: "@<handle>"
   page: '<page path>'
   harvested_from: '<full hash of the baseline draft commit>'
   state: active
   added: <today>
   ---

   ```

   Then append the paragraph's file and compare it with the stored body, with a tool, in one call. The block removes the file whatever `cmp` finds:

   ```
   cat .vela/harvest/<pr>-<n>.txt >> <file>
   awk 'body { if (first && $0 == "") { first = 0; next } first = 0; print; next } $0 == "---" && ++n == 2 { body = 1; first = 1 }' <file> | cmp - .vela/harvest/<pr>-<n>.txt; code=$?; rm -f .vela/harvest/<pr>-<n>.txt; (exit $code)
   ```

   If `cmp` reports a difference, stop, tell the owner, and do not repair the file. Then re-read the frontmatter and confirm it parses as YAML and that `page` and `harvested_from` hold the text you gave. Only now apply the retirements you planned in step 7, changing only each `state:` line. If the save made a folder's active `owner` and `owner-edit` examples of the type 2 or more, retire that folder's active `public-seed` examples of the type the same way, as `/vela:voice-seed` does. A local save retires only local seeds. Retire by editing `state:` and never delete an example.
