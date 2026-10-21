# Windows legacy console and PWA CI pre-change snapshot

Saved before updating the Windows version-transition harness and Pocket test workflow.

- Branch: `codex/windows-vm-webview-acceptance`
- Base commit: `70ee5a82070c7fcb9ab28683839d7b2ff83dcfed`
- Evidence: Windows VM run `39542648189` still failed while starting published v1.0.34 under CP1252 despite setting `PYTHONIOENCODING` and `PYTHONUTF8`; the bundled old frozen interpreter kept a CP1252 stderr stream.
- Python's Windows console documentation says `PYTHONIOENCODING` is ignored for interactive console buffers unless `PYTHONLEGACYWINDOWSSTDIO` is set. The follow-up will set that variable only for v1.0.34, then clear all Python encoding overrides from the candidate process.
- Purpose: preserve the exact pre-change CI files before correcting the old-release environment and ensuring the new candidate starts without inherited Python encoding overrides.
