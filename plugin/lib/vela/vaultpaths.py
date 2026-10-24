"""Which Markdown files of a vault are pages: the one rule the vault loader, the flow check's view of an earlier
version and the companions' page index share. Pure: it takes a vault-relative path and answers."""
from vela import privaterecord, replay, schema


def page_kind(rel):
    """"page", "other" (Markdown the vault skips, such as README.md) or "ignored" for a vault-relative path ending
    .md: the one rule vault_files and the flow check's view of an earlier version share."""
    parts = tuple(p for p in rel.split("/") if p not in ("", "."))  # as PurePosixPath reads it
    if any(p.startswith(".") for p in parts[:-1]) or replay.is_mine_file(rel) or privaterecord.is_private(rel):
        return "ignored"
    if (len(parts) == 1 and parts[0] in schema.SKIP_FILES) or parts[0] in schema.SKIP_DIRS:
        return "other"
    return "page"
