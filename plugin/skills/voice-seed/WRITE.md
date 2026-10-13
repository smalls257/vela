# Writing the examples and checking them

Read by voice-seed in sections 4 and 6. One write path for an owner's passage: frontmatter, the exact text, a compare, and a final count.

## Write the examples (section 4)

Write each passage to `<folder>/<type>/VX-<type>-NNN.md`, where the folder is `voice/examples` or `voice/local`. NNN is one higher than the highest number for that type in both folders, retired files included, in three digits. Write a file in three moves.

First, write the frontmatter with the Write tool. End it with the closing `---` and one blank line. Write `from` in single-quoted YAML, and double any `'` inside it:

````
---
id: VX-<type>-NNN
voice_type: <type>
source: owner
author: "@<handle>"
from: '<where it comes from>'
state: active
added: <today>
---

````

Second, append the pasted text exactly as given, with a quoted heredoc so nothing expands:

```
cat >> <file> <<'PLANNER_EOF'
<the passage, exactly as pasted>
PLANNER_EOF
```

If the passage contains a line `PLANNER_EOF`, pick another delimiter and use it in both places.

Third, compare the stored body with the pasted text, with a tool. Write the pasted text to a temp file with a second quoted heredoc. Extract the stored body, which is everything after the closing frontmatter `---` line and its one blank line. Compare the two with `cmp`:

```
tmp=$(mktemp)
cat > "$tmp" <<'PLANNER_EOF'
<the passage, exactly as pasted>
PLANNER_EOF
awk 'body { if (first && $0 == "") { first = 0; next } first = 0; print; next } $0 == "---" && ++n == 2 { body = 1; first = 1 }' <file> | cmp - "$tmp"; code=$?; rm -f "$tmp"; (exit $code)
```

Run the whole block in one call: the shell keeps no variable between calls, so `$tmp` exists only inside it. If `cmp` reports a difference, stop. Tell the owner and do not repair the file. A heredoc always ends its text with a newline, so a paste that had no final newline gains one in both files, and `cmp` will not show it. When the paste had none, tell the owner. The check proves the file holds what the heredoc received. It does not prove the chat text reached the heredoc unchanged. Store an accepted passage as it was pasted.

Then re-read the frontmatter and confirm it parses as YAML and that `from` is the text the owner gave.

## Final check (section 6)

Re-read every file you wrote or changed. Confirm each frontmatter parses, then run this from the vault root. It prints a count per type and exits 1 if a type has more than 5 active examples or a file does not parse:

```
python3 - <<'PLANNER_EOF'
import glob, sys, yaml
active, bad = {}, []
for path in glob.glob("voice/examples/*/*.md") + glob.glob("voice/local/*/*.md"):
    try:
        meta = yaml.safe_load(open(path, encoding="utf-8").read().split("---\n", 2)[1])
        if meta["state"] == "active":
            active[meta["voice_type"]] = active.get(meta["voice_type"], 0) + 1
    except Exception as err:
        bad.append(f"{path}: {err}")
print(active, bad)
sys.exit(1 if bad or any(n > 5 for n in active.values()) else 0)
PLANNER_EOF
```

If it fails, say what failed and stop.
