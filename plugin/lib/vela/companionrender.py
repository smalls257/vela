"""One session or explain dict, drawn three ways: terminal Markdown, a one-line band, a self-contained HTML page. Pure.

Every surface draws the same dict, so they can't drift (Distributed Monolith ruled out), and none of them holds a plan
rule: the words and the counts come from the dict. The Markdown and the terminal pane both draw the dict's blocks
(`companionblocks.py`), so the fallback a person reads when the pane can't draw is the pane's own content in plain
text. The panels only show; nothing here sends anything back to Claude (owner's ruling of October 24, 2026). Vault text
reaches the HTML only escaped.
"""
from vela import companionblocks, companionhtml, companionsvg

BAR_CELLS = 20
MARKDOWN_DRAWING = "60"  # why: the pane is 64 columns wide and a Markdown code block is indented four


def with_renders(data):
    """The dict with its blocks, its band and its diagram's drawings filled in, so the JSON carries what the surfaces
    show."""
    data["blocks"] = companionblocks.blocks_of(data)
    data["band_spans"] = companionblocks.band_spans(data)
    data["out_of_date"] = companionblocks.OUT_OF_DATE
    if data.get("kind") == "session":
        data["band"] = band(data)
        diagram = data.get("diagram")
        if diagram:
            diagram["svg"] = companionsvg.sequence(diagram["steps"], diagram["name"])
    return data


def band(data):
    """One line for a narrow window: "Grill: hold, pay, confirm · 2 decided · 1 open · next: Pricing runtime · /vela-companion to open"."""
    return "".join(piece["t"] for piece in companionblocks.session_band(data))


def line_text(line):
    """A Line as plain text: its spans in order, a bar as filled and empty cells."""
    out = []
    for piece in line:
        if "bar" in piece:
            done, total = piece["bar"]
            full = int(BAR_CELLS * done / total + 0.5) if total else 0  # why: half up, as the mod's Math.round does; Python's round() goes to even
            out.append("█" * full + "░" * (BAR_CELLS - full))
        else:
            out.append(piece["t"])
    return "".join(out)


def row_text(row):
    chip = f"[{row['chip']['t']}]" if row["chip"] else ""
    bits = [b for b in (f"{row['mark']} {row['name']}".strip(), row["id"], row["note"], chip) if b]
    lines = ["- " + "  ".join(bits)]
    if row["sub"]:
        lines.append("    " + line_text(row["sub"]))
    return lines


def block_text(block):
    kind = block["type"]
    if kind == "card":
        head = f"**{block['title']}**" + (f"   {block['right']}" if block["right"] else "")
        return [head] + [line_text(line) for line in block["lines"]]
    if kind == "next":
        head = f"{block['chip']}  {block['text']}" + (f"  {block['id']}" if block["id"] else "")
        return [head] + ([f"      {block['note']}"] if block["note"] else [])
    if kind == "section":
        head = (f"**{block['title']}**" + (f" ({block['count']})" if block["count"] else "")) if block["title"] else ""
        return ([head] if head else []) + [line for row in block["rows"] for line in row_text(row)]
    if kind == "bars":
        room = max(len(r["label"]) for r in block["rows"])
        return [f"**{block['title']}**"] + [
            f"  {r['label'].ljust(room)}  " + line_text([{"bar": [r["value"], r["max"]]}]) + f"  {r['text']}" for r in block["rows"]]
    if kind == "diagram":
        if not block["drawings"]:
            return [f"**{block['title']}**", block["alt"]]  # a picture with no character drawing is said in words
        drawing = block["drawings"][MARKDOWN_DRAWING]
        return [f"**{block['title']}**", ""] + ["    " + line_text(line) for line in drawing]
    return [line_text(line) for line in block["lines"]]


def markdown(data):
    """The blocks as plain text, in the panel's order: what a terminal that can't draw them shows."""
    blocks = data.get("blocks") or companionblocks.blocks_of(data)
    parts = ["\n".join(block_text(block)) for block in blocks]
    return "\n\n".join(part for part in parts if part).rstrip("\n") + "\n"


def html(data, palette):
    return companionhtml.page(data, palette)
