---
id: VX-diagnosis-002
voice_type: diagnosis
source: public-seed
author: "Chris Davis"
work: "The Architecture of Open Source Applications, Volume 1"
chapter: "Chapter 7, Graphite, section 7.8. Kernels, Caches, and Catastrophic Failures"
url: https://aosabook.org/en/v1/graphite.html
license: CC BY 3.0
license_url: https://creativecommons.org/licenses/by/3.0/
changes: none, the passage is quoted word for word
state: active
added: 2026-10-03
---

So what does all of this mean for Graphite? We just highlighted carbon's reliance on consistently low I/O latency and we also know that the write system call only returns quickly because the data is merely being copied into a buffer. What happens when there is not enough memory for the kernel to continue buffering writes? The writes become synchronous and thus terribly slow! This causes a dramatic drop in the rate of carbon's write operations, which causes carbon's queues to grow, which eats up even more memory, starving the kernel even further. In the end, this kind of situation usually results in carbon running out of memory or being killed by an angry sysadmin.
