"""American spelling for vault prose: the British forms planner warns on (W372), and the word to write instead.

Pure: a line of text in, the British words in it out. The house voice writes American English, so a page that says
"colour" beside one that says "color" reads as two authors, and a search for one misses the other. A spelling never
breaks a check, so without this list nothing would notice the prose drift back.

The list is the one the toolkit's own move to American spelling used, so a page is held to the same words the toolkit
was. Left out on purpose: CSS color keywords and the toolkit's own old identifiers (`darkslategrey`, `callcentre`,
`harbourline`), which are not words a page writes; and "towards", which American writers use as well as "toward".
A capitalized word inside a sentence is read as a name ("Ministry of Defence", "Harbour Energy") and keeps its spelling.
"""
import re

BRITISH_TO_AMERICAN = {
    "acknowledgement": "acknowledgment", "acknowledgements": "acknowledgments", "aluminium": "aluminum",
    "analogue": "analog", "analyse": "analyze", "analyser": "analyzer", "anodised": "anodized",
    "artefact": "artifact", "artefacts": "artifacts", "authorisation": "authorization", "authorise": "authorize",
    "authorised": "authorized", "authorises": "authorizes", "barycentre": "barycenter", "behaviour": "behavior",
    "behaviours": "behaviors", "bevelled": "beveled", "cancelled": "canceled", "cancelling": "canceling",
    "canonicalised": "canonicalized", "capitalisation": "capitalization", "capitalised": "capitalized",
    "catalogue": "catalog", "catalogues": "catalogs", "centre": "center", "centred": "centered",
    "centreline": "centerline", "centres": "centers", "characterisation": "characterization", "colour": "color",
    "coloured": "colored", "colours": "colors", "criticises": "criticizes", "crystallise": "crystallize",
    "defence": "defense", "dialling": "dialing", "ellipsised": "ellipsized", "enrol": "enroll",
    "enrolment": "enrollment", "enrols": "enrolls", "favour": "favor", "favoured": "favored", "favours": "favors",
    "fibres": "fibers", "finalised": "finalized", "focussing": "focusing", "fulfilment": "fulfillment",
    "generalise": "generalize", "grey": "gray", "greys": "grays", "greyscale": "grayscale", "harbour": "harbor",
    "homogenisation": "homogenization", "honour": "honor", "honoured": "honored", "honouring": "honoring",
    "honours": "honors", "humanisers": "humanizers", "humanising": "humanizing", "initialise": "initialize",
    "initialised": "initialized", "italicise": "italicize", "judgement": "judgment", "judgements": "judgments",
    "labelled": "labeled", "labeller": "labeler", "labellers": "labelers", "labelling": "labeling", "labour": "labor",
    "levelled": "leveled", "levelling": "leveling", "licence": "license", "licences": "licenses",
    "memorisation": "memorization", "memorised": "memorized", "memorisers": "memorizers", "memorises": "memorizes",
    "metre": "meter", "mislabelled": "mislabeled", "misspelt": "misspelled", "mitres": "miters",
    "modelled": "modeled", "modelling": "modeling", "neighbour": "neighbor", "neighbourhood": "neighborhood",
    "neighbourhoods": "neighborhoods", "neighbouring": "neighboring", "neighbours": "neighbors",
    "neutralise": "neutralize", "neutralising": "neutralizing", "nominalisations": "nominalizations",
    "normalisation": "normalization", "normalise": "normalize", "normalised": "normalized",
    "normalises": "normalizes", "normalising": "normalizing", "notarisation": "notarization", "notarise": "notarize",
    "notarised": "notarized", "optimisation": "optimization", "optimise": "optimize", "optimised": "optimized",
    "optimises": "optimizes", "optimising": "optimizing", "organisation": "organization",
    "organisational": "organizational", "organisations": "organizations", "organise": "organize",
    "organised": "organized", "organiser": "organizer", "organisers": "organizers", "parameterised": "parameterized",
    "penalise": "penalize", "penalises": "penalizes", "personalisation": "personalization",
    "personalised": "personalized", "personalising": "personalizing", "practise": "practice",
    "practised": "practiced", "practises": "practices", "practising": "practicing",
    "prioritisation": "prioritization", "prioritise": "prioritize", "programme": "program",
    "publicised": "publicized", "quantised": "quantized", "randomised": "randomized", "realised": "realized",
    "recognise": "recognize", "recognised": "recognized", "recognises": "recognizes", "relabelled": "relabeled",
    "reorganisation": "reorganization", "reorganising": "reorganizing", "revolutionised": "revolutionized",
    "rumour": "rumor", "rumours": "rumors", "sanitisation": "sanitization", "sanitise": "sanitize",
    "sanitised": "sanitized", "sanitiser": "sanitizer", "signalling": "signaling", "specialisation": "specialization",
    "spelt": "spelled", "stabilised": "stabilized", "summarisation": "summarization", "summarise": "summarize",
    "summarised": "summarized", "summariser": "summarizer", "summarises": "summarizes", "summarising": "summarizing",
    "synthesised": "synthesized", "theatre": "theater", "tokenise": "tokenize", "tokenising": "tokenizing",
    "traveller": "traveler", "travelling": "traveling", "trialled": "trialed", "trialling": "trialing",
    "unlabelled": "unlabeled", "visualisation": "visualization", "visualisations": "visualizations",
    "visualise": "visualize",
}

WORD = re.compile(r"[A-Za-z]+")
OPENS_SENTENCE = re.compile(r"(?:^|[.!?:;\"“(\[])$")


def _is_name(text, found):
    """A capitalized word that does not open a sentence, or one in capitals, is a name such as "Ministry of Defence"."""
    word = found.group(0)
    if word.islower():
        return False
    if word.isupper():
        return True
    return not OPENS_SENTENCE.search(text[:found.start()].rstrip(" \t-*_>#"))


def british_words(text):
    """(British word as written, American word) for each mapped British spelling in `text`, in order. Matching
    ignores case, and the American word starts with a capital when the written one does."""
    out = []
    for found in WORD.finditer(text):
        american = BRITISH_TO_AMERICAN.get(found.group(0).lower())
        if american is None or _is_name(text, found):
            continue
        written = found.group(0)
        out.append((written, american.capitalize() if written[0].isupper() else american))
    return out
