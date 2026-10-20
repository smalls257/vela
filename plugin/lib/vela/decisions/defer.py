"""The `defer` apply kind: an owed question handed to whoever can answer it, as a new open unknown that blocks it
(epics section 7's E805 route "defer it to an owner"; close section 2's "left for a grill"). Pure.

The Violation this exists to prevent is a Silent Fallback at process level: "we'll come back to it" with nobody
chasing it. A deferral is only honest while an open question with an owner and an ask-by date carries it, so a
deferral IS an unknown: `### UNK-nnn <name>` with `**Owner:**` the handle the lead named, `**Ask by:**` only if the
lead gave or agreed a date (never one the tool picks), and `**Blocks:**` the owed question's copy or
`R-` ID as written, so the gate can see the question has someone chasing it. The capture is kept as that unknown.

The question-ledger row `unknown` that disposes of the copy is the `ledger` kind's to write at close; until then the
epics gate still shows the question, which is expected: the skill says so once and moves on, rather than re-offering
the routes (the loop the old gate caused).

The writing is `add unknown`'s (`add_unknown`), one grammar for every unknown; this kind only says what a deferral
holds.
"""
from vela.decisions import add_unknown, schema, textedit

SCHEMA = schema.KindSchema(
    fields={"copy": "the owed question's copy ID (Q-XXX-nn@<scope>) or reviewer question ID (R-XXX-nn)",
            "name": "the unknown's short name: at most six words",
            "question": "the question, in the lead's words (leave null to take the capture's words)",
            "owner": "the handle of whoever the lead said answers it",
            "ask": "who would actually know, when that isn't the owner",
            "ask_by": "YYYY-MM-DD, only a date the lead gave or said yes to; leave null otherwise",
            "capture": "the capture holding the lead's word on who answers it"},
    judgment=("owner", "capture"), required=("copy", "name", "owner", "capture"),
    example={"copy": "Q-FIN-02@INI-001", "name": "Stored value liability", "owner": "@cfo", "capture": "^c41"})


def as_unknown(item):
    unknown = {k: item.get(k) for k in ("name", "question", "owner", "ask", "ask_by", "capture") if item.get(k)}
    return dict(unknown, blocks=[item["copy"]])


def validate(item, vault, record):
    found = textedit.context_refusals(vault)
    if not add_unknown.COPY.match(str(item["copy"])):
        found.append(textedit.refusal("defer-copy", "I couldn't tell which owed question that is.",
                                      f"copy {item['copy']!r} is not a copy ID (Q-XXX-nn@<scope>) or a reviewer "
                                      "question ID (R-XXX-nn).", override="none: name the question"))
    return found + add_unknown.validate(as_unknown(item), vault, record)


def apply(item, vault, record):
    return add_unknown.apply(as_unknown(item), vault, record)
