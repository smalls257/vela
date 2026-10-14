---
id: 2026-10-09-sandbox-fill-pricing
type: session
title: "Grill: sandbox fill pricing"
date: 2026-10-09
modes: [grill]
status: closed
summary: "Grill probe of UNK-069: the product lead's report that the sandbox prices fills stays unconfirmed, and the open part narrows to whether the Coach service may use Quoteline's feed."
---

# 2026-10-09 Grill: sandbox fill pricing

## Agenda

- RUN-coach: GATE-3 confirmed no, status decided already; user chose to probe UNK-069 instead

## Captures

- [thought] (@sim-lead) "Sandbox prices the fills, from the Coach lead—they said it fills the orders." The product lead's recollection that the Brightwater sandbox sets the fill price of a paper order, which means a fill needs no Quoteline price. It repeats the earlier assumption ([[2026-10-09-coach-runtime-failures#^c04]]) and adds that the Coach lead said so. → keep: [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] (open) ^c01
- [thought] (@sim-lead) "Coach channel on the 9th, that's K48, but honestly I'm not seeing fills called out explicitly in that message, so it might be another thread the same day." The thread where the Coach lead said the sandbox fills orders is not identified, and [[sources#SRC-20|the Coach channel message]] is not confirmed to say it. Not a fact: no document is registered, and Claude cannot ask the Coach lead. The product lead asks them. → keep: [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] (open) ^c02
- [thought] (@sim-lead) "That kills question one, so it's just whether Coach as a separate service gets to use Quoteline's feed, which is honest-to-god ambiguous in the wording." The product lead reads the open part of [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] as only whether the Coach service, separate from TickerTalk, may use Quoteline's feed under a license worded for TickerTalk's "own apps". The product lead calls the wording ambiguous. → keep: [[11-unknowns-and-risks#UNK-069 Filling paper orders on Quoteline's delayed quotes|UNK-069]] (open) ^c03
- [thought] (claude) The license text is not in the vault ([[11-unknowns-and-risks#UNK-056 Full texts of the three partner documents|UNK-056]]), so the "own apps" reading rests on [[sources#SRC-04|the data engineer's summary]]. The owner stays @partnerships-manager, with the product lead asking, ask-by 2026-10-16. → park ^c04

## Changes

| ID | From | To | Source |
|---|---|---|---|
