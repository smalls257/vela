"""What `vela new` decides before it touches the disk: whether the folder may become a plan, which of its entries
make room for the template, and the template's own files with the lead's name, initiative and handle in them.

The Violation this exists to prevent is the Infected Core: a start-a-plan rule that needs a real folder and a real git
to be tested. These functions take names and text and return answers; `commands/new.py` holds the disk and git.
Refusing a folder that already has a plan, or sits in someone else's repository, is also what keeps a second
`vela new` from overwriting a plan (Silent Fallback: the copy would have looked like success).
"""
import json
import re

from vela import schema

PLACEHOLDER_HANDLE = "@solution-lead"
INBOX = ".inbox"
KEEP_AT_TOP = (".git", INBOX)  # never moved: git's own folder, and the folder the rest goes into
SKIPPED_FILES = (".DS_Store",)
SKIPPED_FOLDERS = ("__pycache__",)
TITLE_QUESTION = "What short name should this initiative go by? A few words, as you would say it to a colleague."
HANDLE_QUESTION = "What's your GitHub handle, the short name after the @?"


class NotAPlanTitle(ValueError):
    """The title cannot head a plan: empty, several lines, or a control character."""


def clean_title(given):
    title = " ".join(str(given or "").split())
    if not title:
        raise NotAPlanTitle("a title needs a few words")
    if any(ord(c) < 32 for c in str(given).replace("\n", " ").replace("\t", " ")):
        raise NotAPlanTitle("a title is plain words, with no control characters")
    return title


def is_initiative(given):
    return bool(schema.INITIATIVE_RE.match(str(given)))


def vela_yaml(template_text, initiative, title):
    """The template's `.vela.yaml` with this plan's initiative and title. The template's line about the first session
    asking for a name goes: the name is given. A JSON string is a valid YAML string, so any title is safe."""
    out, seen = [], set()
    for line in template_text.split("\n"):
        if re.match(r"^initiative:", line):
            out.append(f"initiative: {initiative}")
            seen.add("initiative")
        elif re.match(r"^title:", line):
            out.append(f"title: {json.dumps(title, ensure_ascii=False)}")
            seen.add("title")
        elif line.startswith("# The first session asks for a short name"):
            continue
        else:
            out.append(line)
    if seen != {"initiative", "title"}:
        raise ValueError("the template's .vela.yaml has no initiative and title lines to fill")
    return "\n".join(out)


def with_handle(text, handle):
    return text.replace(PLACEHOLDER_HANDLE, f"@{handle}")


def top_names(paths):
    """The first part of each path: what the template puts at the folder's top level."""
    return sorted({p.split("/", 1)[0] for p in paths})


def clashes(template_paths, existing_names):
    """The folder's own entries that the template needs the name of. Nothing is overwritten: these stop the start."""
    wanted = set(top_names(template_paths))
    return sorted(name for name in existing_names if name in wanted)


def to_inbox(existing_names, tracked_names=()):
    """What the folder already held that the plan keeps out of its commits: everything but git's folder, the inbox
    itself and what the folder's own repository already tracks (moving that would show as deleted)."""
    return sorted(n for n in existing_names if n not in KEEP_AT_TOP and n not in set(tracked_names))


def inbox_clashes(moving, inbox_names):
    return sorted(n for n in moving if n in set(inbox_names))
