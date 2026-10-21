"""`add source`: a row in the Library register, `| SRC-nn | Title | Owner | Date | Kind | Type | Relates to | Version |
Stored | Location |` on `sources.md` (discover step 2, import; CONVENTIONS "Certainty and sources").

- **The row follows the table's own header.** A register written before the Library columns has six; `--type`,
  `--relates`, `--version` and `--stored` on such a register are refused (naming the columns to add) rather than
  dropped, because a silently dropped column is a Silent Fallback.
- **Type** is spec, design, document, wiki, tracker or link (default `document`). **Relates to** is item IDs that must
  exist. **Version** is a spec's version, `v1.0` or `v1.0 (latest v1.1)`. **Stored** is a file already kept under
  `library/<folder>/`; `vela library add` is what copies a file in, with the owner's yes.

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

from vela import parse, sourcerows
from vela import schema as vault_schema
from vela.decisions import textedit
from vela.decisions.schema import Write

PAGE = "sources"
HEADER = sourcerows.CORE  # a table is found by its first cells; the rest is read by name
FLAGS = {"source_type": "type", "relates": "relates"}
LIBRARY_FIELDS = {"source_type": "Type", "relates": "Relates to", "version": "Version", "stored": "Stored"}
USERINFO = re.compile(r"(?P<scheme>[a-z][a-z0-9+.-]*://)[^/@\s]+@", re.IGNORECASE)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

FIELDS = {"title": "the document's title",
          "owner": "who owns the document: a handle or a team",
          "date": "the document's date, YYYY-MM-DD (default: today)",
          "kind": "exists (describes what runs today), intends (a plan, deck or roadmap) or repo",
          "location": "where it is: `local only`, a URL, `<repo url>@<sha>` for a repo, or `first-hand: <handle>`",
          "source_type": "spec, design, document (default), wiki, tracker or link",
          "relates": "IDs of the items it relates to, separated by spaces (any kind: APP, CAP, CON, PTY, UNK, REL, ...)",
          "version": "a spec's version: `v1.0`, or `v1.0 (latest v1.1)` when a newer one is out",
          "stored": "a file already kept in the vault: library/<specs|designs|documents>/<file>",
          "capture": "the capture where the lead brought it in",
          "id": "leave null: vela numbers it past every open branch"}
REQUIRED = ("title", "owner", "kind")
EXAMPLE = {"title": "Till firmware", "owner": "@till-team", "kind": "repo",
           "location": "https://github.com/acme/till.git@0a1b2c3"}


def stripped(location):
    return USERINFO.sub(lambda m: m["scheme"], str(location))


def notices(item):
    if stripped(item.get("location") or "") == str(item.get("location") or ""):
        return []
    return ["I left the sign-in token out of the repository's address, so it never reaches a page."]


def _register_header(vault):
    """The register's own header cells, or None when sources.md has no Library table."""
    path = textedit.page_path(vault, PAGE)
    if path is None:
        return None
    lines = vault.text(path).split("\n")
    index = textedit.find_table(lines, HEADER)
    header = parse.split_row(lines[index]) if index is not None else None
    return header if header is not None and sourcerows.is_register(header) else None


def _row_probe(item):
    """The item as a Library Row, to ask sourcerows the questions it answers for a register on disk."""
    header = ("ID", "Type", "Stored")
    return sourcerows.read(header, ("", item.get("source_type") or "", item.get("stored") or ""))


def _library_refusals(item, vault, header):
    found = []
    given = [name for key, name in LIBRARY_FIELDS.items() if item.get(key)]
    missing = [name for name in given if name not in header]
    if missing:
        found.append(textedit.refusal("add-source-columns", "This register doesn't have the columns for that yet.",
                                      f"sources.md has no {', '.join(missing)} column; add "
                                      f"`{' | '.join(sourcerows.HEADER)}` as its header first."))
    kind = item.get("source_type") or sourcerows.DEFAULT_TYPE
    if kind not in sourcerows.TYPES:
        found.append(textedit.refusal("add-source-type", f"'{kind}' isn't a type of library item I know.",
                                      f"type is one of {', '.join(sourcerows.TYPES)}."))
    elif item.get("stored") and (problem := sourcerows.stored_problem(_row_probe(item))):
        found.append(textedit.refusal("add-source-stored", "That isn't a path in the library.", problem))
    known = vault.model.known_ids()
    unknown = [i for i in str(item.get("relates") or "").replace(",", " ").split() if i not in known]
    if unknown:
        found.append(textedit.refusal("add-source-relates", f"{', '.join(unknown)} isn't an ID in this plan.",
                                      "relates is the IDs of items that exist (an app, capability, contract, party, "
                                      "unknown or release)."))
    if item.get("version") and kind != "spec":
        found.append(textedit.refusal("add-source-version", "Only a spec carries a version.",
                                      "Drop --version, or set --type spec."))
    return found


def validate(item, vault, record):
    found = textedit.capture_refusals(item, record)
    if item["kind"] not in vault_schema.SOURCE_KINDS:
        found.append(textedit.refusal("add-source-kind", "I couldn't tell whether that document says what runs today "
                                                         "or what someone plans.",
                                      f"kind is one of {', '.join(vault_schema.SOURCE_KINDS)}."))
    if item["kind"] == "repo" and not re.search(r"@[0-9a-f]{7,40}$", stripped(item.get("location") or "")):
        found.append(textedit.refusal("add-source-repo", "A repository is read at one commit, and I don't have it.",
                                      "Location for a repo is <url>@<sha>: git -C <clone> rev-parse HEAD."))
    if not item.get("location") and not item.get("stored"):
        found.append(textedit.refusal("add-source-where", "I don't know where that document is.",
                                      "Give location (a link, or `local only`) or stored (a file under library/)."))
    if item.get("date") and not DATE.match(str(item["date"])):
        found.append(textedit.refusal("add-source-date", "That date isn't one I can read.", "date is YYYY-MM-DD."))
    header = _register_header(vault)
    if header is None:
        found.append(textedit.refusal("add-source-page", "The sources page has no register to add this to.",
                                      "sources.md needs its `| ID | Title | Owner | Date | Kind | ... | Location |` table."))
    else:
        found += _library_refusals(item, vault, header)
    if item.get("id"):
        refusal = textedit.id_refusal(vault, item["id"], "SRC")
        if refusal is not None:
            found.append(refusal)
    return found


def apply(item, vault, record):
    ident = textedit.new_id(item, vault, "SRC")
    path = textedit.page_path(vault, PAGE)
    header = _register_header(vault)
    values = {"ID": ident, "Title": textedit.cell(item["title"]), "Owner": textedit.cell(item["owner"]),
              "Date": item.get("date") or textedit.today(vault), "Kind": item["kind"],
              "Type": item.get("source_type") or "",
              "Relates to": " ".join(str(item.get("relates") or "").replace(",", " ").split()),
              "Version": textedit.cell(item.get("version") or ""), "Stored": textedit.cell(item.get("stored") or ""),
              "Location": textedit.cell(stripped(item.get("location") or ""))}
    line = textedit.row(*[values.get(name, "") for name in header])
    return [Write(path, textedit.add_row(vault.text(path), HEADER, line))]
