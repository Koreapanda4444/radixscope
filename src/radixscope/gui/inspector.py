from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidgetItem,
)

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
from radixscope.gui.i18n import UI_TEXT_ROLE, LocalizedComboBox
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
        self.analysis = LocalizedComboBox()
        self.analysis.addItems(["Number representation", "Format comparison"])
        self.negative_zero = QCheckBox("Encode a zero value as -0")
        self.payload = QLineEdit("0")
        self.quiet = QCheckBox("Quiet NaN")
        self.quiet.setChecked(True)
        self._show_special = QCheckBox("Special value options")
        self._show_special.toggled.connect(self.update_controls)
        self._comparison_rows: list[dict[str, object]] = []
        self._comparison_columns: list[str] = []
        self.raw_hex = QLineEdit()
        self.raw_hex.setPlaceholderText("Edit the raw hexadecimal pattern, then press Enter")
        self.form.addRow("Input", self.input)
        self.form.addRow("Input format", self.input_mode)
        self.form.addRow("Analysis", self.analysis)
        self.form.addRow("Representation", control_row("Base", self.base, self.data_type,
                                                       "Width", self.bit_width))
        self.form.addRow("Interpretation", control_row(self.pattern, self.signed, "Bytes",
                                                       self.byteorder))
        self.form.addRow(self._show_special)
        self.form.addRow("Signed zero", self.negative_zero)
        self.form.addRow("NaN payload (decimal)", self.payload)
        self.form.addRow("NaN kind", self.quiet)
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
        self.analysis.currentIndexChanged.connect(self.update_controls)
        self.input.textChanged.connect(self.update_controls)
        self.pattern.toggled.connect(self.update_controls)
        self.input_mode.currentIndexChanged.connect(self.update_controls)
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
        comparison = self.analysis.currentText() == "Format comparison"
        raw = self.pattern.isChecked() and not comparison
        self.bit_width.setEnabled(integer and not comparison)
        self.signed.setEnabled(integer and not comparison)
        self.pattern.setEnabled(not comparison)
        self.data_type.setEnabled(not comparison)
        self.input_mode.setEnabled(not raw)
        self.base.setEnabled(raw or self.input_mode.currentText() == "Number")
        nan = self.input.text().strip().lower().lstrip("+-") == "nan"
        special = self._show_special.isChecked() or nan
        for widget in (self.raw_hex, self.bit_editor, self._byte_preview.parentWidget()):
            if widget is not None:
                self.form.setRowVisible(widget, not comparison)
        self.form.setRowVisible(self.float_navigator, not integer and not comparison)
        self.form.setRowVisible(self._show_special, not integer and not raw and not comparison)
        self.form.setRowVisible(self.negative_zero, not integer and not raw and special)
        self.form.setRowVisible(
            self.payload, not integer and not raw and special and not comparison
        )
        self.form.setRowVisible(self.quiet, not integer and not raw and special and not comparison)
        if not integer and not comparison:
            self.bit_width.setValue(IEEEFormat[self.data_type.currentText().upper()].bit_width)

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
                item = QTableWidgetItem(str(row.get(key)))
                if key == "classification" or isinstance(row.get(key), bool):
                    item.setData(UI_TEXT_ROLE, str(row.get(key)))
                self.result_table.setItem(row_index, column, item)
        self.result_table.resizeColumnsToContents()
        self.result_table.selectRow(0)
        self.filter_results()
        self.translate_ui()

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
        self._comparison_rows = []
        blockers = [QSignalBlocker(widget) for widget in (
            self.input, self.pattern, self.input_mode, self.analysis
        )]
        self.input.setText(format_integer(ExactValue(pattern), self.base.value()))
        self.pattern.setChecked(True)
        self.input_mode.setCurrentText("Number")
        self.analysis.setCurrentText("Number representation")
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
