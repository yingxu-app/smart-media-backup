# AI credential migration hardening snapshot

- Captured before changing the current uncommitted AI provider integration.
- `ai_namer.py.before` is the exact pre-fix source.
- Reproduction used synthetic credentials and a fake OS keyring that rejects only the `openrouter` entry; the current migration removed that key from JSON even though it was not saved in the vault.
- Intended fix: retain the legacy JSON until all supported credential entries have been migrated successfully.
