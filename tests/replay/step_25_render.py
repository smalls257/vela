"""Close section 6: `vela render` rewrites the generated blocks, so the close commit carries what render rewrote."""


def run(ctx):
    code, out = ctx.vela("render")
    ctx.outputs["render"] = out
