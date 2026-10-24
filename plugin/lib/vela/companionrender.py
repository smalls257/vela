"""One session or explain dict, drawn three ways: terminal Markdown, a one-line band, a self-contained HTML page. Pure.

Every surface draws the same dict, so they can't drift (Distributed Monolith ruled out), and none of them holds a plan
rule: the words and the counts come from the dict. The panels only show; nothing here sends anything back to Claude
(owner's ruling of October 24, 2026), so there are no buttons. Vault text reaches the HTML only escaped.
"""
import datetime
import re
from html import escape as _escape

from vela import companionsvg, say

def escape(text):
    """Text for an HTML text node: markup is escaped; quotes are safe there and stay readable."""
    return _escape(str(text), quote=False)


BAND_WIDTH = 100  # why: the band shows below 110 columns, beside the prompt's own margins
OPEN_HINT = "/vela-companion to open"
DASHBOARD_LINE = "Full dashboard: dashboard.html in this folder"
UNREADABLE = "I can't read this session's notes on this machine."
NEXT_SOURCE = {"agenda": "from the agenda", "map": "from your topic map", "design order": "the next section of the design"}
NONE_NEXT = "Say *what's next* to hear vela's suggestion."


def with_renders(data):
    """The dict with its band and its diagram's drawings filled in, so the JSON carries what the surfaces show."""
    if data.get("kind") == "session":
        data["band"] = band(data)
        diagram = data.get("diagram")
        if diagram:
            diagram["svg"] = companionsvg.sequence(diagram["steps"], diagram["name"])
            diagram["text"] = companionsvg.text_of(diagram["steps"])
    return data


def time_of(data):
    return data["as_of"].split("T")[-1]


def header_line(data):
    return f"as of {time_of(data)} · capture {data['capture']}"


def count_words(data):
    return len(data["decided"] or ()), len(data["open"] or ())


def short(text, limit):
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def band(data):
    """One line for a narrow window: "Grill: hold, pay, confirm · 2 decided · 1 open · next: Pricing runtime · /vela-companion to open"."""
    title = data["session"]["title"]
    if data["notes"] == "unreadable":
        middle = "notes can't be read here"
    else:
        decided, opened = count_words(data)
        middle = f"{decided} decided · {opened} open"
        if data["next"]["text"]:
            middle += " · next: " + data["next"]["text"].split(" (vela's")[0]
    tail = f" · {OPEN_HINT}"
    room = BAND_WIDTH - len(tail)
    head = f"{title} · {middle}"
    if len(head) > room:
        head = short(title, 30) + " · " + short(middle, room - len(short(title, 30)) - 3)
    return head + tail


def next_lines(data):
    move = data["next"]
    if not move["text"]:
        return [NONE_NEXT]
    lines = [move["text"]]
    source = NEXT_SOURCE.get(move["source"], "")
    if source:
        more = f" · {move['left_after']} left after it" if move["left_after"] else ""
        hint = " · say *next* to go on" if move["source"] == "agenda" else ""
        lines.append(source + more + hint)
    return lines


def open_line(row):
    bits = [row["name"]]
    if row.get("who"):
        bits.append(row["who"])
    bits.append("new this session" if row.get("new_this_session") and not row["open_days"] else
                f"{row['open_days']} days" if row["open_days"] else "")
    return " · ".join(b for b in bits if b)


def yes_line(row):
    held = f"held by {row['blocked_by']}" + (f" ({row['who']})" if row["who"] else "") if row["blocked_by"] else ""
    return " · ".join(b for b in (row["name"], held) if b)


def session_sections(data):
    """[(title, count or None, [lines])] in the order the panels show them, shared by Markdown and HTML."""
    sections = []
    decided = data["decided"]
    sections.append(("Decided this session", len(decided),
                     [f"{row['name']} · {row['label']}" for row in decided] or ["Nothing decided yet."]))
    if data["said_yes"]:
        sections.append(("Said yes, waiting", len(data["said_yes"]), [yes_line(row) for row in data["said_yes"]]))
    sections.append(("Still open", len(data["open"]), [open_line(row) for row in data["open"]] or ["Nothing open."]))
    sections.append(("Next", None, next_lines(data)))
    if data["touched"] is not None:
        sections.append(("Pages changed", len(data["touched"]), [row["name"] for row in data["touched"]] or ["None yet."]))
    return sections


def explain_header(data):
    day = data["copy"]["made"]["date"]
    return f"copy of {say.date_words(day, datetime.date.fromisoformat(data['as_of']))}"


def item_line(view, item, today):
    """One item as a plain line; "" for a totals row (its numbers are in the headline)."""
    if item["id"] == "total":
        return ""
    bits = [item["name"]]
    if view == "flow":
        return f"{item['id']}. {item['name']}"
    if view in ("stuck", "who"):
        if item.get("who") and view == "stuck":
            bits.append(item["who"])
        if item.get("open_days") is not None:
            bits.append(f"{item['open_days']} days")
        if item.get("ask_by"):
            bits.append("ask by " + say.date_words(item["ask_by"], today))
        if item.get("holds"):
            bits.append("holds " + ", ".join(item["holds"]))
    elif view == "needs" and item.get("date"):
        bits.append("by " + say.date_words(item["date"], today))
    elif view == "left":
        bits.append(f"{item['decided']} of {item['total']} decided")
    elif view == "track":
        bits.append(item.get("status") or ("due " + item["target"] if item.get("target") else ""))
    return " \u00b7 ".join(b for b in bits if b)


def explain_blocks(data):
    """[(heading or "", [lines])]: the groups when the view has them, else the items; never the page's own opening."""
    view, today = data["view"], datetime.date.fromisoformat(data["as_of"])
    if view in ("none", "page"):
        return []
    if data["groups"]:
        return [(g["who"], [item_line(view, i, today) for i in g["items"]]) for g in data["groups"]]
    lines = [line for line in (item_line(view, i, today) for i in data["items"]) if line]
    return [("", lines)] if lines else []


def explain_markdown(data):
    out = [f"**{data['copy']['title']}**   {explain_header(data)}", ""]
    out += [*data["headline"], ""]
    if data["since"]:
        out += [data["since"], ""]
    for heading, lines in explain_blocks(data):
        if heading:
            out.append(f"**{heading}**")
        out += [f"- {line}" for line in lines]
        out.append("")
    if data["diagram"] and data["diagram"]["text"]:
        out += ["    " + line for line in data["diagram"]["text"].split("\n")] + [""]
    out += [*data["not_recorded"]]
    out += [f"Full picture: {data['dashboard']} in this folder", ""]
    out += [f"Note: {w}" for w in data["warnings"]]
    return "\n".join(out).rstrip("\n") + "\n"


def markdown(data):
    if data["kind"] == "explain":
        return explain_markdown(data)
    title = data["session"]["title"]
    out = [f"**{title}**   {header_line(data)}", ""]
    if data["notes"] == "unreadable":
        return "\n".join(out + [UNREADABLE] + [""] + [f"Note: {w}" for w in data["warnings"]] + [""]) .rstrip("\n") + "\n"
    out += [data["about"] or "No summary yet", ""]
    for name, count, lines in session_sections(data):
        out.append(f"**{name}**" + (f" ({count})" if count is not None else ""))
        out += [("  " if name == "Next" else "- ") + line for line in lines]
        out.append("")
    if data["diagram"]:
        out += [f"**{data['diagram']['name']}, as decided**", ""]
        out += ["    " + line for line in data["diagram"]["text"].split("\n")]
        out.append("")
    out += [f"Note: {w}" for w in data["warnings"]]
    out += [DASHBOARD_LINE, ""]
    return "\n".join(out)


STYLE = """body{margin:0;background:var(--room);color:var(--ink);font:14px/1.45 system-ui,sans-serif}
main{padding:16px 18px;max-width:420px}h1{font-size:15px;margin:0 0 2px}.asof{color:var(--ink-3);font-size:12px}
.about{color:var(--ink-2);margin:8px 0 12px}h2{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin:14px 0 4px}
ul{list-style:none;margin:0;padding:0}li{padding:3px 0}.next{background:var(--deck-2);border-left:3px solid var(--unexamined);padding:6px 10px;border-radius:4px}
.sub{color:var(--ink-3);font-size:12px}.note{color:var(--caution-text);font-size:12px}.lead{font-size:22px;font-weight:600;margin:10px 0 2px}.since{color:var(--diff-add);font-size:13px}footer{color:var(--ink-3);font-size:12px;margin-top:14px}
svg{max-width:100%;height:auto}"""


def emphasis(text):
    """*word* as <em>word</em> in text already escaped: the only markup the panel's own sentences use."""
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escape(text))


def html_list(lines, css=""):
    return "<ul>" + "".join(f"<li{css}>{escape(line)}</li>" for line in lines) + "</ul>"


def inline(svg):
    """The SVG as inline HTML needs it: the namespace is implied there, and a page with no web address in it is one a
    reader can check holds no outside reference."""
    return svg.replace(' xmlns="http://www.w3.org/2000/svg"', "")


def explain_html(data, palette):
    body = [f"<h1>{escape(data['copy']['title'])}</h1><div class=\"asof\">{escape(explain_header(data))}</div>"]
    body += [f"<p class=\"{'lead' if n == 0 else 'about'}\">{escape(line)}</p>" for n, line in enumerate(data["headline"])]
    if data["since"]:
        body.append(f"<p class=\"since\">{escape(data['since'])}</p>")
    for heading, lines in explain_blocks(data):
        body.append((f"<h2>{escape(heading)} ({len(lines)})</h2>" if heading else "") + html_list(lines))
    if data["diagram"]:
        body.append(inline(data["diagram"]["svg"]))
    body += [f"<p class=\"note\">{escape(line)}</p>" for line in data["not_recorded"]]
    body += [f"<p class=\"note\">{escape(w)}</p>" for w in data["warnings"]]
    body.append(f"<footer>{escape('Full picture: ' + data['dashboard'] + ' in this folder')}</footer>")
    return (f"<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">"
            f"<title>{escape(data['copy']['title'])}</title><style>{palette}\n{STYLE}</style><body><main>"
            + "".join(body) + "</main></body></html>\n")


def html(data, palette):
    if data["kind"] == "explain":
        return explain_html(data, palette)
    body = [f"<h1>{escape(data['session']['title'])}</h1><div class=\"asof\">{escape(header_line(data))}</div>"]
    if data["notes"] == "unreadable":
        body.append(f"<p>{escape(UNREADABLE)}</p>")
    else:
        body.append(f"<p class=\"about\">{escape(data['about'] or 'No summary yet')}</p>")
        for name, count, lines in session_sections(data):
            heading = escape(name) + (f" ({count})" if count is not None else "")
            if name == "Next":
                body.append(f"<h2>{heading}</h2><div class=\"next\">{emphasis(lines[0])}"
                            + "".join(f"<div class=\"sub\">{emphasis(line)}</div>" for line in lines[1:]) + "</div>")
            else:
                body.append(f"<h2>{heading}</h2>" + html_list(lines))
        if data["diagram"]:
            body.append(f"<h2>{escape(data['diagram']['name'])}, as decided</h2>{inline(data['diagram']['svg'])}")
    body += [f"<p class=\"note\">{escape(w)}</p>" for w in data["warnings"]]
    body.append(f"<footer>{escape(DASHBOARD_LINE)}</footer>")
    return (f"<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">"
            f"<title>{escape(data['session']['title'])}</title><style>{palette}\n{STYLE}</style><body><main>"
            + "".join(body) + "</main></body></html>\n")
