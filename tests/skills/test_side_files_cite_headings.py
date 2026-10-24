"""A side file that says "section 4" points at a number that moves when its skill is trimmed (Fossil Comments, made by
the renumbering: close's READER.md once told a reader to skip a section that had become two). Side files cite headings;
a number that remains must still name a numbered heading in the skill's own SKILL.md."""
import re

from conftest import REPO

SKILLS = REPO / "plugin" / "skills"
SIDE_FILES = sorted(p for p in SKILLS.glob("*/*.md") if p.name != "SKILL.md")
NUMBERED = re.compile(r"^## (\d+)\. ", re.MULTILINE)
CITED = re.compile(r"\bsections? (\d+)\b", re.IGNORECASE)


def test_there_are_side_files_to_check():
    assert len(SIDE_FILES) >= 8


def test_every_section_number_a_side_file_cites_is_a_numbered_heading_in_its_skill():
    stale = []
    for side in SIDE_FILES:
        headings = set(NUMBERED.findall((side.parent / "SKILL.md").read_text(encoding="utf-8")))
        stale += [f"{side.parent.name}/{side.name}: section {n}" for n in CITED.findall(side.read_text(encoding="utf-8"))
                  if n not in headings]
    assert not stale, f"cite the heading, not the number: {stale}"
