"""Lane groups written on the flow page (mermaid's `box`): the checker reads them, the build carries them, the skill and the conventions name the rule.

Violation this holds off: Leaky Narrative at the page. A group the author writes with `box` must reach the Flows view as data
(flow["groups"]), never as an "unreadable line" in the checker or a second reading of the diagram in the explorer; and a box that
cannot be a group (one lane, a lane the plan does not draw) is dropped where it is read, not drawn wrong.
"""
import json
import pathlib
import re
import shutil

import pytest
from conftest import REPO, run

from vela import cli
from vela.flowcheck import mermaid, readers
from vela.flowcheck.tables import FlowLine

TODAY = "2026-11-20"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)
FLO_001 = "06-runtime/flows/FLO-001-hold-pay-confirm.md"


def tokens(*lines):
    problems = []
    return mermaid.tokenize(["sequenceDiagram", *lines], 1, "p.md", "FLO-9", problems), problems


def test_a_box_is_read_with_its_participants_and_its_end_closes_the_box_not_an_alt():
    out, problems = tokens("box Channels", "  participant W as Public website", "  participant D", "end", "participant B", "alt The customer books on the website", "W->>B: CON-001 hold", "else The customer calls in", "D->>B: CON-001 hold", "end")
    assert problems == []
    assert [t.kind for t in out][:5] == ["box", "participant", "participant", "boxend", "participant"]
    tree = mermaid.parse_tree(type("F", (), {"lines": out, "path": "p.md", "id": "FLO-9"})(), problems)
    assert problems == []
    assert tree.boxes == [("Channels", ["W", "D"], 2)]
    assert [b.label for b in tree.starts] == ["The customer books on the website", "The customer calls in"]  # the opening alt still reads: the box's end was not taken for the alt's


@pytest.mark.parametrize("written,name", [("box Channels", "Channels"), ("box rgb(10, 20, 30) Lookups and more", "Lookups and more"), ("box transparent Back end", "Back end"),
                                           ("box #aabbcc Edge", "Edge"), ("box Aqua Group Description", "Group Description"), ("box Pink Floyd", "Floyd"), ("box Customer lookups", "Customer lookups")])
def test_a_box_name_is_what_mermaid_draws_after_an_optional_color(written, name):
    out, problems = tokens(written, "participant A", "end")
    assert problems == [] and out[0] == FlowLine(2, "box", (name,))


def test_a_box_holds_only_participants_and_must_be_closed_and_named():
    _, problems = tokens("box Channels", "participant A", "A->>B: CON-001 hold", "end")
    assert any("Only participants go inside a box" in p.text for p in problems)
    _, problems = tokens("box Channels", "participant A")
    assert any("never closed" in p.text for p in problems)
    _, problems = tokens("box", "participant A", "end")
    assert any("needs a name" in p.text for p in problems)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("groups")
    vault = root / "vault"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    out = root / "d.html"
    assert run("explore", str(vault), "-o", str(out), "--today", TODAY, "--no-open")[0] == 0
    data = json.loads(DATA.search(out.read_text(encoding="utf-8")).group(1))
    return vault, {f["key"]: f for f in data["flows"]}


def test_the_example_flow_opens_with_its_two_groups_in_the_order_the_page_writes_them(built):
    _, flows = built
    assert flows["FLO-001"]["groups"] == [
        {"name": "Channels", "lanes": ["APP-website", "APP-call-center", "APP-kiosks"]},
        {"name": "Lookups", "lanes": ["APP-vessel-schedule", "APP-customer-identity", "APP-pricing"]}]
    assert all(f["groups"] == [] for k, f in flows.items() if k != "FLO-001")


def test_the_checker_reads_the_example_page_with_no_unreadable_line_and_no_new_finding(built, tmp_path):
    vault, _ = built
    catalog = readers.read_catalog(cli.load_vault(vault), {})
    problems = []
    tree = mermaid.parse_tree(catalog.flows["FLO-001"], problems)
    assert not [p for p in problems if "Unreadable" in p.text] and len(tree.boxes) == 2
    # the same page with the boxes taken out checks the same: grouping is a drawing, not a behavior
    plain = tmp_path / "plain"
    shutil.copytree(vault, plain)
    page = plain / FLO_001
    text = page.read_text(encoding="utf-8")
    for box in re.findall(r"^    box .*\n(?:        participant .*\n)+    end\n", text, flags=re.M):
        text = text.replace(box, "".join(line[4:] + "\n" for line in box.splitlines()[1:-1]))
    page.write_text(text, encoding="utf-8")
    assert "box " not in page.read_text(encoding="utf-8")

    def findings(path):
        out = run("check-slice", "--all", "--vault", str(path), "--today", TODAY)[1]
        return sorted(re.sub(r":\d+:", ":N:", line) for line in out.splitlines() if re.match(r"F\d+ ", line))
    assert findings(vault) == findings(plain) and findings(vault)


def test_mermaid_itself_draws_the_example_page(built):
    out = run("check", "--vault", str(built[0]), "--today", TODAY)[1]
    assert "E604" not in out


def test_a_box_of_one_lane_or_of_lanes_the_plan_does_not_draw_is_no_group(built, tmp_path):
    vault, _ = built
    page = tmp_path / "v"
    shutil.copytree(vault, page)
    flow = page / FLO_001
    flow.write_text(flow.read_text(encoding="utf-8").replace("    box Lookups\n        participant VS as Vessel schedule\n        participant CI as Customer identity\n        participant P as Pricing\n    end\n",
                                                             "    box Lookups\n        participant VS as Vessel schedule\n    end\n"), encoding="utf-8")
    flow.write_text(flow.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    out = tmp_path / "d.html"
    assert run("explore", str(page), "-o", str(out), "--today", TODAY, "--no-open")[0] == 0
    data = json.loads(DATA.search(out.read_text(encoding="utf-8")).group(1))
    groups = {f["key"]: f for f in data["flows"]}["FLO-001"]["groups"]
    assert [g["name"] for g in groups] == ["Channels"]  # Lookups is left with one lane: not a group


def test_the_conventions_and_the_flow_writing_skill_name_the_rule():
    for path in ("plugin/template/CONVENTIONS.md", "examples/unified-booking/CONVENTIONS.md", "tests/stub-conventions/CONVENTIONS.md"):
        text = (REPO / path).read_text(encoding="utf-8")
        assert "| `box Channels` ... `participant` lines ... `end` |" in text, path
    skill = (REPO / "plugin/skills/boundary/SKILL.md").read_text(encoding="utf-8")
    for want in ("Group what makes sense by default", "an opening `alt` names", "Never group the app the flow is about", "don't group lanes just to save width", "one plain line"):
        assert want in skill, want
    page = (REPO / "examples/unified-booking" / FLO_001).read_text(encoding="utf-8")
    assert "Channels groups the website, call center desktop and port kiosks; Lookups groups Pricing, Customer identity and Vessel schedule." in page
