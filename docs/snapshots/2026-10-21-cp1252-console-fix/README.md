# CP1252 Windows console fix pre-change snapshot

Saved before changing the packaged desktop entry point and its focused regression tests.

- Branch: `codex/windows-vm-webview-acceptance`
- HEAD: `7a69c7add6654dba731a89b09304916328cc9ef5`
- Reported failure: the v1.0.34 process in the Windows x64 VM exited before health became ready when its server thread wrote localized diagnostics through CP1252.
- Purpose: retain the exact pre-fix implementation and current audit/closure docs for recovery and evidence comparison.
