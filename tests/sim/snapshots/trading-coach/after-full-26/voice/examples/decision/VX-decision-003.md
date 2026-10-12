---
id: VX-decision-003
voice_type: decision
source: public-seed
author: "Dirkjan Ochtman"
work: "The Architecture of Open Source Applications, Volume 1"
chapter: "Chapter 12, Mercurial, section 12.6. Lessons Learned"
url: https://aosabook.org/en/v1/mercurial.html
licence: CC BY 3.0
licence_url: https://creativecommons.org/licenses/by/3.0/
changes: none, the passage is quoted word for word
state: active
added: 2026-10-03
---

An early choice was made to make it hard to modify changesets after committing. Because it's impossible to change a revision without modifying its identity hash, "recalling" changesets after having published them on the public Internet is a pain, and Mercurial makes it hard to do so. However, changing unpublished revisions should usually be fine, and the community has been trying to make this easier since soon after the release. There are extensions that try to solve the problem, but they require learning steps that are not very intuitive to users who have previously used basic Mercurial.
