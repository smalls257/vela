"""A GitHub link as a way to open a plan, and what to say when it doesn't work. Pure.

The Violation this prevents is a Paper Tiger setup: a director with a link in an email stuck at "ask the owner to send
a zip". And two Silent Fallbacks: a failed fetch that quietly opens an older copy, and git's own words
("fatal: could not read Username") reaching someone who has never seen a terminal. So the failure is classified here,
each kind has one plain sentence, and nothing ever opens an older copy instead.
"""
import re
from dataclasses import dataclass

NO_GIT, NO_ACCESS, UNREACHABLE = "no-git", "no-access", "unreachable"
NAME = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
LINK = re.compile(rf"^(?:https?://|git@)?(?:www\.)?github\.com[/:](?P<owner>{NAME})/(?P<name>{NAME})(?:/(?:tree|blob)/.*)?/?$")
NO_ACCESS_WORDS = ("repository not found", "authentication failed", "could not read username",
                   "does not appear to be a git repository", "403", "permission denied")
UNREACHABLE_WORDS = ("could not resolve host", "timed out", "connection refused", "network is unreachable",
                     "unable to access", "failed to connect")
SOMEONE = "the person who sent you the link"


@dataclass(frozen=True)
class Repo:
    owner: str
    name: str

    @property
    def label(self):
        return f"{self.owner}/{self.name}"

    @property
    def url(self):
        return f"https://github.com/{self.owner}/{self.name}"


def parse(text):
    """The Repo a GitHub link names, or None for anything else (a folder, a zip, another host)."""
    found = LINK.match((text or "").strip())
    if not found:
        return None
    name = found["name"][:-4] if found["name"].endswith(".git") else found["name"]
    return Repo(found["owner"], name) if name else None


def failure_kind(stderr):
    """NO_ACCESS or UNREACHABLE from git's own words. GitHub answers a private repository you can't read as "not
    found", so anything unrecognized is read as no access, not as a network fault."""
    said = (stderr or "").lower()
    if any(word in said for word in NO_ACCESS_WORDS):
        return NO_ACCESS
    if any(word in said for word in UNREACHABLE_WORDS):
        return UNREACHABLE
    return NO_ACCESS


def message(kind, owner_name):
    if kind == NO_GIT:
        return (f"This computer doesn't have git, so I can't fetch the plan from GitHub. Ask {owner_name} to send the plan "
                "as a file, put it in this folder and say *open it*.")
    if kind == UNREACHABLE:
        return f"I couldn't reach GitHub from this computer. Try again when you're online, or ask {owner_name} to send the plan as a file."
    return (f"GitHub didn't let this computer read the plan. Sign in to GitHub here, or ask {owner_name} to add you, "
            "or to send the plan as a file.")


def owner_of(config, repo):
    """{"name", "contact"} for the stamp: .vela.yaml's owner_contact, else the repository's owner on GitHub with the
    repository's address. Never the director's own git config."""
    contact = str(config.get("owner_contact") or "")
    if contact:
        return {"name": contact, "contact": contact}
    return {"name": f"{repo.owner} on GitHub", "contact": repo.url}
