import os
import sqlite3
import datetime
import urllib.parse
import hmac
import hashlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

# Optional SMTP Settings (fallback if Microsoft Graph Mail.Send is not enabled)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@enuguair.com")

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
        # Pre-approve Isaac Eke automatically as admin owner
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
    version="2.1.0",
    description="Backend service managing operator email approvals and streaming techlog scans into Isaac Eke's Microsoft 365 OneDrive AppFolder."
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
# ACTION TOKEN GENERATION & VERIFICATION
# -----------------------------------------------------------------------------
def generate_action_token(email: str, action: str) -> str:
    msg = f"{email.lower().strip()}:{action.upper()}"
    return hmac.new(ADMIN_SECRET.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()[:24]

def verify_action_token(email: str, action: str, token: str) -> bool:
    expected = generate_action_token(email, action)
    return hmac.compare_digest(expected, token)

# -----------------------------------------------------------------------------
# GRAPH API HELPER: Application Token
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
    try:
        resp = requests.post(token_url, data=data, timeout=15)
        if resp.status_code in (200, 201):
            return resp.json().get("access_token")
    except Exception as e:
        print(f"[GRAPH TOKEN ERROR] {e}")
    return None

# -----------------------------------------------------------------------------
# DISPATCH APPROVAL EMAIL TO ISAAC EKE
# -----------------------------------------------------------------------------
def build_approval_email_html(email: str, name: str, approve_url: str, decline_url: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Operator Access Request</title>
    </head>
    <body style="margin: 0; padding: 24px; background-color: #0B0F19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #F1F5F9;">
        <div style="max-width: 600px; margin: 0 auto; background: #131B2E; border: 1px solid #1E293B; border-radius: 16px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            <div style="border-bottom: 1px solid #1E293B; padding-bottom: 20px; margin-bottom: 24px;">
                <h2 style="margin: 0; font-size: 20px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px;">Enugu Air Techlog Scanner</h2>
                <p style="margin: 6px 0 0 0; font-size: 13px; color: #94A3B8;">New Operator Access Request</p>
            </div>
            
            <p style="font-size: 15px; line-height: 1.6; color: #E2E8F0; margin-top: 0;">
                An operator has signed into the Enugu Air Techlog Scanner and is requesting authorization to upload scans directly into your Microsoft 365 OneDrive account.
            </p>

            <div style="background: #0B0F19; border: 1px solid #1E293B; border-radius: 12px; padding: 20px; margin: 24px 0;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <tr>
                        <td style="padding: 6px 0; color: #64748B; width: 140px;">Operator Name:</td>
                        <td style="padding: 6px 0; color: #F8FAFC; font-weight: 600;">{name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748B;">Operator Email:</td>
                        <td style="padding: 6px 0; color: #38BDF8; font-weight: 600; font-family: monospace;">{email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748B;">Target Storage:</td>
                        <td style="padding: 6px 0; color: #F8FAFC; font-weight: 600;">{TARGET_ONEDRIVE_USER} (1 TB Drive)</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748B;">Target Folder:</td>
                        <td style="padding: 6px 0; color: #A5B4FC; font-family: monospace; font-size: 12px;">OneDrive/Apps/Enugu Air Scanner/</td>
                    </tr>
                </table>
            </div>

            <p style="font-size: 14px; color: #94A3B8; margin-bottom: 24px;">
                Select an action below to instantly grant or deny access directly from this email:
            </p>

            <div style="text-align: center; margin: 32px 0 24px 0;">
                <a href="{approve_url}" style="display: inline-block; background-color: #10B981; color: #042F1E; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-weight: 700; font-size: 15px; margin-right: 12px; letter-spacing: 0.5px;">
                    ACCEPT OPERATOR
                </a>
                <a href="{decline_url}" style="display: inline-block; background-color: #EF4444; color: #FFFFFF; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-weight: 700; font-size: 15px; letter-spacing: 0.5px;">
                    DECLINE
                </a>
            </div>

            <div style="border-top: 1px solid #1E293B; padding-top: 20px; margin-top: 32px; font-size: 12px; color: #64748B; line-height: 1.5;">
                <p style="margin: 0;">This email was automatically generated by the Enugu Air Ingestion Backend Service.</p>
                <p style="margin: 4px 0 0 0;">If you did not expect this request, tap Decline to block this operator from submitting scans.</p>
            </div>
        </div>
    </body>
    </html>
    """

def dispatch_operator_approval_email(email: str, name: str):
    approve_token = generate_action_token(email, "APPROVE")
    decline_token = generate_action_token(email, "REJECT")
    
    approve_url = f"{BASE_URL}/api/admin/email-action?email={urllib.parse.quote(email)}&action=APPROVE&token={approve_token}"
    decline_url = f"{BASE_URL}/api/admin/email-action?email={urllib.parse.quote(email)}&action=REJECT&token={decline_token}"
    
    html_content = build_approval_email_html(email, name, approve_url, decline_url)
    subject = f"Action Required: Operator Access Request from {email}"

    # Always log one-click links in console/logs for instant audit & manual access
    print("\n" + "=" * 80)
    print(f"[OPERATOR ACCESS REQUEST] {name} ({email})")
    print(f"ACCEPT:  {approve_url}")
    print(f"DECLINE: {decline_url}")
    print("=" * 80 + "\n")

    # 1. Attempt Microsoft Graph API sendMail
    token = get_graph_app_token()
    if token:
        try:
            graph_mail_url = f"https://graph.microsoft.com/v1.0/users/{TARGET_ONEDRIVE_USER}/sendMail"
            payload = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_content
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": TARGET_ONEDRIVE_USER
                            }
                        }
                    ]
                },
                "saveToSentItems": "false"
            }
            resp = requests.post(
                graph_mail_url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=15
            )
            if resp.status_code in (200, 202):
                print(f"[GRAPH MAIL] Successfully delivered approval email to {TARGET_ONEDRIVE_USER}")
                return
            else:
                print(f"[GRAPH MAIL NOTICE] HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[GRAPH MAIL EXCEPTION] {e}")

    # 2. Fallback to standard SMTP if configured
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM
            msg["To"] = TARGET_ONEDRIVE_USER
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [TARGET_ONEDRIVE_USER], msg.as_string())
            print(f"[SMTP MAIL] Successfully delivered approval email via SMTP to {TARGET_ONEDRIVE_USER}")
        except Exception as e:
            print(f"[SMTP MAIL EXCEPTION] {e}")

# -----------------------------------------------------------------------------
# API ROUTES
# -----------------------------------------------------------------------------
@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Enugu Air Techlog Scanner Backend",
        "version": "2.1.0",
        "target_onedrive": TARGET_ONEDRIVE_USER,
        "client_id": CLIENT_ID,
        "tenant_id": TENANT_ID,
        "has_client_secret": bool(CLIENT_SECRET),
        "approval_mode": "EMAIL_ONE_CLICK",
        "admin_email": TARGET_ONEDRIVE_USER
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
            # If still pending, re-dispatch the approval email
            if status == "PENDING":
                dispatch_operator_approval_email(email, name)
        else:
            # Isaac is always auto-approved
            status = "APPROVED" if email == TARGET_ONEDRIVE_USER.lower() else "PENDING"
            conn.execute("""
                INSERT INTO operators (email, name, status, registered_at, approved_at)
                VALUES (?, ?, ?, ?, ?)
            """, (email, name, status, now, now if status == "APPROVED" else None))
            conn.commit()

            # Dispatch approval email to Isaac Eke if pending
            if status == "PENDING":
                dispatch_operator_approval_email(email, name)

    return {
        "email": email,
        "name": name,
        "status": status,
        "is_approved": status == "APPROVED",
        "message": "Operator approved" if status == "APPROVED" else "Approval request sent to Isaac Eke via email"
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

# -----------------------------------------------------------------------------
# ONE-CLICK EMAIL ACTION ENDPOINT (Tapped directly inside Outlook / Mail)
# -----------------------------------------------------------------------------
@app.get("/api/admin/email-action", response_class=HTMLResponse)
def email_action(email: str, action: str, token: str):
    email_clean = email.strip().lower()
    action_clean = action.strip().upper()

    if not verify_action_token(email_clean, action_clean, token):
        return HTMLResponse(
            status_code=403,
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>Authorization Failed</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="font-family: -apple-system, sans-serif; background: #0B0F19; color: #F1F5F9; padding: 40px; text-align: center;">
                <div style="max-width: 480px; margin: 40px auto; background: #131B2E; border: 1px solid #EF4444; border-radius: 16px; padding: 32px;">
                    <h2 style="color: #EF4444; margin-top: 0;">Authorization Token Invalid</h2>
                    <p style="color: #94A3B8;">This action link is expired or invalid. Please check the latest request email.</p>
                </div>
            </body>
            </html>
            """
        )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_status = "APPROVED" if action_clean == "APPROVE" else "REJECTED"

    with get_db() as conn:
        conn.execute("""
            UPDATE operators SET status = ?, approved_at = ? WHERE email = ?
        """, (new_status, now if new_status == "APPROVED" else None, email_clean))
        conn.commit()

    is_approved = new_status == "APPROVED"
    header_color = "#10B981" if is_approved else "#EF4444"
    status_title = "Operator Approved" if is_approved else "Operator Declined"
    description = (
        f"Operator <strong>{email_clean}</strong> is now authorized to upload aircraft techlog scans directly into your 1 TB OneDrive storage."
        if is_approved
        else f"Operator <strong>{email_clean}</strong> access has been declined. Uploads from this account are blocked."
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{status_title} — Enugu Air Scanner</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0B0F19; color: #F1F5F9; margin: 0; padding: 24px; text-align: center; }}
            .card {{ max-width: 500px; margin: 40px auto; background: #131B2E; border: 1px solid #1E293B; border-radius: 16px; padding: 36px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }}
            .badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; background: {header_color}22; color: {header_color}; border: 1px solid {header_color}; margin-bottom: 20px; }}
            h1 {{ margin: 0 0 16px 0; font-size: 22px; color: #FFFFFF; }}
            p {{ color: #94A3B8; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0; }}
            .details {{ background: #0B0F19; border: 1px solid #1E293B; border-radius: 10px; padding: 16px; text-align: left; font-size: 13px; margin-bottom: 24px; }}
            .details div {{ margin-bottom: 8px; }}
            .label {{ color: #64748B; }}
            .val {{ color: #F8FAFC; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">{new_status}</div>
            <h1>{status_title}</h1>
            <p>{description}</p>
            <div class="details">
                <div><span class="label">Operator: </span><span class="val">{email_clean}</span></div>
                <div><span class="label">Decided At: </span><span class="val">{now[:19]} UTC</span></div>
                <div><span class="label">Target Drive: </span><span class="val">{TARGET_ONEDRIVE_USER}</span></div>
                <div><span class="label">Destination: </span><span class="val">OneDrive/Apps/Enugu Air Scanner/</span></div>
            </div>
            <p style="font-size: 12px; color: #64748B; margin: 0;">You can safely close this browser window. The operator's Android app will reflect this status automatically.</p>
        </div>
    </body>
    </html>
    """

# -----------------------------------------------------------------------------
# DIRECT API ACTION (For dashboard or programmatic callers)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# SCAN UPLOAD INGESTION (Proxies directly into Isaac Eke's OneDrive)
# -----------------------------------------------------------------------------
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
        op = conn.execute("SELECT status FROM operators WHERE email = ?", (clean_email)).fetchone() if False else conn.execute("SELECT status FROM operators WHERE email = ?", (clean_email,)).fetchone()
        if not op or op["status"] != "APPROVED":
            raise HTTPException(
                status_code=403,
                detail=f"Operator '{clean_email}' is not approved to upload. Awaiting email approval from Isaac Eke."
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
# ADMIN CONSOLE (Optional secondary overview)
# -----------------------------------------------------------------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    with get_db() as conn:
        operators = conn.execute("SELECT * FROM operators ORDER BY registered_at DESC").fetchall()
        scans = conn.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 50").fetchall()

    op_rows = ""
    for op in operators:
        status_color = "#10B981" if op["status"] == "APPROVED" else ("#F59E0B" if op["status"] == "PENDING" else "#EF4444")
        action_buttons = ""
        if op["status"] != "APPROVED":
            action_buttons += f"""<button onclick="takeAction('{op['email']}', 'APPROVE')" style="background:#10B981; color:#042F1E; border:none; padding:6px 12px; border-radius:6px; font-weight:bold; cursor:pointer; margin-right:6px;">APPROVE</button>"""
        if op["status"] != "REJECTED" and op["email"] != TARGET_ONEDRIVE_USER:
            action_buttons += f"""<button onclick="takeAction('{op['email']}', 'REJECT')" style="background:#EF4444; color:#fff; border:none; padding:6px 12px; border-radius:6px; font-weight:bold; cursor:pointer;">REJECT</button>"""

        op_rows += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #1E293B;">{op['email']}</td>
            <td style="padding:10px; border-bottom:1px solid #1E293B;">{op['name']}</td>
            <td style="padding:10px; border-bottom:1px solid #1E293B;"><span style="color:{status_color}; font-weight:bold;">{op['status']}</span></td>
            <td style="padding:10px; border-bottom:1px solid #1E293B;">{action_buttons}</td>
        </tr>
        """

    scan_rows = ""
    for s in scans:
        scan_rows += f"""
        <tr>
            <td style="padding:8px; border-bottom:1px solid #1E293B;">{s['filename']}</td>
            <td style="padding:8px; border-bottom:1px solid #1E293B;">{s['aircraft']}</td>
            <td style="padding:8px; border-bottom:1px solid #1E293B;">{s['operator_email']}</td>
            <td style="padding:8px; border-bottom:1px solid #1E293B;">{s['uploaded_at'][:19]}</td>
            <td style="padding:8px; border-bottom:1px solid #1E293B; font-size:11px;">{s['graph_status']}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enugu Air Scanner - Admin Overview</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0B0F19; color: #F1F5F9; margin: 0; padding: 24px; }}
            .card {{ background: #131B2E; border: 1px solid #1E293B; border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
            h1, h2 {{ margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
            th {{ background: #1E293B; padding: 10px; font-weight: bold; color: #94A3B8; }}
            .pill {{ background: #0B0F19; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12px; border: 1px solid #1E293B; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Enugu Air Scanner — Admin Overview</h1>
            <p>Target Storage: <span class="pill">{TARGET_ONEDRIVE_USER}</span> (1 TB Account)</p>
            <p>Target Path: <span class="pill">OneDrive/Apps/Enugu Air Scanner/&lt;AIRCRAFT&gt;/</span></p>
            <p>Approval Route: <span class="pill">Emails routed directly to {TARGET_ONEDRIVE_USER} with ACCEPT / DECLINE buttons</span></p>
            <p>Microsoft Entra App ID: <span class="pill">{CLIENT_ID}</span> | Tenant: <span class="pill">{TENANT_ID}</span></p>
        </div>

        <div class="card">
            <h2>Registered Operators</h2>
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
