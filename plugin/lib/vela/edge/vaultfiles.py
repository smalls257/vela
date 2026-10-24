"""The vault's files on disk: which pages to parse, what changed since a cache was written.

`fingerprint` is what "the plan changed" means for the companions' caches: the page list with each file's
modification time and size, so a cache is never served for a plan that was edited since (Silent Fallback ruled out).
"""
import hashlib
import json

from vela import errors, untrusted, vaultpaths


def vault_files(root):
    """(pages to parse, basenames of other Markdown files) under the vault root."""
    pages, others = [], []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        kind = vaultpaths.page_kind(rel.as_posix())
        if kind == "ignored":
            continue
        if path.is_symlink():
            raise errors.ToolError(str(untrusted.link_refusal(rel.as_posix())))
        if kind == "other":
            others.append(path.stem)
            continue
        pages.append(path)
    return pages, others


def stats(root):
    """{vault-relative path: (mtime_ns, size)} for the pages vault_files returns and for .vela.yaml."""
    found = {}
    pages, _ = vault_files(root)
    config = root / ".vela.yaml"
    for path in pages + ([config] if config.is_file() else []):
        try:
            info = path.stat()
        except OSError as exc:
            raise errors.ToolError(f"Cannot read {path.relative_to(root).as_posix()}: {exc}") from exc
        found[path.relative_to(root).as_posix()] = (info.st_mtime_ns, info.st_size)
    return found


def fingerprint(root):
    """sha256 over the sorted stats: changes whenever a page is added, removed, edited or touched."""
    body = json.dumps(sorted(stats(root).items()), separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
