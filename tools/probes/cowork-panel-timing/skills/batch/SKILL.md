---
name: batch
description: Timing probe arm B. Use only when the user runs /vela-probe-timing:batch. Files each message and publishes the panel in the same tool batch.
---

Do exactly this for every message the user sends until they say stop. Never add a step, never explain, never write HTML yourself, and publish the file exactly as it was written.

For each message: in ONE message, make two tool calls in this order. First one Bash call, `python3 "${CLAUDE_PLUGIN_ROOT}/probe.py" write --arm B; python3 "${CLAUDE_PLUGIN_ROOT}/probe.py" render`. Second, in the same message after it, publish `./.vela-probe/panel.html` to the artifact titled "Probe panel" (the first turn creates it; every later turn publishes to the same one). Then reply with exactly "Noted N." where N is the number the Bash call printed first.
