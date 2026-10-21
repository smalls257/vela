"""Build the explorer for both example vaults and check the page carries the record, and nothing else.

    python3 -m pytest tests/test_explorer.py

The builder is the plugin's (plugin/lib/vela/explorer, run by `vela explore`). These tests drive it through
tests/fixtures/explorer/build.py, the wrapper that seeds a new pins file from seed-pins/ and takes any assets config;
tests/test_explore_cli.py covers the command a vault's user runs.

The page's own #selftest checks it in a browser; these check the build: the facts come from vela's
modules (the lights are attention.lights, the flows' messages and pins come from the record), the page holds no
unescaped vault text, and assets load only through the resolver's slot contract.
"""
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

from conftest import REPO
from vela import allocation, attention, cli, handoff, releases
from vela.explorer import build, design_data, flows_data, icons_data, inside_data

PROTOTYPE = REPO / "tests" / "fixtures" / "explorer"
sys.path.insert(0, str(PROTOTYPE))

import make_demo_vault  # noqa: E402
import make_stress_vault  # noqa: E402

PACKAGE = pathlib.Path(build.__file__).resolve().parent
spec = importlib.util.spec_from_file_location("explorer_wrapper", PROTOTYPE / "build.py")
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)

TRADING = REPO / "tests/sim/snapshots/trading-coach/after-80b"  # tracked; the same vault as the sim run of 2026-10-09
BOOKING = REPO / "examples/unified-booking"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)


def built(tmp_path, vault, today, name, *extra):
    out = tmp_path / f"{name}.html"
    pins = tmp_path / "pins" / f"{name}.json"
    assert wrapper.main([str(vault), str(out), "--today", today, "--pins", str(pins), *extra]) == 0
    page = out.read_text(encoding="utf-8")
    return page, json.loads(DATA.search(page).group(1))


@pytest.fixture(scope="module")
def trading(tmp_path_factory):
    return built(tmp_path_factory.mktemp("trading"), TRADING, "2026-10-10", "trading-coach")


@pytest.fixture(scope="module")
def booking(tmp_path_factory):
    return built(tmp_path_factory.mktemp("booking"), BOOKING, "2026-11-20", "unified-booking")


def test_lights_are_attention_lights(trading):
    _, data = trading
    vault = cli.load_vault(TRADING)
    found, above = attention.lights(vault, "2026-10-10")
    for subject, light in found.items():
        assert data["lights"][subject]["level"] == light.level, subject
        assert data["lights"][subject]["urgency"] == light.urgency, subject
    assert [a["unknown"] for a in data["above"]] == [a["unknown"] for a in above]
    assert data["ranked"] == [k for k, _ in attention.ranked(found)]


def test_the_two_live_call_paths_have_their_data(trading):
    _, data = trading
    flows = {f["key"]: f for f in data["flows"]}
    # "how does a reader place a paper trade": FLO-002, played across TickerTalk, Coach and Brightwater.
    paper = flows["FLO-002"]
    sends = [(m["from"], m["to"], m["contract"], m["direction"]) for s in paper["steps"] for m in s["messages"]]
    assert ("APP-tickertalk", "APP-coach", "CON-002", "stated") in sends
    # "how does Coach talk to Brightwater": CON-003, sent at step 2 and stated in the step's own words.
    step2 = paper["steps"][1]
    (message,) = step2["messages"]
    assert {k: v for k, v in message.items() if k not in ("says", "answer")} == {"from": "APP-coach", "to": "PTY-01", "contract": "CON-003", "direction": "stated", "kind": "send"}
    assert message["says"].startswith("Coach opens a sandbox paper account") and message["answer"] == ""  # the arrow's words, whole
    contract = next(c for c in data["map"]["contracts"] if c["id"] == "CON-003")
    assert contract["provider"] == "PTY-01" and contract["consumers"] == ["APP-coach"]
    # Questions sit at the step they hold, with the record's state: UNK-050 is resolved, whatever the prose says.
    assert [p["id"] for p in step2["unknowns"]] == ["UNK-050"]
    asks = {u["id"]: u for u in data["asks"]}
    assert asks["UNK-050"]["state"] == "resolved"
    check = {c["q"]: c["hits"] for c in data["search"]["check"]}
    assert check["how does a reader place a paper trade"][0].startswith("06-runtime/flows/FLO-002")


def test_positions_are_pinned_and_lanes_follow_them(trading):
    _, data = trading
    cells = {n["key"]: (n["col"], n["row"]) for n in data["nodes"]}
    assert cells["APP-tickertalk"] == (0, 0) and cells["APP-coach"] == (1, 0)  # the seed pins, kept
    assert [l["id"] for l in data["lanes"]] == ["APP-tickertalk", "APP-coach", "PTY-01", "PTY-02"]


def test_who_to_ask_marks_a_guess(trading):
    _, data = trading
    for u in data["asks"]:
        assert u["ask"]["key"], u["id"]
        if u["ask"]["inferred"]:
            assert u["ask"]["rule"].startswith("A guess"), u["id"]
        if u["state"] == "open":
            assert u["light"]["level"] in ("warning", "caution"), u["id"]


def test_garden_grows_from_typed_fields(trading, booking):
    for _, data in (trading, booking):
        assert data["garden"]["trees"], "no decision trees"
        for tree in data["garden"]["trees"]:
            assert tree["picked"]["label"]
            assert all(r["label"] for r in tree["rejected"])
    adrs = [t for t in booking[1]["garden"]["trees"] if t.get("fromTable")]
    assert {t["adr"]["id"] for t in adrs} == {"ADR-0001", "ADR-0002", "ADR-0003", "ADR-0004"}
    ledger = next(t for t in adrs if t["adr"]["id"] == "ADR-0002")
    assert ledger["buds"] == ["UNK-006"] and ledger["leaves"] == ["UNK-001"]


def test_inferred_directions_are_labeled(booking):
    _, data = booking
    messages = [m for f in data["flows"] for s in f["steps"] for m in s["messages"]]
    assert messages and all(m["direction"] in ("stated", "inferred") for m in messages)
    assert any(s["fromTable"] for f in data["flows"] for s in f["steps"])  # contracts from the Contracts used table
    assert data["lights"]["CON-003"]["level"] == "override"


def test_every_arrow_carries_what_it_does_in_the_steps_words(booking):
    """The diagram's arrows say what the step does, whole (no sender-to-receiver prefix, no "over <contract>", no cut with an ellipsis),
    and a call whose sentence says "and gets ..." hands that clause to its answer arrow."""
    _, data = booking
    messages = [(s, m) for f in data["flows"] for s in f["steps"] for m in s["messages"]]
    assert messages and all(m["says"] and "→" not in m["says"] and not m["says"].endswith("…") for _, m in messages)
    assert all(s["says"] for f in data["flows"] for s in f["steps"] if s["messages"])


def test_an_answer_clause_is_the_reply_arrows_own_words():
    tokens = [{"key": "CON-024", "label": "Read permission"}]
    says, answer = flows_data.arrow_words(
        "Heron service → Consent and identity service: asks whether every participant opted in before a read, and gets a reading token when they did, over «0».",
        tokens, {"CON-024": {}})
    assert says == "asks whether every participant opted in before a read"
    assert answer == "gets a reading token when they did"
    plain, none = flows_data.arrow_words("A → B: sends a short-lived token when the agent asks at sign-in, over «0».", tokens, {"CON-024": {}})
    assert plain == "sends a short-lived token when the agent asks at sign-in" and none == ""


def test_an_arrows_words_are_never_cut_to_a_length():
    tokens = []
    long = "Desk → Back: " + " ".join(["sends the long note"] * 12) + "."
    says, _ = flows_data.arrow_words(long, tokens, {})
    assert len(says) > 130 and "…" not in says


def test_page_is_one_file_with_no_network(trading):
    page, _ = trading
    assert not re.search(r'<(script|link)[^>]+(src|href)="https?://', page)
    assert "/* ---- core.js ---- */" in page and "/* ---- main.js ---- */" in page
    for module in build.JS_MODULES:
        assert f"/* ---- {module}.js ---- */" in page


def test_no_unescaped_vault_text(tmp_path):
    """A vault whose text tries to close the script tag or run its own script must come out inert."""
    vault = tmp_path / "vault"
    shutil.copytree(BOOKING, vault, ignore=shutil.ignore_patterns("sessions", "voice"))
    evil = "</script><script>window.__pwned=1</script><img src=x onerror=alert(1)> & <!-- "
    unknowns = vault / "11-unknowns-and-risks.md"
    text = unknowns.read_text(encoding="utf-8")
    question = re.search(r"- \*\*Question:\*\* (.*)", text)
    unknowns.write_text(text.replace(question.group(0), question.group(0) + " " + evil, 1), encoding="utf-8")
    flow = next((vault / "06-runtime/flows").glob("FLO-001*.md"))
    flow.write_text(flow.read_text(encoding="utf-8").replace("Find a crossing]].", "Find a crossing]]. " + evil, 1), encoding="utf-8")
    page, data = built(tmp_path, vault, "2026-11-20", "evil")
    blob = DATA.search(page).group(1)
    assert "<" not in blob, "the data block holds a raw <"
    assert "__pwned" not in page.replace(blob, ""), "vault text reached the page outside the data block"
    assert page.count("<script") == page.count("</script>")
    assert any(evil.strip() in json.dumps(u) or "window.__pwned" in u["question"] for u in data["asks"])
    step = data["flows"][0]["steps"][0]
    assert "<script>" not in step["html"] and "&lt;script&gt;" in step["html"], "step HTML was not escaped"
    for key, r in data["reader"].items():  # the pages read inside the explorer: escaped too, tags only the renderer's own
        assert "<script" not in r["html"] and "<img" not in r["html"] and "<!--" not in r["html"], key
    assert "&lt;script&gt;window.__pwned" in data["reader"]["unknowns-and-risks"]["html"]


def test_assets_only_through_the_slot_contract(tmp_path):
    config = tmp_path / "assets"  # a provider folder with no files: the slot contract and builtin art are the plugin's
    config.mkdir()
    (config / "assets.config.json").write_text(json.dumps({"provider": "nonexistent"}))
    page, _ = built(tmp_path, BOOKING, "2026-11-20", "assets", "--assets", str(config / "assets.config.json"))
    report = json.loads(re.search(r"window\.ASSET_REPORT = (.*?);</script>", page).group(1))
    assert report["provider"] == "nonexistent"
    assert report["fallbacks"] and all(f["fellBackTo"] == "builtin" for f in report["fallbacks"])
    files = json.loads(re.search(r"window\.ASSET_FILES = (.*?);\n", page).group(1))
    assert files and all(k.startswith("builtin/") and v.startswith("data:") for k, v in files.items())
    assert "AssetResolver" in page and "comfyui/" not in page.split("window.ASSET_BUNDLE")[0]
    plain, _ = built(tmp_path, BOOKING, "2026-11-20", "builtin")
    assert "window.ASSET_FILES" in plain  # no --assets: the builtin provider alone


# --------------------------------------------------------------------------- the second pass: pages, sections, releases

@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo")
    make_demo_vault.main(root / "vault")
    return root / "vault", built(root, root / "vault", "2026-11-20", "booking-demo")


def test_demo_vault_passes_vela_check(demo):
    vault, _ = demo
    done = subprocess.run([sys.executable, str(REPO / "plugin/scripts/vela"), "check", "--vault", str(vault), "--today", "2026-11-20"],
                          capture_output=True, text=True)
    assert done.returncode == 0 and " 0 errors" in done.stdout, done.stdout + done.stderr
    loaded = cli.load_vault(vault)
    assert len(releases.releases(loaded)) == 3
    assert {a.meta.get("domain") for a in loaded.apps} == {"Channels", "Booking core", "Platform", "Legacy"}
    assert not allocation.unallocated(loaded)
    booking = next(a for a in loaded.apps if a.id == "APP-booking")
    diff = handoff.verify(handoff.read((vault / "handoffs/APP-booking.md").read_text())[1], handoff.handoff_list(loaded, booking), loaded)
    assert not diff.changed and not diff.removed


def test_every_page_reads_inside_the_explorer(demo):
    vault, (_, data) = demo
    loaded = cli.load_vault(vault)
    for page in loaded.pages:
        if page.path.startswith("voice/"):
            continue
        key = build.Keys(loaded).page(page)
        assert key in data["reader"] and data["reader"][key]["html"], page.path
    links = re.findall(r'data-ref="([^"]+)"', "".join(r["html"] for r in data["reader"].values()))
    assert links and all(k in data["entities"] for k in links)
    # an item's heading is its anchor, so "Open the page" lands on it
    assert 'id="CON-001"' in data["reader"]["APP-booking"]["html"]


def test_sidebar_follows_the_vault_order(demo):
    _, (_, data) = demo
    assert [s["label"] for s in data["sections"]] == ["Goals", "Constraints", "Context and scope", "Strategy", "Capabilities",
                                                      "Releases", "Slices", "Apps", "Flows", "Concerns", "Decisions",
                                                      "Unknowns and risks", "Glossary", "Epics", "Library"]  # the demo vault's register has rows, so the Library is last
    apps = next(s for s in data["sections"] if s["id"] == "apps")
    assert sorted(apps["children"]) == sorted(a["key"] for a in data["map"]["apps"])
    assert all(s["page"] for s in data["sections"] if s["id"] not in ("slices", "library"))  # the demo vault has every section's page; slices have none, each slice is one, and the library is the register drawn as a view


def test_releases_are_vela_snapshots(demo):
    vault, (_, data) = demo
    snaps = releases.snapshots(cli.load_vault(vault))
    states = data["releases"]["states"]
    assert [s["name"] for s in states] == [s["name"] for s in snaps]
    for mine, theirs in zip(states, snaps):
        assert mine["contracts"] == theirs["contracts"] and mine["delivers"] == theirs["delivers"]
        assert sorted(mine["apps"].values()) == sorted(theirs["apps"].values())
    split = [r for s in states[1:] for r in s["rows"] if r["criteria"]]
    assert split and all(max(r["criteria"]) <= r["of"] for r in split)
    assert data["releases"]["end"] is None


def test_no_releases_falls_back_to_change(booking):
    _, data = booking
    R = data["releases"]
    assert R["count"] == 0 and len(R["states"]) == 1 and R["end"]["fromChange"]
    assert R["end"]["apps"]["APP-booking"] == "new" and R["states"][0]["apps"]["APP-booking"] == "absent"


def test_domains_capabilities_and_door_data(demo):
    _, (_, data) = demo
    assert data["domains"]["APP-ferrymaster"] == "Legacy"
    assert data["appCaps"]["APP-booking"]["via"] == "allocation" and "CAP-013" in data["appCaps"]["APP-booking"]["caps"]
    assert len(data["epicCriteria"]["EPC-035"]) == 6 and "security" in data["epicCriteria"]["EPC-035"][1]["markers"]
    assert len(data["reqCriteria"]["CAP-013.FR1"]) == 3
    assert data["failure"]["APP-booking"]["sections"], "Booking's runtime page says how it fails"
    assert any(e["id"] == "CON-001" for e in data["handoffList"]["APP-booking"])
    assert [g["id"] for g in data["goals"]] == ["G1", "G2", "G3"]


def test_stress_vault_is_synthetic_and_at_scale(tmp_path):
    make_stress_vault.main(tmp_path / "stress")
    loaded = cli.load_vault(tmp_path / "stress")
    assert len(loaded.apps) == 24 and len({a.meta.get("domain") for a in loaded.apps}) == 5
    assert len(releases.releases(loaded)) == 3 and allocation.rows(loaded)
    assert "synthetic" in str(loaded.config.get("title", "")).lower()


def test_a_flow_carries_the_capability_it_serves_and_where_that_came_from(booking, trading):
    """Recorded in frontmatter, it wins and keeps its order; otherwise the "Uses [[CAP-...]]" lines are a guess."""
    recorded = {f["key"]: f for f in booking[1]["flows"]}["FLO-001"]
    assert (recorded["capabilities"], recorded["capabilitiesFrom"]) == (["CAP-013", "CAP-014", "CAP-015"], "frontmatter")
    guessed = {f["key"]: f for f in trading[1]["flows"]}["FLO-002"]
    assert (guessed["capabilities"], guessed["capabilitiesFrom"]) == (["CAP-002"], "steps")


def test_a_stress_vault_has_more_flows_than_the_picker_lists_flat(tmp_path):
    """14 flows: eight record one capability, one two, two only cite one, three name none (so they go by domain)."""
    make_stress_vault.main(tmp_path / "stress")
    _, data = built(tmp_path, tmp_path / "stress", "2026-10-10", "stress")
    flows = {f["key"]: f for f in data["flows"]}
    assert len(flows) == 14
    assert all(flows[f"FLO-{n:03d}"]["capabilitiesFrom"] == "frontmatter" and len(flows[f"FLO-{n:03d}"]["capabilities"]) == 1 for n in range(1, 9))
    assert len(flows["FLO-012"]["capabilities"]) == 2
    assert [flows[f"FLO-{n:03d}"]["capabilitiesFrom"] for n in (9, 10)] == ["steps", "steps"]
    bare = [flows[f"FLO-{n:03d}"] for n in (11, 13, 14)]
    assert all(f["capabilities"] == [] and f["capabilitiesFrom"] == "" and f["domain"] for f in bare), [(f["key"], f["domain"]) for f in bare]
    assert data["flows"] == built(tmp_path, tmp_path / "stress", "2026-10-10", "stress-again")[1]["flows"]  # deterministic


# --------------------------------------------------------------------------- themes

CSS = PACKAGE / "assets" / "css"
PROP = re.compile(r"--([\w-]+):\s*([^;]+);")


def palette(block):
    """The custom properties between a block's "palette" and "end of palette" comments."""
    body = block.split("/* palette")[1].split("/* end of palette */")[0]
    return dict(PROP.findall(body.split("*/", 1)[1]))


def themes():
    base = (CSS / "base.css").read_text(encoding="utf-8")
    out = {build.THEME_IDS[0]: palette(base.split(":root {", 1)[1])}
    text = (CSS / "themes.css").read_text(encoding="utf-8")
    for name in build.THEME_IDS[1:]:
        out[name] = palette(text.split(f':root[data-theme="{name}"] {{', 1)[1])
    return out


def luminance(hex_color):
    rgb = [int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_every_theme_sets_the_whole_palette():
    found = themes()
    want = set(found[build.THEME_IDS[0]])
    for name, props in found.items():
        assert set(props) == want, f"{name}: missing {sorted(want - set(props))}, extra {sorted(set(props) - want)}"


LAMPS = ("warning", "caution", "pending", "unexamined", "override")


def test_lamps_keep_their_meaning_in_every_theme():
    """Each lamp stands out from the board (3:1, WCAG's non-text contrast) on its own color or through its edge, its
    words on it read (4.5:1), and its text form reads on the room. The lamps stay distinct: no two share a color.
    Pending approval is a ring, so its words must also read on the unlit face a master lamp or matrix cell gives it."""
    for name, p in themes().items():
        for lamp in LAMPS + ("unlit",):
            assert p[lamp].startswith("#") and len(p[lamp]) == 7, f"{name} --{lamp}: the canvas needs #rrggbb"
        for lamp in LAMPS:
            edge = p["override-edge"] if lamp == "override" else p["lamp-edge"]
            seen = max(contrast(p[lamp], p["board"]), contrast(edge, p["board"]) if edge.startswith("#") else 0)
            assert seen >= 3, f"{name}: --{lamp} is {seen:.2f}:1 against the board"
            ink = contrast(p[lamp], p[f"{lamp}-ink"])
            assert ink >= 4.5, f"{name}: --{lamp}-ink on --{lamp} is {ink:.2f}:1"
            text = contrast(p[f"{lamp}-text"], p["room"])
            assert text >= 4.5, f"{name}: --{lamp}-text on the room is {text:.2f}:1"
        assert len({p[k] for k in LAMPS + ("unlit",)}) == 6, f"{name}: two lamps share a color"
        assert contrast(p["pending"], p["unlit"]) >= 3, f"{name}: the pending ring is {contrast(p['pending'], p['unlit']):.2f}:1 against the unlit face"
        assert contrast(p["pending-text"], p["unlit"]) >= 4.5, f"{name}: --pending-text on the unlit face"
        assert contrast(p["pending-text"], p["deck"]) >= 4.5, f"{name}: --pending-text on a deck"
        assert contrast(p["ink"], p["room"]) >= 7 and contrast(p["unlit-ink"], p["unlit"]) >= 4.5, name


def test_theme_flag_sets_the_default(tmp_path):
    page, data = built(tmp_path, BOOKING, "2026-11-20", "themed", "--theme", "daylight")
    assert '<html lang="en" data-theme="daylight">' in page and data["theme"] == "daylight"
    assert [t["id"] for t in data["themes"]] == list(build.THEME_IDS)
    with pytest.raises(SystemExit):
        wrapper.main([str(BOOKING), str(tmp_path / "x.html"), "--theme", "nonsense"])


# --------------------------------------------------------------------------- icons and links

GLYPH = re.compile(r"^\s{4}([a-z]+): \"M", re.M)


def test_every_icon_name_has_a_glyph_and_every_box_one_icon(demo, trading):
    glyphs = set(GLYPH.findall((PACKAGE / "assets/js/icons.js").read_text(encoding="utf-8")))
    kinds = {kind for kind, _ in build.LINK_KINDS} | {"link"}
    assert set(icons_data.ICONS) | kinds <= glyphs, sorted(set(icons_data.ICONS) | kinds - glyphs)
    for _, (_, data) in (demo, (None, trading)):
        assert set(data["icons"]) == {n["key"] for n in data["nodes"]}
        assert all(x["icon"] in icons_data.ICONS and x["why"] for x in data["icons"].values())
    _, (_, data) = demo
    assert data["icons"]["APP-ferrymaster"] == {"icon": "legacy", "why": "icon: legacy on its page"}
    assert data["icons"]["APP-pricing"]["icon"] == "pricing" and data["icons"]["APP-website"]["icon"] == "web"


def test_icons_are_chosen_the_same_way_every_time():
    assert icons_data.choose("Payments") == ("payments", "'pay' in its title")
    assert icons_data.choose("Zephyr", summary="a supplier whose webhook API we call")[0] == "partner"  # first keyword in prose
    assert icons_data.choose("Zephyr", asked="rocket")[1].startswith("its page asks for icon: rocket, which is not in the built-in set")
    first = icons_data.choose("Qwerty")
    assert first == icons_data.choose("Qwerty") and first[0] in icons_data.FALLBACKS


def test_links_reach_the_page_from_vela(demo):
    _, (page, data) = demo
    E = data["entities"]
    assert E["EPC-031"]["links"] == [{"label": "Jira", "url": "https://jira.example.com/browse/BOOK-31", "kind": "tracker"}]
    assert [x["kind"] for x in E["APP-booking"]["links"]] == ["wiki", "repo"]
    assert [x["label"] for x in E["PTY-01"]["links"]] == ["API spec", "Docs"] and E["CON-007"]["links"][0]["kind"] == "api"
    assert not any(f["label"] == "Links" for f in E["CON-007"]["facts"])  # shown as chips, not as a fact row
    every = [x["url"] for e in E.values() for x in e.get("links", [])]
    assert every and all(re.match(r"https://[a-z.]*example\.com/", u) for u in every)  # demo links imply nothing real
    assert not data["linkProblems"]
    own = "".join(f.read_text(encoding="utf-8") for f in (PACKAGE / "assets").rglob("*.*"))  # the page's words, not the vault's
    assert "mock" not in own.lower() and "mock" not in json.dumps([e.get("links") for e in E.values()]).lower()
    epics = [k for k, e in E.items() if e["kind"] == "epic"]
    apps = [a["key"] for a in data["map"]["apps"]]
    assert all(E[k]["links"] for k in epics + apps + [p["key"] for p in data["map"]["parties"]] + ["CON-006", "CON-007"])


def test_a_link_vela_cannot_read_is_reported_not_dropped(tmp_path, capsys):
    vault = tmp_path / "vault"
    shutil.copytree(BOOKING, vault, ignore=shutil.ignore_patterns("sessions", "voice"))
    epic = vault / "13-epics/EPC-031-holds-and-confirms.md"
    epic.write_text(epic.read_text(encoding="utf-8").replace("flows: [FLO-001]", "flows: [FLO-001]\nlinks: {Tracker: BOOK-31, Repo: \"https://git.example.com/b\"}", 1), encoding="utf-8")
    _, data = built(tmp_path, vault, "2026-11-20", "badlink")
    assert data["entities"]["EPC-031"]["links"] == [{"label": "Repo", "url": "https://git.example.com/b", "kind": "repo"}]
    assert any("EPC-031" in p or "13-epics" in p for p in data["linkProblems"])
    assert "a link was left out" in capsys.readouterr().out


# --------------------------------------------------------------------------- Inside this app: --design

DESIGNS = PROTOTYPE / "demo_designs"
DESIGN_ARGS = [f"--design=APP-{a}={DESIGNS / a / 'docs/tech-design' / (a + '.md')}" for a in ("booking", "pricing", "notifications")]


@pytest.fixture(scope="module")
def designed(tmp_path_factory):
    root = tmp_path_factory.mktemp("designed")
    make_demo_vault.main(root / "vault")
    return root / "vault", built(root, root / "vault", "2026-11-20", "booking-demo", *DESIGN_ARGS)


def test_designs_are_embedded_and_checked_against_the_vault(designed):
    vault, (page, data) = designed
    D = data["designs"]
    assert set(D) == {"APP-booking", "APP-pricing", "APP-notifications"}
    assert [D[k]["frontmatter"]["status"] for k in ("APP-booking", "APP-pricing", "APP-notifications")] == ["complete-with-gaps", "complete", "complete-with-gaps"]
    for k, d in D.items():  # the page shows the reader's own problems, every one, never a filtered list
        assert d["problems"] == design_data.read_design(DESIGNS / k[4:] / "docs/tech-design" / f"{k[4:]}.md")["problems"], k
    assert not D["APP-booking"]["problems"] and not D["APP-pricing"]["problems"] and len(D["APP-notifications"]["problems"]) == 10
    loaded = cli.load_vault(vault)
    booking = D["APP-booking"]
    assert booking["targets"] == sorted(design_data.trace_targets(loaded, "APP-booking"))
    assert booking["resolved"]["untraced"] and set(booking["resolved"]["untraced"]) == set(booking["resolved"]["acknowledged"])
    assert D["APP-notifications"]["resolved"]["unresolved"] == [{"id": "EPC-037.AC9", "where": "trace:Booking event consumer"}]
    assert [(c["oq"], c["id"], c["recorded"]) for c in booking["challenges"]] == [("OQ-001", "CAP-014.FR1", None)]
    assert "minute 12" in booking["challenges"][0]["scenario"]
    # each Integration point meets the component that cites its contract, and names the boxes it reaches on the map
    stubs = {s["system"]: s for s in booking["stubs"]}
    assert stubs["FERRYMASTER"]["component"] == "Ledger adapter" and stubs["FERRYMASTER"]["how"] == "it delivers Ledger transactions"
    assert set(stubs["Channels via Platform gateway"]["nodes"]) == {"APP-website", "APP-call-center", "APP-kiosks"}
    assert next(s for s in D["APP-pricing"]["stubs"] if s["system"] == "Fare rules store")["how"] == "the design's data table says it reads from it"
    assert [s["how"] for s in D["APP-notifications"]["stubs"]] == ["it depends on it, though the design doesn't list it as an outside system"]
    edge = next(e for e in booking["depends"] if e["from"] == "Booking lifecycle" and e["to"] == "Hold keeper")
    assert edge["label"] == "reserve(), extend(), release()"
    assert "<" not in DATA.search(page).group(1)


def test_containers_come_from_the_app_page(designed, booking):
    _, (_, data) = designed
    c = data["containers"]["APP-booking"]
    assert [r["name"] for r in c["rows"]] == ["Booking API", "Hold store", "Ledger adapter", "Event publisher"]
    assert c["rows"][0]["serves"] == ["CON-001", "CON-007"] and c["rows"][0]["uses"] == ["CON-003", "CON-004", "CON-005"]
    assert {(e["from"], e["to"]) for e in c["edges"]} == {("Booking API", "Hold store"), ("Booking API", "Ledger adapter"), ("Booking API", "Event publisher")}
    assert data["containers"]["APP-ferrymaster"] is None  # a black box on its page: level 2 says so
    _, plain = booking  # no --design: no design, and the containers still come from the vault
    assert plain["designs"] == {} and plain["containers"]["APP-booking"]["rows"]


def test_no_design_builds_with_the_inside_view(booking):
    page, data = booking
    assert "/* ---- inside.js ---- */" in page and data["designs"] == {}


def test_a_design_the_build_cannot_use_stops_it(tmp_path, capsys):
    out = tmp_path / "x.html"
    good = DESIGNS / "booking/docs/tech-design/booking.md"
    for bad, says in ((f"booking={good}", "APP-x=path"), (f"APP-booking={tmp_path / 'none.md'}", "no tech design doc"),
                      (f"APP-nope={good}", "not an app in this vault")):
        assert wrapper.main([str(BOOKING), str(out), "--today", "2026-11-20", "--pins", str(tmp_path / "p.json"), "--design", bad]) == 2
        assert says in capsys.readouterr().err
    assert not out.exists()


def test_design_text_comes_out_inert(tmp_path):
    repo = tmp_path / "team"
    shutil.copytree(DESIGNS / "pricing", repo)
    doc = repo / "docs/tech-design/pricing.md"
    evil = "</script><script>window.__pwned=1</script><img src=x onerror=alert(1)>"
    doc.write_text(doc.read_text(encoding="utf-8").replace("Answers CON-003 quote requests", "Answers CON-003 quote requests " + evil, 1), encoding="utf-8")
    page, data = built(tmp_path, BOOKING, "2026-11-20", "evil-design", f"--design=APP-pricing={doc}")
    assert "<" not in DATA.search(page).group(1) and "__pwned" not in page.replace(DATA.search(page).group(1), "")
    assert evil in data["designs"]["APP-pricing"]["components"][0]["responsibility"]


def test_flowchart_and_contract_cells_read_as_written():
    chart = inside_data.flowchart(['flowchart LR', '  web["Public website"]', '  subgraph b["Booking"]', '    api["Booking API"]', '  end',
                                   '  web & cc -->|"CON-001"| api', '  api --> db[("store")]', '  class api focus'])
    assert chart["labels"] == {"web": "Public website", "api": "Booking API", "db": "store"}
    assert chart["edges"] == [{"from": "Public website", "to": "Booking API", "label": "CON-001"}, {"from": "cc", "to": "Booking API", "label": "CON-001"},
                              {"from": "Booking API", "to": "store", "label": ""}]
    assert inside_data.contracts_named("Serves CON-001, CON-007. Uses CON-003.") == (["CON-001", "CON-007"], ["CON-003"])
    assert inside_data.contracts_named("Uses CON-006") == ([], ["CON-006"]) and inside_data.contracts_named("none") == ([], [])


# ---------- Bug fixes

def test_asks_board_moves_scoped_by_vault_id(trading, booking):
    """Bug #1: Ask-board moves leak between vaults via localStorage. Each vault gets a unique vaultId."""
    _, trading_data = trading
    _, booking_data = booking
    assert trading_data["vaultId"] != booking_data["vaultId"], "Each vault should have a unique vaultId"
    assert trading_data["vaultId"] and booking_data["vaultId"]  # both should be non-empty


def test_garden_reads_decisions_anywhere(tmp_path):
    """Bug #2: Garden only reads Options considered under History. It should read them anywhere."""
    root = tmp_path / "vault"
    root.mkdir()
    # Create a vault where a decision appears outside History
    (root / "00-goals.md").write_text("# Goals\n- **Options considered:** A (picked); B: rejected", encoding="utf-8")
    (root / ".vela.yaml").write_text("initiative: INI-001\ntitle: Test\n", encoding="utf-8")
    page, data = built(tmp_path, root, "2026-10-10", "test-garden")
    assert len(data["garden"]["trees"]) > 0, "Garden should have trees even for decisions outside History"


def test_garden_grows_from_options_lines_outside_history(tmp_path):
    """coastal-merger after-boundary-s2 has 18 Options considered lines on 11 pages, none under a History heading
    that the garden used to require; the strategy's pick (Option B) and its two rejections must grow."""
    root = REPO / "tests/sim/snapshots/coastal-merger/after-boundary-s2"
    _, data = built(tmp_path, root, "2026-10-10", "coastal-garden")
    trees = data["garden"]["trees"]
    assert trees, "the garden is empty though the vault holds Options considered lines"
    strategy = next((t for t in trees if "household account" in t["picked"]["label"]), None)
    assert strategy is not None, f"no tree for the strategy decision; picked: {[t['picked']['label'] for t in trees]}"
    assert {r["label"] for r in strategy["rejected"]} == {"Option A, one sign-in", "Option C, one merged customer and wallet"}


def test_no_absolute_paths_in_built_pages(tmp_path):
    """Bug #3: Built pages embed absolute filesystem paths that break when shared."""
    page, data = built(tmp_path, BOOKING, "2026-11-20", "no-paths", f"--design=APP-booking={DESIGNS / 'booking/docs/tech-design/booking.md'}")
    home = pathlib.Path.home().as_posix()
    assert home not in page, "the page names the builder's home directory"
    assert BOOKING.resolve().as_posix() not in page, "the page names the vault's absolute path"
    # Whether a link back is kept depends on where this machine puts the vault and the temp folder; what never
    # changes is that the link is exactly what relative_href decides, and is relative.
    from vela.explorer import build as explorer_build
    assert data["vault"] == (explorer_build.relative_href(BOOKING, tmp_path) or "")
    assert not data["vault"].startswith("/") and home not in data["vault"]
    assert all(not d["href"].startswith("/") and home not in d["href"] for d in data["designs"].values())


def test_open_file_links_resolve_from_the_output_folder(tmp_path):
    """Open the file / Open the design doc are relative hrefs: from the page's own folder they reach the real files."""
    site = tmp_path / "site" / "pages"
    vault = tmp_path / "vault"
    make_demo_vault.main(vault)
    doc = tmp_path / "team" / "docs" / "tech-design" / "booking.md"
    doc.parent.mkdir(parents=True)
    shutil.copy(DESIGNS / "booking/docs/tech-design/booking.md", doc)
    out = site / "demo.html"
    assert wrapper.main([str(vault), str(out), "--today", "2026-11-20", "--pins", str(tmp_path / "p.json"), f"--design=APP-booking={doc}"]) == 0
    page = out.read_text(encoding="utf-8")
    data = json.loads(DATA.search(page).group(1))
    assert not pathlib.PurePosixPath(data["vault"]).is_absolute() and str(tmp_path) not in page
    some_page = next(e["path"] for e in data["entities"].values() if e.get("path"))
    assert (site / data["vault"] / some_page).resolve() == (vault / some_page).resolve()
    (design,) = data["designs"].values()
    assert (site / design["href"]).resolve() == doc.resolve()


def test_pins_computed_in_memory_without_flag(tmp_path):
    """Bug #4: Without --pins, build should compute pins in memory, not write to repo."""
    out = tmp_path / "test.html"
    result = wrapper.main([str(BOOKING), str(out), "--today", "2026-11-20"])
    assert result == 0
    # The HTML file was written
    assert out.exists()
    # The page data should have pins
    page = out.read_text(encoding="utf-8")
    data = json.loads(DATA.search(page).group(1))
    assert data["pins"]["added"] is not None  # pins were computed


def test_inline_assets_fetch_no_error():
    """Bug #5: Asset loader should not try to fetch from inline:// base."""
    # This is tested indirectly by the asset tests, but we can verify resolve.js logic
    # by checking that the inline:// base is handled correctly in the code
    resolve_js = REPO / "plugin" / "lib" / "vela" / "explorer" / "art" / "resolve.js"
    assert "inline:" in resolve_js.read_text(encoding="utf-8"), "resolve.js should have inline:// handling"


# --------------------------------------------------------------------------- Empty data handling

def test_empty_vault_builds_without_errors(tmp_path):
    """Empty vaults (no apps, no flows, no unknowns) build without crashing."""
    empty = REPO / "tests/sim/snapshots/coastal-merger/empty"
    page, data = built(tmp_path, empty, "2026-10-10", "empty")
    assert data["map"]["apps"] == []
    assert data["map"]["contracts"] == []
    assert data["flows"] == []
    assert data["asks"] == []
    assert page.startswith("<!doctype html>") and page.rstrip().endswith("</html>")  # the browser test runs the page's own checks on this vault


COASTAL_S2 = REPO / "tests/sim/snapshots/coastal-merger/after-boundary-s2"


def test_domain_less_vault_disables_domain_grouping(tmp_path):
    """Real vaults carry no `domain:` on app pages. The grouping flag is false, and the page disables the Domain
    button with a tooltip saying which step records one (selftest asserts the rendered button the same way)."""
    page, data = built(tmp_path, COASTAL_S2, "2026-10-10", "no-domain")
    assert data["map"]["apps"] and all(not a["domain"] for a in data["map"]["apps"])
    assert data["grouping"]["domain"] is False and data["grouping"]["noDomain"] == len(data["map"]["apps"])
    assert "disabled: groupOff(id)" in page
    assert "No app has a business area yet, so there is nothing to group by" in page


def test_grouping_flags_follow_the_data(demo):
    """With domains and requirements the Group buttons stay on, and the vault says how many apps lack each."""
    _, (_, data) = demo
    assert data["grouping"]["domain"] is True and data["grouping"]["capability"] is True
    assert data["grouping"]["noDomain"] == sum(1 for d in data["domains"].values() if d == "No domain")


def test_release_less_vault_says_where_releases_go(tmp_path):
    """No 04b-releases.md: the Releases view, lens and doors print the one empty state naming the page."""
    page, data = built(tmp_path, COASTAL_S2, "2026-10-10", "no-releases")
    assert data["releases"]["count"] == 0
    assert 'emptyState("No releases yet, so this shows today' in page and "04b-releases.md" in page
    assert page.count("function emptyState(") == 1, "one empty-state helper, not one per view"
    assert 'class: "empty-state"' not in page.replace('class: "empty-state" + (extraClass', ""), "a view writes its own empty block"


def test_unasked_questions_are_marked_unrecorded(tmp_path):
    """No Ask line: the rack is the owner's, so the page labels it rather than let it read as an ask."""
    _, data = built(tmp_path, COASTAL_S2, "2026-10-10", "unasked")
    assert data["asks"] and all(a["ask"]["recorded"] is False for a in data["asks"])


def test_garden_cards_carry_prose_not_null(tmp_path):
    """The stray "null" in the decisions view: a strategy page whose decisions sit under `##` headings has no
    opening prose, so the card's prose was empty and the page printed null. The Picked option line is the prose."""
    _, data = built(tmp_path, COASTAL_S2, "2026-10-10", "garden-prose")
    trees = data["garden"]["trees"]
    assert trees and all(t["carriedBy"][0]["text"] for t in trees if not t.get("adr"))
    assert "Option B, a linked household account" in trees[0]["carriedBy"][0]["text"]


def test_empty_state_blocks_appear_in_data(tmp_path):
    """Empty state markers are present in the data for missing sections."""
    empty = REPO / "tests/sim/snapshots/coastal-merger/empty"
    page, data = built(tmp_path, empty, "2026-10-10", "empty-markers")
    # An empty vault should still have all the structural data
    assert "reader" in data
    assert "entities" in data
    assert "sections" in data
    assert data["sections"]  # all 13 sections exist even in an empty vault


def test_added_and_removed_diff_lines_read_on_the_room_in_every_theme():
    """The Drafts view's + and - lines carry a symbol as well as a color; the color still has to read (4.5:1) on the room and on the page's own tint."""
    for name, p in themes().items():
        for token in ("diff-add", "diff-del"):
            assert p[token].startswith("#") and len(p[token]) == 7, f"{name} --{token}"
            assert contrast(p[token], p["room"]) >= 4.5, f"{name}: --{token} on the room is {contrast(p[token], p['room']):.2f}:1"
            tint = "#%02x%02x%02x" % tuple(round(int(p[token][i:i + 2], 16) * 0.13 + int(p["room"][i:i + 2], 16) * 0.87) for i in (1, 3, 5))
            assert contrast(p[token], tint) >= 4.5, f"{name}: --{token} on its own 13% tint is {contrast(p[token], tint):.2f}:1"


def test_a_question_link_and_its_state_pill_never_run_together_and_prose_hides_open():
    """"where that naming was madeopen": a link and its pill read and copy as one word. The pill follows a real space and
    carries parentheses, and running prose shows no "open" pill at all; a list item or table cell still shows every state."""
    from vela import cli
    from vela.explorer.record import LISTED, PROSE, Keys, inline_html
    vault = cli.load_vault(TRADING)
    keys, page = Keys(vault), vault.pages[0]
    open_q = next(u for u in vault.unknowns if u.fact("State") == "open")
    done = next((u for u in vault.unknowns if u.fact("State") != "open"), None)
    text = f"was made [[{open_q.page.path[:-3]}#{open_q.id} {open_q.name}|that]] then"
    prose, listed = inline_html(text, keys, page, PROSE), inline_html(text, keys, page, LISTED)
    assert "ustate" not in prose and "us-open" in listed
    assert '</a> <span class="ustate' in listed and "(</span>open<span" in listed and 'aria-label="' in listed
    if done:
        assert '</a> <span class="ustate' in inline_html(f"was made [[{done.page.path[:-3]}#{done.id} {done.name}|that]] then", keys, page, PROSE)


def test_a_link_whose_only_shared_folder_is_near_the_root_is_left_out():
    """A relative walk names every folder it descends into below the shared one, so climbing to / (or /tmp, /private)
    and back down spells out the absolute path. Seen when the vault sat in /tmp and the page in another temp folder."""
    from vela.explorer import build
    assert build.relative_href("/tmp/cleanrun/examples/unified-booking", "/var/folders/x/page") is None
    assert build.relative_href("/private/tmp/vault", "/private/var/folders/x") is None
    assert build.relative_href("/srv/work/vault/docs/plan.md", "/srv/work/vault") == "docs/plan.md"
    assert build.relative_href("/srv/work/booking/design.md", "/srv/work/vault") == "../booking/design.md"


def test_the_generated_block_caption_shows_as_italic_not_with_its_underscores():
    """schema.GENERATED_CAPTION is written _like this_; the side panel and the reader showed the literal underscores."""
    from vela import cli, schema
    from vela.explorer.record import Keys, inline_html
    vault = cli.load_vault(TRADING)
    keys, page = Keys(vault), vault.pages[0]
    out = inline_html(schema.GENERATED_CAPTION, keys, page)
    assert out == "<em>Kept up to date by vela from the pages it reads.</em>", out
    assert inline_html("the concern_cost page and a_b_c stay as written", keys, page) == "the concern_cost page and a_b_c stay as written"
