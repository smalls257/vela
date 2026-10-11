---
id: concern-observability
type: concern
title: Observability
arc42: "§8"
owner: "@solution-lead"
authored: authored
---

# Observability

What is measured, so a failure shows up without a debugger or a release.

## Strategy

Nobody has examined observability for Coach yet, and [[sources#SRC-19|the mobile lead says]] TickerTalk's existing practice holds. How the team would see that Coach, Brightwater's sandbox or Quoteline is failing is not recorded.

The Coach lead says, in [[sources#SRC-16|the answers the product lead gathered by 9 October]], that Coach ships with request dashboards and alerts on errors and Brightwater sandbox failures, owned by the Coach team. That is a plan, so it is an assumption.

## Per app

| App | State | Why |
|---|---|---|
| [[coach-building-blocks\|Coach]] | unchanged | the product lead says the existing observability practice holds ([[2026-10-09-concern-cells#^c07]])
| [[tickertalk-building-blocks\|TickerTalk]] | unchanged | the mobile lead says TickerTalk's existing observability practice holds ([[sources#SRC-19|the later answers]]) |
