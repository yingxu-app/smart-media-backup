# Windows legacy stderr diagnostic snapshot

Preserves the workflow before adding an error stream capture for the published v1.0.34 executable.

On the exact-head Windows x64 runner, the legacy app no longer showed a CP1252 exception in the Actions log after stdout was attached to the UTF-8 console, but `/api/health` still timed out. The next run routes only legacy stderr to a captured PowerShell stream so startup errors are visible; candidate stdout/stderr continue through the runner pipes.
