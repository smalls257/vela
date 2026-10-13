# ADR-0001: Build the Desktop agent as one Tauri process for Mac and Windows

**Status:** accepted
**Date:** 2026-10-12
**Slug:** desktop-agent

## Context
The Desktop agent runs on each person's laptop and is pushed by Intune (Windows) and Jamf (Mac); a person can only switch it on (CST-007). It must ship in the endpoint lead's 18 January 2027 packaging slot (CST-010) for the 2 February pilot (CST-009). Whether the Mac is in the first release is open in the vault as UNK-054; the team has chosen to build for both (design OQ-001). The agent needs a local encrypted store, a Microsoft Graph client and a small webview for the Note view, and an idle budget of 5 percent of one core.

## Decision
One signed per-user process built with Tauri. A Rust core owns the local store, the Graph pull and the calls to Consent and identity and the Summariser. The Tauri webview shows the Note view. One codebase ships as a signed Mac pkg (Jamf) and a Windows MSIX (Intune). The vault's three containers are modules inside the process.

## Alternatives considered
- **Native per platform (Swift on Mac, C# on Windows)**: two pipelines and two hiring profiles, and every behaviour built and tested twice.
- **Electron**: one codebase, but the team would own a bundled browser runtime on the fleet, and patch it.
- **Separate processes for core and view**: not chosen; it adds IPC across a boundary nobody asked for and splits the consent state that withdrawal must purge in one place.

## Consequences
- **Positive:** one codebase, one build pipeline and one hiring pool; a small footprint within the idle budget.
- **Negative:** a critical bug in the Rust core takes down the whole agent. The team judged two Rust engineers enough to catch these. Mitigated by failing closed and by OS relaunch after a crash, so a crash shows nothing rather than something wrong.
- **Negative (security):** the consent gate is enforced inside one address space by an unforgeable `Grant` type and the webview command allow-list. If same-user malware becomes the threat model, the readers must move to a separate process.
- **Reversibility cost:** high. The toolkit sets the packaging, the signing and the hiring. Unwinding means rewriting the core and the view per platform.
- **Open dependency:** the Mac half rests on the product owner's answer to UNK-054 (design OQ-001). The packaging of the encrypted store is a pending spike (design D-001).
