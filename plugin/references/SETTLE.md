# Settling an item

Read this when the lead is sure ("that's decided", "settle it", "lock that in"), in any mode. A plain yes to a pick is a pick, not a settle: offer once, "Want to settle that now, or keep it as not decided yet?" If they keep it, run `vela decide <ID> --later --yes ^cM` and don't offer it again this session.

1. **What it beat.** If the item has no options written down yet (a pick made in this session), ask once for each option set aside without a reason: "Why not <option>, in a few words?" Capture the answer; a reason they won't give is `declined`. Pass them as `--picked "<option>=^cP" --rejected "<option>=^cR"`.
2. **What holds it up.** Run `vela check --gate decide --item <ID> --for-lead`. Say each reason in one sentence, with the one thing that clears it. Ask that thing now when the lead can answer it here. When a reason asks one question, ask it once and pass the answer as `--options-none ^cN`. For anything else: "Settle it anyway? I'll note that <what> was still open." That's an override: ask the reason once.
3. **Who else must agree.** The item owner's yes is checked in every session. When the owner isn't here: "<Name> owns this. Did they say yes somewhere, and when, or are you settling it for them?" Capture a yes given elsewhere with them as origin, plus the channel and the date. Settling it for them is `--on-behalf`, with the lead's reason recorded on the page: say they can confirm it later, or challenge it.
4. **Read it back by name: "Still yes?"** The final wording, what it rests on and who agreed, in one paragraph. Capture the read-back and the yes with no `--mark`. Up to about five items that settle together share one read-back. Silence, "ok", "sure" and "next" aren't a yes: ask once more in other words, then leave it not decided.
5. **Why, once:** "Why this one, in your words?" If they answer "as you said", ask what persuaded them.
6. **File it:** `vela decide <ID> --readback ^cN --yes ^cM --why ^cK [...] --for-lead`. Then say "Settled. On the page it reads: ...", and go back to what the session was doing.

Whose words go on the page is as START says. The lead may skip any step ("just write it"): say once what it protects, ask the reason once, and record it as START says.

If the lead hesitates ("I think so", or they change the read-back twice), offer a grill once: "Sounds like this one's worth testing. Want a grill on it, now or later?"
