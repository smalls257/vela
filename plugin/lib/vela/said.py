"""Whether the words of a capture are words a person typed. Pure.

The Violation this exists to prevent is a Silent Fallback in the consent path: `vela record add` defaults a capture's
origin to the lead's handle, so the model could write its own sentence as the lead's yes ("The team chose Tauri with
Rust...") and the close gate and design gate would accept it. They check that a person's capture exists, never that the
person said it. The Sensor is a log of what the person typed, written by a plugin hook (`vela hook said`, the edge) and
read here: a person's capture must be a contiguous excerpt of one logged message.

Matching is by words, not characters: case, spacing, curly quotes and punctuation around the words don't matter; a
paraphrase, a reordering or an invented word does. Where no log exists at all (a host whose hooks don't fire), nothing
can be proven either way, so the capture is written marked `unverified` in its origin and every gate that counts yeses
asks the lead to confirm it by name first, never counting it silently.
"""
import json
import re

UNVERIFIED = "unverified"
UNVERIFIED_SUFFIX = ", " + UNVERIFIED
WORD_RE = re.compile(r"[\w@'-]+")
QUOTE_RE = re.compile(r"[\"“](?P<q>[^\"”]+)[\"”]")
CURLY = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def tokens(text):
    """The words of `text`, folded: case, curly quotes, spacing and punctuation gone."""
    return [w.strip("'-") for w in WORD_RE.findall(text.translate(CURLY).casefold()) if w.strip("'-")]


def log_line(at, text):
    """One logged message, as a single JSON line (a message may span lines)."""
    return json.dumps({"at": at, "text": text}, ensure_ascii=False)


HARNESS_PREFIXES = ("<task-notification>", "<system-reminder>")


def harness_injected(text):
    """True for a prompt the host injected (a background agent's finished notice, a reminder): the model's own words
    arriving through the prompt channel, never something a person typed. Logged by older hooks, so read-side too."""
    return text.lstrip().startswith(HARNESS_PREFIXES)


def messages(log_texts):
    """The typed messages in the given log files' texts. A line that isn't a log entry, or a host-injected notice, is
    skipped: a notice carrying the model's summary must never back a person's yes."""
    entries = (entry_text(line) for log in log_texts for line in log.splitlines())
    return [text for text in entries if text is not None and not harness_injected(text)]


def entry_text(line):
    """The message a log line holds, or None for a line that isn't an entry (never a typed message)."""
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    return entry["text"] if isinstance(entry, dict) and isinstance(entry.get("text"), str) else None


def _within(wanted, have):
    if not wanted or len(wanted) > len(have):
        return False
    return any(have[i:i + len(wanted)] == wanted for i in range(len(have) - len(wanted) + 1))


def typed(words, typed_messages):
    """Whether `words` is a contiguous excerpt of one typed message. A capture written `"Yes to these." says yes to
    X` is judged on its quoted span, the part every gate reads as the person's words."""
    spans = [words]
    quoted = QUOTE_RE.search(words)
    if quoted:
        spans.append(quoted.group("q"))
    haves = [tokens(m) for m in typed_messages]
    return any(_within(tokens(span), have) for span in spans for have in haves)


def is_unverified(origin):
    return origin.strip().lower().endswith(UNVERIFIED_SUFFIX)


def mark_unverified(origin):
    return origin.strip() + UNVERIFIED_SUFFIX


def confirmed(origin):
    """The origin with the unverified mark taken off, once the lead has said the words were theirs."""
    text = origin.strip()
    return text[:-len(UNVERIFIED_SUFFIX)].strip() if is_unverified(text) else text
