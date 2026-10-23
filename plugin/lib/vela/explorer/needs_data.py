"""D.needs: the lines of the Needs you block, from data the build already holds. Pure: dicts in, dict out.

The Violation this exists to prevent is a Distributed Monolith between the block and the data behind it: if the block
re-derived "who owns the thing a reader proposed" or "when an app was handed over" from the entities itself, a change to
how owners are recorded would need an edit in the script and another here. The pieces are gathered here in the
shapes `vela.needsyou` takes, and the rules (late, soon, just handed, most urgent first) are decided there.
"""
from vela import needsyou


def owner_of(entities, key):
    """The handle that owns what a key names: its own Owner line, else the owner of the page it sits on. "" when nobody is recorded."""
    found = entities.get(key) or {}
    return found.get("ownerKey") or (entities.get(found.get("pageKey")) or {}).get("ownerKey", "")


def proposals(pending, awaiting, entities):
    """Decisions waiting on an owner's yes: a reader's pending approval goes to the owner of what it is on; a decision
    made on someone's behalf goes to the owners it names."""
    out = [{"key": p["key"], "by": p["by"], "date": p["date"], "owners": [owner_of(entities, p["key"])]} for p in pending]
    out += [{"key": a["key"], "by": a["by"], "date": "", "owners": list(a["owners"])} for a in awaiting]
    return out


def extract(data, entities, handed, today):
    """{"lines": [...], "dates": [...]}: see needsyou.extract. `handed` is [{"key": app key, "handed_off": the app's field}]."""
    return needsyou.extract(data["asks"], data["grills"]["rows"], proposals(data["pending"], data["progress"]["awaiting"], entities), handed, today)
