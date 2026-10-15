"""Who owns a skill's text pins (overhaul plan Task 3, review M2).

A test that pins two skills' text in one function is a Distributed Monolith in the suite: two skill rewrites edit the same
test, so they cannot run in parallel and one silently breaks the other's pin. Shield: each skill's (or shared
reference's) text is pinned in exactly one file, `tests/skills/test_<owner>_text.py`, owned by that skill's rewrite.

The sensor reads test source with `ast`, so it needs no run of the tests it inspects. A function "names" a skill when a
path to that skill's text reaches a read in it, directly or through a module-level helper or constant it uses:
`skill_text("close")`, `PLUGIN / "skills" / "grill" / "SKILL.md"`, `read("references", "START.md")`,
`text("skills/epics/SKILL.md")`, or a loop of skill names fed to such a read. A string on the left of `in` is the text
being looked for, not a read, so `"references/START.md" in body` names nothing. A glob over every skill names none:
that is a rule every skill keeps, not a pin of one skill's words.
"""
import ast
import re

from conftest import REPO

TESTS = REPO / "tests"
SKILLS = frozenset(p.name for p in (REPO / "plugin" / "skills").iterdir() if (p / "SKILL.md").is_file())

# A shared reference's owner is the file its pins live in: tests/skills/test_<owner>_text.py.
REFERENCE_OWNER = {
    "START.md": "start", "ANSWER-A-CHALLENGE.md": "start",  # START sends a challenge answer to its own file
    "MODES.md": "modes",
    "REVIEW.md": "review", "REVIEW-RERUN.md": "review",  # REVIEW sends a rerun to its own file
    "CONVERSATION-VOICE.md": "conversation-voice",
    "NEG-AUDIT.md": "neg-audit",
    "TECH-DESIGN-FROM-VAULT.md": "tech-design-from-vault",
    "REQUIREMENTS-IN-VAULT.md": "requirements-in-vault",
}

# The one file allowed to read many skills in one function: one loop over the mode skills, kept shared on purpose (plan 8.2).
SHARED_ON_PURPOSE = {"test_conversation_voice.py"}
# Checks that two texts agree with each other, not pins of either's wording. Splitting one would leave each half unable
# to see the other drift, which is the failure it exists to catch.
AGREEMENT_CHECKS = {
    # both copies are the user's own self-audit, kept byte for byte; no rewrite edits it
    "test_design_skill.py::test_the_two_copies_of_the_self_audit_stay_identical",
    # START's list of mode names must show every mode MODES.md defines; a new mode edits both
    "test_session_experience.py::test_session_modes_are_listed_the_same_everywhere",
}

PATH_SKILL = re.compile(r"(?:^|/)skills/([a-z][a-z-]*)/[A-Z][A-Z-]*\.md$")  # a path to a skill's text, not to its folder
PATH_REFERENCE = re.compile(r"(?:^|/)references/([A-Z][A-Z-]*\.md)$")
READERS = {"skill_text"}


def _owner(word):
    if word in SKILLS:
        return word
    return REFERENCE_OWNER.get(word)


def _strings(node):
    """String constants in a `/` chain or a call's arguments, in order: ("plugin", "skills", "grill", "SKILL.md")."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _strings(node.left) + _strings(node.right)
    if isinstance(node, ast.Call):
        found = _strings(node.func.value) if isinstance(node.func, ast.Attribute) else []
        for arg in node.args:
            found += _strings(arg)
        return found
    return []


def _chain_owners(parts):
    owners = set()
    for before, word in zip(parts, parts[1:]):
        if before in ("skills", "plugin/skills") and word in SKILLS:
            owners.add(word)
        if before in ("references", "plugin/references") and word in REFERENCE_OWNER:
            owners.add(REFERENCE_OWNER[word])
    return owners


def _is_text(node, value):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _is_text(node.right, value)
    return isinstance(node, ast.Constant) and node.value == value


def _path_owners(value):
    owners = {m for m in PATH_SKILL.findall(value) if m in SKILLS}
    owners |= {REFERENCE_OWNER[m] for m in PATH_REFERENCE.findall(value) if m in REFERENCE_OWNER}
    return owners


class _Names(ast.NodeVisitor):
    """Owners one node names directly, the module-level names it uses, and whether it reads a skill named by a variable."""

    def __init__(self):
        self.owners, self.used, self.dynamic, self.name_lists, self.calls = set(), set(), False, set(), set()
        self._searched = set()

    def visit_Compare(self, node):
        for op, right in zip(node.ops, node.comparators):
            if isinstance(op, (ast.In, ast.NotIn)) and isinstance(node.left, (ast.Constant, ast.JoinedStr)):
                self._searched.add(id(node.left))
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str) and id(node) not in self._searched:
            self.owners |= _path_owners(node.value)

    def visit_JoinedStr(self, node):
        if id(node) in self._searched:
            return
        literal = "".join(v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
        if re.search(r"(?:^|/)skills/$", literal.split("{")[0]) or "skills/" in literal:
            self.dynamic = True
        self.generic_visit(node)

    def visit_BinOp(self, node):
        self.owners |= _chain_owners(_strings(node))
        if isinstance(node.op, ast.Div) and _is_text(node.left, "skills") and not isinstance(node.right, ast.Constant):
            self.dynamic = True  # PLUGIN / "skills" / name
        self.generic_visit(node)

    def visit_Call(self, node):
        self.owners |= _chain_owners(_strings(node))
        name = node.func.id if isinstance(node.func, ast.Name) else None
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value in SKILLS:
                self.calls.add((name, arg.value))  # a reader only if the callee reads a skill named by its argument
            elif name in READERS and not isinstance(arg, ast.Constant):
                self.dynamic = True
        self.generic_visit(node)

    def visit_Tuple(self, node):
        self._list(node)

    visit_List = visit_Set = visit_Tuple

    def _list(self, node):
        words = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        if words and len(words) == len(node.elts) and all(_owner(w) for w in words):
            self.name_lists.add(frozenset(_owner(w) for w in words))
        self.generic_visit(node)

    def visit_Name(self, node):
        self.used.add(node.id)


def _module_defs(tree):
    defs = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defs[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        defs[name.id] = node
    return defs


def pin_owners(source):
    """{test function name: owners its text pins name}, for every top-level `test_*` function in `source`."""
    tree = ast.parse(source)
    defs = _module_defs(tree)
    seen_nodes = {}

    def names_of(node):
        if id(node) not in seen_nodes:
            visitor = _Names()
            visitor.visit(node)
            if isinstance(node, ast.FunctionDef):
                visitor.used |= {a.arg for a in node.args.args}  # a fixture is used by naming it as a parameter
            seen_nodes[id(node)] = visitor
        return seen_nodes[id(node)]

    def closure(node):
        """Everything `node` reaches through the module-level names it uses."""
        found, todo, done = [], [node], set()
        while todo:
            current = todo.pop()
            if id(current) in done:
                continue
            done.add(id(current))
            found.append(names_of(current))
            todo += [defs[n] for n in found[-1].used if n in defs]
        return found

    def reads_by_argument(name):
        if name in READERS:
            return True
        helper = defs.get(name)
        return isinstance(helper, ast.FunctionDef) and any(v.dynamic for v in closure(helper))

    result = {}
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith("test_")):
            continue
        reached = closure(node)
        owners = set().union(*(v.owners for v in reached))
        owners |= {owner for v in reached for callee, owner in v.calls if reads_by_argument(callee)}
        if any(v.dynamic for v in reached):
            owners |= set().union(*(group for v in reached for group in v.name_lists))
        result[node.name] = owners
    return result


def test_the_sensor_sees_two_skills_through_a_helper_a_constant_and_a_loop():
    source = '''
from conftest import REPO, skill_text
PLUGIN = REPO / "plugin"
CLOSE = skill_text("close")
NAMES = ("boundary", "releases")
def read(*parts):
    return PLUGIN.joinpath(*parts).read_text()
def test_through_a_constant_and_a_helper():
    assert "x" in CLOSE and "y" in read("skills", "grill", "SKILL.md")
def test_through_a_loop():
    for name in NAMES:
        assert "x" in skill_text(name)
def test_a_reference_by_its_path():
    assert "y" in (PLUGIN / "references" / "START.md").read_text() and "z" in (PLUGIN / "skills/epics/SKILL.md").read_text()
def test_looking_for_a_path_is_not_reading_it():
    assert "references/START.md" in skill_text("tickets")
def test_a_glob_over_every_skill_names_none():
    for path in (PLUGIN / "skills").glob("*/SKILL.md"):
        assert "sed -i" not in path.read_text()
'''
    found = pin_owners(source)
    assert found["test_through_a_constant_and_a_helper"] == {"close", "grill"}
    assert found["test_through_a_loop"] == {"boundary", "releases"}
    assert found["test_a_reference_by_its_path"] == {"start", "epics"}
    assert found["test_looking_for_a_path_is_not_reading_it"] == {"tickets"}
    assert found["test_a_glob_over_every_skill_names_none"] == set()


def test_no_text_pin_outside_tests_skills_spans_two_skills():
    spans = []
    for path in sorted(TESTS.glob("*.py")):
        if path.name in SHARED_ON_PURPOSE:
            continue
        for test, owners in pin_owners(path.read_text(encoding="utf-8")).items():
            if len(owners) > 1 and f"{path.name}::{test}" not in AGREEMENT_CHECKS:
                spans.append(f"tests/{path.name}::{test} pins {', '.join(sorted(owners))}")
    assert not spans, ("one test function pins more than one skill's text, so two skill rewrites would edit it; split it "
                       "into one test per skill in tests/skills/test_<skill>_text.py:\n" + "\n".join(spans))


def test_each_file_in_tests_skills_pins_only_its_own_skill():
    strays = []
    for path in sorted((TESTS / "skills").glob("test_*_text.py")):
        own = path.name[len("test_"):-len("_text.py")].replace("_", "-")
        for test, owners in pin_owners(path.read_text(encoding="utf-8")).items():
            if owners - {own}:
                strays.append(f"tests/skills/{path.name}::{test} pins {', '.join(sorted(owners - {own}))}")
    assert not strays, "a skill's text file pins another skill's text, so that skill's rewrite would edit it:\n" + "\n".join(strays)
