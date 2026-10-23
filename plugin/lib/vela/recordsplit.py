"""Moving a plan that holds whole session records over to stubs and private notes. Pure: files in, files out.

The Violation this exists to prevent is a Silent Fallback in the migration. Moving the record files is the easy half;
a split that stops there reports success while a person's words still sit on committed pages (a Dissent, a receipt
quoting someone else, an answered ledger row quoting a session). Every such strip is therefore returned as a
`Stripped` with its page, line and words, so the dry run can show the lead exactly what comes out, and nothing is
removed that the report does not name.

`plan(files, lead, today)` takes every committed text of the plan by vault-relative path (the pages, `sources.md`,
`.vela.yaml`, `.gitignore`) and returns `Report.writes`, the new text of every file the split changes or creates,
private notes included. Reading and writing the disk, loading the vault to re-hash handoffs, and git are the edge's
job (`commands/private_records.py`).

What the split does, in order: each whole record becomes a stub plus its private notes (part 1); `[[id#^c07]]`
links become `[[id]] c07`; words that fail the words rule are cut from committed pages (a Dissent unless the lead's,
a receipt's words unless the lead's, an `answered` ledger quote of a session, which becomes a first-hand source
row); `records_split: <date>` and the `.gitignore` line are written.
"""
import datetime
import re
from dataclasses import dataclass, field, replace

from vela import ids, ledger, parse, privaterecord, receipts, sourcerows
from vela.decisions import textedit

HISTORY_TELL = (
    "Your past records are still in this repository's history and in every clone. Read copies published before "
    "today carry them, and so does the gh-pages history. So do your old PR pages and their diffs on GitHub. "
    "Branches not yet merged still hold full records until each is split; vela warns on those (W720). This stops "
    "new ones from being shared and republishes the read copy without them. It doesn't take back old copies. "
    "Removing them means rewriting history and asking GitHub support about PR pages.")
IGNORE_LINE = f"{privaterecord.PRIVATE_DIR}/"
SOURCES_FILE = "sources.md"
DISSENT, RECEIPT, ANSWERED_QUOTE = "dissent", "receipt", "answered quote"

_RECORD_PATH = re.compile(r"^sessions/[^/]+\.md$")
_WORDS_LINE = re.compile(r"^(?P<head>\s*- \*\*(?P<label>Decision|Dissent):\*\* )(?P<value>.*?)(?P<tail>\s*)$")
_QUOTED_SOURCE = re.compile(r'(?P<key>\bsource:\s*)"(?P<words>[^"]+)"\s+in\s+\[\[(?P<page>[^\]|#]+)\]\]')
_LEDGER_ROW = re.compile(r"^\|\s*(?:Q-|R-)")
_RECORDS_SPLIT_LINE = re.compile(r"^records_split:.*$", re.M)


@dataclass(frozen=True)
class Stripped:
    path: str
    line: int
    what: str  # DISSENT, RECEIPT or ANSWERED_QUOTE
    words: str


@dataclass(frozen=True)
class Report:
    writes: dict
    stripped: list
    links: int
    sources_added: list
    records: list
    split_date: str
    handoff_rows: list = field(default_factory=list)  # filled by the edge, which re-hashes the manifests


def replace_report(report, **changes):
    """The report with some fields changed: the edge adds the handoff rows it re-hashed."""
    return replace(report, **changes)


# ---- small pure writers ------------------------------------------------------------------------------------------

def split_date(record_dates, today):
    """The later of `today` and the day after the newest record the split touched: a plan whose records are dated
    ahead of today still has every one of them earlier than this date, so all of them are exempt."""
    newest = max((datetime.date.fromisoformat(d) for d in record_dates), default=None)
    day = datetime.date.fromisoformat(today)
    if newest is not None and newest + datetime.timedelta(days=1) > day:
        day = newest + datetime.timedelta(days=1)
    return day.isoformat()


def with_records_split(yaml_text, date):
    """`.vela.yaml` with one `records_split:` line, added or replaced; every other line and comment kept."""
    line = f"records_split: {date}"
    if _RECORDS_SPLIT_LINE.search(yaml_text):
        return _RECORDS_SPLIT_LINE.sub(line, yaml_text, count=1)
    return yaml_text + ("" if yaml_text.endswith("\n") or not yaml_text else "\n") + line + "\n"


def with_ignore_line(gitignore_text):
    """`.gitignore` with the line that keeps the private notes out of git, once."""
    if IGNORE_LINE in gitignore_text.split("\n"):
        return gitignore_text
    return gitignore_text + ("" if gitignore_text.endswith("\n") or not gitignore_text else "\n") + IGNORE_LINE + "\n"


def updated_manifest(text, before, after):
    """A handoff manifest with a row's hash replaced only when the row still held the hash the vault had before the
    split (nobody had changed the item since the handoff) and the split changed it. Any other change since the
    handoff stays for `vela handoff verify` to report."""
    out = []
    for line in text.split("\n"):
        cells = parse.split_row(line) if line.lstrip().startswith("|") else []
        item = cells[0] if len(cells) == 5 else None
        if item in before and item in after and cells[4] == before[item] != after[item]:
            line = line.rstrip()[:-len(before[item]) - 2] + f"{after[item]} |"
        out.append(line)
    return "\n".join(out)


# ---- finding the records ---------------------------------------------------------------------------------------

def _whole_records(files):
    """{id: path} of the records that still hold their words in the committed file."""
    found = {}
    for path, text in files.items():
        if not _RECORD_PATH.match(path):
            continue
        try:
            meta = privaterecord.stub_meta(text)
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from exc
        if meta.get("type") == "session" and "captures_sha256" not in meta:
            found[str(meta.get("id") or path[len("sessions/"):-3])] = path
    return found


def _split_records(files, whole):
    """The stub and private-notes writes, and the date of each record."""
    writes, dates = {}, []
    for record_id, path in sorted(whole.items()):
        if privaterecord.private_path(record_id) in files:
            raise ValueError(f"{record_id} already has notes at {privaterecord.private_path(record_id)}, so I won't "
                             "overwrite them with a second copy of the record.")
        both = privaterecord.split_record(files[path])
        writes[path], writes[privaterecord.private_path(record_id)] = both.stub, both.private
        dates.append(str(privaterecord.stub_meta(both.stub).get("date", "")))
    return writes, [d for d in dates if d]


# ---- stripping words -------------------------------------------------------------------------------------------

def _may_keep(who, lead):
    return bool(lead) and receipts.handle_ref(who) == receipts.handle_ref(lead)


def _strip_words_line(line, lead):
    """(new line, what, words) for a Decision or Dissent line that carries someone else's words, else None."""
    found = _WORDS_LINE.match(line)
    if not found:
        return None
    value = found["value"]
    if found["label"] == "Decision":
        receipt = receipts.parse_decision(value)
        if receipt is None or not receipt.words or _may_keep(receipt.who, lead):
            return None
        bare = receipts.decision_value(receipt.record, receipt.ref, receipt.who, None, receipt.stated_in)
        return found["head"] + bare + found["tail"], RECEIPT, receipt.words
    dissent = receipts.parse_dissent(value)
    if dissent is None or not dissent.words or _may_keep(dissent.who, lead):
        return None
    return found["head"] + receipts.dissent_value(dissent.who, dissent.date) + found["tail"], DISSENT, dissent.words


class _FirstHand:
    """The first-hand `sources.md` rows an answered quote points at: one per person, found or added."""

    def __init__(self, files, today):
        self.path = next((p for p in files if p == SOURCES_FILE or p.endswith("/" + SOURCES_FILE)), None)
        self.text = files.get(self.path, "")
        self.today = today
        self.numbers = list(files.values())
        self.added = {}

    def row_for(self, handle, where):
        """The SRC-nn of the first-hand row for `handle`, adding it when sources.md has none."""
        if not handle:
            raise ValueError(f"{where} is answered with a quote and no By, so there is no one whose first-hand "
                             "source it could point at. Write who answered it in the By cell, then split again.")
        if handle in self.added:
            return self.added[handle]
        found = self._existing(handle)
        if found:
            return found
        if self.path is None:
            raise ValueError(f"{where} is answered with a quote from a session, and this plan has no sources.md "
                             "to hold the first-hand source that replaces it.")
        ident = ids.next_id("SRC", self.numbers)
        self.text = self._with_row(ident, handle)
        self.numbers.append(self.text)
        self.added[handle] = ident
        return ident

    def _table(self):
        lines = self.text.split("\n")
        index = textedit.find_table(lines, sourcerows.CORE)
        if index is None:
            raise ValueError("sources.md has no register table (ID | Title | Owner | Date | Kind ...), so the "
                             "first-hand source that replaces an answered quote has nowhere to go.")
        return lines, index, parse.split_row(lines[index])

    def _existing(self, handle):
        lines, index, header = self._table()
        for line in lines[index + 2:]:
            if not line.lstrip().startswith("|"):
                break
            row = sourcerows.read(header, parse.split_row(line))
            if row.kind == "exists" and row.location.casefold() == f"first-hand: {handle}".casefold():
                return row.id
        return None

    def _with_row(self, ident, handle):
        _, _, header = self._table()
        values = {"ID": ident, "Title": f"First-hand knowledge of {receipts.handle_ref(handle)[1:]}", "Owner": handle,
                  "Date": self.today, "Kind": "exists", "Location": f"first-hand: {handle}"}
        row = textedit.row(*[values.get(name, "") for name in header])
        return textedit.add_row(self.text, sourcerows.CORE, row)


def _page_stripped(path, text, lead, session_ids, first_hand):
    """(new text, [Stripped]) for one committed page: Decision and Dissent words, then answered ledger quotes."""
    out, stripped, in_ledger = [], [], False
    for number, line in enumerate(text.split("\n"), start=1):
        if line.startswith("#"):
            in_ledger = line.lstrip("#").strip() == ledger.HEADING
        cut = _strip_words_line(line, lead)
        if cut is not None:
            line = cut[0]
            stripped.append(Stripped(path, number, cut[1], cut[2]))
        elif in_ledger and _LEDGER_ROW.match(line):
            line = _strip_answered_quote(path, number, line, session_ids, first_hand, stripped)
        out.append(line)
    return "\n".join(out), stripped


def _strip_answered_quote(path, number, line, session_ids, first_hand, stripped):
    cells = parse.split_row(line)
    found = _QUOTED_SOURCE.search(line)
    if len(cells) != len(ledger.HEADER) or cells[1] != "answered" or not found or found["page"].strip() not in session_ids:
        return line
    ident = first_hand.row_for(receipts.handle_ref(cells[3]), cells[0])
    stripped.append(Stripped(path, number, ANSWERED_QUOTE, found["words"]))
    return line[:found.start()] + f"{found['key']}{ident}" + line[found.end():]


# ---- the plan ----------------------------------------------------------------------------------------------------

def plan(files, lead, today, branch_texts=()):
    """The split of a whole plan. `files` is every committed text by vault-relative path; `lead` is the lead's handle
    ("" when unknown, which keeps no one's words); `branch_texts` are other branches' ID tokens, so a new SRC-nn never
    takes a number another open branch holds. Raises ValueError, naming the record or row, for what it cannot move."""
    whole = _whole_records(files)
    writes, dates = _split_records(files, whole)
    session_ids = {path[len("sessions/"):-3] for path in files if _RECORD_PATH.match(path)}
    first_hand = _FirstHand(files, today)
    first_hand.numbers += list(branch_texts)
    stripped, links = [], 0
    for path, text in sorted(files.items()):
        if not path.endswith(".md") or path.startswith(("sessions/", "handoffs/")):
            continue
        linked, count = privaterecord.rewrite_anchor_links(text)
        cut, found = _page_stripped(path, linked, lead, session_ids, first_hand)
        links += count
        stripped += found
        if cut != text:
            writes[path] = cut
    if first_hand.added:
        writes[first_hand.path] = first_hand.text
    if whole:
        date = split_date(dates, today)
        writes[".vela.yaml"] = with_records_split(files.get(".vela.yaml", ""), date)
    else:
        date = ""
    ignored = with_ignore_line(files.get(".gitignore", ""))
    if ignored != files.get(".gitignore"):
        writes[".gitignore"] = ignored
    return Report(writes, stripped, links, list(first_hand.added.values()),
                  sorted(whole), date)
