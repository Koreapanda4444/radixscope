"""Exercise desktop integration without writing to the user's settings."""

import json
import os
import tempfile
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication

from radixscope import __version__
from radixscope.core import BitField, BitfieldLayout, ExactValue
from radixscope.gui.app import MainWindow, create_application
from radixscope.gui.byte_inspector import ByteInspectorWorkspace
from radixscope.gui.comparison import ComparisonWorkspace
from radixscope.gui.conversion import ConversionWorkspace
from radixscope.gui.i18n import localize, tr
from radixscope.gui.inspector import InspectorWorkspace
from radixscope.gui.preferences import PreferencesDialog
from radixscope.gui.programmer import IEEEWorkspace
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
                assert window._navigation_items[3].text(0) == "IEEE 754"
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

            inspector = window.workspaces[4]
            assert isinstance(inspector, InspectorWorkspace)
            conversion._destination.setCurrentText("Number Inspector")
            conversion._transfer_mode.setCurrentText("Numeric value")
            conversion._transfer_button.click()
            _settle(inspector, application)
            transferred = inspector.current_report()
            assert transferred is not None and str(transferred["exact"]) == "256"
            calculations += 1

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

            inspector.base.setValue(16)
            inspector.bit_width.setValue(8)
            inspector.signed.setChecked(True)
            inspector.pattern.setChecked(True)
            inspector.input.setText("80")
            inspector.start_calculation()
            _settle(inspector, application)
            inspected = inspector.current_report()
            assert inspected is not None and str(inspected["exact"]) == "-128"
            calculations += 1
            inspector.bit_editor.toggle_bit(0)
            inspected = inspector.current_report()
            assert inspected is not None and str(inspected["exact"]) == "-127"
            inspector.raw_hex.setText("7F")
            inspector.raw_hex.setModified(True)
            inspector.raw_hex.editingFinished.emit()
            inspected = inspector.current_report()
            assert inspected is not None and str(inspected["exact"]) == "127"

            byte_workspace.input_format.setCurrentText("hex")
            byte_workspace.input.setPlainText("FF 80")
            byte_workspace.start_calculation()
            _settle(byte_workspace, application)
            calculations += 1
            panel = byte_workspace.bitfields
            panel.fields.setRowCount(0)
            panel.add_field(BitField("low", 0, 8, True))
            panel.add_field(BitField("high", 8, 8))
            panel.analyze()
            assert not panel.error.text(), panel.error.text()
            item = panel.values.item(0, 1)
            assert item is not None and item.text() == "-128"
            layout = BitfieldLayout(16, panel.field_definitions())
            assert BitfieldLayout.from_json(layout.to_json()) == layout
            byte_workspace._show_fields.setChecked(True)
            panel.bits.toggle_bit(0)
            _settle(byte_workspace, application)
            assert byte_workspace.input.toPlainText() == "FF 81"
            item = panel.values.item(0, 1)
            assert item is not None and item.text() == "-127"
            calculations += 1

            comparison = window.workspaces[6]
            assert isinstance(comparison, ComparisonWorkspace)
            comparison.input.setPlainText("FF 80")
            comparison.other_input.setPlainText("FF 81")
            comparison.restore_state({"layout": layout.to_json()})
            comparison.start_calculation()
            _settle(comparison, application)
            difference = comparison.current_report()
            assert difference is not None and difference["changed_bits"] == 1
            assert difference["changed_bytes"] == 1
            calculations += 1

            ieee = window.workspaces[3]
            assert isinstance(ieee, IEEEWorkspace)
            ieee.mode.setCurrentText("encode")
            ieee.bit_width.setCurrentText("16")
            assert ieee.bit_width.currentText() == "16"
            ieee.input.setText("0.1")
            ieee.calculate()
            _settle(ieee, application)
            floating = ieee.current_report()
            assert floating is not None
            assert len(str(floating["bits"])) == 16
            pattern = int(str(floating["bits"]), 2)
            ieee.float_navigator.next.click()
            floating = ieee.current_report()
            assert floating is not None and int(str(floating["bits"]), 2) == pattern + 1
            assert ieee.mode.currentText() == "decode"
            calculations += 1
            ieee.mode.setCurrentText("encode")
            ieee.input.setText("0.1")
            ieee.compare_formats()
            _settle(ieee, application)
            floating = ieee.current_report()
            assert floating is not None
            rows = floating.get("comparison")
            assert isinstance(rows, list) and len(rows) == 4
            calculations += 1

            conversion.input.setText("1/7")
            conversion.start_calculation()
            conversion.input.setText("2")
            application.processEvents()
            assert conversion.job is None and conversion.current_report() is None
            conversion.start_calculation()
            _settle(conversion, application)
            latest = conversion.current_report()
            assert latest is not None and latest["exact"] == str(ExactValue(2))
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
            saved = store.path.read_bytes()
            original_path = store.path
            store.path = original_path / "cannot-write.json"
            try:
                window.save_preferences()
                assert original_path.read_bytes() == saved
                assert "설정을 저장할 수 없습니다" in window.statusBar().currentMessage()
            finally:
                store.path = original_path
            window.history_search.setText("변환")
            assert window.displayed_history()
        finally:
            window.close()
            application.processEvents()
    return {"status": "ok", "version": __version__, "workspaces": 8, "calculations": calculations,
            "languages": ["en", "ko"], "cancellation": True, "settings": True,
            "editing": True, "transfer": True, "stale_result": True, "save_failure": True}


def main() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    print(json.dumps(verify_desktop(), ensure_ascii=True))


if __name__ == "__main__":
    main()
