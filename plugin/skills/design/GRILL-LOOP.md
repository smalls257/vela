# Grill loop

How each question in a design session is asked and when it counts as answered.

## The loop

1. **One question at a time.** Wait for the answer before the next. Two questions in one turn get one answer, and the other is lost.
2. **Give your recommended answer with every question,** and the reason in one line:
   > Question? *Recommended: <answer>. <one-line reason>.*
   The team lead can take it, change it or reject it, and the session moves faster than with an open question.
3. **Read before you ask.** If the code, an ADR or a vault page can answer it, read that instead of asking.
4. **Turn "later" into a record.** "We'll figure that out later" is not an answer yet. Either settle it now, or write a deferral (`D-XXX`, the answer is known and put off) or an open question (`OQ-XXX`, nobody knows yet), each with its reason and what would unblock it.
5. **Hold terms to the glossary.** The vault's glossary (`12-glossary.md`) owns the initiative's terms and `CONTEXT.md` the app's own. When the team lead uses a term differently, say so at once: *"The glossary says a held note is one waiting to be shown, but you mean one already shown. Which is it?"*
6. **Sharpen fuzzy words.** When a vague word appears, offer the one term to use: *"You're saying 'account': the person or their Microsoft sign-in?"*
7. **Probe with concrete scenarios.** When a relationship is stated in general terms, invent a specific case that forces a precise answer. Pick edge cases, not the happy path: the boundary is where the ambiguity lives.
   > *"A customer cancels an order with three line items, one already shipped. What happens to the shipped line, the refund, and the order status?"*

   > *"The agent writes the withdrawal to its outbox, then the laptop loses power before the purge runs. What does it do on the next launch, and what does the person see?"*

   If the answer comes back general, restate the scenario more concretely until it isn't.
8. **Check against what's known,** in this order:
   1. **This conversation.** Earlier decisions stand until someone revisits them: *"You said the outbox owns retries. Now you're putting a retry loop in the consent check."*
   2. **The documents.** The vault's pages for the app (its allocated rows, contracts and epic criteria), the ADRs and `CONTEXT.md`: *"The withdrawal criterion says nothing is read once a person switches off. A read already in flight would finish after that."*
   3. **The code,** if the app exists: *"You said the new service owns the calendar sync, but a sync job already runs in the old agent. Are we moving it or running two?"*

   Then settle it one of three ways: the latest intent wins, and the earlier choice is marked superseded (or kept as a deferral if the reversal needs a trail); the earlier choice wins, and you correct the current statement; or it is genuinely open, and becomes an open question. A conflict with the vault is a challenge, as SKILL.md says under "When the vault is wrong or silent".

## Walking the tree

Settle one branch before the next, and when a branch forks, settle the fork before going down either side. Start with the walking skeleton's branches.

## What counts as answered

- A statement of fact, best of all.
- A deferral or an open question with its reason and what would unblock it.

## When a section is done

Propose moving on when every branch the section opened is closed and the section has its content. Propose completion only when every section has, the review checkpoint is disposed of, and the self-audit has run (`${CLAUDE_PLUGIN_ROOT}/references/NEG-AUDIT.md`).
