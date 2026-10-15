---
name: where
description: Check what this host gives a vela session and where the vela program is. Use when a skill can't find vela, or on a new host, then send the table to the plugin's maintainer.
disable-model-invocation: true
allowed-tools: Bash(echo *) Bash(pwd) Bash(ls *) Bash(python3 *scripts/vela *)
disallowed-tools: Write Edit NotebookEdit
---

# Where is vela, and what works here

This line only tests whether the host runs a skill's `!` lines:

!`echo "CLAUDE_PLUGIN_ROOT = ${CLAUDE_PLUGIN_ROOT}"; echo "CLAUDE_SKILL_DIR = ${CLAUDE_SKILL_DIR}"; echo "working folder = $(pwd)"`

First, say `injection: yes` on its own line if you were given its output (lines such as `CLAUDE_SKILL_DIR = ...`), or `injection: no` if you see the line itself, starting with an exclamation mark and a backtick. If it's `no`, run the same `echo ...` line yourself and show its output. Never skip this.

Then say `skill base directory = <path>` if the host told you where this skill loaded from ("Base directory for this skill"), or `skill base directory = not given`. Don't work it out.

Find the program, the first that exists: `${CLAUDE_SKILL_DIR}/../../scripts/vela`; `${CLAUDE_PLUGIN_ROOT}/scripts/vela`; `<skill base directory>/../../scripts/vela`; the first path `ls -t "${CLAUDE_CODE_PLUGIN_CACHE_DIR:-$HOME/.claude/plugins}"/synced/*/vela/scripts/vela "${CLAUDE_CODE_PLUGIN_CACHE_DIR:-$HOME/.claude/plugins}"/cache/*/vela/*/scripts/vela 2>/dev/null` prints (Cowork leaves both variables empty and keeps the plugin under `synced/`); `.claude/skills/vela/scripts/vela`. Say which you used. If none exists, say so and ask the user to send everything above to the maintainer.

Run it as a normal step:

`python3 <program> where --probe --json --plugin-root "${CLAUDE_PLUGIN_ROOT}" --skill-dir "${CLAUDE_SKILL_DIR}" --injection <yes|no>`

Exit 1 only means a check wasn't a yes. Show a table, one row per `rows` entry: the label, `yes`, `no` or `couldn't tell`, and the meaning with its detail.

Then say the `stance` sentence as printed. The probe picks it from the git, network and gh rows:

- git, network and gh yes: every session runs here, close included.
- git yes, network or gh not: sessions run here; `/vela:close` in Claude Code sends them.
- a git repo where git doesn't run: read, ask, find, explore and draft here.
- no git: sessions are recorded in Claude Code; drafts reach the vault as a proposal.

Last, ask the user to try what the probe can't: in a fresh chat, ask Claude to capture an idea without typing `/vela:dump`. If dump starts by itself, this host ignores skill frontmatter flags. Then ask the user to send this whole output to the plugin's maintainer.
