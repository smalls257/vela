"""Render a Markdown doc under docs/ to a single-file HTML page, drawing its mermaid diagrams.

    python3 docs/render_doc.py docs/PHILOSOPHY.md
"""
import json
import pathlib
import sys

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "plugin" / "lib" / "vela" / "assets"
STYLE = """:root{color-scheme:light dark;--ink:#1d2433;--soft:#5b6475;--line:#d9dee8;--accent:#3b5bdb;--bg:#fbfcfe;--tint:#eef1f7}
@media (prefers-color-scheme:dark){:root{--ink:#e7ebf3;--soft:#a3acbd;--line:#2e3646;--accent:#8ea6ff;--bg:#12161f;--tint:#1a202c}}
body{font:17px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;max-width:760px;margin:0 auto;padding:56px 24px 72px;color:var(--ink);background:var(--bg)}
h1{font-size:40px;margin:0 0 8px;letter-spacing:-.5px}h2{font-size:22px;margin-top:2.4rem}h3{font-size:18px;margin-top:1.8rem}
a{color:var(--accent)}table{border-collapse:collapse;width:100%;font-size:15px;margin:.6rem 0}
td,th{border:1px solid var(--line);padding:.4rem .55rem;vertical-align:top;text-align:left}th{background:var(--tint)}
code{font-size:14px;background:var(--tint);padding:0 .25rem;border-radius:4px}pre{background:var(--tint);border:1px solid var(--line);border-radius:8px;padding:.8rem 1rem;overflow:auto}
pre code{background:none;padding:0}li{margin:.25rem 0}blockquote{border-left:3px solid var(--line);margin:1rem 0;padding:2px 0 2px 14px;color:var(--soft)}
.mermaid{margin:1.2rem 0;text-align:center;background:var(--tint);border:1px solid var(--line);border-radius:12px;padding:.8rem}"""
SCRIPT = """const r=new marked.Renderer();const code=r.code.bind(r);
r.code=function(t,l){const text=typeof t==='object'?t.text:t;const lang=typeof t==='object'?t.lang:l;
if(lang==='mermaid')return '<pre class="mermaid">'+text.replace(/</g,'&lt;')+'</pre>';return code(t,l);};
document.getElementById('d').innerHTML=marked.parse(SOURCE,{renderer:r});
mermaid.initialize({startOnLoad:false,theme:matchMedia('(prefers-color-scheme: dark)').matches?'dark':'neutral',securityLevel:'loose'});mermaid.run();"""


def page(markdown, title):
    marked = (ASSETS / "marked.min.js").read_text(encoding="utf-8")
    mermaid = (ASSETS / "mermaid.min.js").read_text(encoding="utf-8")
    script = SCRIPT.replace("SOURCE", json.dumps(markdown).replace("</", "<\\/"))
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content=width=device-width,initial-scale=1><title>{title}</title><style>{STYLE}</style>"
            f"<script>{marked}</script><script>{mermaid}</script></head><body><div id=d></div>"
            f"<script>{script}</script></body></html>")


if __name__ == "__main__":
    source = pathlib.Path(sys.argv[1])
    text = source.read_text(encoding="utf-8")
    title = next((line[2:] for line in text.splitlines() if line.startswith("# ")), source.stem)
    source.with_suffix(".html").write_text(page(text, title), encoding="utf-8")
    print(source.with_suffix(".html"))
