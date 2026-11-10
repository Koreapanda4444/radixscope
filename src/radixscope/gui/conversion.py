from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QPushButton, QSpinBox

from radixscope.core import RoundingMode
from radixscope.core.input_syntax import detect_input_syntax
from radixscope.gui.widgets import Workspace


def base_input(value: int = 10) -> QSpinBox:
    widget = QSpinBox()
    widget.setRange(2, 36)
    widget.setValue(value)
    return widget


class ConversionWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__("Conversion", "Convert exact numbers or evaluate mixed-base expressions")
        self.input = QLineEdit("255")
        self.mode = QComboBox()
        self.mode.addItems(["Number", "Expression", "Auto"])
        self._syntax_hint = QLabel()
        self._syntax_hint.setWordWrap(True)
        self._detect_button = QPushButton("Use automatic input")
        self._detect_button.clicked.connect(lambda: self.mode.setCurrentText("Auto"))
        self.input.textChanged.connect(self.update_input_hint)
        self.source_base = base_input()
        self.targets = QLineEdit("2, 8, 10, 16")
        self.exact_output = QCheckBox(
            "Exact recurring output · display limit: 1000 fractional digits"
        )
        self.exact_output.setChecked(True)
        self.precision = QSpinBox()
        self.precision.setRange(0, 1000)
        self.precision.setValue(16)
        self.rounding = QComboBox()
        self.rounding.addItems([mode.value for mode in RoundingMode])
        self.rounding.setCurrentText(RoundingMode.HALF_EVEN.value)
        self.form.addRow("Input", self.input)
        self.form.addRow("Auto suggestion", self._syntax_hint)
        self.form.addRow("Input detection", self._detect_button)
        self.form.addRow("Mode", self.mode)
        self.form.addRow("Source base", self.source_base)
        self.form.addRow("Target bases", self.targets)
        self.form.addRow("Output", self.exact_output)
        self.form.addRow("Fractional digits", self.precision)
        self.form.addRow("Rounding", self.rounding)
        self.exact_output.toggled.connect(self.update_controls)
        self.mode.currentIndexChanged.connect(self.update_controls)
        self.run_button.setText("Convert")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.calculate)
        self.input.returnPressed.connect(self.calculate)
        self.update_controls()
        self.update_input_hint()
        self.bind_inputs()

    def update_controls(self) -> None:
        self.source_base.setEnabled(self.mode.currentText() == "Number")
        self.precision.setEnabled(not self.exact_output.isChecked())
        self.rounding.setEnabled(not self.exact_output.isChecked())

    def calculate(self) -> None:
        self.start_calculation()

    def update_input_hint(self) -> None:
        syntax = detect_input_syntax(self.input.text())
        self._syntax_hint.setText(syntax.description)
        self._detect_button.setEnabled(syntax.kind != "invalid")


class TraceWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__("Trace", "Divide the integer part, then multiply fractional remainders")
        self.input = QLineEdit("1/3")
        self.source_base = base_input()
        self.target_base = base_input(2)
        self.limit = QSpinBox()
        self.limit.setRange(1, 10000)
        self.limit.setValue(1000)
        self.form.addRow("Input", self.input)
        self.form.addRow("Source base", self.source_base)
        self.form.addRow("Target base", self.target_base)
        self.form.addRow("Maximum fractional steps", self.limit)
        self.run_button.setText("Trace conversion")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.calculate)
        self.input.returnPressed.connect(self.calculate)
        self.bind_inputs()

    def calculate(self) -> None:
        self.start_calculation()
