"""The companion page: the blocks (`companionblocks.py`) drawn as one self-contained HTML document. Pure.

The Violation this exists to prevent is a Leaky Narrative at the page: if it chose its own marks, colors or wording per
panel, the page would drift from the terminal pane. So it draws only what the blocks say: a block's tone is mapped to
the dashboard palette's variables in one table (`TONES`), and nothing else here knows what a "stuck" row is. A second
Violation is an Infected Core in the other direction: vault text reaches the page only through `escape`/`attr`, and the
page holds no script and no outside reference, so nothing a plan says can run or call out. Fold toggles are plain
`<details>`; nothing here sends anything back to Claude (owner's ruling of October 24, 2026).
"""
from html import escape as _escape

from vela import companionblocks

# tone -> (text color, chip background, chip ink): every color is a variable of the dashboard's palette
TONES = {
    "plain": ("--ink", "--deck-3", "--ink"),
    "dim": ("--ink-3", "--deck-3", "--ink-2"),
    "strong": ("--ink", "--deck-3", "--ink"),
    "info": ("--unexamined-text", "--unexamined", "--unexamined-ink"),
    "good": ("--diff-add", "--diff-add", "--room"),
    "warn": ("--caution-text", "--caution", "--caution-ink"),
    "bad": ("--warning-text", "--warning", "--warning-ink"),
    "accent": ("--caution-text", "--caution", "--caution-ink"),
    "new": ("--pending-text", "--pending", "--pending-ink"),
    "id": ("--unexamined-text", "--deck-3", "--unexamined-text"),
}


def escape(text):
    """Text for an HTML text node: markup is escaped; quotes are safe there and stay readable."""
    return _escape(str(text), quote=False)


def attr(text):
    """Text for a double-quoted attribute value."""
    return _escape(str(text), quote=True)


def style():
    rules = [f".t-{tone}{{color:var({ink})}}.c-{tone}{{background:var({back});color:var({chip})}}"
             f".box-{tone}{{border-color:var({ink})}}.fill-{tone}{{background:var({ink})}}"
             for tone, (ink, back, chip) in TONES.items()]
    return STYLE + "\n" + "\n".join(rules)


STYLE = """body{margin:0;color-scheme:dark;background:var(--room);color:var(--ink);font:14px/1.45 system-ui,sans-serif}
main{padding:14px 16px 18px;max-width:440px}
.t-strong,.strong{font-weight:600}.id{font:12px var(--mono,ui-monospace,monospace)}
.card{border:1px solid;border-radius:8px;padding:8px 12px;margin:0 0 12px;background:var(--room-2)}
.card header{display:flex;justify-content:space-between;gap:12px;align-items:baseline;margin-bottom:4px}
.card .title{font-size:15px;margin:0;font-weight:600;letter-spacing:0;text-transform:none;color:var(--ink)}.right{color:var(--ink-3);font-size:12px;white-space:nowrap}
.line{min-height:1.2em}.bar{display:inline-block;vertical-align:middle;width:140px;height:8px;border-radius:2px;background:var(--deck-3);overflow:hidden}
.bar i{display:block;height:100%}
.chip{display:inline-block;font-size:11px;font-weight:700;padding:0 7px;border-radius:9px;margin-left:6px;white-space:nowrap}
.next{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 8px;background:var(--deck-2);border-radius:6px;padding:7px 10px;margin:0 0 12px}
.next .chip{margin:0;border-radius:3px}.next .note{flex-basis:100%}
details{margin:0 0 12px}summary{cursor:pointer;font-weight:600;padding:2px 0;border-bottom:1px solid var(--rule)}
summary .count{color:var(--ink-3);font-weight:400;margin-left:4px}
.row{display:flex;gap:8px;padding:3px 0 3px 4px}.mark{flex:0 0 1.2em;text-align:center}.what{min-width:0}
.id{color:var(--unexamined-text);margin-left:6px}.note,.sub{color:var(--ink-3)}.note{margin-left:6px}.sub{display:block;font-size:12px}
.dimmed{color:var(--ink-3)}.page{text-decoration:underline dotted;text-underline-offset:2px}.page.plainpage{text-decoration:none}
h2{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin:0 0 4px}
.bars{margin:0 0 12px}.brow{display:grid;grid-template-columns:minmax(0,9em) 1fr auto;gap:8px;align-items:center;padding:2px 0}
.brow .bar{width:100%}.label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
figure{margin:0 0 12px;overflow-x:auto}svg{max-width:none}  /* why: step words are 11 px at the SVG's own width; shrinking it to the panel makes them unreadable */
.foot{color:var(--ink-3);font-size:12px;margin-top:14px}"""


def tone_of(tone):
    return tone if tone in TONES else "plain"


def page_name(page, body):
    """A page name, with its path on hover. Not a link: the panel is also published to Cowork, where a path into the
    vault leads nowhere, and a link that goes nowhere is worse than none. The dotted underline says "hover me", so the
    dashboard line, which is a file beside the panel and not a vault page, goes without it."""
    plain = " plainpage" if page.startswith("dashboard.html") else ""
    return f"<span class=\"page{plain}\" title=\"{attr(page)}\">{body}</span>"


def span_html(piece):
    if "bar" in piece:
        done, total = piece["bar"]
        share = round(100 * done / total) if total else 0
        return f"<span class=\"bar\"><i class=\"fill-good\" style=\"width:{share}%\"></i></span>"
    body = f"<span class=\"t-{tone_of(piece['tone'])}\">{escape(piece['t'])}</span>"
    return page_name(piece["page"], body) if piece.get("page") else body


def line_html(line):
    return "<div class=\"line\">" + "".join(span_html(piece) for piece in line) + "</div>"


def card_html(block):
    right = f"<span class=\"right\">{escape(block['right'])}</span>" if block["right"] else ""
    return (f"<section class=\"card box-{tone_of(block['tone'])}\"><header><h2 class=\"title\">{escape(block['title'])}</h2>{right}</header>"
            + "".join(line_html(line) for line in block["lines"]) + "</section>")


def next_html(block):
    ident = f"<span class=\"id\">{escape(block['id'])}</span>" if block["id"] else ""
    note = f"<span class=\"note\">{escape(block['note'])}</span>" if block["note"] else ""
    return (f"<div class=\"next\"><span class=\"chip c-accent\">&#9654; {escape(block['chip'])}</span>"
            f"<span class=\"strong t-accent\">{escape(block['text'])}</span>{ident}{note}</div>")


def chip_html(chip):
    return f"<span class=\"chip c-{tone_of(chip['tone'])}\">{escape(chip['t'])}</span>"


def row_html(row):
    tone = tone_of(row["tone"])
    name = escape(row["name"])
    name = page_name(row["page"], name) if row["page"] else name
    name = f"<span class=\"dimmed\">{name}</span>" if tone == "dim" else name
    bits = [name]
    if row["id"]:
        bits.append(f"<span class=\"id\">{escape(row['id'])}</span>")
    if row["note"]:
        bits.append(f"<span class=\"note\">{escape(row['note'])}</span>")
    if row["chip"]:
        bits.append(chip_html(row["chip"]))
    if row["sub"]:
        bits.append("<span class=\"sub\">" + "".join(span_html(piece) for piece in row["sub"]) + "</span>")
    return (f"<div class=\"row\"><span class=\"mark t-{tone}\">{escape(row['mark'])}</span>"
            f"<span class=\"what\">{' '.join(bits)}</span></div>")


def section_html(block):
    rows = "".join(row_html(row) for row in block["rows"])
    if not block["title"]:
        return f"<div class=\"rows\">{rows}</div>"
    count = f"<span class=\"count\">{escape(block['count'])}</span>" if block["count"] else ""
    return f"<details open><summary>{escape(block['title'])} {count}</summary>{rows}</details>"


def bars_html(block):
    rows = []
    for item in block["rows"]:
        share = round(100 * item["value"] / item["max"]) if item["max"] else 0
        rows.append(f"<div class=\"brow\"><span class=\"label\">{escape(item['label'])}</span>"
                    f"<span class=\"bar\"><i class=\"fill-{tone_of(item['tone'])}\" style=\"width:{share}%\"></i></span>"
                    f"<span class=\"t-dim\">{escape(item['text'])}</span></div>")
    return f"<div class=\"bars\"><h2>{escape(block['title'])}</h2>{''.join(rows)}</div>"


def inline(svg):
    """The SVG as inline HTML needs it: the namespace is implied there, and a page with no web address in it is one a
    reader can check holds no outside reference."""
    return svg.replace(' xmlns="http://www.w3.org/2000/svg"', "")


def diagram_html(block, svg):
    """The picture carries its own label (role=img, aria-label); a second one on the figure would be read twice, and the
    block's `alt` is for the Svg element and the terminal."""
    return f"<figure><h2>{escape(block['title'])}</h2>{inline(svg)}</figure>"


def lines_html(block):
    return "<div class=\"foot\">" + "".join(line_html(line) for line in block["lines"]) + "</div>"


def block_html(block, data):
    kind = block["type"]
    if kind == "diagram":
        return diagram_html(block, data["diagram"]["svg"])
    drawn = {"card": card_html, "next": next_html, "section": section_html, "bars": bars_html, "lines": lines_html}
    return drawn[kind](block)


def title_of(data):
    return companionblocks.explain_title(data) if data["kind"] == "explain" else data["session"]["title"]


def page(data, palette):
    blocks = data["blocks"]
    return (f"<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">"
            f"<title>{escape(title_of(data))}</title><style>{palette}\n{style()}</style><body><main>"
            + "".join(block_html(block, data) for block in blocks) + "</main></body></html>\n")
