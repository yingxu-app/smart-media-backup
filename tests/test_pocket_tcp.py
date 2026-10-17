import json
import socket
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import quote, unquote

from smb.pocket import PocketNotesStore
from smb.pocket_tcp import PocketTcpBridge


class FakePairingManager:
    def __init__(self):
        self.authorized = set()
        self.revoked = []

    def connect(self, code):
        if code != "123456":
            return None
        token = "session-token"
        self.authorized.add(token)
        return token

    def is_authorized(self, token):
        return token in self.authorized

    def revoke(self, token):
        self.authorized.discard(token)
        self.revoked.append(token)


class PocketTcpBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pairing = FakePairingManager()
        self.notes = PocketNotesStore(Path(self.temp_dir.name) / "notes.json")
        self.bridge = PocketTcpBridge(
            pairing=self.pairing,
            status_provider=lambda: {"status": "copying", "phase_progress": 25},
            history_provider=lambda limit: [{"id": i} for i in range(limit)],
            notes_store=self.notes,
            host="127.0.0.1",
            port=0,
        )
        self.port = self.bridge.start()

    def tearDown(self):
        self.bridge.stop()
        self.temp_dir.cleanup()

    def test_pair_then_read_status_and_disconnect(self):
        paired = self.bridge.handle_message(
            {"id": 1, "command": "pair", "code": "123456"}, "192.168.1.20"
        )
        self.assertTrue(paired["ok"])
        self.assertEqual(paired["token"], "session-token")

        status = self.bridge.handle_message(
            {"id": 2, "command": "status", "token": paired["token"]}
        )
        self.assertEqual(status["data"]["status"], "copying")
        self.assertEqual(status["id"], 2)

        disconnected = self.bridge.handle_message(
            {"id": 3, "command": "disconnect", "token": paired["token"]}
        )
        self.assertTrue(disconnected["disconnected"])
        self.assertFalse(self.pairing.is_authorized(paired["token"]))

    def test_rejects_unauthorized_and_unknown_commands(self):
        unauthorized = self.bridge.handle_message(
            {"id": "a", "command": "history", "token": "bad"}
        )
        self.assertFalse(unauthorized["ok"])
        self.assertEqual(unauthorized["error"], "未配对或会话已过期")
        unknown = self.bridge.handle_message({"id": "b", "command": "backup"})
        self.assertFalse(unknown["ok"])
        self.assertEqual(unknown["error"], "不支持的操作")

    def test_limits_history_and_saves_only_note_fields(self):
        self.pairing.authorized.add("session-token")
        history = self.bridge.handle_message(
            {"command": "history", "token": "session-token", "limit": 500}
        )
        self.assertEqual(len(history["items"]), 50)
        saved = self.bridge.handle_message({
            "command": "notes.save",
            "token": "session-token",
            "data": {"event": "山景", "location": "山顶", "secret": "discard"},
        })
        self.assertEqual(saved["notes"]["event"], "山景")
        self.assertNotIn("secret", saved["notes"])

    def test_limits_failed_pairing_attempts_per_peer(self):
        for attempt in range(5):
            result = self.bridge.handle_message(
                {"command": "pair", "code": "000000"}, "192.168.1.20"
            )
            self.assertEqual(result["error"], "配对码无效或已过期")
        blocked = self.bridge.handle_message(
            {"command": "pair", "code": "123456"}, "192.168.1.20"
        )
        self.assertEqual(blocked["error"], "尝试次数过多，请稍后重试")
        other_peer = self.bridge.handle_message(
            {"command": "pair", "code": "123456"}, "192.168.1.21"
        )
        self.assertTrue(other_peer["ok"])

    def test_tcp_wire_protocol_handles_multiple_requests_and_utf8(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2) as client:
            stream = client.makefile("rwb", buffering=0)
            request = {"id": 1, "command": "pair", "code": "123456"}
            stream.write((quote(json.dumps(request), safe="") + "\n").encode("ascii"))
            first = json.loads(unquote(stream.readline().decode("ascii")))
            self.assertEqual(first["token"], "session-token")

            notes = {"event": "星空拍摄", "location": "湖边", "device": "相机", "notes": "夜景"}
            request = {
                "id": 2,
                "command": "notes.save",
                "token": first["token"],
                "data": notes,
            }
            stream.write((quote(json.dumps(request, ensure_ascii=False), safe="") + "\n").encode("ascii"))
            second = json.loads(unquote(stream.readline().decode("ascii")))
            self.assertEqual(second["notes"]["event"], "星空拍摄")
            self.assertEqual(second["id"], 2)

    def test_session_is_bound_to_socket_and_revoked_when_client_disconnects(self):
        client = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        stream = client.makefile("rwb", buffering=0)
        try:
            pair = {"id": 1, "command": "pair", "code": "123456"}
            stream.write((quote(json.dumps(pair), safe="") + "\n").encode("ascii"))
            paired = json.loads(unquote(stream.readline().decode("ascii")))
            token = paired["token"]
            self.assertTrue(self.pairing.is_authorized(token))

            other = socket.create_connection(("127.0.0.1", self.port), timeout=2)
            other_stream = other.makefile("rwb", buffering=0)
            try:
                status = {"id": 2, "command": "status", "token": token}
                other_stream.write(
                    (quote(json.dumps(status), safe="") + "\n").encode("ascii")
                )
                rejected = json.loads(unquote(other_stream.readline().decode("ascii")))
                self.assertFalse(rejected["ok"])
                self.assertEqual(rejected["error"], "未配对或会话已过期")
            finally:
                other_stream.close()
                other.close()
        finally:
            stream.close()
            client.shutdown(socket.SHUT_RDWR)
            client.close()

        deadline = time.monotonic() + 2
        while self.pairing.is_authorized(token) and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(self.pairing.is_authorized(token))


if __name__ == "__main__":
    unittest.main()
