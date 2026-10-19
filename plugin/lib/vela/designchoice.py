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
