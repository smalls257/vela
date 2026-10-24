---
name: after
description: Timing probe arm C. Use only when the user runs /vela-probe-timing:after. Files each message, answers, and publishes the panel after the answer.
---

Do exactly this for every message the user sends until they say stop. Never add a step, never explain, never write HTML yourself, and publish the file exactly as it was written.

For each message: run one Bash call, `python3 "${CLAUDE_PLUGIN_ROOT}/probe.py" write --arm C; python3 "${CLAUDE_PLUGIN_ROOT}/probe.py" render`. Then send one message whose text is exactly "Noted N." (N is the number the Bash call printed first) followed, in that same message, by the publish of `./.vela-probe/panel.html` to the artifact titled "Probe panel" (the first turn creates it; every later turn publishes to the same one).
