"""Completeness on a small plan doesn't count an unwritten releases page it doesn't need."""
from sizing_vault import choose, from_template, write_plan
from vela import cli, completeness


def share(root):
    return completeness.pages(cli.load_vault(root))


def test_small_plan_leaves_out_the_unwritten_releases_page(tmp_path):
    root = from_template(tmp_path)
    small = share(root)
    write_plan(root, config=choose("medium"))
    medium = share(root)
    assert medium.total == small.total + 1


def test_a_written_releases_page_counts_at_any_size(tmp_path):
    root = write_plan(from_template(tmp_path), releases=["2027-01-15"])
    names = completeness.pages(cli.load_vault(root))
    write_plan(root, releases=["2027-01-15"], config=choose("medium"))
    assert completeness.pages(cli.load_vault(root)).total == names.total
