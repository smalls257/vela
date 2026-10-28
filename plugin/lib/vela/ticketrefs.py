"""What a story relies on and what it still waits on, copied by code from the vault and the design. No model writes a
word of it. A question counts as waited on only when a sentence of the plan's Blocked by line says the story waits on it
("Not blocked by OQ-007" and "OQ-005 is not planned" do not), so a ticket never says the opposite of the plan. Pure: a Story, the loaded Vault and the design's open questions in; plain dicts out.

    relies_on(vault, story, app_id)      -> [ref]  each contract and requirement on the story's Traces to line, in order
    still_open(vault, story, questions)  -> [question]  each OQ-/UNK- its Blocked by line or design notes name
    open_problems(vault, story, questions) -> [(text, flag)]

A Jira reader can't follow CON-003 to a vault page, so the ticket carries the contract itself. The Violation this
prevents is a Paper Tiger: tickets that link everything and explain nothing. Copying by code, never by a model, keeps
the ticket saying what the vault says (Anchor).
"""
import re

from vela import breakdown, model, plainwords, ticketcopy

WIKILINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
CROSSES = re.compile(r"^\s*In:\s*(.*?)\.?\s*Out:\s*(.*?)\.?\s*$", re.I | re.S)
DESIGN_UNREAD = "the plan's design couldn't be read"
QUESTION_ID = re.compile(r"\b(?:OQ|UNK)-\d+\b")
SENTENCE = re.compile(r"(?<=[.?!])\s+")
NOT_A_WAIT = re.compile(r"\bnot blocked by\b|\b(?:is|are) not planned\b(?! until)|\bnot decided here\b", re.I)  # a sentence that names a question to say the story doesn't wait on it
MEANWHILE = re.compile(r"([^;]*?)\s+meanwhile\b", re.I)
CONTRACT = re.compile(r"^CON-\d+$")
REQUIREMENT = re.compile(r"^CAP-\d+\.FR\d+$")


def normal(text):
    """A sentence as a reader compares it: wiki links shown as their words, runs of space as one, curly quotes straight."""
    text = WIKILINK.sub(r"\1", text or "")
    for fancy, plain in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"')):
        text = text.replace(fancy, plain)
    return re.sub(r"\s+", " ", text).strip()


def statement_of(item):
    """The sentence under a requirement's heading, before its fact bullets: what the requirement says."""
    out = []
    for line in item.page.text.split("\n")[item.line:]:
        if line.startswith("#") or line.lstrip().startswith("-") or (out and not line.strip()):
            break
        if line.strip():
            out.append(line.strip())
    return " ".join(out)


def provider_of(vault, contract):
    """Who provides a contract: its Provider bullet, else the app whose page it is written on."""
    said = contract.fact("Provider")
    return normal(said) if said else vault.name_of(contract.page.id)


def contract_ref(vault, item, app_id, held):
    crossing = normal(item.fact("Crosses the boundary") or "")
    split = CROSSES.match(crossing)
    return {"kind": "contract", "id": item.id, "name": item.name, "description": statement_of(item),
            "sends": split.group(1) if split else None, "gets": split.group(2) if split else None,
            "crosses": "" if split else crossing, "provides": item.page.id == app_id,
            "provider": provider_of(vault, item), "state": plainwords.state_word(item.fact("State") or ""),
            "open": len(held.get(item.id, []))}


def quoted_at(story, statement):
    """The 1-based number of the plan criterion that quotes `statement` word for word, or None."""
    want = normal(statement)
    return next((n for n, c in enumerate(story.criteria, 1) if normal(c) == want), None)


def requirement_ref(item, story):
    statement = statement_of(item)
    shown = quoted_at(story, statement) in ticketcopy.covered(story)
    return {"kind": "requirement", "id": item.id, "name": item.name, "statement": None if shown else statement}


def relies_on(vault, story, app_id):
    held, out = model.blockers(vault), []
    for target in breakdown.labels_of(story):
        base = target.split("@")[0]
        item = vault.item(base)
        if CONTRACT.match(base) or REQUIREMENT.match(base):
            if item is None:
                out.append({"kind": "missing", "id": base})  # check_story already flags it; the ticket says it too
            elif CONTRACT.match(base):
                out.append(contract_ref(vault, item, app_id, held))
            else:
                out.append(requirement_ref(item, story))
    return out


def plan_sentences(story):
    """Each sentence of the story's Blocked by line and open-for-the-design notes, in the plan's order."""
    return [s for text in [story.blocked or "", *story.open_notes] for s in SENTENCE.split(text) if s.strip()]


def waits_sentence(sentence):
    """True when the sentence says the story waits (the default for a sentence that names a question); False for one
    that says it doesn't."""
    return not NOT_A_WAIT.search(sentence)


def waits_on_ids(story):
    found = [q for s in plan_sentences(story) if waits_sentence(s) for q in QUESTION_ID.findall(s)]
    return list(dict.fromkeys(found))


def until_clause(sentence, question_id):
    """The plan's words for what happens meanwhile, in one sentence that names the question: what follows "until
    then" or "until it's answered", or, when the sentence says only what it holds until the question is answered, the
    clause that ends "meanwhile". None when the sentence doesn't say."""
    after = re.search(rf"\buntil (?:then|it(?:'s| is) answered|{re.escape(question_id)} is answered)\b[,:]?\s*([^;]*?)[.;]?\s*$", sentence, re.I)
    if after and after.group(1).strip():
        return after.group(1).strip()
    held = MEANWHILE.search(sentence)
    if held:
        clause = re.split(r"\bso\b", held.group(1))[-1].strip(" ,:")
        return clause or None
    return None


def until_then(story, question_id):
    """What the story does until the question is answered, in the plan's words, from a sentence that names the
    question. None when the plan doesn't say."""
    for sentence in plan_sentences(story):
        if question_id in sentence and waits_sentence(sentence):
            found = until_clause(sentence, question_id)
            if found:
                return found
    return None


def lead_lowered(role):
    """A role as the vault spells it, for the middle of a sentence: only an ordinary leading word loses its capital
    ("Product owner" -> "product owner"); "IT endpoint lead", "CISO" and "DPO" keep theirs."""
    return role if role[1:2].isupper() else role[:1].lower() + role[1:]


def owner_words(raw):
    """"@product-owner (Product owner)" -> "the product owner"; "(IT endpoint lead)" -> "the IT endpoint lead"; a bare
    handle -> its words."""
    role = re.search(r"\(([^)]+)\)", raw or "")
    if role:
        return "the " + lead_lowered(role.group(1).strip())
    handle = re.search(r"@([\w-]+)", raw or "")
    return handle.group(1).replace("-", " ") if handle else normal(raw or "")


def still_open(vault, story, questions):
    out = []
    for qid in waits_on_ids(story):
        if qid.startswith("UNK-"):
            item = vault.item(qid)
            out.append({"id": qid, "found": item is not None,
                        "question": normal(item.fact("Question") or item.name) if item else "",
                        "until": until_then(story, qid), "waits_label": "Waiting on",
                        "waits": owner_words(item.fact("Owner")) if item else ""})
        else:
            entry = (questions or {}).get(qid)
            out.append({"id": qid, "found": entry is not None, "question": entry["title"] if entry else "",
                        "until": until_then(story, qid), "waits_label": "What would answer it",
                        "waits": normal(entry["what_would_unblock"]) if entry else ""})
    return out


def open_problems(vault, story, questions, design_gap=""):
    out = []
    for q in still_open(vault, story, questions):
        if q["id"].startswith("OQ-") and questions is None:
            out.append((f"waits on {q['id']}, but {design_gap or DESIGN_UNREAD}, so its ticket can't say what the question is", True))
            continue
        if not q["found"]:
            if q["id"].startswith("OQ-"):
                out.append((f"waits on {q['id']}, which isn't an open question of the design", True))
            continue  # an unknown the vault lacks is already "isn't in the plan" (tickets.check_story)
        name = vault.named(q["id"]) if q["id"].startswith("UNK-") else f'"{q["question"]}" ({q["id"]})'
        if q["until"] is None:
            out.append((f"waits on {name}, but doesn't say what it does until that's answered; say it in the same "
                        "sentence of 'Blocked by:', as 'until then ...'", True))
    return out
