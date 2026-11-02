"""Shared scanner API. Only authenticated GUI actions can approve an account."""
import datetime
import hashlib
import json
import os
import re
import secrets
import sqlite3
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

SERVICE = "enugu-air-scanner"
VERSION = "3.1.0"
MAX_UPLOAD = 32 * 1024 * 1024

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

@dataclass(frozen=True)
class Settings:
    data_dir: Path
    tenant_id: str = "38de9dec-d800-439b-a669-60f628a90e72"
    client_id: str = "dc7101d3-3bb7-462f-92e8-374958f4ddb5"
    client_secret: str = ""
    target_user: str = "isaac.eke@attair.com.ng"

    @classmethod
    def from_environment(cls):
        return cls(
            data_dir=Path(os.getenv("SCANNER_DATA_DIR", str(Path(__file__).resolve().parent))),
            tenant_id=os.getenv("TENANT_ID", cls.tenant_id),
            client_id=os.getenv("CLIENT_ID", cls.client_id),
            client_secret=os.getenv("CLIENT_SECRET", ""),
            target_user=os.getenv("TARGET_ONEDRIVE_USER", cls.target_user),
        )

@contextmanager
def database(settings):
    conn = sqlite3.connect(str(settings.data_dir / "scanner.db"), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def initialize(settings):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with database(settings) as conn:
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS service_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS operator_accounts (
                id TEXT PRIMARY KEY, email TEXT NOT NULL, name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING', registered_at TEXT NOT NULL,
                decided_at TEXT, CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED'))
            );
            CREATE TABLE IF NOT EXISTS operator_sessions (
                digest TEXT PRIMARY KEY, operator_id TEXT NOT NULL, expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS owner_sessions (
                digest TEXT PRIMARY KEY, microsoft_id TEXT NOT NULL, email TEXT NOT NULL,
                name TEXT NOT NULL, expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approval_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, operator_id TEXT NOT NULL,
                action TEXT NOT NULL, decided_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scan_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT, operator_id TEXT NOT NULL,
                filename TEXT NOT NULL, aircraft TEXT NOT NULL, uploaded_at TEXT NOT NULL,
                local_path TEXT NOT NULL, digest TEXT NOT NULL, graph_uploaded INTEGER NOT NULL DEFAULT 0,
                destination_path TEXT NOT NULL, UNIQUE(operator_id, filename, aircraft, digest)
            );
        """)
        conn.execute("INSERT OR IGNORE INTO service_metadata VALUES ('instance_id', ?)", (secrets.token_hex(16),))
    # Keep legacy email-only tables as history; do not import unverified approvals.

def http_json(url, *, headers=None, data=None, method=None):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        error.close()
        raise

def microsoft_identity(access_token):
    """Graph validates its own opaque token. Never accept a phone-supplied identity."""
    try:
        profile = http_json(
            "https://graph.microsoft.com/v1.0/me?$select=id,displayName,mail,userPrincipalName",
            headers={"Authorization": "Bearer " + access_token},
        )
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise HTTPException(401, "Microsoft sign-in expired. Sign in again.") from None
        raise HTTPException(503, "Microsoft identity verification is unavailable. Retry shortly.") from None
    except (OSError, ValueError):
        raise HTTPException(503, "Cannot verify Microsoft identity. Request has not been submitted.") from None
    email = profile.get("mail") or profile.get("userPrincipalName")
    if not profile.get("id") or not email:
        raise HTTPException(401, "Microsoft did not return a usable account identity.")
    return {"id": str(profile["id"]), "email": email.lower().strip(), "name": profile.get("displayName") or email}

def deliver_to_graph(settings, contents, relative):
    # Preserve the existing configured storage integration; never add permissions or consent.
    if not settings.client_secret:
        return False
    try:
        body = urllib.parse.urlencode({"client_id": settings.client_id, "client_secret": settings.client_secret,
            "grant_type": "client_credentials", "scope": "https://graph.microsoft.com/.default"}).encode()
        token = http_json(f"https://login.microsoftonline.com/{settings.tenant_id}/oauth2/v2.0/token", data=body)["access_token"]
        path = urllib.parse.quote(relative.replace("\\", "/"), safe="/")
        url = f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(settings.target_user)}/drive/special/approot:/{path}:/content"
        http_json(url, method="PUT", data=contents, headers={"Authorization": "Bearer " + token, "Content-Type": "application/pdf"})
        return True
    except (OSError, ValueError, KeyError):
        return False  # The durable server copy remains available.

class RegisterRequest(BaseModel):
    email: str | None = None  # Legacy fields are ignored; Graph supplies identity.
    name: str | None = None

class AdminActionRequest(BaseModel):
    operator_id: str
    action: str

def create_app(settings=None, identity_resolver=microsoft_identity, graph_delivery=deliver_to_graph):
    settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(app):
        initialize(settings)
        yield

    app = FastAPI(title="Enugu Air Shared Scanner API", version=VERSION, lifespan=lifespan)
    app.state.settings = settings

    def bearer(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 16384:
            raise HTTPException(401, "Sign-in required.")
        return authorization[7:]

    def operator(token=Depends(bearer)):
        digest = hashlib.sha256(token.encode()).hexdigest()
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        with database(settings) as conn:
            row = conn.execute("""
                SELECT a.* FROM operator_accounts a JOIN operator_sessions s ON s.operator_id = a.id
                WHERE s.digest = ? AND s.expires_at > ?
            """, (digest, now)).fetchone()
        if row is None:
            raise HTTPException(401, "Scanner session expired. Reconnect to the server.")
        return dict(row)

    def admin(token=Depends(bearer)):
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        with database(settings) as conn:
            row = conn.execute("SELECT microsoft_id FROM owner_sessions WHERE digest=? AND expires_at>? AND email=?",
                (hashlib.sha256(token.encode()).hexdigest(), now, settings.target_user.lower().strip())).fetchone()
        if not row:
            raise HTTPException(401, "Owner sign-in required.")
        return row["microsoft_id"]

    def health():
        with database(settings) as conn:
            instance = conn.execute("SELECT value FROM service_metadata WHERE key='instance_id'").fetchone()[0]
        return {"service": SERVICE, "version": VERSION, "status": "online", "instance_id": instance,
                "approval_mode": "HUMAN_GUI", "owner_sign_in": True}

    app.get("/")(health)
    app.get("/api/health")(health)

    @app.post("/api/admin/login")
    def owner_login(access_token=Depends(bearer)):
        identity = identity_resolver(access_token)
        if identity["email"].lower().strip() != settings.target_user.lower().strip():
            raise HTTPException(403, "Sign in with the Microsoft account that owns the scanner storage.")
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        session = secrets.token_urlsafe(48)
        with database(settings) as conn:
            conn.execute("DELETE FROM owner_sessions WHERE expires_at < ?", (now,))
            conn.execute("INSERT INTO owner_sessions VALUES (?, ?, ?, ?, ?)",
                (hashlib.sha256(session.encode()).hexdigest(), identity["id"], identity["email"].lower().strip(),
                 identity["name"], now + 8 * 3600))
        # Owner authentication never inserts or updates an operator approval.
        return {"session_token": session, "name": identity["name"], "email": identity["email"], "role": "OWNER"}

    @app.post("/api/admin/logout", dependencies=[Depends(admin)])
    def owner_logout(token=Depends(bearer)):
        with database(settings) as conn:
            conn.execute("DELETE FROM owner_sessions WHERE digest=?", (hashlib.sha256(token.encode()).hexdigest(),))
        return {"signed_out": True}

    @app.post("/api/auth/register")
    def register(req: RegisterRequest, access_token=Depends(bearer)):
        identity = identity_resolver(access_token)
        session = secrets.token_urlsafe(48)
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        with database(settings) as conn:
            conn.execute("INSERT OR IGNORE INTO operator_accounts (id, email, name, status, registered_at) VALUES (?, ?, ?, 'PENDING', ?)",
                         (identity["id"], identity["email"], identity["name"], utcnow()))
            conn.execute("UPDATE operator_accounts SET email=?, name=? WHERE id=?", (identity["email"], identity["name"], identity["id"]))
            conn.execute("DELETE FROM operator_sessions WHERE expires_at < ?", (now,))
            conn.execute("INSERT INTO operator_sessions VALUES (?, ?, ?)", (hashlib.sha256(session.encode()).hexdigest(), identity["id"], now + 7 * 24 * 3600))
            row = dict(conn.execute("SELECT * FROM operator_accounts WHERE id=?", (identity["id"],)).fetchone())
        return {**row, "session_token": session, "is_approved": row["status"] == "APPROVED",
                "message": "Request received by the shared server. Awaiting the owner's GUI decision."}

    @app.get("/api/auth/status")
    def status(account=Depends(operator)):
        return {**account, "is_approved": account["status"] == "APPROVED"}

    @app.get("/api/admin/overview", dependencies=[Depends(admin)])
    def overview():
        with database(settings) as conn:
            accounts = [dict(row) for row in conn.execute("SELECT * FROM operator_accounts ORDER BY registered_at ASC")]
            scans = [dict(row) for row in conn.execute("""
                SELECT s.id, s.filename, s.aircraft, a.email AS operator_email, s.uploaded_at,
                       s.graph_uploaded, s.destination_path
                FROM scan_uploads s JOIN operator_accounts a ON a.id=s.operator_id ORDER BY s.id DESC LIMIT 50
            """)]
        return {**health(), "operators": accounts, "scans": scans}

    @app.post("/api/admin/action", dependencies=[Depends(admin)])
    def action(req: AdminActionRequest):
        if req.action not in ("APPROVE", "REJECT"):
            raise HTTPException(400, "Choose APPROVE or REJECT.")
        new_status = "APPROVED" if req.action == "APPROVE" else "REJECTED"
        with database(settings) as conn:
            if not conn.execute("SELECT id FROM operator_accounts WHERE id=?", (req.operator_id,)).fetchone():
                raise HTTPException(404, "The selected account no longer exists.")
            conn.execute("UPDATE operator_accounts SET status=?, decided_at=? WHERE id=?", (new_status, utcnow(), req.operator_id))
            conn.execute("INSERT INTO approval_audit (operator_id, action, decided_at) VALUES (?, ?, ?)", (req.operator_id, req.action, utcnow()))
        return {"operator_id": req.operator_id, "status": new_status}

    @app.get("/api/admin/email-action")
    def retired_email_action():
        raise HTTPException(410, "Email approvals have been retired. Use the Control Center GUI.")

    @app.get("/admin")
    def retired_admin_page():
        raise HTTPException(410, "Sign in as owner in the Control Center GUI to manage requests.")

    @app.post("/api/scans/upload")
    async def upload(file: UploadFile = File(...), aircraft: str = Form(...), log_number: str = Form(""),
                     is_patch: bool = Form(False), account=Depends(operator)):
        if account["status"] != "APPROVED":
            raise HTTPException(403, "Awaiting the owner's approval in the Control Center.")
        filename = file.filename or "scan.pdf"
        if not re.fullmatch(r"[A-Z0-9-]{2,16}", aircraft) or len(filename) > 200 or any(c in filename for c in '/\\\x00') or not filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Invalid aircraft or PDF filename.")
        contents = await file.read(MAX_UPLOAD + 1)
        if len(contents) > MAX_UPLOAD or not contents.startswith(b"%PDF-"):
            raise HTTPException(400, "Upload a PDF smaller than 32 MB.")
        digest = hashlib.sha256(contents).hexdigest()
        relative = str(Path(aircraft) / ("patches" if is_patch else "") / filename)
        with database(settings) as conn:
            existing = conn.execute("SELECT id, graph_uploaded FROM scan_uploads WHERE operator_id=? AND filename=? AND aircraft=? AND digest=?", (account["id"], filename, aircraft, digest)).fetchone()
        if existing:
            return {"success": True, "graph_uploaded": bool(existing["graph_uploaded"]), "message": "This PDF is already stored on the shared server."}
        folder = settings.data_dir / "scans_backup" / aircraft / ("patches" if is_patch else "")
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / (digest + ".pdf")
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as pending:
            pending.write(contents)
            pending.flush()
            os.fsync(pending.fileno())
            temporary_path = pending.name
        os.replace(temporary_path, destination)
        with database(settings) as conn:
            conn.execute("INSERT OR IGNORE INTO scan_uploads (operator_id, filename, aircraft, uploaded_at, local_path, digest, destination_path) VALUES (?, ?, ?, ?, ?, ?, ?)", (account["id"], filename, aircraft, utcnow(), str(destination), digest, relative))
        delivered = await run_in_threadpool(graph_delivery, settings, contents, relative)
        if delivered:
            with database(settings) as conn:
                conn.execute("UPDATE scan_uploads SET graph_uploaded=1 WHERE operator_id=? AND filename=? AND aircraft=? AND digest=?", (account["id"], filename, aircraft, digest))
        return {"success": True, "graph_uploaded": bool(delivered), "message": "Uploaded to OneDrive." if delivered else "PDF stored on the shared server. OneDrive delivery is pending."}

    return app

app = create_app()
