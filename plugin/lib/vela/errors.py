"""The one error every command raises when the tool itself cannot do what was asked.

It lives apart from `cli.py` so a module that only needs to raise it does not load the whole CLI (Computational
Friction on the hook path). `cli.ToolError` is this class.
"""


class ToolError(Exception):
    """The tool failed: bad arguments, an unreadable vault, a missing catalog. Exit 2, the message printed after 'vela: '."""
