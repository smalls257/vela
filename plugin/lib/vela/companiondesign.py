"""The session panel for a design session. Pure.

A design session opens no session record, so without this the panel would say "No session is open" through a whole
design session, which reads as nothing happening (Silent Fallback). Its record of the senior's yes lives in
`.vela/design/<slug>.md`, and its work is the tech design doc. This builds the same top-level shape as
`companionsession.build`, so every surface draws it unchanged; only the sources differ:

  decided   the Decisions bullets a `decision` capture names (designchoice's matching), one row per bullet
  open      each open question, each deferral and each gap, by its own words
  next      the first template section the doc has no heading for, "source": "design order"
  touched   the pages the design changed under docs/ and CONTEXT.md
"""
import re

from vela import closegate, companionsession, designchoice
from vela.explorer import design_data

DATE_HEADING = re.compile(r"^# (\d{4}-\d{2}-\d{2})\b", re.M)
HEADING = re.compile(r"^##\s+(.+?)\s*$", re.M)
TITLE_PREFIX = re.compile(r"^Tech Design\s*[—–-]\s*")


def app_name(design, slug):
    title = TITLE_PREFIX.sub("", str(design.get("title") or "")).strip()
    return title or slug


def first_paragraph(text):
    for chunk in re.split(r"\n\s*\n", text.strip()):
        chunk = chunk.strip()
        if chunk and not chunk.startswith(("**", "-", "#", "|", "```")):
            return " ".join(chunk.split())
    return ""


def record_day(record):
    found = DATE_HEADING.search(record)
    return found.group(1) if found else ""


def written_sections(doc_text):
    found = set()
    for title in HEADING.findall(doc_text):
        key = design_data.HEADING_TO_KEY.get(title.strip().lower())
        if key:
            found.add(key)
    return found


def next_section(doc_text):
    """The first template section the doc has no heading for, and how many more follow it."""
    written = written_sections(doc_text)
    missing = [key for key in design_data.TEMPLATE_SECTIONS if key not in written]
    if not missing:
        return {"text": "", "id": "", "source": "none", "left_after": 0}
    return {"text": design_data.TITLES[missing[0]], "id": "", "source": "design order", "left_after": len(missing) - 1}


def decided_rows(doc_rel, doc_text, record, label):
    """One row per Decisions bullet that a decision capture names; a bullet no capture names is not decided."""
    captures = [c for c in closegate.captures(record).values() if c.tag == "decision"]
    rows = []
    for line in designchoice.choice_lines(doc_rel, doc_text):
        for capture in captures:
            if designchoice.names_choice(capture.words, line):
                rows.append({"id": "", "name": designchoice.plain_choice(line), "from": "", "to": "decided",
                             "label": label, "capture": int(capture.n), "page": doc_rel})
                break
    return rows


def open_rows(design):
    found = [{"id": q["id"], "name": q["title"], "who": "", "new_this_session": False, "open_days": 0,
              "kind": "question"} for q in design["open_questions"]]
    frontmatter = design["frontmatter"]
    found += [{"id": d.get("id", ""), "name": d.get("reason", ""), "who": "", "new_this_session": False, "open_days": 0,
               "kind": "deferral"} for d in frontmatter["deferred"]]
    found += [{"id": g.get("id", ""), "name": g.get("what", ""), "who": "", "new_this_session": False, "open_days": 0,
               "kind": "gap"} for g in frontmatter["gaps"]]
    return found


def touched_rows(touched):
    return [{"page": page, "name": page.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("-", " "), "change": "changed"}
            for page in touched]


def build(branch, record, doc_text, design, doc_rel, touched, today, now, stub_date=""):
    """The design session's panel. `touched` is None when git could not say, and the panel then says so."""
    slug = design["frontmatter"]["slug"] or doc_rel.rsplit("/", 1)[-1][:-3]
    day = record_day(record) or stub_date
    label = companionsession.LABEL_TODAY if day == today else companionsession.LABEL_SESSION
    summary = first_paragraph(design["summary"]["text"])
    session = {"id": slug, "title": f"Design: {app_name(design, slug)}", "modes": ["design"], "opened": day,
               "branch": branch, "start_commit": ""}
    warnings = [] if touched is not None else ["I couldn't tell which pages this design changed."]
    return {"version": companionsession.VERSION, "kind": "session", "as_of": companionsession.as_of(today, now),
            "capture": companionsession.highest_capture(record), "notes": "read", "session": session,
            "about": summary, "decided": decided_rows(doc_rel, doc_text, record, label), "said_yes": [],
            "open": open_rows(design), "agenda": [], "next": next_section(doc_text),
            "touched": touched_rows(touched) if touched is not None else None, "diagram": None, "band": "",
            "files": dict(companionsession.FILES), "vault": "", "warnings": warnings}
