"""dashboard.html: the explorer page that ships with the vault, so a colleague opens it from git or OneDrive without building.

The failure to prevent is a Paper Tiger: a page that builds but that nobody downstream can get (hidden under an ignored
folder), or that churns on every build (a clock, a path of the builder's machine), so git shows a 3 MB diff for nothing.
"""
import json
import re
import shutil
import zipfile

from conftest import REPO, run
from sharing import git, make_vault

from vela import publish

SNAPSHOT = REPO / "tests/sim/snapshots/trading-coach/after-80b"
TODAY = "2026-10-11"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)


def page_data(path):
    return json.loads(DATA.search(path.read_text(encoding="utf-8")).group(1))


def explore(root, *extra):
    code, said = run("explore", str(root), "--today", TODAY, *extra)
    assert code == 0, said
    return said


# ------------------------------------------------------------------ item 1: where the page is written

def test_explore_writes_dashboard_html_at_the_vault_root_and_nothing_under_planner_but_the_pins(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    explore(vault)
    assert (vault / "dashboard.html").is_file()
    assert not (vault / ".planner" / "explorer.html").exists()


def test_open_the_file_links_resolve_from_the_vault_root(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    explore(vault)
    data = page_data(vault / "dashboard.html")
    paths = [e["path"] for e in data["entities"].values() if e.get("path")]
    assert paths
    # the page builds each link as D.vault + "/" + path, resolved beside the page
    assert all((vault / "dashboard.html").parent.joinpath(data["vault"], path).is_file() for path in paths)


def test_a_custom_out_still_gets_links_that_reach_the_vault(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    explore(vault, "-o", str(tmp_path / "elsewhere" / "page.html"))
    data = page_data(tmp_path / "elsewhere" / "page.html")
    first = next(e["path"] for e in data["entities"].values() if e.get("path"))
    assert (tmp_path / "elsewhere" / data["vault"] / first).resolve() == (vault / first).resolve()


def test_a_gitignore_that_hides_the_dashboard_is_called_out(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    (vault / ".gitignore").write_text("*.html\n", encoding="utf-8")
    assert "lists dashboard.html" in explore(vault)


# ------------------------------------------------------------------ item 2: git tracks it, and a rebuild is identical

def test_the_template_does_not_ignore_the_dashboard_and_git_can_add_it(tmp_path):
    vault = make_vault(tmp_path, "tracked")
    shutil.copy(REPO / "template" / ".gitignore", vault / ".gitignore")
    explore(vault)
    git(vault, "add", "dashboard.html")  # an ignored file would be refused here
    assert "dashboard.html" in git(vault, "ls-files")


def test_two_builds_of_the_same_vault_are_byte_identical_even_the_first_one_that_writes_the_pins(tmp_path):
    vault = make_vault(tmp_path, "twice")
    explore(vault)
    first = (vault / "dashboard.html").read_bytes()
    explore(vault)
    assert (vault / "dashboard.html").read_bytes() == first


def test_a_build_names_no_clock_time_and_no_path_of_the_builder(tmp_path):
    vault = make_vault(tmp_path, "clean")
    explore(vault)
    page = (vault / "dashboard.html").read_text(encoding="utf-8")
    assert str(vault.parent) not in page and str(vault) not in page
    data = page_data(vault / "dashboard.html")
    assert data["freshness"]["checked_at"] == TODAY, "checked to the day: a second would change every build"


def test_the_same_vault_in_two_folders_builds_the_same_page(tmp_path):
    one = make_vault(tmp_path, "one")
    two = tmp_path / "two"
    shutil.copytree(one, two)
    explore(one)
    explore(two)
    assert (one / "dashboard.html").read_bytes() == (two / "dashboard.html").read_bytes()


def test_the_dashboard_itself_is_not_an_uncommitted_change_in_its_own_stamp(tmp_path):
    vault = make_vault(tmp_path, "selfcount")
    explore(vault)
    assert page_data(vault / "dashboard.html")["freshness"]["uncommitted"] == 0
    git(vault, "add", "dashboard.html")
    git(vault, "commit", "-q", "-m", "dashboard")
    explore(vault)
    assert page_data(vault / "dashboard.html")["freshness"]["uncommitted"] == 0


# ------------------------------------------------------------------ item 5: when and from which commit

def test_the_page_says_when_it_was_built_and_from_which_commit(tmp_path):
    vault = make_vault(tmp_path, "stamped")
    explore(vault)
    built = page_data(vault / "dashboard.html")["built"]
    assert built == {"date": git(vault, "log", "-1", "--format=%cs"), "commit": git(vault, "rev-parse", "--short", "HEAD")}


def test_a_vault_with_no_git_names_the_build_day_and_no_commit(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    explore(vault)
    assert page_data(vault / "dashboard.html")["built"] == {"date": TODAY, "commit": ""}


def test_the_shell_has_a_quiet_line_for_it_above_the_banner():
    shell = (REPO / "plugin/lib/vela/explorer/assets/shell.html").read_text(encoding="utf-8")
    main = (REPO / "plugin/lib/vela/explorer/assets/js/main.js").read_text(encoding="utf-8")
    assert shell.index('id="built"') < shell.index('id="fresh"')
    assert "D.built.commit" in main and "D.built.date" in main


# ------------------------------------------------------------------ item 3: publish, open, a reader's close

def publish_vault(tmp_path, name="copy"):
    vault = make_vault(tmp_path)
    out = tmp_path / name
    code, text = run("publish", "--vault", str(vault), "--out", str(out), "--today", TODAY)
    assert code == 0, text
    return vault, out


def test_publish_puts_a_dashboard_in_the_read_copy_built_from_the_published_commit(tmp_path):
    vault, out = publish_vault(tmp_path)
    page = out / "dashboard.html"
    assert page.is_file()
    assert page_data(page)["built"] == {"date": git(vault, "log", "-1", "--format=%cs"), "commit": git(vault, "rev-parse", "--short", "HEAD")}


def test_publish_rebuilds_a_stale_committed_dashboard_from_the_published_pages(tmp_path):
    vault = make_vault(tmp_path)
    (vault / "dashboard.html").write_text("<html>STALE-DASHBOARD-MARKER</html>", encoding="utf-8")
    git(vault, "add", "dashboard.html")
    git(vault, "commit", "-q", "-m", "an old dashboard")
    out = tmp_path / "copy"
    assert run("publish", "--vault", str(vault), "--out", str(out), "--today", TODAY)[0] == 0
    assert "STALE-DASHBOARD-MARKER" not in (out / "dashboard.html").read_text(encoding="utf-8")


def test_publish_uses_the_committed_pages_not_the_working_tree(tmp_path):
    vault = make_vault(tmp_path)
    goals = vault / "01-goals.md"
    goals.write_text(goals.read_text(encoding="utf-8") + "\nUNCOMMITTED-MARKER\n", encoding="utf-8")
    out = tmp_path / "copy"
    assert run("publish", "--vault", str(vault), "--out", str(out), "--today", TODAY)[0] == 0
    assert "UNCOMMITTED-MARKER" not in (out / "dashboard.html").read_text(encoding="utf-8")


def test_two_publishes_of_one_commit_on_different_days_carry_the_same_tree_hash(tmp_path):
    vault = make_vault(tmp_path)
    stamps = []
    for day in ("2026-10-11", "2026-10-12"):
        out = tmp_path / f"copy-{day}"
        assert run("publish", "--vault", str(vault), "--out", str(out), "--today", day)[0] == 0
        stamps.append(json.loads((out / ".planner/published.json").read_text(encoding="utf-8"))["tree_hash"])
    assert stamps[0] == stamps[1], "a reader's freshness check would call a same-commit republish different content"


def test_a_zip_carries_the_dashboard_too(tmp_path):
    vault = make_vault(tmp_path)
    archive = tmp_path / "copy.zip"
    assert run("publish", "--vault", str(vault), "--out", str(archive), "--today", TODAY)[0] == 0
    assert any(name.endswith("/dashboard.html") for name in zipfile.ZipFile(archive).namelist())


def test_the_dashboard_is_not_a_page_a_reader_changed_but_it_travels():
    assert publish.is_excluded(publish.DASHBOARD_PATH)
    assert publish.DASHBOARD_PATH in publish.selected({publish.DASHBOARD_PATH: b"x", "01-goals.md": b"g"})
    assert publish.tree_hash({"a": b"1"}) == publish.tree_hash({"a": b"1", publish.DASHBOARD_PATH: b"anything"})


def test_open_leaves_a_dashboard_in_the_workspace_that_knows_the_publish_it_came_from(tmp_path):
    vault, out = publish_vault(tmp_path)
    ws = tmp_path / "ws"
    code, text = run("open", str(out), "--into", str(ws), "--author", "Sam", "--today", "2026-10-12")
    assert code == 0, text
    built = page_data(ws / "dashboard.html")["built"]
    assert built["commit"] == git(vault, "rev-parse", "--short", "HEAD") and page_data(ws / "dashboard.html")["role"] == "reader"


def test_a_readers_draft_shows_on_the_dashboard_their_close_rebuilds_and_is_not_itself_a_draft(tmp_path):
    _, out = publish_vault(tmp_path)
    ws = tmp_path / "ws"
    assert run("open", str(out), "--into", str(ws), "--author", "Sam", "--today", "2026-10-12")[0] == 0
    assert page_data(ws / "dashboard.html")["draft"]["count"] == 0
    goals = ws / "01-goals.md"
    goals.write_text(goals.read_text(encoding="utf-8") + "\nA reader's new sentence.\n", encoding="utf-8")
    assert run("explore", str(ws), "--today", "2026-10-12")[0] == 0  # what the close skill's last step runs
    draft = page_data(ws / "dashboard.html")["draft"]
    assert draft["count"] == 1, "the rebuilt dashboard is not itself a changed page"


# ------------------------------------------------------------------ item 4: not a vault page

def test_check_search_and_capture_ignore_the_dashboard(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, vault)
    asked = (("check", "--vault", str(vault), "--today", TODAY), ("capture", "--vault", str(vault)))
    untimed = lambda results: [(code, re.sub(r"Took [0-9.]+ s", "", text)) for code, text in results]
    before = untimed([run(*argv) for argv in asked])
    marker = "zebradashboardonlyword"
    (vault / "dashboard.html").write_text(f"<html><body># {marker}\n[broken](missing.md)</body></html>", encoding="utf-8")
    assert untimed([run(*argv) for argv in asked]) == before
    _, found = run("query", "search", marker, "--vault", str(vault))
    assert "dashboard.html" not in found
