from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidgetItem,
)

from radixscope.core import (
    ExactValue,
    FixedWidthInteger,
    IEEEFormat,
    decode_ieee754,
    format_integer,
)
from radixscope.gui.bits import BitEditor
from radixscope.gui.conversion import base_input
from radixscope.gui.floating import FloatNavigator
from radixscope.gui.widgets import Workspace
from radixscope.reports import ieee_report, integer_report


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
        self.bit_editor = BitEditor()
        self.form.addRow("Result bits", self.bit_editor)
        self.bit_editor.pattern_changed.connect(self.edit_bits)
        self.result_ready.connect(self.show_bits)
        self.result_invalidated.connect(self.bit_editor.clear)
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

    def show_bits(self, title: str, report: dict[str, object]) -> None:
        bits = report.get("bits")
        if isinstance(bits, str):
            width = len(bits)
            fields = {"sign": (width - 1, width - 1)} if self.signed.isChecked() else {}
            self.bit_editor.set_pattern(int(bits, 2), width, fields)

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


class IEEEWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__(
            "IEEE 754", "Encode exact values or decode binary16, bfloat16, binary32 and binary64"
        )
        self.input = QLineEdit("0.1")
        self.mode = QComboBox()
        self.mode.addItems(["encode", "decode"])
        self.bit_width = QComboBox()
        self.bit_width.addItems(["32", "64", "16", "bfloat16"])
        self.base = base_input(16)
        self.byteorder = QComboBox()
        self.byteorder.addItems(["big", "little"])
        self.negative_zero = QCheckBox("Encode a zero value as -0")
        self.payload = QLineEdit("0")
        self.quiet = QCheckBox("Quiet NaN")
        self.quiet.setChecked(True)
        self._compare = False
        self._comparison_rows: list[dict[str, object]] = []
        self._comparison_columns: list[str] = []
        self.compare_button = QPushButton("Compare all four formats")
        self.compare_button.clicked.connect(self.compare_formats)
        self.form.addRow("Input", self.input)
        self.form.addRow("Mode", self.mode)
        self.form.addRow("Bit width", self.bit_width)
        self.form.addRow("Raw pattern base", self.base)
        self.form.addRow("Byte order", self.byteorder)
        self.form.addRow("Signed zero", self.negative_zero)
        self.form.addRow("NaN payload (decimal)", self.payload)
        self.form.addRow("NaN kind", self.quiet)
        self.form.addRow("Format comparison", self.compare_button)
        self.bit_editor = BitEditor()
        self.bit_legend = QLabel("Sign · Exponent · Fraction")
        self.form.addRow("Bit fields", self.bit_legend)
        self.form.addRow("Result bits", self.bit_editor)
        self.float_navigator = FloatNavigator()
        self.form.addRow("Neighbors / boundaries", self.float_navigator)
        self.float_navigator.pattern_requested.connect(self.edit_bits)
        self.result_invalidated.connect(self.float_navigator.clear)
        self.bit_editor.pattern_changed.connect(self.edit_bits)
        self.result_ready.connect(self.show_bits)
        self.result_invalidated.connect(self.bit_editor.clear)
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
        self.compare_button.setEnabled(encoding)
        nan = self.input.text().strip().lower().lstrip("+-") == "nan"
        self.base.setEnabled(not encoding)
        self.negative_zero.setEnabled(encoding and not nan)
        self.payload.setEnabled(encoding and nan)
        self.quiet.setEnabled(encoding and nan)
        self.input.setPlaceholderText("Exact expression, nan or inf" if encoding else "Raw digits")

    def calculate(self) -> None:
        self._compare = False
        self.start_calculation()

    def compare_formats(self) -> None:
        self._compare = True
        self.start_calculation()

    def snapshot(self) -> dict[str, object]:
        state = super().snapshot()
        state["compare"] = self._compare
        return state

    def restore_state(self, state: dict[str, object]) -> None:
        super().restore_state(state)
        self._compare = state.get("compare") is True

    def set_result(self, report: dict[str, object], text: str | None = None) -> None:
        super().set_result(report, text)
        rows = report.get("comparison")
        self._comparison_rows = [row for row in rows if isinstance(row, dict)] if (
            isinstance(rows, list)
        ) else []
        if not self._comparison_rows:
            return
        columns = ["format", "hexadecimal", "exact", "absolute_error", "relative_error",
                   "error_ulps", "effective_significand_bits", "classification",
                   "double_rounding_via_binary32", "double_rounding_via_binary64"]
        self._comparison_columns = columns
        self.result_table.setColumnCount(len(columns))
        self.result_table.setHorizontalHeaderLabels([key.replace("_", " ") for key in columns])
        self.result_table.setRowCount(len(self._comparison_rows))
        for row_index, row in enumerate(self._comparison_rows):
            for column, key in enumerate(columns):
                self.result_table.setItem(row_index, column, QTableWidgetItem(str(row.get(key))))
        self.result_table.resizeColumnsToContents()
        self.result_table.selectRow(0)

    def copy_selected(self) -> None:
        if not self._comparison_rows:
            super().copy_selected()
            return
        rows = sorted({index.row() for index in self.result_table.selectedIndexes()})
        QApplication.clipboard().setText("\n".join(
            "\t".join(str(self._comparison_rows[row].get(key)) for key in self._comparison_columns)
            for row in rows
        ))

    def request_transfer(self) -> None:
        if not self._comparison_rows:
            super().request_transfer()
            return
        row = max(0, self.result_table.currentRow())
        self.transfer_requested.emit(
            self._destination.currentText(), self._transfer_mode.currentIndex() == 1,
            self._comparison_rows[row],
        )

    def show_bits(self, title: str, report: dict[str, object]) -> None:
        bits = report.get("bits")
        if isinstance(bits, str) and len(bits) in (16, 32, 64):
            width = len(bits)
            format_name = str(report.get("format", f"binary{width}"))
            fraction_width = IEEEFormat[format_name.upper()].fraction_width
            fields = {
                "sign": (width - 1, width - 1),
                "exponent": (fraction_width, width - 2),
                "fraction": (0, fraction_width - 1),
            }
            self.bit_legend.setText(
                f"Sign: {width - 1} · Exponent: {width - 2}…{fraction_width} · "
                f"Fraction: {fraction_width - 1}…0"
            )
            self.bit_editor.set_pattern(int(bits, 2), width, fields)
            self.float_navigator.set_value(decode_ieee754(int(bits, 2), format_name))

    def edit_bits(self, pattern: int) -> None:
        value = decode_ieee754(pattern, self.bit_width.currentText())
        blockers = [QSignalBlocker(widget) for widget in (self.input, self.mode)]
        self.mode.setCurrentText("decode")
        self.input.setText(format_integer(ExactValue(pattern), self.base.value()))
        del blockers
        self.update_controls()
        report = ieee_report(value, self.byteorder.currentText())
        report["input"] = self.input.text()
        self.set_result(report)
