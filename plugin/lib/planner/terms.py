"""The three words Vela keeps from its own working vocabulary, each with the one-line definition readers see.

The user ruled (2026-10-14) that slice, tracer and grill stay, and that each is defined where a reader first meets
it: a sentence in CLI output and generated pages, a tooltip on the dashboard. This is the only copy of those
definitions, so the CLI, the rendered pages and the dashboard can't drift apart.
"""

TERMS = {
    "slice": "A slice is one thin piece of the product built end to end, from what the user does to what gets stored, "
             "so it can ship and be tried on its own.",
    "tracer": "The tracer is the first slice built: one journey run end to end through every app release one needs, "
              "to prove the apps fit together before the rest is built.",
    "grill": "A grill is a working session where Vela asks you questions one at a time until a part of the plan is "
             "settled.",
}


def define(term):
    """The definition of one kept term. An unknown term raises: a missing definition is a bug, not a blank."""
    return TERMS[term]
