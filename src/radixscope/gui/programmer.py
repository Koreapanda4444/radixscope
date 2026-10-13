from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QSpinBox

from radixscope.gui.conversion import base_input
from radixscope.gui.widgets import Workspace


class ProgrammerWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__(
            "Programmer", "Inspect bits or operate on fixed-width signed and unsigned values"
        )
        self.input = QLineEdit("255")
        self.base = base_input()
        self.bit_width = QSpinBox()
        self.bit_width.setRange(1, 4096)
        self.bit_width.setValue(8)
        self.signed = QCheckBox("Signed two's complement")
        self.pattern = QCheckBox("Read input as a raw bit pattern")
        self.operation = QComboBox()
        self.operation.addItems(
            ["inspect", "add", "subtract", "multiply", "and", "or", "xor", "not",
             "shl", "shr", "lshr"]
        )
        self.operand = QLineEdit("1")
        self.operand_label = QLabel("Operand")
        self.byteorder = QComboBox()
        self.byteorder.addItems(["big", "little"])
        self.form.addRow("Input", self.input)
        self.form.addRow("Input base", self.base)
        self.form.addRow("Bit width", self.bit_width)
        self.form.addRow("Interpretation", self.signed)
        self.form.addRow("Input type", self.pattern)
        self.form.addRow("Operation", self.operation)
        self.form.addRow(self.operand_label, self.operand)
        self.form.addRow("Byte order", self.byteorder)
        self.operation.currentIndexChanged.connect(self.update_controls)
        self.run_button.setText("Inspect / calculate")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.calculate)
        self.input.returnPressed.connect(self.calculate)
        self.operand.returnPressed.connect(self.calculate)
        self.update_controls()
        self.bind_inputs()

    def update_controls(self) -> None:
        operation = self.operation.currentText()
        self.operand.setEnabled(operation not in ("inspect", "not"))
        shift = operation in ("shl", "shr", "lshr")
        self.operand_label.setText("Shift count (decimal)" if shift else "Operand")

    def calculate(self) -> None:
        self.start_calculation()


class IEEEWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__(
            "IEEE 754", "Encode exact expressions or decode raw binary32 / binary64 bits"
        )
        self.input = QLineEdit("0.1")
        self.mode = QComboBox()
        self.mode.addItems(["encode", "decode"])
        self.bit_width = QComboBox()
        self.bit_width.addItems(["32", "64"])
        self.base = base_input(16)
        self.byteorder = QComboBox()
        self.byteorder.addItems(["big", "little"])
        self.negative_zero = QCheckBox("Encode a zero value as -0")
        self.payload = QLineEdit("0")
        self.quiet = QCheckBox("Quiet NaN")
        self.quiet.setChecked(True)
        self.form.addRow("Input", self.input)
        self.form.addRow("Mode", self.mode)
        self.form.addRow("Bit width", self.bit_width)
        self.form.addRow("Raw pattern base", self.base)
        self.form.addRow("Byte order", self.byteorder)
        self.form.addRow("Signed zero", self.negative_zero)
        self.form.addRow("NaN payload (decimal)", self.payload)
        self.form.addRow("NaN kind", self.quiet)
        self.mode.currentIndexChanged.connect(self.update_controls)
        self.input.textChanged.connect(self.update_controls)
        self.run_button.setText("Encode / decode")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.calculate)
        self.input.returnPressed.connect(self.calculate)
        self.update_controls()
        self.bind_inputs()

    def update_controls(self) -> None:
        encoding = self.mode.currentText() == "encode"
        nan = self.input.text().strip().lower().lstrip("+-") == "nan"
        self.base.setEnabled(not encoding)
        self.negative_zero.setEnabled(encoding and not nan)
        self.payload.setEnabled(encoding and nan)
        self.quiet.setEnabled(encoding and nan)
        self.input.setPlaceholderText("Exact expression, nan or inf" if encoding else "Raw digits")

    def calculate(self) -> None:
        self.start_calculation()
