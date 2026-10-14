"""What is not firm at handoff, in plain words. Pure: a vault and an app in, gaps out.

The Violation this exists to prevent is a Silent Fallback at the hinge of the product: an override on someone's behalf,
and the senior accepts an app without knowing that half its handoff list was never decided. One reader here feeds the grill's
read-back, close's manifest, `planner next` and `planner check`, so none of them can tell the senior less than another.
"""
from dataclasses import dataclass

from planner import cases, criteria, handoff, model, progress, schema, trace

UNFIRM_STATES = ("inkling", "assumption", "draft")
KINDS_THAT_NEED_A_YES = ("app", "runtime", "provides", "consumes", "requirement", "epic")


@dataclass(frozen=True)
class Gap:
    kind: str  # "unfirm", "no-case-table" or "no-designer"
    subject: str  # the ID the gap is about
    page: object
    line: int
    sentence: str


def at_handoff(app):
    """An app that is handed off, or whose pages have reached the handoff stage."""
    return bool(app.meta.get("handed_off")) or app.meta.get("stage") == "handoff"


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


def _unfirm_sentence(vault, entry, page):
    name = name_of(vault, entry)
    base = f"{name} ({entry.id}) is still {entry.state}: nobody has decided it."
    if entry.kind == "epic":
        count = sum(1 for c in criteria.read(page) if not c.struck)
        if count:
            return f"{name} ({entry.id}) is still {entry.state}, and so are its {count} acceptance criteria: nobody has said yes to what done means."
    if entry.kind == "requirement":
        return f"{name} ({entry.id}) is still {entry.state}, and so are its acceptance criteria."
    return base


def _without_case_tables(vault, app):
    for contract in progress.provided(vault, app) + progress.consumed(vault, app):
        if cases.case_table(contract.page, contract) is None:
            yield Gap("no-case-table", contract.id, contract.page, contract.line,
                      f"{contract.name} ({contract.id}) has no case table: what it answers when something goes wrong is not written down.")


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
        names = ", ".join(f"{c.name} ({c.id})" for c in contracts)
        yield Gap("no-designer", provider.id, first.page, first.line,
                  f"{provider.meta.get('title', provider.id)} provides {names} to {app.meta.get('title', app.id)}, and nobody has designed it yet: "
                  f"no team has taken it, so there is nothing to build the calls against.")


def gaps(vault, app):
    """Every gap in the app's handoff list, unfirm items first."""
    return [*_unfirm(vault, app), *_without_case_tables(vault, app), *_undesigned_providers(vault, app)]


def lines(found):
    """The gaps as a plain list, one sentence each."""
    return [f"- {gap.sentence}" for gap in found]
