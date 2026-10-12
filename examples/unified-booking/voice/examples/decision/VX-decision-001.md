---
id: VX-decision-001
voice_type: decision
source: public-seed
author: "Margo Seltzer and Keith Bostic"
work: "The Architecture of Open Source Applications, Volume 1"
chapter: "Chapter 4, Berkeley DB, section 4.7. The Lock Manager: Lock"
url: https://aosabook.org/en/v1/bdb.html
licence: CC BY 3.0
licence_url: https://creativecommons.org/licenses/by/3.0/
changes: none, the passage is quoted word for word
state: active
added: 2026-10-03
---

Berkeley DB's choice to use page-level locking was made for good reasons, but we've found that choice to be problematic at times. Page-level locking limits the concurrency of the application as one thread of control modifying a record on a database page will prevent other threads of control from modifying other records on the same page, while record-level locks permit such concurrency as long as the two threads of control are not modifying the same record. Page-level locking enhances stability as it limits the number of recovery paths that are possible (a page is always in one of a couple of states during recovery, as opposed to the infinite number of possible states a page might be in if multiple records are being added and deleted to a page). As Berkeley DB was intended for use as an embedded system where no database administrator would be available to fix things should there be corruption, we chose stability over increased concurrency.
