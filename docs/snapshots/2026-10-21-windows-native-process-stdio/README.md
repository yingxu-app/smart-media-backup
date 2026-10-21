# Windows native process standard-handle snapshot

- Captured before replacing `System.Diagnostics.Process.Start` for the legacy v1.0.34 process.
- Evidence: run 39551598807 no longer exposed the CP1252 traceback through its file-free console path, but v1.0.34 still did not bind the health endpoint and no console-buffer output reached the Actions log. The likely remaining issue is inherited standard handles from the .NET launcher.
- Restore source: `build-windows.yml.before`.
- Retain as diagnostic/recovery evidence.
