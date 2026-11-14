from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from radixscope.core import ExactValue, RoundingMode
from radixscope.core.input_syntax import detect_input_syntax
from radixscope.gui.i18n import UI_TEXT_ROLE, LocalizedComboBox, tr
from radixscope.gui.widgets import Workspace, control_row


def base_input(value: int = 10) -> QSpinBox:
    widget = QSpinBox()
    widget.setRange(2, 36)
    widget.setValue(value)
    return widget


class ConversionWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__("Conversion", "Convert exact numbers or evaluate mixed-base expressions")
        self.input = QLineEdit("255")
        self.mode = LocalizedComboBox()
        self.mode.addItems(["Number", "Expression", "Auto"])
        self._syntax_hint = QLabel()
        self._syntax_hint.setWordWrap(True)
        self._detect_button = QPushButton("Use automatic input")
        self._detect_button.clicked.connect(lambda: self.mode.setCurrentText("Auto"))
        self.input.textChanged.connect(self.update_input_hint)
        self.source_base = base_input()
        self.targets = QLineEdit("2, 8, 10, 16")
        self.exact_output = QCheckBox(
            "Exact expansion · 1000 digit display limit"
        )
        self.exact_output.setChecked(True)
        self.precision = QSpinBox()
        self.precision.setRange(0, 1000)
        self.precision.setValue(16)
        self.rounding = LocalizedComboBox()
        self.rounding.addItems([mode.value for mode in RoundingMode])
        self.rounding.setCurrentText(RoundingMode.HALF_EVEN.value)
        self.form.addRow("Input", self.input)
        self.form.addRow("Input format", control_row(self.mode, "Base", self.source_base,
                                                     self._detect_button))
        self.form.addRow(self._syntax_hint)
        self.form.addRow("Target bases", self.targets)
        self.form.addRow("Output", self.exact_output)
        self.show_trace = QCheckBox("Show conversion steps")
        self.target_base = base_input(2)
        self.limit = QSpinBox()
        self.limit.setRange(1, 10000)
        self.limit.setValue(1000)
        self._trace_options = control_row("Base", self.target_base, "Step limit", self.limit)
        self.form.addRow(self.show_trace)
        self.form.addRow(self._trace_options)
        self.show_trace.toggled.connect(self.update_controls)
        self._rounding_row = control_row("Digits", self.precision, self.rounding)
        self.form.addRow("Rounded output", self._rounding_row)
        self.exact_output.toggled.connect(self.update_controls)
        self.mode.currentIndexChanged.connect(self.update_controls)
        self.run_button.setText("Convert")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.calculate)
        self.input.returnPressed.connect(self.calculate)
        self._trace_panel = QWidget()
        self._trace_summary = QLabel()
        self._trace_summary.setWordWrap(True)
        self._trace_table = QTableWidget(0, 5)
        self._trace_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._trace_table.setWordWrap(False)
        self._trace_table.verticalHeader().setVisible(False)
        self._trace_table.horizontalHeader().setStretchLastSection(True)
        trace_layout = QVBoxLayout(self._trace_panel)
        trace_layout.addWidget(self._trace_summary)
        trace_layout.addWidget(self._trace_table)
        self._trace_index = self.result_views.addTab(self._trace_panel, "Conversion steps")
        self.result_ready.connect(self.show_trace_result)
        self.result_invalidated.connect(self.clear_trace)
        self.clear_trace()
        self.update_controls()
        self.update_input_hint()
        self.bind_inputs()

    def update_controls(self) -> None:
        self.form.setRowVisible(self._trace_options, self.show_trace.isChecked())
        self.source_base.setEnabled(self.mode.currentText() == "Number")
        self.precision.setEnabled(not self.exact_output.isChecked())
        self.rounding.setEnabled(not self.exact_output.isChecked())
        self.form.setRowVisible(self._rounding_row, not self.exact_output.isChecked())

    def calculate(self) -> None:
        self.start_calculation()

    def update_input_hint(self) -> None:
        syntax = detect_input_syntax(self.input.text())
        self._syntax_hint.setText(syntax.description)
        self._detect_button.setEnabled(syntax.kind != "invalid")


    def clear_trace(self) -> None:
        self._trace_table.setRowCount(0)
        self._trace_summary.clear()
        self.result_views.setTabEnabled(self._trace_index, False)

    def show_trace_result(self, title: str, report: dict[str, object]) -> None:
        trace = report.get("trace")
        if not isinstance(trace, dict):
            self.clear_trace()
            return
        self.result_views.setTabEnabled(self._trace_index, True)
        self._trace_table.setHorizontalHeaderLabels([
            tr(key) for key in ("Stage", "Step", "Operation", "Digit", "Next remainder")
        ])
        complete = trace.get("complete") is True
        recurring = trace.get("recurring_start")
        status = "Complete trace" if complete else "Partial trace · step limit reached"
        self._trace_summary.setText(tr(status) + " · " + str(trace.get("result", "")))
        integers, fractions = trace.get("integer_steps"), trace.get("fractional_steps")
        if not isinstance(integers, list) or not isinstance(fractions, list):
            return
        self._trace_table.setRowCount(len(integers) + len(fractions))
        for row, step in enumerate([*integers, *fractions]):
            if not isinstance(step, dict):
                continue
            integer = row < len(integers)
            position = row if integer else row - len(integers)
            def number(key: str, data: dict[str, object] = step) -> str:
                value = data[key]
                return str(ExactValue(value)) if type(value) is int else str(value)
            operation = (number("dividend") + " ÷ " + number("divisor") + " = "
                         + number("quotient")) if integer else (
                number("remainder") + " * " + number("multiplier") + " = " + number("product")
            )
            values = ["Integer division" if integer else "Fraction multiplication",
                      str(position), operation, str(step["digit"]),
                      number("remainder" if integer else "next_remainder")]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(UI_TEXT_ROLE, value)
                if not integer and type(recurring) is int and position >= recurring:
                    item.setBackground(QColor(54, 118, 200, 40))
                    item.setToolTip(tr("Recurring digits"))
                self._trace_table.setItem(row, column, item)
        self._trace_table.resizeColumnsToContents()
        if self.show_trace.isChecked():
            self.result_views.setCurrentIndex(self._trace_index)

    def restore_state(self, state: dict[str, object]) -> None:
        super().restore_state(state)
        self.update_controls()
        self.update_input_hint()
