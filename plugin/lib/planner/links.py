"""Links out of the vault: where a page's or an item's work lives elsewhere, such as its ticket, its wiki
space, its GitHub repo or a partner's API spec.

A page holds them in its frontmatter as `links:`, a map of label to URL. A label that .planner.yaml's
`link_templates` names may hold a key instead of a URL, and the template's `{key}` is filled from it, so an epic
writes `links: {Tracker: BOOK-12}` and the vault says once where the tracker lives. An item (a contract, an outside party)
holds them in a **Links:** bullet of Markdown links, `[API spec](https://...)`.

Planner reads and checks links; it never fetches one. Each reader returns the links it could read and a problem
sentence for each it could not, so a check reports a bad link and a viewer still shows the good ones.
"""
import re
from dataclasses import dataclass

from planner import schema

URL_RE = re.compile(r"^(?:https?://|file:///)[^\s<>\"']+$")  # file:// is a local clone: `planner explore` reads a team design from one
MD_LINK = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


@dataclass(frozen=True)
class Link:
    label: str
    url: str


def templates(config):
    """(label -> template, problems) from .planner.yaml's link_templates. A template is an http(s) URL with {key}."""
    found, problems = {}, []
    raw = config.get(schema.LINK_TEMPLATES_KEY)
    if raw is None:
        return found, problems
    if not isinstance(raw, dict):
        return found, [f".planner.yaml's {schema.LINK_TEMPLATES_KEY} is not a map of label to URL"]
    for label, template in raw.items():
        if not (isinstance(template, str) and "{key}" in template and URL_RE.match(template.replace("{key}", "KEY"))):
            problems.append(f".planner.yaml's {schema.LINK_TEMPLATES_KEY} {label} is not an http(s) URL with {{key}} in it")
            continue
        found[str(label)] = template
    return found, problems


def of_page(page, config):
    """(links, problems) from a page's `links:` frontmatter, in the order the page writes them."""
    raw = page.meta.get(schema.LINKS_FIELD)
    if raw is None:
        return [], []
    if not isinstance(raw, dict):
        return [], ["'links' must be a map of label to URL, such as links: {Tracker: https://tracker.example.com/browse/BOOK-12}"]
    known, _ = templates(config)
    out, problems = [], []
    for label, value in raw.items():
        label, value = str(label).strip(), value.strip() if isinstance(value, str) else value
        if not label or not isinstance(value, str) or not value:
            problems.append(f"link '{label}' needs a URL")
        elif URL_RE.match(value):
            out.append(Link(label, value))
        elif label in known and KEY_RE.match(value):
            out.append(Link(label, known[label].replace("{key}", value)))
        elif label in known:
            problems.append(f"link '{label}: {value}' is not a key the {label} template can take")
        else:
            problems.append(f"link '{label}: {value}' is not an http(s) or file:// URL, and .planner.yaml has no "
                            f"{schema.LINK_TEMPLATES_KEY} entry for {label}")
    return out, problems


def of_item(item):
    """(links, problems) from an item's **Links:** bullet."""
    bullet = item.facts.get(schema.LINKS_LABEL)
    if bullet is None:
        return [], []
    found = MD_LINK.findall(bullet.value)
    if not found:
        return [], [f"{item.id}'s **{schema.LINKS_LABEL}:** holds no Markdown link, such as [API spec](https://...)"]
    out, problems = [], []
    for label, url in found:
        if URL_RE.match(url):
            out.append(Link(label.strip(), url))
        else:
            problems.append(f"{item.id}'s link '{label}' is not an http(s) or file:// URL")
    return out, problems
