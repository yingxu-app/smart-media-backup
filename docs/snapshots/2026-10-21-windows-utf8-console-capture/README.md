# Windows UTF-8 console capture snapshot

- Captured before switching the legacy v1.0.34 stderr stream from a file handle to the hidden UTF-8 console.
- Evidence: run 39549444458 still raised `UnicodeEncodeError` from `encodings/cp1252.py` when stderr was file-backed; packaged-service and pywebview UI E2E both passed.
- Restore source: `build-windows.yml.before`.
- Retain as diagnostic/recovery evidence.
