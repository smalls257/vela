---
title: Words and sources
kind: reference
lede: The words this site uses, where its outside claims come from, and what has no outside source at all.
---

## Words used here

- **Vault, or the plan.** The folder of Markdown pages for one initiative, kept in git.
- **Session.** One conversation with Claude that has one job, on its own branch.
- **Capture.** One numbered line in the session record, in the person's own words, with who said it.
- **Grill.** A session that asks one question at a time until a part of the plan is settled. The only one that marks anything decided.
- **Item.** Anything with a state: a goal, requirement, app, contract, flow or epic.
- **Library.** `sources.md`: every document and link the plan rests on, with its kind (`exists`, `intends`, `repo`).
- **Requirement.** One thing the business needs, in its own words, with acceptance criteria, naming no app.
- **Contract.** The agreed interface between two apps, with a table of every answer the provider can give.
- **Flow.** A journey across apps, step by step, naming each hand-over and its contract.
- **Slice, tracer.** A slice is one thin piece of product built end to end. The tracer is the first, through every app it touches.
- **Epic.** One team's chunk of work, with acceptance criteria a tester can see at a contract or flow boundary.
- **Handoff.** Giving an app to its team lead, with a record of what they accepted.
- **Challenge.** A team lead's recorded disagreement, kept as an open question for the solution lead.
- **Override.** A rule set aside on purpose, written on the item with who, when and why.
- **Check, gate.** `vela check` reads the plan against the format. A stricter run, such as `--gate epics`, is held before a stage is called done.

For the commands, see the [README](../../../README.md#the-vela-cli). For installing and running vela, see the [user guide][guide]. For the short version of this site, see [How Vela works][phil].

## Sources

Every outside claim has a number. They come from two places only: the owner's research notes (kept outside the repository) and works the repository itself cites. Where the notes record that a source couldn't be opened, that is stated.

1. Cowan, N. (2001). "The magical number 4 in short-term memory: A reconsideration of mental storage capacity." *Behavioral and Brain Sciences*. <https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/article/magical-number-4-in-shortterm-memory-a-reconsideration-of-mental-storage-capacity/44023F1147D4A1D44BDC0AD226838496>. Cited in [`CONVENTIONS.md`](../../../plugin/template/CONVENTIONS.md#pages) ("A page fits in a head"). Used for: people hold only a handful of things in mind at once.
2. Miller, G. A. (1956). "The magical number seven, plus or minus two." *Psychological Review*. <https://psychclassics.yorku.ca/Miller/>. Cited in the same place. Used for the "four to seven" range.
3. Klein, G. (2007). "Performing a Project Premortem." *Harvard Business Review* 85(9). Named in the research notes, which record the article was paywalled and not read. Used only to name the premortem technique, which is the dump skill's pre-mortem.
4. Hunt, A. and Thomas, D. (1999). *The Pragmatic Programmer*, "Tracer Bullets." <https://www.oreilly.com/library/view/the-pragmatic-programmer/9780135956977/f_0030.xhtml>. Cited by the repository's [tracer-bullets explainer][tracer-explainer]. The notes record that the page returned an access error, so they worked from search excerpts. Used for where the tracer-bullet idea comes from.
5. Cockburn, A. (2004). *Crystal Clear*, "Walking Skeleton." Cited in the research notes, which record that Cockburn's own page could not be reached. Used only for the attribution.
6. Shneiderman, B. (1996). "The Eyes Have It." <https://drum.lib.umd.edu/handle/1903/5784>. Quoted in the research notes as "Overview first, zoom and filter, then details-on-demand." Used for the shape of the dashboard and of list pages.
7. International Institute of Business Analysis. *A Guide to the Business Analysis Body of Knowledge (BABOK Guide)*, version 3, chapter 10. Named in the research notes, with no web address. Used only for the statement that interviews, workshops and brainstorming are standard elicitation techniques.
8. Nygard, M. (2011). "Documenting Architecture Decisions." Cognitect blog. <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>. Listed in the research notes. Used for the idea of short records of one decision and its alternatives.

## What has no outside source

These are vela's own design choices. We looked and found no source we could cite, so we don't claim one: the order of the rungs, requirements before boundary, a grill as the only way to decide, the voice (colleague across a desk, its target numbers, drafting from examples), the "about four things" limit on a reply as applied, the slice and release model as vela writes it, and the sealed-simulation method. The simulator's recall and precision are its own scoring design, described in [`tests/sim/README.md`][simreadme].
