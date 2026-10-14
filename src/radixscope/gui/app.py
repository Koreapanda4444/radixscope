import sys
from functools import partial
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from radixscope import __version__
from radixscope.gui.conversion import ConversionWorkspace, TraceWorkspace
from radixscope.gui.preferences import PreferencesDialog
from radixscope.gui.programmer import IEEEWorkspace, ProgrammerWorkspace
from radixscope.gui.widgets import Workspace
from radixscope.settings import SettingsStore


def default_state_path() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(location) / "state.json"


class MainWindow(QMainWindow):
    def __init__(self, store: SettingsStore | None = None) -> None:
        super().__init__()
        self.store = store if store is not None else SettingsStore(default_state_path())
        self.system_palette = QPalette(self.palette())
        self.setWindowTitle(f"RadixScope {__version__}")
        self.resize(1000, 720)
        self.setMinimumSize(640, 480)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.workspaces: list[Workspace] = [
            ConversionWorkspace(),
            TraceWorkspace(),
            ProgrammerWorkspace(),
            IEEEWorkspace(),
        ]
        for index, workspace in enumerate(self.workspaces):
            self.tabs.addTab(workspace, workspace.title)
            action = QAction(workspace.title, self)
            action.setShortcut(QKeySequence(f"Ctrl+{index + 1}"))
            action.triggered.connect(partial(self.tabs.setCurrentIndex, index))
            self.addAction(action)
            workspace.result_ready.connect(self.show_completed)
        self.setCentralWidget(self.tabs)
        self.recent = QListWidget()
        self.recent.itemDoubleClicked.connect(self.restore_recent)
        restore = QPushButton("Restore selected input")
        restore.clicked.connect(self.restore_recent)
        clear = QPushButton("Clear history")
        clear.clicked.connect(self.clear_history)
        recent_container = QWidget()
        recent_layout = QVBoxLayout(recent_container)
        recent_layout.addWidget(self.recent)
        recent_layout.addWidget(restore)
        recent_layout.addWidget(clear)
        self.recent_dock = QDockWidget("Recent", self)
        self.recent_dock.setWidget(recent_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.recent_dock)
        settings_action = QAction("Preferences", self)
        settings_action.triggered.connect(self.edit_preferences)
        menu = self.menuBar().addMenu("Settings")
        menu.addAction(settings_action)
        menu.addAction(self.recent_dock.toggleViewAction())
        self.statusBar().showMessage("Ready · Ctrl+1 through Ctrl+4 switch workspaces")
        self.base_stylesheet = (
            "QWidget { font-size: 13px; }"
            "QLabel#heading { font-size: 22px; font-weight: 600; margin-top: 8px; }"
            "QLabel#error { color: #d34a4a; }"
            "QPushButton { padding: 7px 14px; }"
            "QLineEdit, QSpinBox, QComboBox { padding: 5px; }"
            "QTabWidget::pane { border: 0; }"
        )
        self.restore_preferences()
        self.refresh_history()
        if self.store.warning:
            self.statusBar().showMessage(self.store.warning)

    def show_completed(self, title: str, report: dict[str, object]) -> None:
        workspace = next(workspace for workspace in self.workspaces if workspace.title == title)
        summary = report.get("exact")
        if summary is None:
            summary = report.get("value")
        if summary is None:
            summary = report.get("classification", "")
        self.store.record(title, workspace.snapshot(), str(summary))
        self.refresh_history()
        self.statusBar().showMessage(f"{title} complete", 5000)
        self.save_preferences()

    def refresh_history(self) -> None:
        self.recent.clear()
        for entry in self.store.history:
            state = entry["state"]
            text = str(state.get("input", "")) if isinstance(state, dict) else ""
            self.recent.addItem(f"{entry['workspace']} · {text[:50]} → {entry['summary']}")

    def restore_recent(self) -> None:
        index = self.recent.currentRow()
        if not 0 <= index < len(self.store.history):
            return
        entry = self.store.history[index]
        state = entry["state"]
        if not isinstance(state, dict):
            return
        for index, workspace in enumerate(self.workspaces):
            if workspace.title == entry["workspace"]:
                workspace.restore_state(state)
                self.tabs.setCurrentIndex(index)
                self.statusBar().showMessage("Input restored · Run to calculate", 5000)
                return

    def clear_history(self) -> None:
        self.store.history.clear()
        self.refresh_history()
        self.save_preferences()

    def restore_preferences(self) -> None:
        states = self.store.preferences.get("workspaces")
        if isinstance(states, dict):
            for workspace in self.workspaces:
                state = states.get(workspace.title)
                if isinstance(state, dict):
                    workspace.restore_state(state)
        tab = self.store.preferences.get("active_tab", 0)
        if isinstance(tab, int) and not isinstance(tab, bool) and 0 <= tab < self.tabs.count():
            self.tabs.setCurrentIndex(tab)
        dimensions = (("window_width", self.resize_width), ("window_height", self.resize_height))
        for name, setter in dimensions:
            value = self.store.preferences.get(name)
            if isinstance(value, int) and not isinstance(value, bool) and 480 <= value <= 3000:
                setter(value)
        self.apply_theme()

    def resize_width(self, value: int) -> None:
        self.resize(value, self.height())

    def resize_height(self, value: int) -> None:
        self.resize(self.width(), value)

    def save_preferences(self) -> None:
        self.store.preferences.update({
            "active_tab": self.tabs.currentIndex(),
            "window_width": self.width(), "window_height": self.height(),
            "workspaces": {workspace.title: workspace.snapshot() for workspace in self.workspaces},
        })
        try:
            self.store.save()
        except (OSError, ValueError) as error:
            self.statusBar().showMessage(f"Could not save preferences: {error}")

    def edit_preferences(self) -> None:
        dialog = PreferencesDialog(self.store, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.preferences.update({
                "theme": dialog.theme.currentText(),
                "remember_history": dialog.remember.isChecked(),
                "history_limit": dialog.limit.value(),
            })
            del self.store.history[self.store.history_limit:]
            self.apply_theme()
            self.refresh_history()
            self.save_preferences()

    def apply_theme(self) -> None:
        theme = self.store.preferences.get("theme", "System")
        palette = QPalette(self.system_palette)
        stylesheet = self.base_stylesheet
        if theme in ("Dark", "Light"):
            dark = theme == "Dark"
            background = "#20242b" if dark else "#f5f6f8"
            foreground = "#e8edf3" if dark else "#17202b"
            base = "#151920" if dark else "#ffffff"
            for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Button):
                palette.setColor(role, QColor(background))
            text_roles = (
                QPalette.ColorRole.WindowText,
                QPalette.ColorRole.Text,
                QPalette.ColorRole.ButtonText,
            )
            for role in text_roles:
                palette.setColor(role, QColor(foreground))
            palette.setColor(QPalette.ColorRole.Base, QColor(base))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#3676c8"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            border = "#495261" if dark else "#b7c0cc"
            stylesheet += f"QWidget {{ color: {foreground}; background-color: {background}; }}"
            stylesheet += (
                "QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QListWidget {"
                f"background-color: {base}; color: {foreground}; border: 1px solid {border}; }}"
                "QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled { color: #8793a3; }"
                f"QTabBar::tab:selected {{ background-color: {base}; }}"
            )
        self.setPalette(palette)
        self.setStyleSheet(stylesheet)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.shutdown()
        self.save_preferences()
        super().closeEvent(event)

    def shutdown(self) -> None:
        for workspace in self.workspaces:
            workspace.cancel_calculation()


def create_application() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    application = QApplication(sys.argv)
    application.setApplicationName("RadixScope")
    application.setOrganizationName("Koreapanda4444")
    application.setApplicationVersion(__version__)
    icon = Path(__file__).resolve().parents[1] / "assets/radixscope.svg"
    application.setWindowIcon(QIcon(str(icon)))
    return application


def run() -> int:
    application = create_application()
    window = MainWindow()
    application.aboutToQuit.connect(window.shutdown)
    window.show()
    return application.exec()
