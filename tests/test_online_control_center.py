"""Unit tests for the Online Control Center GUI.
Tests run completely offline against synthetic endpoints with zero external calls.
"""
import io
import json
import sys
import time
import tkinter as tk
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "control_center"))

from online_control_center_v3 import OnlineControlCenter


class FakeHttpResponse:
    def __init__(self, data, code=200):
        self.code = code
        self.data = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else data
        self.headers = {"Content-Type": "application/json"}

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class FakeOnlineBackend:
    def __init__(self):
        self.owner_email = "isaac.eke@attair.com.ng"
        self.approved = [{"email": "tech1@example.com", "identity_id": "id-1"}]
        self.pending = [{"email": "pending_google@example.com", "name": "Google Operator", "provider": "google", "requested_at": 1700000000000}]
        self.storage_connected = True
        self.challenges = {}
        self.signed_in = False
        self.build_invocations = []
        self.browser_urls = []
        self.confirm_response = True

    def opener(self, req, timeout=30):
        url = req.full_url
        data = req.data
        body = json.loads(data.decode("utf-8")) if data else {}

        if url.endswith("/api/owner/signin/start"):
            cid = "challenge-12345"
            self.challenges[cid] = {"status": "CONNECTED", "session_token": "token-xyz-98765"}
            return FakeHttpResponse({
                "id": cid,
                "secret": "secret-abc",
                "user_code": "ABCD-1234",
                "verification_uri": "https://microsoft.com/devicelogin",
                "interval": 1,
                "expires_in": 300
            })

        if url.endswith("/api/owner/signin/poll"):
            cid = body.get("id")
            if cid in self.challenges:
                return FakeHttpResponse({
                    "status": "CONNECTED",
                    "session_token": "mock-owner-session-token-43charslong012345678"
                })
            return FakeHttpResponse({"status": "PENDING", "interval": 1}, code=202)

        if url.endswith("/api/owner/overview"):
            return FakeHttpResponse({
                "owner": {"email": self.owner_email, "id": "owner-guid"},
                "storage_connected": self.storage_connected,
                "approved_emails": self.approved,
                "pending_requests": self.pending
            })

        if url.endswith("/api/owner/emails"):
            new_email = body.get("email")
            self.approved.append({"email": new_email, "identity_id": None})
            self.pending = [p for p in self.pending if p.get("email") != new_email]
            return FakeHttpResponse({"approved": True, "email": new_email})

        if url.endswith("/api/owner/emails/remove"):
            rem_email = body.get("email")
            self.approved = [a for a in self.approved if a.get("email") != rem_email]
            return FakeHttpResponse({"removed": True})

        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b'{"error": "Not Found"}'))


class OnlineControlCenterTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.backend = FakeOnlineBackend()
        self.gui = OnlineControlCenter(
            self.root,
            base_url="https://mock-relay.example.invalid",
            opener=self.backend.opener,
            apk_builder=lambda progress: self.backend.build_invocations.append("built") or "TECHLOG SCAN.apk",
            browser_open=self.backend.browser_urls.append,
            confirm=lambda title, msg: self.backend.confirm_response
        )

    def tearDown(self):
        self.gui.close()

    def pump(self, timeout=2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.root.update()
            if not self.gui.busy and self.gui.events.empty():
                return
            time.sleep(0.02)
        self.fail("GUI background worker did not finish before deadline.")

    def test_initial_state_has_no_active_session_and_controls_disabled(self):
        self.assertIsNone(self.gui.session)
        self.assertEqual("normal", str(self.gui.signin["state"]))
        self.assertEqual("disabled", str(self.gui.approve["state"]))
        self.assertEqual("disabled", str(self.gui.refresh_button["state"]))
        self.assertEqual("disabled", str(self.gui.build_button["state"]))
        self.assertEqual("disabled", str(self.gui.approve_pending_button["state"]))
        self.assertEqual("disabled", str(self.gui.remove["state"]))

    def test_owner_signin_flow_opens_browser_and_connects(self):
        self.gui.sign_in()
        self.pump(3.0)
        self.assertIn("https://microsoft.com/devicelogin", self.backend.browser_urls)
        self.assertEqual("mock-owner-session-token-43charslong012345678", self.gui.session)
        self.assertIn("Connected as isaac.eke@attair.com.ng", self.gui.status.get())
        self.assertEqual("normal", str(self.gui.approve["state"]))
        self.assertEqual("normal", str(self.gui.refresh_button["state"]))
        self.assertEqual("normal", str(self.gui.build_button["state"]))

    def test_overview_populates_treeview_rows_and_pending_requests(self):
        self.gui.session = "mock-owner-session-token-43charslong012345678"
        self.gui.refresh()
        self.pump()
        children = self.gui.table.get_children()
        self.assertEqual(1, len(children))
        row_vals = self.gui.table.item(children[0], "values")
        self.assertEqual("tech1@example.com", row_vals[0])
        self.assertEqual("Account linked", row_vals[1])

        pending_children = self.gui.pending_table.get_children()
        self.assertEqual(1, len(pending_children))
        pending_vals = self.gui.pending_table.item(pending_children[0], "values")
        self.assertEqual("pending_google@example.com", pending_vals[0])
        self.assertEqual("Google", pending_vals[1])

    def test_approve_pending_request_moves_to_approved_table(self):
        self.gui.session = "mock-owner-session-token-43charslong012345678"
        self.gui.refresh()
        self.pump()
        pending_children = self.gui.pending_table.get_children()
        self.gui.pending_table.selection_set(pending_children[0])
        self.gui.buttons()
        self.assertEqual("normal", str(self.gui.approve_pending_button["state"]))

        self.gui.approve_pending()
        self.pump()
        self.assertEqual(0, len(self.backend.pending))
        approved_emails = [a["email"] for a in self.backend.approved]
        self.assertIn("pending_google@example.com", approved_emails)

    def test_approve_email_adds_record_and_refreshes(self):
        self.gui.session = "mock-owner-session-token-43charslong012345678"
        self.gui.email.set("newtech@example.com")
        self.gui.approve_email()
        self.pump()
        self.assertEqual("", self.gui.email.get())
        emails = [a["email"] for a in self.backend.approved]
        self.assertIn("newtech@example.com", emails)
        children = self.gui.table.get_children()
        self.assertEqual(2, len(children))

    def test_remove_email_deletes_record_when_confirmed(self):
        self.gui.session = "mock-owner-session-token-43charslong012345678"
        self.gui.refresh()
        self.pump()
        children = self.gui.table.get_children()
        self.gui.table.selection_set(children[0])
        self.gui.buttons()
        self.assertEqual("normal", str(self.gui.remove["state"]))

        self.backend.confirm_response = True
        self.gui.remove_email()
        self.pump()
        self.assertEqual(0, len(self.backend.approved))

    def test_escape_cancels_active_device_challenge(self):
        self.gui.code.set("ABCD-1234")
        self.gui.code_help.set("Enter code")
        self.gui.on_escape()
        self.assertEqual("", self.gui.code.get())
        self.assertEqual("", self.gui.code_help.get())
        self.assertIn("cancelled", self.gui.status.get().lower())

    def test_build_apk_button_triggers_builder(self):
        self.gui.session = "mock-owner-session-token-43charslong012345678"
        self.gui.build()
        self.pump()
        self.assertEqual(["built"], self.backend.build_invocations)
        self.assertIn("TECHLOG SCAN.apk", self.gui.status.get())


if __name__ == "__main__":
    unittest.main()
