import datetime
# ruleid: no-second-boolean-parameter
def render(vault, today, strict=False, quiet=False):
    return vault
# ok: no-second-boolean-parameter
def render_one(vault, today, mode="check"):
    return vault

def parse_today(value):
    # ok: cli-reads-clock-once
    return datetime.date.today().isoformat()

def cmd_health(args):
    # ruleid: cli-reads-clock-once
    today = datetime.date.today().isoformat()
