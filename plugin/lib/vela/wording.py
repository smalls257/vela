"""Which text on an imported page is a document's own wording. Pure, and imports nothing, so the voice checks can read
it without pulling in the CLI.

The Violation this prevents is a Silent Fallback in the voice pass. An import keeps a document's exact words where they
carry weight (a requirement, a contract or legal term, a number, a direct quote), and close's voice redraft rewrites
prose. Without a mark on the page, the redraft would smooth "the supplier shall respond within four hours" into "the
supplier answers within the morning", and nothing would say a term had changed. So the lead's answer to the voice
question is stamped on each page (`vela import page`), and close (closedrafts), the voice score (voicescore) and the
rewrite check (voicecheck) all read it here:

- `keep`: every word on the page is the documents' own. Nothing is voiced. Until the lead answers, this is what a
  page gets.
- `split`: quoted lines (`> "..."`, cited) are the documents' own; the page's explaining sentences are voiced.
- `voice`: all of it is in the plan's voice; nothing is protected beyond what every page protects.

`source-wording-yes` links the capture of the lead's answer; `vela check` (E361) refuses `split` or `voice` without it.
"""
WORDING_KEY, WORDING_YES_KEY = "source-wording", "source-wording-yes"
KEEP, SPLIT, VOICE = "keep", "split", "voice"
WORDINGS = (KEEP, SPLIT, VOICE)  # strictest first


def wording_of(meta):
    """A page's recorded wording, or "" for a page no import stamped."""
    value = str((meta or {}).get(WORDING_KEY) or "").strip()
    return value if value in WORDINGS else ""


def kept_text(meta, line):
    """Whether one body line is a document's own wording: every non-blank line of a `keep` page, and each quoted line
    of a `split` page."""
    wording = wording_of(meta)
    if wording == KEEP:
        return bool(line.strip())
    return wording == SPLIT and line.lstrip().startswith(">")
