"""Offline workflow tests. All databases and identities are synthetic and temporary."""
import io
import json
import sqlite3
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "control_center"))
from fastapi import HTTPException
from fastapi.testclient import TestClient
from shared_api import Settings, create_app, database
from api_client import APIClient, APIError, normalize_server_url

KEY = "isolated-test-administrator-key-123456789"

def fake_identity(token):
    if token == "owner-token":
        return {"id": "isolated-owner", "email": "owner@example.invalid", "name": "Test Owner"}
    if token not in ("test-token", "other-token"):
        raise HTTPException(401, "Test identity rejected")
    identity = "test-account" if token == "test-token" else "other-account"
    return {"id": identity, "email": identity + "@example.invalid", "name": identity}

class Response(io.BytesIO):
    def __init__(self, response):
        super().__init__(response.content)
        self.headers = response.headers

class SharedWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.temp.name), target_user="owner@example.invalid")
        self.app = create_app(self.settings, identity_resolver=fake_identity, graph_delivery=lambda *args: False)
        self.context = TestClient(self.app)
        self.web = self.context.__enter__()
        owner = self.web.post("/api/admin/login", headers={"Authorization": "Bearer owner-token"}).json()
        self.gui = APIClient("https://shared.example.invalid", owner["session_token"], opener=self.open_request)

    def tearDown(self):
        self.context.__exit__(None, None, None)
        self.temp.cleanup()

    def open_request(self, request, timeout):
        import urllib.parse
        parsed = urllib.parse.urlsplit(request.full_url)
        response = self.web.request(request.get_method(), parsed.path, content=request.data, headers=dict(request.header_items()))
        if response.status_code >= 400:
            raise urllib.error.HTTPError(request.full_url, response.status_code, "test error", response.headers, io.BytesIO(response.content))
        return Response(response)

    def register(self, token="test-token", **body):
        result = self.web.post("/api/auth/register", headers={"Authorization": "Bearer " + token}, json=body)
        self.assertEqual(200, result.status_code)
        return result.json()

    def auth(self, account):
        return {"Authorization": "Bearer " + account["session_token"]}

    def upload(self, account, filename="scan.pdf", aircraft="ENO", contents=b"%PDF-1.4\nsynthetic document"):
        return self.web.post("/api/scans/upload", headers=self.auth(account),
            data={"aircraft": aircraft, "operator_email": "untrusted@example.invalid"},
            files={"file": (filename, contents, "application/pdf")})

    def test_request_is_pending_and_visible_to_gui_without_any_decision(self):
        account = self.register(email="forged@example.invalid", name="untrusted")
        self.assertEqual("PENDING", account["status"])
        for _ in range(3):
            overview = self.gui.snapshot()
            self.assertEqual("test-account@example.invalid", overview["operators"][0]["email"])
            self.assertEqual("PENDING", overview["operators"][0]["status"])
        with database(self.settings) as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM approval_audit").fetchone()[0])
        self.assertEqual(403, self.upload(account).status_code)

    def test_only_authenticated_gui_action_changes_decision_and_phone_sees_it(self):
        account = self.register()
        bad = self.web.post("/api/admin/action", json={"operator_id": account["id"], "action": "APPROVE"})
        self.assertEqual(401, bad.status_code)
        self.gui.decide(account["id"], "APPROVE")  # Simulated human GUI action, isolated database only.
        status = self.web.get("/api/auth/status", headers=self.auth(account)).json()
        self.assertEqual("APPROVED", status["status"])
        self.gui.decide(account["id"], "REJECT")
        self.assertEqual("REJECTED", self.web.get("/api/auth/status", headers=self.auth(account)).json()["status"])
        self.assertEqual(403, self.upload(account).status_code)

    def test_bad_or_absent_identity_never_creates_pending_request(self):
        self.assertEqual(401, self.web.post("/api/auth/register", json={"email": "claim@example.invalid"}).status_code)
        self.assertEqual(401, self.web.post("/api/auth/register", json={}, headers={"Authorization": "Bearer bad"}).status_code)
        self.assertEqual([], self.gui.snapshot()["operators"])

    def test_duplicate_registration_does_not_create_or_approve_another_account(self):
        first = self.register()
        second = self.register()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual("PENDING", second["status"])
        self.assertEqual(1, len(self.gui.snapshot()["operators"]))

    def test_legacy_email_approval_is_preserved_as_history_not_silently_granted(self):
        with database(self.settings) as conn:
            conn.execute("CREATE TABLE operators(email TEXT, status TEXT)")
            conn.execute("INSERT INTO operators VALUES ('test-account@example.invalid','APPROVED')")
        self.assertEqual("PENDING", self.register()["status"])
        with database(self.settings) as conn:
            self.assertEqual("APPROVED", conn.execute("SELECT status FROM operators").fetchone()[0])

    def test_session_cannot_impersonate_another_approved_account(self):
        approved = self.register()
        pending = self.register("other-token")
        self.gui.decide(approved["id"], "APPROVE")
        self.assertEqual(403, self.upload(pending).status_code)

    def test_retired_email_links_cannot_approve_and_public_health_contains_no_key(self):
        account = self.register()
        response = self.web.get("/api/admin/email-action?email=test@example.invalid&action=APPROVE&token=guess")
        self.assertEqual(410, response.status_code)
        self.assertEqual(410, self.web.get("/admin").status_code)
        self.assertNotIn(KEY, self.web.get("/api/health").text)
        self.assertEqual("PENDING", self.web.get("/api/auth/status", headers=self.auth(account)).json()["status"])

    def test_durable_upload_and_duplicate_does_not_claim_onedrive_delivery(self):
        account = self.register()
        self.gui.decide(account["id"], "APPROVE")
        first = self.upload(account)
        self.assertEqual(200, first.status_code)
        self.assertTrue(first.json()["success"])
        self.assertFalse(first.json()["graph_uploaded"])
        self.assertEqual(200, self.upload(account).status_code)
        self.assertEqual(1, len(self.gui.snapshot()["scans"]))
        files = list((Path(self.temp.name) / "scans_backup").rglob("*.pdf"))
        self.assertEqual(1, len(files))
        self.assertTrue(files[0].read_bytes().startswith(b"%PDF-"))

    def test_upload_rejects_paths_and_non_pdf(self):
        account = self.register()
        self.gui.decide(account["id"], "APPROVE")
        self.assertEqual(400, self.upload(account, filename="../../bad.pdf").status_code)
        self.assertEqual(400, self.upload(account, aircraft="../../ENO").status_code)
        self.assertEqual(400, self.upload(account, contents=b"not a PDF").status_code)

    def test_pending_requests_and_instance_survive_api_restart(self):
        account = self.register()
        instance = self.gui.snapshot()["instance_id"]
        restarted = create_app(self.settings, identity_resolver=fake_identity)
        with TestClient(restarted) as web:
            self.assertEqual(instance, web.get("/api/health").json()["instance_id"])
            self.assertEqual("PENDING", web.get("/api/auth/status", headers=self.auth(account)).json()["status"])

    def test_expired_session_is_not_accepted(self):
        account = self.register()
        with database(self.settings) as conn:
            conn.execute("UPDATE operator_sessions SET expires_at=0")
        self.assertEqual(401, self.web.get("/api/auth/status", headers=self.auth(account)).status_code)

    def test_administrator_key_cannot_replace_owner_sign_in(self):
        with tempfile.TemporaryDirectory() as other:
            with TestClient(create_app(Settings(Path(other)), identity_resolver=fake_identity)) as web:
                self.assertEqual(401, web.get("/api/admin/overview", headers={"X-Admin-Key": KEY}).status_code)

    def test_owner_sign_in_does_not_approve_or_register_an_operator(self):
        self.assertEqual([], self.gui.snapshot()["operators"])
        with database(self.settings) as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM approval_audit").fetchone()[0])
        account = self.register()
        self.web.post("/api/admin/login", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual("PENDING", self.web.get("/api/auth/status", headers=self.auth(account)).json()["status"])

    def test_operator_account_cannot_authenticate_as_owner(self):
        denied = self.web.post("/api/admin/login", headers={"Authorization": "Bearer test-token"})
        self.assertEqual(403, denied.status_code)

    def test_owner_sign_out_revokes_management_session(self):
        self.gui.logout()
        with self.assertRaises(APIError) as result:
            self.gui.snapshot()
        self.assertEqual(401, result.exception.status_code)

    def test_operator_session_cannot_be_used_for_management(self):
        account = self.register()
        response = self.web.get("/api/admin/overview", headers=self.auth(account))
        self.assertEqual(401, response.status_code)

    def test_gui_rejects_temporary_tunnels_and_connection_errors(self):
        for url in ("https://random.loca.lt", "https://random.trycloudflare.com", "http://unsafe.example.invalid", "https://user:password@example.invalid"):
            with self.assertRaises(APIError):
                normalize_server_url(url)
        def offline(*args, **kwargs):
            raise OSError("offline")
        client = APIClient("https://shared.example.invalid", KEY, opener=offline)
        with self.assertRaisesRegex(APIError, "No approval decision was sent"):
            client.snapshot()

if __name__ == "__main__":
    unittest.main()

