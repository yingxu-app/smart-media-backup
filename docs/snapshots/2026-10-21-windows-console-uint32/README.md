# Windows console access mask snapshot

Preserves the workflow before correcting the signed PowerShell conversion of the `GENERIC_READ | GENERIC_WRITE` value passed to Win32 `CreateFile`.

The 2026-10-21 exact-head Windows runner stopped before starting the legacy executable because PowerShell converted `0xC0000000` to a negative signed integer. The next run passes the same access mask as an explicit `UInt32` value.
