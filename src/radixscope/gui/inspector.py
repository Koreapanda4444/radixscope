from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QSpinBox

from radixscope.core import ExactValue, IEEEFormat, format_integer, inspect_number, parse_integer
from radixscope.gui.bits import BitEditor
from radixscope.gui.conversion import base_input
from radixscope.gui.widgets import Workspace
from radixscope.reports import inspection_report


class InspectorWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__(
            "Number Inspector", "One value, synchronized numeric, signed, bit and byte views"
        )
        self.input = QLineEdit("255")
        self.base = base_input()
        self.data_type = QComboBox()
        self.data_type.addItems(["integer", "binary32", "binary64", "binary16", "bfloat16"])
        self.bit_width = QSpinBox()
        self.bit_width.setRange(1, 4096)
        self.bit_width.setValue(32)
        self.signed = QCheckBox("Signed two's complement")
        self.pattern = QCheckBox("Reinterpret raw bits instead of converting a value")
        self.byteorder = QComboBox()
        self.byteorder.addItems(["big", "little"])
        self.raw_hex = QLineEdit()
        self.raw_hex.setPlaceholderText("Edit the raw hexadecimal pattern, then press Enter")
        self.form.addRow("Input", self.input)
        self.form.addRow("Input base", self.base)
        self.form.addRow("Data type", self.data_type)
        self.form.addRow("Bit width", self.bit_width)
        self.form.addRow("Integer interpretation", self.signed)
        self.form.addRow("Input meaning", self.pattern)
        self.form.addRow("Byte order", self.byteorder)
        self.form.addRow("Editable Hex pattern", self.raw_hex)
        self.bit_editor = BitEditor()
        self.bit_editor.setToolTip("Raw result bits; numeric conversion uses the input above")
        self.form.addRow("Bit pattern", self.bit_editor)
        self.result_ready.connect(self.show_bits)
        self.bit_editor.pattern_changed.connect(self.edit_pattern)
        self.raw_hex.editingFinished.connect(self.edit_hex)
        self.result_invalidated.connect(self.bit_editor.clear)
        self.data_type.currentIndexChanged.connect(self.update_controls)
        self.run_button.setText("Inspect number")
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
        if not integer:
            self.bit_width.setValue(IEEEFormat[self.data_type.currentText().upper()].bit_width)

    def show_bits(self, title: str, report: dict[str, object]) -> None:
        bits = report.get("bits")
        if isinstance(bits, str):
            width = len(bits)
            fields = {}
            if self.data_type.currentText() != "integer":
                fraction = IEEEFormat[self.data_type.currentText().upper()].fraction_width
                fields = {"sign": (width - 1, width - 1),
                          "exponent": (fraction, width - 2), "fraction": (0, fraction - 1)}
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
        blockers = [QSignalBlocker(widget) for widget in (self.input, self.pattern)]
        self.input.setText(format_integer(ExactValue(pattern), self.base.value()))
        self.pattern.setChecked(True)
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
