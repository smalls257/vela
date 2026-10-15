"""`add source`: a row in the register, `| SRC-nn | Title | Owner | Date | Kind | Location |` on `sources.md` (discover
step 2, import; CONVENTIONS "Certainty and sources").

- **A token never reaches a page.** A repository's URL may carry `user:token@` (a clone made with a personal access
  token): that part is stripped from Location before anything is written, and `notices` says so for the CLI to tell
  the lead, because a token in a committed page is a leaked credential.
- **Kind** is `exists`, `intends` or `repo`: whether the document describes what runs today or what someone plans,
  which decides whether what it says can be a fact (an `intends` source only ever gives an assumption).
- **A repo source** is read at a commit: Location `<url>@<sha>`.
- **A first-hand source** (the lead's own knowledge) is `Kind: exists` with Location `first-hand: <handle>`.
- Date defaults to today; numbered `SRC-nn` past every open branch.
"""
import re

from vela import schema as vault_schema
from vela.decisions import textedit
from vela.decisions.schema import Write

PAGE = "sources"
HEADER = ("ID", "Title", "Owner", "Date", "Kind", "Location")
USERINFO = re.compile(r"(?P<scheme>[a-z][a-z0-9+.-]*://)[^/@\s]+@", re.IGNORECASE)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

FIELDS = {"title": "the document's title",
          "owner": "who owns the document: a handle or a team",
          "date": "the document's date, YYYY-MM-DD (default: today)",
          "kind": "exists (describes what runs today), intends (a plan, deck or roadmap) or repo",
          "location": "where it is: `local only`, a URL, `<repo url>@<sha>` for a repo, or `first-hand: <handle>`",
          "capture": "the capture where the lead brought it in",
          "id": "leave null: vela numbers it past every open branch"}
REQUIRED = ("title", "owner", "kind", "location")
EXAMPLE = {"title": "Till firmware", "owner": "@till-team", "kind": "repo",
           "location": "https://github.com/acme/till.git@0a1b2c3"}


def stripped(location):
    return USERINFO.sub(lambda m: m["scheme"], str(location))


def notices(item):
    if stripped(item.get("location") or "") == str(item.get("location") or ""):
        return []
    return ["I left the sign-in token out of the repository's address, so it never reaches a page."]


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    if item["kind"] not in vault_schema.SOURCE_KINDS:
        found.append(textedit.refusal("add-source-kind", "I couldn't tell whether that document says what runs today "
                                                         "or what someone plans.",
                                      f"kind is one of {', '.join(vault_schema.SOURCE_KINDS)}."))
    if item["kind"] == "repo" and not re.search(r"@[0-9a-f]{7,40}$", stripped(item["location"])):
        found.append(textedit.refusal("add-source-repo", "A repository is read at one commit, and I don't have it.",
                                      "Location for a repo is <url>@<sha>: git -C <clone> rev-parse HEAD."))
    if item.get("date") and not DATE.match(str(item["date"])):
        found.append(textedit.refusal("add-source-date", "That date isn't one I can read.", "date is YYYY-MM-DD."))
    path = textedit.page_path(vault, PAGE)
    if path is None or textedit.find_table(vault.text(path).split("\n"), HEADER) is None:
        found.append(textedit.refusal("add-source-page", "The sources page has no register to add this to.",
                                      "sources.md needs its `| ID | Title | Owner | Date | Kind | Location |` table."))
    if item.get("id"):
        refusal = textedit.id_refusal(vault, item["id"], "SRC")
        if refusal is not None:
            found.append(refusal)
    return found


def apply(item, vault, record):
    ident = textedit.new_id(item, vault, "SRC")
    path = textedit.page_path(vault, PAGE)
    line = textedit.row(ident, textedit.cell(item["title"]), textedit.cell(item["owner"]),
                        item.get("date") or textedit.today(vault), item["kind"],
                        textedit.cell(stripped(item["location"])))
    return [Write(path, textedit.add_row(vault.text(path), HEADER, line))]
