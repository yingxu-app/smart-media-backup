# Windows legacy release console snapshot

This directory preserves the workflow before the Windows runner's v1.0.34 launch was changed to use a temporary UTF-8 console.

The previous exact-head run still reproduced `UnicodeEncodeError` from CP1252 when the published frozen v1.0.34 executable started under GitHub Actions pipe-backed stdout. The next workflow run will check the old executable in an isolated console and keep the current candidate attached to the runner's CP1252 pipes.
