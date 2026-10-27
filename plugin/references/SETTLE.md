# Settling an item

Read this when the lead is sure ("that's decided", "settle it", "lock that in"), in any mode. A plain yes to a pick is a pick, not a settle: offer once, "Want to settle that now, or keep it as not decided yet?" If they keep it, run `vela decide <ID> --later --yes ^cM` and don't offer it again this session.

1. **The lead's word is the yes.** When the lead says "settle it", "that's decided" or "lock that in", capture those words with them as origin. That capture is `--yes`. Don't read the wording back and don't ask for a second yes.
2. **What holds it up.** Run `vela check --gate decide --item <ID> --for-lead`. Say an open question under the item once, by name; settling notes it. For anything else it names, ask the one thing it asks, or offer "Settle it anyway?"; their yes is the reason (`--override <rule> --reason-from ^cM`, the same capture as the yes). When it asks if anything else was on the table, pass the answer as `--options-none ^cN`.
3. **Someone else's item.** The lead's yes settles it; `vela decide` notes it was for the owner, and you say so once, as its answer words it.
4. **File it.** Run `vela decide <ID> --yes ^cM --for-lead`. Add `--why ^cK` only when the lead gave a reason unasked or in the same breath. Never ask for one, and never ask "why not" an option. Then say "Settled. On the page it reads: ...", and go back to what the session was doing.

Whose words go on the page is as START says. The lead may skip any step ("just write it"): say once what it protects and record it as START says.

If the lead hesitates ("I think so", or they change the wording twice), offer a grill once: "Sounds like this one's worth testing. Want a grill on it, now or later?"
