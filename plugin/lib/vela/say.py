"""What a command says, in the three modes every new command offers, and the one place the lead-facing rule is held.

The Violation this module exists to prevent is the Leaky Narrative: the October 13 review of a sim vault counted 709 `UNK-`
mentions and 72 check codes in what the lead read, most of them CLI output a model pasted. Adding more "never say a
code" sentences to the skills did not stop it. So the interface itself carries the fix:

- default mode prints lines with codes and IDs, for files, the PR body and CI;
- `--json` prints the structured result the skill reasons over;
- `--for-lead` prints plain lines with every ID resolved to its name first, and then *checks every line it prints*
  against `LEAD_PATTERNS`. A match raises `LeadLeak`, which `cli.main` turns into exit 2, "vela bug: a line meant
  for the lead held an ID", naming the command. A leak fails loudly at its source (Sensor) instead of being counted in
  a paid run months later.

Exit codes (one meaning each, so no command author reinvents them; `cli.main`'s docstring says the same):
0 done; 1 refused or findings, with a plain reason; 2 the tool failed; 3 needs the lead: nothing changed, the choices
are printed, and `--json` carries the `needs_lead` list. `vela check` keeps 0/1/2.

Pure: no disk, git or clock. The resolver is handed a built vault model (or nothing) by its caller.
"""
import json
import re
from dataclasses import dataclass, field

DONE, REFUSED, FAILED, NEEDS_LEAD = 0, 1, 2, 3

# The one copy of the patterns a lead-facing line may never match. `tests/test_conversation_voice.py` and the sim's
# scorecard read the same ideas; this dict is what the `--for-lead` formatter enforces. The first eight are codes and
# IDs. The rest are the builder's plumbing the October 14 voice audit found passing the check: a session's slug, git's
# or gh's own error words, a command line, a file path, a branch, a flag, a date in ISO form, an @handle and a commit
# hash. Order matters only for the name a leak is reported by: the narrower pattern comes first.
LEAD_PATTERNS = {
    "check code": re.compile(r"\b[EWT]\d{3}\b"),
    "gate": re.compile(r"\bGATE-\w+|--gate\b"),
    "capture": re.compile(r"\^c\d+\b|\b\d+\.c\d+\b|\]\] c\d+\b"),
    "copy": re.compile(r"\bQ-[A-Z]{3}-\d{2,}(?:@[\w*.-]+)?"),
    "finding": re.compile(r"\bF\d+\.\d+\b"),
    "reviewer row": re.compile(r"\bR-[A-Z]{3}-\d{2,}\b"),
    "item": re.compile(r"\b(?:UNK|CAP|CON|EPC|APP|RUN|FLO|SLC|ADR|ENT|PTY|SV|CST|SRC|INI|R)-\d[\w.]*"
                       r"|\b(?:APP|RUN)-[a-z][\w-]*"),
    "goal": re.compile(r"\bG\d+\b"),
    "session slug": re.compile(r"\b\d{4}-\d{2}-\d{2}-[a-z][\w-]*"),
    "git error": re.compile(r"\bfatal:|\berror:|\bhint:|\bgh auth\b|\bgit remotes?\b|not a git repository"
                            r"|Could not resolve host|Permission denied \(publickey\)|\bCONFLICT \(|non-fast-forward"
                            r"|\bgit (?:push|pull|fetch|merge|switch|checkout|config|add|commit|rebase|stash|status)\b"),
    # `vela <subcommand>`: "vela needs 3.9" is prose, "vela check" is a command (test_say holds the list to the parser).
    "command": re.compile(r"\bvela (?:add|apply|boundary|capture|check(?:-diagrams|-slice)?|close|conventions|decide"
                          r"|doctor|epics|explore|export|findings|freshness|grill|guard|handoff|health|hook|import|ladder|library|map|marks"
                          r"|new|next(?:-id)?|onboard|open|plans|proposals|propose|prose|publish|query|questions|record|releases|render"
                          r"|records|reviewers|role|session|status|style|team|terms|tickets|upgrade|view|voice(?:check|score)?"
                          r"|where|whoami)\b"),
    "file path": re.compile(r"(?<![\w/])(?:\.{1,2}/|~/)?(?:[\w.-]+/)+[\w.-]+\.[A-Za-z]{1,5}\b"
                            r"|(?<![\w/])/(?:private|tmp|Users|home|var)/\S+"
                            r"|(?<![\w.-])\.vela\b|\b\d{2}-[\w-]+\.(?:md|ya?ml)\b"),
    "branch": re.compile(r"\b(?:session|dashboard|challenge|answer|proposal)/[\w.-]+|\borigin/[\w.-]+|\(origin\)"),
    "flag": re.compile(r"(?<![\w-])--[a-z][\w-]*"),
    "ISO date": re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    "handle": re.compile(r"(?<![\w.@/])@[A-Za-z0-9][\w-]*"),
    "commit hash": re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b"),
}

# The codes and IDs, as the sim's "codes and IDs" count has always meant them; the rest of LEAD_PATTERNS is plumbing,
# counted apart so a run scored before October 14 still compares like with like.
ID_KINDS = ("check code", "gate", "capture", "copy", "finding", "reviewer row", "item", "goal")

# Who a refusal or a line is for. A model-only one (a missing handle, a field the model put in the wrong place, an ID
# it numbered wrong) is the model's to fix and never prints under `--for-lead`: the lead can't act on it, and hearing
# it next to their real choices is how six flat lines reached them for one decide. The model reads it in the default
# output and `--json`; when nothing else refused, the lead hears only `MY_SIDE`, so an exit 1 is never silent.
MODEL, LEAD = "model", "lead"
MY_SIDE = "Something went wrong on my side; I'll fix it and try again."

# A reader's published folder has one name in what the lead hears: "your copy" (voice audit row 215 found "read
# copy", "reader copy", "reading copy" and "published copy" across seven commands). Builder text keeps its own words.
YOUR_COPY = "This is your copy"
YOUR_COPY_PROPOSAL = f"{YOUR_COPY}, so the change reaches the owner as a proposal."

# Conversation voice rule 7: the lead judges about four things at a time; the rest wait behind "N more; want them?",
# and `--more` prints them all. Default and `--json` always carry the full list.
LEAD_LIMIT = 4
NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# What the lead hears once, after their refusals, when any of them can be set aside: the "user can override" rule in
# the lead's terms. A refusal whose rule takes no end date (an event rule) sets its own `waiver`; "" says nothing.
WAIVE_ONE = "It's your call: you can set this aside with your reason and an end date, and I'll note it."
WAIVE_MANY = "Any of these is yours to set aside: give me your reason and an end date, and I'll note it."
WAIVE_MIXED = ("Any of these is yours to set aside: give me your reason, and an end date for the ones that last, and "
               "I'll note it.")

# What a reader is told for an ID nothing names, so a sentence never loses its subject and never shows the code.
KIND_WORDS = {"UNK": "an open question", "R": "a risk", "CON": "a contract", "CAP": "a capability", "EPC": "an epic",
              "APP": "an app", "RUN": "an app's runtime page", "FLO": "a flow", "SLC": "a slice", "ADR": "a decision",
              "ENT": "an entity", "PTY": "a party", "SV": "a stored value", "CST": "a constraint", "SRC": "a source",
              "INI": "the initiative", "G": "a goal"}

# Override bullets name the rule they set aside (`GATE-4`, `E316`), and findings quote those bullets. The lead hears what
# the rule protects instead, in the grill skill's own terms.
GATE_WORDS = {"GATE-1": "the stage check", "GATE-2": "the preferred-option check",
              "GATE-3": "the check that you agreed the agenda", "GATE-4": "the open-question check",
              "GATE-5": "the check that the owner said yes"}
# The overridable check codes, said by what each protects (the October 14 voice audit, row 72), so one rule never has
# two names: E316 and GATE-4 are both "the open-question check". A code not here is said by its schema meaning.
RULE_WORDS = {"E316": "the open-question check", "E303": "the grill-decides check",
              "E317": "the check that requirements alone can't decide", "E318": "the who-tests-it check",
              "E304": "the needs-a-source check", "E805": "the urgent-questions check", "grill": "the grill-decides check"}
_GATE = re.compile(r"\bGATE-\d\b")
_CODE = re.compile(r"\b[EW]\d{3}\b")

_WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\\?\|([^\]]+))?\]\]")
# "Name (ID)" said as the name. A lower-case ID ("Cost (concern-cost)") counts only when the vault knows it, so a
# bracketed aside like "(read-only)" stays as written.
_NAMED_ID = re.compile(r"(?P<name>\S[^()]*?) \((?P<id>[A-Z]{1,3}-[\w.-]+|G\d+|[a-z][a-z0-9]*(?:-[a-z0-9]+)+)\)")
_ISO_DAY = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b(?!-[a-z])")
# A rule's or a check's sentence about "the lead's own words", said to the lead: "your own words".
_THE_LEADS = re.compile(r"\bthe lead's\b")
# A skill the lead may type, said without the flags the model passes it: "/vela:design --app APP-x" -> "/vela:design".
_SLASH_FLAGS = re.compile(r"(/vela:[\w-]+)(?: --[\w-]+(?: (?!--)[^\s.,;]+)?)+")
_ANY_ID = re.compile(r"\b(?:(?:UNK|CAP|CON|EPC|FLO|SLC|ADR|ENT|PTY|SV|CST|SRC|INI|R)-\d[\w.]*"
                     r"|(?:APP|RUN)-[a-z][\w-]*|G\d+)\b")
_TOKEN = re.compile(r"[\w][\w.-]*[\w]")


class LeadLeak(Exception):
    """A line meant for the lead still held a code or an ID after resolution. Always a vela bug, never the vault's."""

    def __init__(self, command, kind, line):
        self.command, self.kind, self.line = command, kind, line
        super().__init__(f"vela bug: a line meant for the lead held an ID ({kind}) in `vela {command}`. "
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

    def __init__(self, vault=None, findings=None, today=None):
        self.vault = vault
        self.today = today  # a datetime.date: a date in this year is said without its year
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
        if word in RULE_WORDS:
            return RULE_WORDS[word]
        meaning = schema.CODES.get(word)
        return f'the "{meaning}" check' if meaning else "a check"

    def plain(self, text):
        """`text` with links, IDs, copies, findings, captures and the rules overrides name, said in words. A caller
        with a finding drops its code before calling; a code inside the message (an override quoting `E316`) is
        said by its meaning."""
        text = _WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).replace("\\", ""), text)
        text = _GATE.sub(self.rule, text)
        text = _CODE.sub(self.rule, text)
        text = _NAMED_ID.sub(self.named, text)
        text = LEAD_PATTERNS["copy"].sub(self.copy, text)
        text = LEAD_PATTERNS["finding"].sub(self.finding, text)
        text = LEAD_PATTERNS["reviewer row"].sub(self.reviewer_row, text)
        text = LEAD_PATTERNS["capture"].sub("a note in the session record", text)
        text = _ISO_DAY.sub(lambda m: date_words(m.group(0), self.today), text)
        text = LEAD_PATTERNS["handle"].sub(lambda m: person_words(m.group(0)), text)
        text = _THE_LEADS.sub("your", text)
        text = _SLASH_FLAGS.sub(r"\1", text)
        if self.vault is not None:
            text = _TOKEN.sub(lambda m: self.page_word(m.group(0)), text)
        return self.ids_said(text)

    def ids_said(self, text):
        """Every ID by its name; an ID its own name already follows ("SLC-001 Book a room") is just dropped, so the
        name is never said twice."""
        out, last = [], 0
        for found in _ANY_ID.finditer(text):
            name = self.name(found.group(0))
            out.append(text[last:found.start()])
            after = text[found.end():]
            if not (after.startswith(" " + name) and name not in KIND_WORDS.values()):
                out.append(name)
            else:
                after_space = found.end() + 1
                last = after_space
                continue
            last = found.end()
        out.append(text[last:])
        return "".join(out)

    def named(self, match):
        """'Cost (concern-cost)' -> 'Cost'. An upper-case ID always goes; a lower-case one only when it is a page this
        vault knows, so the ID is never said twice as "Cost (Cost)" once the page word turns it into its title."""
        ident = match.group("id")
        if ident[0].isupper() or (self.vault is not None and (ident in self.vault.by_id
                                                               or ident.lower() in self.vault.by_name)):
            return match.group("name")
        return match.group(0)

    def page_word(self, word):
        """A page's file name or page ID, said as its title; any other word unchanged. Only hyphenated words count, so a
        plain word that happens to be a page ID ("sources", "index") stays a word."""
        if "-" not in word:
            return word
        if word.endswith(".md") and word[:-3].lower() in self.vault.by_name:  # "05-solution-strategy.md"
            return self.page_title(word[:-3]) or word
        if word.lower() in self.vault.by_name:
            return self.page_title(word) or word
        pages = self.vault.by_id.get(word)
        title = pages[0].meta.get("title") if pages else None
        return str(title) if title else word


def count_words(n, capital=False):
    """3 -> 'three', 0 -> 'no', 40 -> '40': a count the way a person says it."""
    word = NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)
    return word[0].upper() + word[1:] if capital else word


def names_said(names):
    """['a', 'b', 'c'] -> 'a, b and c'."""
    names = [n for n in names if n]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" and {names[-1]}" if names else ""


def person_words(handle):
    """'@solution-lead' -> 'solution lead': a person said the way the lead would, not as a GitHub handle."""
    return handle.lstrip("@").replace("-", " ").replace("_", " ")


def date_words(value, today=None):
    """'2026-10-14' -> 'October 14', with the year ('October 14, 2026') when it isn't `today`'s; anything else unchanged.
    American order is the house rule for every date written in words (the owner's call); ISO stays in records and IDs."""
    import datetime
    try:
        day = datetime.date.fromisoformat(str(value))
    except ValueError:
        return value
    words = f"{MONTHS[day.month - 1]} {day.day}"
    return words if today is not None and today.year == day.year else f"{words}, {day.year}"


def date_words_with_weekday(value, today=None):
    """'2027-02-02' -> 'Tuesday, February 2, 2027'; the year is left off only when it is `today`'s. Not a date: unchanged."""
    import datetime
    try:
        day = datetime.date.fromisoformat(str(value))
    except ValueError:
        return value
    return f"{WEEKDAYS[day.weekday()]}, {date_words(value, today)}"


@dataclass(frozen=True)
class Line:
    """One line of output. `text` is the default mode's line (codes and IDs allowed); `plain` is what the lead hears.
    When `plain` is None the resolver derives it from `text`; "" says nothing to the lead. A MODEL line (housekeeping,
    a note only the model acts on) prints in default and `--json` only."""
    text: str
    plain: str = None
    audience: str = LEAD


@dataclass(frozen=True)
class Refusal:
    """Why a command would not proceed: what the lead hears, what the model does next, and the exact route to set it
    aside. Every refusal carries an override route, because the lead may override any rule (it just goes on record).

    `audience` says whose it is. A LEAD refusal is a choice the lead makes, so it carries `recommend`, what I'd do
    (conversation voice rule 2), and the lead hears once that it can be set aside (`waiver`; None means the standing
    sentence, "" means nothing to set aside). A MODEL refusal is a slip the model fixes; the lead never hears it."""
    rule: str
    plain: str
    fix: str
    override: str = ""
    audience: str = LEAD
    recommend: str = ""
    waiver: str = None

    @property
    def overridable(self):
        route = self.override.strip().lower()
        return bool(route) and not route.startswith(("none", "nothing to override"))

    def waiver_words(self):
        if self.waiver is not None:
            return self.waiver
        return WAIVE_ONE if self.overridable else ""

    def as_json(self):
        return {"refused": True, "rule": self.rule, "plain": self.plain, "fix": self.fix, "override": self.override,
                "audience": self.audience, "recommend": self.recommend}


@dataclass
class Result:
    """What a command found or did. `wrote` lists the paths it changed; exit 3 promises nothing changed, so a Result
    with exit 3 and anything in `wrote` is refused by `emit` as a vela bug. `answer` is the lead's first line, the
    answer before the list (conversation voice rule 7); a command whose first line already answers leaves it empty."""
    command: str
    exit: int = DONE
    lines: list = field(default_factory=list)
    refusals: list = field(default_factory=list)
    needs_lead: list = field(default_factory=list)
    wrote: list = field(default_factory=list)
    data: dict = field(default_factory=dict)
    answer: str = ""
    closing: str = ""  # what the lead hears last, after the grouped list: the one question or the way out

    def as_json(self):
        return {"command": self.command, "exit": self.exit, "lines": [line.text for line in self.lines],
                "refusals": [r.as_json() for r in self.refusals], "needs_lead": self.needs_lead,
                "wrote": self.wrote, **self.data}


def lead_items(result, resolver):
    """What the lead is asked to judge, in order, each said once: their refusals (each with my recommendation), then
    the lines. Model-only refusals and lines are not among them."""
    items = []
    for r in result.refusals:
        if r.audience == LEAD:
            items.append(" ".join(filter(None, (resolver.plain(r.plain), resolver.plain(r.recommend)))))
    for line in result.lines:
        if line.audience == LEAD:
            items.append(resolver.plain(line.plain if line.plain is not None else line.text))
    seen, out = set(), []
    for item in items:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def waiver_line(result):
    """One closing sentence when any lead refusal can be set aside: said once, never once per refusal."""
    words = [r.waiver_words() for r in result.refusals if r.audience == LEAD]
    said = list(dict.fromkeys(w for w in words if w))
    if not said:
        return ""
    if len(said) == 1:
        return WAIVE_MANY if said == [WAIVE_ONE] and len([w for w in words if w]) > 1 else said[0]
    return WAIVE_MIXED  # one sentence, never two that each say "it's your call"


def lead_lines(result, resolver, more=False):
    """Every line the lead would hear, resolved, grouped and checked: the answer first, then about four things
    (`LEAD_LIMIT`), then "N more; want them?" unless `more`, then whether they may set any of it aside. Raises LeadLeak
    on the first line that still leaks."""
    answer = resolver.plain(result.answer) if result.answer else ""
    items = [i for i in lead_items(result, resolver) if i != answer]
    shown, rest = (items, []) if more else (items[:LEAD_LIMIT], items[LEAD_LIMIT:])
    if rest and len(rest) == 1:  # "one more; want it?" costs the lead as much as reading it
        shown, rest = items, []
    said = ([answer] if answer else []) + ([my_side(result)] if my_side(result) and not items else []) + shown
    if rest:
        said.append(f"{count_words(len(rest), capital=True)} more; want them?")
    said += [w for w in (waiver_line(result), resolver.plain(result.closing) if result.closing else "") if w]
    for text in said:
        leak = leak_in(text)
        if leak:
            raise LeadLeak(result.command, leak[0], text)
    return said


def my_side(result):
    """The one line the lead hears when only the model's own slips refused: true, plain, and no detail. The model
    reads the slips themselves in the default output or `--json`, never through the lead's text."""
    model_only = any(r.audience == MODEL for r in result.refusals)
    if model_only and not any(r.audience == LEAD for r in result.refusals):
        return MY_SIDE
    return ""


def check_contract(result):
    """The exit-code promises, held in one place."""
    if result.exit == NEEDS_LEAD and result.wrote:
        raise ValueError(f"vela bug: `vela {result.command}` exited 3 (needs the lead, nothing changed) "
                         f"after writing {', '.join(result.wrote)}")
    if result.exit == NEEDS_LEAD and not result.needs_lead:
        raise ValueError(f"vela bug: `vela {result.command}` exited 3 without saying what the lead must choose")


def render(result, mode, resolver=None, more=False):
    """The text `result` prints in `mode` ("default", "json" or "for-lead"). Pure: `commands.emit` does the printing,
    because only the shell writes output. `more` lifts the about-four cap, for when the lead said "yes, want them"."""
    check_contract(result)
    if mode == "json":
        return json.dumps(result.as_json(), indent=2, ensure_ascii=False)
    if mode == "for-lead":
        return "\n".join(lead_lines(result, resolver or Resolver(), more=more))
    said = [f"refused ({r.rule}): {r.plain} Fix: {r.fix}" + (f" Override: {r.override}" if r.override else "")
            for r in result.refusals]
    return "\n".join(said + [line.text for line in result.lines if line.text])


def add_output_flags(parser):
    """--json and --for-lead, mutually exclusive, on a command's parser, and --more, which goes with --for-lead."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="the structured result, for the skill to reason over")
    group.add_argument("--for-lead", action="store_true",
                       help="plain lines for the lead: the answer first, about four things, no codes and no IDs")
    add_more_flag(parser)
    return parser


def add_more_flag(parser):
    parser.add_argument("--more", action="store_true",
                        help="with --for-lead: every item, not just the first four (the lead asked for the rest)")
    return parser


def mode_of(args):
    if getattr(args, "for_lead", False):
        return "for-lead"
    return "json" if getattr(args, "json", False) else "default"
