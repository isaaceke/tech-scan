"""A missing owner folder must never publish a replacement APK."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "control_center"))
import build_apk


class ApkBuildGuardTests(unittest.TestCase):
    def google_fixture(self, hosting="firebase-google-cloud", mode="direct"):
        from unittest.mock import MagicMock
        config = {"drive_id":"fixture-drive", "folder_id":"fixture-folder", "owner_id":"fixture-owner"}
        response = MagicMock()
        response.headers = {"Content-Type":"application/json"}
        response.read.return_value = json.dumps({"service":"enugu-scanner-relay", "storage_connected":True,
            "hosting":hosting, "delivery_mode":mode, "destination":config}).encode()
        response.__enter__.return_value = response
        return config, lambda *args, **kwargs: response

    def test_selected_google_service_requires_direct_run_address(self):
        config, opener = self.google_fixture()
        with self.assertRaisesRegex(RuntimeError, "Google Cloud Run"):
            build_apk.validate_online_service(config, {"mode":"online", "server_url":"https://fixture.web.app",
                "hosting":"firebase-google-cloud"}, opener)

    def test_google_selection_rejects_other_infrastructure(self):
        config, opener = self.google_fixture(hosting="cloudflare")
        with self.assertRaisesRegex(RuntimeError, "Google Cloud Run"):
            build_apk.validate_online_service(config, {"mode":"online", "server_url":"https://fixture.run.app",
                "hosting":"firebase-google-cloud"}, opener)

    def test_google_selection_rejects_undecided_review_workflow(self):
        config, opener = self.google_fixture(mode="pending_review")
        with self.assertRaisesRegex(RuntimeError, "direct-delivery workflow"):
            build_apk.validate_online_service(config, {"mode":"online", "server_url":"https://fixture.run.app",
                "hosting":"firebase-google-cloud"}, opener)

    def test_matching_google_service_accepts_direct_upload_address(self):
        config, opener = self.google_fixture()
        self.assertEqual("https://fixture.run.app", build_apk.validate_online_service(config,
            {"mode":"online", "server_url":"https://fixture.run.app", "hosting":"firebase-google-cloud"}, opener))

    def test_matching_free_cloudflare_service_accepts_workers_address(self):
        config, opener = self.google_fixture(hosting="cloudflare")
        self.assertEqual("https://fixture.workers.dev", build_apk.validate_online_service(config,
            {"mode":"online", "server_url":"https://fixture.workers.dev", "hosting":"cloudflare"}, opener))

    def test_free_cloudflare_selection_rejects_wrong_infrastructure(self):
        config, opener = self.google_fixture()
        with self.assertRaisesRegex(RuntimeError, "Cloudflare Workers"):
            build_apk.validate_online_service(config,
                {"mode":"online", "server_url":"https://fixture.workers.dev", "hosting":"cloudflare"}, opener)

    def test_unconfigured_host_cannot_publish_a_replacement(self):
        with self.assertRaisesRegex(RuntimeError, "hosting is not configured"):
            build_apk.validate_online_service({"drive_id":"drive"}, {"mode":"online", "server_url":""})

    def test_unconnected_service_cannot_publish_a_replacement(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.headers = {"Content-Type":"application/json"}
        response.read.return_value = json.dumps({"service":"enugu-scanner-relay", "storage_connected":False}).encode()
        response.__enter__.return_value = response
        with self.assertRaisesRegex(RuntimeError, "Sign in as owner"):
            build_apk.validate_online_service({"drive_id":"drive"}, {"mode":"online", "server_url":"https://example.invalid"}, lambda *a, **k: response)

    def test_wrong_destination_cannot_publish_a_replacement(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.headers = {"Content-Type":"application/json"}
        response.read.return_value = json.dumps({"service":"enugu-scanner-relay", "storage_connected":True, "destination":{"drive_id":"wrong"}}).encode()
        response.__enter__.return_value = response
        with self.assertRaisesRegex(RuntimeError, "different scanner folder"):
            build_apk.validate_online_service({"drive_id":"right"}, {"mode":"online", "server_url":"https://example.invalid"}, lambda *a, **k: response)

    def test_missing_folder_preserves_existing_apk_and_does_not_start_gradle(self):
        with tempfile.TemporaryDirectory(prefix="EnuguApkGuard_") as directory:
            root = Path(directory)
            config = root / "scanner_folder.json"
            config.write_text(json.dumps({"drive_id": "", "folder_id": "", "owner_id": ""}))
            existing = root / "TECHLOG SCAN.apk"
            existing.write_bytes(b"synthetic existing APK")
            with patch.object(build_apk, "CONFIG", config), patch.object(build_apk, "ROOT", root), patch.object(build_apk.subprocess, "Popen") as start:
                with self.assertRaisesRegex(RuntimeError, "connect the folder"):
                    build_apk.build_apk()
                start.assert_not_called()
                self.assertEqual(b"synthetic existing APK", existing.read_bytes())
