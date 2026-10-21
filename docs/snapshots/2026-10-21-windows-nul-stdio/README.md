# Pre-change snapshot: legacy Windows NUL stdio launch

Created after run 39545231559 confirmed that changing the runner console output code page alone did not change v1.0.34's CP1252 stream. This preserves the pre-change workflow and audit notes before redirecting the legacy executable's output to the NUL character device while it inherits the UTF-8 console code page.

This snapshot is evidence for rollback and comparison, not a release artifact.
