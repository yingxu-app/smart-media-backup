import base64
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PIL import Image

from smb import ai_namer as ai_namer_module
from smb import server as server_module


class FakeKeyring:
    def __init__(self, fail_for=()):
        self.values = {}
        self.fail_for = set(fail_for)

    def set_password(self, service, username, password):
        if username in self.fail_for:
            raise RuntimeError("simulated credential vault failure")
        self.values[(service, username)] = password

    def get_password(self, service, username):
        return self.values.get((service, username))


class AINamerCredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp.name)
        self.settings_path = self.config_dir / "ai_settings.json"
        self.keyring = FakeKeyring()
        self.constants = mock.patch.multiple(
            ai_namer_module,
            CONFIG_DIR=self.config_dir,
            AI_SETTINGS_PATH=self.settings_path,
        )
        self.constants.start()
        self.keyring_patch = mock.patch.object(
            ai_namer_module.AINamer, "_keyring", return_value=self.keyring
        )
        self.keyring_patch.start()

    def tearDown(self):
        self.keyring_patch.stop()
        self.constants.stop()
        self.temp.cleanup()

    def test_save_keeps_api_key_in_vault_and_reload_restores_provider_key(self):
        namer = ai_namer_module.AINamer()
        namer.cloud_provider = "qwen"
        namer.openai_key = "synthetic-qwen-key"
        namer.backend = "openai"
        namer.save()

        saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.assertNotIn("openai_key", saved)
        self.assertNotIn("synthetic-qwen-key", self.settings_path.read_text(encoding="utf-8"))
        self.assertEqual(
            self.keyring.get_password(ai_namer_module.AI_KEYRING_SERVICE, "qwen"),
            "synthetic-qwen-key",
        )

        restored = ai_namer_module.AINamer()
        self.assertEqual(restored.cloud_provider, "qwen")
        self.assertEqual(restored.openai_key, "synthetic-qwen-key")

    def test_partial_legacy_key_migration_preserves_unmigrated_plaintext(self):
        self.settings_path.write_text(json.dumps({
            "backend": "openai",
            "cloud_provider": "qwen",
            "openai_key": "synthetic-custom-key",
            "cloud_keys": {
                "qwen": "synthetic-qwen-key",
                "openrouter": "synthetic-router-key",
            },
            "openai_model": "test-model",
            "openai_base": "https://example.invalid/v1",
        }), encoding="utf-8")
        self.keyring.fail_for.add("openrouter")

        ai_namer_module.AINamer()

        saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["cloud_keys"]["openrouter"], "synthetic-router-key")
        self.assertEqual(
            self.keyring.get_password(ai_namer_module.AI_KEYRING_SERVICE, "qwen"),
            "synthetic-qwen-key",
        )
        self.assertIsNone(
            self.keyring.get_password(ai_namer_module.AI_KEYRING_SERVICE, "openrouter")
        )

    def test_legacy_custom_key_is_not_reassigned_to_qwen(self):
        self.settings_path.write_text(json.dumps({
            "backend": "openai",
            "openai_key": "synthetic-legacy-custom-key",
            "openai_model": "old-custom-model",
            "openai_base": "https://custom.example/v1",
        }), encoding="utf-8")

        namer = ai_namer_module.AINamer()

        self.assertEqual(namer.cloud_provider, "qwen")
        self.assertEqual(namer.openai_model, ai_namer_module.CLOUD_PROVIDER_PRESETS["qwen"]["model"])
        self.assertEqual(namer.openai_key, "")
        self.assertEqual(
            self.keyring.get_password(ai_namer_module.AI_KEYRING_SERVICE, "custom"),
            "synthetic-legacy-custom-key",
        )
        self.assertIsNone(
            self.keyring.get_password(ai_namer_module.AI_KEYRING_SERVICE, "qwen")
        )

    def test_provider_keys_remain_separate_when_switching_services(self):
        namer = ai_namer_module.AINamer()
        namer.cloud_provider = "qwen"
        namer.openai_key = "synthetic-qwen-key"
        namer.save()

        namer.cloud_provider = "deepseek"
        namer.openai_key = "synthetic-deepseek-key"
        namer.save()

        namer.use_cloud_provider("qwen")
        self.assertEqual(namer.openai_key, "synthetic-qwen-key")
        namer.use_cloud_provider("deepseek")
        self.assertEqual(namer.openai_key, "synthetic-deepseek-key")

    def test_provider_switch_uses_fixed_service_endpoint_and_model(self):
        namer = ai_namer_module.AINamer()
        for provider, preset in ai_namer_module.CLOUD_PROVIDER_PRESETS.items():
            with self.subTest(provider=provider):
                namer.use_cloud_provider(provider)
                self.assertEqual(namer.openai_base, preset["base_url"])
                self.assertEqual(namer.openai_model, preset["model"])
        with self.assertRaises(ValueError):
            namer.use_cloud_provider("custom")

    def test_cloud_connection_probe_sends_only_generated_one_pixel_image(self):
        captured = {}

        class FakeClient:
            def __init__(self, *, api_key, base_url):
                captured["api_key"] = api_key
                captured["base_url"] = base_url
                self.chat = SimpleNamespace(
                    completions=SimpleNamespace(create=self.create_completion)
                )

            @staticmethod
            def create_completion(**kwargs):
                captured["request"] = kwargs
                return SimpleNamespace(choices=[SimpleNamespace(
                    message=SimpleNamespace(content="OK")
                )])

        fake_openai = types.ModuleType("openai")
        fake_openai.OpenAI = FakeClient
        namer = ai_namer_module.AINamer()
        namer.openai_key = "synthetic-never-sent-key"
        namer.openai_model = "vision-test"
        namer.openai_base = "https://example.invalid/v1"

        with mock.patch.dict(sys.modules, {"openai": fake_openai}):
            namer.test_cloud_vision()

        self.assertEqual(captured["api_key"], "synthetic-never-sent-key")
        self.assertEqual(captured["base_url"], "https://example.invalid/v1")
        image_url = captured["request"]["messages"][0]["content"][1]["image_url"]["url"]
        image_bytes = base64.b64decode(image_url.split(",", 1)[1])
        with Image.open(io.BytesIO(image_bytes)) as image:
            self.assertEqual(image.size, (1, 1))
            self.assertEqual(image.getpixel((0, 0)), (0, 0, 0))


class AINamerAPIAccessTests(unittest.TestCase):
    def test_ai_settings_and_cloud_probe_reject_non_loopback_requests(self):
        client = server_module.app.test_client()
        for path in ("/api/ai/settings", "/api/ai/test"):
            with self.subTest(path=path):
                response = client.post(
                    path,
                    json={"openai_key": "synthetic-never-sent-key"},
                    environ_base={"REMOTE_ADDR": "192.168.31.20"},
                )
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("synthetic-never-sent-key", response.get_data(as_text=True))

    def test_ai_settings_only_accept_supported_providers_and_ignore_custom_url(self):
        namer = ai_namer_module.AINamer()
        namer.backend = "disabled"
        with mock.patch.object(namer, "save"):
            with mock.patch.object(ai_namer_module, "ai_namer", namer):
                client = server_module.app.test_client()
                rejected = client.post("/api/ai/settings", json={
                    "backend": "openai",
                    "cloud_provider": "custom",
                })
                self.assertEqual(rejected.status_code, 400)
                self.assertEqual(namer.backend, "disabled")

                accepted = client.post("/api/ai/settings", json={
                    "backend": "openai",
                    "cloud_provider": "qwen",
                    "openai_model": "qwen3-vl-flash",
                    "openai_base": "https://attacker.example/collect",
                })
                self.assertEqual(accepted.status_code, 200)
                self.assertEqual(
                    namer.openai_base,
                    ai_namer_module.CLOUD_PROVIDER_PRESETS["qwen"]["base_url"],
                )


if __name__ == "__main__":
    unittest.main()
