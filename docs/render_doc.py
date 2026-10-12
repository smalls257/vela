"""Render a Markdown doc under docs/ to a single-file HTML page, drawing its mermaid diagrams.

    python3 docs/render_doc.py docs/PHILOSOPHY.md
"""
import json
import pathlib
import sys

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "plugin" / "lib" / "planner" / "assets"
STYLE = """body{font:16px/1.6 -apple-system,system-ui,sans-serif;max-width:56rem;margin:2.5rem auto;padding:0 1.2rem;color:#1d232b}
h2{margin-top:2.4rem}table{border-collapse:collapse;width:100%;font-size:14px;margin:.6rem 0}
td,th{border:1px solid #d5dbe3;padding:.35rem .5rem;vertical-align:top;text-align:left}th{background:#eef1f5}
code{font-size:13px;background:#eef1f5;padding:0 .2rem;border-radius:3px}li{margin:.25rem 0}
.mermaid{margin:1.2rem 0;text-align:center;background:#fafbfc;border:1px solid #e3e7ec;border-radius:6px;padding:.8rem}"""
SCRIPT = """const r=new marked.Renderer();const code=r.code.bind(r);
r.code=function(t,l){const text=typeof t==='object'?t.text:t;const lang=typeof t==='object'?t.lang:l;
if(lang==='mermaid')return '<pre class="mermaid">'+text.replace(/</g,'&lt;')+'</pre>';return code(t,l);};
document.getElementById('d').innerHTML=marked.parse(SOURCE,{renderer:r});
mermaid.initialize({startOnLoad:false,theme:'neutral',securityLevel:'loose'});mermaid.run();"""


def page(markdown, title):
    marked = (ASSETS / "marked.min.js").read_text(encoding="utf-8")
    mermaid = (ASSETS / "mermaid.min.js").read_text(encoding="utf-8")
    script = SCRIPT.replace("SOURCE", json.dumps(markdown).replace("</", "<\\/"))
    return (f"<!doctype html><html><head><meta charset=utf-8><title>{title}</title><style>{STYLE}</style>"
            f"<script>{marked}</script><script>{mermaid}</script></head><body><div id=d></div>"
            f"<script>{script}</script></body></html>")


if __name__ == "__main__":
    source = pathlib.Path(sys.argv[1])
    text = source.read_text(encoding="utf-8")
    title = next((line[2:] for line in text.splitlines() if line.startswith("# ")), source.stem)
    source.with_suffix(".html").write_text(page(text, title), encoding="utf-8")
    print(source.with_suffix(".html"))
