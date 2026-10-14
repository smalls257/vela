"""The tracer on release one: parsed from two bullets, checked by W345 and W347, quoted by W343, and carried in the
handoff so a changed tracer reaches the senior who accepted the slice."""
import shutil
import sys

from conftest import REPO, findings, run
from test_releases import LINK, check, release, vault_with

sys.path.insert(0, str(REPO / "plugin" / "lib"))
from planner import cli, flows, releases  # noqa: E402

BOOKING = "[[booking-building-blocks|Booking]]"
WEBSITE = "[[website-building-blocks|Website]]"
PRICING = "[[pricing-building-blocks|Pricing]]"
CON1 = "[[booking-building-blocks#CON-001 Booking API|Booking API]]"
CON3 = "[[pricing-building-blocks#CON-003 Quote a fare|Quote a fare]]"
TIDEPAY = "[[03-context-and-scope#PTY-01 Tidepay|Tidepay]]"


def flow_page(number, *steps):
    body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    return (f"---\nid: FLO-{number}\ntype: flow\ntitle: Tracer flow {number}\nstate: assumption\nowner: \"@x\"\nauthored: authored\n---\n\n"
            f"# Tracer flow {number}\n\n## Steps\n\n{body}\n")


def add_flows(vault):
    d = vault / "06-runtime" / "flows"
    (d / "FLO-901-site-to-booking.md").write_text(flow_page(
        901, f"{WEBSITE} → {BOOKING}: holds a seat, over {CON1}.", f"{BOOKING} → {PRICING}: asks the fare, over {CON3}."), encoding="utf-8")
    (d / "FLO-902-booking-to-tidepay.md").write_text(flow_page(
        902, f"{BOOKING} → {TIDEPAY}: sends the person to the hosted payment page."), encoding="utf-8")
    (d / "FLO-903-booking-only.md").write_text(flow_page(903, f"{BOOKING} → {PRICING}: asks the fare, over {CON3}."), encoding="utf-8")


def with_bullets(bullets, rows=None):
    text = release("Release one: pilot", rows if rows is not None else [f"{LINK} | all | "])
    return text.replace("- **State:** assumption\n", "- **State:** assumption\n" + "".join(f"- {b}\n" for b in bullets), 1)


def vault_for(tmp_path, bullets, **kw):
    """The example with its slice pages taken out: these tests are about the releases page's own tracer, which is how
    a vault reads its slices until it has slice pages (test_slices.py covers the pages)."""
    vault = vault_with(tmp_path, with_bullets(bullets, **kw))
    shutil.rmtree(vault / "slices")
    add_flows(vault)
    return vault


def codes(vault):
    return check(vault)


def test_tracer_bullet_parses_flows_in_order_words_and_what_is_left_out(tmp_path):
    vault = vault_for(tmp_path, [
        "**Tracer:** [[FLO-901-site-to-booking|FLO-901]], [[FLO-902-booking-to-tidepay|FLO-902]], a person holds a seat and pays",
        "**Not in the tracer:** Pricing (APP-pricing, CON-003): waits on the fare review"])
    first = releases.releases(cli.load_vault(vault))[0]
    assert first.tracer_flows == ("FLO-901", "FLO-902")
    assert first.tracer_words == "a person holds a seat and pays"
    assert first.tracer_none == "" and first.tracer_given
    left = first.not_in_tracer[0]
    assert left.ids == ("APP-pricing", "CON-003") and left.reason == "waits on the fare review"


def test_plain_words_none_and_a_bullet_alone_do_not_make_a_release(tmp_path):
    assert releases.read_tracer("a person gets the digest, no flow page yet") == ((), "a person gets the digest, no flow page yet", "")
    assert releases.read_tracer("none, the date is set by the CISO") == ((), "", "the date is set by the CISO")
    assert releases.read_tracer("[[FLO-901-x|FLO-901]]") == (("FLO-901",), "", "")
    vault = vault_with(tmp_path, "## Notes\n\n- **Tracer:** a thought\n\n" + release("Release one", [f"{LINK} | all | "]))
    assert [r.name for r in releases.releases(cli.load_vault(vault))] == ["Release one"]


def test_w345_fires_when_release_one_has_no_tracer_bullet(tmp_path):
    assert "W345" in codes(vault_for(tmp_path, []))


def test_w345_is_quiet_for_any_tracer_bullet(tmp_path):
    for n, bullet in enumerate(["**Tracer:** none, the date is set by an outside gate", "**Tracer:** a person holds a seat, no flow page yet",
                                "**Tracer:** [[FLO-903-booking-only|FLO-903]], one fare quote"]):
        assert "W345" not in codes(vault_for(tmp_path / str(n), [bullet])), bullet


def test_no_releases_means_no_w345(tmp_path):
    vault = vault_with(tmp_path, "")
    assert "W345" not in codes(vault)


def test_w347_fires_for_each_app_and_contract_the_tracer_crosses_that_release_one_does_not_deliver(tmp_path):
    out = check(vault_for(tmp_path, ["**Tracer:** [[FLO-901-site-to-booking|FLO-901]], hold and quote"]))
    text = "\n".join(line for line in out.split("\n") if "W347" in line)
    assert "APP-website" in text and "APP-pricing" in text and "CON-003" in text
    assert "APP-booking" not in text and "CON-001" not in text, text


def test_w347_is_quiet_when_not_in_the_tracer_names_them(tmp_path):
    vault = vault_for(tmp_path, [
        "**Tracer:** [[FLO-901-site-to-booking|FLO-901]], hold and quote",
        "**Not in the tracer:** Website (APP-website): the team has no capacity yet",
        "**Not in the tracer:** Pricing (APP-pricing, CON-003): waits on the fare review"])
    assert "W347" not in codes(vault)


def test_outside_parties_never_trigger_w347(tmp_path):
    vault = vault_for(tmp_path, ["**Tracer:** [[FLO-902-booking-to-tidepay|FLO-902]], pay"])
    assert flows.passes_through(cli.load_vault(vault), ["FLO-902"]) == (["APP-booking"], [])
    out = check(vault)
    assert "W347" not in out and "Tidepay" not in out


def test_several_flows_union_their_apps_and_contracts(tmp_path):
    v = cli.load_vault(vault_for(tmp_path, []))
    assert flows.passes_through(v, ["FLO-901"]) == (["APP-website", "APP-booking", "APP-pricing"], ["CON-001", "CON-003"])
    assert flows.passes_through(v, ["FLO-902", "FLO-903"]) == (["APP-booking", "APP-pricing"], ["CON-003"])
    assert flows.passes_through(v, ["FLO-901", "FLO-902"])[0] == ["APP-website", "APP-booking", "APP-pricing"]


def test_w347_unions_across_the_tracers_flows(tmp_path):
    out = check(vault_for(tmp_path, ["**Tracer:** [[FLO-902-booking-to-tidepay|FLO-902]], [[FLO-903-booking-only|FLO-903]], pay and quote"]))
    out = "\n".join(l for l in out.splitlines() if " W390 " not in l)  # the example's decided items carry no Why; not what this tests
    assert "APP-pricing" in out and "APP-website" not in out


def test_w343_quotes_the_reason_when_the_requirement_is_listed_not_in_the_tracer(tmp_path):
    plain = check(vault_for(tmp_path / "a", ["**Tracer:** none, x"], rows=[]))
    assert "W343" in plain and "nothing says when it ships" in plain
    listed = check(vault_for(tmp_path / "b", ["**Tracer:** none, x",
                                                "**Not in the tracer:** Hold a seat (CAP-014.FR1): waits on the CISO review"], rows=[]))
    assert "W343" in listed and "waits on the CISO review" in listed and "nothing says when it ships" not in listed


def test_tracer_labels_and_codes_are_known():
    from planner import schema
    assert "Tracer" in schema.PAGE_LABELS and "Not in the tracer" in schema.PAGE_LABELS
    assert "W345" in schema.CODES and "W347" in schema.CODES


def hand_off(vault):
    return run("handoff", "APP-booking", "--vault", str(vault), "--today", "2026-11-20", "--commit", "abc1234", "--replace")


def verify(vault):
    return run("handoff", "verify", "APP-booking", "--vault", str(vault))


def test_handoff_verify_fails_when_the_tracer_changes(tmp_path):
    vault = vault_for(tmp_path, ["**Tracer:** [[FLO-903-booking-only|FLO-903]], one fare quote"])
    code, out = hand_off(vault)
    assert code == 0, out
    assert "TRACER-1 | release |" in (vault / "handoffs" / "APP-booking.md").read_text(encoding="utf-8")
    assert verify(vault)[0] == 0
    page = vault / "04b-releases.md"
    page.write_text(page.read_text(encoding="utf-8").replace("one fare quote", "a fare quote and a hold"), encoding="utf-8")
    code, out = verify(vault)
    assert code == 1 and "TRACER-1" in out, out


def test_handoff_verify_ignores_other_edits_to_the_releases_page(tmp_path):
    vault = vault_for(tmp_path, ["**Tracer:** [[FLO-903-booking-only|FLO-903]], one fare quote"])
    hand_off(vault)
    page = vault / "04b-releases.md"
    page.write_text(page.read_text(encoding="utf-8").replace("Two releases.", "Two releases, maybe three."), encoding="utf-8")
    assert verify(vault)[0] == 0


def test_page_data_carries_release_ones_tracer(tmp_path):
    from planner.explorer import roles_data
    vault = cli.load_vault(vault_for(tmp_path, ["**Tracer:** [[FLO-903-booking-only|FLO-903]], one fare quote",
                                                "**Not in the tracer:** Website (APP-website): later"]))
    tracer = roles_data.release_data(vault, type("K", (), {"page": staticmethod(lambda p: p.id)})())["tracer"]
    assert tracer["flows"] == ["FLO-903"] and tracer["words"] == "one fare quote"
    assert tracer["notIn"][0]["ids"] == ["APP-website"]


def test_w347_skips_an_app_or_contract_that_release_one_leaves_unchanged(tmp_path):
    """An existing app on the tracer's path that no release changes needs no share in release one: it already runs."""
    vault = vault_for(tmp_path, ["**Tracer:** [[FLO-901-site-to-booking|FLO-901]], hold and quote"])
    page = vault / "05-building-blocks" / "pricing-building-blocks.md"
    text = page.read_text(encoding="utf-8")
    page.write_text(text.replace("\nchange: ", "\nchange: unchanged\nold_change: ", 1), encoding="utf-8")
    out = "\n".join(line for line in check(vault).split("\n") if "W347" in line)
    assert "APP-pricing" not in out and "APP-website" in out, out
