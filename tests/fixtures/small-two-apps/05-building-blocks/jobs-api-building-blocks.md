---
id: APP-jobs-api
type: app-building-blocks
title: Jobs API
state: assumption
change: new
stage: target
owner: "@mo"
authored: authored
sources: [SRC-01]
---

# Jobs API

The Jobs API takes the jobs that are due and runs them, and tells other systems on the platform event bus.

## Containers

| Container | Job | Contracts served or used | Proposed by | State |
|---|---|---|---|---|
| Runner | Runs a job that is due | [[#CON-002 Event bus\|Event bus]] | claude | assumption |

## Contracts this app provides

None. Nothing else relies on the Jobs API in the first release.

## Contracts this app consumes

### CON-002 Event bus

The Jobs API publishes an event for each finished job.

- **Provider:** Platform event bus
- **Crosses the boundary:** the Jobs API sends one event for each finished job. Nothing comes back.
- **Consumers:** [[jobs-api-building-blocks|Jobs API]]
- **Owner:** @ravi
- **Change policy:** Not agreed with the platform team.
- **Change:** new
- **State:** assumption
