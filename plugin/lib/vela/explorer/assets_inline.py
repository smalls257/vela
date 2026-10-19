"""Optional generated art, inlined so the page still opens from disk.

The explorer draws everything itself: lamps, lines, strips, plants. Assets only add identity and atmosphere,
and only through the slot contract (art/slots.json): the page asks resolve.js for a slot id such as emblem.coach
or texture.cockpit and never names a file or a provider.

The slot contract, the builtin hand-drawn art and the resolver ship in art/ beside this file, and this is the only
copy: the gallery reads it from here. Provider art (ComfyUI renders) does not ship: `vela explore --assets
<assets.config.json>` reads the config and the provider's folder (<provider>/manifest.json and its files) from the
config's own folder (the gallery's prototypes/gallery/assets is one). Each slot's file is picked the way resolve.js
does (the provider's when it has one and the file exists, otherwise builtin, with the reason logged, never
silently), and the chosen files are inlined as data URIs beside resolve.js and a bundle it can read from file://.
With no --assets, the builtin provider alone is used.
"""
import base64
import json
import pathlib

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parent / "art"
MIME = {"svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "mp4": "video/mp4",
        "webm": "video/webm", "mp3": "audio/mpeg", "wav": "audio/wav"}
# The slots the explorer asks for, by prefix; the rest of the contract is not inlined, to keep the page small.
USED = ("emblem.", "emblem-on-dark.", "texture.", "loop.title-card")


class AssetError(Exception):
    pass


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AssetError(f"cannot read {path}: {exc}") from exc


def bundle(today, config_path=None):
    """{"bundle", "files", "resolver", "report"}. `today` stamps the bundle, so the date is the caller's, once."""
    root = DEFAULT_ROOT
    if not (root / "slots.json").exists() or not (root / "resolve.js").exists():
        raise AssetError(f"{root} is missing slots.json or resolve.js, so the builtin art cannot load. "
                         "Reinstall the vela plugin.")
    if config_path is None:
        provider_root = root
        config = {"provider": "builtin"}
        source = "builtin only (no --assets given)"
    else:
        config_path = pathlib.Path(config_path).resolve()
        provider_root = config_path.parent
        config = read_json(config_path)
        source = str(config_path)
    slots = read_json(root / "slots.json")
    builtin = read_json(root / "builtin" / "manifest.json")
    provider = config.get("provider", "builtin")
    chosen_manifest, provider_error = None, ""
    if provider != "builtin":
        path = provider_root / provider / "manifest.json"
        if path.exists():
            chosen_manifest = read_json(path)
        else:
            provider_error = f"{provider}/manifest.json is missing"
    files, recipes, fallbacks, kept = {}, {}, [], {}
    for slot in slots["slots"]:
        sid = slot["id"]
        used = sid.startswith(USED)
        b = builtin["slots"].get(sid)
        if b is None:
            raise AssetError(f"builtin has no entry for slot {sid}; the slot contract is broken")
        p = (chosen_manifest or {}).get("slots", {}).get(sid) if chosen_manifest else None
        why = ""
        if provider != "builtin":
            if provider_error:
                why = provider_error
            elif not p:
                why = f"{provider} has no file for this slot"
            elif not (provider_root / provider / p["file"]).exists():
                why = f"{provider}/{p['file']} is missing"
                p = None
        use, name = (p, provider) if (p and not why) else (b, "builtin")
        if why and used:
            fallbacks.append({"slot": sid, "fellBackTo": "builtin", "because": why})
        if use is p:
            kept[sid] = p
        rel = f"{name}/{use['file']}"
        path = (root if name == "builtin" else provider_root) / name / use["file"]
        if use["form"] == "recipe":
            recipes[rel] = read_json(path)
        elif used:  # resolve.js resolves every slot, so every recipe goes in; only the files the page shows are inlined
            try:
                raw = path.read_bytes()
            except OSError as exc:
                raise AssetError(f"slot {sid}: cannot read {path}: {exc}") from exc
            mime = MIME.get(use["form"], "application/octet-stream")
            files[rel] = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    providers = {"builtin": builtin}
    if provider != "builtin" and chosen_manifest is not None:
        providers[provider] = {**chosen_manifest, "slots": kept}
    try:
        resolver = (root / "resolve.js").read_text(encoding="utf-8")
    except OSError as exc:
        raise AssetError(f"cannot read resolve.js: {exc}") from exc
    payload = {"built": today, "config": {"provider": provider}, "slots": slots,
               "providers": providers, "recipes": recipes}
    size = sum(len(v) for v in files.values())
    report = {"source": source, "provider": provider, "fallbacks": fallbacks, "slots": sorted(
        s["id"] for s in slots["slots"] if s["id"].startswith(USED)), "inlinedBytes": size}
    return {"bundle": payload, "files": files, "resolver": resolver, "report": report}
