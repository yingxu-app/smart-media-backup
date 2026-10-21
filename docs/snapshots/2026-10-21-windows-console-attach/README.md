# Windows console attachment snapshot

Preserves the workflow before the console workaround was adjusted.

The exact-head Windows runner showed that `AllocConsole` fails while the hosted runner already has a console code page. The next revision checks that code page instead of using `GetConsoleWindow` as a proxy, then temporarily attaches the legacy executable's standard handles to `CONOUT$` while keeping the current candidate on the runner's CP1252 pipe-backed streams.
