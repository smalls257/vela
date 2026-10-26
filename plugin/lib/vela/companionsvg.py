"""Two small SVG shapes the companion panels draw, and the terminal's text rendition of a flow. Pure.

The design suggested Mermaid inside the Cowork artifact. vela's Mermaid bundle is 3.2 MB and the panel is republished
after every write, so that would be Computational Friction on the chat path. These shapes are a few KB, the same SVG
the desktop pane's `Svg` element takes, and every vault string in them is escaped: the vault is untrusted input, so no
script, no event attribute and no external reference can come out of here.
"""
import re
from xml.sax.saxutils import escape

MAX_CHARS = 131_072  # the desktop Svg element's limit (mods reference, Elements)
MAX_STEPS = 12
LANE_WIDTH, ROW_HEIGHT, TOP = 150, 34, 46
WIKILINK = re.compile(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]")
LIGHT_FILL = {"warning": "#ff5a48", "caution": "#ffb21e", "unexamined": "#52c8ff", "dark": "#2a3236", "": "#2a3236"}


def label(text, limit=34):
    """A vault phrase as a short plain label: links as their words, markup and a trailing parenthesis dropped."""
    text = WIKILINK.sub(lambda m: m.group(2) or m.group(1), str(text or ""))
    text = re.sub(r"\([^)]*\)\s*$", "", text.replace("**", "").replace("`", ""))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _first_sentence(text):
    return label(re.split(r"(?<=[.!?])\s", WIKILINK.sub(lambda m: m.group(2) or m.group(1), str(text or "")))[0], 44)


def _lanes(steps):
    lanes = []
    for step in steps:
        for end in (step.get("from", ""), step.get("to", "")):
            name = label(end)
            if name and name not in lanes:
                lanes.append(name)
    return lanes[:6]


def sequence(steps, title):
    shown, more = steps[:MAX_STEPS], max(0, len(steps) - MAX_STEPS)
    lanes = _lanes(shown) or [""]
    width = max(320, LANE_WIDTH * len(lanes))
    height = TOP + ROW_HEIGHT * (len(shown) + (1 if more else 0)) + 12
    x = {name: LANE_WIDTH // 2 + n * LANE_WIDTH for n, name in enumerate(lanes)}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
           f'role="img" aria-label="{escape(label(title, 80), {chr(34): "&quot;"})}" font-family="system-ui,sans-serif" font-size="11">']
    for name, cx in x.items():
        if name:
            out.append(f'<rect x="{cx - 60}" y="4" width="120" height="22" rx="4" fill="#1b2830" stroke="#34475a"/>'
                       f'<text x="{cx}" y="19" text-anchor="middle" fill="#e8eef0">{escape(name)}</text>'
                       f'<line x1="{cx}" y1="26" x2="{cx}" y2="{height - 6}" stroke="#34475a" stroke-dasharray="3 3"/>')
    for row, step in enumerate(shown):
        y = TOP + row * ROW_HEIGHT
        sender, receiver = label(step.get("from", "")), label(step.get("to", ""))
        words = escape(_first_sentence(step.get("text", "")))
        if sender in x and receiver in x and sender != receiver:
            a, b = x[sender], x[receiver]
            head = f"{b - 6},{y - 4} {b},{y} {b - 6},{y + 4}" if b > a else f"{b + 6},{y - 4} {b},{y} {b + 6},{y + 4}"
            out.append(f'<line x1="{a}" y1="{y}" x2="{b}" y2="{y}" stroke="#5b9bff"/><polyline points="{head}" fill="none" stroke="#5b9bff"/>'
                       f'<text x="{min(a, b) + 6}" y="{y - 6}" fill="#b7c4c9">{words}</text>')
        else:
            out.append(f'<rect x="8" y="{y - 12}" width="{width - 16}" height="22" rx="4" fill="#152027" stroke="#34475a"/>'
                       f'<text x="16" y="{y + 3}" fill="#b7c4c9">{step.get("n", row + 1)}. {words}</text>')
    if more:
        out.append(f'<text x="16" y="{TOP + len(shown) * ROW_HEIGHT}" fill="#82939a">and {more} more</text>')
    out.append("</svg>")
    return "".join(out)


def lit_map(apps, lights):
    """One box per app ([{"key", "name"}]) filled by its light level ("warning", "caution", "unexamined", else dark)."""
    cols = 4
    rows = (len(apps) + cols - 1) // cols or 1
    width, height = cols * 130 + 10, rows * 44 + 10
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
           f'role="img" aria-label="Where the questions sit" font-family="system-ui,sans-serif" font-size="11">']
    for n, app in enumerate(apps):
        x, y = 8 + (n % cols) * 130, 8 + (n // cols) * 44
        fill = LIGHT_FILL.get(lights.get(app["key"], ""), LIGHT_FILL["dark"])
        out.append(f'<rect x="{x}" y="{y}" width="118" height="32" rx="5" fill="#152027" stroke="{fill}" stroke-width="2"/>'
                   f'<text x="{x + 59}" y="{y + 20}" text-anchor="middle" fill="#e8eef0">{escape(label(app["name"], 18))}</text>')
    out.append("</svg>")
    return "".join(out)


def text_of(steps):
    """The terminal's rendition: "Website -hold seat-> Booking" for a paired step, "1. <text>" for the rest."""
    lines = []
    for step in steps[:MAX_STEPS]:
        words = _first_sentence(step.get("text", ""))
        if step.get("from") and step.get("to"):
            lines.append(f"{label(step['from'])} ─{words}─▶ {label(step['to'])}")
        else:
            lines.append(f"{step.get('n', len(lines) + 1)}. {words}")
    if len(steps) > MAX_STEPS:
        lines.append(f"and {len(steps) - MAX_STEPS} more")
    return "\n".join(lines)
