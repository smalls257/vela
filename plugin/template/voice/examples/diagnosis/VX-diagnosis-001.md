---
id: VX-diagnosis-001
voice_type: diagnosis
source: public-seed
author: "Chris Davis"
work: "The Architecture of Open Source Applications, Volume 1"
chapter: "Chapter 7, Graphite, section 7.7. Keeping It Real-Time"
url: https://aosabook.org/en/v1/graphite.html
license: CC BY 3.0
license_url: https://creativecommons.org/licenses/by/3.0/
changes: none, the passage is quoted word for word
state: active
added: 2026-10-03
---

Buffering data points was a nice way to optimize carbon's I/O but it didn't take long for my users to notice a rather troubling side effect. Revisiting our example again, we've got 600,000 metrics that update every minute and we're assuming our storage can only keep up with 60,000 write operations per minute. This means we will have approximately 10 minutes worth of data sitting in carbon's queues at any given time. To a user this means that the graphs they request from the Graphite webapp will be missing the most recent 10 minutes of data: Not good!
