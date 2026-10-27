"""The ticket copy a session writes into the plan, held against the plan's own criteria. Pure: a Story in, lines out.

    problems(story) -> [(text, flag)]   each line a person reads before a ticket is made; flag False is a note
    covered(story)  -> {criterion number}  the plan criteria the ticket shows: all of them when it falls back to the flat list
    tag_of(line)    -> (words, numbers, bad tokens or None when the line has no tag)
    has_copy(story) -> whether the story has grouped ticket criteria

The copy is model-written: a `Summary:` line and a `Ticket criteria (from <stamp>):` block of short headings and
reworded lines, each tagged `(covers AC1, AC3)`, where ACn is the nth bullet under the story's Acceptance criteria.
The Violation this exists to prevent is a Paper Tiger: a ticket that reads better than the plan and quietly drops a
criterion. A copy written for criteria that have since changed is a Fossil Comment, caught by the stamp. A story with no
copy still gets a ticket, with the plan's list, and a flag here: never a silent fallback.
"""
import re

from vela import breakdown

COVERS = re.compile(r"\(covers\s+([^)]*)\)\s*$", re.I)
TOKEN = re.compile(r"^AC(\d+)$")
# The words a session writes carry no IDs: vela adds each as a suffix and a label, so a Jira reader never meets a bare one.
ID_IN_WORDS = re.compile(r"\b(?:CAP|CON|EPC|FR|APP|CST|OQ|UNK|SLC|PG|D|G|S)-\d+")
SENTENCE = re.compile(r"(?<=[.?!])\s+(?=[A-Z\"'(])")
SUMMARY_SENTENCES = (4, 5)


def has_copy(story):
    return any(lines for _, lines in story.ticket_groups)


def tag_of(line):
    found = COVERS.search(line)
    if not found:
        return line.strip(), [], None
    tokens = [t for t in re.split(r"[\s,]+", found.group(1)) if t and t.lower() != "and"]
    numbers = [int(TOKEN.match(t).group(1)) for t in tokens if TOKEN.match(t)]
    return line[:found.start()].strip(), numbers, [t for t in tokens if not TOKEN.match(t)]


def covered(story):
    if not has_copy(story):
        return set(range(1, len(story.criteria) + 1))
    count = len(story.criteria)
    return {n for _, lines in story.ticket_groups for line in lines for n in tag_of(line)[1] if 1 <= n <= count}


def ids_in(words):
    return list(dict.fromkeys(ID_IN_WORDS.findall(words)))


def summary_problems(story):
    if story.summary is None:
        return [("has grouped ticket criteria but no 'Summary:' line, so its ticket opens with no summary", True)]
    out = []
    count = len([s for s in SENTENCE.split(story.summary.strip()) if s.strip()])
    if count not in SUMMARY_SENTENCES:
        out.append((f"has a summary of {count} sentences; the ticket reads best with 4 or 5", False))
    if ids_in(story.summary):
        out.append((f"names {', '.join(ids_in(story.summary))} in its summary; write names, and vela adds the IDs", True))
    return out


def stamp_problems(story):
    stamp = breakdown.criteria_stamp(story.criteria)
    label = f"`Ticket criteria (from {stamp}):`"
    if story.ticket_stamp is None:
        return [(f"has ticket criteria with no stamp; once they match its acceptance criteria, write the label as {label}", True)]
    if story.ticket_stamp != stamp:
        return [("has ticket criteria written for earlier acceptance criteria; rewrite them against the criteria as they "
                 f"are now, then write the label as {label}", True)]
    return []


def line_problems(story):
    out, count = [], len(story.criteria)
    for heading, lines in story.ticket_groups:
        if not heading and lines:
            out.append(("has ticket lines before the first heading; put each line under a short heading", True))
        if heading and not lines:
            out.append((f"has a ticket heading, '{heading}', with no lines under it", True))
        for line in lines:
            words, numbers, bad = tag_of(line)
            if bad is None:
                out.append((f"has a ticket line with no covers tag: {words!r}", True))
                continue
            if bad is not None and not numbers and not bad:
                out.append(("has a covers tag that names no criterion; write it as (covers AC1, AC2)", True))
            if bad:
                out.append((f"has a covers tag it can't read ({', '.join(repr(b) for b in bad)}); write it as (covers AC1, AC2)", True))
            for n in numbers:
                if not 1 <= n <= count:
                    out.append((f"has a ticket line that covers AC{n}, but the story has {count} acceptance criteria", True))
            if ids_in(words):
                out.append((f"names {', '.join(ids_in(words))} in a ticket line; write names, and vela adds the IDs", True))
    return out


def coverage_problems(story):
    shown = covered(story)
    return [(f"AC{n} isn't covered by any ticket line: {c!r}", True)
            for n, c in enumerate(story.criteria, 1) if n not in shown]


def problems(story):
    """Every line about one story's ticket copy, in the order a person fixes them."""
    if not has_copy(story):
        if story.ticket_label:
            return [("has a 'Ticket criteria' label with no lines under it, so its ticket carries the plan's criteria as a flat list", True)]
        if story.summary is None:
            return [("has no ticket copy yet (a summary and its criteria grouped for the ticket), so its ticket carries the "
                     "plan's criteria as a flat list", True)]
        return summary_problems(story) + [("has a summary but no 'Ticket criteria' block, so its ticket carries the plan's "
                                           "criteria as a flat list", True)]
    return summary_problems(story) + stamp_problems(story) + line_problems(story) + coverage_problems(story)
