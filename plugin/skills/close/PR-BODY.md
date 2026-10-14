# The pull request body

Read by close in section 8, when it writes the body.

The pull request is the reviewer's record. Fill the headings of the vault's PR template. Leave out a list that has nothing to say, except **Overrides**, **Questions** and **Check**, which are always there ("none" when empty). **What changed** is always there.

- **What changed.** The promoted items, each with its new state. Then these lists:
  - **Prose drafted:** each prose paragraph drafted in section 4, page by page, and each merged paragraph rewritten whole, with the page and a pointer to `## Replaced prose` in the session record.
  - **House voice:** each "No examples for <type>: drafted without examples" line house-voice gave, one per type.
  - **Voice review:** each paragraph the reviewer flagged, what it said, and whether it was rewritten or kept because voicecheck named a changed token; each sentence dropped as redundant, quoted, with the reviewer named as the one who asked and the sentence that already says it; or "not run: <reason>". Then the voicescore `summary` line, or "voicescore: not run (<reason>)".
  - **Voice examples:** each example harvested or retired. Name a local example only as a count, never by its text. Add each PR harvest could not check, and why, and say when the PR limit hid older PRs.
  - **Decided wording not yet read back:** each `decided` item whose owner was not present in section 5.
  - **Promoted on a nod:** every item kept or promoted from a capture whose origin starts with `claude`, not only the deciding capture, with the capture quoted.
  - **Overrides:** every `**Override:**` bullet this session wrote, with its item, rules and reason, and every item decided on an owner's behalf that is not yet confirmed, with the owner @-mentioned so they can confirm or raise `/planner:challenge`. Or "none".
  - **Changed contracts:** each contract, and for each consumer, who was asked: present, async, in this PR, or "not consulted: <reason>".
  - **Overdue open questions:** each `W705` line from section 6, with its owner @-mentioned.
  - **Questions:** the coverage line from section 6, each ledger row this session wrote with its state, each W806 from the shape gate, each item decided with a question open (W807), each subject typed with the copies it now owes, each left untyped with its unknown, and each W809 and W804 from section 6 with what the user chose. Never write that the questions are complete.
  - **Reviews:** each checkpoint's `**Coverage:**` line from `## Reviews`, word for word, with its dropped findings and their reasons. An area that did not run is listed with its reason, never left out.
  - **Catalog proposals:** each entry the user approved, and each entry `--stats` names as one to prune or tighten.
  - **May still say the old value:** for each `decided` or `fact` value this session changed, run `grep -rn -F "<old wording>" --include='*.md' . | grep -v '^./sessions/'` and list every hit.
  - **Check:** the first line of the check output, and any error left in place.
  - **Stage:** run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner ladder` and copy each line whose `pages reach` is later than its `stage`, word for word. This is a line in the report, never a question: the lead types `stage` on the app page when they choose, in this session or a later one.
- **Minutes.** Work it out from the session's commits: `git log --format=%ct <main>..HEAD` gives the first and last commit times. Write "about <n> minutes (from the commit log)", and if there is only one commit, write "not recorded". Never ask.
- **Structural fixes** and **Prose edits.** Write "Filled in by the reviewer."
