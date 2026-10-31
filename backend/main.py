import os
import sqlite3
import datetime
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
TENANT_ID = os.getenv("TENANT_ID", "38de9dec-d800-439b-a669-60f628a90e72")
CLIENT_ID = os.getenv("CLIENT_ID", "dc7101d3-3bb7-462f-92e8-374958f4ddb5")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")  # Generated in Azure Entra -> Certificates & Secrets
TARGET_ONEDRIVE_USER = os.getenv("TARGET_ONEDRIVE_USER", "isaac.eke@attair.com.ng")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "enugu2026")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "scanner.db"
LOCAL_BACKUP_DIR = BASE_DIR / "scans_backup"
LOCAL_BACKUP_DIR.mkdir(exist_ok=True)

# -----------------------------------------------------------------------------
# DATABASE INITIALIZATION
# -----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS operators (
                email TEXT PRIMARY KEY,
                name TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                registered_at TEXT,
                approved_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                aircraft TEXT NOT NULL,
                operator_email TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                graph_status TEXT,
                destination_path TEXT
            )
        """)
        # Pre-approve Isaac Eke automatically as admin operator
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute("""
            INSERT OR IGNORE INTO operators (email, name, status, registered_at, approved_at)
            VALUES (?, ?, 'APPROVED', ?, ?)
        """, (TARGET_ONEDRIVE_USER, "Isaac Eke (Owner)", now, now))
        conn.commit()

init_db()

# -----------------------------------------------------------------------------
# FASTAPI APP
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Enugu Air Techlog Ingestion API",
    version="2.0.0",
    description="Backend service managing operator approvals and uploading techlog scans directly to Isaac Eke's Microsoft 365 OneDrive AppFolder."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# MODELS
# -----------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str
    name: Optional[str] = "Operator"

class AdminActionRequest(BaseModel):
    email: str
    action: str  # "APPROVE" or "REJECT"
    admin_secret: str

# -----------------------------------------------------------------------------
# GRAPH API HELPER: Get Application-Only Access Token
# -----------------------------------------------------------------------------
def get_graph_app_token() -> Optional[str]:
    if not CLIENT_SECRET:
        return None
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default"
    }
    resp = requests.post(token_url, data=data, timeout=15)
    if resp.status_code in (200, 201):
        return resp.json().get("access_token")
    return None

# -----------------------------------------------------------------------------
# API ROUTES
# -----------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Enugu Air Techlog Scanner Backend",
        "target_onedrive": TARGET_ONEDRIVE_USER,
        "client_id": CLIENT_ID,
        "tenant_id": TENANT_ID,
        "has_client_secret": bool(CLIENT_SECRET),
        "admin_dashboard": "/admin"
    }

@app.post("/api/auth/register")
def register_operator(req: RegisterRequest):
    email = req.email.strip().lower()
    name = req.name.strip() if req.name else "Operator"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with get_db() as conn:
        row = conn.execute("SELECT status FROM operators WHERE email = ?", (email,)).fetchone()
        if row:
            status = row["status"]
        else:
            # Isaac is always auto-approved
            status = "APPROVED" if email == TARGET_ONEDRIVE_USER.lower() else "PENDING"
            conn.execute("""
                INSERT INTO operators (email, name, status, registered_at, approved_at)
                VALUES (?, ?, ?, ?, ?)
            """, (email, name, status, now, now if status == "APPROVED" else None))
            conn.commit()

    return {
        "email": email,
        "name": name,
        "status": status,
        "is_approved": status == "APPROVED"
    }

@app.get("/api/auth/status")
def check_operator_status(email: str):
    email_clean = email.strip().lower()
    with get_db() as conn:
        row = conn.execute("SELECT status, name FROM operators WHERE email = ?", (email_clean,)).fetchone()
        if not row:
            return {"email": email_clean, "status": "UNREGISTERED", "is_approved": False}
        return {
            "email": email_clean,
            "name": row["name"],
            "status": row["status"],
            "is_approved": row["status"] == "APPROVED"
        }

@app.post("/api/admin/action")
def admin_action(req: AdminActionRequest):
    if req.admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Invalid admin secret")

    email = req.email.strip().lower()
    action = req.action.upper()
    if action not in ("APPROVE", "REJECT"):
        raise HTTPException(status_code=400, detail="Action must be APPROVE or REJECT")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_status = "APPROVED" if action == "APPROVE" else "REJECTED"

    with get_db() as conn:
        conn.execute("""
            UPDATE operators SET status = ?, approved_at = ? WHERE email = ?
        """, (new_status, now if new_status == "APPROVED" else None, email))
        conn.commit()

    return {"email": email, "status": new_status}

@app.post("/api/scans/upload")
async def upload_scan(
    file: UploadFile = File(...),
    operator_email: str = Form(...),
    aircraft: str = Form(...),
    log_number: str = Form(...),
    is_patch: bool = Form(False)
):
    clean_email = operator_email.strip().lower()

    # 1. Verify operator is APPROVED in database
    with get_db() as conn:
        op = conn.execute("SELECT status FROM operators WHERE email = ?", (clean_email,)).fetchone()
        if not op or op["status"] != "APPROVED":
            raise HTTPException(
                status_code=403,
                detail=f"Operator '{clean_email}' is not approved to upload. Awaiting approval from Isaac Eke."
            )

    pdf_bytes = await file.read()
    filename = file.filename or f"scan_{aircraft}_{log_number}.pdf"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 2. Upload to Isaac's OneDrive AppFolder via Microsoft Graph
    token = get_graph_app_token()
    graph_success = False
    dest_path = f"Apps/Enugu Air Scanner/{aircraft}/{'patches/' if is_patch else ''}{filename}"

    if token:
        # Construct Graph endpoint for approot inside Isaac Eke's drive
        sub_folder = f"{aircraft}/patches/{filename}" if is_patch else f"{aircraft}/{filename}"
        encoded_path = urllib.parse.quote(sub_folder)
        graph_url = f"https://graph.microsoft.com/v1.0/users/{TARGET_ONEDRIVE_USER}/drive/special/approot:/{encoded_path}:/content"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/pdf"
        }
        resp = requests.put(graph_url, headers=headers, data=pdf_bytes, timeout=30)
        if resp.status_code in (200, 201):
            graph_success = True
            graph_note = "Uploaded to OneDrive AppFolder"
        else:
            graph_note = f"Graph HTTP {resp.status_code}: {resp.text[:200]}"
    else:
        # Fallback to local server backup if CLIENT_SECRET has not been set yet
        local_ac_dir = LOCAL_BACKUP_DIR / aircraft / ("patches" if is_patch else "")
        local_ac_dir.mkdir(parents=True, exist_ok=True)
        local_file = local_ac_dir / filename
        local_file.write_bytes(pdf_bytes)
        graph_note = "Saved locally to backend (Set CLIENT_SECRET in environment for live Graph upload)"

    # Record scan in database
    with get_db() as conn:
        conn.execute("""
            INSERT INTO scans (filename, aircraft, operator_email, uploaded_at, graph_status, destination_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (filename, aircraft, clean_email, now_str, graph_note, dest_path))
        conn.commit()

    return {
        "success": True,
        "filename": filename,
        "aircraft": aircraft,
        "destination": dest_path,
        "graph_uploaded": graph_success,
        "message": "Scan received and stored in Isaac Eke's storage" if graph_success else graph_note
    }

# -----------------------------------------------------------------------------
# ADMIN DASHBOARD (Clean Dark-Mode UI for Isaac)
# -----------------------------------------------------------------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_page(key: Optional[str] = None):
    with get_db() as conn:
        operators = conn.execute("SELECT * FROM operators ORDER BY registered_at DESC").fetchall()
        scans = conn.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 50").fetchall()

    op_rows = ""
    for op in operators:
        status_color = "#10B981" if op["status"] == "APPROVED" else ("#F59E0B" if op["status"] == "PENDING" else "#EF4444")
        action_buttons = ""
        if op["status"] != "APPROVED":
            action_buttons += f"""<button onclick="takeAction('{op['email']}', 'APPROVE')" style="background:#10B981; color:#000; border:none; padding:6px 12px; border-radius:6px; font-weight:bold; cursor:pointer; margin-right:6px;">APPROVE</button>"""
        if op["status"] != "REJECTED" and op["email"] != TARGET_ONEDRIVE_USER:
            action_buttons += f"""<button onclick="takeAction('{op['email']}', 'REJECT')" style="background:#EF4444; color:#fff; border:none; padding:6px 12px; border-radius:6px; font-weight:bold; cursor:pointer;">REJECT</button>"""

        op_rows += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #27272A;">{op['email']}</td>
            <td style="padding:10px; border-bottom:1px solid #27272A;">{op['name']}</td>
            <td style="padding:10px; border-bottom:1px solid #27272A;"><span style="color:{status_color}; font-weight:bold;">{op['status']}</span></td>
            <td style="padding:10px; border-bottom:1px solid #27272A;">{action_buttons}</td>
        </tr>
        """

    scan_rows = ""
    for s in scans:
        scan_rows += f"""
        <tr>
            <td style="padding:8px; border-bottom:1px solid #27272A;">{s['filename']}</td>
            <td style="padding:8px; border-bottom:1px solid #27272A;">{s['aircraft']}</td>
            <td style="padding:8px; border-bottom:1px solid #27272A;">{s['operator_email']}</td>
            <td style="padding:8px; border-bottom:1px solid #27272A;">{s['uploaded_at'][:19]}</td>
            <td style="padding:8px; border-bottom:1px solid #27272A; font-size:11px;">{s['graph_status']}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enugu Air Scanner - Admin Console</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #09090B; color: #FAFAFA; margin: 0; padding: 24px; }}
            .card {{ background: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
            h1, h2 {{ margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
            th {{ background: #27272A; padding: 10px; font-weight: bold; color: #A1A1AA; }}
            .pill {{ background: #27272A; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Enugu Air Scanner — Operator Approvals & Ingestion</h1>
            <p>Target OneDrive: <span class="pill">{TARGET_ONEDRIVE_USER}</span> (1 TB Storage Account)</p>
            <p>Target Path: <span class="pill">OneDrive/Apps/Enugu Air Scanner/&lt;AIRCRAFT&gt;/</span></p>
            <p>Microsoft Entra App ID: <span class="pill">{CLIENT_ID}</span> | Tenant: <span class="pill">{TENANT_ID}</span></p>
            <p>Live Graph Upload: <span class="pill" style="color: {'#10B981' if CLIENT_SECRET else '#F59E0B'};">{'ACTIVE (Client Secret Configured)' if CLIENT_SECRET else 'STANDBY (Local Backup Active - Paste Secret to enable Graph PUT)'}</span></p>
        </div>

        <div class="card">
            <h2>Authorized Operators</h2>
            <table>
                <thead>
                    <tr><th>Email</th><th>Name</th><th>Approval Status</th><th>Actions</th></tr>
                </thead>
                <tbody>
                    {op_rows}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>Recent Scans</h2>
            <table>
                <thead>
                    <tr><th>Filename</th><th>Aircraft</th><th>Operator</th><th>Timestamp</th><th>Status</th></tr>
                </thead>
                <tbody>
                    {scan_rows}
                </tbody>
            </table>
        </div>

        <script>
            async function takeAction(email, action) {{
                const secret = prompt("Enter Admin Secret:", "{ADMIN_SECRET}");
                if (!secret) return;
                const resp = await fetch("/api/admin/action", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ email: email, action: action, admin_secret: secret }})
                }});
                const data = await resp.json();
                if (resp.ok) {{
                    window.location.reload();
                }} else {{
                    alert("Error: " + (data.detail || "Action failed"));
                }}
            }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
