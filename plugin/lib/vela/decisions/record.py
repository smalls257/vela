"""The open session record a decision file is applied against, and its captures (overhaul Task 4). Pure.

The consent checks read only what the record holds, so this is the one place a decision kind gets it from: the open
stub is found by `vela.sessions` (the rules for which record is open live there, not here), `edge/sessiongit.open_record`
reads the private notes behind it, and the captures are
parsed by `vela.closegate.captures`, the same parser the close gate judges with, so `apply` and the gate can never
disagree about what a capture says. Numbering new captures is `vela record add`'s work, not this module's.

`path` is the private file's path; `stub` is the committed header beside it. No disk, git or clock here.
"""
import re
from dataclasses import dataclass

from vela import closegate, privaterecord

_REF = re.compile(r"^\^?c?(\d+)$")


@dataclass(frozen=True)
class OpenRecord:
    id: str
    path: str  # relative to the vault root
    text: str
    captures: dict  # {int number: closegate.Capture}
    part: int = 1  # which part of the session's notes this machine holds (privaterecord)

    @property
    def stub(self):
        """The committed header whose lists and status follow this record's notes."""
        return privaterecord.stub_path(self.id)

    def capture(self, ref):
        """The capture `ref` names (`^c31`, `c31`, `31`, `^c07`), or None when the record holds no such capture."""
        number = number_of(ref)
        return self.captures.get(number) if number is not None else None

    @property
    def count(self):
        return len(self.captures)


def number_of(ref):
    found = _REF.match(str(ref or "").strip())
    return int(found.group(1)) if found else None


def from_text(record_id, path, text, part=1):
    return OpenRecord(record_id, path, text, {int(n): c for n, c in closegate.captures(text).items()}, part)


@dataclass(frozen=True)
class Opened:
    """Why no single record was chosen: none open (`records` empty) or several (the lead picks)."""
    records: list
    problems: list

    @property
    def several(self):
        return len(self.records) > 1
