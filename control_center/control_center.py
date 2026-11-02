"""Owner panel for Microsoft folder permissions. No scanner server is used."""
import json
import datetime
import queue
import re
import threading
import time
import tkinter as tk
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import messagebox, ttk

from api_client import APIError
from build_apk import build_apk
from folder_access import GraphClient, individual_write, load_folder_config, normalize_email, permission_emails, save_folder_config
from owner_sign_in import MicrosoftOwnerSignIn, MicrosoftTokenSession, SHARED_SCOPES
from session_store import SessionStore


class ControlCenter:
    def __init__(self, root, client_factory=GraphClient, sign_in_factory=MicrosoftOwnerSignIn,
                 session_store=None, browser_open=webbrowser.open, config_save=save_folder_config,
                 apk_builder=build_apk, confirm=messagebox.askyesno):
        self.root = root
        self.client_factory = client_factory
        self.write_live_diagnostics = client_factory is GraphClient
        self.sign_in_factory = sign_in_factory
        self.session_store = session_store or SessionStore(Path(__file__).with_name("owner_graph_session.dat"))
        self.browser_open = browser_open
        self.config_save = config_save
        self.apk_builder = apk_builder
        self.confirm = confirm
        self.client = None
        self.owner_profile = None
        self.owner_session = None
        self.test_client = None
        self.test_allowed = False
        self.connected = False
        self.busy = False
        self.closed = False
        self.generation = 0
        self.cancelled = threading.Event()
        self.events = queue.Queue()
        self.after_ids = set()
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.permissions_by_id = {}
        self.email_labels = {}
        root.title("Enugu Air Access Panel")
        root.geometry("1060x770")
        root.minsize(900, 700)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.configure(background="#0b101b")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#0b101b")
        style.configure("TLabel", background="#0b101b", foreground="#e6edf7", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 11), padding=9)
        style.configure("Treeview", background="#141d2c", fieldbackground="#141d2c", foreground="#e6edf7", rowheight=32, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Enugu Air Access Panel", font=("Segoe UI", 23, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Add the Microsoft emails that may use your scanner folder.").pack(anchor="w", pady=(5, 16))
        connection = ttk.Frame(frame)
        connection.pack(fill="x")
        self.owner_label = tk.StringVar(value="Sign in as the folder owner to manage access.")
        ttk.Label(connection, textvariable=self.owner_label).pack(side="left", expand=True, fill="x")
        self.sign_in_button = ttk.Button(connection, text="SIGN IN AS OWNER", command=self.sign_in)
        self.sign_in_button.pack(side="left", padx=8)
        self.sign_out_button = ttk.Button(connection, text="Sign out", command=self.sign_out, state="disabled")
        self.sign_out_button.pack(side="left")
        self.code_card = ttk.Frame(frame, padding=(0, 10))
        self.sign_in_code = tk.StringVar()
        ttk.Label(self.code_card, text="Enter this code on the Microsoft sign-in page:").pack(anchor="w")
        ttk.Label(self.code_card, textvariable=self.sign_in_code, font=("Consolas", 22, "bold")).pack(side="left")
        ttk.Button(self.code_card, text="Copy code", command=self.copy_code).pack(side="left", padx=10)
        ttk.Button(self.code_card, text="Cancel", command=self.cancel_sign_in).pack(side="left")
        self.status = tk.StringVar(value="Microsoft controls the folder permissions. You add and remove people here.")
        self.status_widget = ttk.Label(frame, textvariable=self.status, wraplength=980)
        self.status_widget.pack(anchor="w", pady=(12, 14))
        email_row = ttk.Frame(frame)
        email_row.pack(fill="x")
        ttk.Label(email_row, text="Microsoft email").pack(side="left", padx=(0, 12))
        self.email = tk.StringVar()
        self.email_entry = ttk.Entry(email_row, textvariable=self.email, width=44, font=("Segoe UI", 12))
        self.email_entry.pack(side="left", fill="x", expand=True)
        self.email_entry.bind("<Return>", lambda event: self.approve_email())
        self.approve = ttk.Button(email_row, text="APPROVE EMAIL", command=self.approve_email, state="disabled")
        self.approve.pack(side="left", padx=(12, 0))
        ttk.Label(frame, text="Folder access", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(16, 6))
        self.operators = ttk.Treeview(frame, columns=("email", "access"), show="headings", height=7)
        self.operators.heading("email", text="Microsoft email / identity")
        self.operators.heading("access", text="Microsoft folder permission")
        self.operators.column("email", width=540)
        self.operators.column("access", width=320)
        self.operators.pack(fill="both", expand=True)
        self.operators.bind("<<TreeviewSelect>>", lambda event: self.update_buttons())
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=10)
        self.remove = ttk.Button(actions, text="Remove selected access", command=self.remove_access, state="disabled")
        self.remove.pack(side="left")
        self.refresh_button = ttk.Button(actions, text="Refresh list", command=self.refresh, state="disabled")
        self.refresh_button.pack(side="left", padx=10)
        self.open_folder_button = ttk.Button(actions, text="Open scanner folder", command=self.open_folder, state="disabled")
        self.open_folder_button.pack(side="left")
        ttk.Label(frame, text="Test the actual Microsoft sign-in", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(10, 8))
        testing = ttk.Frame(frame)
        testing.pack(fill="x")
        self.test_button = ttk.Button(testing, text="TEST MICROSOFT SIGN-IN", command=self.test_sign_in, state="disabled")
        self.test_button.pack(side="left")
        self.upload_test_button = ttk.Button(testing, text="Verify PDF delivery", command=self.upload_test, state="disabled")
        self.upload_test_button.pack(side="left", padx=10)
        self.test_result = tk.StringVar(value="Shared-folder sign-in asks Microsoft for access to all files that account can access. The app addresses the ATTAIR scanner folder. Review Microsoft's consent before accepting.")
        ttk.Label(frame, textvariable=self.test_result, wraplength=980).pack(anchor="w", pady=8)
        deployment = ttk.Frame(frame)
        deployment.pack(fill="x", pady=(12, 0))
        self.build_button = ttk.Button(deployment, text="BUILD APK FOR THIS FOLDER", command=self.build, state="disabled")
        self.build_button.pack(side="left")
        ttk.Label(deployment, text="Build after connecting your folder, then send TECHLOG SCAN.apk.").pack(side="left", padx=12)
        self.schedule(100, self.drain_events)
        self.schedule(30000, self.poll)
        saved = self.session_store.load()
        self.record_status("OWNER_AUTHORIZATION_REQUIRED")
        if saved and saved.get("tokens"):
            try:
                self.owner_session = MicrosoftTokenSession(saved["tokens"])
                self.client = self.client_factory(self.owner_session, saved.get("config"))
                self.status.set("Checking the saved Microsoft owner sign-in…")
                self.submit(self.client.connect_owner, "owner_restored")
            except APIError as error:
                self.status.set(str(error))

    def schedule(self, delay, callback):
        if self.closed:
            return
        def invoke():
            self.after_ids.discard(after_id)
            if not self.closed:
                callback()
        after_id = self.root.after(delay, invoke)
        self.after_ids.add(after_id)

    def submit(self, function, kind):
        if self.closed:
            return
        self.busy = True
        self.update_buttons()
        generation = self.generation
        def work():
            try:
                self.events.put((generation, kind, function(), None))
            except Exception as error:
                self.events.put((generation, kind, None, error))
        self.worker.submit(work)

    def authenticate(self, test=False):
        if self.busy:
            return
        self.cancelled.set()
        self.cancelled = threading.Event()
        cancelled = self.cancelled
        self.generation += 1
        generation = self.generation
        config = self.client.config if self.client else None
        if not test:
            self.connected = False
            self.client = None
            self.owner_profile = None
            self.owner_session = None
        self.status.set("Starting Microsoft sign-in…")
        self.record_status("TEST_SIGN_IN_STARTED" if test else "OWNER_SIGN_IN_STARTED")
        if test:
            self.test_client = None
            self.test_allowed = False
            self.test_result.set("Sign in with the account to test. Review Microsoft's shared-file access consent; continue only if you accept it.")
        def work():
            flow = self.sign_in_factory()
            if test:
                flow.scope = SHARED_SCOPES
            challenge = flow.begin()
            if cancelled.is_set():
                raise APIError("Microsoft sign-in cancelled.")
            self.events.put((generation, "challenge", challenge, None))
            tokens = flow.finish(challenge, cancelled)
            if cancelled.is_set():
                raise APIError("Microsoft sign-in cancelled.")
            session = MicrosoftTokenSession.from_result(tokens)
            client = self.client_factory(session, config)
            result = client.test_access() if test else client.connect_owner()
            return {"client": client, "result": result, "session": session}
        self.submit(work, "test_signed_in" if test else "owner_signed_in")

    def sign_in(self):
        self.authenticate()

    def test_sign_in(self):
        if self.connected:
            self.authenticate(test=True)

    def copy_code(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.sign_in_code.get())

    def cancel_sign_in(self):
        self.cancelled.set()
        self.generation += 1
        self.busy = False
        self.code_card.pack_forget()
        self.status.set("Microsoft sign-in cancelled.")
        self.update_buttons()

    def sign_out(self):
        self.cancel_sign_in()
        self.session_store.clear()
        self.client = None
        self.owner_profile = None
        self.owner_session = None
        self.test_client = None
        self.test_allowed = False
        self.connected = False
        self.permissions_by_id.clear()
        self.operators.delete(*self.operators.get_children())
        self.owner_label.set("Sign in as the folder owner to manage access.")
        self.status.set("Signed out.")
        self.update_buttons()

    def refresh(self):
        if self.client and self.connected and not self.busy:
            self.submit(self.client.permissions, "permissions")

    def poll(self):
        self.refresh()
        self.schedule(30000, self.poll)

    def approve_email(self):
        if not self.connected or self.busy:
            return
        try:
            email = normalize_email(self.email.get())
        except APIError as error:
            self.status.set(str(error))
            return
        self.status.set("Granting Microsoft folder access to " + email + "…")
        self.submit(lambda: self.client.approve_email(email), "approved")

    def remove_access(self):
        selected = self.operators.selection()
        if not self.connected or self.busy or not selected:
            return
        permission = self.permissions_by_id.get(selected[0])
        if not permission or permission.get("inheritedFrom") or "owner" in permission.get("roles", []):
            return
        label = self.operators.item(selected[0], "values")[0]
        if not self.confirm("Remove folder access", "Remove this Microsoft folder permission?\n\n" + label):
            return
        self.submit(lambda: self.client.remove_access(permission["id"]), "removed")

    def open_folder(self):
        if self.client and self.client.config.get("folder_url"):
            self.browser_open(self.client.config["folder_url"])

    def upload_test(self):
        if self.test_client and self.test_allowed and not self.busy:
            self.test_result.set("Checking this account, uploading one PDF, and reading it back as the ATTAIR owner…")
            self.submit(lambda: self.test_client.upload_test_pdf(self.client), "test_uploaded")

    def build(self):
        if not self.connected or self.busy:
            return
        generation = self.generation
        self.status.set("Building the APK for your connected scanner folder…")
        def progress(line):
            self.events.put((generation, "progress", line, None))
        self.submit(lambda: self.apk_builder(progress), "built")

    def render_permissions(self, permissions):
        selected = self.operators.selection()
        self.permissions_by_id = {item["id"]: item for item in permissions if item.get("id")}
        self.operators.delete(*self.operators.get_children())
        for permission_id, item in self.permissions_by_id.items():
            emails = permission_emails(item)
            label = ", ".join(sorted(emails)) or self.email_labels.get(permission_id)
            if not label:
                people = item.get("grantedToV2") or item.get("grantedTo") or {}
                label = people.get("user", {}).get("displayName") or ("Sharing link" if item.get("link") else "Microsoft identity")
            roles = item.get("roles", [])
            access = "Owner" if "owner" in roles else "Approved — individual write access" if individual_write(item) else ", ".join(roles)
            if item.get("inheritedFrom"):
                access += " (inherited)"
            self.operators.insert("", "end", iid=permission_id, values=(label, access))
        if selected and selected[0] in self.permissions_by_id:
            self.operators.selection_set(selected[0])
        self.status.set("Connected to Microsoft. Enter an email to grant folder access.")

    def drain_events(self):
        while not self.events.empty():
            generation, kind, data, error = self.events.get()
            if generation != self.generation:
                continue
            if kind == "progress":
                self.status.set(data)
                continue
            if kind == "challenge":
                self.sign_in_code.set(data["user_code"])
                self.code_card.pack(fill="x", before=self.status_widget)
                try:
                    self.browser_open(data["verification_uri"])
                except OSError:
                    self.status.set("Open " + data["verification_uri"] + " and enter the code shown.")
                continue
            self.busy = False
            self.code_card.pack_forget()
            if error:
                self.record_status(kind.upper() + "_FAILED", error)
                self.status.set(str(error))
                if isinstance(error, APIError) and error.status_code == 401 and kind != "test_signed_in":
                    self.sign_out()
                    self.status.set("Microsoft owner sign-in expired. Sign in again.")
                if kind == "test_signed_in":
                    self.test_result.set("Access test failed: " + str(error))
                if kind == "test_uploaded":
                    self.test_result.set("NOT VERIFIED: " + str(error))
            elif kind in ("owner_signed_in", "owner_restored"):
                if kind == "owner_signed_in":
                    self.client = data["client"]
                    result = data["result"]
                    self.owner_session = data["session"]
                else:
                    result = data
                try:
                    self.config_save(result["config"])
                except (APIError, OSError) as error:
                    self.connected = False
                    self.status.set("Cannot save the scanner folder configuration: " + str(error))
                    self.update_buttons()
                    continue
                self.owner_profile = result["profile"]
                self.client.config = result["config"]
                self.connected = True
                self.record_status("OWNER_CONNECTED")
                self.owner_label.set("Owner: " + self.owner_profile["email"])
                self.save_owner_session()
                self.refresh()
            elif kind == "permissions":
                self.render_permissions(data)
            elif kind == "approved":
                for item in data["permissions"]:
                    if item.get("id"):
                        self.email_labels[item["id"]] = data["email"]
                self.email.set("")
                self.status.set("Microsoft granted folder access to " + data["email"] + ".")
                self.refresh()
            elif kind == "removed":
                self.status.set("The selected Microsoft folder permission was removed.")
                self.refresh()
            elif kind == "test_signed_in":
                result = data["result"]
                self.test_client = data["client"]
                self.test_allowed = result["allowed"]
                self.test_result.set(("ALLOWED: " if result["allowed"] else "DENIED: ") + result["email"] + " — " + result["message"])
                self.status.set("Microsoft account test complete. No access permission was changed.")
            elif kind == "test_uploaded":
                if data.get("verified") is True:
                    self.test_result.set("VERIFIED: " + data["filename"] + " using " + data["email"] +
                                         "\nATTAIR owner read back identical PDF bytes. SHA-256: " + data["sha256"])
                    self.status.set("PDF delivery verified in the configured ATTAIR scanner folder.")
                    if data.get("live_microsoft") is True:
                        try:
                            evidence = {**data, "verified_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
                            path = Path(__file__).resolve().parents[1] / ".build/live-folder-verification.json"
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
                        except OSError:
                            self.status.set("PDF delivery verified, but the local verification record could not be saved.")
                else:
                    self.test_result.set("NOT VERIFIED: owner read-back evidence is missing.")
            elif kind == "built":
                self.status.set("APK ready: " + data + ". Send this file to your approved users.")
            self.save_owner_session()
            self.update_buttons()
        self.schedule(100, self.drain_events)

    def save_owner_session(self):
        if self.connected and self.client and self.owner_session:
            try:
                self.session_store.save({"tokens": self.owner_session.snapshot(), "config": self.client.config})
            except OSError:
                pass

    def record_status(self, event, error=None):
        if not self.write_live_diagnostics:
            return
        # Preserve provider error codes for diagnostics, never credentials or sign-in codes.
        data = {"event": event, "owner_connected": self.connected,
                "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "provider_codes": re.findall(r"AADSTS\d+", str(error)) if error else [],
                "http_status": getattr(error, "status_code", None)}
        try:
            path = Path(__file__).resolve().parents[1] / ".build/control-panel-status.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    def update_buttons(self):
        available = self.connected and not self.busy
        self.sign_in_button.configure(state="disabled" if self.busy else "normal")
        self.sign_out_button.configure(state="normal" if self.connected and not self.busy else "disabled")
        for button in (self.approve, self.refresh_button, self.open_folder_button, self.test_button, self.build_button):
            button.configure(state="normal" if available else "disabled")
        selected = self.operators.selection()
        permission = self.permissions_by_id.get(selected[0]) if selected else None
        removable = available and permission and not permission.get("inheritedFrom") and "owner" not in permission.get("roles", [])
        self.remove.configure(state="normal" if removable else "disabled")
        self.upload_test_button.configure(state="normal" if not self.busy and self.test_allowed and self.test_client else "disabled")

    def close(self):
        if self.closed:
            return
        self.cancelled.set()
        self.closed = True
        for after_id in self.after_ids:
            self.root.after_cancel(after_id)
        self.after_ids.clear()
        self.worker.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()


def main():
    root = tk.Tk()
    service_config = Path(__file__).resolve().parents[1] / '.SCRATCH/sample_app/app/src/main/assets/scanner_service.json'
    if service_config.is_file() and json.loads(service_config.read_text(encoding='utf-8')).get('mode') == 'online':
        from online_control_center import OnlineControlCenter
        OnlineControlCenter(root)
    else:
        ControlCenter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
