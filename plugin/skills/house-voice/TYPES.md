# Page types and voice types

Read by house-voice only when `vela voice examples --page <page>` can't resolve a page: it says the page's type isn't listed, or the page is new and has no file yet. The same table is `PAGE_VOICE` in `plugin/lib/vela/voiceplan.py`, which the command reads; a test keeps the two equal, so a change goes in both.

A page's key is its `id` if the table lists it, and its `type` otherwise. Find the key, take its voice type, and run `vela voice examples --type how-it-works --json` with that voice type.

## Page types and voice types

| Key | Voice type |
|---|---|
| `goals` | diagnosis |
| `solution-strategy` | decision |
| `capability-delta` | decision |
| `context-and-scope` | how-it-works |
| `constraints` | structured |
| `glossary` | structured |
| `initiative-section` | how-it-works |
| `index` | structured |
| `sources` | structured |
| `session` | structured |
| `app-building-blocks` | how-it-works |
| `app-runtime` | how-it-works |
| `flow` | how-it-works |
| `concern` | how-it-works |
| `decision` | decision |
| `epic` | how-it-works |
| `capability` | how-it-works |
| `entity` | structured |
| `slice` | how-it-works |

`structured` means the page holds no voiced prose. Its content is tables, lists and fact bullets.

A page type the table doesn't list has no voice type yet. Don't guess one: draft from the rules alone, say "No examples for <type>: drafted without examples" in the PR body, and name the missing row there so it gets added.
