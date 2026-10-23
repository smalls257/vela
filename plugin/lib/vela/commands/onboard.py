"""`vela onboard`: the one source of truth for getting someone up to speed, read by the /vela:onboard skill and by the
dashboard's onboarding mode alike.

    vela onboard show [--role R]            the standard path for a role: stage, parts, minutes, what each says
    vela onboard modules                    every module's name and what it is for (the names the lead types, too)
    vela onboard check                      mistakes on the lead's onboarding page, if there is one
    vela onboard path set --role R --modules "A, B" [--depth D] [--diagrams yes|no] [--bring-back "X"]
    vela onboard path show | clear          a person's own path (choices only), under their handle
    vela onboard build                      rebuild the person's own page from their path

The Violation this shape prevents is a Leaky Narrative at the skill: the skill never sees a module id or a file
format, only names. The dashboard and this command read `explorer.onboard_data.extract`, so a path the skill sets is
exactly the path the page shows. A person's path is choices only (`onboardpath`), written under `.vela/onboard/`,
never committed and never published; the page built from it goes beside it, because the shared dashboard.html is
committed and must not carry one person's path.

Exit codes: 0 done; 1 refused (a name that is no module, a module the lead hid, a role that is not one); 2 the tool
failed (a file couldn't be written, the build failed); 3 the person's handle is unknown (ask once, then `vela whoami --set`).
"""
import argparse
import difflib
import io
import pathlib

from vela import commands, onboardpath, onboardtune, onboarding, say
from vela.commands import whoami
from vela.edge import sessiongit

NAME = "onboard"
ROLE_WORDS = onboarding.ROLE_WORDS


def register(sub):
    top = sub.add_parser("onboard", help="get someone up to speed: the standard path for a role, and a person's own path")
    verbs = top.add_subparsers(dest="onboard_command", metavar="{show,modules,check,path,build}")
    verbs.required = True
    show = verbs.add_parser("show", help="the standard path for a role at the project's stage")
    show.add_argument("--role", default="", help="lead, exec, product, qa, eng or mgr (default: the lead's record for you, else your choice, else your path's, else exec)")
    common(show, cmd_show)
    common(verbs.add_parser("modules", help="every module's name and what it is for"), cmd_modules)
    common(verbs.add_parser("check", help="mistakes on the lead's onboarding page"), cmd_check)
    build = verbs.add_parser("build", help="rebuild your own page from your path")
    build.add_argument("--handle", default="", help="whose path (default: the handle vela whoami keeps)")
    common(build, cmd_build)
    path = verbs.add_parser("path", help="your own path: choices only, kept under your handle")
    acts = path.add_subparsers(dest="path_command", metavar="{set,show,clear}")
    acts.required = True
    setter = acts.add_parser("set", help="write your path and rebuild your page")
    setter.add_argument("--role", required=True, help="lead, exec, product, qa, eng or mgr")
    setter.add_argument("--modules", required=True, help="module names in the order you want them, comma separated")
    setter.add_argument("--depth", default="normal", help="how much each part shows: " + ", ".join(onboardpath.DEPTHS))
    setter.add_argument("--diagrams", default="no", help="yes shows the real items as diagrams, no as cards")
    setter.add_argument("--bring-back", default="", help="module names the lead hid that you asked for, comma separated")
    setter.add_argument("--handle", default="", help="whose path (default: the handle vela whoami keeps)")
    common(setter, cmd_path_set)
    for verb, func in (("show", cmd_path_show), ("clear", cmd_path_clear)):
        one = acts.add_parser(verb, help=f"{verb} your path")
        one.add_argument("--handle", default="", help="whose path (default: the handle vela whoami keeps)")
        common(one, func)


def common(parser, func):
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    parser.add_argument("--today", help="the date due windows count from, YYYY-MM-DD (default: system date)")
    say.add_output_flags(parser)
    parser.set_defaults(func=func)


# --------------------------------------------------------------------------- reading the plan

def load(args):
    """(root, today, vault, D.onboard): the plan as the page will show it. Builds nothing and writes nothing."""
    from vela import cli
    from vela.explorer import build, onboard_data
    root = pathlib.Path(args.vault).resolve()
    today, _ = cli.parse_today(args.today)
    vault = cli.load_vault(root)
    try:
        data = build.extract(vault, root, today)
    except onboard_data.OnboardError as exc:
        raise cli.ToolError(str(exc)) from exc
    return root, today, vault, data["onboard"]


def resolver_for(vault):
    return say.Resolver(vault)


def refuse(rule, plain, fix, audience=say.MODEL, recommend=""):
    return say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(rule, plain, fix, audience=audience, recommend=recommend)])


def role_of(word, default):
    if not word:
        return default, None
    found = ROLE_WORDS.get(word.strip().casefold())
    if found is None:
        return None, refuse("onboard-role", f"'{word}' isn't a role.", "use one of: " + ", ".join(onboarding.AUDIENCES))
    return found, None


def ids_of(names_csv):
    """(ids, refusal or None) for a comma-separated list of module names."""
    ids = []
    for name in [n.strip() for n in names_csv.split(",") if n.strip()]:
        module = onboarding.BY_NAME.get(name.casefold())
        if module is None:
            near = difflib.get_close_matches(name.casefold(), list(onboarding.BY_NAME), n=1, cutoff=0.6)
            hint = f" Did you mean '{onboarding.NAMES[onboarding.BY_NAME[near[0]]]}'?" if near else ""
            return [], refuse("onboard-module", f"'{name}' isn't a module.{hint}", "run vela onboard modules for the names")
        ids.append(module)
    return ids, None


def effective_role(root, onboard):
    """(role, source): the lead's record for this person, else their own choice, else their own path's role, else exec
    with source "none", which tells the skill to ask once."""
    handle = sessiongit.read_handle(root)
    if not onboardpath.HANDLE.match(handle):
        handle = ""  # a file under .vela/ that holds something else is no handle; it must not name a path to read
    role, source = onboarding.role_for(onboard["roles"].get(handle, ""), whoami.read_role(root))
    if role:
        return role, source
    try:
        path, _ = onboardpath.from_text(handle, (root / onboardpath.file_for(handle)).read_text(encoding="utf-8")) if handle else (None, [])
    except (OSError, UnicodeDecodeError):
        path = None
    return (path.audience, "path") if path else ("exec", "none")


def handle_of(args, root):
    """(handle, Result or None): --handle, else whoami's. A Result means stop and return it (exit 3 asks the lead once)."""
    if args.handle:
        handle = args.handle.lstrip("@")
        if not onboardpath.HANDLE.match(handle):
            return "", refuse("onboard-handle", f"'{args.handle}' isn't a handle: letters, digits and hyphens, up to 39.", "pass the name after the @ on their GitHub profile")
        return handle, None
    found = whoami.find_handle(root)
    return (found.data["handle"], None) if found.exit == say.DONE else ("", found)


def line_for(module, minutes=True):
    mark = f" (about {module['minutes']} min)" if minutes else ""
    text = f"{module['title']}{mark}: {module['gist']}"
    return say.Line(text, plain=text)


# --------------------------------------------------------------------------- show, modules, check

def cmd_show(args, out):
    root, today, vault, onboard = load(args)
    default, source = ("exec", "said") if args.role else effective_role(root, onboard)
    audience, bad = role_of(args.role, default)
    if bad:
        return commands.emit(bad, args, out)
    path = onboard["paths"][audience]
    modules = [onboard["modules"][k] for k in path["modules"]]
    total = sum(m["minutes"] for m in modules)
    label = onboarding.AUDIENCE_LABELS[audience]
    answer = f"This project is at the {onboard['stage']} stage. The {label} path is {len(modules)} parts, about {total} minutes."
    lines = [line_for(m) for m in modules]
    if path["note"]:
        lines.insert(0, say.Line(f"The lead's note for {label}: {path['note']}", plain=f"The lead's note for {label}: {path['note']}"))
    data = {"stage": onboard["stage"], "role": audience, "roleSource": source, "note": path["note"], "hidden": path["hidden"], "minutes": total,
            "modules": [{"name": m["name"], "title": m["title"], "gist": m["gist"], "minutes": m["minutes"], "items": len(m["items"]),
                         "diagram": bool(m["items"]), "notRecorded": bool(m["notRecorded"])} for m in modules]}
    return commands.emit(say.Result(NAME, lines=lines, data=data, answer=answer), args, out, resolver_for(vault))


def cmd_modules(args, out):
    from vela import onboardmodules
    lines, rows = [], []
    for module in onboarding.MODULE_IDS:
        title, lede = onboardmodules.TITLES[module]
        who = [a for a in onboarding.AUDIENCES if module in onboarding.CORE or any(module in ids for ids in onboarding.SPECIFICS[a].values())]
        rows.append({"name": onboarding.NAMES[module], "lede": lede, "roles": who})
        lines.append(say.Line(f"{onboarding.NAMES[module]}: {lede}", plain=f"{onboarding.NAMES[module]}: {lede}"))
    return commands.emit(say.Result(NAME, lines=lines, data={"modules": rows},
                                    answer=f"There are {len(rows)} modules; the first five are the same for everyone."), args, out)


def cmd_check(args, out):
    root, today, vault, onboard = load(args)
    problems = [p for p in onboard["problems"] if p.startswith("The onboarding page")]
    lines = [say.Line(p, plain=p) for p in problems]
    answer = "The onboarding page reads cleanly." if not problems else f"The onboarding page has {len(problems)} thing{'s' if len(problems) != 1 else ''} to fix."
    return commands.emit(say.Result(NAME, exit=say.REFUSED if problems else say.DONE, lines=lines, data={"problems": problems}, answer=answer),
                         args, out, resolver_for(vault))


# --------------------------------------------------------------------------- a person's own path

def rebuild(root, handle, args):
    """Build the person's page from their path file. (file, error text): error is "" when it worked."""
    from vela import cli
    target = root / onboardpath.page_for(handle)
    ns = argparse.Namespace(vault=str(root), out=str(target), today=args.today, theme="console", design=[], breakdown=[], assets=None,
                            selftest=False, serve=False, port=None, model="haiku", no_open=True, person=handle)
    printed = io.StringIO()
    try:
        code = cli.cmd_explore(ns, printed)
    except cli.ToolError as exc:
        return "", str(exc)
    return (target.relative_to(root).as_posix(), "") if code == 0 else ("", printed.getvalue().strip() or "the build failed")


def cmd_path_set(args, out):
    root, today, vault, onboard = load(args)
    handle, stop = handle_of(args, root)
    if stop:
        return commands.emit(stop, args, out)
    audience, bad = role_of(args.role, "")
    if bad:
        return commands.emit(bad, args, out)
    modules, bad = ids_of(args.modules)
    asked, bad2 = ids_of(args.bring_back)
    if bad or bad2:
        return commands.emit(bad or bad2, args, out)
    stage = onboard["stage"]
    tuning = onboardtune.parse((root / onboardtune.FILE).read_text(encoding="utf-8")) if (root / onboardtune.FILE).is_file() else onboardtune.EMPTY
    hidden = onboarding.hidden_ids(audience, stage, tuning.for_audience(audience))
    left = [m for m in modules if m in hidden and m not in asked]
    if left:
        names = ", ".join(onboarding.NAMES[m] for m in left)
        return commands.emit(refuse("onboard-hidden", f"The lead hid {names} for this role.", f"re-run with --bring-back \"{names}\" if the person asks for it",
                                    audience=say.LEAD, recommend="I'd leave it out, but it's yours to ask for and I'll note that you did."), args, out, resolver_for(vault))
    if args.diagrams not in ("yes", "no"):
        return commands.emit(refuse("onboard-diagrams", f"'{args.diagrams}' isn't yes or no.", "pass --diagrams yes or --diagrams no"), args, out)
    path, problems = onboardpath.make(handle, audience, modules, args.depth, args.diagrams == "yes", hidden, asked)
    if path is None:
        return commands.emit(refuse("onboard-path", " ".join(problems), "fix the choices and run it again"), args, out)
    try:
        wrote = sessiongit.write_text(root, onboardpath.file_for(handle), onboardpath.to_text(path))
    except OSError as exc:
        return commands.emit(say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"couldn't write the path: {exc}", plain="I couldn't save your path on this machine.")]), args, out)
    file, error = rebuild(root, handle, args)
    if error:
        return commands.emit(say.Result(NAME, exit=say.FAILED, wrote=[wrote], lines=[say.Line(f"the page was not built: {error}", plain="I saved your path but couldn't rebuild your page.")]),
                             args, out, resolver_for(vault))
    names = ", ".join(onboarding.NAMES[m] for m in path.modules)
    return commands.emit(say.Result(NAME, wrote=[wrote, file], data={"handle": handle, "file": file, "path": onboardpath.as_data(path)},
                                    lines=[say.Line(f"Your path: {names}.", plain=f"Your path: {names}.")], answer="Your path is saved and your page is rebuilt."),
                         args, out, resolver_for(vault))


def read_own(root, handle):
    """(Path or None, Result or None): the person's path, or the refusal that says there isn't one."""
    file = root / onboardpath.file_for(handle)
    try:
        text = file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, say.Result(NAME, lines=[say.Line("no personal path yet", plain="You have no path of your own yet, so the standard path for your role is what the page shows.")],
                                data={"path": None})
    except (OSError, UnicodeDecodeError) as exc:
        return None, say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"can't read the path: {exc}", plain="I couldn't read your saved path.")])
    path, problems = onboardpath.from_text(handle, text)
    if path is None:
        return None, say.Result(NAME, exit=say.FAILED, lines=[say.Line("the path file is not usable: " + "; ".join(problems), plain="Your saved path isn't usable, so the standard path is shown. Setting it again replaces it.")])
    return path, None


def cmd_path_show(args, out):
    root = pathlib.Path(args.vault).resolve()
    handle, stop = handle_of(args, root)
    if stop:
        return commands.emit(stop, args, out)
    path, result = read_own(root, handle)
    if result:
        return commands.emit(result, args, out)
    names = ", ".join(onboarding.NAMES[m] for m in path.modules)
    text = f"Your path for {onboarding.AUDIENCE_LABELS[path.audience]}: {names}. Depth: {path.depth}. Diagrams: {'yes' if path.diagrams else 'no'}."
    return commands.emit(say.Result(NAME, lines=[say.Line(text, plain=text)], data={"path": onboardpath.as_data(path)}), args, out)


def cmd_path_clear(args, out):
    root = pathlib.Path(args.vault).resolve()
    handle, stop = handle_of(args, root)
    if stop:
        return commands.emit(stop, args, out)
    gone = []
    for rel in (onboardpath.file_for(handle), onboardpath.page_for(handle)):
        if not (root / rel).exists():
            continue
        try:
            (root / rel).unlink()
            gone.append(rel)
        except OSError as exc:
            return commands.emit(say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"couldn't remove {rel}: {exc}", plain="I couldn't clear your path.")]), args, out)
    text = "Your own path is cleared; the standard path is what the page shows." if gone else "You had no path of your own to clear."
    return commands.emit(say.Result(NAME, wrote=gone, lines=[say.Line(text, plain=text)], data={"cleared": bool(gone)}), args, out)


def cmd_build(args, out):
    root = pathlib.Path(args.vault).resolve()
    handle, stop = handle_of(args, root)
    if stop:
        return commands.emit(stop, args, out)
    path, result = read_own(root, handle)
    if result:
        return commands.emit(result, args, out)
    file, error = rebuild(root, handle, args)
    if error:
        return commands.emit(say.Result(NAME, exit=say.FAILED, lines=[say.Line(f"the page was not built: {error}", plain="I couldn't rebuild your page.")]), args, out)
    return commands.emit(say.Result(NAME, wrote=[file], data={"handle": handle, "file": file}, answer="Your page is rebuilt."), args, out)
