"""Vault health as one Markdown report, for a person to run (`vela health`) and read or paste. Pure.

The report is built from `vela check`'s own findings (W704, W705, W711, W716),
so the report and the check never disagree about what is stale or overdue.
"""
import datetime

from vela import rules, schema
from vela.parse import split_row


JOINER = "\u200d"


def inert(text):
    """Free text that cannot @-mention anyone or link an issue. Only owners are meant to ping."""
    return str(text).replace("@", "@" + JOINER).replace("#", "#" + JOINER)


def owner(text):
    """The leading handle of an owner field, which is what check's owner rule matched; nothing after it."""
    match = schema.OWNER_BULLET_RE.match(text.strip()) if isinstance(text, str) else None
    return match.group(0) if match else ""


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
                rows.append((inert(f"{unknown.id} {unknown.name}"), owner(unknown.fact("Owner")) or "no owner recorded",
                             inert(unknown.fact("Ask by"))))
    return rows


def dated(date, finding):
    """A future date is a typo, not staleness, so its cell says which one the row is."""
    note = " (in the future; check for a typo)" if "dated in the future" in finding.message else ""
    return inert(date) + note


def stale_page_rows(vault, found):
    by_path = {p.path: p for p in vault.pages}
    rows = []
    for finding in found:
        page = by_path.get(finding.path)
        if page is not None:
            rows.append((inert(page.path), dated(page.meta.get("last_verified", ""), finding), inert(page.meta.get("verified_by", "")),
                         owner(page.meta.get("owner")) or inert(page.meta.get("owner", ""))))
    return rows


def stale_source_rows(vault, found):
    by_path = {p.path: p for p in vault.pages}
    rows = []
    for finding in found:
        page = by_path.get(finding.path)
        lines = page.text.split("\n") if page is not None else []
        if 0 < finding.line <= len(lines):
            row = split_row(lines[finding.line - 1])
            source, title, who, date = (row + ("",) * 4)[:4]
            rows.append((inert(source), inert(title), dated(date, finding), owner(who) or inert(who)))
    return rows


def last_closed(vault):
    dates = [s.meta.get("date") for s in vault.sessions if s.meta.get("status") == "closed"]
    return max((d for d in dates if rules.is_date(d)), default="")


def verified(value):
    return bool(value.strip()) if isinstance(value, str) else value is not None


def never_verified(vault):
    pages = [p for p in vault.pages if p.type in schema.PAGE_TYPES and p.type != "session"]
    return sum(1 for p in pages if not verified(p.meta.get("last_verified"))), len(pages)


def section(title, header, rows, found):
    """A table, plus a visible line when findings could not be mapped to a row. Nothing is dropped silently."""
    lines = ["", f"## {title}", ""]
    lines += table(header, rows) if rows or not found else []
    if len(rows) < len(found):
        lines += ["", f"{len(found) - len(rows)} findings not shown; run `vela check`."]
    return lines


def report(vault, findings, today, commit):
    """The report, as Markdown. `findings` is the output of rules.check for the same `today`."""
    by_code = {}
    for finding in findings:
        by_code.setdefault(finding.code, []).append(finding)
    errors = sum(1 for f in findings if f.is_error)
    out = ["# Vault health",
           "",
           f"Made by `vela health` on {today}, from {commit}. `vela check` found {errors} errors and "
           f"{len(findings) - errors} warnings."]
    for title, header, rower, code in (
            ("Overdue open questions", ("Open question", "Owner", "Ask by"), overdue_rows, "W705"),
            ("Stale pages", ("Page", "Last verified", "By", "Owner"), stale_page_rows, "W704"),
            ("Stale sources", ("Source", "Title", "Date", "Owner"), stale_source_rows, "W716")):
        found = by_code.get(code, [])
        out += section(title, header, rower(vault, found), found)
    last = last_closed(vault)
    if not last:
        sessions = "No session has closed yet."
    else:
        days = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(last)).days
        if days < 0:
            sessions = f"The last closed session is dated in the future ({last}); check for a typo."
        else:
            sessions = f"The last session closed on {last}, {days} days ago." + (" That is over 30 days." if "W711" in by_code else "")
    missing, total = never_verified(vault)
    out += ["", "## Sessions", "", sessions, "", "## Never verified", "",
            f"{missing} of {total} pages don't record when someone last checked them (their last_verified date)."]
    return "\n".join(out) + "\n"
