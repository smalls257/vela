#!/usr/bin/env python3
"""Copy the Unified Booking example and add demo data the explorer needs to show its releases, domains and front doors.

    python3 tests/fixtures/explorer/make_demo_vault.py <dir>

`examples/unified-booking` has no releases, no domains on its app pages and no functional requirements, and many
tests depend on it as it is, so it is never edited. This writes a copy to <dir> (replacing what is there) and adds,
all labeled as demo data on the pages themselves:

- a `domain:` on every app page, as a proposal: Channels (website, kiosks, call center); Booking core (booking,
  pricing, vessel schedule); Platform (customer identity, notifications); Legacy (FERRYMASTER);
- functional requirements at `assumption`, two or three on several capability pages, in the CONVENTIONS format;
- a `## Requirements allocated` table on each app that carries a share, through existing contracts only;
- `04b-releases.md` with three releases, two requirements split across releases by acceptance criteria;
- links out of the vault, every one on an example.com host: a Jira key on every epic (with a `link_templates`
  entry in `.vela.yaml`), Confluence and GitHub on every app page, and API spec and docs on each outside party
  and third-party contract; and `icon: legacy` on FERRYMASTER, whose title would otherwise read as a ship;
- three open questions with ask-by dates around the demo date, one already overdue, so the map shows work in
  flight rather than a finished plan.

Then it runs `vela render`, so the generated blocks agree with the new rows, and rewrites Booking's handoff
manifest, so the demo rows do not read as drift since the senior's handoff. The demo's pinned layout, pins/unified-booking.json,
is copied to `.vela/explorer-pins.json` in the new vault, where `vela explore` keeps it, so the plugin's build and
the explorer's own builds place every app alike. The result passes
`vela check --today 2026-11-20` with no errors.
"""
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / "examples" / "unified-booking"
VELA = REPO / "plugin" / "scripts" / "vela"
DEMO_PINS = HERE / "pins" / "unified-booking.json"
VAULT_PINS = ".vela/explorer-pins.json"
TODAY = "2026-11-20"
DEMO = "Demo data, written by `tests/fixtures/explorer/make_demo_vault.py`, not part of the example."

DOMAINS = {  # app page file -> domain (a proposal for the demo)
    "website": "Channels", "kiosks": "Channels", "call-center": "Channels",
    "booking": "Booking core", "pricing": "Booking core", "vessel-schedule": "Booking core",
    "customer-identity": "Platform", "notifications": "Platform",
    "ferrymaster": "Legacy",
}

# capability page stem -> [(FR number, short name, paragraph, [acceptance criteria])]
REQUIREMENTS = {
    "CAP-013-reserve-a-crossing": [
        (1, "Confirm a booking online",
         "A customer on the website turns a held crossing into a confirmed booking, and is told it is confirmed only "
         "once the ledger has it.",
         ["The website shows a booking as confirmed only after the ledger has recorded it.",
          "A confirmation the ledger rejects shows as failed, never as confirmed.",
          "The customer is given a booking reference on the confirmation page."]),
        (2, "Confirm a booking at the call center",
         "An agent books a crossing for a caller and sees the same booking state the website would show.",
         ["An agent confirms a held crossing and reads the booking reference back to the caller.",
          "An agent finds a booking made on the website by its reference."]),
        (3, "Confirm a booking at a port kiosk",
         "A customer at the terminal buys a crossing at a kiosk and can look the booking up there later.",
         ["A kiosk confirms a held crossing and prints the booking reference.",
          "A kiosk shows a booking's state when its reference is scanned.",
          "A kiosk shows bookings made in any channel, not only its own."]),
    ],
    "CAP-014-hold-a-seat": [
        (1, "Hold a seat while the customer pays",
         "A seat is held for the customer from the moment they choose a crossing until they pay, so nobody else can "
         "take it in between.",
         ["A hold keeps the seat for 15 minutes.",
          "A hold is refused when the sailing is full."]),
        (2, "Release a hold that runs out",
         "A hold that is not paid for in time goes back on sale without anyone acting.",
         ["A hold that passes 15 minutes unpaid is released.",
          "A released hold's seat can be booked again straight away."]),
    ],
    "CAP-012-quote-a-fare": [
        (1, "One fare in every channel",
         "The same crossing, date and passengers get the same fare whichever channel asks.",
         ["The website, call center and kiosks quote the same fare for the same crossing.",
          "A quoted fare holds for as long as the seat is held."]),
    ],
    "CAP-015-take-payment": [
        (1, "Pay for a held crossing",
         "The customer pays by card for a held crossing, and the booking follows the payment's outcome.",
         ["A paid hold becomes a confirmed booking.",
          "A failed payment releases the hold and says so to the customer."]),
    ],
    "CAP-021-amend-or-cancel": [
        (1, "Amend a booking online",
         "A customer moves their booking to another sailing on the same route without phoning.",
         ["A customer moves a booking to another sailing on the same route.",
          "The fare difference is shown before the customer confirms the change.",
          "An amendment is confirmed only once the ledger has it."]),
        (2, "Cancel a booking online",
         "A customer cancels their own booking and is told what refund they get.",
         ["A customer cancels a booking up to 24 hours before sailing.",
          "The refund the customer will get is shown before they confirm."]),
    ],
    "CAP-022-notify-customer": [
        (1, "Tell the customer when a booking changes",
         "The customer hears from us when their booking is confirmed, amended or canceled, whichever channel made the "
         "change.",
         ["An email goes out when a booking is confirmed.",
          "An email goes out when a booking is amended or canceled.",
          "No message goes out for a booking that failed."]),
    ],
}

CAP_PAGES = {stem.split("-", 2)[0] + "-" + stem.split("-", 2)[1]: stem for stem in REQUIREMENTS}  # "CAP-013" -> stem

# app page file -> [(requirement, share, through, state)]; Through names existing contracts only
ALLOCATION = {
    "booking": [
        ("CAP-013.FR1", "decides a booking is confirmed once the ledger has it, and answers the website", "CON-001", "assumption"),
        ("CAP-013.FR2", "answers the call center's confirm and look-up calls", "CON-001", "assumption"),
        ("CAP-013.FR3", "answers the kiosks' confirm and look-up calls", "CON-001", "assumption"),
        ("CAP-014.FR1", "holds the seat after checking capacity", "CON-004", "assumption"),
        ("CAP-014.FR2", "releases a hold that runs out", "—", "assumption"),
        ("CAP-012.FR1", "asks Pricing for the fare it quotes to every channel", "CON-003", "assumption"),
        ("CAP-015.FR1", "follows Tidepay's payment outcome", "CON-007", "assumption"),
        ("CAP-021.FR1", "moves a booking to another sailing and writes it to the ledger", "CON-001", "assumption"),
        ("CAP-021.FR2", "cancels a booking and writes it to the ledger", "CON-001", "assumption"),
        ("CAP-022.FR1", "publishes each change of a booking's state", "CON-002", "assumption"),
    ],
    "website": [
        ("CAP-013.FR1", "shows the confirmation and the reference", "—", "assumption"),
        ("CAP-021.FR1", "lets the customer pick another sailing and see the fare difference", "—", "assumption"),
        ("CAP-021.FR2", "lets the customer cancel and see the refund", "—", "assumption"),
    ],
    "call-center": [
        ("CAP-013.FR2", "lets the agent confirm and find bookings", "—", "assumption"),
    ],
    "kiosks": [
        ("CAP-013.FR3", "confirms, prints and looks up bookings at the terminal", "—", "assumption"),
    ],
    "pricing": [
        ("CAP-012.FR1", "quotes one fare for a crossing to Booking", "CON-003", "assumption"),
    ],
    "ferrymaster": [
        ("CAP-013.FR1", "records the confirmed booking in the ledger of record", "CON-006", "assumption"),
        ("CAP-021.FR1", "records the amendment in the ledger of record", "CON-006", "assumption"),
    ],
    "notifications": [
        ("CAP-022.FR1", "sends the customer the email for each change", "—", "assumption"),
    ],
}

# Links out of the vault (CONVENTIONS, "Links out of the vault"). Every host is example.com, so nothing real is implied.
LINK_TEMPLATES = 'link_templates: {Jira: "https://jira.example.com/browse/{key}"}\n'
APP_TITLES = {"website": "Public website", "kiosks": "Port kiosks", "call-center": "Call center desktop", "booking": "Booking",
              "pricing": "Pricing", "vessel-schedule": "Vessel schedule", "customer-identity": "Customer identity",
              "notifications": "Notifications", "ferrymaster": "FERRYMASTER"}
ICONS = {"ferrymaster": "legacy"}
# (page, heading) -> the **Links:** bullet for an outside party or a third-party contract
ITEM_LINKS = {
    ("03-context-and-scope.md", "### PTY-01 Tidepay"):
        "[API spec](https://developer.tidepay.example.com/openapi.yaml), [Docs](https://developer.tidepay.example.com/docs)",
    ("03-context-and-scope.md", "### PTY-02 FERRYMASTER vendor"):
        "[Docs](https://support.ferrymaster.example.com/mq-interface), [Support](https://support.ferrymaster.example.com/tickets)",
    ("05-building-blocks/booking-building-blocks.md", "### CON-007 Tidepay payment outcome"):
        "[API spec](https://developer.tidepay.example.com/webhooks/payment-outcome.yaml), [Docs](https://developer.tidepay.example.com/docs/webhooks)",
    ("05-building-blocks/ferrymaster-building-blocks.md", "### CON-006 Ledger transactions"):
        "[API spec](https://support.ferrymaster.example.com/mq/ledger-transactions.html), [Docs](https://confluence.example.com/display/HARBOR/Ledger+transactions)",
}
# Open questions around the demo date (2026-11-20): one overdue, two due soon. Each says it is demo data.
IN_FLIGHT = [
    ("UNK-009", "Tidepay refund webhook retries", "How often does Tidepay retry a payment outcome Booking did not acknowledge, and for how long?",
     "@hl-booking-senior (Booking senior)", "2026-11-03 Discover", "2026-11-16",
     "[[booking-building-blocks#CON-007 Tidepay payment outcome|CON-007]]"),
    ("UNK-010", "Capacity checks at the kiosk peak", "Does Vessel schedule answer capacity checks within a second when every kiosk sells at once on a summer Saturday?",
     "@hl-port-senior (Port Systems senior)", "2026-11-12 Discover", "2026-11-27",
     "[[vessel-schedule-building-blocks#CON-004 Capacity check|CON-004]]"),
    ("UNK-011", "Guest bookings in the customer lookup", "Does Customer identity return a record for a customer who booked as a guest, or must Booking create one?",
     "@hl-solution-lead (solution lead)", "2026-11-18 Discover", "2026-12-04",
     "[[customer-identity-building-blocks#CON-005 Customer lookup|CON-005]]"),
]

RELEASES = [
    ("Release one: the website books through Booking", "2027-02-01", "assumption",
     "Booking arrives and the website is its first channel: hold, quote, pay and confirm.",
     [("CAP-014.FR1", "all", ""), ("CAP-014.FR2", "all", ""), ("CAP-012.FR1", "AC1, AC2", ""),
      ("CAP-015.FR1", "all", ""), ("CAP-013.FR1", "AC1, AC2", "AC3, the reference, in release two")]),
    ("Release two: call center and kiosks", "2027-03-15", "assumption",
     "The call center moves to Booking, and kiosks follow in the March 2027 image (CST-3).",
     [("CAP-013.FR1", "AC3", "the reference, once every channel prints the same one"),
      ("CAP-013.FR2", "all", ""), ("CAP-013.FR3", "AC1, AC2", "AC3 waits for the September image"),
      ("CAP-022.FR1", "AC1, AC3", "amend and cancel emails come with release three")]),
    ("Release three: amend and cancel online", "2027-05-03", "inkling",
     "Customers amend and cancel without phoning (G3).",
     [("CAP-021.FR1", "all", ""), ("CAP-021.FR2", "all", ""), ("CAP-022.FR1", "AC2", ""),
      ("CAP-013.FR3", "AC3", "the September 2027 kiosk image")]),
]


def requirement_link(fr):
    cap = fr.split(".")[0]
    stem = CAP_PAGES[cap]
    number = int(fr.split("FR")[1])
    name = next(n for k, n, _, _ in REQUIREMENTS[stem] if k == number)
    return f"[[{stem}#{fr} {name}\\|{fr}]]"


def add_domain(path, domain):
    text = path.read_text(encoding="utf-8")
    head, sep, rest = text.partition("\n---\n")
    if "\ndomain:" in head:
        return
    lines = head.split("\n")
    at = next(i for i, line in enumerate(lines) if line.startswith("change:")) + 1
    lines.insert(at, f"domain: {domain}")
    path.write_text("\n".join(lines) + sep + rest, encoding="utf-8")


def add_requirements(path, frs):
    cap = path.stem.split("-", 2)[0] + "-" + path.stem.split("-", 2)[1]
    out = ["", "## Functional requirements", "", DEMO, ""]
    for number, name, para, criteria in frs:
        out += [f"### {cap}.FR{number} {name}", "", para, "", "- **State:** assumption"]
        out += [f"- {c}" for c in criteria]
        out.append("")
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(out))


def add_allocation(path, rows):
    text = path.read_text(encoding="utf-8")
    table = ["## Requirements allocated", "", DEMO, "", "| Requirement | Share | Through | State |", "|---|---|---|---|"]
    table += [f"| {requirement_link(fr)} | {share} | {through} | {state} |" for fr, share, through, state in rows]
    block = "\n".join(table) + "\n\n"
    marker = "\n## Concerns\n"
    if marker in text:
        text = text.replace(marker, "\n" + block + "## Concerns\n", 1)
    else:
        text = text.rstrip("\n") + "\n\n" + block
    path.write_text(text, encoding="utf-8")


def releases_page():
    out = ["---", "id: releases", "type: initiative-section", "title: Releases", "initiative: INI-002", 'arc42: "§4"',
           "state: assumption", 'owner: "@hl-solution-lead"', "authored: mixed", "---", "",
           "[[README|Harborline]] / Releases", "", "# Releases", "",
           f"{DEMO} The example plans no releases; these three show how the explorer draws the system before and after "
           "each one. Two requirements are split across releases by their acceptance criteria.", ""]
    for name, target, state, para, rows in RELEASES:
        out += [f"## {name}", "", f"- **Target:** {target}", f"- **State:** {state}", "", para, "",
                "| Delivers | Criteria | Note |", "|---|---|---|"]
        out += [f"| {requirement_link(fr)} | {criteria} | {note} |" for fr, criteria, note in rows]
        out.append("")
    return "\n".join(out)


def add_frontmatter(path, lines):
    """Insert frontmatter lines just before the closing ---."""
    text = path.read_text(encoding="utf-8")
    head, sep, rest = text[4:].partition("\n---\n")
    path.write_text("---\n" + head + "\n" + "\n".join(lines) + sep + rest, encoding="utf-8")


def add_item_links(path, heading, links):
    """Add a **Links:** bullet as the last bullet of the item under `heading`."""
    lines = path.read_text(encoding="utf-8").split("\n")
    at = lines.index(heading) + 1
    while at < len(lines) and not lines[at].startswith("- "):
        at += 1
    while at < len(lines) and lines[at].startswith("- "):
        at += 1
    lines.insert(at, f"- **Links:** {links}")
    path.write_text("\n".join(lines), encoding="utf-8")


def add_in_flight(path):
    text = path.read_text(encoding="utf-8")
    block = []
    for uid, name, question, owner, opened, ask_by, blocks in IN_FLIGHT:
        block += [f"### {uid} {name}", "", f"- **Question:** {question}", f"- **Owner:** {owner}", f"- **Opened:** {opened}",
                  "- **State:** open", f"- **Ask by:** {ask_by}", f"- **Blocks:** {blocks}", f"- **Notes:** {DEMO}", ""]
    marker = "\n## Risks\n"
    assert marker in text, "the unknowns page has no ## Risks heading to add the demo questions before"
    path.write_text(text.replace(marker, "\n" + "\n".join(block) + "## Risks\n", 1), encoding="utf-8")


def add_links(out):
    config = out / ".vela.yaml"
    config.write_text(config.read_text(encoding="utf-8").rstrip("\n") + "\n" + LINK_TEMPLATES, encoding="utf-8")
    for epic in sorted((out / "13-epics").glob("EPC-*.md")):
        number = int(epic.stem.split("-")[1])
        add_frontmatter(epic, [f"links: {{Jira: BOOK-{number}}}"])
    for app, title in APP_TITLES.items():
        space = title.replace(" ", "+")
        lines = [f'links: {{Confluence: "https://confluence.example.com/display/HARBOR/{space}", '
                 f'GitHub: "https://github.example.com/harborline/{app}"}}']
        if app in ICONS:
            lines.append(f"icon: {ICONS[app]}")
        add_frontmatter(out / "05-building-blocks" / f"{app}-building-blocks.md", lines)
    for (page, heading), links in ITEM_LINKS.items():
        add_item_links(out / page, heading, links)


def run(*args):
    done = subprocess.run([sys.executable, str(VELA), *args], capture_output=True, text=True, timeout=120)
    if done.returncode not in (0, 1):
        sys.exit(f"make_demo_vault.py: vela {' '.join(args)} failed:\n{done.stdout}{done.stderr}")
    return done


def main(out):
    out = pathlib.Path(out).resolve()
    if out == SOURCE.resolve() or SOURCE.resolve() in out.parents:
        sys.exit("make_demo_vault.py: the target must not be the example itself")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SOURCE, out)
    blocks = out / "05-building-blocks"
    for app, domain in DOMAINS.items():
        add_domain(blocks / f"{app}-building-blocks.md", domain)
    index = blocks / "05-building-blocks.md"
    index.write_text(index.read_text(encoding="utf-8").rstrip("\n") + "\n\n**Domains.** " + DEMO
                     + " Each app page's `domain` is a proposal: Channels (website, kiosks, call center); Booking core "
                     "(Booking, Pricing, Vessel schedule); Platform (Customer identity, Notifications); Legacy "
                     "(FERRYMASTER). The `links` on each app page, epic, outside party and third-party contract are demo "
                     "data too, all on example.com hosts.\n", encoding="utf-8")
    for stem, frs in REQUIREMENTS.items():
        add_requirements(out / "capabilities" / f"{stem}.md", frs)
    for app, rows in ALLOCATION.items():
        add_allocation(blocks / f"{app}-building-blocks.md", rows)
    (out / "04b-releases.md").write_text(releases_page(), encoding="utf-8")
    add_links(out)
    add_in_flight(out / "11-unknowns-and-risks.md")
    run("render", "--vault", str(out))
    run("handoff", "APP-booking", "--replace", "--commit", "demo", "--today", TODAY, "--vault", str(out))
    (out / VAULT_PINS).parent.mkdir(exist_ok=True)
    shutil.copyfile(DEMO_PINS, out / VAULT_PINS)
    print(f"make_demo_vault.py: wrote the demo vault at {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
