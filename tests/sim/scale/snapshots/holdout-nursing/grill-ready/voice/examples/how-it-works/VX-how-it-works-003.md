---
id: VX-how-it-works-003
voice_type: how-it-works
source: public-seed
author: "Andrew Alexeev"
work: "The Architecture of Open Source Applications, Volume 2"
chapter: "Chapter 14, nginx, section 14.2. Overview of nginx Architecture"
url: https://aosabook.org/en/v2/nginx.html
license: CC BY 3.0
license_url: https://creativecommons.org/licenses/by/3.0/
changes: none, the passage is quoted word for word
state: active
added: 2026-10-03
---

As previously mentioned, nginx doesn't spawn a process or thread for every connection. Instead, worker processes accept new requests from a shared "listen" socket and execute a highly efficient run-loop inside each worker to process thousands of connections per worker. There's no specialized arbitration or distribution of connections to the workers in nginx; this work is done by the OS kernel mechanisms. Upon startup, an initial set of listening sockets is created. workers then continuously accept, read from and write to the sockets while processing HTTP requests and responses.
