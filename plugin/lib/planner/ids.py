"""The next free item ID, worked out from every ID anyone has used.

Anchor: an ID is a promise that other pages and other open branches can link to it. Handing out a number an open branch
already holds breaks that promise (two UNK-026 in one vault), so the count covers every place a number can live, and
a gap is never filled.
"""
import re

PREFIX_RE = re.compile(r"^[A-Z]{1,4}$")
MIN_WIDTH = 3
# The digits a prefix's ID pattern needs at least (schema.PAGE_ID_RE, ITEM_ID_RE): ADR-0001, R-01, PTY-01, SV-01.
MIN_WIDTHS = {"ADR": 4, "R": 2, "PTY": 2, "SV": 2}


def used_numbers(prefix, texts):
    """The numbers written as <prefix>-<digits> anywhere in these texts, and the widest run of digits seen."""
    found = re.compile(rf"(?<![A-Za-z0-9-]){prefix}-(\d+)(?!\d)")
    numbers = set()
    widest = MIN_WIDTHS.get(prefix, MIN_WIDTH)
    for text in texts:
        for match in found.finditer(text):
            numbers.add(int(match.group(1)))
            widest = max(widest, len(match.group(1)))
    return numbers, widest


def next_id(prefix, texts):
    """<prefix>-<n>, n one above the highest number used in texts, zero-padded to the widest width seen (at least the prefix's own: 3, 4 for ADR, 2 for R, PTY and SV)."""
    if not PREFIX_RE.match(prefix):
        raise ValueError(f"'{prefix}' is not an ID prefix: use 1 to 4 capital letters, such as UNK or R.")
    numbers, width = used_numbers(prefix, texts)
    return f"{prefix}-{(max(numbers) + 1 if numbers else 1):0{width}d}"
