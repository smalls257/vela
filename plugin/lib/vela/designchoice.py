"""What counts as a design choice in a design doc, and whether a person's yes names it (the one implementation: `vela
team commit` gates on it and the design-yes probe scores with it).

Why: a design session wrote "we'll use X" lines the senior never agreed to (a Silent Fallback: the doc reads as a
decision, and nobody made it). A skill sentence asking the model to wait for the yes did not hold, so the commit
refuses until a person's capture names the choice.

A design choice is an ADR (its title line is the one choice it records) or, anywhere else, a line that says what was
picked: a bullet under a Decisions heading, "we'll use/build X", "chosen option", a `Decision:` line. Pure: text in,
lines out; the edge reads files and the record.
"""
import collections
import re

ADR_TITLE = re.compile(r"^#\s+ADR-\d+", re.I)
CHOICE = re.compile(r"\bwe(?:'ll|’ll| will| are going to)\s+(?:use|build|adopt|go with|run|store|ship|write|keep)\b"
                    r"|\bchosen (?:option|approach|design)\b|\b(?:option|approach)\s+[a-d1-4]\s+(?:is|was) (?:chosen|picked|selected)\b"
                    r"|^\s*(?:[-*+]\s+)?(?:\*\*)?(?:decision|chosen option|choice)(?:\*\*)?\s*:", re.I)
DECISIONS_HEAD = re.compile(r"^\s*(?:#{2,4}\s+decisions?\b|>?\s*\*\*decisions\b[^*]*\*\*)", re.I)
BULLET = re.compile(r"^\s*>?\s*[-*+]\s+\S")
NO_CHOICE = re.compile(r"^\s*>?\s*[-*+]\s+(?:\*\*)?(?:none|nothing|n/?a|tbd|no decisions?)\b", re.I)  # "- None yet" records no choice

_WORD = re.compile(r"[a-z0-9]+")
_FILLER = {"that", "this", "with", "from", "will", "well", "have", "into", "than", "then", "they", "them", "when",
           "decision", "chosen", "option", "approach", "choice", "adr", "yes", "the", "and", "for", "use", "using"}
MATCH_SHARE = 0.5  # a yes names a choice when it carries this share of the choice's content words


def choice_lines(rel, text):
    """Counter of the stripped lines in one doc (`rel`, repository-relative) that write a design choice."""
    found = collections.Counter()
    is_adr = "/adr/" in f"/{rel}"
    listing = False
    for line in text.splitlines():
        if is_adr:
            hit = bool(ADR_TITLE.match(line))
        else:
            if DECISIONS_HEAD.match(line):
                listing = True
            elif listing and not BULLET.match(line) and line.strip():
                listing = False
            hit = (listing and bool(BULLET.match(line)) and not NO_CHOICE.match(line)) or bool(CHOICE.search(line))
        if hit:
            found[line.strip()] += 1
    return found


def added_choices(rel, before, after):
    """The choice lines `after` has that `before` (the committed text, "" for a new file) did not, one per new copy."""
    return list((choice_lines(rel, after) - choice_lines(rel, before)).elements())


def _stems(text):
    return {w[:5] for w in _WORD.findall(text.lower()) if len(w) > 2 and w not in _FILLER}


def names_choice(yes_words, choice):
    """True when the person's words carry at least half of the choice's content words (compared by five-letter stem,
    so 'keeping' names 'keep'). An ADR title's number and 'ADR' are not content."""
    wanted = _stems(re.sub(r"adr-\d+", "", choice, flags=re.I))
    if not wanted:
        return True
    return len(wanted & _stems(yes_words)) / len(wanted) >= MATCH_SHARE


def unbacked(choices, yes_captures):
    """The choices no person capture names, in order."""
    return [c for c in choices if not any(names_choice(words, c) for words in yes_captures)]


def plain_choice(line):
    """The choice as a sentence for the person: markup and the ADR number stripped."""
    text = re.sub(r"^\s*(?:>?\s*[-*+]\s+|#+\s+)", "", line)
    text = re.sub(r"^ADR-\d+[:\s.—-]*", "", text.replace("*", "").replace("`", ""), flags=re.I)
    return text.strip().rstrip(".")


# ---- a gap's `acknowledged_by` is a claim that a person accepted it; only their typed words can back it ----
#
# Why: a design session copied the lead's handle onto 21 gaps when the lead had accepted one (a Silent Fallback: fake
# consent in hand-written frontmatter, with no verifier). The Violation this prevents is a handle nobody typed a word
# under. One implementation: `vela team commit` and `vela check` both ask `unnamed_gaps`.

GAP_ID = re.compile(r"\bG-\d+\b", re.I)


def acknowledged_gaps(text):
    """The gaps in a design doc's frontmatter that carry an `acknowledged_by`, as (id, what, handle) tuples. A doc with
    no readable frontmatter has none (the design reader reports that problem; this does not repeat it)."""
    import yaml
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return []
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return []
    try:
        meta = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        return []
    gaps = meta.get("gaps") if isinstance(meta, dict) else None
    if not isinstance(gaps, list):
        return []
    return [(str(g.get("id", "")), str(g.get("what", "")), str(g["acknowledged_by"]))
            for g in gaps if isinstance(g, dict) and g.get("acknowledged_by")]


def gap_named(gap, typed_messages):
    """True when one typed message names the gap: it carries the gap's ID, or half the content words of what it says."""
    gap_id, what, _ = gap
    for message in typed_messages:
        ids = {m.upper() for m in GAP_ID.findall(message)}
        if (gap_id and gap_id.upper() in ids) or (what and names_choice(message, what)):
            return True
    return False


def unnamed_gaps(gaps, typed_messages):
    """The acknowledged gaps no typed message names, in order. `typed_messages` is None when no said log exists at
    all: nothing can be proven, so the caller lists them as unverified, never as accepted and never as refused."""
    if typed_messages is None:
        return list(gaps)
    return [g for g in gaps if not gap_named(g, typed_messages)]


def new_acknowledged_gaps(before, after):
    """The acknowledged gaps `after` has that `before` (the committed text) did not carry as-is."""
    old = set(acknowledged_gaps(before))
    return [g for g in acknowledged_gaps(after) if g not in old]
