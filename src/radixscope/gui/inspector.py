from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QPushButton, QSpinBox

from radixscope.core import (
    ExactValue,
    IEEEFormat,
    decode_ieee754,
    format_integer,
    inspect_number,
    parse_integer,
)
from radixscope.gui.bits import BitEditor
from radixscope.gui.conversion import base_input
from radixscope.gui.floating import FloatNavigator
from radixscope.gui.i18n import LocalizedComboBox
from radixscope.gui.widgets import Workspace, control_row
from radixscope.reports import inspection_report


class InspectorWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__(
            "Number Inspector", "One value, synchronized numeric, signed, bit and byte views"
        )
        self.input = QLineEdit("255")
        self.base = base_input()
        self.input_mode = LocalizedComboBox()
        self.input_mode.addItems(["Number", "Expression"])
        self.data_type = LocalizedComboBox()
        self.data_type.addItems(["integer", "binary32", "binary64", "binary16", "bfloat16"])
        self.bit_width = QSpinBox()
        self.bit_width.setRange(1, 4096)
        self.bit_width.setValue(32)
        self.signed = QCheckBox("Signed")
        self.signed.setToolTip("Signed two's-complement interpretation of the selected bit width")
        self.pattern = QCheckBox("Raw bits")
        self.pattern.setToolTip(
            "Reinterpret the input as a bit pattern instead of converting its value"
        )
        self.byteorder = LocalizedComboBox()
        self.byteorder.addItems(["big", "little"])
        self.raw_hex = QLineEdit()
        self.raw_hex.setPlaceholderText("Edit the raw hexadecimal pattern, then press Enter")
        self.form.addRow("Input", self.input)
        self.form.addRow("Input format", self.input_mode)
        self.form.addRow("Representation", control_row("Base", self.base, self.data_type,
                                                       "Width", self.bit_width))
        self.form.addRow("Interpretation", control_row(self.pattern, self.signed, "Bytes",
                                                       self.byteorder))
        self.form.addRow("Hex pattern", self.raw_hex)
        self._byte_preview = QLineEdit()
        self._byte_preview.setReadOnly(True)
        self._byte_preview.setPlaceholderText("Bytes in the selected byte order")
        self._copy_bytes = QPushButton("Copy bytes")
        self._copy_bytes.setEnabled(False)
        self._copy_bytes.clicked.connect(
            lambda: QApplication.clipboard().setText(self._byte_preview.text())
        )
        self.form.addRow("Byte representation", control_row(self._byte_preview, self._copy_bytes))
        self.result_invalidated.connect(lambda: self._byte_preview.clear())
        self.result_invalidated.connect(lambda: self._copy_bytes.setEnabled(False))
        self.bit_editor = BitEditor()
        self.bit_editor.setToolTip("Raw result bits; numeric conversion uses the input above")
        self.form.addRow(self.bit_editor)
        self.float_navigator = FloatNavigator()
        self.form.addRow(self.float_navigator)
        self.float_navigator.pattern_requested.connect(self.edit_pattern)
        self.result_invalidated.connect(self.float_navigator.clear)
        self.result_ready.connect(self.show_bits)
        self.bit_editor.pattern_changed.connect(self.edit_pattern)
        self.raw_hex.editingFinished.connect(self.edit_hex)
        self.result_invalidated.connect(self.bit_editor.clear)
        self.data_type.currentIndexChanged.connect(self.update_controls)
        self.run_button.setText("Inspect")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.start_calculation)
        self.input.returnPressed.connect(self.start_calculation)
        self.update_controls()
        self.bind_inputs()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(150)
        self.refresh_timer.timeout.connect(self.start_calculation)
        for combo in (self.base, self.data_type, self.bit_width, self.byteorder):
            if isinstance(combo, QSpinBox):
                combo.valueChanged.connect(lambda: self.refresh_timer.start())
            else:
                combo.currentIndexChanged.connect(lambda: self.refresh_timer.start())
        for checkbox in (self.signed, self.pattern):
            checkbox.toggled.connect(lambda: self.refresh_timer.start())

    def update_controls(self) -> None:
        integer = self.data_type.currentText() == "integer"
        self.bit_width.setEnabled(integer)
        self.signed.setEnabled(integer)
        self.float_navigator.setVisible(not integer)
        if not integer:
            self.bit_width.setValue(IEEEFormat[self.data_type.currentText().upper()].bit_width)

    def show_bits(self, title: str, report: dict[str, object]) -> None:
        self._byte_preview.setText(str(report.get("bytes", "")))
        self._copy_bytes.setEnabled(bool(self._byte_preview.text()))
        bits = report.get("bits")
        if isinstance(bits, str):
            width = len(bits)
            fields = {}
            if self.data_type.currentText() != "integer":
                fraction = IEEEFormat[self.data_type.currentText().upper()].fraction_width
                fields = {"sign": (width - 1, width - 1),
                          "exponent": (fraction, width - 2), "fraction": (0, fraction - 1)}
                self.float_navigator.set_value(decode_ieee754(
                    int(bits, 2), self.data_type.currentText()
                ))
            elif self.signed.isChecked():
                fields = {"sign": (width - 1, width - 1)}
            self.bit_editor.set_pattern(int(bits, 2), width, fields)
            blocker = QSignalBlocker(self.raw_hex)
            self.raw_hex.setText(format(int(bits, 2), f"0{(width + 3) // 4}X"))
            del blocker

    def edit_hex(self) -> None:
        if not self.raw_hex.isModified():
            return
        try:
            self.edit_pattern(parse_integer(self.raw_hex.text().replace(" ", ""), 16).numerator)
        except (ValueError, TypeError) as error:
            self.invalidate_result()
            self.set_error(str(error))

    def edit_pattern(self, pattern: int) -> None:
        self.refresh_timer.stop()
        self.invalidate_result()
        blockers = [QSignalBlocker(widget) for widget in (
            self.input, self.pattern, self.input_mode
        )]
        self.input.setText(format_integer(ExactValue(pattern), self.base.value()))
        self.pattern.setChecked(True)
        self.input_mode.setCurrentText("Number")
        del blockers
        try:
            report = inspection_report(inspect_number(
                self.input.text(), base=self.base.value(), width=self.bit_width.value(),
                signed=self.signed.isChecked(), data_type=self.data_type.currentText(),
                raw=True, byteorder=self.byteorder.currentText(),
            ))
            report["input"] = self.input.text()
            self.set_result(report)
        except (ValueError, TypeError) as error:
            self.set_error(str(error))

    def start_calculation(self) -> None:
        self.refresh_timer.stop()
        super().start_calculation()

    def restore_state(self, state: dict[str, object]) -> None:
        super().restore_state(state)
        self.update_controls()
        self.refresh_timer.stop()

    def cancel_calculation(self) -> None:
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()
        super().cancel_calculation()
