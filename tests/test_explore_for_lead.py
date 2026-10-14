"""`vela explore --for-lead` (overhaul Task 21c): the command says what the build reported, in the lead's words.

explore/SKILL.md "What the build reports" used to make the model translate each kind of build line into plain words
on every run, so raw lines ("no design yet for Coach (APP-coach)", "... reports it as E105") reached the lead: a
Leaky Narrative. These tests hold the translation in code, one table row per kind of line the build prints.
"""
import io
import re
import shutil

import pytest

from conftest import REPO, run
from vela import cli, explorereport, say

SNAPSHOT = REPO / "tests/sim/snapshots/trading-coach/after-80b"
TODAY = "2026-10-10"


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, root)
    return root


@pytest.fixture(scope="module")
def resolver():
    return say.Resolver(cli.load_vault(SNAPSHOT))


def test_explore_for_lead_relays_design_not_found(vault):
    code, said = run("explore", str(vault), "--today", TODAY, "--for-lead")
    assert code == 0, said
    assert "No design yet for Coach and TickerTalk" in said
    assert "APP-" not in said and "vela explore:" not in said


# (kind, a line the build prints, words the lead must hear). Every kind explorereport knows has a row here, and every
# row's kind must be the one explorereport picks, so a new kind of build line cannot go unsaid.
ROWS = [
    ("first build", "first build: wrote the pinned positions of 4 apps and parties to .vela/explorer-pins.json. They keep "
     "every app in the same place on every later build; delete the file to lay the map out afresh.",
     "I saved where each app sits on the map, so it stays put next time."),
    ("pinned new", "pinned new positions in .vela/explorer-pins.json: APP-coach", "I saved where Coach sits on the map"),
    ("moved", "moved APP-coach, APP-tickertalk to the nearest free cell in .vela/explorer-pins.json: each stood on another "
     "box, and the map would have drawn them over one another", "Coach and TickerTalk stood on top of"),
    ("computed", "computed positions for APP-coach; nothing keeps them, so the next build may place them differently",
     "may place Coach somewhere else"),
    ("link left out", "a link was left out, 05-building-blocks/coach-building-blocks.md: links: entry 2 is not a link "
     "(vela check reports it as E105)", "A link on the Coach page couldn't be read, so it isn't shown."),
    ("design found", "Coach (APP-coach): using the design docs/tech-design/coach.md, found from design: on its page",
     "Coach's design is docs/tech-design/coach.md"),
    ("no design", "no design yet for Coach (APP-coach), TickerTalk (APP-tickertalk), so Inside this app shows only their "
     "containers. To add one, the app's team runs /vela:design --app <app ID> from the plan's folder (it writes "
     "docs/tech-design/<slug>.md), or point to one with design: on the app page, designs: in .vela.yaml, or "
     "--design <app ID>=<path>.\n  Coach (APP-coach): docs/tech-design/ holds 1 design doc, but none is for this app",
     "No design yet for Coach and TickerTalk"),
    ("warning", "warning: Coach (APP-coach): from design: on its page is docs/x.md, which is not a file (/v/docs/x.md)",
     "Coach: from design: on its page is docs/x.md, which is not a file"),
    ("design status", "APP-coach design docs/tech-design/coach.md: draft, 3 components, 1 things it could not read\n"
     "  line 12, components: a row names no component", "Coach's design (docs/tech-design/coach.md) is marked draft, not complete"),
    ("plan found", "Coach (APP-coach): using the build plan docs/plan/coach-breakdown.md, found beside its design",
     "Coach's build plan is docs/plan/coach-breakdown.md"),
    ("no plan", "no build plan yet for Coach (APP-coach); their Build plan level says so. Point to one with breakdown: on "
     "the app page, breakdowns: in .vela.yaml, or --breakdown <app ID>=<path>.", "No build plan yet for Coach"),
    ("plan status", "APP-coach build plan coach-breakdown.md: complete, 4 stories, 9 tasks, 21 points, 0 things it could not read",
     "Coach's build plan (coach-breakdown.md) is marked complete: 4 stories, 9 tasks, 21 points."),
    ("icon", "APP-coach asks for icon: rocket, which is not in the built-in set; it is drawn by keyword instead",
     "Coach asks for an icon called rocket"),
    ("page far away", "no Open the file links, the vault and the page sit apart under the home folder; build the page "
     "beside the vault to get them", "The page is saved too far from the plan's files, so its 'Open the file' links were "
     "left out. Build it again without -o to get them."),
    ("design far away", "no Open the design doc link for APP-coach, the doc and the page sit apart under the home folder",
     "Coach's design doc is saved too far from the page"),
    ("plan far away", "no Open the plan or Tickets link for APP-coach, the file and the page sit apart under the home folder",
     "Coach's build plan is saved too far from the page"),
    ("gitignore", "this vault's .gitignore lists dashboard.html, so colleagues who pull the repo will not get the page. "
     "Remove that line from .gitignore, or build with --out somewhere else.", "colleagues who pull the repo won't get the page"),
    ("assets", "assets from builtin only (no --assets given), provider builtin, 18 slots, 21 KB inlined, 0 fell back to builtin",
     "All the pictures came from the built-in art."),
    ("assets fell back", "assets from art.config.json, provider acme, 18 slots, 9 KB inlined, 1 fell back to builtin\n"
     "  logo: the file is missing", "1 picture fell back to the built-in art: logo (the file is missing)"),
    ("party", "CON-003 names its provider in running text, \"Brightwater sandbox API\", so the map draws \"Brightwater\". "
     "Add the party under Outside parties in 03-context-and-scope.md and link it as the contract's Provider.",
     "The Brightwater sandbox contract names its provider only in its text"),
    ("draft changed", "draft: 2 pages changed since the copy you opened", "You've changed 2 pages since you opened this copy."),
    ("draft conflicts", "draft: 1 conflict from the last re-open still to settle (your version sits beside each page as .mine.md)",
     "1 conflict from the last re-open is still to settle"),
    ("draft unreadable", "draft: cannot compare with the baseline, the baseline is missing",
     "I couldn't compare your draft with the copy you opened: the baseline is missing"),
    ("vault id", "this vault has no vault_id in .vela.yaml, so the browser keeps its saved marks, layout and Ask "
     "conversations under a name made from the initiative and title: another vault with the same two shares them, and a "
     "new title loses them. Add the line `vault_id: v-0123456789abcd` and commit it; what was saved before moves over once",
     "Adding the line `vault_id: v-0123456789abcd` to .vela.yaml"),
    ("summary", f"wrote /tmp/v/dashboard.html for INI-001 New initiative: 2 apps, 5 contracts, 75 unknowns, 3 epics, "
     f"3 flows, as of {TODAY}.", "I built the page at /tmp/v/dashboard.html for New initiative: 2 apps, 5 contracts, "
     "75 open questions, 3 epics and 3 flows"),
]


@pytest.mark.parametrize("kind,line,expected", ROWS, ids=[r[0] for r in ROWS])
def test_every_report_line_type_has_a_lead_line(kind, line, expected, resolver):
    assert explorereport.kind_of(line) == kind
    plain = explorereport.lead_line(line, resolver)
    assert expected in plain, plain
    assert say.leak_in(plain) is None, plain


def test_every_kind_has_a_row():
    assert {k for k, _, _ in ROWS} == set(explorereport.KINDS)


def test_a_line_no_kind_matches_is_still_resolved_and_said(resolver):
    """A build line added later, before it gets its own wording, still reaches the lead with names, not IDs."""
    line = "a new kind of line about APP-coach"
    assert explorereport.kind_of(line) is None
    assert explorereport.lead_line(line, resolver) == "a new kind of line about Coach"


def test_for_lead_passes_the_leak_check(vault):
    (vault / ".gitignore").write_text("dashboard.html\n", encoding="utf-8")
    page = vault / "05-building-blocks/coach-building-blocks.md"
    page.write_text(page.read_text(encoding="utf-8").replace("title: Coach", "title: Coach\ndesign: docs/nowhere.md", 1),
                    encoding="utf-8")
    code, said = run("explore", str(vault), "--today", TODAY, "--for-lead")
    assert code == 0, said
    lines = [line for line in said.splitlines() if line.strip()]
    assert len(lines) >= 4, said
    for line in lines:
        assert say.leak_in(line) is None, line
    assert "I saved where each app sits on the map, so it stays put next time." in said
    assert "colleagues who pull the repo won't get the page" in said
    assert not re.search(r"\bAPP-", said), said


def test_for_lead_with_serve_is_refused_and_builds_nothing(vault):
    code, said = run("explore", str(vault), "--today", TODAY, "--for-lead", "--serve")
    assert code == 1, said
    assert not (vault / "dashboard.html").exists()
    assert "without --for-lead" in said


def test_json_carries_each_line_with_its_kind_and_plain_words(vault):
    import json
    code, said = run("explore", str(vault), "--today", TODAY, "--json")
    assert code == 0, said
    report = json.loads(said)["report"]
    assert [r["kind"] for r in report][0] == "first build"
    assert report[-1]["kind"] == "summary" and "APP-" not in report[-1]["plain"]


def test_default_output_unchanged(tmp_path):
    """Without --json or --for-lead the command prints exactly what cli.cmd_explore prints."""
    first, second = tmp_path / "a", tmp_path / "b"
    shutil.copytree(SNAPSHOT, first)
    shutil.copytree(SNAPSHOT, second)
    code, said = run("explore", str(first), "--today", TODAY)
    assert code == 0, said
    direct = io.StringIO()
    args = cli.build_parser().parse_args(["explore", str(second), "--today", TODAY])
    assert cli.cmd_explore(args, direct) == 0
    assert said == direct.getvalue().replace(str(second.resolve()), str(first.resolve()))
    assert said.startswith("vela explore: first build: wrote the pinned positions")
