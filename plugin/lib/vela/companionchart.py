"""A flow as a colored character drawing, for the terminal pane. Pure.

The Violation this exists to prevent is a Leaky Narrative at the drawer: if the mod had to lay out lanes and cut labels it
would hold plan wording and a layout rule of its own, and the Cowork page would draw a different picture. So vela draws
the whole picture here, as lines of toned spans, at the widths the pane can have; the mod only picks the widest one
that fits. A second Violation is Forensic Coding of the arrows: today every label repeats "Sender → Receiver:" (fix E133),
so a reader scans lane names instead of what happens. The lanes are the header; the label says only what the step does.

Every line is at most `columns` terminal cells wide. Box-drawing characters and arrows are one cell; East Asian wide
characters are two, and vault text can hold them, so widths are counted by cell, never by character.
"""
import unicodedata

from vela import companionsvg

WIDTHS = (48, 60, 72, 96)  # the pane widths the mod can pick between (the contract's four drawings)
MIN_LANE, MAX_LANE = 10, 24  # why: a lane narrower than 10 cells leaves no room for a label; wider than 24 stretches arrows
OTHERS = "others"
MORE = "…"
NAME_LIMIT = 40


def clean(text):
    """The text with the characters that take no cell (marks, joiners, controls) removed, so widths add up."""
    return "".join(ch for ch in str(text) if unicodedata.category(ch) not in ("Mn", "Me", "Cf", "Cc", "Cs", "Co"))


def cell_width(ch):
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def width_of(text):
    return sum(cell_width(ch) for ch in clean(text))


def cut(text, room):
    """The text in at most `room` cells, ending in an ellipsis when it was cut."""
    text = clean(text)
    if room <= 0:
        return ""
    if width_of(text) <= room:
        return text
    kept, used = "", 0
    for ch in text:
        if used + cell_width(ch) > room - 1:
            break
        kept, used = kept + ch, used + cell_width(ch)
    return kept.rstrip() + MORE


class Canvas:
    """One row of cells; a wide character takes its cell and an empty continuation cell."""

    def __init__(self, columns):
        self.cells = [(" ", "plain")] * columns

    def clear(self, col):
        """Blank the whole character that covers `col`, so a write never leaves half of a wide one."""
        if not 0 <= col < len(self.cells):
            return
        if self.cells[col][0] == "" and col > 0:
            col -= 1
        if cell_width(self.cells[col][0] or " ") == 2 and col + 1 < len(self.cells):
            self.cells[col + 1] = (" ", "plain")
        self.cells[col] = (" ", "plain")

    def put(self, col, text, tone="plain"):
        """Write `text` from `col`; whatever does not fit before the right edge is left off. Returns the next column."""
        for ch in clean(text):
            width = cell_width(ch)
            if col < 0 or col + width > len(self.cells):
                break
            for at in range(col, col + width):
                self.clear(at)
            self.cells[col] = (ch, tone)
            if width == 2:
                self.cells[col + 1] = ("", tone)
            col += width
        return col

    def line(self):
        """The row as spans: neighbors of one tone merged, trailing blanks dropped."""
        cells = list(self.cells)
        while cells and cells[-1] == (" ", "plain"):
            cells.pop()
        spans = []
        for ch, tone in cells:
            if spans and spans[-1]["tone"] == tone:
                spans[-1]["t"] += ch
            else:
                spans.append({"t": ch, "tone": tone})
        return spans


class Lanes:
    """Where each lane's lifeline runs, and which lane a name lands in once the narrow widths fold the rest."""

    def __init__(self, names, columns):
        self.names = names
        self.size = min(MAX_LANE, columns // len(names)) if names else 0
        self.box = self.size - 1

    def center(self, lane):
        return self.names.index(lane) * self.size + self.box // 2


def ends_of(step):
    return companionsvg.label(step.get("from", ""), NAME_LIMIT), companionsvg.label(step.get("to", ""), NAME_LIMIT)


def lane_names(steps):
    """Lane names in order of first appearance, with how many messages touch each."""
    found = {}
    for step in steps:
        sender, receiver = ends_of(step)
        for name in (sender, receiver):
            if name:
                found.setdefault(name, 0)
        if sender and receiver and sender != receiver:
            found[sender] += 1
            found[receiver] += 1
    return found


def fit(steps, columns):
    """(lane names to draw, names folded into "others"): all lanes when each gets MIN_LANE cells, else the most connected
    ones (ties go to the one seen first) and one "others" lane for the rest."""
    found = lane_names(steps)
    room = max(1, columns // MIN_LANE)
    if len(found) <= room:
        return list(found), []
    ranked = sorted(found, key=lambda name: (-found[name], list(found).index(name)))
    kept = set(ranked[:room - 1])
    return [name for name in found if name in kept] + [OTHERS], [name for name in found if name not in kept]


def folded_lanes(steps, columns):
    """The names the drawing at this width shows together as one "others" lane."""
    return fit(steps[:companionsvg.MAX_STEPS], columns)[1]


def wrap(name, room):
    """The name as one or two lines of at most `room` cells, broken at spaces. A word wider than the box is cut with an
    ellipsis, and so is whatever would need a third line."""
    one = cut(name, room)
    if width_of(name) <= room:
        return [one]
    first, rest = "", name.split()
    while rest and width_of((first + " " + rest[0]).strip()) <= room:
        first = (first + " " + rest.pop(0)).strip()
    if not first:  # the first word alone is wider than the box
        return [cut(rest[0], room)] if len(rest) == 1 else [cut(rest[0], room), cut(" ".join(rest[1:]), room)]
    return [first, cut(" ".join(rest), room)] if rest else [first]


def centered(text, room):
    pad = room - width_of(text)
    return " " * (pad // 2) + text + " " * (pad - pad // 2)


def header(lanes, columns):
    """Each lane's name in a box (wrapped to two lines when a name needs it) and the box's foot, where its lifeline
    starts. Two rows when every name fits on one line, else three."""
    names = {name: wrap(name, lanes.box - 2) for name in lanes.names}
    tall = any(len(lines) > 1 for lines in names.values())
    top, low, foot = Canvas(columns), Canvas(columns), Canvas(columns)
    for number, name in enumerate(lanes.names):
        start, inner, middle = number * lanes.size, lanes.box - 2, lanes.box // 2
        lines = names[name] + [""] * (1 + tall - len(names[name]))
        fill = inner - width_of(lines[0])
        top.put(start, "\u256d" + "\u2500" * (fill // 2), "dim")
        top.put(start + 1 + fill // 2, lines[0], "strong")
        top.put(start + 1 + fill // 2 + width_of(lines[0]), "\u2500" * (fill - fill // 2) + "\u256e", "dim")
        if tall:
            low.put(start, "\u2502", "dim")
            low.put(start + 1, centered(lines[1], inner), "strong")
            low.put(start + inner + 1, "\u2502", "dim")
        foot.put(start, "\u2570" + "\u2500" * (middle - 1) + "\u252c" + "\u2500" * (lanes.box - middle - 2) + "\u256f", "dim")
    return [row.line() for row in ((top, low, foot) if tall else (top, foot))]


def lifelines(lanes, columns, before=None):
    """The lifelines, only those left of column `before` when a label or a step's words take the rest of the row."""
    row = Canvas(columns)
    for name in lanes.names:
        if before is None or lanes.center(name) < before:
            row.put(lanes.center(name), "\u2502", "dim")
    return row


def lane_of(name, kept):
    return name if name in kept else OTHERS


def arrow_row(lanes, columns, sender, receiver):
    """(label row, arrow row, the column the label starts at): the label runs from the arrow's left end to the right edge
    of the panel, so the lifelines on its row stop where it starts."""
    a, b = lanes.center(sender), lanes.center(receiver)
    left = min(a, b)
    arrow = lifelines(lanes, columns)
    if a < b:
        arrow.put(a, "\u251c" + "\u2500" * (b - a - 2) + "\u25b6", "info")
    else:
        arrow.put(b + 1, "\u25c0" + "\u2500" * (a - b - 2) + "\u2524", "info")
    return lifelines(lanes, columns, before=left), arrow, left


def drawing(steps, columns):
    """The flow as lines of {"t", "tone"} spans, each at most `columns` cells wide. At most MAX_STEPS steps are drawn,
    then a dim line saying how many more there are."""
    shown, more = steps[:companionsvg.MAX_STEPS], max(0, len(steps) - companionsvg.MAX_STEPS)
    names, folded = fit(shown, columns)
    lanes = Lanes(names, columns)
    kept = set(names) - {OTHERS}
    out = header(lanes, columns) if names else []
    current = names[0] if names else None  # the lane a step with no sender or receiver happens on: the last receiver
    for number, step in enumerate(shown):
        sender, receiver = (lane_of(end, kept) if end else "" for end in ends_of(step))
        words = companionsvg.step_words(step, 200)
        if names and number:
            out.append(lifelines(lanes, columns).line())
        if sender and receiver and sender != receiver:
            label, arrow, start = arrow_row(lanes, columns, sender, receiver)
            label.put(start, cut(f"{step.get('n', number + 1)}. {words}", columns - start), "plain")
            out += [label.line(), arrow.line()]
            current = receiver
            continue
        current = sender or current
        text = cut(f"◆ {step.get('n', number + 1)}. {words}", columns)
        start = max(0, min(lanes.center(current) if names else 0, columns - width_of(text)))
        row = lifelines(lanes, columns, before=start) if names else Canvas(columns)
        row.put(start, text, "strong")
        out.append(row.line())
    if more:
        tail = Canvas(columns)
        tail.put(0, cut(f"+ {more} more steps" if more != 1 else "+ 1 more step", columns), "dim")
        out.append(tail.line())
    return out


def flatten(lines):
    """The lines as plain text, tones dropped: what a test or a Markdown fallback shows."""
    return ["".join(span["t"] for span in line) for line in lines]
