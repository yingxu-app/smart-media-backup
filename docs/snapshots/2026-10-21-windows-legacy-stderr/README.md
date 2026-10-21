# Pre-change snapshot: legacy service stderr diagnostics

Created after Windows run 39545905105 no longer showed a CP1252 UnicodeEncodeError, but v1.0.34 still did not answer its health endpoint when launched with stdout/stderr directed to NUL.

This snapshot preserves the workflow and current audit notes before retaining stderr diagnostics for the next root-cause check.
