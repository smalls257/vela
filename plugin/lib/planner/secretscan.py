"""Finding credentials in text that is about to go to every reader. Pure: no disk, clock or network.

The Violation this prevents is a Silent Fallback at the publish door: the home-path scan existed, so an owner could
believe publish checked what it sends, while a pasted Jira token or connection string went to every reader unremarked.
The scan names the file, the line and the kind of secret and never prints the secret itself (the warning lands in
terminals, logs and screen shares). It looks for shapes that are almost never anything else; it is not a promise
that nothing sensitive is left, and the message says so.

cli.py publish runs it over the committed pages and refuses unless the owner passes --allow-secrets.
"""
import re
from dataclasses import dataclass

_PLACEHOLDER = re.compile(r"^(?:<.*>|\$\{.*\}|\{\{.*\}\}|x{4,}|\*{3,}|\.{3,}|your[-_ ]?.*|changeme|example.*|placeholder|redacted)$", re.IGNORECASE)

SHAPES = (
    ("an AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("a GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("an Anthropic or OpenAI API key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}")),
    ("a Stripe key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("an Atlassian API token", re.compile(r"\bATATT[A-Za-z0-9_=-]{30,}")),
    ("a private key", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----")),
    ("a web token (JWT)", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("a password inside a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:([^\s/@]{3,})@")),
)
# password = "value", token: value, api_key=value. Only when the value is a real-looking string, not a word of prose.
ASSIGNMENT = re.compile(r"""(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|token)\b["']?\s*[:=]\s*["']?([A-Za-z0-9/+_=.-]{12,})["']?""")


@dataclass(frozen=True)
class SecretHit:
    path: str
    line: int
    kind: str


def _is_placeholder(value):
    return bool(_PLACEHOLDER.match(value))


def _line_hits(line):
    kinds = []
    for kind, pattern in SHAPES:
        match = pattern.search(line)
        if match and not _is_placeholder(match.group(match.lastindex or 0)):
            kinds.append(kind)
    for match in ASSIGNMENT.finditer(line):
        value = match.group(1)
        looks_random = any(c.isdigit() for c in value) and any(c.isalpha() for c in value)
        if looks_random and not _is_placeholder(value) and "a password or token set in plain text" not in kinds:
            kinds.append("a password or token set in plain text")
    return kinds


def find_secrets(texts):
    """[SecretHit] for {path: text}, in path then line order. One hit per kind per line."""
    hits = []
    for path in sorted(texts):
        for number, line in enumerate(texts[path].split("\n"), start=1):
            hits += [SecretHit(path, number, kind) for kind in _line_hits(line)]
    return hits


def refusal(hits):
    """The plain message for an owner whose publish was stopped: what, where, and how to go on. Never the secret."""
    shown = "; ".join(f"{h.path} line {h.line} looks like {h.kind}" for h in hits[:5])
    more = f" (and {len(hits) - 5} more)" if len(hits) > 5 else ""
    return (f"I did not publish: {shown}{more}. A published copy goes to every reader and cannot be taken back. "
            "Remove the secret from the page (and rotate it, since it is in the git history), commit, and publish again. "
            "If these are not real secrets, pass --allow-secrets. This scan looks for common shapes only; it cannot promise nothing sensitive is left.")
