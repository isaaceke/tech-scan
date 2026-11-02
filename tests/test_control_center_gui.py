"""The panel tests use a fake Microsoft service and never modify real users."""
import sys
import time
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "control_center"))
from control_center import ControlCenter
from api_client import APIError

class FakeStore:
    def load(self): return None
    def save(self, data): self.saved = data
    def clear(self): self.saved = None

class FakeSignIn:
    token = "owner"
    def begin(self):
        return {"user_code": "TEST-CODE", "verification_uri": "https://microsoft.com/devicelogin"}
    def finish(self, challenge, cancelled):
        return {"access_token": self.token, "expires_in": 3600, "scope": getattr(self, "scope", "User.Read Files.ReadWrite")}

class FakeMicrosoft:
    def __init__(self):
        self.grants = []
        self.removals = []
        self.items = []
        self.offline = False

class FakeClient:
    def __init__(self, backend, token, config=None):
        self.backend = backend
        self.access_token = token() if callable(token) else token
        self.config = config or {"drive_id": "test-drive", "folder_id": "test-folder", "owner_id": "test-owner", "folder_url": "https://example.invalid/folder"}
    def connect_owner(self):
        if self.access_token != "owner":
            raise APIError("Not the owner", 403)
        return {"profile": {"id": "test-owner", "email": "owner@example.invalid"}, "config": self.config}
    def permissions(self):
        if self.backend.offline:
            raise APIError("Microsoft offline")
        return list(self.backend.items)
    def approve_email(self, email):
        self.backend.grants.append(email)
        item = {"id": "synthetic-permission", "invitation": {"email": email}, "roles": ["write"]}
        self.backend.items = [item]
        return {"email": email, "permissions": [item]}
    def remove_access(self, permission_id):
        self.backend.removals.append(permission_id)
        self.backend.items = []
        return {}
    def test_access(self):
        email = self.access_token + "@example.invalid"
        allowed = any(item["invitation"]["email"] == email for item in self.backend.items)
        return {"email": email, "allowed": allowed, "message": "Synthetic Microsoft test"}
    def upload_test_pdf(self, owner):
        if self.backend.offline:
            raise APIError("Synthetic owner read-back failed")
        return {"email": self.access_token + "@example.invalid", "filename": "synthetic-test.pdf", "verified": True, "sha256": "a" * 64}

class ControlCenterTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.backend = FakeMicrosoft()
        self.flow = FakeSignIn()
        self.saved_configs = []
        self.opened_urls = []
        self.builds = []
        self.gui = ControlCenter(self.root,
            client_factory=lambda token, config=None: FakeClient(self.backend, token, config),
            sign_in_factory=lambda: self.flow, session_store=FakeStore(),
            browser_open=self.opened_urls.append, config_save=self.saved_configs.append,
            apk_builder=lambda progress: self.builds.append(True) or "synthetic.apk", confirm=lambda *args: True)
    def tearDown(self):
        self.gui.close()
    def pump(self):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            self.root.update()
            if not self.gui.busy and self.gui.events.empty(): return
            time.sleep(0.01)
        self.fail("Panel worker did not complete")
    def sign_in(self):
        self.gui.sign_in_button.invoke()
        self.pump()
    def test_owner_sign_in_loads_folder_without_approving_any_email(self):
        self.sign_in()
        self.assertTrue(self.gui.connected)
        self.assertEqual([], self.backend.grants)
        self.assertEqual(1, len(self.saved_configs))
    def test_only_approve_button_sends_entered_email(self):
        self.sign_in()
        self.gui.email.set("synthetic@example.invalid")
        self.gui.approve.invoke()
        self.pump()
        self.assertEqual(["synthetic@example.invalid"], self.backend.grants)
        self.assertEqual("", self.gui.email.get())
    def test_real_sign_in_test_shows_denied_without_granting_it(self):
        self.sign_in()
        self.flow.token = "not-approved"
        self.gui.test_button.invoke()
        self.pump()
        self.assertIn("DENIED: not-approved@example.invalid", self.gui.test_result.get())
        self.assertEqual([], self.backend.grants)
        self.assertEqual("disabled", str(self.gui.upload_test_button["state"]))
    def test_approved_sign_in_test_shows_allowed_without_new_grant(self):
        self.sign_in()
        self.backend.items = [{"id": "synthetic-permission", "invitation": {"email": "approved@example.invalid"}, "roles": ["write"]}]
        self.flow.token = "approved"
        self.gui.test_button.invoke()
        self.pump()
        self.assertIn("ALLOWED: approved@example.invalid", self.gui.test_result.get())
        self.assertEqual([], self.backend.grants)
    def test_panel_has_email_entry_and_no_backend_or_key_fields(self):
        self.assertTrue(hasattr(self.gui, "email_entry"))
        self.assertFalse(hasattr(self.gui, "admin_key"))
        self.assertFalse(hasattr(self.gui, "server"))
    def test_sign_out_disables_approval_and_upload(self):
        self.sign_in()
        self.gui.sign_out()
        self.gui.email.set("synthetic@example.invalid")
        self.gui.approve_email()
        self.assertEqual([], self.backend.grants)
        self.assertEqual("disabled", str(self.gui.approve["state"]))
    def test_cancelled_owner_login_cannot_use_previous_connection(self):
        self.sign_in()
        self.gui.authenticate()
        self.gui.cancel_sign_in()
        self.gui.approve_email()
        self.assertFalse(self.gui.connected)
        self.assertEqual([], self.backend.grants)
    def test_build_is_only_called_by_build_button(self):
        self.sign_in()
        self.gui.refresh()
        self.pump()
        self.assertEqual([], self.builds)
        self.gui.build_button.invoke()
        self.pump()
        self.assertEqual([True], self.builds)
    def test_wrong_owner_account_does_not_enable_approval(self):
        self.flow.token = "not-owner"
        self.gui.sign_in_button.invoke()
        self.pump()
        self.assertFalse(self.gui.connected)
        self.assertEqual([], self.saved_configs)
        self.assertEqual("disabled", str(self.gui.approve["state"]))

    def test_verification_failure_is_visible_and_does_not_claim_success(self):
        self.sign_in()
        self.backend.items = [{"invitation": {"email": "approved@example.invalid"}}]
        self.flow.token = "approved"
        self.gui.test_button.invoke()
        self.pump()
        self.backend.offline = True
        self.gui.upload_test_button.invoke()
        self.pump()
        self.assertTrue(self.gui.test_result.get().startswith("NOT VERIFIED:"))
        self.assertEqual([], self.backend.grants)

    def test_only_owner_readback_evidence_shows_verified(self):
        self.sign_in()
        self.backend.items = [{"invitation": {"email": "approved@example.invalid"}}]
        self.flow.token = "approved"
        self.gui.test_button.invoke()
        self.pump()
        self.gui.upload_test_button.invoke()
        self.pump()
        self.assertTrue(self.gui.test_result.get().startswith("VERIFIED:"))
        self.assertIn("a" * 64, self.gui.test_result.get())
        self.assertEqual([], self.backend.grants)

if __name__ == "__main__":
    unittest.main()
