"""The plan's size, measured once. Pure.

The Violation this exists to prevent is a Distributed Monolith: every check guessing the plan's size on its own
(`DOMAIN_MIN_APPS` was the first), so that "what counts as small" lived in as many places as there were checks.
Here one function reads apps, capabilities and releases, the session stubs' recorded sizes and the lead's choice,
and every caller asks `sizing.of(vault).needs(Need.X)`. Nothing else compares a band; a test walks the library to
hold that. Parties and provider contracts never move the band: they bring their own catalog questions at every
size, and letting the same fact also move the band would make two mechanisms disagree.

The band never drops on its own (the ratchet): a stub that recorded medium keeps a two-app plan medium until the
lead sets it. Nothing here blocks anything. A choice by the lead is recorded with their reason, never refused.
"""
import datetime
import enum
import re
from dataclasses import dataclass

from vela import privaterecord, releases, say, schema

_STUB_SIZE = re.compile(r"^(small|medium|large);")
_SIGNAL_WORDS = {"apps": ("app", "apps"), "capabilities": ("capability", "capabilities"),
                 "releases": ("release", "releases")}
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Need(enum.Enum):
    READING_LOAD_SHOWN = "READING_LOAD_SHOWN"
    OPTIONS_BEFORE_GRILL = "OPTIONS_BEFORE_GRILL"
    REVIEW_EACH_MODE = "REVIEW_EACH_MODE"
    VOICE_REVIEW_ALWAYS = "VOICE_REVIEW_ALWAYS"
    DOMAIN_FIELD = "DOMAIN_FIELD"
    REQUIREMENTS_SESSION = "REQUIREMENTS_SESSION"
    ALLOCATE_SESSION = "ALLOCATE_SESSION"
    RELEASES_SESSION = "RELEASES_SESSION"


@dataclass(frozen=True)
class Signal:
    name: str    # "apps" | "capabilities" | "releases"
    count: int
    band: str
    words: str   # "two apps", "one capability", "one release"


@dataclass(frozen=True)
class Choice:
    band: str
    because: str   # a committed capture reference, "[[<session>]] c14"
    date: str      # YYYY-MM-DD


@dataclass(frozen=True)
class Announcement:
    kind: str    # "first" | "grew" | "kept"
    band: str    # the band said
    text: str    # the model's line: "size: small (first): apps 2, capabilities 1, releases 1"
    plain: str   # what the lead hears


def _rank(band):
    return schema.SIZE_BANDS.index(band) if band in schema.SIZE_BANDS else -1


def higher(*bands):
    """The highest band given; "" is ignored, and "" comes back when all are empty."""
    held = [b for b in bands if b]
    return max(held, key=_rank) if held else ""


def band_of(name, count):
    small_max, medium_max = schema.SIZE_SIGNALS[name][0]
    return "small" if count <= small_max else "medium" if count <= medium_max else "large"


def _words(name, count):
    one, many = _SIGNAL_WORDS[name]
    return f"{say.count_words(count)} {one if count == 1 else many}"


@dataclass(frozen=True)
class Sizing:
    band: str        # in force: the choice when set, else `shape`
    measured: str    # what the pages alone read now
    shape: str       # higher(measured, recorded): the ratcheted shape
    signals: tuple   # (Signal, ...) in SIZE_SIGNALS order
    chosen: object   # Choice or None
    recorded: str    # the highest band any session stub records, "" when none does
    kept_said: str   # an open stub's size_kept, "" when none

    def needs(self, need):
        return _rank(self.band) >= _rank(schema.NEEDS[need.value][0])

    def counts_text(self):
        return ", ".join(f"{s.name} {s.count}" for s in self.signals)

    def stub_value(self):
        return f"{self.shape}; {self.counts_text()}"

    def voice_review_due(self, paragraphs):
        return self.needs(Need.VOICE_REVIEW_ALWAYS) or paragraphs >= schema.VOICE_REVIEW_MIN_PARAGRAPHS

    def as_json(self):
        return {"band": self.band, "measured": self.measured, "shape": self.shape, "recorded": self.recorded,
                "chosen": None if self.chosen is None else {"band": self.chosen.band, "because": self.chosen.because,
                                                            "date": self.chosen.date},
                "signals": [{"name": s.name, "count": s.count, "band": s.band} for s in self.signals],
                "needs": {n.value: self.needs(n) for n in Need}}


def counts(vault):
    apps = [p for p in vault.of_type("app-building-blocks") if p.meta.get("change") in schema.LADDERED_CHANGES]
    caps = [p for p in vault.of_type("capability") if p.meta.get("change") not in (None, "", "unchanged")]
    return {"apps": len(apps), "capabilities": len(caps), "releases": len(releases.releases(vault))}


def read_choice(config):
    """The lead's choice in `.vela.yaml`, or None when there is none. Raises ValueError naming what is wrong."""
    if "size" not in config:
        return None
    raw = config["size"]
    if not isinstance(raw, dict) or set(raw) != {"band", "because", "date"}:
        raise ValueError("it must be a mapping with band, because and date")
    band, because = raw["band"], str(raw["because"])
    day = raw["date"].isoformat() if isinstance(raw["date"], datetime.date) else str(raw["date"])
    if band not in schema.SIZE_BANDS:
        raise ValueError(f"band {band!r} is not small, medium or large")
    if not privaterecord.CITATION.fullmatch(because):
        raise ValueError(f"because {because!r} is not a capture reference such as [[2026-10-02-grill-a]] c14")
    try:
        if not _DAY.match(day):
            raise ValueError
        datetime.date.fromisoformat(day)
    except ValueError:
        raise ValueError(f"date {day!r} is not a YYYY-MM-DD day") from None
    return Choice(band, because, day)


def _recorded(vault):
    found = [m.group(1) for m in (_STUB_SIZE.match(str(p.meta.get("size", ""))) for p in vault.sessions) if m]
    return higher(*found)


def _kept_said(vault):
    said = [str(p.meta.get("size_kept", "")) for p in vault.sessions if p.meta.get("status") == "open"]
    return next((s for s in said if s), "")


def of(vault):
    if "sizing" in vault.cache:
        return vault.cache["sizing"]
    held = counts(vault)
    signals = tuple(Signal(name, held[name], band_of(name, held[name]), _words(name, held[name]))
                    for name in schema.SIZE_SIGNALS)
    measured = higher(*(s.band for s in signals))
    recorded = _recorded(vault)
    shape = higher(measured, recorded)
    chosen = read_choice(vault.config)
    sized = Sizing(chosen.band if chosen else shape, measured, shape, signals, chosen, recorded, _kept_said(vault))
    vault.cache["sizing"] = sized
    return sized


# ---- the lead's choice in .vela.yaml: the size block, edited without touching any other line ---------------------

_SIZE_KEY = re.compile(r"^size:")


def _without_block(text):
    kept, inside = [], False
    for line in text.splitlines(keepends=True):
        if _SIZE_KEY.match(line):
            inside = True
            continue
        if inside and (line.startswith((" ", "\t")) or not line.strip()):
            continue
        inside = False
        kept.append(line)
    return "".join(kept)


def config_without_choice(text):
    return _without_block(text)


def config_with_choice(text, choice):
    """`.vela.yaml` text with the size block set to `choice`, replacing an old one; every other line is kept."""
    held = _without_block(text)
    held += "" if held.endswith("\n") or not held else "\n"
    return (f'{held}size:\n  band: {choice.band}\n  because: "{choice.because}"\n  date: "{choice.date}"\n')


# ---- what the lead hears, once ------------------------------------------------------------------------------------

def _listed(signals):
    return say.names_said([s.words for s in signals])


def _line(kind, sized, band):
    return f"size: {band} ({kind}): {sized.counts_text()}"


def announcement(sized):
    """What to say about the size, once: the first reading, growth, or a kept choice the shape disagrees with."""
    if sized.chosen and _rank(sized.shape) > _rank(sized.chosen.band) and sized.kept_said != sized.shape:
        at_shape = [s for s in sized.signals if s.band == sized.shape]
        why = (f"the shape reads {sized.shape} because of {_listed(at_shape)}" if at_shape else
               f"an earlier session read it {sized.shape}, and the size doesn't come down on its own")
        return Announcement("kept", sized.shape, _line("kept", sized, sized.band),
                            f"Kept {sized.band}, as you chose; {why}.")
    if sized.chosen and not sized.recorded:
        return Announcement("first", sized.band, _line("first", sized, sized.band),
                            f"I'm treating this as a {sized.band} plan, as you set it.")
    if not sized.chosen and not sized.recorded:
        plain = (f"I'm treating this as a {sized.band} plan: {_listed(sized.signals)}. "
                 f"{schema.SIZE_MEANS[sized.band]}")
        return Announcement("first", sized.band, _line("first", sized, sized.band), plain)
    if not sized.chosen and _rank(sized.shape) > _rank(sized.recorded):
        at_band = [s for s in sized.signals if s.band == sized.shape]
        plain = (f"The plan has grown: {_listed(at_band)} now, so it's a {sized.shape} plan from here. "
                 f"{_GROWN[sized.shape]} Nothing already decided changes.")
        return Announcement("grew", sized.shape, _line("grew", sized, sized.shape), plain)
    return None


_GROWN = {"medium": "Options get written down before a grill.",
          "large": "Every step is in, with a review after each mode."}
