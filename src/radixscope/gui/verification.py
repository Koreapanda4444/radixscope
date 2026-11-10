"""Exercise desktop integration without writing to the user's settings."""

import json
import os
import tempfile
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication

from radixscope.gui.app import MainWindow, create_application
from radixscope.gui.byte_inspector import ByteInspectorWorkspace
from radixscope.gui.conversion import ConversionWorkspace
from radixscope.gui.i18n import localize, tr
from radixscope.gui.preferences import PreferencesDialog
from radixscope.gui.widgets import Workspace
from radixscope.settings import SettingsStore


def _settle(workspace: Workspace, application: QApplication) -> None:
    deadline = time.monotonic() + 30
    while workspace.job is not None:
        application.processEvents()
        if time.monotonic() >= deadline:
            workspace.cancel_calculation()
            raise RuntimeError(f"desktop calculation timed out: {workspace.title}")
        time.sleep(0.01)
    application.processEvents()


def verify_desktop() -> dict[str, object]:
    application = create_application()
    assert not application.windowIcon().isNull(), "application icon is unavailable"
    calculations = 0
    with tempfile.TemporaryDirectory(prefix="radixscope-check-") as directory:
        store = SettingsStore(Path(directory) / "state.json")
        store.preferences["language"] = "en"
        window = MainWindow(store)
        try:
            window.show()
            for language in ("en", "ko", "en"):
                before = [workspace.snapshot() for workspace in window.workspaces]
                store.preferences["language"] = language
                window.apply_language()
                assert before == [workspace.snapshot() for workspace in window.workspaces]
                for index, workspace in enumerate(window.workspaces):
                    window.tabs.setCurrentIndex(index)
                    window.resize(640, 480)
                    application.processEvents()
                    assert window.width() <= 640, (workspace.title, window.width())
                    workspace.start_calculation()
                    _settle(workspace, application)
                    assert workspace.current_report() is not None, (
                        workspace.title, workspace.error.text()
                    )
                    assert workspace.status.text() == tr("Complete")
                    calculations += 1

            conversion = window.workspaces[0]
            assert isinstance(conversion, ConversionWorkspace)
            conversion.mode.setCurrentText("Auto")
            conversion.input.setText("0xFF + 1")
            conversion.start_calculation()
            state = conversion.snapshot()
            store.preferences["language"] = "ko"
            window.apply_language()
            assert conversion.snapshot() == state
            assert conversion.mode.currentText() == "Auto"
            assert conversion.mode.itemText(conversion.mode.currentIndex()) == "자동"
            _settle(conversion, application)
            report = conversion.current_report()
            assert report is not None and str(report["exact"]) == "256"
            calculations += 1
            assert conversion.run_button.text() == "변환"
            assert conversion.output.toPlainText() != conversion._english_report

            conversion.mode.setCurrentText("Expression")
            conversion.input.setText("1 / 0")
            conversion.start_calculation()
            _settle(conversion, application)
            assert conversion.current_report() is None
            assert conversion.status.text() == "오류"
            assert "0으로" in conversion.error.text()
            assert conversion.input.cursorPosition() <= len(conversion.input.text())

            byte_workspace = window.workspaces[5]
            assert isinstance(byte_workspace, ByteInspectorWorkspace)
            byte_workspace.input_format.setCurrentText("utf8")
            byte_workspace.input.setPlainText("입력 Auto true")
            byte_workspace.start_calculation()
            _settle(byte_workspace, application)
            assert byte_workspace.current_report() is not None, byte_workspace.error.text()
            assert byte_workspace.input.toPlainText() == "입력 Auto true"
            calculations += 1

            conversion.input.setText("1/99991")
            conversion.start_calculation()
            conversion.cancel_calculation()
            application.processEvents()
            assert conversion.job is None and conversion.current_report() is None
            assert conversion.status.text() == "취소됨"
            dialog = PreferencesDialog(store, window)
            localize(dialog)
            assert dialog.language.currentData() == "ko"
            dialog.theme.setCurrentText("Dark")
            assert dialog.theme.currentText() == "Dark"
            assert dialog.theme.itemText(dialog.theme.currentIndex()) == "다크"
            dialog.close()
            window.save_preferences()
            restored = SettingsStore(store.path)
            assert restored.preferences["language"] == "ko"
            assert restored.preferences["workspaces"] == store.preferences["workspaces"]
            window.history_search.setText("변환")
            assert window.displayed_history()
        finally:
            window.close()
            application.processEvents()
    return {"status": "ok", "workspaces": 8, "calculations": calculations,
            "languages": ["en", "ko"], "cancellation": True, "settings": True}


def main() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    print(json.dumps(verify_desktop(), ensure_ascii=True))


if __name__ == "__main__":
    main()
