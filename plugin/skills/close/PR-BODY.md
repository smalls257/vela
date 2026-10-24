# The sentences a reviewer reads first

Read by close under "The pull request, and what you tell the lead". `vela close pr` builds the rest of the body. Don't repeat any of it. The body says what changed, never what anyone said: the session's notes stay on the lead's machine, and a reviewer who wants to see one of the lead's own yeses asks them (`vela records show <id> <ref>` prints it).

Write two or three sentences, in the house voice:

- what the session settled, in the reader's terms;
- what to look at first, and why: a decision that shapes the design, a contract another team uses, a page rewritten whole;
- what is still open that matters to them, and who is chasing it.

Name things; an ID only as a tag after a name. Quote no one, and name no one's opinion: the lines above are the only place words appear. No check codes and no lists. For example: "This settles how the dock service takes payment: through the card processor, not a till of its own. Look first at the change to the payment contract, since the fleet console uses it too. Who owns the Spokewell repair feed is still open; Ines is asking by October 23."

Then add a line for anything the body can't see, only when there is one: each paragraph rewritten whole, pointing to `## Replaced prose` in the session's notes (the reviewer can't open them, so say which page instead); each "No examples for <type>: drafted without examples" line house-voice gave; each catalog entry drafted under `## Catalog proposals` (in the notes too, so name the entry).
