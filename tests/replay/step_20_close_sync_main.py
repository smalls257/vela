"""Close section 6: `vela close sync-main` brings in main (nothing moved here) and records that it did."""


def run(ctx):
    code, out = ctx.vela("close", "sync-main", "--today", ctx.today)
    ctx.outputs["close sync-main"] = out
