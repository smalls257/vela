"""`vela grill owner`: set who runs a grill and who is asked to join, only through the command."""
import yaml

from conftest import run
from grills_vault import make


def owner(root, *argv):
    return run("grill", "owner", *argv, "--vault", str(root))


def written(root):
    return (yaml.safe_load((root / ".vela.yaml").read_text(encoding="utf-8")) or {}).get("grills")


def test_it_sets_the_owner_and_who_is_asked_to_join(tmp_path):
    root = make(tmp_path)
    code, out = owner(root, "CON-010", "--owner", "mini-lead", "--join", "@mini-qa", "--join", "sam")
    assert code == 0, out
    assert written(root) == {"CON-010": {"owner": "@mini-lead", "join": ["@mini-qa", "@sam"]}}


def test_join_alone_keeps_the_owner_and_owner_alone_keeps_the_list(tmp_path):
    root = make(tmp_path)
    owner(root, "CON-010", "--owner", "@a", "--join", "@b")
    owner(root, "CON-010", "--join", "@c")
    assert written(root) == {"CON-010": {"owner": "@a", "join": ["@c"]}}
    owner(root, "CON-010", "--owner", "@d")
    assert written(root) == {"CON-010": {"owner": "@d", "join": ["@c"]}}


def test_naming_the_owner_among_those_asked_does_not_list_them_twice(tmp_path):
    root = make(tmp_path)
    owner(root, "CON-010", "--owner", "@a", "--join", "@a", "--join", "@b")
    assert written(root) == {"CON-010": {"owner": "@a", "join": ["@b"]}}


def test_clear_puts_the_grill_back_with_the_items_owner(tmp_path):
    root = make(tmp_path)
    owner(root, "CON-010", "--owner", "@a")
    code, out = owner(root, "CON-010", "--clear")
    assert code == 0 and written(root) is None, out


def test_a_page_id_works_as_well_as_an_item_id(tmp_path):
    root = make(tmp_path)
    assert owner(root, "goals", "--owner", "@a")[0] == 0
    assert owner(root, "CAP-1.FR1", "--owner", "@a")[0] == 1  # not in this plan


def test_it_refuses_what_it_cannot_read_and_writes_nothing(tmp_path):
    root = make(tmp_path)
    before = (root / ".vela.yaml").read_text(encoding="utf-8")
    for argv, rule in ((["NOPE", "--owner", "@a"], "grill-item"), (["CON-010", "--owner", "not a handle"], "grill-handle"),
                       (["CON-010", "--join", "@ok", "--join", "bad one"], "grill-handle"), (["CON-010"], "grill-nothing"),
                       (["CON-010", "--clear", "--owner", "@a"], "grill-clear")):
        code, out = owner(root, *argv)
        assert code == 1 and rule in out, (argv, out)
    assert (root / ".vela.yaml").read_text(encoding="utf-8") == before


def test_it_says_what_it_did_in_the_leads_words(tmp_path):
    root = make(tmp_path)
    code, out = run("grill", "owner", "CON-010", "--owner", "@sam-hadley", "--join", "@lee-ng", "--for-lead", "--vault", str(root))
    assert code == 0 and "Receipt delivery: sam hadley runs the grill, with lee ng asked to join." in out
    assert "CON-010" not in out and "@" not in out


def test_a_reader_copy_cannot_change_who_runs_a_grill(tmp_path):
    root = make(tmp_path)
    (root / ".vela").mkdir()
    (root / ".vela" / "workspace.json").write_text("{}", encoding="utf-8")
    code, out = owner(root, "CON-010", "--owner", "@a")
    assert code == 1 and "grill-reader-copy" in out and written(root) is None
