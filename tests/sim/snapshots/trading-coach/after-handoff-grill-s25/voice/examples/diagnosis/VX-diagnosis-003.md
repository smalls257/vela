---
id: VX-diagnosis-003
voice_type: diagnosis
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

The syntax of the configuration file was driven by a couple of issues. First, the entire application had to fit into a 16-bit address space, so the parser had to be small. Second, early configurations were quite short (under one page), so while the syntax was obscure, the file was still comprehensible. However, as time passed, more operational decisions moved out of the C code into the configuration file, and the file started to grow. The configuration file acquired a reputation for being arcane. One particular frustration for many people was the choice of the tab character as an active syntax item. This was a mistake that was copied from other systems of the time, notably make. That particular problem became more acute as window systems (and hence cut-and-paste, which usually did not preserve the tabs) became available.
