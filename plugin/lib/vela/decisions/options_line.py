"""The one writer of the `**Options considered:**` line, so no form of it is spelled in two places.

The line has three forms, and the dashboard and the grill listing read all of them back:
  only this one: <the lead's words> (<cite>)      the lead said nothing else was on the table
  <pick> (picked); <option>: rejected, <reason>   a pick with what it was picked over
  ...; <option>: rejected, reason declined        the lead would not give a reason

The readers split the line on "; ", so a reason holding one would read back as a bogus option. `reason` therefore
turns each "; " in a reason into ", " before it joins the line: the sentence keeps its words and loses one mark."""
import re

LABEL = "**Options considered:**"
DECLINED_REASON = "reason declined"
_SPLIT_MARK = re.compile(r";\s+")


def reason(words):
    """A reason as it may sit on the line: one that no reader would split."""
    return _SPLIT_MARK.sub(", ", str(words))


def only_this_one(cite, words=None):
    """`only this one: <words> (<cite>)`; the reference alone when the words may not be quoted."""
    if words:
        return f"- {LABEL} only this one: {reason(words)} ({cite})"
    return f"- {LABEL} only this one ({cite})"


def picked(pick, rejected):
    """`<pick> (picked); <option>: rejected, <reason>` for each (option, reason) pair; names arrive tidy."""
    parts = [f"{pick} (picked)"] + [f"{name}: rejected, {reason(why)}" for name, why in rejected]
    return f"- {LABEL} {'; '.join(parts)}"
