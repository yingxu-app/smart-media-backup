"""影序 Pocket 配对、权限边界和移动端 API 回归测试。"""
import socket
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from smb import db
from smb.pocket import PocketNotesStore, PocketPairingManager
from smb import server


class LocalAddressSelectionTests(unittest.TestCase):
    def test_prefers_wifi_address_over_vpn_and_virtual_interfaces(self):
        interfaces = {
            "utun6": [SimpleNamespace(family=socket.AF_INET, address="198.18.0.1")],
            "lo0": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
            "bridge100": [SimpleNamespace(family=socket.AF_INET, address="192.168.3.1")],
            "bridge102": [SimpleNamespace(family=socket.AF_INET, address="192.168.2.1")],
            "en0": [SimpleNamespace(family=socket.AF_INET, address="10.52.188.32")],
        }
        stats = {name: SimpleNamespace(isup=True) for name in interfaces}
        with mock.patch.object(server.psutil, "net_if_addrs", return_value=interfaces), \
             mock.patch.object(server.psutil, "net_if_stats", return_value=stats), \
             mock.patch.object(server.socket, "socket") as create_socket:
            self.assertEqual(server._local_ip(), "10.52.188.32")
        create_socket.assert_not_called()

    def test_ignores_down_wifi_and_selects_active_ethernet(self):
        interfaces = {
            "Wi-Fi": [SimpleNamespace(family=socket.AF_INET, address="192.168.10.8")],
            "Ethernet": [SimpleNamespace(family=socket.AF_INET, address="10.0.0.24")],
        }
        stats = {
            "Wi-Fi": SimpleNamespace(isup=False),
            "Ethernet": SimpleNamespace(isup=True),
        }
        with mock.patch.object(server.psutil, "net_if_addrs", return_value=interfaces), \
             mock.patch.object(server.psutil, "net_if_stats", return_value=stats):
            self.assertEqual(server._local_ip(), "10.0.0.24")


class PocketPairingTests(unittest.TestCase):
    def test_code_is_single_use_and_session_expires(self):
        manager = PocketPairingManager(code_ttl_seconds=30, session_hours=1)
        issued = manager.issue_code()
        self.assertRegex(issued["code"], r"^\d{6}$")
        self.assertIsNone(manager.connect("999999"))
        token = manager.connect(issued["code"])
        self.assertTrue(token)
        self.assertTrue(manager.is_authorized(token))
        self.assertIsNone(manager.connect(issued["code"]))
        manager._sessions[token] = time.time() - 1
        self.assertFalse(manager.is_authorized(token))


class PocketApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_db_path = db.DB_PATH
        self.old_pairing = server.pocket_pairing
        self.old_notes = server.pocket_notes
        self.old_pocket_enabled = server.config.pocket_enabled
        self.old_pocket_tcp_enabled = server.config.pocket_tcp_enabled
        self.old_tcp_bridge = server._pocket_tcp_bridge
        db.DB_PATH = self.root / "history.db"
        db.init_db()
        server.pocket_pairing = PocketPairingManager()
        server.pocket_notes = PocketNotesStore(self.root / "notes.json")
        server.config.pocket_enabled = True
        # Avoid inheriting a user's persisted opt-in LAN listener setting.
        server.config.pocket_tcp_enabled = False
        server.app.config.update(TESTING=True)
        self.client = server.app.test_client()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        server.pocket_pairing = self.old_pairing
        server.pocket_notes = self.old_notes
        server.config.pocket_enabled = self.old_pocket_enabled
        server.config.pocket_tcp_enabled = self.old_pocket_tcp_enabled
        server._pocket_tcp_bridge = self.old_tcp_bridge
        self.temp.cleanup()

    def test_lan_cannot_open_desktop_workbench(self):
        response = self.client.get("/", environ_base={"REMOTE_ADDR": "192.168.1.8"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("仅允许在本机访问", response.get_json()["error"])
        pocket = self.client.get("/pocket/", environ_base={"REMOTE_ADDR": "192.168.1.8"})
        self.assertEqual(pocket.status_code, 200)

    def test_pairing_notes_status_and_sanitized_history(self):
        issued = self.client.post("/api/pocket/pairing").get_json()
        self.assertRegex(issued["code"], r"^\d{6}$")
        connected = self.client.post(
            "/api/pocket/connect",
            json={"code": issued["code"]},
            environ_base={"REMOTE_ADDR": "192.168.1.8"},
        )
        self.assertEqual(connected.status_code, 200)

        saved = self.client.post(
            "/api/pocket/notes",
            json={"event": "上海漫展", "location": "国家会展中心", "device": "Sony A7M4", "notes": "主舞台"},
            environ_base={"REMOTE_ADDR": "192.168.1.8"},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(server.pocket_notes.load()["event"], "上海漫展")

        backup_id = db.create_backup("测试项目", "/Users/test/Secret/Desktop/Backup")
        db.finish_backup(backup_id, status="completed")
        history = self.client.get(
            "/api/pocket/history",
            environ_base={"REMOTE_ADDR": "192.168.1.8"},
        ).get_json()["items"]
        self.assertEqual(history[0]["target"], "Backup")
        self.assertNotIn("/Users/test", str(history[0]))

        status = self.client.get(
            "/api/pocket/status",
            environ_base={"REMOTE_ADDR": "192.168.1.8"},
        )
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.get_json()["paired"])

    def test_pairing_advertises_wifi_address_when_vpn_is_default_route(self):
        interfaces = {
            "utun8": [SimpleNamespace(family=socket.AF_INET, address="198.18.0.1")],
            "en0": [SimpleNamespace(family=socket.AF_INET, address="192.168.31.172")],
        }
        stats = {name: SimpleNamespace(isup=True) for name in interfaces}
        with mock.patch.object(server.psutil, "net_if_addrs", return_value=interfaces), \
             mock.patch.object(server.psutil, "net_if_stats", return_value=stats):
            issued = self.client.post("/api/pocket/pairing").get_json()
        self.assertEqual(issued["tcp_host"], "192.168.31.172")
        self.assertEqual(
            issued["url"],
            f"http://192.168.31.172:{server.config.web_port}/pocket/",
        )

    def test_invalid_code_and_unpaired_api_are_rejected(self):
        self.assertEqual(
            self.client.post("/api/pocket/connect", json={"code": "000000"}, environ_base={"REMOTE_ADDR": "192.168.1.8"}).status_code,
            401,
        )
        self.assertEqual(
            self.client.get("/api/pocket/status", environ_base={"REMOTE_ADDR": "192.168.1.8"}).status_code,
            401,
        )

    def test_desktop_can_read_phone_notes_without_mobile_cookie(self):
        server.pocket_notes.save({"event": "街拍", "location": "外滩"})
        response = self.client.get("/api/pocket/notes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["notes"]["location"], "外滩")

    def test_tcp_settings_are_loopback_only(self):
        for method in ("get", "post"):
            response = getattr(self.client, method)(
                "/api/pocket/tcp-settings",
                json={"enabled": True} if method == "post" else None,
                environ_base={"REMOTE_ADDR": "192.168.1.8"},
            )
            self.assertEqual(response.status_code, 403)
        self.assertFalse(server.config.pocket_tcp_enabled)

    def test_tcp_settings_reject_malformed_toggle_and_report_stale_listener(self):
        server.config.pocket_tcp_enabled = True
        server._pocket_tcp_bridge = None
        status = self.client.get(
            "/api/pocket/tcp-settings", environ_base={"REMOTE_ADDR": "127.0.0.1"}
        )
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.get_json()["enabled"])
        self.assertFalse(status.get_json()["running"])

        malformed = self.client.post(
            "/api/pocket/tcp-settings",
            json={"enabled": "false"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertTrue(server.config.pocket_tcp_enabled)

    def test_tcp_settings_persist_a_valid_loopback_toggle(self):
        server.config.pocket_tcp_enabled = False
        with mock.patch.object(server, "_configure_pocket_tcp") as configure, \
             mock.patch.object(server.config, "save") as save:
            response = self.client.post(
                "/api/pocket/tcp-settings",
                json={"enabled": True},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(server.config.pocket_tcp_enabled)
        configure.assert_called_once_with(True)
        save.assert_called_once_with()

    def test_tcp_settings_start_and_stop_the_listener(self):
        original_port = server.POCKET_TCP_PORT
        original_bridge_class = server.PocketTcpBridge
        server.POCKET_TCP_PORT = 0
        server._pocket_tcp_bridge = None

        def make_loopback_bridge(**kwargs):
            kwargs.update(host="127.0.0.1", port=0)
            return original_bridge_class(**kwargs)

        bridge = None
        try:
            with mock.patch.object(server, "PocketTcpBridge", side_effect=make_loopback_bridge):
                with mock.patch.object(server.config, "save"):
                    started = self.client.post(
                        "/api/pocket/tcp-settings",
                        json={"enabled": True},
                        environ_base={"REMOTE_ADDR": "127.0.0.1"},
                    )
                self.assertEqual(started.status_code, 200)
                self.assertTrue(started.get_json()["running"])
                bridge = server._pocket_tcp_bridge
                with socket.create_connection(("127.0.0.1", bridge.bound_port), timeout=2):
                    pass

                with mock.patch.object(server.config, "save"):
                    stopped = self.client.post(
                        "/api/pocket/tcp-settings",
                        json={"enabled": False},
                        environ_base={"REMOTE_ADDR": "127.0.0.1"},
                    )
                self.assertEqual(stopped.status_code, 200)
                self.assertFalse(stopped.get_json()["running"])
                self.assertFalse(bridge.running)
        finally:
            if bridge is not None and bridge.running:
                bridge.stop()
            server._pocket_tcp_bridge = None
            server.POCKET_TCP_PORT = original_port


if __name__ == "__main__":
    unittest.main()
