"""The companion panels as blocks: a small closed vocabulary of layout pieces whose every word and tone comes from here. Pure.

The Violation this exists to prevent is a Distributed Monolith of look and wording: the terminal mod, the desktop pane
and the Cowork page each deciding for themselves what a "stuck" row is called, what color it has and what mark it
carries. So vela decides all of it once, here, and the three drawers only map blocks to their own elements. A second
Violation is a Leaky Narrative at the drawer: if the mod had to be told "this is a session" or "this view is stuck" to
pick a mark, the mark would be the mod's rule. A row carries its own mark and tone, so no drawer chooses one.

The block contract (binding for the mod and the page, which read it):

  Span  {"t": str, "tone": Tone}            optional "page": a vault-relative path, drawn as a link
  Line  [Span | {"bar": [done, total]}]     a bar item is 20 cells: the done share in "good", the rest "dim"
  Tone  plain dim strong info good warn bad accent new id
  Block card | next | section | bars | diagram | lines     (see the builders below for each one's keys)
"""
import datetime
import re

from vela import companionchart, say

BAND_WIDTH = 100  # why: the band shows below 110 columns, beside the prompt's own margins
OPEN_HINT = "/vela-companion to open"
DASHBOARD_LINE = "Full dashboard: dashboard.html in this folder"
UNREADABLE = "I can't read this session's notes on this machine."
NO_SUMMARY = "No summary yet"
NONE_NEXT = "Say what's next to hear vela's suggestion."
NOTHING_DECIDED, NOTHING_OPEN = "Nothing decided yet.", "Nothing open."
TITLE_DECIDED, TITLE_WAITING, TITLE_OPEN = "Decided this session", "Yes given, waiting", "Open questions"
NEXT_SOURCE = {"agenda": "from the agenda", "map": "from your topic map", "design order": "the next section of the design"}
STALE_DAYS = 14  # why: a question that has waited two weeks is stuck, not merely open
MORE_PAGES = 6   # pages listed under "Pages changed" before the rest is counted

VIEW_QUESTION = {"track": "When is it due?", "stuck": "What's stuck?", "needs": "What do you need from me?",
                     "left": "What's left?", "who": "Who holds what?"}
ALSO_ASK = {"track": "when is it due?", "stuck": "what's stuck?", "needs": "what do you need from me?",
            "left": "what's left?", "who": "who holds what?"}  # never "on track": the plan can't say that (a Paper Tiger)
ALSO_ORDER = ("stuck", "needs", "left", "who", "track")


def span(text, tone="plain", page=None):
    found = {"t": str(text), "tone": tone}
    if page:
        found["page"] = page
    return found


def bar(done, total):
    return {"bar": [done, total]}


def plain_line(text, tone="plain"):
    return [span(text, tone)]


def count_words(n, one, many):
    return f"{n} {one if n == 1 else many}"


def days_chip(days):
    return {"t": count_words(days, "day", "days"), "tone": "bad" if days >= STALE_DAYS else "warn"}


def row(mark, tone, name, ident="", note="", chip=None, sub=None, page=None):
    return {"mark": mark, "tone": tone, "name": name, "id": ident, "note": note, "chip": chip, "sub": sub, "page": page}


def card(title, right, tone, lines):
    return {"type": "card", "title": title, "right": right, "tone": tone, "lines": lines}


def section(key, title, count, rows):
    return {"type": "section", "key": key, "title": title, "count": count, "rows": rows}


def lines_block(lines):
    return {"type": "lines", "lines": lines}


def warning_lines(data):
    return [plain_line(w, "warn") for w in data["warnings"]]


def time_of(data):
    return data["as_of"].split("T")[-1]


def short(text, limit):
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


# --- the one-line band -------------------------------------------------------------------------------------------

def fit_middle(spans, room):
    """The spans cut to `room` characters in all, the last one kept shortened with an ellipsis."""
    out, used = [], 0
    for item in spans:
        if used + len(item["t"]) <= room:
            out.append(item)
            used += len(item["t"])
            continue
        left = room - used
        if left > 0:
            out.append({**item, "t": short(item["t"], left)})
        break
    return out


def session_band(data):
    title = data["session"]["title"]
    dim = lambda text: span(text, "dim")
    if data["notes"] == "unreadable":
        middle = [span("notes can't be read here", "warn")]
    else:
        middle = [span(f"{len(data['decided'] or ())} decided", "good"), dim(" · "),
                  span(f"{len(data['open'] or ())} open", "new")]
        if data["next"]["text"]:
            middle += [dim(" · next: "), span(suggestion_split(data["next"]["text"])[0], "accent")]
    tail = dim(f" · {OPEN_HINT}")
    head = [span(title, "strong"), dim(" · ")]
    room = BAND_WIDTH - len(tail["t"])
    if len(title) + 3 + sum(len(s["t"]) for s in middle) > room:
        head = [span(short(title, 30), "strong"), dim(" · ")]
        return head + fit_middle(middle, room - len(short(title, 30)) - 3) + [tail]
    return head + middle + [tail]


def explain_band(data):
    title = explain_title(data)
    first = data["headline"][0] if data["headline"] else ""
    tone = "bad" if is_stuck(data) else "plain"
    head = [span(short(title, 30), "strong"), span(" · ", "dim")]
    return head + fit_middle([span(first, tone)], BAND_WIDTH - len(short(title, 30)) - 3)


def band_spans(data):
    return explain_band(data) if data["kind"] == "explain" else session_band(data)


# --- the session panel -------------------------------------------------------------------------------------------

def capture_words(n):
    return count_words(n, "note", "notes")


def agenda_line(agenda):
    done = sum(1 for item in agenda if item["status"] == "decided")
    return [span("Agenda  "), bar(done, len(agenda)), span(f"  {done} of {len(agenda)} done", "dim")]


def session_card(data):
    lines = [plain_line(data["about"] or NO_SUMMARY, "dim")]
    if data["agenda"]:
        lines.append(agenda_line(data["agenda"]))
    return card(data["session"]["title"], f"{capture_words(data['capture'])} · {time_of(data)}", "info", lines)


SUGGESTION = re.compile(r"^(.*?) \((vela's suggestion[^)]*)\)$")


def suggestion_split(text):
    """(the move, vela's own note about it): "Pricing (vela's suggestion as of October 24)" -> two parts; no note, "" ."""
    found = SUGGESTION.match(text)
    return (found.group(1), found.group(2)) if found else (text, "")


def next_note(move):
    """The line under the next move: where it came from and what follows it. "" when vela has nothing to say."""
    if move["source"] == "agenda":
        return "last item on the agenda" if not move["left_after"] else f"{NEXT_SOURCE['agenda']} · {move['left_after']} left after it"
    if move["source"] == "vela":
        return suggestion_split(move["text"])[1]
    source = NEXT_SOURCE.get(move["source"], "")
    return f"{source} · {move['left_after']} left after it" if source and move["left_after"] else source


def next_block(data):
    move = data["next"]
    if not move["text"]:
        return {"type": "next", "chip": "NEXT", "text": NONE_NEXT, "id": "", "note": ""}
    return {"type": "next", "chip": "NEXT", "text": suggestion_split(move["text"])[0], "id": move["id"], "note": next_note(move)}


def decided_row(item):
    return row("✔", "good", item["name"], item["id"], f"was {item['from']}" if item["from"] else "", page=item["page"] or None)


def waiting_row(item):
    holder = [span("held by ", "dim"), span(item["blocked_by"])] if item["blocked_by"] else []
    if item["blocked_by"] and item["who"]:
        holder.append(span(f" · {item['who']}", "dim"))
    return row("◷", "warn", item["name"], item["id"], sub=holder or None)


def open_row(item):
    fresh = item["new_this_session"] and not item["open_days"]
    note = " · ".join(bit for bit in (item["who"], "" if fresh else (count_words(item["open_days"], "day", "days") if item["open_days"] else "")) if bit)
    return row("?", "new", item["name"], item["id"], note, chip={"t": "NEW", "tone": "new"} if fresh else None)


def nothing_row(text):
    return row("", "dim", text)


def session_sections(data):
    decided = [decided_row(i) for i in data["decided"]] or [nothing_row(NOTHING_DECIDED)]
    found = [section("decided", TITLE_DECIDED, str(len(data["decided"])), decided)]
    if data["said_yes"]:
        found.append(section("waiting", TITLE_WAITING, str(len(data["said_yes"])), [waiting_row(i) for i in data["said_yes"]]))
    opened = [open_row(i) for i in data["open"]] or [nothing_row(NOTHING_OPEN)]
    found.append(section("open", TITLE_OPEN, str(len(data["open"])), opened))
    return found


def diagram_block(diagram):
    """The flow drawn as characters at each width the pane can have, or None when the diagram is not a flow."""
    if not diagram or diagram["kind"] != "sequence":
        return None
    steps = diagram["steps"]
    return {"type": "diagram", "title": f"Flow: {diagram['name']}", "id": diagram["of"], "alt": flow_alt(diagram),
            "drawings": {str(w): companionchart.drawing(steps, w) for w in companionchart.WIDTHS}}


def flow_alt(diagram):
    """What the picture says in words, including which apps a narrow drawing folds together."""
    steps = diagram["steps"]
    said = f"{diagram['name']}: {count_words(len(steps), 'step', 'steps')}."
    for width in companionchart.WIDTHS:
        folded = companionchart.folded_lanes(steps, width)
        if folded:
            said += f" At {width} columns {', '.join(folded)} are shown together as one lane, \"{companionchart.OTHERS}\"."
    return said


def pages_changed(touched):
    """The "Pages changed" lines: one line for a couple of pages, one per page after that."""
    if touched is None:
        return []
    if not touched:
        return [[span("Pages changed  ", "dim"), span("None yet.")]]
    entries = [[span(p["name"], "info", page=p["page"]), span(f" {p['change']}", "dim")] for p in touched]
    if len(entries) <= 2:
        joined = entries[0] + [piece for entry in entries[1:] for piece in [span(" · ", "dim")] + entry]
        return [[span("Pages changed  ", "dim")] + joined]
    lines = [[span("Pages changed", "dim")]] + [[span("  ")] + entry for entry in entries[:MORE_PAGES]]
    if len(entries) > MORE_PAGES:
        lines.append([span(f"  + {len(entries) - MORE_PAGES} more", "dim")])
    return lines


def session_blocks(data):
    if data["notes"] == "unreadable":
        return [card(data["session"]["title"], "", "warn", [plain_line(UNREADABLE)]), lines_block(warning_lines(data))]
    blocks = [session_card(data), next_block(data), *session_sections(data)]
    drawn = diagram_block(data["diagram"])
    if drawn:
        blocks.append(drawn)
    blocks.append(lines_block(pages_changed(data["touched"]) + warning_lines(data) + [plain_line(DASHBOARD_LINE, "dim")]))
    return blocks


# --- the explain panel -------------------------------------------------------------------------------------------

def is_stuck(data):
    return data["view"] == "stuck" and bool(data["items"])


def explain_title(data):
    """The question the view answers, in the words a person asks it; the plan's own title for views that are not one."""
    if data["view"] in VIEW_QUESTION:
        return VIEW_QUESTION[data["view"]]
    if data["view"] == "flow" and data["diagram"]:
        return data["diagram"]["name"]
    if data["view"] == "page" and data["items"]:
        return data["items"][0]["name"]
    return data["copy"]["title"]


def explain_date(data):
    return say.date_words(data["copy"]["made"]["date"], datetime.date.fromisoformat(data["as_of"]))


def viewer_words(viewer):
    """"as the director" when the reader's role is known. Never the handle: a GitHub name in lead-facing text is a leak."""
    return f"as the {viewer['role']}" if viewer["role"] else ""


def explain_card(data):
    lines = [[span(data["copy"]["title"], "strong"), span(f"  · copy of {explain_date(data)}", "dim")]]
    lines += [plain_line(line, "strong") for line in data["headline"]]
    if data["since"]:
        lines.append(plain_line(data["since"], "good"))
    return card(explain_title(data), viewer_words(data["viewer"]), "bad" if is_stuck(data) else "info", lines)


def date_of(value, data):
    return say.date_words(value, datetime.date.fromisoformat(data["as_of"]))


def asked_row(item, data, mark, tone):
    """A question someone holds: how long it has waited, the apps it holds up and when the answer is wanted."""
    days = item.get("open_days")
    chip = days_chip(days) if days is not None else None
    bits = []
    if item.get("holds"):
        bits.append(f"{', '.join(item['holds'])} holds")
    if item.get("ask_by"):
        bits.append("ask by " + date_of(item["ask_by"], data))
    return row(mark, chip["tone"] if chip and mark == "■" else tone, item["name"], chip=chip,
               sub=[span(" · ".join(bits), "dim")] if bits else None)


def view_row(data, item):
    """The row for one item of the view, or None for an item the headline already carries (totals)."""
    view = data["view"]
    if item["id"] == "total":
        return None
    if view == "stuck":
        return asked_row(item, data, "■", "warn")
    if view == "who":
        return asked_row(item, data, "?", "new")
    if view == "needs":
        return row("●", "info", item["name"], note="by " + date_of(item["date"], data) if item.get("date") else "")
    if view == "left":
        return row("○", "dim", item["name"], note=f"{item['decided']} of {item['total']} decided")
    if view == "track":
        note = item.get("status") or ("due " + date_of(item["target"], data) if item.get("target") else "")
        return row("○", "dim", item["name"], note=note)
    return None


def explain_sections(data):
    if data["view"] in ("none", "page", "flow"):
        return []  # a flow's steps are the drawing; the others have no items to list
    if data["groups"]:
        return [section(f"group:{g['who']}", g["who"], str(len(g["items"])),
                        [r for r in (view_row(data, i) for i in g["items"]) if r]) for g in data["groups"]]
    rows = [r for r in (view_row(data, i) for i in data["items"]) if r]
    return [section("items", "", "", rows)] if rows else []


def bars_block(data):
    """A bar per holder, per app or per person when the view has two or more numbers worth comparing, else None."""
    view, items = data["view"], [i for i in data["items"] if i["id"] != "total"]
    if view == "stuck":
        waited = [i for i in items if i.get("open_days") is not None]
        if len(waited) < 2:
            return None
        oldest = {}
        for g in data["groups"]:
            days = [i["open_days"] for i in g["items"] if i.get("open_days") is not None]
            if days:
                oldest[g["who"]] = max(days)
        top = max(oldest.values(), default=1) or 1
        rows = [{"label": who, "value": days, "max": top, "tone": days_chip(days)["tone"], "text": str(days)}
                for who, days in oldest.items()]
        return {"type": "bars", "title": "Waiting, by days", "rows": rows}
    if view == "left" and len(items) >= 2:
        rows = [{"label": i["name"], "value": i["decided"], "max": max(i["total"], 1), "tone": "good",
                 "text": f"{i['decided']} of {i['total']}"} for i in items]
        return {"type": "bars", "title": "Decided, by app", "rows": rows}
    if view == "who" and len(items) >= 2:
        top = max((len(g["items"]) for g in data["groups"]), default=1)
        rows = [{"label": g["who"], "value": len(g["items"]), "max": top, "tone": "new", "text": str(len(g["items"]))}
                for g in data["groups"]]
        return {"type": "bars", "title": "Open questions, by person", "rows": rows}
    return None


def also_ask_line(data):
    views = [v for v in ALSO_ORDER if v in data.get("also", ())]
    if not views:
        return None
    line = [span("Also ask  ", "dim")]
    for n, view in enumerate(views):
        line += [span(" · ", "dim")] if n else []
        line.append(span(ALSO_ASK[view], "info"))
    return line


def explain_blocks(data):
    blocks = [explain_card(data), *explain_sections(data)]
    bars = bars_block(data)
    if bars:
        blocks.append(bars)
    drawn = diagram_block(data["diagram"])
    if drawn:
        blocks.append(drawn)
    if data["not_recorded"]:
        blocks.append(card("Not in the plan", "", "dim", [plain_line(line, "dim") for line in data["not_recorded"]]))
    tail = [also_ask_line(data), [span("Full picture  ", "dim"), span(data["dashboard"], "info", page=data["dashboard"])]]
    blocks.append(lines_block([line for line in tail if line] + warning_lines(data)))
    return blocks


def blocks_of(data):
    return explain_blocks(data) if data["kind"] == "explain" else session_blocks(data)
