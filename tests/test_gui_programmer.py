from PySide6.QtWidgets import QApplication

from radixscope.gui.programmer import IEEEWorkspace, ProgrammerWorkspace
from tests.conftest import wait_for_workspace


def test_programmer_overflow_and_raw_pattern_controls(qt_app: QApplication) -> None:
    workspace = ProgrammerWorkspace()
    workspace.signed.setChecked(True)
    workspace.input.setText("127")
    workspace.operation.setCurrentText("add")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    result = workspace.output.toPlainText()
    assert "value: -128" in result
    assert "exact_result: 128" in result and "overflowed: True" in result
    workspace.operation.setCurrentText("inspect")
    assert not workspace.operand.isEnabled()
    workspace.pattern.setChecked(True)
    workspace.base.setValue(16)
    workspace.input.setText("FF")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "value: -1" in workspace.output.toPlainText()
    workspace.input.setText("100")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert workspace.error.text() and workspace.output.toPlainText() == ""
    workspace.close()


def test_shift_counts_and_signed_byte_order(qt_app: QApplication) -> None:
    workspace = ProgrammerWorkspace()
    workspace.signed.setChecked(True)
    workspace.bit_width.setValue(16)
    workspace.input.setText("-2")
    workspace.byteorder.setCurrentText("little")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "bytes: FE FF" in workspace.output.toPlainText()
    workspace.operation.setCurrentText("lshr")
    assert workspace.operand_label.text() == "Shift count (decimal)"
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "value: 32767" in workspace.output.toPlainText()
    workspace.operand.setText("-1")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert workspace.error.text()
    workspace.close()


def test_ieee_encoding_decoding_and_negative_zero(qt_app: QApplication) -> None:
    workspace = IEEEWorkspace()
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "hexadecimal: 3DCCCCCD" in workspace.output.toPlainText()
    assert "fraction: 10011001100110011001101" in workspace.output.toPlainText()
    workspace.mode.setCurrentText("decode")
    assert workspace.base.isEnabled() and not workspace.payload.isEnabled()
    workspace.input.setText("80000000")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "classification: zero" in workspace.output.toPlainText()
    assert "sign: 1" in workspace.output.toPlainText()
    workspace.mode.setCurrentText("encode")
    workspace.input.setText("0")
    workspace.negative_zero.setChecked(True)
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "hexadecimal: 80000000" in workspace.output.toPlainText()
    workspace.close()


def test_nan_payload_controls_do_not_leak_into_other_modes(qt_app: QApplication) -> None:
    workspace = IEEEWorkspace()
    workspace.input.setText("-nan")
    workspace.payload.setText("123")
    workspace.quiet.setChecked(False)
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    result = workspace.output.toPlainText()
    assert "nan_payload: 123" in result and "quiet_nan: False" in result
    assert "sign: 1" in result
    workspace.input.setText("1")
    assert not workspace.payload.isEnabled()
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "exact: 1" in workspace.output.toPlainText()
    workspace.input.setText("nan")
    workspace.payload.setText("invalid")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert workspace.error.text() and workspace.output.toPlainText() == ""
    workspace.close()


def test_integer_bit_editor_updates_signed_value_and_arithmetic_result(
    qt_app: QApplication,
) -> None:
    workspace = ProgrammerWorkspace()
    workspace.signed.setChecked(True)
    workspace.input.setText("127")
    workspace.operation.setCurrentText("add")
    workspace.calculate()
    wait_for_workspace(workspace, qt_app)
    assert workspace.bit_editor.pattern == 128
    workspace.bit_editor.buttons[0].click()
    assert "value: -127" in workspace.output.toPlainText()
    assert workspace.pattern.isChecked() and workspace.operation.currentText() == "inspect"
    assert workspace.input.text() == "129"
    workspace.bit_editor.buttons[7].click()
    assert "value: 1" in workspace.output.toPlainText()
    assert "bytes: 01" in workspace.output.toPlainText()
    workspace.input.setText("bad")
    assert workspace.bit_editor.pattern is None and not workspace.bit_editor.isEnabled()
    workspace.close()


def test_large_integer_bit_editor_pages_preserve_offscreen_bits(qt_app: QApplication) -> None:
    workspace = ProgrammerWorkspace()
    workspace.bit_width.setValue(4096)
    workspace.input.setText("1")
    workspace.calculate()
    wait_for_workspace(workspace, qt_app)
    assert len(workspace.bit_editor.buttons) == 64
    workspace.bit_editor.buttons[4095].click()
    assert workspace.bit_editor.pattern == (1 << 4095) | 1
    workspace.bit_editor.page.setValue(64)
    assert 0 in workspace.bit_editor.buttons and len(workspace.bit_editor.buttons) == 64
    workspace.bit_editor.buttons[0].click()
    assert workspace.bit_editor.pattern == 1 << 4095
    workspace.bit_editor.page.setValue(1)
    assert workspace.bit_editor.buttons[4095].isChecked()
    workspace.close()
