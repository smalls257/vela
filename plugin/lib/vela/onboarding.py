"""Which onboarding path a person gets: the audience, the project's stage, the lead's tuning, and the order of modules.

The Violation this module exists to prevent is the Paper Tiger: an onboarding that lists every page and covers no
one's need. So the path is a short, fixed shape: the five core parts every newcomer gets, in this order, then three
to five role specifics chosen by audience and stage. The lead can reorder or hide the specifics (never the five), and
the newcomer's own path can only choose among modules this file names, so "nothing invented" is structural: a module
id that is not in `MODULE_IDS` cannot be written anywhere.

Pure: facts in (the explorer's data), a path out. No disk, git or clock. `onboardmodules` builds what each module says.
"""
AUDIENCES = ("lead", "exec", "product", "qa", "eng", "mgr")
AUDIENCE_LABELS = {"lead": "Lead", "exec": "Exec", "product": "Product", "qa": "QA", "eng": "Engineering", "mgr": "Managers"}
STAGES = ("discovery", "design", "delivery")
# A role as a person says it, including each phrase /vela:onboard offers ("exec sponsor, product owner, engineer, QA lead, ...").
ROLE_WORDS = {**{a: a for a in AUDIENCES}, **{label.casefold(): a for a, label in AUDIENCE_LABELS.items()},
              "exec sponsor": "exec", "executive": "exec", "sponsor": "exec", "product owner": "product", "engineer": "eng", "qa lead": "qa",
              "delivery manager": "mgr", "manager": "mgr", "solution lead": "lead"}

CORE = ("goal", "approach", "standing", "fit", "people")
AUDIENCE_BOUND = ("fit", "people")  # these two read differently for each audience; every other module is one text for all

# Three to five role specifics per audience and stage, in the order the path shows them.
SPECIFICS = {
    "lead": {"discovery": ("open-questions", "needs-you", "risks"),
             "design": ("needs-you", "open-questions", "handoff"),
             "delivery": ("needs-you", "slices", "blocked")},
    # An exec asks "what ships when, and in what pieces" at every stage, so the slices are on the path from discovery on;
    # before the plan has any, the module says so and who to ask rather than being absent.
    "exec": {"discovery": ("risks", "dates", "slices", "decisions-waiting"),
             "design": ("risks", "dates", "slices", "decisions-waiting"),
             "delivery": ("risks", "dates", "slices", "decisions-waiting")},
    "product": {"discovery": ("capabilities", "open-questions", "journeys"),
                "design": ("capabilities", "journeys", "dates", "open-questions"),
                "delivery": ("slices", "journeys", "dates")},
    "qa": {"discovery": ("journeys", "open-questions", "risks"),
           "design": ("criteria", "contracts", "failure", "open-questions"),
           "delivery": ("slices", "criteria", "failure", "contracts")},
    "eng": {"discovery": ("apps", "open-questions", "journeys"),
            "design": ("apps", "contracts", "journeys", "open-questions"),
            "delivery": ("handoff", "contracts", "journeys", "blocked")},
    "mgr": {"discovery": ("open-questions", "dates", "risks"),
            "design": ("progress", "dates", "blocked"),
            "delivery": ("progress", "slices", "blocked", "dates")},
}


def _all_specifics():
    seen = []
    for by_stage in SPECIFICS.values():
        for ids in by_stage.values():
            for module in ids:
                if module not in seen:
                    seen.append(module)
    return tuple(seen)


MODULE_IDS = CORE + _all_specifics()

# What the lead types on the tuning page and what `vela onboard` lists: a plain name per module, never the id.
NAMES = {
    "goal": "Goal", "approach": "Approach", "standing": "Where things stand", "fit": "Where you fit", "people": "Who to talk to",
    "needs-you": "What's waiting", "open-questions": "Open questions", "risks": "Risks", "dates": "Dates",
    "decisions-waiting": "Decisions waiting", "capabilities": "Capabilities", "journeys": "Journeys", "slices": "Slices",
    "apps": "Apps", "contracts": "Contracts", "criteria": "Acceptance criteria", "failure": "Failure behavior",
    "handoff": "Handoff", "progress": "Progress", "blocked": "Who is blocking what",
}
BY_NAME = {name.casefold(): module for module, name in NAMES.items()}

BUILT = ("building", "journey passes", "live but off", "on")  # slice statuses that mean building has begun
DESIGN_STAGES = ("boundaries", "contracts", "handoff", "epics")  # app stages that mean design is under way


def stage_of(facts):
    """One stage for the whole project, from what the vault holds: discovery until an app is past naming and
    researching (or a flow or contract exists), design until an app is handed off or a slice is being built,
    then delivery. A role's modules still show each app's own state, so one value per project is enough."""
    rows = facts["progress"]["rows"]
    slices = facts["slicePlan"]["list"]
    if any(r["handoff"]["handedOff"] for r in rows) or any(s["status"] in BUILT for s in slices):
        return "delivery"
    if any(r["stage"] in DESIGN_STAGES for r in rows) or facts["flows"] or facts["map"]["contracts"]:
        return "design"
    return "discovery"


def key_of(module_id, audience):
    """The key a module goes by in the data: `fit@eng` for the two audience-bound modules, else the id."""
    return f"{module_id}@{audience}" if module_id in AUDIENCE_BOUND else module_id


def standard_ids(audience, stage, tuning=None):
    """The ids of the standard path: the five core parts, then the audience's specifics for the stage after the
    lead's tuning (`tuning` is an `onboardtune.RoleTuning` or None). Stressed ones come first, played-down ones
    last, hidden ones are left out; the order is otherwise the table's. The five core parts are never moved."""
    specifics = list(SPECIFICS[audience][stage])
    if tuning is not None:
        specifics = [m for m in specifics if m not in tuning.hide]
        specifics.sort(key=lambda m: 0 if m in tuning.stress else 2 if m in tuning.play_down else 1)  # stable
    return list(CORE) + specifics


def hidden_ids(audience, stage, tuning):
    """The specifics the lead hid for this audience at this stage: what a newcomer may ask to bring back."""
    if tuning is None:
        return []
    return [m for m in SPECIFICS[audience][stage] if m in tuning.hide]


def path_keys(audience, ids):
    return [key_of(m, audience) for m in ids]


def role_for(record="", cached="", picked=""):
    """(role, source) a person opens as: the lead's record for them (`roles:` in .vela.yaml), else their own choice kept by
    `vela whoami --role`, else the role door a reader of the shared copy picked. ("", "") when none is known.
    The lead's record wins because the lead knows who holds which seat; the person's choice is a default."""
    for source, value in (("record", record), ("choice", cached), ("door", picked)):
        if value in AUDIENCES:
            return value, source
    return "", ""
