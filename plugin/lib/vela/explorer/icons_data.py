"""The built-in icon each app and outside party is drawn with, chosen at build time, the same on every build.

Generated art is optional and never relied on, so every box gets one of the page's own line glyphs
(assets/js/icons.js). The choice, in order:

1. an app page's `icon:` frontmatter, when it names a glyph in the set;
2. the first keyword rule that matches the title, then the domain, then the opening words (a party's facts);
3. a fallback picked by a hash of the name, so a box with no keyword keeps the same shape from build to build.

Each choice carries the reason it was made, which the page shows on hover. A generated emblem, when its slot
resolves, still wins over the glyph in the page.
"""
import re
import zlib

# Keyword rules, most specific first. Each pattern matches at the start of a word, so "pay" finds "payment" but
# not "repay"'s middle.
RULES = (
    ("legacy", "legacy|mainframe|ledger of record|cobol"),
    ("gateway", "gateway|api gateway|edge|proxy|integration hub"),
    ("callcenter", "call cent|contact cent|agent|telephon|phone line"),
    ("kiosk", "kiosk|terminal|self.service"),
    ("mobile", "mobile|app store|ios|android"),
    ("web", "web|site|portal|browser|front.?end"),
    ("ship", "vessel|ferry|ship|sailing|fleet|port\\b"),
    ("refund", "refund|chargeback|reimburs"),
    ("voucher", "voucher|coupon|gift"),
    ("loyalty", "loyalty|points|reward"),
    ("fraud", "fraud|risk score|anti.?money"),
    ("payments", "pay|card|billing|checkout|invoice|acquir"),
    ("ledger", "ledger|accounting|journal|bookkeep"),
    ("pricing", "pric|fare|quote|tariff|rate card"),
    ("booking", "book|reserv|hold|order"),
    ("schedule", "schedul|timetable|calendar|roster"),
    ("inventory", "inventor|stock|capacity|warehouse stock|seat"),
    ("identity", "identit|customer id|account|profile|login|sso|user"),
    ("consent", "consent|privacy|gdpr|preference"),
    ("lock", "auth|security|secret|permission|access"),
    ("notifications", "notif|alert|email|sms|push"),
    ("messaging", "messag|chat|queue|event|bus|kafka|mq\\b"),
    ("search", "search|find|lookup|index"),
    ("catalog", "catalog|product|menu|listing"),
    ("analytics", "report|analytic|insight|dashboard|metric|bi\\b"),
    ("database", "data|database|warehouse|lake|store\\b|storage"),
    ("audit", "audit|log\\b|compliance trail|record keeping"),
    ("legal", "tax|regulat|legal|complian|licen"),
    ("location", "map|geo|location|address|route"),
    ("news", "news|article|feed|editorial|content"),
    ("learning", "coach|lesson|learn|teach|course|tutor"),
    ("trading", "trade|trading|broker|market|stock price|exchange"),
    ("partner", "partner|vendor|supplier|third.?party|external"),
)
FALLBACKS = ("cube", "hexagon", "layers", "nodes", "diamond")
ICONS = tuple(name for name, _ in RULES) + FALLBACKS
# The glyphs took American names; a vault written before that still says `icon: catalogue` or `icon: callcentre`.
# Those must keep drawing their glyph, not fall to a keyword guess with a "not in the built-in set" note.
ICON_ALIASES = {"catalogue": "catalog", "callcentre": "callcenter"}
_COMPILED = tuple((name, re.compile(rf"\b(?:{pattern})", re.I)) for name, pattern in RULES)


def canonical(asked):
    """The built-in glyph name an `icon:` value means: its American name when it is an older British spelling."""
    return ICON_ALIASES.get(asked, asked)


def choose(title, domain="", summary="", asked=""):
    """(icon name, why) for one box. `asked` is the page's `icon:`, when it has one."""
    if asked:
        if canonical(asked) in ICONS:
            return canonical(asked), f"icon: {asked} on its page"
        reason = f"its page asks for icon: {asked}, which is not in the built-in set, so "
    else:
        reason = ""
    # a title or domain names the thing, so the most specific rule wins there; in running prose the first keyword
    # the text reaches is what it is about ("a supplier ... its webhook API" is a partner, not a website)
    for where, text in (("title", title), ("domain", domain)):
        for name, pattern in _COMPILED:
            found = pattern.search(text or "")
            if found:
                return name, f"{reason}'{found.group(0).lower()}' in its {where}"
    hits = [(m.start(), i, name, m.group(0)) for i, (name, pattern) in enumerate(_COMPILED) for m in [pattern.search(summary or "")] if m]
    if hits:
        _, _, name, word = min(hits)
        return name, f"{reason}'{word.lower()}' in its opening words"
    pick = FALLBACKS[zlib.crc32((title or "").encode("utf-8")) % len(FALLBACKS)]
    return pick, f"{reason}no keyword in its title, domain or opening words; a shape kept by its name"


def for_map(nodes, entities, domains, apps_meta):
    """{node key: {"icon", "why"}} for every box on the map, and the `icon:` values the set does not hold."""
    out, unknown = {}, []
    for n in nodes:
        e = entities.get(n["key"], {})
        asked = str(apps_meta.get(n["key"], {}).get("icon") or "")
        summary = e.get("text", "") or " ".join(f.get("text", "") for f in e.get("facts", []))
        name, why = choose(n["title"], domains.get(n["key"], ""), summary, asked)
        if asked and canonical(asked) not in ICONS:
            unknown.append((n["key"], asked))
        out[n["key"]] = {"icon": name, "why": why}
    return out, unknown
