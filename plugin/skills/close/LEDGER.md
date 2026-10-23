# Ledger rows and catalog gaps

Read by close when `marks plan` leaves a ledger row's state to you, or the lead says the catalog missed a question. `marks plan` drafts the question-ledger rows (`vela apply --schema ledger` lists the fields), and `vela apply` writes them and refuses a row written wrong. Two things stay yours.

### A row the lead's words leave unclear

Ask it as one of the leftovers under "Find the session and mark the captures": "You said the call recorder probably doesn't keep audio. I'd note that as something we're resting on, and check it with the vendor. Right?" Then fill the row from the answer:

- answered: `item` is the item the answer went into, and `source` is a document's source row, or a first-hand row you add with `vela add source --location "first-hand: <handle>"` when the lead's word is the only source. Never invent a source; with none, the row is `assumed`.
- assumed: `load_bearing` says whether the plan rests on it, and `signpost` points at what the lead said would show it wrong. Ask only when it's high severity and you can't tell.
- unknown: it waits on an open question (`vela add unknown`).

A grill's "decided with ... open" note records a decision, not an answer: write no row for those copies.

### A question the catalog missed

Only when the lead said so in so many words; never ask whether a gap turned up late. Draft one YAML block under `## Catalog proposals` in the session's notes:

```yaml
- id: Q-<AREA>-nn  # the next free number in that area
  area: <AREA>
  scope: <initiative, app, contract, capability, party or stored-value>
  trigger: <exists, or a condition>
  question: <the question, worded for any vault>
  why: <found late in session <id>: what was missed, and what that cost>
  severity: <high or normal>
```

Never edit `${CLAUDE_PLUGIN_ROOT}/catalog/questions.yaml`: the catalog is the toolkit's, and pruning is the maintainer's call.
