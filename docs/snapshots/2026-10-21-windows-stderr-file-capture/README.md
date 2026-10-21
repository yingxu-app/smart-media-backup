# Windows stderr file-capture snapshot

- Captured before replacing the legacy v1.0.34 redirected stderr pipe.
- Reason: Windows x64 VM upgrade/rollback step exceeded the 45-second service startup probe because waiting for the redirected pipe to close could hang after the process tree stopped.
- Restore source: `build-windows.yml.before`.
- Snapshot is diagnostic/recovery evidence; retain it with the audit record.
