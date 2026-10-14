"""Which of the vault's own files the served page may open: `Open the file`, `Open the design doc`, `Open the plan`.

Served, the page is at the helper's root, so the relative hrefs a file:// page uses (../team/docs/x.md) reach
nothing. serve.py answers /vault-file/<path> with the file, and this module decides whether a path may be answered.

What it exists to prevent is Infected Core in reverse: the rule for "what may leave this machine's disk through the
helper" lives here as one pure function of (vault folder, URL path), tested without a socket, instead of being spread
through the request handler. The answer is "inside the vault, not hidden, a regular file, and still inside after
symlinks are followed". Nothing outside the vault is ever served; a design doc or plan that lives in a team repo
beside the vault has no link when the page is served, and the page says why."""
import mimetypes
import pathlib
import urllib.parse

PREFIX = "/vault-file/"
MAX_BYTES = 20 * 1024 * 1024
# Everything else goes out as plain text: an html or svg file sent as itself would run script with the page's own origin.
IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


class Refused(Exception):
    """A request the helper will not answer. `status` is the HTTP status; the message says why, in plain words."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def resolve(vault, url_path):
    """The file inside `vault` that a /vault-file/ URL path names. Raises Refused for anything else."""
    if not url_path.startswith(PREFIX):
        raise Refused(404, f"nothing at {url_path}")
    raw = urllib.parse.urlsplit(url_path[len(PREFIX):]).path
    segments = [urllib.parse.unquote(part) for part in raw.split("/")]
    if not segments or any(not s or s in (".", "..") or "/" in s or "\\" in s or "\x00" in s for s in segments):
        raise Refused(400, "that is not a path inside the vault")
    if any(s.startswith(".") for s in segments):
        raise Refused(403, "hidden files and folders (.git, .planner, .claude) are not served")
    root = pathlib.Path(vault).resolve()
    target = (root.joinpath(*segments)).resolve()
    if root != target and root not in target.parents:
        raise Refused(403, "that file is outside the vault, so this helper will not serve it")
    if not target.is_file():
        raise Refused(404, f"no file {'/'.join(segments)} in the vault")
    if target.stat().st_size > MAX_BYTES:
        raise Refused(413, f"{'/'.join(segments)} is over {MAX_BYTES // (1024 * 1024)} MB")
    return target


def content_type(path):
    """The image type for a picture, plain text for everything else (html, svg and script included)."""
    suffix = pathlib.Path(path).suffix.lower()
    if suffix in IMAGES:
        return mimetypes.types_map.get(suffix, "application/octet-stream")
    return "text/plain; charset=utf-8"
