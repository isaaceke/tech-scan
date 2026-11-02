"""Human-operated access panel for the online scanner relay (Version 3).
Enables the owner to sign in via Microsoft OAuth device code, review and approve
incoming operator requests (Google / Microsoft), manage approved emails on the relay,
and build the updated APK without requiring ATTAIR tenant administrator privileges.
"""
import datetime
import json
import logging
import queue
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "control_center") not in sys.path:
    sys.path.insert(0, str(ROOT / "control_center"))

from build_apk import build_apk

SERVICE_CONFIG = ROOT / ".SCRATCH/sample_app/app/src/main/assets/scanner_service.json"

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "online_control_center.log"

logger = logging.getLogger("OnlineControlCenter")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(file_handler)


class OnlineControlCenter:
    def __init__(self, root, base_url=None, opener=None, apk_builder=None, browser_open=None, confirm=None):
        self.root = root
        if base_url is not None:
            self.base = base_url.rstrip("/")
        else:
            self.base = ""
            if SERVICE_CONFIG.is_file():
                try:
                    self.base = json.loads(SERVICE_CONFIG.read_text(encoding="utf-8")).get("server_url", "").rstrip("/")
                except Exception as ex:
                    logger.warning("Could not read scanner_service.json: %s", ex)
        self.opener = opener or urllib.request.urlopen
        self.apk_builder = apk_builder or build_apk
        self.browser_open = browser_open or webbrowser.open
        self.confirm = confirm or messagebox.askyesno
        self.session = None
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.closed = False
        self.busy = False
        self.after_ids = set()

        logger.info("Initializing Online Control Center GUI v3. Base URL: %s", self.base or "<none>")

        root.title("Enugu Air Access Panel - Online Relay")
        root.geometry("1020x760")
        root.minsize(900, 640)
        root.protocol("WM_DELETE_WINDOW", self.close)

        ico_path = Path(__file__).resolve().parent / "app.ico"
        if ico_path.is_file():
            try:
                root.iconbitmap(default=str(ico_path))
            except Exception:
                pass

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#0b101b")
        style.configure("TLabel", background="#0b101b", foreground="#e6edf7", font=("Segoe UI", 11))
        style.configure("Section.TLabel", background="#0b101b", foreground="#94a3b8", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", padding=8, font=("Segoe UI", 10))
        style.configure("Accent.TButton", padding=8, font=("Segoe UI", 10, "bold"), background="#2563eb", foreground="#ffffff")
        style.configure("Treeview", background="#141d2c", fieldbackground="#141d2c", foreground="#e6edf7", rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Enugu Air Scanner Access", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Approve Microsoft & Google accounts. Scans reach your OneDrive while your laptop is off.").pack(anchor="w", pady=(4, 12))

        self.status = tk.StringVar(value="Online hosting setup is incomplete." if not self.base else "Sign in as owner to manage approved emails.")
        ttk.Label(frame, textvariable=self.status, wraplength=960, font=("Segoe UI", 10)).pack(anchor="w")

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=10)
        self.signin = ttk.Button(actions, text="SIGN IN AS OWNER", command=self.sign_in)
        self.signin.pack(side="left")
        self.refresh_button = ttk.Button(actions, text="Refresh (F5)", command=self.refresh)
        self.refresh_button.pack(side="left", padx=10)

        self.code = tk.StringVar()
        ttk.Label(frame, textvariable=self.code, font=("Consolas", 18, "bold")).pack(anchor="w")
        self.code_help = tk.StringVar()
        ttk.Label(frame, textvariable=self.code_help, wraplength=960).pack(anchor="w")

        # Section 1: Pending Operator Requests
        ttk.Label(frame, text="PENDING ACCESS REQUESTS (SIGN-INS WAITING APPROVAL)", style="Section.TLabel").pack(anchor="w", pady=(10, 4))
        self.pending_table = ttk.Treeview(frame, columns=("email", "provider", "requested_at"), show="headings", height=4)
        self.pending_table.heading("email", text="Operator Email")
        self.pending_table.heading("provider", text="Identity Provider")
        self.pending_table.heading("requested_at", text="Requested At")
        self.pending_table.column("email", width=480)
        self.pending_table.column("provider", width=160)
        self.pending_table.column("requested_at", width=220)
        self.pending_table.pack(fill="x")

        pending_actions = ttk.Frame(frame)
        pending_actions.pack(fill="x", pady=(6, 12))
        self.approve_pending_button = ttk.Button(pending_actions, text="APPROVE SELECTED REQUEST", command=self.approve_pending)
        self.approve_pending_button.pack(side="left")

        # Section 2: Approved Accounts
        ttk.Label(frame, text="APPROVED OPERATORS", style="Section.TLabel").pack(anchor="w", pady=(4, 4))

        manual_row = ttk.Frame(frame)
        manual_row.pack(fill="x", pady=4)
        ttk.Label(manual_row, text="Add operator email:").pack(side="left", padx=(0, 10))
        self.email = tk.StringVar()
        self.email_entry = ttk.Entry(manual_row, textvariable=self.email, font=("Segoe UI", 11))
        self.email_entry.pack(side="left", fill="x", expand=True)
        self.email_entry.bind("<Return>", lambda event: self.approve_email())
        self.approve = ttk.Button(manual_row, text="APPROVE EMAIL", command=self.approve_email)
        self.approve.pack(side="left", padx=10)

        self.table = ttk.Treeview(frame, columns=("email", "state"), show="headings", height=6)
        self.table.heading("email", text="Approved Operator Email")
        self.table.heading("state", text="Account Status")
        self.table.column("email", width=540)
        self.table.column("state", width=320)
        self.table.pack(fill="both", expand=True, pady=4)

        bot_row = ttk.Frame(frame)
        bot_row.pack(fill="x", pady=10)
        self.remove = ttk.Button(bot_row, text="Remove Selected Access", command=self.remove_email)
        self.remove.pack(side="left")
        self.build_button = ttk.Button(bot_row, text="BUILD UPDATED APK", command=self.build)
        self.build_button.pack(side="right")

        self.pending_table.bind("<<TreeviewSelect>>", lambda event: self.buttons())
        self.table.bind("<<TreeviewSelect>>", lambda event: self.buttons())
        root.bind("<F5>", lambda event: self.refresh())
        root.bind("<Escape>", lambda event: self.on_escape())

        self.buttons()
        after_id = self.root.after(100, self.drain)
        self.after_ids.add(after_id)

    def on_escape(self):
        if self.code.get():
            logger.info("Escape pressed; cancelling active device code sign-in.")
            self.cancel.set()
            self.code.set("")
            self.code_help.set("")
            self.status.set("Sign-in cancelled by user.")
            self.buttons()

    def api(self, path, body=None):
        if not self.base.startswith("https://"):
            logger.error("API call attempted without valid https base URL: %s", self.base)
            raise RuntimeError("Online hosting setup is incomplete. The existing APK has not been changed.")
        headers = {"Accept": "application/json", "User-Agent": "EnuguTechlogScanner/1.4"}
        if self.session:
            headers["Authorization"] = "Bearer " + self.session
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        logger.info("API Request: %s %s", "POST" if data is not None else "GET", path)
        try:
            req = urllib.request.Request(self.base + path, data=data, headers=headers)
            with self.opener(req, timeout=30) as response:
                content = response.read() if hasattr(response, "read") else b""
                result = json.loads(content) if isinstance(content, (bytes, str)) and content else {}
                logger.info("API Response 200 OK for %s", path)
                return result
        except urllib.error.HTTPError as error:
            try:
                err_content = error.read()
                result = json.loads(err_content) if err_content else {}
            except Exception:
                result = {}
            finally:
                error.close()
            msg = result.get("error", "Online service request failed.")
            logger.warning("API HTTPError %s on %s: %s", error.code, path, msg)
            raise RuntimeError(msg) from None
        except Exception as error:
            logger.error("API Network Exception on %s: %s", path, error)
            raise

    def submit(self, kind, function):
        if self.busy or self.closed:
            return
        self.busy = True
        self.buttons()
        def work():
            try:
                res = function()
                self.events.put((kind, res, None))
            except Exception as error:
                self.events.put((kind, None, str(error)))
        self.worker.submit(work)

    def buttons(self):
        ready = bool(self.session) and not self.busy
        self.signin.configure(state="normal" if self.base and not self.busy else "disabled")
        for button in (self.approve, self.refresh_button, self.build_button):
            button.configure(state="normal" if ready else "disabled")
        self.approve_pending_button.configure(state="normal" if ready and self.pending_table.selection() else "disabled")
        self.remove.configure(state="normal" if ready and self.table.selection() else "disabled")

    def sign_in(self):
        logger.info("Initiating owner sign-in flow.")
        self.cancel.clear()
        self.submit("challenge", lambda: self.api("/api/owner/signin/start", {}))

    def poll_sign_in(self, challenge):
        deadline = time.monotonic() + int(challenge["expires_in"])
        interval = int(challenge.get("interval", 5))
        logger.info("Polling owner sign-in: challenge id=%s interval=%ss deadline=%ss", challenge.get("id"), interval, int(challenge["expires_in"]))
        while time.monotonic() < deadline:
            if self.cancel.wait(interval):
                logger.info("Owner sign-in polling cancelled.")
                raise RuntimeError("Owner sign-in cancelled.")
            result = self.api("/api/owner/signin/poll", {"id": challenge["id"], "secret": challenge["secret"]})
            if result.get("status") == "CONNECTED":
                logger.info("Owner sign-in confirmed CONNECTED by relay.")
                return result
            interval = int(result.get("interval", interval))
        logger.warning("Owner sign-in device code expired before authentication completed.")
        raise RuntimeError("Microsoft sign-in expired. Sign in again.")

    def refresh(self):
        logger.info("Refreshing owner overview and operator access list.")
        self.submit("overview", lambda: self.api("/api/owner/overview"))

    def approve_email(self):
        value = self.email.get().strip()
        if value:
            logger.info("Submitting email approval: %s", value)
            self.submit("approved", lambda: self.api("/api/owner/emails", {"email": value}))

    def approve_pending(self):
        selected = self.pending_table.selection()
        if not selected:
            return
        value = self.pending_table.item(selected[0], "values")[0]
        logger.info("Approving pending operator request for: %s", value)
        self.submit("approved", lambda: self.api("/api/owner/emails", {"email": value}))

    def remove_email(self):
        selected = self.table.selection()
        if not selected:
            return
        value = self.table.item(selected[0], "values")[0]
        if self.confirm("Remove Scan Access", f"Remove scan access for {value}?"):
            logger.info("Submitting access removal: %s", value)
            self.submit("removed", lambda: self.api("/api/owner/emails/remove", {"email": value}))

    def build(self):
        logger.info("Triggering APK build from GUI.")
        self.submit("built", lambda: self.apk_builder(lambda line: self.events.put(("progress", line, None))))

    def drain(self):
        if self.closed:
            return
        while not self.events.empty():
            kind, value, error = self.events.get()
            if kind == "progress":
                self.status.set(value)
                continue
            self.busy = False
            if error:
                logger.error("GUI Event %s reported error: %s", kind, error)
                self.status.set(error)
                self.code.set("")
                self.code_help.set("")
            elif kind == "challenge":
                logger.info("Displaying device code %s and opening verification URI", value.get("user_code"))
                self.code.set(value["user_code"])
                self.code_help.set("Enter this code on the Microsoft page. Your authorization stays in the online relay.")
                self.browser_open(value["verification_uri"])
                self.submit("signed", lambda challenge=value: self.poll_sign_in(challenge))
            elif kind == "signed":
                logger.info("Owner session acquired.")
                self.session = value["session_token"]
                self.code.set("")
                self.code_help.set("")
                self.status.set("Owner connected.")
                self.refresh()
            elif kind == "overview":
                # Populate Pending Requests
                self.pending_table.delete(*self.pending_table.get_children())
                pending_list = value.get("pending_requests", [])
                for req in pending_list:
                    req_email = req.get("email", "")
                    provider = (req.get("provider") or "microsoft").title()
                    ts = req.get("requested_at")
                    date_str = datetime.datetime.fromtimestamp(ts / 1000.0).strftime("%Y-%m-%d %H:%M:%S") if ts else "Recent"
                    self.pending_table.insert("", "end", values=(req_email, provider, date_str))

                # Populate Approved Accounts
                self.table.delete(*self.table.get_children())
                approved_list = sorted(value.get("approved_emails", []), key=lambda item: item.get("email", ""))
                for approval in approved_list:
                    email_str = approval.get("email", "")
                    status_str = "Account linked" if approval.get("identity_id") else "Awaiting first sign-in"
                    self.table.insert("", "end", values=(email_str, status_str))

                if value.get("storage_connected"):
                    owner_email = value.get("owner", {}).get("email", "owner")
                    approved_count = len(approved_list)
                    pending_count = len(pending_list)
                    pending_msg = f", {pending_count} pending request(s)" if pending_count else ""
                    self.status.set(f"Connected as {owner_email}. {approved_count} approved operators{pending_msg}. Uploads run online.")
                else:
                    self.status.set("OneDrive needs owner sign-in again. Saved scans remain on the phones.")
            elif kind in ("approved", "removed"):
                if kind == "approved":
                    self.email.set("")
                self.status.set("Email approved." if kind == "approved" else "Access removed.")
                self.refresh()
            elif kind == "built":
                logger.info("APK build succeeded: %s", value)
                self.status.set("Updated APK created: " + str(value))
            self.buttons()
        if not self.closed:
            after_id = self.root.after(100, self.drain)
            self.after_ids.add(after_id)

    def close(self):
        logger.info("Closing Online Control Center.")
        self.closed = True
        self.cancel.set()
        self.session = None
        for after_id in list(self.after_ids):
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
        self.after_ids.clear()
        self.worker.shutdown(wait=False, cancel_futures=True)
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = OnlineControlCenter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
