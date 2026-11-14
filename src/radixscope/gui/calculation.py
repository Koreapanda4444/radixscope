from PySide6.QtWidgets import QCheckBox, QLineEdit, QSpinBox

from radixscope.core import RoundingMode
from radixscope.gui.i18n import LocalizedComboBox
from radixscope.gui.programmer import ProgrammerWorkspace
from radixscope.gui.widgets import control_row


class CalculationWorkspace(ProgrammerWorkspace):
    def __init__(self) -> None:
        super().__init__("Calculation")
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
        self.calculation_mode.currentIndexChanged.connect(self.update_calculation_controls)
        self.calculation_mode.currentIndexChanged.connect(self.invalidate_result)
        self.exact_output.toggled.connect(self.update_calculation_controls)
        for widget in (self.targets,):
            widget.textChanged.connect(self.invalidate_result)
        self.exact_output.toggled.connect(self.invalidate_result)
        self.precision.valueChanged.connect(self.invalidate_result)
        self.rounding.currentIndexChanged.connect(self.invalidate_result)
        self.update_calculation_controls()

    def update_calculation_controls(self) -> None:
        fixed = self.calculation_mode.currentText() == "Fixed-width integer"
        for widget in (self.base.parentWidget(), self.pattern.parentWidget(), self.operation,
                       self.extract, self.bit_editor):
            if widget is not None:
                self.form.setRowVisible(widget, fixed)
        self.form.setRowVisible(self.operand, fixed and self.operation.currentText()
                                not in ("inspect", "not"))
        self.form.setRowVisible(self._range_row, fixed and self.extract.isChecked())
        self.form.setRowVisible(self.targets, not fixed)
        self.form.setRowVisible(self.exact_output, not fixed)
        self.form.setRowVisible(
            self._exact_rounding, not fixed and not self.exact_output.isChecked()
        )
        self.input.setPlaceholderText("Fixed-width integer" if fixed else "0xFF + 1/3")

    def restore_state(self, state: dict[str, object]) -> None:
        super().restore_state(state)
        self.update_controls()
        self.update_calculation_controls()
