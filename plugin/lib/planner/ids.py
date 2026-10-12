"""The next free item ID, worked out from every ID anyone has used.

Anchor: an ID is a promise that other pages and other open branches can link to it. Handing out a number an open branch
already holds breaks that promise (two UNK-026 in one vault), so the count covers every place a number can live, and
a gap is never filled.
"""
import re

PREFIX_RE = re.compile(r"^[A-Z]{2,4}$")
MIN_WIDTH = 3


def used_numbers(prefix, texts):
    """The numbers written as <prefix>-<digits> anywhere in these texts, and the widest run of digits seen."""
    found = re.compile(rf"(?<![A-Za-z0-9-]){prefix}-(\d+)(?!\d)")
    numbers = set()
    widest = MIN_WIDTH
    for text in texts:
        for match in found.finditer(text):
            numbers.add(int(match.group(1)))
            widest = max(widest, len(match.group(1)))
    return numbers, widest


def next_id(prefix, texts):
    """<prefix>-<n>, n one above the highest number used in texts, zero-padded to the widest width seen (at least 3)."""
    if not PREFIX_RE.match(prefix):
        raise ValueError(f"'{prefix}' is not an ID prefix: use 2 to 4 capital letters, such as UNK.")
    numbers, width = used_numbers(prefix, texts)
    return f"{prefix}-{(max(numbers) + 1 if numbers else 1):0{width}d}"
