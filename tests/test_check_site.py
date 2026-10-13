"""tools/check_site.py: what the pre-push hook runs on the published example site instead of the gate."""
import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_site", REPO / "tools" / "check_site.py")
check_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_site)


def site_with(tmp_path, name, text):
    site = tmp_path / "site"
    site.mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text("<p>hello</p>", encoding="utf-8")
    (site / name).write_text(text, encoding="utf-8")
    return site


def test_a_clean_site_passes(tmp_path):
    site = site_with(tmp_path, "dashboard.html", "<a href='../heron-desk/docs/plan.md'>plan</a> <a href='https://example.com'>x</a>")
    assert check_site.main([str(site)]) == 0


def test_each_kind_of_leak_is_refused_and_named(tmp_path, capsys):
    cases = {
        "home.html": "see /Users/someone/Code/vault",
        "tmp.html": "built from /private/tmp/x",
        "token.html": "ghp_" + "a" * 36,
        "url.html": "https://user:secret@github.com/o/r.git",
        "script.html": "<script src='https://cdn.example.com/x.js'></script>",
        "style.html": "<style>@import url(//fonts.example.com/a.css)</style>",
        "notes.md": "# a markdown file",
    }
    for name, text in cases.items():
        site = site_with(tmp_path / name, name, text)
        assert check_site.main([str(site)]) == 1, name
        assert name in capsys.readouterr().err, name


def test_a_private_word_named_by_the_caller_is_refused(tmp_path):
    site = site_with(tmp_path, "dashboard.html", "Built by Someone Private")
    assert check_site.main([str(site), "--forbid", "someone private"]) == 1
    assert check_site.main([str(site), "--forbid", "nobody"]) == 0


def test_a_folder_with_no_page_fails(tmp_path):
    (tmp_path / "empty").mkdir()
    assert check_site.main([str(tmp_path / "empty")]) == 1
