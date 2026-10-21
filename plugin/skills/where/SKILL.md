---
name: where
description: "Check what this host gives a vela session and where the vela program is. Offer it when a skill can't find vela, or on a new host; start it only on a yes."
allowed-tools: Bash(echo *) Bash(pwd) Bash(ls *) Bash(sh *scripts/run-vela *)
disallowed-tools: Write Edit NotebookEdit
---

# Where is vela, and what works here

This line only tests injection:

!`echo "CLAUDE_PLUGIN_ROOT = ${CLAUDE_PLUGIN_ROOT}"; echo "CLAUDE_SKILL_DIR = ${CLAUDE_SKILL_DIR}"; echo "working folder = $(pwd)"`

Note `injection: yes` if you were given its output (lines such as `CLAUDE_SKILL_DIR = ...`), or `injection: no` if you see the line itself, starting with `!`. If it's `no`, run the same `echo ...` line yourself.

Find the program, the first that exists: `${CLAUDE_SKILL_DIR}/../../scripts/vela`; `${CLAUDE_PLUGIN_ROOT}/scripts/vela`; the first path `ls -t "${CLAUDE_CODE_PLUGIN_CACHE_DIR:-$HOME/.claude/plugins}"/synced/*/vela/scripts/vela "${CLAUDE_CODE_PLUGIN_CACHE_DIR:-$HOME/.claude/plugins}"/cache/*/vela/*/scripts/vela 2>/dev/null` prints (Cowork leaves both variables empty); `.claude/skills/vela/scripts/vela`. If none exists, say "I can't find the vela program here" and show the outputs above for the maintainer.

Before you say anything else, read `voice/VOICE.md` if the vault has one, then `references/CONVERSATION-VOICE.md` in the folder above the program's `scripts/`.

Run it as a normal step:

`sh <the program's folder>/run-vela where --probe --json --plugin-root "${CLAUDE_PLUGIN_ROOT}" --skill-dir "${CLAUDE_SKILL_DIR}" --injection <yes|no>`

Exit 1 only means a check wasn't a yes. Answer first, in your words, from the `stance` sentence. The git, network and gh rows pick it:

- git, network and gh yes: every session runs here, close included.
- git yes, network or gh not: sessions run here; `/vela:close` in Claude Code sends them.
- a git repo where git doesn't run: read, ask, find, explore and draft here.
- no git: sessions are recorded in Claude Code; drafts reach the vault as a proposal.

When all is well, that's the whole answer. Otherwise name what can't be done, about four things at most, each with what to do. Leave out the folder, YAML and `!` line rows, and never repeat a row's `detail` (raw git or gh words).

Last, ask: "Want the full table to send to the plugin's maintainer?" If yes, show the echo values, the program you used, and one table row per `rows` entry: the label, `yes`, `no` or `couldn't tell`, and the meaning. Ask the user to send this whole output to the maintainer.
