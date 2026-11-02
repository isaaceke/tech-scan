"""Production panel + Graph HTTP client against loopback, never live Microsoft.

Synthetic sign-in skips Microsoft's identity service. This is contract evidence,
not proof of tenant consent, guest redemption, Graph behavior, or Android runtime.
"""
import json
import sys
import threading
import time
import tkinter as tk
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "control_center"))
from control_center import ControlCenter
from folder_access import GraphClient, OWNER_EMAIL

OPERATOR = "contract-operator@example.invalid"
CONFIG = {"drive_id": "contract-attair-drive", "folder_id": "contract-folder", "owner_id": "contract-owner",
          "owner_email": OWNER_EMAIL, "folder_url": "https://example.invalid/folder"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def handle_graph(self):
        service = self.server
        token = self.headers.get("Authorization", "").removeprefix("Bearer ")
        owner = token == "synthetic-owner"
        operator = token == "synthetic-operator"
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).removeprefix("/v1.0")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        service.calls.append((self.command, path, "owner" if owner else "operator" if operator else "unknown"))
        status = 200
        result = None
        if path == "/me":
            result = {"id": CONFIG["owner_id"] if owner else "contract-operator-id", "mail": OWNER_EMAIL if owner else OPERATOR}
        elif path == "/me/drive/special/approot" and owner:
            result = {"id": CONFIG["folder_id"], "folder": {}, "parentReference": {"driveId": CONFIG["drive_id"]}, "webUrl": CONFIG["folder_url"]}
        elif path.endswith("/invite") and self.command == "POST" and owner:
            request = json.loads(body)
            assert request["recipients"] == [{"email": OPERATOR}]
            assert request["roles"] == ["write"] and request["requireSignIn"] is True
            assert request["sendInvitation"] is False
            service.permission = {"id": "contract-permission", "roles": ["write"],
                                  "grantedToIdentitiesV2": [{"user": {"id": "contract-operator-id", "email": OPERATOR}}],
                                  "link": {"scope": "users"}}
            result = {"value": [service.permission]}
        elif path.endswith("/permissions/contract-permission") and self.command == "DELETE" and owner:
            service.permission = None
            result = {}
        elif not owner and (not operator or not service.permission):
            status, result = 403, {"error": {"code": "accessDenied", "message": "Synthetic individual permission is absent"}}
        elif path.endswith("/permissions"):
            result = {"value": [service.permission] if service.permission else []}
        elif self.command == "PUT" and ":/SCANNER_CONNECTION_TEST_" in path:
            name = path.split(":/", 1)[1].removesuffix(":/content")
            service.contents = body
            service.item = {"id": "contract-pdf", "name": name, "file": {}, "size": len(body),
                            "parentReference": {"driveId": CONFIG["drive_id"], "id": CONFIG["folder_id"]}}
            result = service.item
            status = 201
        elif path.endswith("/items/contract-pdf/content"):
            result = service.contents
        elif path.endswith("/items/contract-pdf"):
            result = service.item
        elif path == "/drives/contract-attair-drive/items/contract-folder":
            result = {"id": CONFIG["folder_id"], "folder": {}, "parentReference": {"driveId": CONFIG["drive_id"]}}
        else:
            status, result = 404, {"error": {"message": "Synthetic route is absent"}}
        data = result if isinstance(result, bytes) else json.dumps(result).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/pdf" if isinstance(result, bytes) else "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = handle_graph


class MemoryStore:
    def load(self): return None
    def save(self, value): self.value = value
    def clear(self): self.value = None


class SyntheticSignIn:
    token = "synthetic-owner"
    def begin(self):
        return {"user_code": "CONTRACT", "verification_uri": "https://microsoft.com/devicelogin"}
    def finish(self, challenge, cancelled):
        return {"access_token": self.token, "expires_in": 3600, "scope": getattr(self, "scope", "User.Read Files.ReadWrite")}


class GraphHttpContractTests(unittest.TestCase):
    def test_panel_approval_signin_upload_owner_readback_and_revocation_over_http(self):
        service = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        service.permission = None
        service.contents = None
        service.item = None
        service.calls = []
        thread = threading.Thread(target=service.serve_forever, daemon=True)
        thread.start()
        root = tk.Tk()
        root.withdraw()
        flow = SyntheticSignIn()
        configs = []
        graph_root = "http://127.0.0.1:" + str(service.server_port) + "/v1.0"
        gui = ControlCenter(root, client_factory=lambda token, config=None: GraphClient(token, config, graph_root=graph_root),
                            sign_in_factory=lambda: flow, session_store=MemoryStore(), browser_open=lambda url: None,
                            config_save=configs.append, confirm=lambda *args: True)

        def pump():
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                root.update()
                if not gui.busy and gui.events.empty():
                    return
                time.sleep(.01)
            self.fail("Production panel did not complete the local HTTP operation")

        try:
            gui.sign_in_button.invoke()
            pump()
            self.assertTrue(gui.connected)
            self.assertEqual(CONFIG, configs[0])
            self.assertFalse(any(method in ("POST", "PUT", "DELETE") for method, _, _ in service.calls))

            flow.token = "synthetic-operator"
            gui.test_button.invoke()
            pump()
            self.assertTrue(gui.test_result.get().startswith("DENIED:"))
            self.assertIsNone(service.permission)

            # Simulated human GUI action changes this loopback fixture only.
            gui.email.set(OPERATOR)
            gui.approve.invoke()
            pump()
            self.assertIsNotNone(service.permission)
            gui.test_button.invoke()
            pump()
            self.assertTrue(gui.test_result.get().startswith("ALLOWED:"))
            gui.upload_test_button.invoke()
            pump()
            self.assertTrue(gui.test_result.get().startswith("VERIFIED:"), gui.test_result.get())
            self.assertTrue(service.contents.startswith(b"%PDF-"))
            self.assertTrue(any(method == "PUT" and role == "operator" for method, _, role in service.calls))
            self.assertTrue(any(path.endswith("contract-pdf/content") and role == "owner" for _, path, role in service.calls))
            self.assertEqual(1, sum(method == "POST" for method, _, _ in service.calls))

            gui.operators.selection_set("contract-permission")
            gui.update_buttons()
            gui.remove.invoke()
            pump()
            self.assertIsNone(service.permission)
            gui.test_button.invoke()
            pump()
            self.assertTrue(gui.test_result.get().startswith("DENIED:"))
            self.assertEqual("disabled", str(gui.upload_test_button["state"]))
            self.assertEqual(1, sum(method == "PUT" for method, _, _ in service.calls))
        finally:
            gui.close()
            service.shutdown()
            service.server_close()
            thread.join(timeout=2)
