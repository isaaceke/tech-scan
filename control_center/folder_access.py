"""Direct Microsoft folder permissions. Mutations are invoked by GUI buttons only."""
import datetime
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from api_client import APIError

GRAPH = "https://graph.microsoft.com/v1.0"
OWNER_EMAIL = "isaac.eke@attair.com.ng"
PUBLIC_CONFIG = Path(__file__).resolve().parent / "scanner_folder.json"
APK_CONFIG = Path(__file__).resolve().parents[1] / ".SCRATCH/sample_app/app/src/main/assets/scanner_folder.json"


def normalize_email(value):
    value = value.strip().lower()
    if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value) or len(value) > 254:
        raise APIError("Enter the exact Microsoft email address, for example name@company.com.")
    return value


def profile_email(profile):
    return normalize_email(profile.get("mail") or profile.get("userPrincipalName") or "")


def identities(permission):
    result = []
    for key in ("grantedToV2", "grantedTo"):
        if isinstance(permission.get(key), dict):
            result.append(permission[key])
    for key in ("grantedToIdentitiesV2", "grantedToIdentities"):
        result.extend(item for item in permission.get(key, []) if isinstance(item, dict))
    return result


def permission_emails(permission):
    values = [permission.get("invitation", {}).get("email", "")]
    for identity in identities(permission):
        for key in ("user", "siteUser"):
            person = identity.get(key, {})
            values.extend([person.get("email", ""), person.get("loginName", "")])
    emails = set()
    for value in values:
        try:
            emails.add(normalize_email(value))
        except APIError:
            pass
    return emails


def permission_matches(profile, permission):
    if not profile.get("id") or not individual_write(permission):
        return False
    people = identities(permission)
    if any("group" in person or "siteGroup" in person for person in people):
        return False  # Organization links and groups do not count as individual approval.
    email = profile_email(profile)
    # Specific-person links must name this person in their grantee list.
    matched_emails = permission_emails({**permission, "invitation": {}}) if permission.get("link") else permission_emails(permission)
    if email in matched_emails:
        return True
    return any(user_id_matches(person.get("user", {}).get("id"), profile.get("id")) for person in people)


def user_id_matches(first, second):
    if not first or not second:
        return False
    guid = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    return first.lower() == second.lower() if re.fullmatch(guid, first) and re.fullmatch(guid, second) else first == second


def individual_write(permission):
    link = permission.get("link")
    if permission.get("expirationDateTime"):
        try:
            expiry = datetime.datetime.fromisoformat(permission["expirationDateTime"].replace("Z", "+00:00"))
            if expiry.tzinfo is None or expiry <= datetime.datetime.now(datetime.timezone.utc):
                return False
        except (TypeError, ValueError):
            return False
    return ("write" in permission.get("roles", []) and permission.get("inheritedFrom") is None
            and (link is None or link.get("scope") == "users")
            and not any("group" in person or "siteGroup" in person for person in identities(permission)))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def save_folder_config(config):
    public = {key: config[key] for key in ("drive_id", "folder_id", "owner_id", "owner_email", "folder_url")}
    if not all(public[key] for key in ("drive_id", "folder_id", "owner_id")):
        raise APIError("Microsoft did not identify the scanner folder.")
    content = json.dumps(public, indent=2) + "\n"
    for path in (PUBLIC_CONFIG, APK_CONFIG):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    return public


def load_folder_config():
    try:
        return json.loads(PUBLIC_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class GraphClient:
    def __init__(self, access_token, config=None, opener=None, graph_root=GRAPH, download_opener=urllib.request.urlopen):
        self.access_token = access_token
        self.config = config
        # An explicit loopback root is used only by the offline HTTP contract tests.
        if graph_root != GRAPH and urllib.parse.urlsplit(graph_root).hostname != "127.0.0.1":
            raise ValueError("Unsupported Graph test address")
        self.graph_root = graph_root
        self.live_service = opener is None and graph_root == GRAPH
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open
        self.download_opener = download_opener

    def request(self, path, method="GET", payload=None, data=None, raw=False, max_bytes=None):
        if "://" in path and not path.startswith(self.graph_root + "/"):
            raise APIError("Unexpected Microsoft service address.")
        url = path if path.startswith(self.graph_root + "/") else self.graph_root + path
        if not url.startswith(self.graph_root + "/"):
            raise APIError("Unexpected Microsoft service address.")
        token = self.access_token() if callable(self.access_token) else self.access_token
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        elif data is not None:
            headers["Content-Type"] = "application/pdf"
        request = urllib.request.Request(url, method=method, data=data, headers=headers)
        try:
            with self.opener(request, timeout=20) as response:
                contents = response.read(max_bytes + 1) if max_bytes is not None else response.read()
                if max_bytes is not None and len(contents) > max_bytes:
                    raise APIError("Downloaded PDF exceeds its expected size.")
                return contents if raw else json.loads(contents) if contents else {}
        except urllib.error.HTTPError as error:
            if raw and error.code == 302:
                location = error.headers.get("Location", "")
                error.close()
                address = urllib.parse.urlsplit(location)
                if address.scheme != "https" or not address.hostname or address.username or address.password:
                    raise APIError("Microsoft returned an unexpected PDF download address.")
                # The URL is preauthenticated by Graph. Never forward the Graph bearer token.
                try:
                    with self.download_opener(urllib.request.Request(location), timeout=20) as response:
                        contents = response.read(max_bytes + 1)
                    if len(contents) > max_bytes:
                        raise APIError("Downloaded PDF exceeds its expected size.")
                    return contents
                except OSError:
                    raise APIError("Could not read back the uploaded PDF from Microsoft.") from None
            try:
                problem = json.load(error).get("error", {})
                detail = problem.get("message", "Microsoft rejected the folder operation.")
            except (ValueError, AttributeError):
                detail = "Microsoft rejected the folder operation."
            finally:
                error.close()
            if error.code == 401:
                detail = "Microsoft sign-in expired. Sign in again."
            elif error.code == 403:
                detail = "Microsoft denied folder access or sharing permission. " + detail
            raise APIError(detail, error.code) from None
        except (OSError, ValueError):
            raise APIError("Cannot reach Microsoft. Folder access has not been confirmed.") from None

    def collection(self, path):
        result = []
        while path:
            page = self.request(path)
            result.extend(page.get("value", []))
            path = page.get("@odata.nextLink")
            if path and not path.startswith(self.graph_root + "/"):
                raise APIError("Microsoft returned an unexpected next page.")
        return result

    def me(self):
        profile = self.request("/me?$select=id,displayName,mail,userPrincipalName")
        if not profile.get("id"):
            raise APIError("Microsoft did not confirm the signed-in account.")
        profile["email"] = profile_email(profile)
        return profile

    def connect_owner(self):
        profile = self.me()
        if profile["email"] != OWNER_EMAIL:
            raise APIError("Sign in with the Microsoft account that owns the scanner folder.", 403)
        folder = self.request("/me/drive/special/approot")
        if not folder.get("folder") and "folder" not in folder:
            raise APIError("Microsoft did not return an application folder.")
        drive_id = folder.get("parentReference", {}).get("driveId")
        if not drive_id:
            drive_id = self.request("/me/drive?$select=id").get("id")
        config = {"drive_id": drive_id, "folder_id": folder.get("id"), "owner_id": profile["id"],
                  "owner_email": profile["email"], "folder_url": folder.get("webUrl", "")}
        self.config = config
        return {"profile": profile, "config": config}

    def folder_path(self):
        if not self.config or not self.config.get("drive_id") or not self.config.get("folder_id"):
            raise APIError("The owner must connect the scanner folder first.")
        quote = lambda value: urllib.parse.quote(str(value), safe="")
        return "/drives/" + quote(self.config["drive_id"]) + "/items/" + quote(self.config["folder_id"])

    def permissions(self):
        return self.collection(self.folder_path() + "/permissions")

    def approve_email(self, email):
        email = normalize_email(email)
        result = self.request(self.folder_path() + "/invite", "POST", {
            "recipients": [{"email": email}], "requireSignIn": True,
            "sendInvitation": False, "roles": ["write"],
        })
        permissions = result.get("value", [])
        if not permissions or any(item.get("error") or not item.get("id") or not individual_write(item)
                                  or email not in permission_emails(item) for item in permissions):
            raise APIError("Microsoft did not confirm the email's folder permission.")
        return {"email": email, "permissions": permissions}

    def remove_access(self, permission_id):
        current = next((p for p in self.permissions() if p.get("id") == permission_id), None)
        if current is None:
            raise APIError("That folder permission no longer exists.")
        if current.get("inheritedFrom") or "owner" in current.get("roles", []):
            raise APIError("Inherited or owner permissions cannot be removed from this panel.")
        return self.request(self.folder_path() + "/permissions/" + urllib.parse.quote(permission_id, safe=""), "DELETE")

    def test_access(self):
        self.folder_path()
        profile = self.me()
        if profile["id"] != self.config.get("owner_id") and hasattr(self.access_token, "snapshot"):
            scopes = self.access_token.snapshot().get("scope", "").lower().split()
            if not any(scope.rsplit("/", 1)[-1] == "files.readwrite.all" for scope in scopes):
                raise APIError("Microsoft did not grant shared-file consent. Review the consent in a new shared-folder sign-in.", 403)
        try:
            folder = self.request(self.folder_path() + "?$select=id,folder,parentReference")
            if (folder.get("id") != self.config["folder_id"] or "folder" not in folder
                    or folder.get("parentReference", {}).get("driveId") != self.config["drive_id"]):
                raise APIError("Microsoft returned a different folder.")
            allowed = profile["id"] == self.config["owner_id"] or any(
                permission_matches(profile, item) for item in self.permissions())
        except APIError as error:
            if error.status_code not in (403, 404):
                raise
            return {"email": profile["email"], "allowed": False, "message": str(error)}
        return {"email": profile["email"], "allowed": allowed,
                "message": "This Microsoft account has individual write access." if allowed else
                           "This Microsoft account has no individual write permission to the scanner folder."}

    def upload_test_pdf(self, owner_client):
        if self.graph_root != owner_client.graph_root or any(self.config.get(key) != owner_client.config.get(key) for key in ("drive_id", "folder_id", "owner_id")):
            raise APIError("The upload and verification clients address different folders.")
        owner = owner_client.me()
        if owner["id"] != self.config["owner_id"] or owner["email"] != OWNER_EMAIL:
            raise APIError("Independent verification requires the ATTAIR folder owner.", 403)
        access = self.test_access()
        if not access["allowed"]:
            raise APIError("This account cannot upload to the scanner folder.", 403)
        filename = "SCANNER_CONNECTION_TEST_" + uuid.uuid4().hex[:12] + ".pdf"
        contents = test_pdf()
        result = self.request(self.folder_path() + ":/" + filename + ":/content", "PUT", data=contents)
        self.verify_item(result, filename, len(contents))
        item_path = "/drives/" + urllib.parse.quote(self.config["drive_id"], safe="") + "/items/" + urllib.parse.quote(result["id"], safe="")
        observed = owner_client.request(item_path + "?$select=id,name,size,file,parentReference,webUrl")
        self.verify_item(observed, filename, len(contents))
        if observed.get("id") != result["id"]:
            raise APIError("Owner read-back returned a different PDF.")
        downloaded = owner_client.request(item_path + "/content", raw=True, max_bytes=len(contents))
        digest = hashlib.sha256(contents).hexdigest()
        if len(downloaded) != len(contents) or hashlib.sha256(downloaded).hexdigest() != digest:
            raise APIError("The PDF read back by the owner does not match the uploaded PDF.")
        return {"email": access["email"], "filename": filename, "url": observed.get("webUrl", ""),
                "drive_id": self.config["drive_id"], "folder_id": self.config["folder_id"],
                "item_id": result["id"], "size": len(contents), "sha256": digest, "verified": True,
                "live_microsoft": self.live_service and owner_client.live_service}

    def verify_item(self, item, filename, size):
        parent = item.get("parentReference", {})
        if (not item.get("id") or "file" not in item or item.get("name") != filename or item.get("size") != size
                or parent.get("driveId") != self.config["drive_id"] or parent.get("id") != self.config["folder_id"]):
            raise APIError("Microsoft did not confirm the PDF's exact ATTAIR destination, name and size.")


def test_pdf():
    stream = b"BT /F1 16 Tf 50 750 Td (SCANNER CONNECTION TEST) Tj ET"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    contents = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(contents))
        contents.extend(str(index).encode() + b" 0 obj\n" + obj + b"\nendobj\n")
    xref = len(contents)
    contents.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        contents.extend(f"{offset:010d} 00000 n \n".encode())
    contents.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(contents)
