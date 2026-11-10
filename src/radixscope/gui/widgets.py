import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QFontDatabase, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from radixscope.calculations import CalculationJob
from radixscope.exports import report_csv, report_json, write_export
from radixscope.reports import ReportField, StructuredReport, render_report


class Workspace(QWidget):
    result_ready = Signal(str, object)
    result_invalidated = Signal()
    transfer_requested = Signal(str, bool, object)

    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.title = title
        self._report: dict[str, object] | None = None
        self.job: CalculationJob | None = None
        self.job_state: dict[str, object] = {}
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll_calculation)
        self.form = QFormLayout()
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.form.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.form_container = QWidget()
        self.form_container.setLayout(self.form)
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.form_scroll.setMinimumHeight(100)
        self.form_scroll.setWidget(self.form_container)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.output.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.output.setAccessibleName(f"{title} result")
        self.report_fields: tuple[ReportField, ...] = ()
        self.result_table = QTableWidget(0, 2)
        self.result_table.setHorizontalHeaderLabels(["Representation", "Value"])
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.result_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setAccessibleName(f"{title} output items")
        self.result_table.cellDoubleClicked.connect(self.copy_selected)
        copy_action = QAction(self.result_table)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copy_action.triggered.connect(self.copy_selected)
        self.result_table.addAction(copy_action)
        self.result_views = QTabWidget()
        self.result_views.addTab(self.result_table, "Results")
        self.result_views.addTab(self.output, "Text report")
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setObjectName("error")
        self.run_button = QPushButton("Run")
        self.run_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_calculation)
        self.status = QLabel("Ready")
        self.copy_button = QPushButton("Copy result")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_result)
        self.copy_selected_button = QPushButton("Copy selected")
        self.copy_selected_button.clicked.connect(self.copy_selected)
        self.copy_selected_button.setEnabled(False)
        actions = QHBoxLayout()
        actions.addWidget(self.run_button)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.status)
        actions.addStretch()
        actions.addWidget(self.copy_selected_button)
        actions.addWidget(self.copy_button)
        self._destination = QComboBox()
        self._destination.addItems([name for name in (
            "Number Inspector", "Programmer", "IEEE 754", "Conversion"
        ) if name != title])
        self._transfer_mode = QComboBox()
        self._transfer_mode.addItems(["Numeric value", "Raw bits"])
        self._transfer_button = QPushButton("Send to workspace")
        self._transfer_button.setEnabled(False)
        self._transfer_button.clicked.connect(self.request_transfer)
        transfer = QHBoxLayout()
        transfer.addWidget(self._destination)
        transfer.addWidget(self._transfer_mode)
        transfer.addWidget(self._transfer_button)
        transfer.addStretch()
        self._export_format = QComboBox()
        self._export_format.addItems(["Text", "JSON", "CSV"])
        self._export_button = QPushButton("Export result")
        self._export_button.setEnabled(False)
        self._export_button.clicked.connect(lambda: self.export_report())
        transfer.addWidget(self._export_format)
        transfer.addWidget(self._export_button)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("heading")
        subtitle = QLabel(description)
        subtitle.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addWidget(self.form_scroll, 2)
        layout.addLayout(actions)
        layout.addLayout(transfer)
        layout.addWidget(self.error)
        layout.addWidget(self.result_views, 2)

    def set_result(self, report: dict[str, object], text: str | None = None) -> None:
        self.error.clear()
        self._report = report
        self._transfer_button.setEnabled(True)
        self._export_button.setEnabled(True)
        self.status.setText("Complete")
        self.output.setPlainText(render_report(report) if text is None else text)
        self.report_fields = StructuredReport(report).fields
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["Representation", "Value"])
        self.result_table.setRowCount(len(self.report_fields))
        for row, field in enumerate(self.report_fields):
            self.result_table.setItem(row, 0, QTableWidgetItem(field.path.replace("_", " ")))
            display = field.text if not isinstance(field.value, list) else (
                f"{len(field.value)} items · Text report / Copy selected"
            )
            item = QTableWidgetItem(display[:4000])
            item.setToolTip(display[:300])
            self.result_table.setItem(row, 1, item)
        self.copy_button.setEnabled(True)
        self.copy_selected_button.setEnabled(True)
        self.result_ready.emit(self.title, report)

    def set_error(self, message: str) -> None:
        self.clear_output()
        self.result_invalidated.emit()
        self.error.setText(message)
        self.status.setText("Error")
        position = re.search(r"at position (\d+)", message)
        input_widget = getattr(self, "input", None)
        if position is not None and isinstance(input_widget, QLineEdit):
            input_widget.setCursorPosition(min(int(position.group(1)), len(input_widget.text())))
            input_widget.setFocus()

    def clear_output(self) -> None:
        self._report = None
        self._transfer_button.setEnabled(False)
        self._export_button.setEnabled(False)
        self.output.clear()
        self.report_fields = ()
        self.result_table.setRowCount(0)
        self.copy_button.setEnabled(False)
        self.copy_selected_button.setEnabled(False)

    def bind_inputs(self) -> None:
        for name, widget in vars(self).items():
            if name.startswith("_"):
                continue
            if isinstance(widget, QLineEdit) or (
                isinstance(widget, QPlainTextEdit) and not widget.isReadOnly()
            ):
                widget.textChanged.connect(self.invalidate_result)
            elif isinstance(widget, QCheckBox):
                widget.toggled.connect(self.invalidate_result)
            elif isinstance(widget, QSpinBox):
                widget.valueChanged.connect(self.invalidate_result)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.invalidate_result)

    def invalidate_result(self) -> None:
        self.cancel_calculation()
        self.clear_output()
        self.error.clear()
        self.status.setText("Input changed · Run to update")
        self.result_invalidated.emit()

    def set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.copy_button.setEnabled(not busy and bool(self.report_fields))
        self.copy_selected_button.setEnabled(not busy and bool(self.report_fields))

    def start_calculation(self) -> None:
        self.invalidate_result()
        self.job_state = self.snapshot()
        try:
            self.job = CalculationJob(self.title, self.job_state)
        except (OSError, ValueError) as error:
            self.set_error(f"Could not start calculation: {error}")
            return
        self.set_busy(True)
        self.status.setText("Calculating…")
        self.timer.start()

    def poll_calculation(self) -> None:
        if self.job is None:
            return
        result = self.job.poll()
        if result is None:
            return
        self.job = None
        self.timer.stop()
        self.set_busy(False)
        if self.snapshot() != self.job_state:
            self.invalidate_result()
        elif result.report is not None:
            self.set_result(result.report, result.text)
        else:
            self.set_error(result.error)

    def cancel_calculation(self) -> None:
        self.timer.stop()
        if self.job is not None:
            self.job.cancel()
            self.job = None
            self.clear_output()
            self.status.setText("Cancelled")
        self.set_busy(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cancel_calculation()
        super().closeEvent(event)

    def copy_result(self) -> None:
        QApplication.clipboard().setText(self.output.toPlainText())

    def copy_selected(self) -> None:
        rows = sorted({index.row() for index in self.result_table.selectedIndexes()})
        QApplication.clipboard().setText("\n".join(
            self.report_fields[row].text for row in rows if row < len(self.report_fields)
        ))

    def request_transfer(self) -> None:
        if self._report is not None:
            self.transfer_requested.emit(
                self._destination.currentText(), self._transfer_mode.currentIndex() == 1,
                self._report,
            )

    def current_report(self) -> dict[str, object] | None:
        return self._report

    def export_report(self, format_: str | None = None) -> None:
        report = self.current_report()
        if report is None:
            return
        selected = (format_ or self._export_format.currentText()).lower()
        extension = "txt" if selected == "text" else selected
        path, _ = QFileDialog.getSaveFileName(
            self, "Export result", "", f"{selected.upper()} (*.{extension})"
        )
        if not path:
            return
        try:
            content = report_json(report) if selected == "json" else (
                report_csv(report) if selected == "csv" else render_report(report)
            )
            write_export(Path(path), content)
        except (OSError, ValueError) as error:
            self.error.setText(f"Could not export result: {error}")

    def snapshot(self) -> dict[str, object]:
        state: dict[str, object] = {}
        for name, widget in vars(self).items():
            if name.startswith("_"):
                continue
            if isinstance(widget, QLineEdit):
                state[name] = widget.text()
            elif isinstance(widget, QPlainTextEdit) and not widget.isReadOnly():
                state[name] = widget.toPlainText()
            elif isinstance(widget, QCheckBox):
                state[name] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                state[name] = widget.value()
            elif isinstance(widget, QComboBox):
                state[name] = widget.currentText()
        return state

    def restore_state(self, state: dict[str, object]) -> None:
        for name, value in state.items():
            widget = vars(self).get(name)
            if isinstance(widget, QLineEdit) and isinstance(value, str):
                widget.setText(value)
            elif (isinstance(widget, QPlainTextEdit) and not widget.isReadOnly()
                  and isinstance(value, str)):
                widget.setPlainText(value)
            elif isinstance(widget, QCheckBox) and isinstance(value, bool):
                widget.setChecked(value)
            elif isinstance(widget, QComboBox) and isinstance(value, str):
                if widget.findText(value) >= 0:
                    widget.setCurrentText(value)
            elif (
                isinstance(widget, QSpinBox) and isinstance(value, int)
                and not isinstance(value, bool) and widget.minimum() <= value <= widget.maximum()
            ):
                widget.setValue(value)
