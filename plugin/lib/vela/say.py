"""What a command says, in the three modes every new command offers, and the one place the lead-facing rule is held.

The Violation this module exists to prevent is the Leaky Narrative: the 13 October Heron review counted 709 `UNK-`
mentions and 72 check codes in what the lead read, most of them CLI output a model pasted. Adding more "never say a
code" sentences to the skills did not stop it. So the interface itself carries the fix:

- default mode prints lines with codes and IDs, for files, the PR body and CI;
- `--json` prints the structured result the skill reasons over;
- `--for-lead` prints plain lines with every ID resolved to its name first, and then *checks every line it prints*
  against `LEAD_PATTERNS`. A match raises `LeadLeak`, which `cli.main` turns into exit 2, "planner bug: a line meant
  for the lead held an ID", naming the command. A leak fails loudly at its source (Sensor) instead of being counted in
  a paid run months later.

Exit codes (one meaning each, so no command author reinvents them; `cli.main`'s docstring says the same):
0 done; 1 refused or findings, with a plain reason; 2 the tool failed; 3 needs the lead: nothing changed, the choices
are printed, and `--json` carries the `needs_lead` list. `planner check` keeps 0/1/2.

Pure: no disk, git or clock. The resolver is handed a built vault model (or nothing) by its caller.
"""
import json
import re
from dataclasses import dataclass, field

DONE, REFUSED, FAILED, NEEDS_LEAD = 0, 1, 2, 3

# The one copy of the patterns a lead-facing line may never match. `tests/test_conversation_voice.py` and the sim's
# scorecard read the same ideas; this dict is what the `--for-lead` formatter enforces.
LEAD_PATTERNS = {
    "check code": re.compile(r"\b[EWT]\d{3}\b"),
    "gate": re.compile(r"\bGATE-\w+|--gate\b"),
    "capture": re.compile(r"\^c\d+\b"),
    "copy": re.compile(r"\bQ-[A-Z]{3}-\d{2,}(?:@[\w*.-]+)?"),
    "finding": re.compile(r"\bF\d+\.\d+\b"),
    "reviewer row": re.compile(r"\bR-[A-Z]{3}-\d{2,}\b"),
    "item": re.compile(r"\b(?:UNK|CAP|CON|EPC|APP|RUN|FLO|SLC|ADR|ENT|PTY|SV|CST|SRC|INI|R)-\d[\w.]*"
                       r"|\b(?:APP|RUN)-[a-z][\w-]*"),
    "goal": re.compile(r"\bG\d+\b"),
}

# What a reader is told for an ID nothing names, so a sentence never loses its subject and never shows the code.
KIND_WORDS = {"UNK": "an open question", "R": "a risk", "CON": "a contract", "CAP": "a capability", "EPC": "an epic",
              "APP": "an app", "RUN": "an app's runtime page", "FLO": "a flow", "SLC": "a slice", "ADR": "a decision",
              "ENT": "an entity", "PTY": "a party", "SV": "a stored value", "CST": "a constraint", "SRC": "a source",
              "INI": "the initiative", "G": "a goal"}

# Override bullets name the rule they set aside (`GATE-4`, `E316`), and findings quote those bullets. The lead hears what
# the rule protects instead, in the grill skill's own terms.
GATE_WORDS = {"GATE-1": "the stage check", "GATE-2": "the preferred-option check", "GATE-3": "the agenda's yes",
              "GATE-4": "the open-question check", "GATE-5": "the owner's yes"}
_GATE = re.compile(r"\bGATE-\d\b")
_CODE = re.compile(r"\b[EW]\d{3}\b")

_WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\\?\|([^\]]+))?\]\]")
_NAMED_ID = re.compile(r"(?P<name>\S[^()]*?) \((?P<id>[A-Z]{1,3}-[\w.-]+|G\d+)\)")
_ANY_ID = re.compile(r"\b(?:(?:UNK|CAP|CON|EPC|FLO|SLC|ADR|ENT|PTY|SV|CST|SRC|INI|R)-\d[\w.]*"
                     r"|(?:APP|RUN)-[a-z][\w-]*|G\d+)\b")
_TOKEN = re.compile(r"[\w][\w.-]*[\w]")


class LeadLeak(Exception):
    """A line meant for the lead still held a code or an ID after resolution. Always a planner bug, never the vault's."""

    def __init__(self, command, kind, line):
        self.command, self.kind, self.line = command, kind, line
        super().__init__(f"planner bug: a line meant for the lead held an ID ({kind}) in `planner {command}`. "
                         f"The line was: {line}")


def leak_in(text):
    """The first (kind, match) of a lead pattern in `text`, or None."""
    for kind, pattern in LEAD_PATTERNS.items():
        found = pattern.search(text)
        if found:
            return kind, found.group(0)
    return None


def area_reviewer(label):
    """'Data and lawful basis' -> 'the data reviewer': the area's first word is how a lead names that reviewer."""
    return f"the {label.split()[0].lower()} reviewer" if label else "a reviewer"


class Resolver:
    """Turns IDs into the names a lead knows. Built from a vault model, the question catalog and, when a command has
    them, the review findings of this session (`{finding_id: (area_code, question)}`)."""

    def __init__(self, vault=None, findings=None):
        self.vault = vault
        self.findings = dict(findings or {})
        self.catalog = getattr(vault, "catalog", None)
        self.reviewer_rows = self._reviewer_questions(vault)

    @staticmethod
    def _reviewer_questions(vault):
        if vault is None:
            return {}
        from vela import ledger  # the ledger parser needs pages, which only a real vault has
        out = {}
        for page in vault.pages:
            for row in ledger.rows(page):
                if row.kind == "reviewer" and row.get("question"):
                    out.setdefault(row.copy, row.get("question"))
        return out

    def page_title(self, name):
        page = self.vault.page(name) if self.vault is not None else None
        title = page.meta.get("title") if page is not None else None
        return str(title) if title else None

    def name(self, ident):
        """The plain name for one ID, or the words for its kind when nothing names it."""
        if self.vault is not None:
            named = self.vault.name_of(ident)
            if named != ident:
                return named
            title = self.page_title(ident)
            if title:
                return title
        prefix = re.match(r"[A-Z]+", ident)
        return KIND_WORDS.get(prefix.group(0) if prefix else "", "an item")

    def copy(self, match):
        entry_id = match.group(0).split("@", 1)[0]
        entry = self.catalog.entry(entry_id) if self.catalog is not None else None
        return f'the standard question "{entry.question.rstrip("?")}"' if entry else "a standard question"

    def finding(self, match):
        area, question = self.findings.get(match.group(0), ("", ""))
        label = self.catalog.area_label(area) if (self.catalog is not None and area) else area
        who = area_reviewer(label)
        return f"{who} asked {question.rstrip('?')}" if question else f"{who}'s question"

    def reviewer_row(self, match):
        question = self.reviewer_rows.get(match.group(0))
        return f'the reviewer question "{question.rstrip("?")}"' if question else "a reviewer's question"

    @staticmethod
    def rule(match):
        """A rule an override names, said as what it checks: a gate by the grill's words, a code by its meaning."""
        from vela import schema
        word = match.group(0)
        if word in GATE_WORDS:
            return GATE_WORDS[word]
        meaning = schema.CODES.get(word)
        return f'the "{meaning}" check' if meaning else "a check"

    def plain(self, text):
        """`text` with links, IDs, copies, findings, captures and the rules overrides name, said in words. A caller
        with a finding drops its code before calling; a code inside the message (an override quoting `E316`) is
        said by its meaning."""
        text = _WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).replace("\\", ""), text)
        text = _GATE.sub(self.rule, text)
        text = _CODE.sub(self.rule, text)
        text = _NAMED_ID.sub(lambda m: m.group("name"), text)
        text = LEAD_PATTERNS["copy"].sub(self.copy, text)
        text = LEAD_PATTERNS["finding"].sub(self.finding, text)
        text = LEAD_PATTERNS["reviewer row"].sub(self.reviewer_row, text)
        text = LEAD_PATTERNS["capture"].sub("a note in the session record", text)
        if self.vault is not None:
            text = _TOKEN.sub(lambda m: self.page_word(m.group(0)), text)
        return _ANY_ID.sub(lambda m: self.name(m.group(0)), text)

    def page_word(self, word):
        """A page's file name or page ID, said as its title; any other word unchanged. Only hyphenated words count, so a
        plain word that happens to be a page ID ("sources", "index") stays a word."""
        if "-" not in word:
            return word
        if word.lower() in self.vault.by_name:
            return self.page_title(word) or word
        pages = self.vault.by_id.get(word)
        title = pages[0].meta.get("title") if pages else None
        return str(title) if title else word


@dataclass(frozen=True)
class Line:
    """One line of output. `text` is the default mode's line (codes and IDs allowed); `plain` is what the lead hears.
    When `plain` is None the resolver derives it from `text`."""
    text: str
    plain: str = None


@dataclass(frozen=True)
class Refusal:
    """Why a command would not proceed: what the lead hears, what the model does next, and the exact route to set it
    aside. Every refusal carries an override route, because the lead may override any rule (it just goes on record)."""
    rule: str
    plain: str
    fix: str
    override: str = ""

    def as_json(self):
        return {"refused": True, "rule": self.rule, "plain": self.plain, "fix": self.fix, "override": self.override}


@dataclass
class Result:
    """What a command found or did. `wrote` lists the paths it changed; exit 3 promises nothing changed, so a Result
    with exit 3 and anything in `wrote` is refused by `emit` as a planner bug."""
    command: str
    exit: int = DONE
    lines: list = field(default_factory=list)
    refusals: list = field(default_factory=list)
    needs_lead: list = field(default_factory=list)
    wrote: list = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def as_json(self):
        return {"command": self.command, "exit": self.exit, "lines": [line.text for line in self.lines],
                "refusals": [r.as_json() for r in self.refusals], "needs_lead": self.needs_lead,
                "wrote": self.wrote, **self.data}


def lead_lines(result, resolver):
    """Every line the lead would hear, resolved and checked. Raises LeadLeak on the first line that still leaks."""
    said = [r.plain for r in result.refusals] + [line.plain if line.plain is not None else resolver.plain(line.text)
                                                 for line in result.lines]
    for text in said:
        leak = leak_in(text)
        if leak:
            raise LeadLeak(result.command, leak[0], text)
    return said


def check_contract(result):
    """The exit-code promises, held in one place."""
    if result.exit == NEEDS_LEAD and result.wrote:
        raise ValueError(f"planner bug: `planner {result.command}` exited 3 (needs the lead, nothing changed) "
                         f"after writing {', '.join(result.wrote)}")
    if result.exit == NEEDS_LEAD and not result.needs_lead:
        raise ValueError(f"planner bug: `planner {result.command}` exited 3 without saying what the lead must choose")


def render(result, mode, resolver=None):
    """The text `result` prints in `mode` ("default", "json" or "for-lead"). Pure: `commands.emit` does the printing,
    because only the shell writes output."""
    check_contract(result)
    if mode == "json":
        return json.dumps(result.as_json(), indent=2, ensure_ascii=False)
    if mode == "for-lead":
        return "\n".join(lead_lines(result, resolver or Resolver()))
    said = [f"refused ({r.rule}): {r.plain} Fix: {r.fix}" + (f" Override: {r.override}" if r.override else "")
            for r in result.refusals]
    return "\n".join(said + [line.text for line in result.lines])


def add_output_flags(parser):
    """--json and --for-lead, mutually exclusive, on a command's parser."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="the structured result, for the skill to reason over")
    group.add_argument("--for-lead", action="store_true",
                       help="plain lines for the lead: no codes and no IDs, every ID said by its name")
    return parser


def mode_of(args):
    if getattr(args, "for_lead", False):
        return "for-lead"
    return "json" if getattr(args, "json", False) else "default"
