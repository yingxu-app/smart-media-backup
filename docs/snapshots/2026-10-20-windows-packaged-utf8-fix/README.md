# Packaged Windows E2E UTF-8 fix snapshot

Preserves the exact workflow and closure-plan state before setting UTF-8 for the packaged-server E2E subprocess. The packaged EXE service had passed its health/version check; the Python backup verifier then exited while printing Chinese to the runner's CP1252 console, before exercising packaged backup assertions.
