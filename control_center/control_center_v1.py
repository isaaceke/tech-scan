import os
import sys
import time
import json
import sqlite3
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Optional, List, Dict

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QLineEdit, QMessageBox, QScrollArea, QSizePolicy
)

# -----------------------------------------------------------------------------
# PATHS & LOGGING
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DB_PATH = BACKEND_DIR / "scanner.db"
ENV_PATH = BACKEND_DIR / ".env"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_FILE = LOG_DIR / "audit.log"

def log_event(level: str, message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{level.upper()}] {message}\n"
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass
    print(entry.strip())

# -----------------------------------------------------------------------------
# BACKGROUND TUNNEL WORKER (Zero-Setup Public Cloud Relay)
# -----------------------------------------------------------------------------
class TunnelWorker(QThread):
    tunnel_ready = pyqtSignal(str)
    tunnel_failed = pyqtSignal(str)

    def __init__(self, port: int = 8000):
        super().__init__()
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.is_running = True

    def run(self):
        log_event("INFO", f"Starting cloud relay tunnel on port {self.port}...")
        try:
            # Prefer npx localtunnel which is installed with Node on user's PC
            cmd = ["npx.cmd", "localtunnel", "--port", str(self.port)]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            # Read public URL from stdout
            for line in self.process.stdout:
                line_clean = line.strip()
                if "your url is:" in line_clean.lower():
                    url = line_clean.split("is:")[-1].strip()
                    log_event("INFO", f"Cloud relay active at: {url}")
                    self.tunnel_ready.emit(url)
                    break

            # Keep process running
            while self.is_running and self.process and self.process.poll() is None:
                time.sleep(1)

        except Exception as e:
            err = f"Tunnel launch exception: {e}"
            log_event("WARNING", err)
            self.tunnel_failed.emit(err)

    def stop(self):
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass

# -----------------------------------------------------------------------------
# MAIN CONTROL CENTER WINDOW (Apple Design Theory Dark Theme)
# -----------------------------------------------------------------------------
class ControlCenterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enugu Air Control Center — Techlog Ingestion & Operator Authorization")
        self.setMinimumSize(980, 680)
        self.resize(1080, 740)

        # Application Icon
        icon_path = str(BASE_DIR / "app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.public_url = "http://localhost:8000"
        self.active_pending_operator: Optional[str] = None
        self.backend_process: Optional[subprocess.Popen] = None
        self.tunnel_worker: Optional[TunnelWorker] = None

        self.setup_ui()
        self.setup_shortcuts()
        self.start_local_backend()
        self.start_tunnel()

        # Database polling timer (2.0s interval)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_database)
        self.poll_timer.start(2000)

        log_event("INFO", "Enugu Air Control Center initialized successfully.")

    # -------------------------------------------------------------------------
    # STYLING & UI SETUP
    # -------------------------------------------------------------------------
    def setup_ui(self):
        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background-color: #0A0E17;
                color: #F1F5F9;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QFrame.card {
                background-color: #121826;
                border: 1px solid #1E293B;
                border-radius: 12px;
                padding: 16px;
            }
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2D3748;
                border-color: #475569;
            }
            QPushButton#btnApprove {
                background-color: #10B981;
                color: #022C1A;
                border: none;
                font-size: 14px;
                font-weight: 700;
                padding: 10px 24px;
            }
            QPushButton#btnApprove:hover {
                background-color: #059669;
            }
            QPushButton#btnReject {
                background-color: #EF4444;
                color: #FFFFFF;
                border: none;
                font-size: 14px;
                font-weight: 700;
                padding: 10px 24px;
            }
            QPushButton#btnReject:hover {
                background-color: #DC2626;
            }
            QPushButton#btnCopy {
                background-color: #38BDF8;
                color: #082F49;
                border: none;
                font-size: 12px;
                font-weight: 700;
                padding: 6px 14px;
            }
            QPushButton#btnCopy:hover {
                background-color: #0EA5E9;
            }
            QTableWidget {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                gridline-color: #1E293B;
                selection-background-color: #1E293B;
                selection-color: #38BDF8;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                font-weight: 600;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #334155;
            }
        """)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. HEADER BAR
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_card.setStyleSheet("QFrame { background-color: #121826; border: 1px solid #1E293B; border-radius: 12px; }")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(18, 14, 18, 14)

        title_vbox = QVBoxLayout()
        lbl_title = QLabel("Enugu Air Control Center")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.5px;")
        lbl_sub = QLabel("Aircraft Techlog Ingestion & Operator Authorization (Zero IT-Admin Architecture)")
        lbl_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        h_layout.addLayout(title_vbox)

        h_layout.addStretch()

        # Status Badge
        self.lbl_status_pill = QLabel("INITIALIZING RELAY...")
        self.lbl_status_pill.setStyleSheet("""
            background-color: #334155;
            color: #F8FAFC;
            font-size: 12px;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 16px;
        """)
        h_layout.addWidget(self.lbl_status_pill)

        main_layout.addWidget(header_card)

        # 2. SERVER & CLOUD RELAY INFO BAR
        relay_card = QFrame()
        relay_card.setStyleSheet("QFrame { background-color: #0F172A; border: 1px solid #1E293B; border-radius: 10px; padding: 12px; }")
        relay_layout = QHBoxLayout(relay_card)
        relay_layout.setContentsMargins(14, 8, 14, 8)

        lbl_relay_tag = QLabel("Server Endpoint for Mobile Scanner:")
        lbl_relay_tag.setStyleSheet("font-size: 13px; color: #94A3B8; font-weight: 600;")
        relay_layout.addWidget(lbl_relay_tag)

        self.txt_relay_url = QLineEdit(self.public_url)
        self.txt_relay_url.setReadOnly(True)
        self.txt_relay_url.setStyleSheet("""
            background-color: #0A0E17;
            color: #38BDF8;
            border: 1px solid #1E293B;
            border-radius: 6px;
            padding: 6px 12px;
            font-family: monospace;
            font-size: 13px;
            font-weight: bold;
        """)
        relay_layout.addWidget(self.txt_relay_url)

        btn_copy = QPushButton("Copy URL")
        btn_copy.setObjectName("btnCopy")
        btn_copy.clicked.connect(self.copy_relay_url)
        relay_layout.addWidget(btn_copy)

        main_layout.addWidget(relay_card)

        # 3. REAL-TIME OPERATOR REQUEST CARD (POPUP/CARD FOR NEW REQUESTS)
        self.card_approval = QFrame()
        self.card_approval.setStyleSheet("""
            QFrame#cardApproval {
                background-color: #1E293B;
                border: 2px solid #F59E0B;
                border-radius: 14px;
                padding: 18px;
            }
        """)
        self.card_approval.setObjectName("cardApproval")
        approval_layout = QVBoxLayout(self.card_approval)
        approval_layout.setContentsMargins(20, 16, 20, 16)
        approval_layout.setSpacing(12)

        appr_header_layout = QHBoxLayout()
        self.lbl_appr_badge = QLabel("NEW OPERATOR ACCESS REQUEST")
        self.lbl_appr_badge.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
        appr_header_layout.addWidget(self.lbl_appr_badge)
        appr_header_layout.addStretch()
        self.lbl_appr_time = QLabel("")
        self.lbl_appr_time.setStyleSheet("color: #94A3B8; font-size: 12px;")
        appr_header_layout.addWidget(self.lbl_appr_time)
        approval_layout.addLayout(appr_header_layout)

        self.lbl_operator_details = QLabel("Operator: Awaiting requests from phone...")
        self.lbl_operator_details.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        approval_layout.addWidget(self.lbl_operator_details)

        self.lbl_operator_sub = QLabel("This operator is requesting permission to upload aircraft technical logs into your OneDrive.")
        self.lbl_operator_sub.setStyleSheet("font-size: 13px; color: #CBD5E1;")
        approval_layout.addWidget(self.lbl_operator_sub)

        # Buttons Row
        btn_box = QHBoxLayout()
        btn_box.setSpacing(16)

        self.btn_approve = QPushButton("APPROVE OPERATOR (Enter)")
        self.btn_approve.setObjectName("btnApprove")
        self.btn_approve.clicked.connect(self.approve_active_operator)
        btn_box.addWidget(self.btn_approve)

        self.btn_reject = QPushButton("REJECT (Esc)")
        self.btn_reject.setObjectName("btnReject")
        self.btn_reject.clicked.connect(self.reject_active_operator)
        btn_box.addWidget(self.btn_reject)

        btn_box.addStretch()
        approval_layout.addLayout(btn_box)

        # Initially hidden until an actual request arrives
        self.card_approval.setVisible(False)
        main_layout.addWidget(self.card_approval)

        # 4. RECENT SCANS TABLE & AUDIT TRAIL
        lbl_scans_title = QLabel("Recent Technical Log Scans (Uploaded to Isaac Eke's OneDrive)")
        lbl_scans_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF; margin-top: 8px;")
        main_layout.addWidget(lbl_scans_title)

        self.table_scans = QTableWidget(0, 5)
        self.table_scans.setHorizontalHeaderLabels(["Filename", "Aircraft", "Operator Email", "Upload Timestamp", "OneDrive Destination"])
        self.table_scans.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_scans.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_scans.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_scans.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_scans.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_scans.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_scans.verticalHeader().setVisible(False)
        self.table_scans.setAlternatingRowColors(True)
        self.table_scans.setStyleSheet("QTableWidget { alternate-background-color: #121826; }")
        main_layout.addWidget(self.table_scans)

        self.setCentralWidget(central)

    # -------------------------------------------------------------------------
    # KEYBOARD SHORTCUTS
    # -------------------------------------------------------------------------
    def setup_shortcuts(self):
        # Enter/Return approves active operator
        sc_return = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        sc_return.activated.connect(self.approve_active_operator)

        sc_enter = QShortcut(QKeySequence(Qt.Key.Key_Enter), self)
        sc_enter.activated.connect(self.approve_active_operator)

        # Esc rejects active operator
        sc_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        sc_esc.activated.connect(self.reject_active_operator)

        # Ctrl+R refreshes
        sc_refresh = QShortcut(QKeySequence("Ctrl+R"), self)
        sc_refresh.activated.connect(self.poll_database)

    # -------------------------------------------------------------------------
    # BACKEND PROCESS MANAGEMENT
    # -------------------------------------------------------------------------
    def start_local_backend(self):
        log_event("INFO", "Checking local backend process...")
        try:
            # Launch FastAPI backend process via uvicorn if not already active
            backend_script = BACKEND_DIR / "main.py"
            cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
            self.backend_process = subprocess.Popen(
                cmd,
                cwd=str(BACKEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            log_event("INFO", "Local backend process launched on port 8000.")
        except Exception as e:
            log_event("ERROR", f"Failed to start local backend: {e}")

    # -------------------------------------------------------------------------
    # CLOUD RELAY TUNNEL MANAGEMENT
    # -------------------------------------------------------------------------
    def start_tunnel(self):
        self.tunnel_worker = TunnelWorker(8000)
        self.tunnel_worker.tunnel_ready.connect(self.on_tunnel_ready)
        self.tunnel_worker.tunnel_failed.connect(self.on_tunnel_failed)
        self.tunnel_worker.start()

    def on_tunnel_ready(self, url: str):
        self.public_url = url
        self.txt_relay_url.setText(url)
        self.lbl_status_pill.setText("ONLINE (INTERNET RELAY ACTIVE)")
        self.lbl_status_pill.setStyleSheet("""
            background-color: #064E3B;
            color: #34D399;
            border: 1px solid #10B981;
            font-size: 12px;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 16px;
        """)
        log_event("INFO", f"Cloud relay ready: {url}")

    def on_tunnel_failed(self, error: str):
        self.lbl_status_pill.setText("LOCAL ONLY (PORT 8000)")
        self.lbl_status_pill.setStyleSheet("""
            background-color: #334155;
            color: #94A3B8;
            font-size: 12px;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 16px;
        """)
        log_event("WARNING", f"Tunnel failed: {error}. Falling back to local backend.")

    def copy_relay_url(self):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.public_url)
            self.lbl_status_pill.setText("URL COPIED!")
            QTimer.singleShot(2000, lambda: self.lbl_status_pill.setText("ONLINE (INTERNET RELAY ACTIVE)"))

    # -------------------------------------------------------------------------
    # REAL-TIME DATABASE POLLING & OPERATOR APPROVAL LOGIC
    # -------------------------------------------------------------------------
    def poll_database(self):
        if not DB_PATH.exists():
            return

        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row

            # 1. Check for PENDING operators
            pending_row = conn.execute(
                "SELECT email, name, registered_at FROM operators WHERE status = 'PENDING' ORDER BY registered_at DESC LIMIT 1"
            ).fetchone()

            if pending_row:
                email = pending_row["email"]
                name = pending_row["name"] or "Operator"
                req_time = pending_row["registered_at"] or ""

                if self.active_pending_operator != email:
                    self.active_pending_operator = email
                    self.lbl_operator_details.setText(f"Operator: {name} ({email})")
                    self.lbl_appr_time.setText(f"Requested: {req_time[:19]}")
                    self.card_approval.setVisible(True)
                    QApplication.beep()
                    log_event("INFO", f"Active approval request displayed for: {email}")
            else:
                if self.active_pending_operator is not None:
                    self.active_pending_operator = None
                    self.card_approval.setVisible(False)

            # 2. Refresh Scans Table
            scans = conn.execute(
                "SELECT filename, aircraft, operator_email, uploaded_at, destination_path FROM scans ORDER BY id DESC LIMIT 50"
            ).fetchall()

            if self.table_scans.rowCount() != len(scans):
                self.table_scans.setRowCount(len(scans))
                for row_idx, scan in enumerate(scans):
                    self.table_scans.setItem(row_idx, 0, QTableWidgetItem(str(scan["filename"])))
                    self.table_scans.setItem(row_idx, 1, QTableWidgetItem(str(scan["aircraft"])))
                    self.table_scans.setItem(row_idx, 2, QTableWidgetItem(str(scan["operator_email"])))
                    self.table_scans.setItem(row_idx, 3, QTableWidgetItem(str(scan["uploaded_at"][:19])))
                    self.table_scans.setItem(row_idx, 4, QTableWidgetItem(str(scan["destination_path"])))

            conn.close()

        except Exception as e:
            log_event("ERROR", f"Database poll error: {e}")

    def approve_active_operator(self):
        if not self.active_pending_operator:
            return

        email = self.active_pending_operator
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("UPDATE operators SET status = 'APPROVED', approved_at = ? WHERE email = ?", (now, email))
            conn.commit()
            conn.close()

            log_event("INFO", f"Human approval granted for operator: {email}")
            self.lbl_operator_details.setText(f"APPROVED: {email} now has full upload access!")
            self.card_approval.setStyleSheet("""
                QFrame#cardApproval {
                    background-color: #064E3B;
                    border: 2px solid #10B981;
                    border-radius: 14px;
                    padding: 18px;
                }
            """)
            self.lbl_appr_badge.setText("OPERATOR APPROVED")
            self.lbl_appr_badge.setStyleSheet("color: #34D399; font-size: 13px; font-weight: 800;")
            self.btn_approve.setEnabled(False)
            self.btn_reject.setEnabled(False)

            # Auto-dismiss card after 3 seconds
            QTimer.singleShot(3000, self.reset_approval_card)

        except Exception as e:
            log_event("ERROR", f"Failed to approve operator {email}: {e}")

    def reject_active_operator(self):
        if not self.active_pending_operator:
            return

        email = self.active_pending_operator
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("UPDATE operators SET status = 'REJECTED' WHERE email = ?", (email,))
            conn.commit()
            conn.close()

            log_event("INFO", f"Operator rejected: {email}")
            self.lbl_operator_details.setText(f"REJECTED: {email} access has been blocked.")
            self.card_approval.setStyleSheet("""
                QFrame#cardApproval {
                    background-color: #450A0A;
                    border: 2px solid #EF4444;
                    border-radius: 14px;
                    padding: 18px;
                }
            """)
            self.lbl_appr_badge.setText("OPERATOR REJECTED")
            self.lbl_appr_badge.setStyleSheet("color: #F87171; font-size: 13px; font-weight: 800;")
            self.btn_approve.setEnabled(False)
            self.btn_reject.setEnabled(False)

            QTimer.singleShot(2500, self.reset_approval_card)

        except Exception as e:
            log_event("ERROR", f"Failed to reject operator {email}: {e}")

    def reset_approval_card(self):
        self.active_pending_operator = None
        self.btn_approve.setEnabled(True)
        self.btn_reject.setEnabled(True)
        self.card_approval.setVisible(False)
        self.card_approval.setStyleSheet("""
            QFrame#cardApproval {
                background-color: #1E293B;
                border: 2px solid #F59E0B;
                border-radius: 14px;
                padding: 18px;
            }
        """)
        self.lbl_appr_badge.setText("NEW OPERATOR ACCESS REQUEST")
        self.lbl_appr_badge.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: 800;")

    # -------------------------------------------------------------------------
    # CLEAN SHUTDOWN
    # -------------------------------------------------------------------------
    def closeEvent(self, event):
        log_event("INFO", "Closing Enugu Air Control Center...")
        if self.tunnel_worker:
            self.tunnel_worker.stop()
        if self.backend_process:
            try:
                self.backend_process.terminate()
            except Exception:
                pass
        event.accept()

# -----------------------------------------------------------------------------
# APPLICATION ENTRYPOINT
# -----------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette setup
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(10, 14, 23))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(241, 245, 249))
    palette.setColor(QPalette.ColorRole.Base, QColor(18, 24, 38))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(15, 23, 42))
    palette.setColor(QPalette.ColorRole.Text, QColor(241, 245, 249))
    palette.setColor(QPalette.ColorRole.Button, QColor(30, 41, 59))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(248, 250, 252))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(56, 189, 248))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(8, 47, 73))
    app.setPalette(palette)

    window = ControlCenterWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
