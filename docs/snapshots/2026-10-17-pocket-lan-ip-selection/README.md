# Pocket LAN address selection snapshot

Saved before correcting `_local_ip()`. The current Mac routes UDP probes to `192.0.2.1` over `utun8`, so the old selector returns the VPN address `198.18.0.1` while Wi-Fi is `192.168.31.172`. Restore the paired source/test copies if the change needs rollback.
