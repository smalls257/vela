"""`vela close <step>`: one subcommand per close capability, each in its own module (plan section 1, God Method).

Close is not one command on purpose: porting the 5,400-word close skill into a single `vela close` would move a God
Method into a God Function. Each step module (`close_sync`, `close_stage`, `close_gate`, and later `close_finish`,
`close_push`, `close_pr`) owns its parser through `register_close(steps)` and its own test file, and none calls
another's internals. A step module whose task has not landed sets `register_close = None`; when none is ready,
`vela close` is not offered at all.
"""
import importlib

STEPS = ("close_sync", "close_stage", "close_gate", "close_reconfirm", "close_readback", "close_drafts", "close_finish", "close_push")


def ready_steps():
    found = [importlib.import_module(f"vela.commands.{name}") for name in STEPS]
    return [m.register_close for m in found if getattr(m, "register_close", None) is not None]


def register(sub):
    steps = ready_steps()
    if not steps:
        return
    close = sub.add_parser("close", help="the steps that file a session: bring in main, stage by path, check it is ready")
    each = close.add_subparsers(dest="step", required=True)
    for add in steps:
        add(each)
