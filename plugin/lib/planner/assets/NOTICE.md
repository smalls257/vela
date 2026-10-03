# Vendored libraries

The offline viewer inlines these two files, so it needs no network. Both are MIT licensed; the licence travels with each project.

| File | Project | Version | Source | SHA-256 |
|---|---|---|---|---|
| `marked.min.js` | marked, Christopher Jeffrey and contributors, https://github.com/markedjs/marked | 12.0.2 | https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js | `15fabce5b65898b32b03f5ed25e9f891a729ad4c0d6d877110a7744aa847a894` |
| `mermaid.min.js` | mermaid, Knut Sveidqvist and contributors, https://github.com/mermaid-js/mermaid | 10.9.1 | https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js | `61b335a46df05a7ce1c98378f60e5f3e77a7fb608a1056997e8a649304a936d6` |

To upgrade, download the new file, update this table and `ASSET_SHA256` in `tests/test_viewer.py`, and open the viewer once with the network off.
