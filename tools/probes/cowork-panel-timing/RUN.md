# Cowork timing probe: your run

This measures whether showing a live panel in Cowork slows the conversation. Three runs of ten messages, about twenty minutes in all.

1. Zip this folder: `cd tools/probes/cowork-panel-timing && zip -r /tmp/vela-probes/timing.zip . -x 'RUN.md'`. In Cowork open Customize, Plugins, and upload that zip.
2. Make an empty folder and use it as the working folder for all three runs.
3. Run A (no panel). Start a task and say `/vela-probe-timing:plain`. Then send `next` ten times, sending each one as soon as the previous reply lands.
4. Run B (panel in the same step as the write). New task, say `/vela-probe-timing:batch`, then `next` ten times. After each reply, glance at the panel: does its big number match the number in the reply? Does it stay open beside the chat without you reopening it?
5. Run C (panel after the answer). New task, say `/vela-probe-timing:after`, then `next` ten times. Same two questions.
6. In a terminal, run `python3 tools/probes/cowork-panel-timing/report.py <the working folder>` (or ask Claude to run it). It prints the median and slowest-tenth turn time for each run and the gap of B and C to A.
7. Send back those lines and your answers to the two questions for B and C. If the report says no hook stamps were found, time ten replies per run with a stopwatch instead and send the medians.

How the answer is used:
- If B is 1.0 second or more slower than A, the Cowork session panel becomes "show me where we are" on request.
- If B's number lags the reply but C's does not, the session panel uses C's order too.
- If C is 1.0 second or more slower than A, the explorer panel becomes on request only.
