import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "control_center"))
from owner_sign_in import AUTHORITY, RESOURCE_TENANT, MicrosoftOwnerSignIn, MicrosoftTokenSession
from api_client import APIError

class Cancelled:
    def __init__(self, value=False):
        self.value = value
        self.intervals = []
    def wait(self, interval):
        self.intervals.append(interval)
        return self.value
    def is_set(self):
        return self.value

class OwnerSignInTests(unittest.TestCase):
    challenge = {"device_code": "isolated-device", "user_code": "TEST-CODE",
                 "verification_uri": "https://microsoft.com/devicelogin", "expires_in": 60, "interval": 5}
    def test_pending_and_slow_down_are_handled_until_microsoft_confirms(self):
        replies = iter([{"error": "authorization_pending"}, {"error": "slow_down"}, {"access_token": "synthetic"}])
        flow = MicrosoftOwnerSignIn(post=lambda endpoint, fields: next(replies), clock=lambda: 0)
        cancellation = Cancelled()
        self.assertEqual({"access_token": "synthetic"}, flow.finish(self.challenge, cancellation))
        self.assertEqual([5, 5, 10], cancellation.intervals)
    def test_cancellation_stops_token_exchange(self):
        def unexpected(*args):
            self.fail("Token endpoint was called after cancellation")
        flow = MicrosoftOwnerSignIn(post=unexpected, clock=lambda: 0)
        with self.assertRaisesRegex(APIError, "cancelled"):
            flow.finish(self.challenge, Cancelled(True))
    def test_declined_authentication_never_issues_session(self):
        flow = MicrosoftOwnerSignIn(post=lambda *args: {"error": "authorization_declined"}, clock=lambda: 0)
        with self.assertRaisesRegex(APIError, "declined"):
            flow.finish(self.challenge, Cancelled())
    def test_actual_tenant_consent_denial_stops_polling_without_a_session(self):
        calls = []
        def denied(endpoint, fields):
            calls.append(endpoint)
            return {"error": "access_denied", "error_description":
                    "AADSTS90094: An administrator has set a policy that prevents you from granting the permissions."}
        flow = MicrosoftOwnerSignIn(post=denied, clock=lambda: 0)
        with self.assertRaisesRegex(APIError, "ATTAIR administrator approval") as failure:
            flow.finish(self.challenge, Cancelled())
        self.assertEqual(["token"], calls)
        self.assertIn("AADSTS90094", str(failure.exception))
        self.assertNotIn("retry", str(failure.exception).lower())
    def test_begin_uses_existing_public_client_and_profile_scope_only(self):
        calls = []
        def post(endpoint, fields):
            calls.append((endpoint, fields))
            return self.challenge
        flow = MicrosoftOwnerSignIn(post=post)
        self.assertEqual(self.challenge, flow.begin())
        self.assertEqual("User.Read Files.ReadWrite offline_access", calls[0][1]["scope"])
    def test_unexpected_login_site_is_rejected(self):
        flow = MicrosoftOwnerSignIn(post=lambda *args: {**self.challenge, "verification_uri": "https://untrusted.example.invalid"})
        with self.assertRaisesRegex(APIError, "unexpected"):
            flow.begin()

class TokenSessionTests(unittest.TestCase):
    def test_resource_tenant_is_pinned(self):
        self.assertIn(RESOURCE_TENANT, AUTHORITY)
        self.assertNotIn("/common/", AUTHORITY)
        with self.assertRaises(APIError):
            MicrosoftTokenSession({"access_token": "old-common-token"})

    def test_expiry_comes_from_microsoft_and_is_not_extended_on_restore(self):
        session = MicrosoftTokenSession.from_result({"access_token": "synthetic", "expires_in": 90,
            "scope": "User.Read Files.ReadWrite", "refresh_token": "synthetic-refresh"}, clock=lambda: 100)
        self.assertEqual(190, session.snapshot()["expires_at"])
        restored = MicrosoftTokenSession(session.snapshot(), clock=lambda: 110)
        self.assertEqual(190, restored.snapshot()["expires_at"])
        self.assertEqual("synthetic", restored())

    def test_refresh_rotates_tokens_and_preserves_existing_consent(self):
        calls = []
        def post(endpoint, fields):
            calls.append(fields)
            return {"access_token": "new-synthetic", "refresh_token": "new-refresh", "expires_in": 3600}
        session = MicrosoftTokenSession.from_result({"access_token": "old", "refresh_token": "old-refresh", "expires_in": 30,
            "scope": "User.Read Files.ReadWrite"}, clock=lambda: 100, post=post)
        self.assertEqual("new-synthetic", session())
        self.assertEqual("new-refresh", session.snapshot()["refresh_token"])
        self.assertEqual("User.Read Files.ReadWrite", session.snapshot()["scope"])
        self.assertNotIn("scope", calls[0])
        self.assertEqual(3700, session.snapshot()["expires_at"])

    def test_expired_or_invalid_metadata_never_returns_session(self):
        for result in ({"access_token": "x"}, {"access_token": "x", "expires_in": 0}, {"access_token": "", "expires_in": 3600}):
            with self.assertRaises(APIError):
                MicrosoftTokenSession.from_result(result)
        session = MicrosoftTokenSession.from_result({"access_token": "x", "expires_in": 1}, clock=lambda: 0)
        with self.assertRaises(APIError):
            session()

    def test_refresh_rejection_never_becomes_access(self):
        session = MicrosoftTokenSession.from_result({"access_token": "x", "expires_in": 1, "refresh_token": "r"},
            clock=lambda: 0, post=lambda *args: {"error": "invalid_grant", "error_description": "Synthetic revoked session"})
        with self.assertRaisesRegex(APIError, "revoked"):
            session()
