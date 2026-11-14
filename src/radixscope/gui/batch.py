
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTableWidgetItem,
)

from radixscope.core import RoundingMode
from radixscope.gui.conversion import base_input
from radixscope.gui.i18n import UI_TEXT_ROLE, LocalizedComboBox
from radixscope.gui.widgets import Workspace, control_row


class BatchWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__("Batch Conversion")
        self.form.setVerticalSpacing(6)
        self._rows: list[dict[str, object]] = []
        self._columns: list[str] = []
        self.input = QPlainTextEdit("255\n1/3\n0.1")
        # Three source lines remain visible while long batches scroll inside this editor.
        self.input.setMinimumHeight(88)
        self.input.setMaximumHeight(112)
        self.mode = LocalizedComboBox()
        self.mode.addItems(["Number", "Expression", "Auto"])
        self.source_base = base_input()
        self.targets = QLineEdit("2, 8, 10, 16")
        self.precision = QSpinBox()
        self.precision.setRange(0, 1000)
        self.precision.setValue(16)
        self.exact_output = QCheckBox("Exact output (expansion work limits still apply)")
        self.rounding = LocalizedComboBox()
        self.rounding.addItems([mode.value for mode in RoundingMode])
        self.rounding.setCurrentText(RoundingMode.HALF_EVEN.value)
        self.row_limit = QSpinBox()
        self.row_limit.setRange(1, 1000)
        self.row_limit.setValue(1000)
        self._summary = QLabel()
        self._summary.setWordWrap(True)
        self.form.addRow("Line input", self.input)
        self.form.addRow("Input format", control_row(self.mode, "Base", self.source_base))
        self.form.addRow("Target bases", self.targets)
        self.form.addRow("Output", self.exact_output)
        self._rounding_row = control_row("Digits", self.precision, self.rounding)
        self.form.addRow("Rounded output", self._rounding_row)
        self.form.addRow("Maximum rows", self.row_limit)
        self.form.addRow("Batch status", self._summary)
        self.form.setRowVisible(self._summary, False)
        self.mode.currentIndexChanged.connect(self.update_controls)
        self.exact_output.toggled.connect(self.update_controls)
        self.run_button.setText("Convert lines")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.start_calculation)
        self.result_invalidated.connect(self.clear_batch)
        self.update_controls()
        self.bind_inputs()

    def update_controls(self) -> None:
        self.source_base.setEnabled(self.mode.currentText() == "Number")
        self.precision.setEnabled(not self.exact_output.isChecked())
        self.rounding.setEnabled(not self.exact_output.isChecked())
        self.form.setRowVisible(self._rounding_row, not self.exact_output.isChecked())

    def clear_batch(self) -> None:
        self._rows = []
        self._summary.clear()
        self.form.setRowVisible(self._summary, False)

    def set_result(self, report: dict[str, object], text: str | None = None) -> None:
        super().set_result(report, text)
        rows, bases = report.get("rows"), report.get("bases")
        assert isinstance(rows, list) and isinstance(bases, list)
        self._rows = rows
        self._columns = ["line", "input", "exact", *[f"base_{base}" for base in bases], "error"]
        self.result_table.setColumnCount(len(self._columns))
        self.result_table.setHorizontalHeaderLabels(self._columns)
        self.result_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, key in enumerate(self._columns):
                item = QTableWidgetItem(self.cell_text(row, key))
                if row.get("error"):
                    item.setForeground(QColor("#c94848"))
                    if key == "error":
                        item.setData(UI_TEXT_ROLE, str(row["error"]))
                self.result_table.setItem(row_index, column, item)
        self.result_table.resizeColumnsToContents()
        self.result_table.selectRow(0)
        self.filter_results()
        message = f"{report['processed']} / {report['total']} rows · {report['errors']} errors"
        if report["limited"]:
            message += " · Limit reached; some inputs were not processed"
        self._summary.setText(message)
        self.form.setRowVisible(self._summary, True)
        self.translate_ui()

    @staticmethod
    def cell_text(row: dict[str, object], key: str) -> str:
        if key.startswith("base_"):
            outputs = row.get("outputs")
            return (
                str(outputs.get(key.removeprefix("base_"), "")) if isinstance(outputs, dict) else ""
            )
        value = row.get(key)
        return str(value) if value is not None else ""

    def copy_selected(self) -> None:
        rows = sorted({index.row() for index in self.result_table.selectedIndexes()})
        QApplication.clipboard().setText(
            "\n".join(
                "\t".join(self.cell_text(self._rows[row], key) for key in self._columns)
                for row in rows
            )
        )

    def request_transfer(self) -> None:
        if self._rows:
            self.transfer_requested.emit(
                self._destination.currentText(),
                self._transfer_mode.currentIndex() == 1,
                self._rows[max(0, self.result_table.currentRow())],
            )

    def export(self, format_: str) -> None:
        self.export_report(format_)
