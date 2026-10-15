"""What the skills make a lead go through (docs/research/2026-10-12-session-experience-review.md and the friction pass).

These test the constraint, not the wording: who may start a close and what stops a push, how many questions a digest puts
to the lead, what the lead's words may contain, what the tool files without asking. Each one fails on the skill text the
review quoted."""
import re


from conftest import REPO

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- S27: no rule codes, raw IDs or gate names in what the lead reads

LEAD_CODE = re.compile(r"\b[EW]\d{3}\b|GATE-\d|\^c\d|\bQ-[A-Z]{3}-\d{2}|\bF\d\.\d+\b")
SPOKEN = re.compile(r'(?:\b[Ss]ay|[Tt]ell (?:the )?(?:user|lead)|\bask)\b[^"\n]{0,80}?: "([^"\n]{10,})"')


def spoken_lines():
    for path in sorted(PLUGIN.glob("skills/*/SKILL.md")) + sorted(PLUGIN.glob("references/*.md")):
        for line in SPOKEN.findall(path.read_text(encoding="utf-8")):
            yield path.relative_to(PLUGIN), line


def test_no_line_a_skill_tells_the_model_to_say_carries_a_code():
    bad = [(str(path), line) for path, line in spoken_lines() if LEAD_CODE.search(line)]
    assert not bad, bad


# --- S29 and S30: handoff and epics no longer wait on each other

def test_conventions_put_the_epics_gate_after_handoff():
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    handoff = conventions.split("\n## Handoff\n", 1)[1].split("\n## ", 1)[0]
    assert "check --gate epics" not in handoff.split("Epics come after handoff")[0]
    assert "Epics come after handoff" in handoff and "--gate epics --app <APP-id>" in handoff


# --- S36 to S47


def test_session_modes_are_listed_the_same_everywhere():
    from vela import schema
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    listed = re.search(r"- `modes` on a session: a list of ([^.]+)\.", conventions).group(1)
    assert set(re.findall(r"`(\w+)`", listed)) == set(schema.SESSION_MODES)
    modes = text("references/MODES.md")
    rows = re.findall(r"^\| ([A-Za-z &]+) \(`(\w+)`\) \|", modes, re.M)
    names = {name for name, _ in rows}
    start = text("references/START.md")
    shown = re.search(r"display name in `MODES.md`: ([^.]+)\.", start).group(1)
    start_names = set(re.split(r", | or ", shown))
    assert names - {"Answer", "Challenge"} <= start_names and "Releases" in start_names
    assert {code for _, code in rows} == set(schema.SESSION_MODES)
