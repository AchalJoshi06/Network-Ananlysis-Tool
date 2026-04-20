"""
Desktop wrapper for the Flask Network Analysis Tool.

Runs the Flask app on localhost and embeds it in a PyQt6 window using QWebEngineView.
"""

import json
import logging
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from werkzeug.serving import make_server

import app as flask_dashboard


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("desktop_app")

SETTINGS_FILE = Path(__file__).with_name("desktop_settings.json")
DEFAULT_SETTINGS = {
    "preferred_port": 5000,
    "auto_start_monitoring": False,
    "log_level": "INFO",
}


def load_settings() -> dict:
    """Load desktop settings from disk with sane defaults."""
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return DEFAULT_SETTINGS.copy()

        settings = DEFAULT_SETTINGS.copy()
        settings.update(raw)
        settings["preferred_port"] = int(settings.get("preferred_port", 5000))
        settings["auto_start_monitoring"] = bool(settings.get("auto_start_monitoring", False))
        settings["log_level"] = str(settings.get("log_level", "INFO")).upper()
        if settings["log_level"] not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            settings["log_level"] = "INFO"
        return settings
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """Persist desktop settings to disk."""
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def set_log_level(level_name: str) -> None:
    """Set desktop logger verbosity from settings."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logger.setLevel(level)


def find_free_port(preferred_port: int = 5000) -> int:
    """Return preferred_port if available, otherwise ask OS for an ephemeral free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if sock.connect_ex(("127.0.0.1", preferred_port)) != 0:
            return preferred_port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def is_server_ready(url: str, timeout: float = 0.75) -> bool:
    """Check if the Flask dashboard is responding."""
    try:
        req = urllib.request.Request(url=f"{url}/api/status", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def start_monitoring(base_url: str, timeout: float = 2.0) -> tuple[bool, str]:
    """Attempt to call dashboard start endpoint."""
    try:
        req = urllib.request.Request(url=f"{base_url}/api/start", method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="ignore")
            payload = json.loads(body) if body else {}
            if payload.get("success"):
                return True, "Monitoring started automatically"
            return False, payload.get("message", "Monitoring was not started")
    except Exception as exc:
        return False, f"Auto-start failed: {exc}"


class SettingsDialog(QDialog):
    """Simple desktop settings dialog."""

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desktop Settings")
        self.setModal(True)
        self.resize(420, 220)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(int(current_settings.get("preferred_port", 5000)))

        self.auto_start_checkbox = QCheckBox("Automatically start monitoring after app launch")
        self.auto_start_checkbox.setChecked(bool(current_settings.get("auto_start_monitoring", False)))

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        current_level = str(current_settings.get("log_level", "INFO")).upper()
        index = self.log_level_combo.findText(current_level)
        self.log_level_combo.setCurrentIndex(index if index >= 0 else 1)

        form.addRow("Preferred port", self.port_input)
        form.addRow("Log level", self.log_level_combo)
        form.addRow("Monitoring", self.auto_start_checkbox)

        note = QLabel("Port changes apply next launch. If occupied, a free port is selected automatically.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #555;")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(note)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def get_settings(self) -> dict:
        """Return sanitized settings payload."""
        return {
            "preferred_port": int(self.port_input.value()),
            "auto_start_monitoring": bool(self.auto_start_checkbox.isChecked()),
            "log_level": self.log_level_combo.currentText(),
        }


class FlaskServerThread(threading.Thread):
    """Runs Flask app in a background thread with explicit shutdown control."""

    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self._server = make_server(self.host, self.port, flask_dashboard.app, threaded=True)

    def run(self) -> None:
        logger.info("Starting embedded Flask server on http://%s:%s", self.host, self.port)
        self._server.serve_forever()

    def shutdown(self) -> None:
        logger.info("Shutting down embedded Flask server")
        self._server.shutdown()

        # Stop monitor thread if the dashboard started monitoring.
        if flask_dashboard.monitoring_state.get("is_running"):
            try:
                flask_dashboard.monitor.stop_monitoring()
                flask_dashboard.monitoring_state["is_running"] = False
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Monitor shutdown warning: %s", exc)


class LoadingScreen(QWidget):
    """Simple loading panel displayed while Flask initializes."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(14)

        title = QLabel("Network Analysis Tool")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 700;")

        subtitle = QLabel("Starting local dashboard server...")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #444;")

        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setTextVisible(False)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(progress)
        layout.addStretch(1)

        self.setLayout(layout)


class DesktopWindow(QMainWindow):
    """Main desktop window that hosts the web dashboard."""

    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        set_log_level(self.settings.get("log_level", "INFO"))

        self.setWindowTitle("Network Analysis Tool")
        self.resize(1200, 800)

        self.host = "127.0.0.1"
        self.port = find_free_port(int(self.settings.get("preferred_port", 5000)))
        self.base_url = f"http://{self.host}:{self.port}"
        self.start_deadline = time.time() + 25
        self.autostart_attempted = False

        self.server_thread = FlaskServerThread(self.host, self.port)

        self.stack = QStackedWidget()
        self.loading_screen = LoadingScreen()
        self.browser = QWebEngineView()
        self.browser.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self.stack.addWidget(self.loading_screen)
        self.stack.addWidget(self.browser)
        self.setCentralWidget(self.stack)

        self.readiness_timer = QTimer(self)
        self.readiness_timer.setInterval(250)
        self.readiness_timer.timeout.connect(self._check_server_ready)

        self._create_menu()
        self.statusBar().showMessage(f"Local server target: {self.base_url}", 7000)

        self._start_server()

    def _create_menu(self) -> None:
        menu_bar = self.menuBar()
        app_menu = menu_bar.addMenu("App")

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._open_settings_dialog)
        app_menu.addAction(settings_action)

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        previous_port = int(self.settings.get("preferred_port", 5000))
        previous_auto = bool(self.settings.get("auto_start_monitoring", False))

        self.settings = dialog.get_settings()
        save_settings(self.settings)
        set_log_level(self.settings.get("log_level", "INFO"))

        if self.settings.get("auto_start_monitoring") and not previous_auto and is_server_ready(self.base_url):
            success, message = start_monitoring(self.base_url)
            if success:
                self.statusBar().showMessage(message, 7000)
            else:
                self.statusBar().showMessage(message, 7000)

        if int(self.settings.get("preferred_port", 5000)) != previous_port:
            QMessageBox.information(
                self,
                "Settings Saved",
                "Preferred port saved. Restart the desktop app to apply this change.",
            )
        else:
            self.statusBar().showMessage("Desktop settings saved", 5000)

    def _start_server(self) -> None:
        logger.info("Launching desktop app with local URL: %s", self.base_url)
        self.server_thread.start()
        self.readiness_timer.start()

    def _check_server_ready(self) -> None:
        if is_server_ready(self.base_url):
            self.readiness_timer.stop()
            self.browser.load(QUrl(self.base_url))
            self.stack.setCurrentWidget(self.browser)
            logger.info("Dashboard loaded in desktop window")
            self._try_auto_start_monitoring()
            return

        if time.time() > self.start_deadline:
            self.readiness_timer.stop()
            self._show_startup_error(
                "The local Flask server did not start in time.\n"
                "Please close this app and run desktop_app.py from a terminal to inspect logs."
            )

    def _try_auto_start_monitoring(self) -> None:
        if self.autostart_attempted:
            return
        self.autostart_attempted = True

        if not self.settings.get("auto_start_monitoring", False):
            return

        success, message = start_monitoring(self.base_url)
        if success:
            logger.info(message)
        else:
            logger.warning(message)
        self.statusBar().showMessage(message, 7000)

    def _show_startup_error(self, message: str) -> None:
        error_panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Startup Error")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #b00020;")

        body = QLabel(message)
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setStyleSheet("font-size: 14px;")

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addStretch(1)

        error_panel.setLayout(layout)
        self.stack.addWidget(error_panel)
        self.stack.setCurrentWidget(error_panel)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._shutdown_server()
        super().closeEvent(event)

    def _shutdown_server(self) -> None:
        if self.readiness_timer.isActive():
            self.readiness_timer.stop()

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.shutdown()
            self.server_thread.join(timeout=5)


def main() -> int:
    qt_app = QApplication(sys.argv)
    window = DesktopWindow()
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
