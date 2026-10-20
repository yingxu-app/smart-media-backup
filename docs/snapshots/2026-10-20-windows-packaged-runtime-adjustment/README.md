# Windows packaged runtime adjustment snapshot

Preserves the first packaged GUI startup probe and prior state before changing the runner check to a deterministic headless service mode. The first run kept the GUI EXE process alive but did not expose its local health endpoint; the follow-up avoids claiming GUI evidence and directly exercises the packaged service and backup routes.
