"""Microsoft replies are synthetic; these tests never change real permissions."""
import io
import json
import sys
import unittest
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "control_center"))
from folder_access import GraphClient, OWNER_EMAIL, normalize_email, permission_matches, test_pdf
from api_client import APIError

CONFIG = {"drive_id": "synthetic-attair-drive", "folder_id": "synthetic-app-folder", "owner_id": "owner-id", "owner_email": OWNER_EMAIL}
PROFILE = {"id": "synthetic-personal-test", "mail": "personal-test@example.invalid", "displayName": "Synthetic test account"}


class GraphReply(io.BytesIO):
    def __init__(self, value):
        super().__init__(value if isinstance(value, bytes) else json.dumps(value).encode())


class FolderAccessTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.permission = {"id": "synthetic-permission", "roles": ["write"],
            "grantedToV2": {"user": {"id": PROFILE["id"]}}, "invitation": {"email": PROFILE["mail"]}}
        self.permitted = True
        self.uploaded = None

    def opener(self, request, timeout):
        self.requests.append((request.get_method(), request.full_url, request.data))
        if "/me?" in request.full_url:
            if request.get_header("Authorization") == "Bearer synthetic-owner-token":
                return GraphReply({"id": CONFIG["owner_id"], "mail": OWNER_EMAIL})
            return GraphReply(PROFILE)
        if request.full_url.endswith("/permissions"):
            return GraphReply({"value": [self.permission] if self.permitted else []})
        if request.full_url.endswith("/invite"):
            return GraphReply({"value": [self.permission]})
        if request.get_method() == "PUT":
            self.uploaded = {"id": "synthetic-pdf", "name": urllib.parse.unquote(urllib.parse.urlsplit(request.full_url).path.split(":/", 1)[1].split(":/content")[0]),
                "file": {}, "size": len(request.data), "parentReference": {"driveId": CONFIG["drive_id"], "id": CONFIG["folder_id"]}}
            return GraphReply(self.uploaded)
        if "/items/synthetic-pdf/content" in request.full_url:
            return GraphReply(test_pdf())
        if "/items/synthetic-pdf?" in request.full_url:
            return GraphReply(self.uploaded)
        return GraphReply({"id": CONFIG["folder_id"], "folder": {}, "parentReference": {"driveId": CONFIG["drive_id"]}})

    def client(self):
        return GraphClient("synthetic-personal-token", dict(CONFIG), self.opener)

    def owner(self):
        return GraphClient("synthetic-owner-token", dict(CONFIG), self.opener)

    def test_personal_test_account_keeps_attair_destination_and_does_not_approve_itself(self):
        result = self.client().test_access()
        self.assertTrue(result["allowed"])
        self.assertEqual(PROFILE["mail"], result["email"])
        self.assertTrue(all(method == "GET" for method, _, _ in self.requests))
        self.assertTrue(any("/drives/synthetic-attair-drive/items/synthetic-app-folder" in url for _, url, _ in self.requests))
        self.assertFalse(any("/me/drive" in url for _, url, _ in self.requests))

    def test_removing_individual_permission_blocks_next_check_and_upload(self):
        client = self.client()
        self.assertTrue(client.test_access()["allowed"])
        self.permitted = False
        self.assertFalse(client.test_access()["allowed"])
        with self.assertRaises(APIError):
            client.upload_test_pdf(self.owner())
        self.assertFalse(any(method == "PUT" for method, _, _ in self.requests))

    def test_wrong_account_cannot_use_another_email_permission(self):
        wrong = {**PROFILE, "id": "wrong-id", "mail": "wrong@example.invalid"}
        self.assertFalse(permission_matches(wrong, self.permission))
        self.assertFalse(permission_matches({"mail": PROFILE["mail"]}, self.permission))

    def test_group_links_inherited_and_read_only_permissions_are_not_individual_approval(self):
        for permission in ({**self.permission, "link": {"scope": "organization"}},
                           {**self.permission, "inheritedFrom": {"id": "parent"}},
                           {**self.permission, "roles": ["read"]},
                           {**self.permission, "grantedToV2": {"group": {"id": "group"}}}):
            self.assertFalse(permission_matches(PROFILE, permission))

    def test_permission_identity_id_covers_microsoft_reply_without_email(self):
        permission = {"roles": ["write"], "grantedToV2": {"user": {"id": PROFILE["id"]}}}
        self.assertTrue(permission_matches(PROFILE, permission))

    def test_grant_sends_exact_recipient_and_requires_microsoft_sign_in(self):
        self.client().approve_email(" Personal-Test@Example.Invalid ")
        method, url, data = self.requests[-1]
        body = json.loads(data)
        self.assertEqual("POST", method)
        self.assertTrue(url.endswith("/invite"))
        self.assertEqual([{"email": PROFILE["mail"]}], body["recipients"])
        self.assertTrue(body["requireSignIn"])
        self.assertFalse(body["sendInvitation"])

    def test_connection_failure_is_not_permission_or_upload_success(self):
        def offline(*args, **kwargs):
            raise OSError("synthetic offline")
        with self.assertRaisesRegex(APIError, "not been confirmed"):
            GraphClient("synthetic", CONFIG, offline).test_access()

    def test_test_pdf_upload_goes_to_attair_folder_with_personal_token(self):
        result = self.client().upload_test_pdf(self.owner())
        uploads = [item for item in self.requests if item[0] == "PUT"]
        self.assertEqual(1, len(uploads))
        self.assertIn("/drives/synthetic-attair-drive/items/synthetic-app-folder:/SCANNER_CONNECTION_TEST_", uploads[0][1])
        self.assertTrue(uploads[0][2].startswith(b"%PDF-"))
        self.assertTrue(result["filename"].endswith(".pdf"))
        self.assertTrue(result["verified"])
        self.assertEqual(64, len(result["sha256"]))

    def test_rejected_or_partial_grant_is_not_reported_as_approved(self):
        def failed(request, timeout):
            return GraphReply({"value": [{"error": {"code": "accessDenied"}}]})
        with self.assertRaises(APIError):
            GraphClient("synthetic", CONFIG, failed).approve_email(PROFILE["mail"])

    def test_email_normalization_never_uses_substring_matching(self):
        self.assertEqual("person@example.invalid", normalize_email(" Person@Example.Invalid "))
        for value in ("person", "person@example.invalid extra", "<person@example.invalid>"):
            with self.assertRaises(APIError):
                normalize_email(value)

    def test_specific_person_link_only_matches_listed_identity(self):
        permission = {"roles": ["write"], "link": {"scope": "users"},
                      "grantedToIdentitiesV2": [{"siteUser": {"email": PROFILE["mail"]}}]}
        self.assertTrue(permission_matches(PROFILE, permission))
        self.assertFalse(permission_matches({**PROFILE, "id": "wrong", "mail": "wrong@example.invalid"}, permission))
        self.assertFalse(permission_matches(PROFILE, {**permission, "grantedToIdentitiesV2": [], "invitation": {"email": PROFILE["mail"]}}))
        for scope in ("anonymous", "organization", "existingAccess", ""):
            self.assertFalse(permission_matches(PROFILE, {**permission, "link": {"scope": scope}}))

    def test_wrong_drive_parent_size_or_name_is_not_verified(self):
        for field, value in (("parentReference", {"driveId": "wrong", "id": CONFIG["folder_id"]}),
                             ("parentReference", {"driveId": CONFIG["drive_id"], "id": "wrong"}),
                             ("name", "wrong.pdf"), ("size", 1)):
            with self.subTest(field=field, value=value):
                def wrong(request, timeout):
                    reply = self.opener(request, timeout)
                    if request.get_method() == "PUT":
                        reply.close()
                        return GraphReply({**self.uploaded, field: value})
                    return reply
                with self.assertRaisesRegex(APIError, "exact ATTAIR destination"):
                    GraphClient("synthetic-personal-token", CONFIG, wrong).upload_test_pdf(self.owner())

    def test_corrupt_owner_readback_is_not_verified(self):
        def corrupt(request, timeout):
            if request.full_url.endswith("/content") and request.get_method() == "GET":
                return GraphReply(b"X" + test_pdf()[1:])
            return self.opener(request, timeout)
        with self.assertRaisesRegex(APIError, "does not match"):
            self.client().upload_test_pdf(GraphClient("synthetic-owner-token", CONFIG, corrupt))

    def test_graph_token_is_not_forwarded_to_signed_download_url(self):
        def redirect(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 302, "Found", {"Location": "https://files.1drv.com/synthetic"}, io.BytesIO())
        downloads = []
        def download(request, timeout):
            downloads.append(request)
            return GraphReply(test_pdf())
        client = GraphClient("synthetic-owner-token", CONFIG, redirect, download_opener=download)
        self.assertEqual(test_pdf(), client.request("/drives/d/items/i/content", raw=True, max_bytes=len(test_pdf())))
        self.assertIsNone(downloads[0].get_header("Authorization"))

    def test_partial_invite_for_different_person_is_rejected(self):
        permission = {**self.permission, "invitation": {"email": "wrong@example.invalid"}}
        with self.assertRaises(APIError):
            GraphClient("synthetic", CONFIG, lambda *args, **kwargs: GraphReply({"value": [permission]})).approve_email(PROFILE["mail"])

    def test_microsoft_guid_casing_does_not_reject_the_same_identity(self):
        permission = {"roles": ["write"], "grantedToV2": {"user": {"id": "42F177F1-22C0-4BE3-900D-4507125C5C20"}}}
        self.assertTrue(permission_matches({**PROFILE, "id": "42f177f1-22c0-4be3-900d-4507125c5c20"}, permission))

    def test_expired_or_malformed_permission_is_not_approval(self):
        for timestamp in ("2000-01-01T00:00:00Z", "not-a-date"):
            self.assertFalse(permission_matches(PROFILE, {**self.permission, "expirationDateTime": timestamp}))
        self.assertTrue(permission_matches(PROFILE, {**self.permission, "expirationDateTime": "2999-01-01T00:00:00Z"}))


if __name__ == "__main__":
    unittest.main()
