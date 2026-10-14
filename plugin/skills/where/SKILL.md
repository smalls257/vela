---
name: where
description: Print where this session thinks the planner program is, and why. Use when a skill says it cannot find the planner program, then send the output to whoever maintains the plugin.
disable-model-invocation: true
allowed-tools: Bash(echo *) Bash(ls *) Bash(pwd) Bash(test *) Bash(python3 *scripts/planner *) Bash(git --version) Bash(gh --version) Bash(find *) Bash(curl -sI *)
disallowed-tools: Write Edit NotebookEdit
---

# Where is the planner

Run each of these and show the output unedited. They need no planner to be found, and say what the host expanded.

!`echo "CLAUDE_PLUGIN_ROOT = ${CLAUDE_PLUGIN_ROOT}"; echo "CLAUDE_SKILL_DIR = ${CLAUDE_SKILL_DIR}"; echo "working folder = $(pwd)"; for p in "${CLAUDE_SKILL_DIR}/../../scripts/planner" "${CLAUDE_PLUGIN_ROOT}/scripts/planner" ".claude/skills/planner/scripts/planner"; do if [ -f "$p" ]; then echo "found:   $p"; else echo "missing: $p"; fi; done; if [ -f .planner/workspace.json ]; then echo "workspace.json: $(grep planner_path .planner/workspace.json)"; else echo "workspace.json: none"; fi; echo "python3: $(python3 --version 2>&1)"`

Before anything else, say on its own line whether the host ran that line for you: `injection: yes` if you were given its output (lines such as `CLAUDE_SKILL_DIR = ...`), or `injection: no` if you see the line itself, starting with an exclamation mark and a backtick. If it is `no`, run the same `echo ...` line yourself as a normal command and show its output. The maintainer needs to know which happened, so never skip this line.

Then report what else this host gives a skill, one line each, shown unedited:

1. `skill base directory = <path>`: the folder the host told you this skill was loaded from (some hosts say it as "Base directory for this skill"), or `skill base directory = not given` if you weren't told one. Don't work it out; say only what the host said.
2. If you were given a base directory, run `ls "<it>/../../scripts"` and show it.
3. `git --version`, `gh --version`, and `curl -sI https://github.com | head -1`, each shown with its output or its error.
4. `find / -path '*scripts/planner' -type f 2>/dev/null | head -5`, so the maintainer sees where the host put the plugin's files, if anywhere.

If any line in all of this shows the planner program (`found:`, or a path from steps 2 or 4), run `python3 <that path> where --plugin-root "${CLAUDE_PLUGIN_ROOT}" --skill-dir "${CLAUDE_SKILL_DIR}"` and show it too. Use only what was shown; don't guess a path. Either way, end by asking the user to send this whole output to the plugin's maintainer.
