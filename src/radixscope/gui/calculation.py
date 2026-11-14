from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QSpinBox

from radixscope.core import ExactValue, FixedWidthInteger, RoundingMode, format_integer
from radixscope.gui.bits import BitEditor
from radixscope.gui.conversion import base_input
from radixscope.gui.i18n import LocalizedComboBox
from radixscope.gui.widgets import Workspace, control_row
from radixscope.reports import integer_report


class CalculationWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__(
            "Calculation", "Exact expressions and explicit fixed-width integer operations"
        )
        self.form.setVerticalSpacing(6)
        self.input = QLineEdit("255")
        self.base = base_input()
        self.bit_width = QSpinBox()
        self.bit_width.setRange(1, 4096)
        self.bit_width.setValue(8)
        self.signed = QCheckBox("Signed")
        self.pattern = QCheckBox("Read raw bits")
        self.operation = LocalizedComboBox()
        self.operation.addItems(
            ["inspect", "add", "subtract", "multiply", "and", "or", "xor", "not",
             "shl", "shr", "lshr"]
        )
        self.operand = QLineEdit("1")
        self.operand_label = QLabel("Operand")
        self.byteorder = LocalizedComboBox()
        self.byteorder.addItems(["big", "little"])
        self.form.addRow("Input", self.input)
        self.form.addRow("Representation", control_row("Base", self.base, "Width", self.bit_width,
                                                       self.signed))
        self.form.addRow("Interpretation", control_row(self.pattern, "Bytes", self.byteorder))
        self.form.addRow("Operation", self.operation)
        self.form.addRow(self.operand_label, self.operand)
        self.extract = QCheckBox("Extract bit range")
        self.extract_offset = QSpinBox()
        self.extract_offset.setRange(0, 4095)
        self.extract_width = QSpinBox()
        self.extract_width.setRange(1, 4096)
        self.extract_width.setValue(1)
        self.form.addRow(self.extract)
        self._range_row = control_row("Offset (LSB 0)", self.extract_offset,
                                      "Width", self.extract_width)
        self.form.addRow(self._range_row)
        self.form.setRowVisible(self._range_row, False)
        self.extract.toggled.connect(lambda shown: self.form.setRowVisible(self._range_row, shown))
        self.bit_editor = BitEditor()
        self.form.addRow(self.bit_editor)
        self.bit_editor.pattern_changed.connect(self.edit_bits)
        self.result_ready.connect(self.show_bits)
        self.result_invalidated.connect(self.bit_editor.clear)
        self.result_invalidated.connect(
            lambda: self.form.setRowVisible(self.bit_editor, False)
        )
        self.operation.currentIndexChanged.connect(self.update_controls)
        self.run_button.setText("Calculate")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.calculate)
        self.input.returnPressed.connect(self.calculate)
        self.operand.returnPressed.connect(self.calculate)
        self.calculation_mode = LocalizedComboBox()
        self.calculation_mode.addItems(["Exact expression", "Fixed-width integer"])
        self.targets = QLineEdit("2, 8, 10, 16")
        self.exact_output = QCheckBox("Exact expansion · 1000 digit display limit")
        self.exact_output.setChecked(True)
        self.precision = QSpinBox()
        self.precision.setRange(0, 1000)
        self.precision.setValue(16)
        self.rounding = LocalizedComboBox()
        self.rounding.addItems([mode.value for mode in RoundingMode])
        self.rounding.setCurrentText("half-even")
        self._exact_rounding = control_row("Digits", self.precision, self.rounding)
        self.form.insertRow(0, "Calculation mode", self.calculation_mode)
        self.form.insertRow(2, "Target bases", self.targets)
        self.form.insertRow(3, "Output", self.exact_output)
        self.form.insertRow(4, "Rounded output", self._exact_rounding)
        self.calculation_mode.currentIndexChanged.connect(self.update_controls)
        self.exact_output.toggled.connect(self.update_controls)
        self._calculation_hint = QLabel()
        self._calculation_hint.setWordWrap(True)
        self.form.insertRow(1, self._calculation_hint)
        self.update_controls()
        self.bind_inputs()

    def update_controls(self) -> None:
        self.form.setRowVisible(self._range_row, self.extract.isChecked())
        operation = self.operation.currentText()
        fixed = self.calculation_mode.currentText() == "Fixed-width integer"
        self.operand.setEnabled(fixed and operation not in ("inspect", "not"))
        self.form.setRowVisible(self.operand, fixed and operation not in ("inspect", "not"))
        shift = operation in ("shl", "shr", "lshr")
        self.operand_label.setText("Shift count (decimal)" if shift else "Operand")
        for widget in (self.base.parentWidget(), self.pattern.parentWidget(), self.operation,
                       self.extract):
            if widget is not None:
                self.form.setRowVisible(widget, fixed)
        self.form.setRowVisible(self._range_row, fixed and self.extract.isChecked())
        # Keep the empty bit editor out of the form until there is a real result.
        self.form.setRowVisible(self.bit_editor, fixed and self.bit_editor.pattern is not None)
        self.form.setRowVisible(self.targets, not fixed)
        self.form.setRowVisible(self.exact_output, not fixed)
        self.form.setRowVisible(
            self._exact_rounding, not fixed and not self.exact_output.isChecked()
        )
        self._calculation_hint.setText(
            "Exact result and wrapped result are separate; only fixed-width operations wrap."
            if fixed else (
                "Expressions use exact rational arithmetic; bitwise operators require integers."
            )
        )
        self.input.setPlaceholderText("Fixed-width integer" if fixed else "0xFF + 1/3")

    def calculate(self) -> None:
        self.start_calculation()

    def show_bits(self, title: str, report: dict[str, object]) -> None:
        bits = report.get("bits")
        if isinstance(bits, str):
            width = len(bits)
            fields = {"sign": (width - 1, width - 1)} if self.signed.isChecked() else {}
            self.bit_editor.set_pattern(int(bits, 2), width, fields)
            self.form.setRowVisible(
                self.bit_editor, self.calculation_mode.currentText() == "Fixed-width integer"
            )

    def edit_bits(self, pattern: int) -> None:
        value = FixedWidthInteger.from_bit_pattern(
            pattern, self.bit_width.value(), self.signed.isChecked()
        )
        blockers = [QSignalBlocker(widget) for widget in (self.input, self.pattern, self.operation)]
        self.input.setText(format_integer(ExactValue(pattern), self.base.value()))
        self.pattern.setChecked(True)
        self.operation.setCurrentText("inspect")
        del blockers
        self.update_controls()
        report = integer_report(value, self.byteorder.currentText())
        report.update({"input": self.input.text(), "operation": "inspect"})
        self.set_result(report)


    def restore_state(self, state: dict[str, object]) -> None:
        super().restore_state(state)
        self.update_controls()
