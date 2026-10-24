"""Who holds a question: the one rule the dashboard and the companions share.

Moved out of `explorer/asks_data.py` so the companion panels name the person the way the dashboard does, from the same
function (Distributed Monolith of names ruled out). `who_to_ask` reads an object with `.fact(label)`: a plan item, or the
tiny adapter `pageindex.who` builds from the indexed owner and ask lines.
"""
import re

from vela import schema
from vela.explorer.record import plain

HANDLE = re.compile(rf"@{schema.HANDLE_NAME}")
ACRONYMS = {"ceo": "CEO", "cto": "CTO", "cio": "CIO", "ciso": "CISO", "cfo": "CFO", "coo": "COO", "dpo": "DPO",
            "hr": "HR", "pr": "PR", "qa": "QA", "ux": "UX"}


def human(handle):
    """@coach-lead -> Coach lead; @ceo -> CEO."""
    words = [ACRONYMS.get(w.lower(), w) for w in handle.lstrip("@").replace("-", " ").split()]
    text = " ".join(words)
    return text[:1].upper() + text[1:]


def resolve_role(role, handles):
    role = role.strip().strip(".").removeprefix("the ").strip()
    slug = role.lower().replace(" ", "-")
    for h in handles:
        if h.lstrip("@").lower() == slug:
            return h, human(h)
    return None, human(role)


def who_to_ask(unknown, handles):
    """{key, name, inferred, recorded, rule, owner, also, asked_by}: the rack a strip sits in. `recorded` is true only
    when the unknown has an Ask line; without one the rack is the owner's or a guess, and the page must not read it as
    a person having been asked."""
    owner = plain(unknown.fact("Owner"))
    found = HANDLE.findall(owner)
    owner_handle = found[0] if found else owner.strip() or "unassigned"
    base = {"owner": owner_handle, "also": [], "asked_by": "", "recorded": False}
    recorded = plain(unknown.fact("Ask"))
    if recorded:
        h = HANDLE.findall(recorded)
        key = h[0] if h else recorded
        return {**base, "key": key, "name": human(key) if h else recorded, "inferred": False, "recorded": True,
                "rule": f"{human(key) if h else recorded}, named on the question"}
    paren = " ".join(re.findall(r"\(([^)]*)\)", owner))
    owner_role = paren.split(",")[0].split(";")[0].strip() if paren else ""
    m = re.search(rf"asking (@{schema.HANDLE_NAME})", paren)
    if m:
        return {**base, "key": m.group(1), "name": human(m.group(1)), "inferred": True,
                "rule": f"A guess: the owner's note says to ask {human(m.group(1))}."}
    m = re.search(r"(?:asking|who asks|asks) (the [a-z ]+?|[a-z ]+?)(?:[;,)]|$)", paren, re.I)
    if m:
        parts = re.split(r"\s+and\s+", m.group(1).strip())
        resolved = [resolve_role(p, handles) for p in parts]
        h, name = resolved[0]
        return {**base, "key": h or name, "name": name, "inferred": True, "also": [n for _, n in resolved[1:]],
                "rule": f"A guess: the owner's note says to ask {' and '.join(n for _, n in resolved)}."}
    m = re.search(r"([a-z ]+?) gives the ruling", paren, re.I)
    if m:
        h, name = resolve_role(m.group(1), handles)
        return {**base, "key": h or name, "name": name, "inferred": True,
                "rule": f"A guess: the owner's note says {name} gives the ruling."}
    asked_by = "the product lead" if "product lead does the asking" in paren else ""
    name = human(owner_role) if owner_role and len(owner_role) < 30 else human(owner_handle)
    return {**base, "key": owner_handle, "name": name, "inferred": False, "also": [human(h) for h in found[1:]],
            "asked_by": asked_by,
            "rule": f"{name}, who owns it (nobody else is named)" + ("; the product lead does the asking" if asked_by else "")}
