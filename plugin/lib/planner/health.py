"""Vault health as one Markdown report, for the weekly "Vault health" issue. Pure.

The report is built from `planner check`'s own findings (W704, W705, W711, W716),
so the issue and the check never disagree about what is stale or overdue.
"""
import datetime

from planner import schema
from planner.parse import split_row


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(header, rows):
    if not rows:
        return ["None."]
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(map(cell, r)) + " |" for r in rows]


def overdue_rows(vault, found):
    rows = []
    for finding in found:
        for unknown in vault.unknowns:
            bullet = unknown.facts.get("Ask by")
            if unknown.page.path == finding.path and bullet is not None and bullet.line == finding.line:
                rows.append((f"{unknown.id} {unknown.name}", unknown.fact("Owner") or "no owner recorded", unknown.fact("Ask by")))
    return rows


def stale_page_rows(vault, found):
    by_path = {p.path: p for p in vault.pages}
    rows = []
    for finding in found:
        page = by_path.get(finding.path)
        if page is not None:
            rows.append((page.path, page.meta.get("last_verified", ""), page.meta.get("verified_by", ""), page.meta.get("owner", "")))
    return rows


def stale_source_rows(vault, found):
    by_path = {p.path: p for p in vault.pages}
    rows = []
    for finding in found:
        page = by_path.get(finding.path)
        lines = page.text.split("\n") if page is not None else []
        if 0 < finding.line <= len(lines):
            row = split_row(lines[finding.line - 1])
            rows.append(tuple((row + ("",) * 6)[i] for i in (0, 1, 3, 2)))
    return rows


def last_closed(vault):
    dates = [s.meta.get("date") for s in vault.sessions if s.meta.get("status") == "closed"]
    return max((d for d in dates if isinstance(d, str) and schema.DATE_RE.match(d)), default="")


def never_verified(vault):
    pages = [p for p in vault.pages if p.type in schema.PAGE_TYPES and p.type != "session"]
    return sum(1 for p in pages if "last_verified" not in p.meta), len(pages)


def report(vault, findings, today, commit):
    """The issue body, as Markdown. `findings` is the output of rules.check for the same `today`."""
    by_code = {}
    for finding in findings:
        by_code.setdefault(finding.code, []).append(finding)
    errors = sum(1 for f in findings if f.is_error)
    out = ["# Vault health", "",
           f"Built by `planner health` on {today} from {commit}. `planner check` found {errors} errors and "
           f"{len(findings) - errors} warnings.", ""]
    out += ["## Overdue unknowns", ""] + table(("Unknown", "Owner", "Ask by"), overdue_rows(vault, by_code.get("W705", [])))
    out += ["", "## Stale pages", ""] + table(("Page", "Last verified", "By", "Owner"),
                                              stale_page_rows(vault, by_code.get("W704", [])))
    out += ["", "## Stale sources", ""] + table(("Source", "Title", "Date", "Owner"),
                                                stale_source_rows(vault, by_code.get("W716", [])))
    last = last_closed(vault)
    if not last:
        sessions = "No session has closed yet."
    else:
        days = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(last)).days
        sessions = f"The last session closed on {last}, {days} days ago." + (" That is over 30 days." if "W711" in by_code else "")
    missing, total = never_verified(vault)
    out += ["", "## Sessions", "", sessions, "", "## Never verified", "",
            f"{missing} of {total} pages carry no `last_verified`, so nobody has said when they were last checked."]
    return "\n".join(out) + "\n"
