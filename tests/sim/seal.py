#!/usr/bin/env python3
"""The seal on the persona answer keys: which personas are dev and which are holdout, the terms that would give a
key away, a redaction pass that strips them from text meant for skill authors, and a leak scan of plugin/**.

The Violation this module exists to prevent is the Paper Tiger: a skill tuned until its sim scores rise because it
learned the answer key (a persona's names, keywords or brief text), not because sessions got better for a real lead.
Scores then pass and real leads still get the old behavior. Three walls keep the key out of the skills:

- a split: every persona file says `split: dev` or `split: holdout`. Dev personas may be read while iterating;
  a holdout is scored, never read. A persona whose split can't be read is treated as holdout (sealed), never as dev.
- a redaction step: text written for skill authors (tests/sim/failures.py) passes through `redact`, which replaces
  every key term with "[redacted]" and counts them, so a missed term shows as a count, not a quiet leak.
- a leak scan: `plugin_leaks` lists every key term found under plugin/**. tests/test_sim_seal.py fails on any leak
  not in tests/sim/seal-known-leaks.txt, and on any listed leak that is gone, so the list only shrinks.

Usage:
  python3 tests/sim/seal.py --leaks            every key term in plugin/**, by file (exit 1 when there is one)
  python3 tests/sim/seal.py --prune            drop the lines of seal-known-leaks.txt whose leak is gone
  python3 tests/sim/seal.py --write-known      rewrite seal-known-leaks.txt from today's plugin, new leaks too:
                                               a reviewed change only, never a way to make the test pass
"""
import argparse
import functools
import pathlib
import re
import sys
import sysconfig

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PERSONAS = HERE / "personas"
PLUGIN = REPO / "plugin"
KNOWN_LEAKS = HERE / "seal-known-leaks.txt"
sys.path.insert(0, str(PLUGIN / "lib"))  # the plugin's bundled PyYAML
import yaml  # noqa: E402

SPLITS = ("dev", "holdout")
REDACTED = "[redacted]"

# Example vaults that are legitimately in the repo. A term that also appears in one is the example's, not a key's:
# coastal-merger borrowed Harborline, Northway and FERRYMASTER from examples/unified-booking, which the plugin's
# explorer and docs quote as the worked example. CONVENTIONS.md in an example is the plugin's own file, copied into
# every vault, so it is not read as the example's text (it would launder the plugin's leaks into the allowlist).
EXAMPLE_VAULTS = (REPO / "examples" / "unified-booking",)
EXAMPLE_SKIP = {"CONVENTIONS.md", "CLAUDE.md"}

# Files under plugin/ that are not the plugin's own words: vendored libraries and binary assets.
PLUGIN_SKIP_DIRS = {("lib", "yaml"), }
PLUGIN_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".mp3", ".ogg", ".wav",
                        ".pyc"}
PLUGIN_SKIP_NAMES = re.compile(r"\.min\.(?:js|css)$")

# Real products, standards, roles and ordinary words the personas mention that any planning tool may name. A
# capitalized word or a keyword listed here is generic, so finding it in the plugin is not a leak. Reviewed against
# the plugin of 2026-10-15; adding to this list is a reviewed change, never a way to make the leak test pass.
REAL_WORLD = {
    "microsoft", "teams", "graph", "intune", "jamf", "windows", "mac", "macs", "macos", "onedrive", "sharepoint",
    "outlook", "zoom", "webex", "copilot", "github", "aws", "ecs", "rds", "fargate", "postgres", "sqlite", "sqlcipher",
    "redis", "dynamodb", "graphql", "openapi", "fastapi", "python", "rust", "swift", "tauri", "android", "datadog",
    "voiceover", "jaws", "nvda", "oauth", "msix", "keychain", "gdpr", "nhs", "wcag", "eu", "uk", "us", "ai",
    "regulation", "agenda", "officer",  # ordinary words a persona only ever capitalizes (Regulation Best Interest)
}
GENERIC_KEYWORDS = {  # ordinary phrases a neutral corpus happens to lack; each is plain planning or IT language
    "never reads", "handed off", "hand off", "linking the", "data protection", "data protection officer", "30 days",
    "screen reader", "product owner", "five times", "unverified", "unmerge", "licence", "notarized", "notarised",
    "running costs", "notice period", "local model", "order status", "never suggests", "security review", "by post",
    "in writing", "a third", "consent record", "cfo", "rtt", "service level", "only review", "new review",
    "three question", "three-question", "not a log", "payment gateway",
}
MIN_NAME = 3
SHINGLE = 6  # brief text is matched as runs of six words: shorter runs collide with ordinary prose


# ------------------------------------------------------------------ the split

def load(path):
    return yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))


def split_of(persona):
    """'dev' or 'holdout' from a persona mapping; None when it says neither. The old `holdout: true` reads holdout."""
    if not isinstance(persona, dict):
        return None
    split = persona.get("split")
    if split in SPLITS:
        return split
    return "holdout" if persona.get("holdout") is True else None


def persona_path(ref, personas=PERSONAS):
    path = pathlib.Path(str(ref))
    return path if path.suffix == ".yaml" else personas / f"{path.name}.yaml"


def sealed(ref, personas=PERSONAS):
    """(sealed, why): True unless the persona file says `split: dev`. A missing name, a missing file or a missing
    split is sealed, so a run nobody labeled never prints its key by default."""
    if not ref:
        return True, "the run names no persona, so it is treated as holdout"
    path = persona_path(ref, personas)
    if not path.is_file():
        return True, f"{path.name} is not in {personas}, so it is treated as holdout"
    split = split_of(load(path))
    if split is None:
        return True, f"{path.name} says neither `split: dev` nor `split: holdout`, so it is treated as holdout"
    return split == "holdout", f"{path.stem} is a {split} persona"


# ------------------------------------------------------------------ the terms that give a key away

def norm(text):
    """Case, whitespace, quote marks and emphasis do not change a term (as run.normalize)."""
    return re.sub(r"\s+", " ", re.sub(r"[\"'“”‘’`*_]", "", str(text))).strip().lower()


@functools.lru_cache(maxsize=1)
def neutral_words():
    """Words of Python's own standard library source: a large English and software corpus no persona fed. A
    capitalized persona word that is also an ordinary word here ("Signal", "Bay") is not read as a coined name."""
    root = pathlib.Path(sysconfig.get_paths()["stdlib"])
    words = set()
    for path in root.rglob("*.py"):
        if "site-packages" in path.parts:
            continue
        words.update(w.lower() for w in re.findall(r"[A-Za-z]+", path.read_text(encoding="utf-8", errors="replace")))
    return frozenset(words)


def tokens(text):
    """Lower-case word tokens of normalized text: how keywords and brief runs are matched."""
    return re.findall(r"[a-z0-9]+", norm(text))


def name_tokens(text):
    """Word tokens as written: how names are matched, so "Heron" is found and "heron" (the bird) is not."""
    return re.findall(r"[A-Za-z0-9]+", str(text))


class Term:
    """One thing that gives a key away: its text, its kind (name, keyword or brief) and the personas it comes from.
    A name matches its words exactly as written; a keyword or brief run matches normalized words, the last one from
    the start of a word, as run.mentions matches a keyword ("partner hotel" finds "partner hotels")."""

    def __init__(self, text, kind, persona):
        self.text, self.kind, self.personas = text, kind, {persona}
        self.words = tuple(name_tokens(text) if kind == "name" else tokens(text))

    @property
    def key(self):
        return self.text if self.kind == "name" else " ".join(self.words)

    def __repr__(self):
        return f"Term({self.text!r}, {self.kind})"


class Matcher:
    """Finds many terms in one pass over a text's words: terms are indexed by their first word, so a scan costs one
    look-up per word, not one regex per term (a regex per term made the plugin scan run for minutes)."""

    def __init__(self, terms):
        self.names, self.flat = {}, {}
        for term in terms:
            if not term.words:
                continue
            index = self.names if term.kind == "name" else self.flat
            index.setdefault(term.words[0], []).append(term)

    @staticmethod
    def _scan(words, index, prefix_last):
        found = set()
        for i, word in enumerate(words):
            for term in index.get(word, ()) if not prefix_last else _starting(index, word):
                n = len(term.words)
                got = words[i:i + n]
                if len(got) < n:
                    continue
                if prefix_last and n > 1:
                    if tuple(got[:-1]) == term.words[:-1] and got[-1].startswith(term.words[-1]):
                        found.add(term)
                elif prefix_last:
                    if got[0].startswith(term.words[0]):
                        found.add(term)
                elif tuple(got) == term.words:
                    found.add(term)
        return found

    def find(self, text):
        return (self._scan(name_tokens(text), self.names, False)
                | self._scan(tokens(text), self.flat, True))


def _starting(index, word):
    """The terms whose first word is `word`, or, for a one-word term, a word `word` starts with."""
    out = list(index.get(word, ()))
    for cut in range(3, len(word)):
        out += [t for t in index.get(word[:cut], ()) if len(t.words) == 1]
    return out


@functools.lru_cache(maxsize=1)
def neutral_words_list():
    """Every normalized word of the standard library, the vault template and the example vaults, in order: a keyword
    phrase found in them is ordinary language or Vela's own vocabulary, not a key."""
    out = []
    root = pathlib.Path(sysconfig.get_paths()["stdlib"])
    for path in sorted(root.rglob("*.py")):
        if "site-packages" not in path.parts:
            out += tokens(path.read_text(encoding="utf-8", errors="replace")) + ["\n"]
    for base in (REPO / "template", *EXAMPLE_VAULTS):
        for path in sorted(base.rglob("*.md")):
            if path.name not in EXAMPLE_SKIP:
                out += tokens(path.read_text(encoding="utf-8", errors="replace")) + ["\n"]
    return out


@functools.lru_cache(maxsize=1)
def example_text():
    """The example vaults' own pages, as written (CONVENTIONS.md left out: it is the plugin's file)."""
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for base in EXAMPLE_VAULTS
                     for p in sorted(base.rglob("*.md")) if p.name not in EXAMPLE_SKIP)


BRIEF_KINDS = ("knows", "wrong", "unaware", "conflicts", "decisions")
BRIEF_FIELDS = ("fact", "belief", "truth", "gap", "why", "position", "question", "choice", "reason", "who", "owner")


def strings(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)
    elif isinstance(value, str):
        yield value


def lower_words(personas):
    """Every word any persona writes in lower case: a word some persona writes as an ordinary word ("consent",
    "regulation") is not a coined name when another capitalizes it."""
    return {w.lower() for path in sorted(pathlib.Path(personas).glob("*.yaml"))
            for w in re.findall(r"\b[a-z][\w-]*", "\n".join(strings(load(path))))}


def coined_names(persona, lower=frozenset()):
    """Capitalized words a persona uses that are names it made up: never written in lower case by any persona, not
    an ordinary word in the neutral corpus, not a real product, and not an acronym of four letters or fewer."""
    text = "\n".join(strings(persona))
    lower = set(lower) | {w.lower() for w in re.findall(r"\b[a-z][\w-]*", text)}
    words = neutral_words()
    out = set()
    for m in re.finditer(r"\b[A-Z][A-Za-z]+\b", text):
        word = m.group(0)
        key = word.lower()
        if len(word) < MIN_NAME or key in words or key in REAL_WORLD or key in lower:
            continue
        if word.isupper() and len(word) <= 4:
            continue
        out.add(word)
    return out


def person_names(persona):
    """The persona's full name and each part of it that isn't an ordinary word."""
    name = str(persona.get("name") or "").strip()
    if not name:
        return set()
    words = neutral_words()
    return {name} | {part for part in name.split() if len(part) >= MIN_NAME and part.lower() not in words}


def keyword_candidates(persona):
    for kind in BRIEF_KINDS:
        for item in persona.get(kind) or []:
            for word in item.get("keywords") or []:
                flat = norm(word) if isinstance(word, str) else ""
                if len(flat) >= MIN_NAME and flat not in GENERIC_KEYWORDS and flat not in REAL_WORLD:
                    yield word


def brief_runs(persona):
    """Every run of SHINGLE words in the brief's item text and the inbox documents."""
    texts = [str(item.get(f)) for kind in BRIEF_KINDS for item in persona.get(kind) or [] for f in BRIEF_FIELDS
             if isinstance(item.get(f), str)]
    texts += [d.get("text", "") for d in persona.get("docs") or [] if isinstance(d, dict)]
    runs = set()
    for text in texts:
        words = tokens(text)
        runs.update(" ".join(words[i:i + SHINGLE]) for i in range(len(words) - SHINGLE + 1))
    return runs


def _all_terms(personas, include_brief):
    terms = {}

    def add(text, kind, who):
        term = Term(text, kind, who)
        if (kind, term.key) in terms:
            terms[(kind, term.key)].personas.add(who)
        else:
            terms[(kind, term.key)] = term

    lower = lower_words(personas)
    for path in sorted(pathlib.Path(personas).glob("*.yaml")):
        persona = load(path)
        if not isinstance(persona, dict):
            continue
        who = path.stem
        for name in person_names(persona) | coined_names(persona, lower):
            add(name, "name", who)
        for word in keyword_candidates(persona):
            add(word, "keyword", who)
        if include_brief:
            for run in brief_runs(persona):
                add(run, "brief", who)
    keywords = [t for t in terms.values() if t.kind == "keyword"]
    ordinary = Matcher._scan(neutral_words_list(), Matcher(keywords).flat, True)
    return [t for t in terms.values() if t not in ordinary]


@functools.lru_cache(maxsize=4)
def _terms_cached(personas, include_brief):
    terms = _all_terms(personas, include_brief)
    in_examples = Matcher(terms).find(example_text())
    return tuple(t for t in terms if t not in in_examples), tuple(sorted(t.key for t in in_examples if t.kind != "brief"))


def persona_terms(personas=PERSONAS, include_brief=True):
    """Every term of every persona file, merged by text. A keyword found in the neutral corpus is ordinary, and a
    term the example vaults hold is the example's (see EXAMPLE_VAULTS), so neither is a key term."""
    return list(_terms_cached(str(personas), include_brief)[0])


def allowlisted_by_examples(personas=PERSONAS):
    """The names and keywords left out because an example vault holds them, for the report."""
    return list(_terms_cached(str(personas), True)[1])


# ------------------------------------------------------------------ redaction

def redact(text, terms):
    """(text with every term replaced by [redacted], how many were replaced). Longest terms first, so a full name
    goes before its surname; names match as written, keywords and brief runs whatever their case."""
    count = 0
    for term in sorted(terms, key=lambda t: -len(t.words)):
        sep = r"[^A-Za-z0-9]+"
        body = sep.join(re.escape(w) for w in term.words)
        if term.kind == "name":
            pattern = re.compile(rf"(?<![A-Za-z0-9]){body}(?![a-z0-9])")
        else:
            pattern = re.compile(rf"(?<![A-Za-z0-9]){body}[a-z0-9]*", re.I)
        text, n = pattern.subn(REDACTED, text)
        count += n
    return text, count


def leaks_in(text, terms):
    return Matcher(terms).find(text)


# ------------------------------------------------------------------ the plugin scan

def plugin_files(plugin=PLUGIN):
    for path in sorted(pathlib.Path(plugin).rglob("*")):
        rel = path.relative_to(plugin)
        if not path.is_file() or "__pycache__" in rel.parts or tuple(rel.parts[:2]) in PLUGIN_SKIP_DIRS:
            continue
        if path.suffix.lower() in PLUGIN_SKIP_SUFFIXES or PLUGIN_SKIP_NAMES.search(path.name):
            continue
        yield rel, path.read_text(encoding="utf-8", errors="replace")


def plugin_leaks(plugin=PLUGIN, personas=PERSONAS):
    """{(file, kind, term)} for every key term found in a plugin file. `file` is relative to plugin/."""
    matcher = Matcher(persona_terms(personas))
    return {(rel.as_posix(), t.kind, t.key) for rel, text in plugin_files(plugin) for t in matcher.find(text)}


def read_known(path=KNOWN_LEAKS):
    if not path.is_file():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            file, kind, term = line.split("\t")
            out.add((file, kind, term))
    return out


def write_known(found, path=KNOWN_LEAKS):
    head = ("# Key terms from tests/sim/personas/ found in plugin/** on the day each line was added. A line here is a\n"
            "# leak still to remove, not a permission: tests/test_sim_seal.py fails on any leak not listed and on any\n"
            "# listed leak that is gone, so this file only shrinks. file<TAB>kind<TAB>term\n")
    path.write_text(head + "".join(f"{f}\t{k}\t{t}\n" for f, k, t in sorted(found)), encoding="utf-8")


def report(found):
    by_file = {}
    for file, kind, term in sorted(found):
        by_file.setdefault(file, []).append(f"{term} ({kind})")
    lines = [f"{len(found)} key terms in {len(by_file)} plugin files:"]
    lines += [f"- plugin/{f}: {', '.join(v)}" for f, v in by_file.items()]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--leaks", action="store_true", help="list every key term found in plugin/**")
    p.add_argument("--prune", action="store_true", help="drop the known leaks that are gone from the plugin")
    p.add_argument("--write-known", action="store_true", help="rewrite seal-known-leaks.txt from today's plugin")
    args = p.parse_args(argv)
    found = plugin_leaks()
    if args.prune:
        known = read_known()
        write_known(known & found)
        print(f"dropped {len(known - found)} lines; {len(known & found)} known leaks remain")
        return 0
    if args.write_known:
        write_known(found)
        print(f"wrote {len(found)} lines to {KNOWN_LEAKS}")
        return 0
    print(report(found))
    print("Allowed because an example vault holds them: " + ", ".join(allowlisted_by_examples()))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
