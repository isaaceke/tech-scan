"""The GUI is a client of the shared API, never a second approval database."""
import json
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_SERVER_URL = "https://enugu-air-scanner.onrender.com"

class APIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

def normalize_server_url(value):
    value = value.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise APIError("Enter the shared server's HTTPS address.")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise APIError("The shared server must use HTTPS.")
    if parsed.hostname.endswith(".loca.lt") or parsed.hostname.endswith(".trycloudflare.com"):
        raise APIError("Use a permanent server address, not a temporary tunnel.")
    return value

class APIClient:
    def __init__(self, base_url, owner_session=None, opener=urllib.request.urlopen):
        self.base_url = normalize_server_url(base_url)
        self.owner_session = owner_session
        self.opener = opener

    def request(self, path, payload=None, bearer=None):
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Accept": "application/json"}
        authorization = bearer or self.owner_session
        if authorization:
            headers["Authorization"] = "Bearer " + authorization
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers)
        try:
            with self.opener(request, timeout=8) as response:
                if "application/json" not in response.headers.get("Content-Type", ""):
                    raise APIError("This address did not return the scanner API. Check the server deployment.")
                return json.load(response)
        except urllib.error.HTTPError as error:
            try:
                detail = json.load(error).get("detail", "Server rejected the request.")
            except (ValueError, AttributeError):
                detail = "Shared server unavailable. Check the API deployment."
            finally:
                error.close()
            raise APIError(str(detail), error.code) from None
        except (OSError, ValueError):
            raise APIError("Cannot reach the shared server. No approval decision was sent.") from None

    def snapshot(self):
        result = self.request("/api/admin/overview")
        if result.get("service") != "enugu-air-scanner" or result.get("approval_mode") != "HUMAN_GUI":
            raise APIError("This server is running the old infrastructure. Deploy API version 3.")
        return result

    def health(self):
        result = self.request("/api/health")
        if result.get("service") != "enugu-air-scanner" or not result.get("owner_sign_in"):
            raise APIError("Scanner service setup is incomplete. The owner sign-in service must be activated.")
        return result

    def login_owner(self, microsoft_access_token):
        result = self.request("/api/admin/login", {}, bearer=microsoft_access_token)
        if result.get("role") != "OWNER" or not result.get("session_token"):
            raise APIError("The service did not confirm the owner account.")
        self.owner_session = result["session_token"]
        return result

    def logout(self):
        return self.request("/api/admin/logout", {})

    def decide(self, operator_id, action):
        if action not in ("APPROVE", "REJECT"):
            raise APIError("Choose APPROVE or REJECT.")
        return self.request("/api/admin/action", {"operator_id": operator_id, "action": action})
