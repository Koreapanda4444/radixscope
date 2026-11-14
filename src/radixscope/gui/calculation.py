from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from radixscope.core import ExactValue, FixedWidthInteger, RoundingMode, format_integer
from radixscope.gui.bits import BitEditor
from radixscope.gui.conversion import base_input
from radixscope.gui.i18n import UI_TEXT_ROLE, LocalizedComboBox, tr
from radixscope.gui.widgets import Workspace, control_row, error_preview
from radixscope.reports import integer_report


class CalculationWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__("Calculation")
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
        self.compare_widths = QCheckBox("Compare 8/16/32/64-bit results")
        self.form.addRow(self.compare_widths)
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
        self.compare_widths.toggled.connect(self.update_controls)
        self._width_table = QTableWidget(0, 6)
        self._width_table.setHorizontalHeaderLabels([
            "Bits", "Result", "Mathematical result", "Overflow", "Hex", "Error"
        ])
        self._width_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._width_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._width_table.setAlternatingRowColors(True)
        self._width_table.setWordWrap(False)
        self._width_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._width_table.verticalHeader().setVisible(False)
        self._width_table.horizontalHeader().setStretchLastSection(True)
        self._width_table.cellDoubleClicked.connect(self.copy_width_comparison)
        copy_action = QAction(self._width_table)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copy_action.triggered.connect(self.copy_width_comparison)
        self._width_table.addAction(copy_action)
        self._copy_widths = QPushButton("Copy comparison")
        self._copy_widths.setMaximumWidth(180)
        self._copy_widths.clicked.connect(self.copy_width_comparison)
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 6, 0, 0)
        panel_layout.addWidget(self._copy_widths)
        panel_layout.addWidget(self._width_table)
        self._width_tab = self.result_views.addTab(panel, "Width comparison")
        self.result_views.currentChanged.connect(self._schedule_input_fit)
        self.result_ready.connect(self.show_width_comparison)
        self.result_invalidated.connect(self.clear_width_comparison)
        self.clear_width_comparison()
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
        self.form.setRowVisible(self.compare_widths, fixed)
        self.form.setRowVisible(self.targets, not fixed)
        self.form.setRowVisible(self.exact_output, not fixed)
        self.form.setRowVisible(
            self._exact_rounding, not fixed and not self.exact_output.isChecked()
        )
        self.input.setPlaceholderText("Fixed-width integer" if fixed else "0xFF + 1/3")
        if not fixed or not self.compare_widths.isChecked():
            self.clear_width_comparison()

    def result_height_hint(self) -> int:
        if self.result_views.currentIndex() == self._width_tab:
            return (
                4 * self._width_table.verticalHeader().defaultSectionSize()
                + self._width_table.horizontalHeader().sizeHint().height()
                + self.result_views.tabBar().sizeHint().height() + 72
            )
        return super().result_height_hint()

    def clear_width_comparison(self) -> None:
        self._width_table.setRowCount(0)
        self._copy_widths.setEnabled(False)
        self.result_views.setTabEnabled(self._width_tab, False)

    def show_width_comparison(self, title: str, report: dict[str, object]) -> None:
        rows = report.get("width_comparison")
        if not self.compare_widths.isChecked() or not isinstance(rows, list):
            self.clear_width_comparison()
            return
        self._width_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            overflow = row.get("overflow")
            texts = [
                str(row["width"]), str(row["value"]) if row["value"] is not None else "—",
                str(row["mathematical"]) if row["mathematical"] is not None else "—",
                "Yes" if overflow is True else "No" if overflow is False else "—",
                str(row["hexadecimal"]) if row["hexadecimal"] is not None else "—",
                str(row.get("error") or ""),
            ]
            for column, value in enumerate(texts):
                item = QTableWidgetItem(value[:400])
                item.setData(Qt.ItemDataRole.UserRole, value)
                item.setToolTip(value[:2000])
                if column in (1, 2, 4):
                    item.setFont(self.output.font())
                if row.get("error") and column in (0, 5):
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                if column == 3 and value in ("Yes", "No"):
                    item.setData(UI_TEXT_ROLE, value)
                self._width_table.setItem(index, column, item)
        self._copy_widths.setEnabled(bool(rows))
        self.result_views.setTabEnabled(self._width_tab, True)
        self.result_views.setCurrentIndex(self._width_tab)
        self.translate_ui()

    def translate_ui(self) -> None:
        super().translate_ui()
        for row in range(self._width_table.rowCount()):
            item = self._width_table.item(row, 5)
            source = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if item is not None and isinstance(source, str):
                item.setText(error_preview(tr(source), 400))
                item.setToolTip(error_preview(tr(source), 2000))
        report = self.current_report()
        selected_error = report.get("selected_width_error") if report is not None else None
        if isinstance(selected_error, str):
            self.error.setText(error_preview(tr(selected_error), 240))
            self.error.setToolTip(error_preview(tr(selected_error), 2000))
        header = self._width_table.horizontalHeader()
        for column in (0, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        for column in (1, 2, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self._width_table.setColumnWidth(
                column, min(280, max(100, self._width_table.sizeHintForColumn(column) + 12))
            )

    def set_result(self, report: dict[str, object], text: str | None = None) -> None:
        super().set_result(report, text)
        selected_error = report.get("selected_width_error")
        if isinstance(selected_error, str):
            self.error.setText(selected_error)
            self.error.show()
            self.status.setText("Comparison complete · selected width failed")
            self._transfer_button.setEnabled(False)
            self.translate_ui()
        self._schedule_input_fit()

    def copy_width_comparison(self) -> None:
        rows = sorted({index.row() for index in self._width_table.selectedIndexes()})
        if not rows:
            rows = list(range(self._width_table.rowCount()))
        lines = []
        for row in rows:
            values = []
            for column in range(self._width_table.columnCount()):
                item = self._width_table.item(row, column)
                source = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
                if item is None:
                    values.append("")
                elif column == 3:
                    values.append(item.text())
                else:
                    values.append(tr(source) if isinstance(source, str) else item.text())
            lines.append("\t".join(values))
        QApplication.clipboard().setText("\n".join(lines))

    def calculate(self) -> None:
        self.start_calculation()

    def show_bits(self, title: str, report: dict[str, object]) -> None:
        self.bit_editor.clear()
        self.form.setRowVisible(self.bit_editor, False)
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
