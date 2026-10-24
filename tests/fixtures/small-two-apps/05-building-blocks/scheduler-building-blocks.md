---
id: APP-scheduler
type: app-building-blocks
title: Scheduler
state: assumption
change: new
stage: target
owner: "@mo"
authored: authored
sources: [SRC-01]
---

# Scheduler

The Scheduler decides when each job is due and tells the Jobs API.

## Containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Clock | Works out which jobs are due now | [[#CON-001 Job due\|Job due]] | claude | assumption |

## Contracts this app provides

### CON-001 Job due

- **Crosses the boundary:** a job that is due goes out; an acknowledgment comes back.
- **Consumers:** [[jobs-api-building-blocks|Jobs API]]
- **Change policy:** versioned.
- **Change:** new
- **State:** assumption

| Case | When | Status | Answer | Emits | Sets |
|---|---|---|---|---|---|
| accepted | | 200 | the Jobs API takes the job | | |
| bus_unavailable | | error | the job waits and is sent again | | |
