---
id: VX-how-it-works-002
voice_type: how-it-works
source: public-seed
author: "Chris Davis"
work: "The Architecture of Open Source Applications, Volume 1"
chapter: "Chapter 7, Graphite, section 7.9. Clustering"
url: https://aosabook.org/en/v1/graphite.html
licence: CC BY 3.0
licence_url: https://creativecommons.org/licenses/by/3.0/
changes: none, the passage is quoted word for word
state: active
added: 2026-10-03
---

To simplify the management of scenarios like this, Graphite comes with an additional tool called carbon-relay. Its job is quite simple; it receives metric data from clients exactly like the standard carbon daemon (which is actually named carbon-cache) but instead of storing the data, it applies a set of rules to the metric names to determine which carbon-cache servers to relay the data to. Each rule consists of a regular expression and a list of destination servers. For each data point received, the rules are evaluated in order and the first rule whose regular expression matches the metric name is used. This way all the clients need to do is send their data to the carbon-relay and it will end up on the right servers.
