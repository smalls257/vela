"""The Grills waiting view's data (D.grills): `vela.grills.waiting`, with every ID turned into the key the page names it by.

The Violation this exists to prevent is a Leaky Narrative on the page: if view-grills.js had to know that an epic's
key is its page's ID, that a source is a Library row and that a grill owner lives in `.vela.yaml`, each rule would
live in script where no vault test reaches it. They are decided in `vela.grills` and here, once, and the page only
draws the rows. Who "Mine" means is the page's (it knows who is viewing); the people each row names are handles.

Pure: it takes the vault, the keys and the verdicts the build computed from the flow checker's record.
"""
from vela import grillowners, grills


def key_of(vault, keys, ident):
    """The page's key for an ID: the item itself, else the page that holds it."""
    if vault.item(ident) is not None:
        return ident
    pages = vault.by_id.get(ident)
    return keys.page(pages[0]) if pages else None


def keyed(vault, keys, ids):
    return [k for k in dict.fromkeys(key_of(vault, keys, i) for i in ids) if k]


def row(vault, keys, found, library_ids):
    out = found.as_json()
    out.update({"key": key_of(vault, keys, found.id), "holdsUp": keyed(vault, keys, found.holds_up), "apps": keyed(vault, keys, found.apps),
                "sources": [f"lib:{s}" for s in found.sources if s in library_ids]})
    return out


def extract(vault, keys, verdicts, today, library_ids=()):
    """{"rows": [...], "people": [handles named], "problems": [...]}: the waiting grills in their groups' order."""
    _, problems = grillowners.read(vault.config)
    rows = [row(vault, keys, g, set(library_ids)) for g in grills.waiting(vault, verdicts, today)]
    people = sorted({h for r in rows for h in (*r["owner"], *r["join"])})
    return {"rows": rows, "people": people, "problems": problems}
