"""The one error every command raises when the tool itself cannot do what was asked.

It lives apart from `cli.py` so a module that only needs to raise it does not load the whole CLI (Computational
Friction on the hook path). `cli.ToolError` is this class.
"""


class ToolError(Exception):
    """The tool failed: bad arguments, an unreadable vault, a missing catalog. Exit 2, the message printed after 'vela: '."""


class Refusal(ToolError):
    """The tool stopped on purpose and says why in words for the person (exit 1, printed as written, no "vela: " in
    front): not a fault in the tool, so not exit 2."""
