---
id: VX-decision-002
voice_type: decision
source: public-seed
author: "Eric Allman"
work: "The Architecture of Open Source Applications, Volume 1"
chapter: "Chapter 17, Sendmail, section 17.4. Design Decisions"
url: https://aosabook.org/en/v1/sendmail.html
licence: CC BY 3.0
licence_url: https://creativecommons.org/licenses/by/3.0/
changes: none, the passage is quoted word for word
state: active
added: 2026-10-03
---

In retrospect, as the file got larger and 32-bit machines took over, it would have made sense to reconsider the syntax. There was a time when I thought about doing this but decided against it because I didn't want to break the "large" installed base (which at that point was probably a few hundred machines). In retrospect this was a mistake; I had simply not appreciated how large the install base would grow and how many hours it would save me had I changed the syntax early. Also, when the standards stabilized a fair amount of the generality could have been pushed back into the C code base, thus simplifying the configurations.
