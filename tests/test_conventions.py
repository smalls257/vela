"""CONVENTIONS.md must explain every name the code uses, and its copies must match."""
import pytest

from conftest import REPO
from planner import catalog, ledger, schema

CONVENTIONS = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")


def names():
    out = set()
    for page_type, spec in schema.PAGE_TYPES.items():
        out.add(f"`{page_type}`")
        out.update(f"`{f}`" for f in spec["required"] + spec["optional"])
        out.update(f"`{s}`" for s in spec["states"] or ())
    for values in schema.ENUMS.values():
        out.update(f"`{v}`" for v in values)
    out.update(f"`{m}`" for m in schema.SESSION_MODES)
    labels = (schema.CONTRACT_REQUIRED + schema.CONTRACT_OPTIONAL + schema.UNKNOWN_REQUIRED
              + schema.UNKNOWN_OPEN_REQUIRED + schema.UNKNOWN_RESOLVED_REQUIRED + schema.UNKNOWN_OPTIONAL
              + schema.RISK_REQUIRED + schema.RISK_OPTIONAL + schema.PAGE_LABELS + schema.SUBJECT_LABELS)
    out.update(f"**{label}:**" for label in labels)
    out.update(f"`{v}`" for v in schema.CONTRACT_STATES + schema.CONTRACT_CHANGES + schema.UNKNOWN_STATES
               + schema.RISK_STATES + schema.SOURCE_KINDS + schema.CONTAINER_STATES + schema.CELL_STATES
               + schema.PARTY_RELATIONSHIPS)
    out.update(f"`{v}`" for v in ledger.STATES + catalog.SCOPES + catalog.SEVERITIES + catalog.BLOCK_KINDS + catalog.CREATES)
    out.update(f"`{k}`" for k in ledger.KEYS)
    out.update(f"`{field}`" for field in ("id", "area", "scope", "trigger", "question", "why", "severity", "blocks",
                                         "creates", "mentions", "mention_why", "mention_except"))
    out.update(f"`{code}`" for code in ("FIN", "DAT", "PTN", "REG", "OPS"))
    out.add("`Q-OPS-01@APP-*`")
    for header in (schema.GOALS_HEADER, schema.SOURCES_HEADER, schema.CHANGES_HEADER, ledger.HEADER):
        out.add(" \\| ".join(header))
    out.update(f"`{name}`" for name in schema.BLOCKS)
    out.update(schema.CODES)
    out.update(f"`{n}`" for n in ("APP-booking", "RUN-booking", "CAP-013", "FLO-001", "EPC-031", "ADR-0001",
                                   "concern-testing", "CON-001", "UNK-001", "R-01", "G1", "CST-1", "SRC-01", "INI-001",
                                   "PTY-01", "SV-01"))
    out.update(f"`{v}`" for v in schema.VOICE_TYPES + schema.VOICE_SOURCES + schema.VOICE_STATES)
    out.add(f"sha={schema.NEW_BLOCK_SHA}")
    out.add(f"at most {schema.FLOWCHART_BUDGET} elements")
    out.add(f"at most {schema.SEQUENCE_BUDGET} participants")
    return sorted(out)


@pytest.mark.parametrize("name", names())
def test_conventions_explain_every_name(name):
    assert name in CONVENTIONS, f"{name} is used by planner but CONVENTIONS.md never mentions it"


def test_conventions_finding_table_matches_codes():
    for code, meaning in schema.CODES.items():
        assert f"| {code} | {meaning} |" in CONVENTIONS, f"{code} row should read '| {code} | {meaning} |'"
