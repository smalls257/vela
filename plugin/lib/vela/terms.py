"""The three words Vela keeps from its own working vocabulary, each with the one-line definition readers see.

The user ruled (2026-10-14) that slice, tracer and grill stay, and that each is defined where a reader first meets
it: a sentence in CLI output and generated pages, a tooltip on the dashboard. This is the only copy of those
definitions, so the CLI, the rendered pages and the dashboard can't drift apart.
"""

TERMS = {
    "slice": "A slice is one thin piece of the product built end to end, from what the user does to what gets stored, "
             "so it can ship and be tried on its own.",
    # voice audit row 220: "every app release one needs" didn't parse, and "built" came twice
    "tracer": "The tracer is the first slice: one journey that runs through every app it touches, built first to "
              "prove the apps fit together.",
    "grill": "A grill is a working session where Vela asks you questions one at a time until a part of the plan is "
             "settled.",
}


def define(term):
    """The definition of one kept term. An unknown term raises: a missing definition is a bug, not a blank."""
    return TERMS[term]
