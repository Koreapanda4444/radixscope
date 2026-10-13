import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from radixscope.gui.app import MainWindow
from radixscope.gui.conversion import ConversionWorkspace
from radixscope.gui.preferences import PreferencesDialog
from radixscope.settings import SettingsStore
from tests.conftest import wait_for_workspace


def test_history_is_bounded_deduplicated_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "state.json"
    store = SettingsStore(path)
    store.preferences.update({"history_limit": 2, "theme": "Dark"})
    for value in ("1", "2", "3", "2"):
        store.record("Conversion", {"input": value}, value)
    assert [entry["summary"] for entry in store.history] == ["2", "3"]
    store.save()
    restored = SettingsStore(path)
    assert restored.preferences == store.preferences and restored.history == store.history
    assert list(path.parent.glob("*.tmp")) == []
    restored.preferences["remember_history"] = False
    restored.record("Conversion", {"input": "4"}, "4")
    assert len(restored.history) == 2
    restored.history.clear()
    restored.save()
    assert SettingsStore(path).history == []


@pytest.mark.parametrize(
    "content", ["broken", "[]", '{"schema": 2}', '{"schema": true}', '{"schema": 1, "history": {}}']
)
def test_corrupt_settings_fall_back_without_blocking_startup(tmp_path: Path, content: str) -> None:
    path = tmp_path / "state.json"
    path.write_text(content, encoding="utf-8")
    store = SettingsStore(path)
    assert store.warning and store.preferences == {} and store.history == []


def test_invalid_history_entries_and_limits_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"schema": 1, "history": [None, {}, "invalid"]}), encoding="utf-8")
    store = SettingsStore(path)
    assert store.history == []
    for limit in (True, 0, 101, "2", 1.5):
        store.preferences["history_limit"] = limit
        assert store.history_limit == 20


def test_failed_atomic_save_preserves_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "state.json"
    store = SettingsStore(path)
    store.save()
    original = path.read_bytes()

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("write denied")

    monkeypatch.setattr("radixscope.settings.os.replace", fail_replace)
    store.record("Conversion", {"input": "1"}, "1")
    with pytest.raises(OSError, match="write denied"):
        store.save()
    assert path.read_bytes() == original
    assert list(tmp_path.glob("*.tmp")) == []


def test_recent_input_restoration_and_persisted_workspace_options(
    qt_app: QApplication, tmp_path: Path
) -> None:
    path = tmp_path / "state.json"
    window = MainWindow(SettingsStore(path))
    conversion = window.workspaces[0]
    assert isinstance(conversion, ConversionWorkspace)
    conversion.input.setText("FF")
    conversion.source_base.setValue(16)
    conversion.run_button.click()
    wait_for_workspace(conversion, qt_app)
    assert window.recent.count() == 1
    conversion.input.setText("0")
    window.recent.setCurrentRow(0)
    window.restore_recent()
    assert conversion.input.text() == "FF"
    assert conversion.source_base.value() == 16
    assert "restored" in window.statusBar().currentMessage().lower()
    window.store.preferences["theme"] = "Dark"
    window.apply_theme()
    assert window.palette().window().color().name() == "#20242b"
    window.close()
    reopened = MainWindow(SettingsStore(path))
    restored = reopened.workspaces[0]
    assert isinstance(restored, ConversionWorkspace)
    assert restored.input.text() == "FF" and restored.source_base.value() == 16
    assert reopened.recent.count() == 1
    reopened.clear_history()
    assert SettingsStore(path).history == []
    reopened.close()


def test_workspace_restore_rejects_invalid_control_values(qt_app: QApplication) -> None:
    workspace = ConversionWorkspace()
    workspace.restore_state({
        "source_base": True, "precision": -1, "rounding": "unknown", "input": 2
    })
    assert workspace.source_base.value() == 10 and workspace.precision.value() == 16
    assert workspace.input.text() == "255" and workspace.rounding.currentText() == "half-even"
    workspace.close()


def test_preferences_dialog_reflects_saved_choices(qt_app: QApplication, tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "state.json")
    store.preferences.update({"history_limit": 5, "remember_history": False, "theme": "Light"})
    parent = MainWindow(store)
    dialog = PreferencesDialog(store, parent)
    assert dialog.limit.value() == 5 and not dialog.remember.isChecked()
    assert dialog.theme.currentText() == "Light"
    dialog.close()
    parent.close()
