"""Progress and next step: the grid behind vela status, vela next and the progress-map block."""
from conftest import check, edit, findings, run
from vela import progress, render
from vela.model import build
from vela.parse import parse_page

CONFIG = {"initiative": "INI-900", "title": "Mini shop"}
# The medium path: options are written down in a Shape session before a grill. A small plan asks one question in a grill.
MEDIUM = {**CONFIG, "size": {"band": "medium", "because": "[[2026-01-01-grill-a]] c1", "date": "2026-01-01"}}
NEW_BLOCK = "<!-- generated:progress-map sha=00000000: do not edit, run vela render -->\n<!-- /generated:progress-map -->\n"


def app_page(name, state="assumption", sources="[SRC-01]", body="", change="changed"):
    lines = [f"id: APP-{name}", "type: app-building-blocks", f"title: {name.capitalize()}", f"state: {state}",
             'owner: "@t"', "authored: authored", f"change: {change}"]
    if sources is not None:
        lines.append(f"sources: {sources}")
    return f"05-building-blocks/{name}-building-blocks.md", "---\n" + "\n".join(lines) + f"\n---\n\n# {name}\n\n{body}"


def contract(cid, consumer, state="decided", options=False):
    extra = "- **Options considered:** versioned (picked); one shared schema: rejected, kiosks lag 6 months\n" if options else ""
    return (f"### {cid} Thing\n\n- **Consumers:** [[{consumer}-building-blocks|{consumer}]]\n- **Change:** new\n"
            f"- **State:** {state}\n{extra}\n")


def unknowns(*entries):
    body = "".join(entries)
    return "11-unknowns-and-risks.md", f"---\nid: unknowns-and-risks\ntype: index\ntitle: Unknowns\nauthored: authored\n---\n\n# Unknowns\n\n{body}"


def unknown(uid, blocks, ask_by="2026-02-01", opened=None):
    extra = f"- **Opened:** {opened} Grill\n" if opened else ""
    return (f"### {uid} Question\n\n- **Question:** Why?\n- **Owner:** @qa (QA lead)\n{extra}- **State:** open\n"
            f"- **Ask by:** {ask_by}\n- **Blocks:** {blocks}\n\n")


def epic(eid, app, state="decided"):
    return (f"13-epics/{eid}-x.md", f"---\nid: {eid}\ntype: epic\ntitle: X\nstate: {state}\nowner: \"@t\"\n"
            f"authored: mixed\napps: [APP-{app}]\ndelivers: [CON-001]\n---\n\n# {eid}\n")


def vault_of(*pages, config=CONFIG):
    return build([parse_page(path, text) for path, text in pages], config)


def only(vault, app_id, as_of="2026-01-15"):
    [row] = [r for r in progress.grid(vault, as_of) if r.app.id == app_id]
    return row


def test_no_sources_means_discover():
    row = only(vault_of(app_page("shop", sources=None)), "APP-shop")
    assert (row.rule, row.mode, row.subject) == (2, "discover", "APP-shop")
    assert row.reason == "Shop lists no sources yet."


def test_an_overdue_unknown_comes_first():
    vault = vault_of(app_page("shop", sources=None), unknowns(unknown("UNK-001", "[[shop-building-blocks|Shop]]")))
    row = only(vault, "APP-shop", as_of="2026-02-02")
    assert (row.rule, row.mode, row.subject) == (1, "probe", "UNK-001")
    assert "due an answer by 2026-02-01" in row.reason


def test_an_item_with_no_options_means_shape():
    row = only(vault_of(app_page("shop"), config=MEDIUM), "APP-shop")  # pins the medium path
    assert (row.rule, row.mode, row.subject) == (3, "shape", "APP-shop")
    assert only(vault_of(app_page("shop", state="inkling"), config=MEDIUM), "APP-shop").reason == "Shop (APP-shop) is only an early idea so far and has no options written down."


def test_options_recorded_before_target_means_discover_for_gate_one():
    # the only source is a session that only dumped, so the pages reach baseline and no further
    dump = ("sessions/2026-01-01-dump.md", "---\nid: 2026-01-01-dump\ntype: session\ndate: 2026-01-01\nmodes: [dump]\nstatus: closed\n---\n")
    page = app_page("shop", state="decided", sources="[2026-01-01-dump]", body=contract("CON-001", "till", "assumption", options=True))
    row = only(vault_of(page, dump), "APP-shop")
    assert (row.rule, row.mode, row.subject) == (4, "discover", "CON-001")
    assert "a grill needs the app at target or later" in row.reason


def test_options_recorded_at_target_means_grill():
    path, text = app_page("shop", state="decided", body=contract("CON-001", "till", "assumption", options=True))
    row = only(vault_of((path, text)), "APP-shop")
    assert (row.rule, row.mode, row.subject) == (5, "grill", "CON-001")


def test_options_label_counts_in_any_case():
    path, text = app_page("shop", state="decided", body=contract("CON-001", "till", "assumption", options=True))
    text = text.replace("**Options considered:**", "**options Considered:**")
    assert only(vault_of((path, text)), "APP-shop").mode == "grill"


def test_a_blocked_item_means_probe_until_its_unknown_is_answered():
    path, text = app_page("shop", state="decided", body=contract("CON-001", "till", "assumption", options=True))
    vault = vault_of((path, text), unknowns(unknown("UNK-002", "[[shop-building-blocks#CON-001 Thing|CON-001]]", "2026-03-01")))
    row = only(vault, "APP-shop")
    assert (row.rule, row.mode, row.subject) == (6, "probe", "UNK-002")
    assert "@qa (QA lead)" in row.reason


def test_a_consumed_contract_still_open_means_wait():
    shop = app_page("shop", state="decided", body=contract("CON-001", "till", "assumption", options=True))
    till = app_page("till", state="decided")
    row = only(vault_of(shop, till), "APP-till")
    assert (row.rule, row.mode, row.subject) == (7, "none", "CON-001")
    assert render.next_cell(vault_of(shop, till), row) == "waits on Thing"


def test_everything_settled_and_no_epic_means_epics():
    row = only(vault_of(app_page("shop", state="decided", body=contract("CON-001", "till"))), "APP-shop")
    assert (row.rule, row.mode, row.subject) == (8, "epics", "APP-shop")


def test_an_epic_not_decided_means_epics():
    shop = app_page("shop", state="decided", body=contract("CON-001", "till"))
    row = only(vault_of(shop, epic("EPC-001", "shop", "draft")), "APP-shop")
    assert (row.mode, row.subject) == ("epics", "EPC-001")
    assert row.reason.startswith("Every interface of Shop is settled, and the epic ") and row.reason.endswith("(EPC-001) is still a draft.")
    done = only(vault_of(shop, epic("EPC-001", "shop")), "APP-shop")
    assert (done.rule, done.mode) == (9, "none")


def test_apps_outside_the_ladder_have_nothing_to_do():
    row = only(vault_of(app_page("stock", state="fact", change="unchanged")), "APP-stock")
    assert (row.stage, row.mode) == ("", "none")


def test_mix_counts_the_page_runtime_page_and_contracts():
    shop = app_page("shop", state="decided", body=contract("CON-001", "till") + contract("CON-002", "till", "fact"))
    runtime = ("06-runtime/apps/shop-runtime.md", "---\nid: RUN-shop\ntype: app-runtime\ntitle: Shop runtime\n"
               "state: inkling\nowner: \"@t\"\nauthored: authored\n---\n\n# Shop runtime\n")
    row = only(vault_of(shop, runtime, config=MEDIUM), "APP-shop")  # pins the medium path
    assert row.mix == (1, 0, 1, 2)
    assert (row.mode, row.subject) == ("shape", "RUN-shop")


def test_oldest_unknown_is_the_first_opened_and_one_with_no_date_comes_last():
    vault = vault_of(app_page("shop", state="decided"), unknowns(
        unknown("UNK-001", "[[shop-building-blocks|Shop]]", "2027-01-01"),
        unknown("UNK-002", "[[shop-building-blocks|Shop]]", "2027-01-01", opened="2026-01-09"),
        unknown("UNK-003", "[[shop-building-blocks|Shop]]", "2027-01-01", opened="2026-01-03")))
    row = only(vault, "APP-shop")
    assert (row.oldest.id, row.opened) == ("UNK-003", "2026-01-03")


def test_malformed_values_never_crash():
    path, text = app_page("shop", state="[a]", sources="not-a-list")
    row = only(vault_of((path, text.replace("change: changed", "change: {a: b}"))), "APP-shop")
    assert row.mode in ("discover", "shape", "none")


def test_best_takes_the_lowest_rule_then_the_earliest_stage():
    parts = "| Container | Job | Contracts served or used | Proposed by | State |\n|---|---|---|---|---|\n| Core | Does it | none | lead | assumption |\n\n"
    a = app_page("alpha", state="decided", body=parts + contract("CON-001", "beta", "assumption", options=True))  # reaches contracts
    b = app_page("beta", state="decided", body=contract("CON-002", "alpha", "assumption", options=True))  # no containers table: boundaries
    rows = progress.grid(vault_of(a, b), "2026-01-15")
    assert progress.best(rows).app.id == "APP-beta"
    settled = app_page("gamma", state="fact", change="unchanged")
    assert progress.best(progress.grid(vault_of(settled), "2026-01-15")) is None


# Through render, on the mini vault.

def add_block(mini):
    edit(mini / "01-goals.md", "## Where it stands\n", "## Progress by app\n\n" + NEW_BLOCK + "\n## Where it stands\n")


def test_progress_map_is_dated_by_the_last_session_and_holds_no_age(mini):
    add_block(mini)
    code, out = run("render", "--vault", str(mini))
    assert code == 0 and "01-goals.md: progress-map" in out, out
    text = (mini / "01-goals.md").read_text(encoding="utf-8")
    block = text[text.index("<!-- generated:progress-map"):text.index("<!-- /generated:progress-map -->")]
    assert "**How sure each app's items are,** as of the last session on January 10, 2026" in block
    assert "| [[till-building-blocks\\|Till]] | named in scope | 0 | 1 | 0 | 0 | none | Discover Till |" in block
    assert " days" not in block
    assert findings(check(mini)[1]) == []
    assert "0 blocks changed" in run("render", "--vault", str(mini))[1]


def test_progress_map_goes_stale_when_an_app_changes(mini):
    add_block(mini)
    run("render", "--vault", str(mini))
    edit(mini / "05-building-blocks/till-building-blocks.md", "state: assumption", "state: inkling")
    assert ("W402", "01-goals.md") in findings(check(mini)[1])
