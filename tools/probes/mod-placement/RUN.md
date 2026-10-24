# Placement probe: your rows (desktop Code tab and Cowork)

This probe answers where a side panel appears. The terminal rows were already run.
It takes about ten minutes.

## Desktop app, Code tab

1. In the desktop app, open Settings, Plugins, and add a marketplace from the folder `tools/probes` in this repository.
2. Install `vela-probe-placement`. Start a new Code session in any folder.
3. Type `/probe-pane` and press Enter. A panel titled "Probe (asked)" should open.
4. Look at it and note: does it sit beside the conversation, or above the message box? Does it show a small blue-gray rectangle that says "probe svg"? Does the text under "Probe pane" look like a drawn diagram, or like plain lines starting with "sequenceDiagram"?
5. Press the "Press me" button. Note whether a message "probe button pressed" appears in the chat. (This button exists only for this test. The shipped panels have none.)
6. Type `/probe-report` and press Enter. Copy the whole text it prints.

## Cowork

1. In a terminal, run: `cd tools/probes/mod-placement && zip -r /tmp/vela-probes/placement.zip . -x '.claude-plugin/types/*'`
2. In Cowork, open Customize, Plugins, and upload `/tmp/vela-probes/placement.zip`.
3. Note whether the upload is accepted or refused (copy the message if refused). If it is accepted, start a task and note whether anything draws beside the chat.

## What to send back

Paste the `/probe-report` text and your notes for each numbered question into the "Proof results" table of the plan, or just tell me and I will fill it in.
