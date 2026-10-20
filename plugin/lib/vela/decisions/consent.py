"""Whether the record holds the lead's yes in the right form: the checks of plan 4.3, one function per row. Pure.

**A Sensor, not a Shield, and said plainly.** The model writes every field these checks read: the capture's origin,
its tag and its words. So what they prove is "the model recorded a yes in the right form", never "the lead said
yes". They make a missing or malformed yes visible before anything is filed (without them, a decision filed on
Claude's own suggestion looks exactly like one the lead gave: a Silent Fallback). The reviewer, reading the quoted
words in the PR's Consent block, is the one who judges them. A model could write a fake capture, and no code can tell.

Each check returns None or a `say.Refusal` whose `plain` is the 4.3 table's sentence, the words the lead hears:

- `exists`: the capture is in this session's record. Filing on an answer nobody wrote down leaves nothing for the
  reviewer to read.
- `from_a_person`: its origin is a person. Anything starting `claude` is Claude's, including `claude, from <name>`,
  which CONVENTIONS' captures grammar defines as Claude's summary of someone's words, not their words.
- `not_bare_non_yes`: "ok", "sure", "next" and the rest are how a lead moves a conversation along, not how they agree
  to a decision. The list is `closegate.BARE_NON_YES`, the one copy in the codebase, so the gate and apply agree.
- `after_readback`: the yes is numbered above the read-back it answers. A yes given before the final wording was read
  back agreed to something else.
- `group_small_enough`: one yes covers at most seven items. Past that the lead can't hold the read-back in mind, so the
  yes doesn't say what was agreed to.
- `why_in_their_words`: a reason is copied verbatim into the page, so it must be the lead's (a person origin).
- `from_the_lead`: a push yes is the lead's own, its origin their `vela whoami` handle. Not just any person: an
  operator's account email or a reviewer's name standing in for the lead is reported as such, and nothing is sent.
- `after_send_notice`: a push yes comes after `close push` printed what it will send; the caller passes the record's
  capture count at the notice.
- `unchanged_since_draft`: the capture's quoted words still hash to what the drafter saw. An answer edited after the
  draft may no longer say what the filled-in file assumes (plan 9.1).

The lead can go ahead without any of these (they may override any rule): each refusal's `override` names the route,
an override citing their reason, which then goes on record and into the Consent block, never hidden.
"""
from vela import closegate, say
from vela.said import is_unverified
from vela.decisions.schema import quote_hash

GROUP_LIMIT = 7  # the most items one read-back may name for one yes
OVERRIDE_YES = (f'an override of {closegate.QUOTED_YES_RULE} on the item, its reason citing the capture with the '
                "lead's words for going ahead, then vela apply again")


# A send has no override: only the lead's own yes, after they heard what goes, sends anything.
NO_PUSH_OVERRIDE = ("none for the push itself: the lead hears what is sent before it goes; tell them, then take their "
                    "yes")

# Going ahead without a quoted yes is an event override: it has a reason and no end date.
WAIVE_YES = "You can also have me go ahead without your yes on record; I'll note that you chose to."


def _refusal(rule, plain, fix, override=OVERRIDE_YES):
    waiver = WAIVE_YES if override == OVERRIDE_YES else None
    return say.Refusal(rule=rule, plain=plain, fix=fix, override=override, waiver=waiver)


def exists(ref, record):
    if record.capture(ref) is not None:
        return None
    return _refusal("consent-capture-missing", "I don't have your answer written down yet, so I haven't filed it.",
                    f"Capture the lead's answer with vela record add, then point the field at it (it named {ref!r}, "
                    "which this session's record doesn't hold).")


def from_a_person(capture):
    if capture.is_person:
        return None
    return _refusal("consent-not-a-person", "That line was mine, not yours. Does the wording I read back sound right to you?",
                    f"Ask the lead; capture their answer in their words with their handle as origin (^c{capture.n} "
                    f"has origin {capture.origin!r}).")


def same_handle(origin, handle):
    """True when a capture's origin is `handle`, written with or without its `@`, in any case (GitHub's are)."""
    return bool(handle) and origin.strip().lstrip("@").casefold() == handle.strip().lstrip("@").casefold()


def from_the_lead(capture, handle, names=()):
    """A send's yes must be the lead's own: `from_a_person` alone let an operator's account email, a name the model
    guessed, or a reviewer stand in for them (the confirm run recorded the sends in S14, S18 and S21 under an email
    address). `handle` is `vela whoami`'s; "" when it isn't known, which is refused too, since then nobody's yes can
    be checked against the lead."""
    if not handle:
        return _refusal("consent-lead-unknown", "I don't know your GitHub handle yet, so I can't tell your yes from "
                                                "anyone else's. What's the short name after the @?",
                        "Ask the lead once, run vela whoami --set <handle>, capture their yes with --origin @<handle>, "
                        "then run vela close push --consent again.", override=NO_PUSH_OVERRIDE)
    if is_unverified(capture.origin):
        return _refusal("consent-unverified", "I couldn't check that you typed that yes, so I haven't sent anything. "
                                              "Did you say yes to sending it?",
                        f"^c{capture.n} is unverified (no log of what was typed). Ask the lead; on their yes run "
                        "vela record confirm, then vela close push --consent again.", override=NO_PUSH_OVERRIDE)
    if same_handle(capture.origin, handle) or capture.origin.strip().casefold() in {n.casefold() for n in names}:
        return None  # the lead's own display name is the lead
    return _refusal("consent-not-the-lead",
                    f"That yes is written down as coming from {capture.origin}, not from you, so I haven't sent "
                    "anything. Shall I send it?",
                    f"^c{capture.n} has origin {capture.origin!r}, but the lead is @{handle} (vela whoami). Only the "
                    f"lead's own yes sends: ask them, capture their answer with --origin @{handle}, then run vela "
                    "close push --consent again.", override=NO_PUSH_OVERRIDE)


def not_bare_non_yes(capture):
    if not capture.is_bare_non_yes:
        return None
    return _refusal("consent-bare-non-yes", "You said 'ok'. Is that a yes to the wording as I read it?",
                    f"Ask once more for a plain yes to the read-back; ^c{capture.n} holds only {capture.quote!r}.")


def after_readback(yes, readback):
    if int(yes.n) > int(readback.n):
        return None
    return _refusal("consent-yes-before-readback",
                    "Your yes came before I read the final wording back, so I'll read it again.",
                    f"Read the final wording back, capture it, then capture the lead's yes after it (the yes ^c{yes.n} "
                    f"is not after the read-back ^c{readback.n}).")


def group_small_enough(count):
    if count <= GROUP_LIMIT:
        return None
    return _refusal("consent-group-too-large",
                    "That was too much for one yes. I'll read it back in smaller groups.",
                    f"Split the {count} items into read-backs of at most {GROUP_LIMIT}, each with its own yes.")


def group_sizes(items, field="readback"):
    """{read-back ref: how many items it covers}, for `group_small_enough`."""
    sizes = {}
    for item in items:
        ref = item.get(field)
        if ref:
            sizes[ref] = sizes.get(ref, 0) + 1
    return sizes


def why_in_their_words(ref, record):
    missing = exists(ref, record)
    if missing is not None:
        return missing
    capture = record.capture(ref)
    if capture.is_person:
        return None
    return _refusal("consent-why-not-theirs", "Why this one, in your words?",
                    f"Ask the lead why, in their words, and capture that (^c{capture.n} is Claude's, origin "
                    f"{capture.origin!r}).", override="leave the reason out (the item is filed with no why), or an "
                                                      "override citing the lead's words for going ahead")


def after_send_notice(yes, notice_count):
    if int(yes.n) > int(notice_count):
        return None
    return _refusal("consent-push-before-notice", "Before I send anything, I need to tell you what goes and to whom.",
                    f"Run close push without a consent to print the send notice, then capture the lead's yes after it "
                    f"(the yes ^c{yes.n} is not after capture {notice_count}).",
                    override=NO_PUSH_OVERRIDE)


def unchanged_since_draft(capture, stored_hash):
    if quote_hash(capture) == stored_hash:
        return None
    return _refusal("consent-capture-changed",
                    "The answer changed since I wrote this down, so I'll check it with you again.",
                    f"Read ^c{capture.n} back to the lead as it now stands, then draft the file again.")


def a_yes(ref, record, readback=None):
    """The first refusal of the checks a yes must pass (exists, a person, not bare, after its read-back), or None.
    A read-back named but missing from the record is refused as a missing capture."""
    missing = exists(ref, record)
    if missing is not None:
        return missing
    yes = record.capture(ref)
    found = from_a_person(yes) or not_bare_non_yes(yes)
    if found is not None or not readback:
        return found
    if record.capture(readback) is None:
        return exists(readback, record)
    return after_readback(yes, record.capture(readback))
