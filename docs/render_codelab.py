"""Build the codelab "Plan your first initiative with vela": docs/codelab/src/*.md -> docs/codelab/index.html.

    python3 docs/render_codelab.py          # write the page
    python3 docs/render_codelab.py --check  # fail when the committed page is out of date

The Violation this exists to prevent is a tutorial that drifts from what vela does, or one that skips the proof: a step
with no checkpoint is a step the reader can't tell they finished. So the build refuses a step that has no checkpoint,
and a middle step with no "Why this step" or no "Stuck?". The words live in the Markdown; the page reuses the Markdown
subset and the look of the method site (render_method.py, ../method/method.css).

Source: one file per step, named NN-slug.md, with front matter title, minutes and summary. Besides plain Markdown and
`::: fold Title ... :::`, a step may hold these blocks (close each with a bare `:::`):
  type        what you type
  asks        what Claude asks you (an example, labeled as one)
  see         what you should see after (real excerpts)
  checkpoint  how you know the step worked
The first and last steps need no Why. Every other step needs fold "Why this step" and fold "Stuck?".
"""
import html
import pathlib
import re
import sys

import render_method as rm

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "codelab" / "src"
OUT = HERE / "codelab" / "index.html"
TITLE = "Plan your first initiative with vela"
BLOCKS = {"type": "You type", "asks": "Claude asks you", "see": "What you should see", "checkpoint": "Checkpoint"}
PLUGIN = HERE.parent / "plugin"


class StepError(rm.PageError):
    pass


def read_refs():
    refs = {}
    for line in (SRC / "refs.md").read_text(encoding="utf-8").splitlines():
        match = re.match(r"\[([^\]]+)\]:\s*(\S+)", line)
        if match:
            refs[match.group(1)] = match.group(2)
    return refs


def render_body(lines, refs):
    out = []
    for piece in rm.split_blocks(lines):
        if piece[0] == "text":
            out.append(rm.markdown(piece[1], refs))
            continue
        _, name, args, children = piece
        if name in BLOCKS:
            inner = rm.render(children, refs)
            if name == "type":
                inner = inner.replace("<pre>", '<div class="code"><button type="button" class="copy">Copy</button><pre>').replace("</pre>", "</pre></div>")
            out.append(f'<div class="cl cl-{name}"><h3>{BLOCKS[name]}</h3>{inner}</div>')
        elif name == "fold":
            out.append(rm.render_children(name, args, children, refs))
        else:
            raise StepError(f"unknown block '{name}'")
    return "\n".join(out)


def load_steps():
    steps = []
    for path in sorted(SRC.glob("[0-9][0-9]-*.md")):
        meta, lines = rm.load(path)
        for key in ("title", "minutes", "summary"):
            if key not in meta:
                raise StepError(f"{path.name} has no {key} in its front matter")
        steps.append((path.name, meta, lines))
    if not steps:
        raise StepError("no steps under docs/codelab/src")
    return steps


def check_step(name, lines, position, count):
    text = "\n".join(lines)
    if "::: checkpoint" not in text:
        raise StepError(f"{name} has no checkpoint")
    if 0 < position < count - 1:
        for fold in ("Why this step", "Stuck?"):
            if f"::: fold {fold}" not in text:
                raise StepError(f"{name} has no fold '{fold}'")


def route(steps):
    items = "".join(
        f'<li><a href="#step-{i}"><span class="dot">{i}</span><span class="t">{html.escape(m["title"])}</span>'
        f'<span class="mins">{m["minutes"]} min</span></a></li>' for i, (_, m, _) in enumerate(steps, 1))
    return f'<nav class="route" aria-label="Steps"><ol>{items}</ol></nav>'


def step_nav(i, steps):
    prev = (f'<a rel="prev" class="prev" href="#step-{i - 1}"><span>Back</span> {html.escape(steps[i - 2][1]["title"])}</a>'
            if i > 1 else "<span></span>")
    nxt = (f'<a rel="next" class="next-step" href="#step-{i + 1}"><span>Next</span> {html.escape(steps[i][1]["title"])}</a>'
           if i < len(steps) else '<a class="next-step" href="../method/index.html"><span>Finish</span> How vela thinks</a>')
    return f'<div class="step-nav">{prev}{nxt}</div>'


def build():
    refs = read_refs()
    steps = load_steps()
    total = sum(int(m["minutes"]) for _, m, _ in steps)
    sections = []
    for i, (name, meta, lines) in enumerate(steps, 1):
        check_step(name, lines, i - 1, len(steps))
        body = render_body(lines, refs).replace("{{total}}", str(total))
        sections.append(
            f'<section class="step" id="step-{i}" data-title="{html.escape(meta["title"])}" data-min="{meta["minutes"]}">'
            f'<header><p class="meta">Step {i} of {len(steps)} &middot; {meta["minutes"]} min</p><h2>{rm.inline(meta["title"], refs)}</h2>'
            f'<p class="sum">{rm.inline(meta["summary"], refs)}</p></header>\n{body}\n{step_nav(i, steps)}</section>')
    head = (f'<h1>{TITLE}</h1><p class="lede">From one sentence to tickets, on the Heron example. About {total} minutes.</p>'
            f'<div class="progress" aria-hidden="true"><div id="bar"></div></div>'
            f'<p class="left"><span id="timeleft">{total} min left</span></p>{route(steps)}')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE} | Vela</title>
<link rel="stylesheet" href="../method/method.css">
<link rel="stylesheet" href="codelab.css">
{rm.THEME_HEAD}
<script src="../method/method.js" defer></script>
<script src="codelab.js" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to the page</a>
<header class="top"><a class="brand" href="../index.html">Vela</a><a href="../method/index.html">How vela thinks</a><a href="index.html">Plan your first initiative</a>{rm.THEME_BUTTON}</header>
<main id="main" class="codelab">
{head}
{chr(10).join(sections)}
</main>
<footer class="foot"><p><a class="home" href="../index.html">&larr; Back to the Vela home page</a> &middot; <a href="../method/index.html">How vela thinks</a></p></footer>
</body>
</html>
"""


def main(argv):
    try:
        page = build()
    except rm.PageError as problem:
        print(f"render_codelab: {problem}", file=sys.stderr)
        return 1
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != page:
            print("render_codelab: out of date, run python3 docs/render_codelab.py", file=sys.stderr)
            return 1
        print("codelab: checked")
        return 0
    OUT.write_text(page, encoding="utf-8")
    print(f"codelab: written, about {rm.visible_words(page)} words")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
