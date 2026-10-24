"""What is not firm at handoff, in plain words. Pure: a vault and an app in, gaps out.

The Violation this exists to prevent is a Silent Fallback at the hinge of the product: an override on someone's behalf,
and the senior accepts an app without knowing that half its handoff list was never decided. One reader here feeds the grill's
read-back, close's manifest, `vela next` and `vela check`, so none of them can tell the senior less than another.
"""
from dataclasses import dataclass

from vela import cases, criteria, handoff, ladder, model, progress, schema, trace

UNFIRM_STATES = ("inkling", "assumption", "draft")
KINDS_THAT_NEED_A_YES = ("app", "runtime", "provides", "consumes", "requirement", "epic")


@dataclass(frozen=True)
class Gap:
    kind: str  # "unfirm", "no-case-table" or "no-designer"
    subject: str  # the ID the gap is about
    page: object
    line: int
    sentence: str


def at_handoff(vault, app):
    """An app that is handed off, or whose pages reach the handoff stage or later: its handoff list is settled, so
    a gap still in it speaks even when the app was handed over on an override."""
    reached = ladder.stage(vault, app)
    return bool(app.meta.get("handed_off")) or (bool(reached) and ladder.rank(reached) >= ladder.rank("handoff"))


def designed(vault, app):
    """A provider counts as designed once a team has taken it (handed off), its design doc is recorded, or an epic
    for it is decided: epics are written after handoff, so a decided one says a team has the boundary."""
    if app.meta.get("handed_off") or app.meta.get("design"):
        return True
    return any(e.meta.get("state") == "decided" for e in trace.epics(vault) if app.id in trace.listed(e, "apps"))


def being_built(app):
    """An app the initiative creates or changes. One that already runs, unchanged, needs no design to be called."""
    return app.meta.get("change") in schema.LADDERED_CHANGES


def name_of(vault, entry):
    found = vault.items.get(entry.id)
    if found:
        return found[0].name
    pages = vault.by_id.get(entry.id)
    return str(pages[0].meta.get("title", entry.id)) if pages else entry.id


def _unfirm(vault, app):
    for entry in handoff.handoff_list(vault, app):
        if entry.kind not in KINDS_THAT_NEED_A_YES or entry.state not in UNFIRM_STATES:
            continue
        item = vault.item(entry.id)
        page = item.page if item else vault.by_id[entry.id][0]
        line = item.line if item else model.meta_line(page, "state")
        yield Gap("unfirm", entry.id, page, line, _unfirm_sentence(vault, entry, page))


# How a not-yet-firm state reads in a sentence. "is still assumption" read as broken English to every reader the
# wording audit tried; the user ruled assumption reads "not decided yet".
STATE_PHRASE = {"inkling": "is only an early idea so far", "assumption": "is not decided yet", "draft": "is still a draft"}
# The one sentence for a contract without a case table, shared with W380 so check and next don't read as two problems.
NO_CASE_TABLE = "doesn't list what it returns when a call fails"


def state_phrase(state):
    return STATE_PHRASE.get(state, f"is {state}")


def _unfirm_sentence(vault, entry, page):
    name = name_of(vault, entry)
    phrase = state_phrase(entry.state)
    if entry.kind == "epic":
        count = sum(1 for c in criteria.read(page) if not c.struck)
        if count:
            return f"{name} ({entry.id}) {phrase}, and the same goes for its {count} acceptance criteria: nobody has agreed what finished looks like."
    if entry.kind == "requirement":
        return f"{name} ({entry.id}) {phrase}, and the same goes for its acceptance criteria."
    return f"{name} ({entry.id}) {phrase}: nobody has said yes to it."


def _without_case_tables(vault, app):
    for contract in progress.provided(vault, app) + progress.consumed(vault, app):
        if cases.case_table(contract.page, contract) is None:
            yield Gap("no-case-table", contract.id, contract.page, contract.line,
                      f"{contract.name} ({contract.id}) {NO_CASE_TABLE}, so nobody can say how a failed call is answered.")


def _undesigned_providers(vault, app):
    by_provider, providers = {}, {}
    for contract in progress.consumed(vault, app):
        provider = contract.page
        if provider.type == "app-building-blocks" and provider is not app and being_built(provider) and not designed(vault, provider):
            by_provider.setdefault(provider.id, []).append(contract)
            providers[provider.id] = provider
    for provider_id, contracts in sorted(by_provider.items()):
        provider = providers[provider_id]
        first = contracts[0]
        said = [f"{c.name} ({c.id})" for c in contracts]
        names = said[0] if len(said) == 1 else ", ".join(said[:-1]) + " and " + said[-1]
        yield Gap("no-designer", provider.id, first.page, first.line,
                  f"{app.meta.get('title', app.id)} calls {names} on {provider.meta.get('title', provider.id)}, but no team has taken "
                  f"{provider.meta.get('title', provider.id)} or designed it yet, so there is no design behind those calls to build against.")


def gaps(vault, app):
    """Every gap in the app's handoff list, unfirm items first."""
    return [*_unfirm(vault, app), *_without_case_tables(vault, app), *_undesigned_providers(vault, app)]


def lines(found):
    """The gaps as a plain list, one sentence each."""
    return [f"- {gap.sentence}" for gap in found]
