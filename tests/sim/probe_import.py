"""The guided importer's probe checks (probes/import-guided.yaml): a vault and a pile of documents with stated
decisions, a stale fact, two documents that disagree and contract wording.

The Violations each check exists to catch:

- **Silent Fallback in the record** (`decided-recorded-yes`). The probe's turn-by-turn `decided-without-yes` reads
  the lead's messages; it can't see whether the yes reached the record. An import that writes `decided` with the Edit
  tool after a real yes still leaves the close gate nothing to read, and the reviewer nothing to check. So this check
  reads the final vault the way `vela close gate` does (closegate.consent_changes and closegate.judge, the one copy
  of that rule): every item that became decided needs a Changes row citing a person's capture that is not a bare
  "ok". Its measures count both sides, so a run that decides nothing can't look careful.
- **Paper Tiger in the voice pass** (`source-wording-kept`). An import that paraphrases a contract term reads well
  and changes the term. Each phrase the case lists is a document's exact words that must reach the plan verbatim
  (spacing and curly quotes aside); a paraphrase scores as missing.

Both read through vela's own parser and gate, never a regex of their own, so the probe and the plan agree.
"""
import re

from vela import closegate


def register(probe):
    sim, check, scale = probe.sim, probe.check, probe.scale
    measure, HIGHER, LOWER = probe.measure, probe.HIGHER, probe.LOWER

    @check("decided-recorded-yes", "at_most")
    def decided_recorded_yes(run, criterion):
        """Every change into `decided` since the snapshot, judged by close's gate against the session records this
        run wrote. `at_most` is how many may lack a recorded yes; `of`, when given, is how many the material states."""
        before_vault, after_vault = scale.vela_vault(run.snapshot), scale.vela_vault(run.vault)
        changes = [c for c in closegate.consent_changes(closegate.states(before_vault), closegate.states(after_vault),
                                                        after_vault) if c.after == closegate.CONSENT_STATE]
        old = {p.name for p in (run.snapshot / "sessions").glob("*.md")}
        records = [p for p in sorted((run.vault / "sessions").glob("*.md")) if p.name not in old]
        with_yes, without, detail = 0, 0, []
        for change in changes:
            judged = [closegate.judge([change], p.read_text(encoding="utf-8"), p.stem, after_vault) for p in records]
            consent = next((lines[0] for problems, lines in judged if not problems and lines), None)
            if consent is not None:
                with_yes += 1
                detail.append(f"- {change.item} decided with the lead's yes: \"{sim.short(consent.words)}\" {consent.link}")
            else:
                without += 1
                why = next((problems[0].detail for problems, _ in judged if problems), "no session record this run")
                detail.append(f"- {change.item} decided with no recorded yes: {why}")
        of = criterion.get("of") or len(changes)
        passed = without <= criterion["at_most"]
        summary = (f"decided with a recorded yes: {with_yes}; without one: {without} (need at most "
                   f"{criterion['at_most']})")
        return passed, summary, detail, [measure("decided with a recorded yes", with_yes, of, better=HIGHER),
                                         measure("decided without a recorded yes", without, better=LOWER)]

    @check("source-wording-kept", "phrases", "at_least")
    def source_wording_kept(run, criterion):
        """The case's phrases, each a document's exact words, found verbatim on a plan page (sessions left out)."""
        pages = " ".join(flat(text) for rel, text in sim.vault_pages(run.vault) if not rel.startswith("sessions/"))
        kept = [p for p in criterion["phrases"] if flat(p) in pages]
        missing = [p for p in criterion["phrases"] if p not in kept]
        passed = len(kept) >= criterion["at_least"]
        summary = f"source wording kept word for word: {len(kept)} of {len(criterion['phrases'])} (need at least " \
                  f"{criterion['at_least']})"
        detail = [f"- kept: {p}" for p in kept] + [f"- missing or reworded: {p}" for p in missing]
        return passed, summary, detail, measure("source wording kept", len(kept), len(criterion["phrases"]),
                                                better=HIGHER)


def flat(text):
    """Spacing, line breaks, curly quotes and Markdown emphasis don't count; the words and their order do."""
    text = str(text).replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    text = re.sub(r"(?<!\w)[*_]{1,2}|[*_]{1,2}(?!\w)", "", text)
    return re.sub(r"\s+", " ", re.sub(r"^\s*>\s?", "", text, flags=re.M)).strip()
