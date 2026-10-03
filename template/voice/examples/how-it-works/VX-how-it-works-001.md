---
id: VX-how-it-works-001
voice_type: how-it-works
source: public-seed
author: "Chris Davis"
work: "The Architecture of Open Source Applications, Volume 1"
chapter: "Chapter 7, Graphite, section 7.6. Optimizing I/O"
url: https://aosabook.org/en/v1/graphite.html
licence: CC BY 3.0
licence_url: https://creativecommons.org/licenses/by/3.0/
changes: none, the passage is quoted word for word
state: active
added: 2026-10-03
---

Next I implemented a buffering mechanism in carbon. Each incoming data point gets mapped to a queue based on its metric name and is then appended to that queue. Another thread repeatedly iterates through all of the queues and for each one it pulls all of the data points out and writes them to the appropriate whisper file with update_many. Going back to our example, if we have 600,000 metrics updating every minute and our storage can only keep up with 1 write per millisecond, then the queues will end up holding about 10 data points each on average. The only resource this costs us is memory, which is relatively plentiful since each data point is only a few bytes.
