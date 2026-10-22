"""Build the "How vela thinks" site: docs/method/src/*.md -> docs/method/*.html.

    python3 docs/render_method.py          # write the pages
    python3 docs/render_method.py --check  # fail when the committed pages are out of date

The Violation this exists to prevent is the one-page wall (the old METHOD.html was 18,600 words): a page must open
with its point and a count of what is below, and carry four to seven sections. The build refuses a page that doesn't,
so the rule holds when someone adds a section later. The words live in the Markdown; the CSS and JS beside the
pages are written by hand and the pages work without the JS (everything is then simply open).

Source format, besides plain Markdown (paragraphs, lists, quotes, fenced code, links, images):
  front matter   title, lede, and kind: reference (a reference page may have fewer sections)
  ## Heading     one section of the page
  [text][ref]    a link named in refs.md (paths relative to docs/method/src/); [`test_x.py`][t-x] needs no entry
  ::: fold Title ... :::                                   a folded block (a bare ::: closes the innermost block)
  ::: deck id | Label ... ::: card id | Label | Question | kind | group ... ::: end card ... ::: end deck
  ::: steps id | Label ... ::: step Title ... ::: end step ... ::: end steps
  ::: flow id | Label, with ::: node id | Label | x | y and ::: step from>to | Contract | Title blocks
  ::: entry page.md | Title | One line                    (home page only, one line, no end)
"""
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "method" / "src"
OUT = HERE / "method"
LEAVES = {"entry", "node"}
NUMBER_WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven"]
MIN_SECTIONS, MAX_SECTIONS = 4, 7
ORDER = ["problem", "ladder", "certainty", "joins", "claude", "trust", "example"]
REFERENCE = "reference"


class PageError(Exception):
    pass


# ------------------------------------------------------------------ inline text

def read_refs():
    refs = {}
    for line in (SRC / "refs.md").read_text(encoding="utf-8").splitlines():
        match = re.match(r"\[([^\]]+)\]:\s*(\S+)", line)
        if match:
            refs[match.group(1)] = match.group(2)
    return refs


def link_attrs(url):
    """href, plus data-repo for a link out of the site into the repository (the JS points it at GitHub when served over http)."""
    if url.startswith("../../../"):
        repo_path = url[len("../../../"):]
        return f'href="../../{repo_path}" data-repo="{html.escape(repo_path)}"'
    if re.match(r"^[\w-]+\.md(#.*)?$", url):
        return f'href="{html.escape(url.replace(".md", ".html", 1))}"'
    return f'href="{html.escape(url)}"'


def inline(text, refs):
    spans = []

    def keep(match):
        spans.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" loading="lazy">', text)

    def by_ref(match):
        if match.group(2).startswith("t-") and match.group(2) not in refs:  # t-name is tests/test_name.py
            refs[match.group(2)] = f"../../../tests/test_{match.group(2)[2:]}.py"
        if match.group(2) not in refs:
            raise PageError(f"link [{match.group(1)}][{match.group(2)}] names a ref that refs.md doesn't define")
        return f"<a {link_attrs(refs[match.group(2)])}>{match.group(1)}</a>"

    text = re.sub(r"\[([^\]]+)\]\[([^\]]+)\]", by_ref, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f"<a {link_attrs(m.group(2))}>{m.group(1)}</a>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)


# ------------------------------------------------------------------ blocks

def split_blocks(lines):
    """Top-level pieces: ('text', [lines]) or ('block', name, args, children, ...) with nested blocks left as lines."""
    pieces, text, i = [], [], 0
    while i < len(lines):
        match = re.match(r"^::: (\w+)\s*(.*)$", lines[i])
        if not match or match.group(1) == "end":
            text.append(lines[i])
            i += 1
            continue
        name, args = match.group(1), match.group(2).strip()
        if text:
            pieces.append(("text", text))
            text = []
        if name in LEAVES:
            pieces.append(("block", name, args, []))
            i += 1
            continue
        depth, j = 1, i + 1
        while j < len(lines) and depth:
            opener = re.match(r"^::: (\w+)", lines[j])
            if re.match(r"^:::\s*$", lines[j]) or (opener and opener.group(1) == "end"):
                depth -= 1
            elif opener and opener.group(1) not in LEAVES:
                depth += 1
            j += 1
        if depth:
            raise PageError(f"block '{name} {args}' is never closed with '::: end {name}'")
        pieces.append(("block", name, args, lines[i + 1:j - 1]))
        i = j
    if text:
        pieces.append(("text", text))
    return pieces


def markdown(lines, refs):
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
        elif re.match(r"^(- |\d+\. )", line):
            ordered = line[0].isdigit()
            items, i = [], i
            while i < len(lines) and re.match(r"^(- |\d+\. )", lines[i]):
                items.append(inline(re.sub(r"^(- |\d+\. )", "", lines[i]), refs))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{item}</li>" for item in items) + f"</{tag}>")
        elif line.startswith("> "):
            quoted = []
            while i < len(lines) and lines[i].startswith("> "):
                quoted.append(lines[i][2:])
                i += 1
            out.append("<blockquote>" + inline(" ".join(quoted), refs) + "</blockquote>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"^(- |\d+\. |> |```)", lines[i]):
                para.append(lines[i])
                i += 1
            out.append("<p>" + inline(" ".join(para), refs) + "</p>")
    return "\n".join(out)


def parts(args, count):
    pieces = [p.strip() for p in args.split("|")]
    if len(pieces) < count:
        raise PageError(f"'{args}' needs {count} parts separated by |")
    return pieces


def render_children(name, args, children, refs):
    pieces = split_blocks(children)
    if name == "fold":
        return f'<details class="fold"><summary>{inline(args, refs)}</summary>{render(children, refs)}</details>'
    if name == "deck":
        ident, label = parts(args, 2)[:2]
        cards = "".join(render_card(p[2], p[3], refs) for p in pieces if p[0] == "block" and p[1] == "card")
        intro = render([line for p in pieces if p[0] == "text" for line in p[1]], refs)
        return (f'<div class="deck" data-deck="{html.escape(ident)}" data-label="{html.escape(label)}">{intro}'
                f'<div class="deck-cards">{cards}</div></div>')
    if name in ("steps", "flow"):
        return render_stepper(name, args, pieces, refs)
    raise PageError(f"unknown block '{name}'")


def render_card(args, children, refs):
    ident, label, question, kind, group = (parts(args, 5) + [""])[:5]
    return (f'<article class="card" id="{html.escape(ident)}" data-label="{html.escape(label)}" data-kind="{html.escape(kind)}" '
            f'data-group="{html.escape(group)}"><h3>{inline(label, refs)}<span class="q">{inline(question, refs)}</span></h3>'
            f'{render(children, refs)}</article>')


def render_stepper(name, args, pieces, refs):
    ident, label = parts(args, 2)[:2]
    nodes, steps = [], []
    for piece in pieces:
        if piece[0] != "block":
            continue
        if piece[1] == "node":
            node_id, node_label, x, y = parts(piece[2], 4)[:4]
            nodes.append({"id": node_id, "label": node_label, "x": int(x), "y": int(y)})
        elif piece[1] == "step":
            step_args, step_lines = piece[2], piece[3]
            if name == "flow":
                route, contract, title = parts(step_args, 3)[:3]
                sender, _, receiver = route.partition(">")
                attrs = f'data-from="{html.escape(sender)}" data-to="{html.escape(receiver or sender)}" data-contract="{html.escape(contract)}"'
            else:
                title, attrs = step_args, ""
            steps.append(f'<div class="step" {attrs}><h3>{inline(title, refs)}</h3>{render(step_lines, refs)}</div>')
    data = f" data-nodes='{html.escape(json.dumps(nodes), quote=True)}'" if nodes else ""
    return (f'<div class="stepper" data-kind="{name}" data-label="{html.escape(label)}" id="{html.escape(ident)}"{data}>'
            f'<div class="step-list">{"".join(steps)}</div></div>')


def render(lines, refs):
    out = []
    for piece in split_blocks(lines):
        if piece[0] == "text":
            out.append(markdown(piece[1], refs))
        else:
            _, name, args, children = piece
            out.append(render_children(name, args, children, refs))
    return "\n".join(part for part in out if part)


# ------------------------------------------------------------------ pages

def load(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise PageError(f"{path.name} has no front matter")
    meta = dict(re.match(r"(\w+):\s*(.*)", line).groups() for line in match.group(1).splitlines() if line.strip())
    return meta, match.group(2).strip("\n").splitlines()


def slug(heading):
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def sections_of(lines):
    sections, current, fenced = [], None, False
    for line in lines:
        fenced ^= line.startswith("```")
        if line.startswith("## ") and not fenced:
            current = (line[3:].strip(), [])
            sections.append(current)
        elif current is not None:
            current[1].append(line)
        elif line.strip():
            raise PageError("text before the first '## ' section; put the opening in the lede")
    return sections


def chrome(title, body, depth_note, nav_prev, nav_next, position):
    prev_link = f'<a rel="prev" href="{nav_prev[0]}.html"><span>Before</span> {html.escape(nav_prev[1])}</a>' if nav_prev else "<span></span>"
    next_link = f'<a rel="next" href="{nav_next[0]}.html"><span>Next</span> {html.escape(nav_next[1])}</a>' if nav_next else "<span></span>"
    where = f'<span class="where">{position}</span>' if position else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="method.css">
<script src="method.js" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to the page</a>
<header class="top"><a class="brand" href="../index.html">Vela</a><a href="index.html">How vela thinks</a>{where}</header>
<main id="main">
{body}
</main>
<footer class="foot"><nav aria-label="Pages">{prev_link}{next_link}</nav>
<p><a class="home" href="../index.html">&larr; Back to the Vela home page</a> &middot; <a href="index.html">All topics</a> &middot; <a href="reference.html">Words and sources</a></p></footer>
</body>
</html>
"""


def count_line(sections):
    word = NUMBER_WORDS[len(sections)]
    items = "".join(f'<li><a href="#{slug(title)}">{html.escape(title)}</a></li>' for title, _ in sections)
    return f'<nav class="count" aria-label="On this page"><p>{word} things below.</p><ol>{items}</ol></nav>'


def build_page(name, refs, titles):
    meta, lines = load(SRC / f"{name}.md")
    sections = sections_of(lines)
    if meta.get("kind") != REFERENCE and not MIN_SECTIONS <= len(sections) <= MAX_SECTIONS:
        raise PageError(f"{name}.md has {len(sections)} sections; a page holds {MIN_SECTIONS} to {MAX_SECTIONS}")
    body = [f'<h1>{inline(meta["title"], refs)}</h1>', f'<p class="lede">{inline(meta["lede"], refs)}</p>']
    if meta.get("kind") != REFERENCE:
        body.append(count_line(sections))
    for title, section_lines in sections:
        body.append(f'<section id="{slug(title)}"><h2>{inline(title, refs)}</h2>\n{render(section_lines, refs)}\n</section>')
    index = ORDER.index(name) if name in ORDER else None
    prev_name = titles[ORDER[index - 1]] if index else None
    next_name = titles[ORDER[index + 1]] if index is not None and index + 1 < len(ORDER) else None
    prev_link = (ORDER[index - 1], prev_name) if prev_name else (("index", "All topics") if index == 0 else None)
    next_link = (ORDER[index + 1], next_name) if next_name else None
    position = f"Topic {index + 1} of {len(ORDER)}" if index is not None else ""
    return chrome(f'{meta["title"]} | How vela thinks', "\n".join(body), "", prev_link, next_link, position)


def build_home(refs, titles):
    meta, lines = load(SRC / "index.md")
    entries = []
    for piece in split_blocks(lines):
        if piece[0] == "block" and piece[1] == "entry":
            target, title, blurb = parts(piece[2], 3)[:3]
            entries.append((target, title, blurb))
    if not MIN_SECTIONS <= len(entries) <= MAX_SECTIONS:
        raise PageError(f"the home page has {len(entries)} entry points; it holds {MIN_SECTIONS} to {MAX_SECTIONS}")
    intro = render([line for p in split_blocks(lines) if p[0] == "text" for line in p[1]], refs)
    cards = "".join(
        f'<li><a class="entry" href="{t.replace(".md", ".html")}"><b>{html.escape(title)}</b><span>{inline(blurb, refs)}</span></a></li>'
        for t, title, blurb in entries)
    body = (f'<h1>{inline(meta["title"], refs)}</h1><p class="lede">{inline(meta["lede"], refs)}</p>{intro}'
            f'<p class="count">{NUMBER_WORDS[len(entries)]} places to start.</p><ol class="entries">{cards}</ol>')
    return chrome(f'{meta["title"]}', body, "", None, (ORDER[0], titles[ORDER[0]]), "")


def build_all():
    refs = read_refs()
    titles = {name: load(SRC / f"{name}.md")[0]["title"] for name in ORDER}
    pages = {"index": build_home(refs, titles), "reference": build_page("reference", refs, titles)}
    for name in ORDER:
        pages[name] = build_page(name, refs, titles)
    return pages


def visible_words(page_html):
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", page_html, flags=re.S)
    return len(re.sub(r"<[^>]+>", " ", html.unescape(text)).split())


def main(argv):
    try:
        pages = build_all()
    except PageError as problem:
        print(f"render_method: {problem}", file=sys.stderr)
        return 1
    stale = []
    for name, text in pages.items():
        target = OUT / f"{name}.html"
        if "--check" in argv:
            if not target.exists() or target.read_text(encoding="utf-8") != text:
                stale.append(target.name)
        else:
            target.write_text(text, encoding="utf-8")
    if stale:
        print("render_method: out of date, run python3 docs/render_method.py: " + ", ".join(stale), file=sys.stderr)
        return 1
    total = sum(visible_words(text) for text in pages.values())
    print(f"{len(pages)} pages, about {total} words on the pages ({'checked' if '--check' in argv else 'written'})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
