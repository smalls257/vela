---
name: plain
description: Timing probe arm A. Use only when the user runs /vela-probe-timing:plain. Files each message with one Bash call and replies in one sentence, with no panel.
---

Do exactly this for every message the user sends until they say stop. Never add a step, never explain, never write HTML yourself, and publish the file exactly as it was written.

For each message: run one Bash call, `python3 "${CLAUDE_PLUGIN_ROOT}/probe.py" write --arm A`. Then reply with exactly "Noted N." where N is the number it printed.
