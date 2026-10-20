"""E604 and W604: every mermaid block on a page or under docs/ parses with the pinned mermaid, or check says it does
not draw. The judge is mermaid's own parser in node (vela.edge.mermaidjs); these tests hold it to the line it
reports, to a quiet pass on good blocks, to one loud warning when node is missing, and to agreement with Chrome."""
import json
import pathlib
import shutil
import subprocess

import pytest

from conftest import REPO, check, findings, run, run_chrome
from vela import diagramcheck, diagrams, parse, render
from vela.edge import mermaidjs

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed, so mermaid's parser cannot run")

DESIGN = "docs/tech-design/shop.md"
# The Heron desktop agent's withdrawal flow as it was written: the ; in line 4 ends the message for mermaid.
BROKEN_FLOW = """sequenceDiagram
  participant R as ConsentRecorder
  participant S as Scheduler
  R->>S: stop; cancel reads and requests in flight
  S-->>R: stopped"""
GOOD_FLOW = BROKEN_FLOW.replace("stop; cancel", "stop, then cancel")


def design_doc(*diagrams_in_it):
    body = "\n\n".join(f"```mermaid\n{d}\n```" for d in diagrams_in_it)
    return f"---\ntype: tech-design\n---\n# Shop design\n\n## Key flows\n{body}\n"


def write_design(vault, *diagrams_in_it):
    path = vault / DESIGN
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(design_doc(*diagrams_in_it), encoding="utf-8")
    return path


# ------------------------------------------------------------------ the pure part: verdicts to findings

PARSE_ERROR = {"message": "Parse error on line 4:\n...stop; cancel\n---^\nExpecting 'SOLID_ARROW', 'DOTTED_ARROW', got 'NEWLINE'",
               "token": "NEWLINE", "text": "\n", "expected": ["'SOLID_ARROW'", "'DOTTED_ARROW'"]}


def test_a_rejected_block_is_reported_at_the_line_mermaid_stopped_on():
    block = diagramcheck.Block(DESIGN, 10, BROKEN_FLOW)
    [found] = diagramcheck.findings([block], [PARSE_ERROR])
    assert (found.path, found.line, found.code) == (DESIGN, 14, "E604")
    assert found.message == ('The diagram at line 10 ("sequenceDiagram") does not draw: mermaid cannot read its line 4, '
                             '"R->>S: stop; cancel reads and requests in flight": it expected an arrow, such as ->> or -->, '
                             "and found the end of the line.")
    assert "A ; ends a statement in mermaid" in found.fix


def test_a_good_block_has_no_finding():
    assert diagramcheck.findings([diagramcheck.Block(DESIGN, 10, GOOD_FLOW)], [None]) == []


def test_an_unknown_diagram_type_is_named():
    block = diagramcheck.Block(DESIGN, 3, "%% a note\nnonsense here")
    [found] = diagramcheck.findings([block], [{"message": "No diagram type detected matching given configuration for text: nonsense here"}])
    assert found.line == 3 and 'does not know the diagram type "nonsense"' in found.message and '("nonsense here")' in found.message


def test_no_runtime_is_one_warning_never_a_pass():
    blocks = [diagramcheck.Block(DESIGN, 3, GOOD_FLOW), diagramcheck.Block("01-goals.md", 9, "flowchart LR\n a --> b")]
    [found] = diagramcheck.unchecked(blocks, "node is not on the PATH")
    assert (found.code, found.path, found.line) == ("W604", DESIGN, 3)
    assert found.message == "2 mermaid diagrams not checked: node is not on the PATH."
    assert diagramcheck.unchecked([], "node is not on the PATH") == []


def test_verdicts_that_do_not_line_up_are_a_tool_failure():
    with pytest.raises(ValueError):
        diagramcheck.findings([diagramcheck.Block(DESIGN, 3, GOOD_FLOW)], [])


# ------------------------------------------------------------------ vela check, end to end

@needs_node
def test_check_reports_a_broken_design_diagram_with_its_line(mini):
    write_design(mini, GOOD_FLOW, BROKEN_FLOW)
    code, out = check(mini)
    assert code == 1
    assert findings(out) == [("E604", DESIGN)]
    # fence of the second block is line 15 of the doc, and mermaid stopped on its line 4
    assert f"{DESIGN}:19: E604 The diagram at line 15 (\"sequenceDiagram\") does not draw" in out, out


@needs_node
def test_check_passes_good_diagrams_quietly(mini):
    write_design(mini, GOOD_FLOW, "erDiagram\n  PERSON ||--o{ NOTE : has\n  NOTE { text body  bool shown }")
    code, out = check(mini)
    assert "E604" not in out and "W604" not in out, out


@needs_node
def test_check_diagrams_checks_only_the_files_named(mini, monkeypatch):
    write_design(mini, BROKEN_FLOW)
    monkeypatch.chdir(mini)
    code, out = run("check-diagrams", "--vault", str(mini), DESIGN)
    assert code == 1 and findings(out) == [("E604", DESIGN)], out
    code, out = run("check-diagrams", "--vault", str(mini), "01-goals.md")
    assert code == 0 and findings(out) == [], out


@needs_node
def test_check_diagrams_needs_no_vault_for_a_named_file(tmp_path, monkeypatch):
    write_design(tmp_path, GOOD_FLOW, BROKEN_FLOW)
    monkeypatch.chdir(tmp_path)
    code, out = run("check-diagrams", DESIGN)
    assert code == 1 and out.startswith("vela check-diagrams: 2 diagrams, 1 that do not draw"), out
    assert findings(out) == [("E604", DESIGN)]


@pytest.mark.parametrize("named", ["/no/such/node", ""])
def test_check_without_node_warns_once(mini, monkeypatch, named):
    write_design(mini, BROKEN_FLOW)
    monkeypatch.setenv("VELA_NODE", named)
    code, out = check(mini)
    warned = [line for line in out.splitlines() if " W604 " in line]
    assert len(warned) == 1 and "not a program that runs" in warned[0], out
    assert "E604" not in out


def test_a_parser_that_crashes_is_a_warning_not_a_pass(mini, monkeypatch, tmp_path):
    write_design(mini, GOOD_FLOW)
    broken = tmp_path / "node"
    broken.write_text("#!/bin/sh\necho boom >&2\nexit 3\n")
    broken.chmod(0o755)
    monkeypatch.setenv("VELA_NODE", str(broken))
    _, out = check(mini)
    assert [l for l in out.splitlines() if " W604 " in l and "exit 3 (boom)" in l], out


# ------------------------------------------------------------------ every diagram the toolkit ships or generates

CORPUS_ROOTS = ["examples", "template", "docs", "tests/fixtures", "tests/sim/snapshots", "tests/stub-conventions"]
# Mermaid that is a placeholder on purpose, for a skill to fill in: never meant to draw.
TEMPLATES = ("plugin/skills/",)


def shipped_blocks():
    out = []
    for root in CORPUS_ROOTS:
        for path in sorted((REPO / root).rglob("*.md")):
            rel = path.relative_to(REPO).as_posix()
            out.extend(diagramcheck.blocks([parse.parse_page(rel, path.read_text(encoding="utf-8"))]))
    return out


def vault_roots():
    seen = set()
    for root in CORPUS_ROOTS:
        for marker in (REPO / root).rglob("01-goals.md"):
            seen.add(marker.parent)
    return sorted(seen)


def generated_blocks():
    """Every diagram the generators draw for every page of every vault in the repo, drawn fresh, so a stale page
    cannot hide a generator that writes bad mermaid."""
    from vela import cli
    out = []
    for root in vault_roots():
        vault = cli.load_vault(root)
        for page in vault.pages:
            for name in ("context-map", "system-context", "app-context", "capability-map"):
                if not render.block_allowed(page, name):
                    continue
                content = render.block_content(vault, page, name) or ""
                label = f"{root.relative_to(REPO).as_posix()}/{page.path} [{name}]"
                out.extend(diagramcheck.blocks([parse.parse_page(label, content)]))
    return out


HOSTILE_NAMES = ['Say "hi"; then end', "A [b] {c} (d) <e> |f| #g; &h", "end", "subgraph", "click", "graph TD",
                 "-->", "%%{init: {}}%%", "x --- y", "Ünïcödé café", "", "   ", "1st", "style", "classDef"]


def hostile_blocks():
    nodes = [diagrams.app_node(type("P", (), {"meta": {"title": n, "change": "new"}, "id": f"APP-{i}", "name": f"app-{i}"})())
             for i, n in enumerate(HOSTILE_NAMES)]
    nodes += [diagrams.external_node(n or "x") for n in HOSTILE_NAMES]
    edges = [(nodes[i], nodes[i + 1], f"CON-{i:03d}") for i in range(len(nodes) - 1)]
    graph = diagrams._graph(nodes, edges)
    groups = [("g_one", diagrams.safe_label('Dom "a"; [b]', "No domain"), [n.key for n in graph.nodes[:5]])]
    return [diagramcheck.Block("hostile", 1, "\n".join(diagrams.flowchart(graph, "LR", groups)))]


# Broken on purpose: the flow checker's fixtures for a diagram it cannot read (a par with no end).
BROKEN_ON_PURPOSE = {
    "tests/fixtures/flowcheck/10-unreadable-and-undeclared/06-runtime/flows/FLO-010-10-unreadable-and-undeclared.md",
    "tests/fixtures/flowcheck/19-handler-not-closed/06-runtime/flows/FLO-019-19-handler-not-closed.md",
}


@needs_node
def test_every_shipped_and_generated_diagram_parses():
    blocks = [b for b in shipped_blocks() + generated_blocks() + hostile_blocks() if not b.path.startswith(TEMPLATES)]
    assert len(blocks) > 100, "the corpus lost its diagrams"
    found = diagramcheck.findings(blocks, mermaidjs.parse_all(b.source for b in blocks))
    assert [f.format() for f in found if f.path not in BROKEN_ON_PURPOSE] == []
    assert {f.path for f in found} == BROKEN_ON_PURPOSE, "a fixture broken on purpose now parses; take it off the list"


# ------------------------------------------------------------------ the node parser agrees with Chrome

AGREEMENT = [GOOD_FLOW, BROKEN_FLOW, "flowchart LR\n  A[\"<b>bold</b><br/>two\"] --> B", "flowchart LR\n  A -->|x| ",
             "erDiagram\n  A ||--o{ B : has\n  A { text t  bool b }", "nonsense", "pie\n  \"a\": 1",
             "flowchart LR\n  A --> B; C --> D", "sequenceDiagram\n  A->>B: hi #59; there", "classDiagram\n  A <|-- B",
             "flowchart LR\n  subgraph s[\"S\"]\n  a\n  end\n  click a call x()"]


@pytest.mark.browser
@needs_node
def test_node_and_chrome_agree_on_what_parses(tmp_path):
    from test_viewer import CHROME
    if CHROME is None:
        pytest.skip("headless Chrome is not installed")
    shutil.copy(mermaidjs.MERMAID, tmp_path / "mermaid.min.js")
    page = tmp_path / "parse.html"
    page.write_text("""<!doctype html><meta charset="utf-8"><script src="mermaid.min.js"></script><pre id="out">pending</pre>
<script>(async () => { mermaid.initialize({startOnLoad: false, securityLevel: 'strict'}); const out = [];
for (const s of %s) { try { await mermaid.parse(s); out.push(true); } catch (e) { out.push(false); } }
document.getElementById('out').textContent = JSON.stringify(out); })();</script>""" % json.dumps(AGREEMENT).replace("</", "<\\/"))
    dom = run_chrome([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files",
                          f"--user-data-dir={tmp_path / 'profile'}", "--virtual-time-budget=10000", "--dump-dom",
                          page.as_uri()], 60)[1]
    chrome = json.loads(dom.split('<pre id="out">', 1)[1].split("</pre>", 1)[0])
    in_node = [v is None for v in mermaidjs.parse_all(AGREEMENT)]
    assert in_node == chrome
    assert False in chrome and True in chrome
