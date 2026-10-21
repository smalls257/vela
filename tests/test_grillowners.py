"""The `grills:` block in `.vela.yaml` (vela/grillowners.py): read it, rewrite it, and leave the rest of the file alone."""
import yaml

from vela import grillowners
from vela.grillowners import Entry

HEAD = 'initiative: INI-900\ntitle: Mini shop # the name\nroles:\n  mini-lead: lead\n'


def test_a_block_is_added_at_the_end_and_everything_else_is_kept_as_written():
    text = grillowners.with_entry(HEAD, "CON-022", Entry("@sam", ["@lee"]))
    assert text.startswith(HEAD)
    assert yaml.safe_load(text)["grills"] == {"CON-022": {"owner": "@sam", "join": ["@lee"]}}


def test_a_block_in_the_middle_is_replaced_and_the_keys_after_it_stay():
    text = HEAD + 'grills:\n  "CON-001":\n    owner: "@a"\nstale_after_days: 30\n'
    new = grillowners.with_entry(text, "CON-002", Entry("@b", []))
    read = yaml.safe_load(new)
    assert read["grills"] == {"CON-001": {"owner": "@a"}, "CON-002": {"owner": "@b"}} and read["stale_after_days"] == 30
    assert "# the name" in new and new.endswith("stale_after_days: 30\n")


def test_an_empty_entry_removes_it_and_the_last_one_removes_the_block():
    text = grillowners.with_entry(HEAD, "CON-022", Entry("@sam", []))
    assert grillowners.with_entry(text, "CON-022", Entry()) == HEAD


def test_read_accepts_handles_with_or_without_the_at_sign_and_team_handles():
    found, problems = grillowners.read({"grills": {"CON-1": {"owner": "sam", "join": ["lee", "@org/team"]}}})
    assert problems == [] and found["CON-1"] == Entry("@sam", ["@lee", "@org/team"])


def test_read_names_what_it_cannot_read_instead_of_dropping_it_quietly():
    _, problems = grillowners.read({"grills": ["CON-1"]})
    assert problems and "grills" in problems[0]
    found, problems = grillowners.read({"grills": {"CON-1": {"join": "lee"}}})
    assert found == {} and "list of handles" in problems[0]
