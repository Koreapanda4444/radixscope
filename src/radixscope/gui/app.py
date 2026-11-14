import ctypes
import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QStandardPaths, Qt
from PySide6.QtGui import QAction, QCloseEvent, QColor, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from radixscope import __version__
from radixscope.exports import report_json, table_csv, write_export
from radixscope.gui.batch import BatchWorkspace
from radixscope.gui.calculation import CalculationWorkspace
from radixscope.gui.conversion import ConversionWorkspace
from radixscope.gui.i18n import (
    LocalizedComboBox,
    default_language,
    localize,
    set_language,
    tr,
)
from radixscope.gui.icon import application_icon
from radixscope.gui.inspector import InspectorWorkspace
from radixscope.gui.navigation import transfer_state
from radixscope.gui.notices import show_notices
from radixscope.gui.preferences import PreferencesDialog
from radixscope.gui.widgets import Workspace
from radixscope.reports import render_report
from radixscope.settings import SettingsStore
from radixscope.workspaces import WORKSPACES, restored_workspace


def default_state_path() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(location) / "state.json"


class MainWindow(QMainWindow):
    def __init__(self, store: SettingsStore | None = None) -> None:
        super().__init__()
        self.store = store if store is not None else SettingsStore(default_state_path())
        set_language(self.store.preferences.get("language", default_language()))
        self._restoring = False
        self.system_palette = QPalette(self.palette())
        self.setWindowTitle(f"RadixScope {__version__}")
        self.setWindowIcon(application_icon())
        self.resize(1000, 720)
        self.setMinimumSize(640, 480)
        self.tabs = QStackedWidget()
        workspace_factories: dict[str, Callable[[], Workspace]] = {
            "Conversion": ConversionWorkspace, "Calculation": CalculationWorkspace,
            "Number Inspector": InspectorWorkspace,
            "Batch Conversion": BatchWorkspace,
        }
        self.workspaces = [workspace_factories[item.title]() for item in WORKSPACES]
        for index, workspace in enumerate(self.workspaces):
            self.tabs.addWidget(workspace)
            action = QAction(workspace.title, self)
            action.setShortcut(QKeySequence(f"Ctrl+{index + 1}"))
            action.triggered.connect(partial(self.tabs.setCurrentIndex, index))
            self.addAction(action)
            workspace.result_ready.connect(self.show_completed)
            workspace.transfer_requested.connect(self.receive_transfer)
        self.navigation = QTabBar()
        self.navigation.setExpanding(True)
        self.navigation.setDrawBase(False)
        self.navigation.setElideMode(Qt.TextElideMode.ElideRight)
        self.navigation.setAccessibleName("Workspaces")
        for index, definition in enumerate(WORKSPACES):
            self.navigation.addTab(definition.label)
            self.navigation.setTabToolTip(index, f"{definition.title} · Ctrl+{index + 1}")
        self.navigation.currentChanged.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.sync_navigation)
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(8, 0, 8, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.navigation)
        central_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.recent = QListWidget()
        self.recent.itemDoubleClicked.connect(self.restore_recent)
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search input, result or work type")
        self.history_search.textChanged.connect(self.refresh_history)
        self.history_kind = LocalizedComboBox()
        self.history_kind.addItem("All work types")
        self.history_kind.currentIndexChanged.connect(self.refresh_history)
        restore = QPushButton("Restore selected work")
        restore.clicked.connect(self.restore_recent)
        clear = QPushButton("Clear history")
        clear.clicked.connect(self.clear_history)
        recent_container = QWidget()
        recent_layout = QVBoxLayout(recent_container)
        recent_layout.addWidget(self.history_search)
        recent_layout.addWidget(self.history_kind)
        recent_layout.addWidget(self.recent)
        recent_layout.addWidget(restore)
        recent_layout.addWidget(clear)
        self.history_export_format = LocalizedComboBox()
        self.history_export_format.addItems(["JSON", "CSV", "Text"])
        history_export = QPushButton("Export displayed history")
        history_export.clicked.connect(self.export_history)
        recent_layout.addWidget(self.history_export_format)
        recent_layout.addWidget(history_export)
        self.recent_dock = QDockWidget("Recent", self)
        self.recent_dock.setWidget(recent_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.recent_dock)
        settings_action = QAction("Preferences", self)
        settings_action.triggered.connect(self.edit_preferences)
        menu = self.menuBar().addMenu("Settings")
        menu.addAction(settings_action)
        help_menu = self.menuBar().addMenu("Help")
        notices_action = help_menu.addAction("Open-source notices")
        notices_action.triggered.connect(lambda: show_notices(self))
        menu.addAction(self.recent_dock.toggleViewAction())
        self.recent_dock.toggleViewAction().setShortcut(QKeySequence("Ctrl+H"))
        self.show_status("Ready · Ctrl+1 through Ctrl+4 switch workspaces")
        self.restore_preferences()
        self.sync_navigation(self.tabs.currentIndex())
        self.refresh_history()
        if self.store.warning:
            self.show_status(self.store.warning)
        self.apply_language()

    def show_status(self, message: str, timeout: int = 0) -> None:
        self._status_source, self._status_timeout = message, timeout
        self.statusBar().showMessage(tr(message), timeout)

    def apply_language(self) -> None:
        language = self.store.preferences.get("language", default_language())
        self.store.preferences["language"] = "ko" if language == "ko" else "en"
        set_language(self.store.preferences["language"])
        self.refresh_history()
        localize(self)
        for workspace in self.workspaces:
            workspace.translate_ui()
        if hasattr(self, "_status_source"):
            self.statusBar().showMessage(tr(self._status_source), self._status_timeout)

    def sync_navigation(self, index: int) -> None:
        blocker = QSignalBlocker(self.navigation)
        self.navigation.setCurrentIndex(index)
        del blocker

    def show_completed(self, title: str, report: dict[str, object]) -> None:
        if self._restoring:
            return
        workspace = next(workspace for workspace in self.workspaces if workspace.title == title)
        report = workspace.current_report() or report
        summary = report.get("exact")
        if summary is None:
            summary = report.get("value")
        if summary is None:
            summary = report.get("source_exact")
        if summary is None and "processed" in report:
            summary = f"{report['processed']}/{report['total']} rows · {report['errors']} errors"
        if summary is None:
            comparison = report.get("numeric_comparison")
            summary = comparison.get("relation") if isinstance(comparison, dict) else (
                report.get("classification", "comparison")
            )
        self.store.record(title, workspace.snapshot(), str(summary), report)
        self.refresh_history()
        self.show_status(f"{title} complete", 5000)
        self.save_preferences()

    def receive_transfer(self, title: str, raw: bool, report: dict[str, object]) -> None:
        destination = next(workspace for workspace in self.workspaces if workspace.title == title)
        try:
            state = transfer_state(report, title, destination.snapshot(), raw)
        except ValueError as error:
            self.show_status(str(error), 8000)
            return
        destination.restore_state(state)
        self.tabs.setCurrentWidget(destination)
        destination.start_calculation()

    def refresh_history(self) -> None:
        self.recent.clear()
        category = self.history_kind.currentText()
        blocker = QSignalBlocker(self.history_kind)
        kinds = sorted({str(entry.get("kind", entry["workspace"])) for entry in self.store.history})
        self.history_kind.clear()
        self.history_kind.addItems(["All work types", *kinds])
        if category in kinds:
            self.history_kind.setCurrentText(category)
        del blocker
        for index, entry in self.displayed_history():
            state = entry["state"]
            text = str(state.get("input", "")) if isinstance(state, dict) else ""
            item = QListWidgetItem(
                f"{tr(str(entry['workspace']))} · {text[:50]} → {tr(str(entry['summary']))}"
            )
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.recent.addItem(item)
        localize(self.history_kind)

    def displayed_history(self) -> list[tuple[int, dict[str, object]]]:
        kind = self.history_kind.currentText()
        query = self.history_search.text().casefold().strip()
        entries = self.store.search_history("", None if kind == "All work types" else kind)
        result = []
        for index, entry in entries:
            state = entry["state"]
            assert isinstance(state, dict)
            values = (entry["workspace"], entry.get("kind", ""), entry["summary"],
                      state.get("input", ""), state.get("other_input", ""))
            text = " ".join(str(value) + " " + tr(str(value)) for value in values).casefold()
            if not query or query in text:
                result.append((index, entry))
        return result

    def restore_recent(self) -> None:
        item = self.recent.currentItem()
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or not 0 <= index < len(self.store.history):
            return
        entry = self.store.history[index]
        state = entry["state"]
        if not isinstance(state, dict):
            return
        for index, workspace in enumerate(self.workspaces):
            if workspace.title == entry["workspace"]:
                workspace.restore_state(state)
                self.tabs.setCurrentIndex(index)
                report = entry.get("report")
                if isinstance(report, dict):
                    self._restoring = True
                    try:
                        workspace.set_result(report)
                        self.show_status("Saved result restored", 5000)
                    except (ValueError, TypeError, KeyError, AssertionError):
                        workspace.invalidate_result()
                        self.show_status("Input restored · Run to calculate", 5000)
                    finally:
                        self._restoring = False
                else:
                    self.show_status("Input restored · Run to calculate", 5000)
                return

    def export_history(self) -> None:
        selected = self.history_export_format.currentText().lower()
        extension = "txt" if selected == "text" else selected
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export displayed history"), "", f"{selected.upper()} (*.{extension})"
        )
        if not path:
            return
        entries = [entry for _, entry in self.displayed_history()]
        try:
            content = report_json({"history": entries}) if selected == "json" else (
                table_csv(entries) if selected == "csv" else render_report({"history": entries})
            )
            write_export(Path(path), content)
        except (OSError, ValueError) as error:
            self.show_status(f"Could not export history: {error}")

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
        active = restored_workspace(self.store.preferences)
        self.tabs.setCurrentIndex(next(
            index for index, workspace in enumerate(self.workspaces) if workspace.title == active
        ))
        dimensions = (("window_width", self.resize_width), ("window_height", self.resize_height))
        for name, setter in dimensions:
            value = self.store.preferences.get(name)
            if isinstance(value, int) and not isinstance(value, bool) and 480 <= value <= 3000:
                setter(value)
        self.apply_theme()
        views = self.store.preferences.get("workspace_views")
        if isinstance(views, dict):
            for workspace in self.workspaces:
                workspace.restore_view_state(views.get(workspace.title))
        self.recent_dock.setVisible(self.store.preferences.get("history_visible", False) is True)

    def resize_width(self, value: int) -> None:
        self.resize(value, self.height())

    def resize_height(self, value: int) -> None:
        self.resize(self.width(), value)

    def save_preferences(self) -> None:
        self.store.preferences.update({
            "active_tab": self.tabs.currentIndex(),
            "active_workspace": self.workspaces[self.tabs.currentIndex()].title,
            "history_visible": self.recent_dock.isVisible(),
            "window_width": self.width(), "window_height": self.height(),
            "workspaces": {workspace.title: workspace.snapshot() for workspace in self.workspaces},
            "workspace_views": {workspace.title: workspace.view_state()
                                for workspace in self.workspaces},
        })
        try:
            self.store.save()
        except (OSError, ValueError) as error:
            self.show_status(f"Could not save preferences: {error}")

    def edit_preferences(self) -> None:
        dialog = PreferencesDialog(self.store, self)
        localize(dialog)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.preferences.update({
                "theme": dialog.theme.currentText(),
                "language": dialog.language.currentData(),
                "remember_history": dialog.remember.isChecked(),
                "history_limit": dialog.limit.value(),
            })
            del self.store.history[self.store.history_limit:]
            self.apply_theme()
            self.apply_language()
            self.refresh_history()
            self.save_preferences()

    def apply_theme(self) -> None:
        theme = self.store.preferences.get("theme", "System")
        palette = QPalette(self.system_palette)
        dark = theme == "Dark" or (theme == "System" and palette.window().color().lightness() < 128)
        background = "#171d27" if dark else "#f3f6fa"
        foreground = "#e7edf6" if dark else "#182536"
        base = "#101620" if dark else "#ffffff"
        border = "#334258" if dark else "#c7d2e1"
        header = "#243044" if dark else "#e7eef8"
        muted = "#9eacc0" if dark else "#5d6c80"
        blue = "#3275cb"
        assets = Path(__file__).resolve().parents[1] / "assets"
        up_icon = (assets / "ui-up.svg").as_posix()
        down_icon = (assets / "ui-down.svg").as_posix()
        check_icon = (assets / "ui-check.svg").as_posix()
        for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Button):
            palette.setColor(role, QColor(background))
        for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                     QPalette.ColorRole.ButtonText):
            palette.setColor(role, QColor(foreground))
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(muted))
        palette.setColor(QPalette.ColorRole.Base, QColor(base))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(background))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(muted))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(blue))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)
        stylesheet = (
            f"QWidget {{ font-size: 13px; color: {foreground}; background-color: {background}; }}"
            "QLabel#heading { font-size: 22px; font-weight: 600; margin: 4px 0; }"
            f"QLabel#subtitle {{ color: {muted}; margin-bottom: 4px; }}"
            "QLabel#error { color: #c94e5a; }"
            f"QPushButton, QToolButton {{ border: 1px solid {border}; border-radius: 4px;"
            "padding: 5px 9px; min-height: 20px; }"
            f"QPushButton:hover, QToolButton:hover {{ border-color: {blue}; }}"
            f"QPushButton#primary {{ color: white; background-color: {blue};"
            f"border-color: {blue}; }}"
            f"QPushButton:disabled, QToolButton:disabled {{ color: {muted}; }}"
            "QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTableWidget,"
            "QTreeWidget, QListWidget {"
            f"background-color: {base}; color: {foreground}; border: 1px solid {border};"
            "border-radius: 4px; padding: 3px; }"
            f"QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {blue}; }}"
            f"QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ color: {muted}; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {muted}; }}"
            f"QCheckBox::indicator:checked {{ background-color: {blue}; border-color: {blue};"
            f'image: url("{check_icon}"); }}'
            "QSpinBox::up-button, QSpinBox::down-button { width: 15px;"
            f"background-color: {header}; border-left: 1px solid {border}; }}"
            f'QSpinBox::up-arrow {{ width: 12px; height: 8px; image: url("{up_icon}"); }}'
            "QSpinBox::down-arrow, QComboBox::down-arrow { width: 12px; height: 8px;"
            f'image: url("{down_icon}"); }}'
            "QHeaderView::section { border: 0; padding: 6px; font-weight: 600;"
            f"background-color: {header}; color: {foreground};"
            f"border-bottom: 1px solid {border}; }}"
            f"QTableWidget {{ gridline-color: {border}; alternate-background-color: {background};"
            f"selection-background-color: {blue}; selection-color: white; }}"
            "QTreeWidget { border: 0; border-radius: 0; }"
            "QTreeWidget::item { padding: 7px 4px; }"
            f"QTreeWidget::item:selected {{ background-color: {blue}; color: white; }}"
            "QTabWidget::pane { border: 0; }"
            "QTabBar::tab { padding: 6px 10px; border: 0; }"
            f"QTabBar::tab:selected {{ border-bottom: 2px solid {blue}; }}"
            f"QSplitter::handle {{ background: {border}; height: 3px; }}"
        )
        self.setStyleSheet(stylesheet)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.shutdown()
        self.save_preferences()
        super().closeEvent(event)

    def shutdown(self) -> None:
        for workspace in self.workspaces:
            workspace.cancel_calculation()


def create_application() -> QApplication:
    if sys.platform == "win32":
        # Stable identity groups source and packaged windows under the same taskbar icon.
        shell = ctypes.windll.shell32
        shell.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
        shell.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        result = shell.SetCurrentProcessExplicitAppUserModelID("Koreapanda4444.RadixScope")
        if result < 0:
            raise OSError("could not set the Windows application identity")
    existing = QApplication.instance()
    application = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    application.setApplicationName("RadixScope")
    application.setOrganizationName("Koreapanda4444")
    application.setApplicationVersion(__version__)
    application.setWindowIcon(application_icon())
    return application


def run() -> int:
    application = create_application()
    window = MainWindow()
    application.aboutToQuit.connect(window.shutdown)
    window.show()
    return application.exec()
