from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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

from radixscope.core import ExactValue, RoundingMode, parse_number
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
        super().__init__("Conversion", "Convert exact numbers between bases 2 through 36")
        self.form.setVerticalSpacing(4)
        self.form_container.setStyleSheet(
            "QLineEdit, QSpinBox, QComboBox { min-height: 20px; }"
        )
        self.input = QLineEdit("255")
        self.mode = LocalizedComboBox()
        self.mode.addItems(["Number", "Auto"])
        self._syntax_hint = QLabel()
        self._syntax_hint.setWordWrap(True)
        self._detect_button = QPushButton("Use automatic input")
        self._detect_button.clicked.connect(lambda: self.mode.setCurrentText("Auto"))
        self.input.textChanged.connect(self.update_input_hint)
        self.source_base = base_input()
        self.targets = QLineEdit("2, 8, 10, 16")
        self.preset = LocalizedComboBox()
        self.preset.addItems(["Custom", "Common bases", "Decimal to Hex", "Hex to Decimal",
                              "Decimal to Binary", "Binary to Decimal"])
        self._swap_to = 0
        self._swap_target = LocalizedComboBox()
        self._swap_button = QPushButton("Swap source and target")
        self._swap_button.clicked.connect(self.swap_bases)
        self.targets.textChanged.connect(self.update_swap_targets)
        self.source_base.valueChanged.connect(self.mark_custom)
        self.targets.textChanged.connect(self.mark_custom)
        self.preset.currentIndexChanged.connect(self.apply_preset)
        self.exact_output = QCheckBox(
            "Exact expansion (1000 digits)"
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
        # Presets and a quick swap are alternate ways to change the same bases.
        self._swap_target.setToolTip("Target base for quick swap")
        self.form.addRow("Preset", control_row(self.preset, self._swap_target,
                                               self._swap_button))
        self.form.addRow("Target bases", self.targets)
        self.show_trace = QCheckBox("Conversion steps")
        self.compare_rounding = QCheckBox("Compare rounding")
        self.compare_rounding.setToolTip("Compare all five rules using the original exact value")
        self.comparison_base = base_input(10)
        self.comparison_base.setToolTip("Target base for rounding comparison")
        self._comparison_base_label = QLabel("Base")
        self.form.addRow("Output", control_row(
            self.exact_output, self.show_trace, self.compare_rounding
        ))
        self.compare_rounding.toggled.connect(self.update_controls)
        self.target_base = base_input(2)
        self.limit = QSpinBox()
        self.limit.setRange(1, 10000)
        self.limit.setValue(1000)
        self._trace_options = control_row("Base", self.target_base, "Step limit", self.limit)
        self.form.addRow(self._trace_options)
        self.show_trace.toggled.connect(self.update_controls)
        self._rounding_row = control_row(
            "Digits", self.precision, self.rounding,
        )
        self.form.addRow("Rounding", self._rounding_row)
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
        self._rounding_table = QTableWidget(0, 2)
        self._rounding_table.setHorizontalHeaderLabels(["Rounding mode", "Result"])
        self._rounding_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._rounding_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._rounding_table.setAlternatingRowColors(True)
        self._rounding_table.setWordWrap(False)
        self._rounding_table.verticalHeader().setVisible(False)
        self._rounding_table.verticalHeader().setDefaultSectionSize(26)
        self._rounding_table.horizontalHeader().setStretchLastSection(True)
        self._rounding_table.setFont(self.output.font())
        self._rounding_table.cellDoubleClicked.connect(self.copy_rounding)
        copy_action = QAction(self._rounding_table)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copy_action.triggered.connect(self.copy_rounding)
        self._rounding_table.addAction(copy_action)
        self._copy_rounding = QPushButton("Copy comparison")
        self._copy_rounding.clicked.connect(self.copy_rounding)
        comparison_panel = QWidget()
        comparison_layout = QVBoxLayout(comparison_panel)
        comparison_layout.setContentsMargins(0, 6, 0, 0)
        self._comparison_digits = QSpinBox()
        self._comparison_digits.setRange(self.precision.minimum(), self.precision.maximum())
        self._comparison_digits.setValue(self.precision.value())
        self._comparison_digits.setToolTip("Fractional digits in the comparison base")
        self._comparison_digits.valueChanged.connect(self.precision.setValue)
        self.precision.valueChanged.connect(self._comparison_digits.setValue)
        self._copy_rounding.setMaximumWidth(180)
        comparison_layout.addWidget(control_row(
            self._comparison_base_label, self.comparison_base,
            "Digits", self._comparison_digits, self._copy_rounding,
        ))
        comparison_layout.addWidget(self._rounding_table)
        self._rounding_index = self.result_views.addTab(comparison_panel, "Rounding comparison")
        self.result_invalidated.connect(self.clear_rounding)
        self.clear_rounding()
        self.result_views.currentChanged.connect(self._schedule_input_fit)
        self.result_ready.connect(self.show_trace_result)
        self.result_ready.connect(self.show_rounding_result)
        self.result_invalidated.connect(self.clear_trace)
        self.clear_trace()
        self.update_controls()
        self.update_input_hint()
        self.update_swap_targets()
        self.source_base.valueChanged.connect(self.update_input_hint)
        self.mode.currentIndexChanged.connect(self.update_input_hint)
        self.bind_inputs()

    def update_controls(self) -> None:
        self.form.setRowVisible(self._trace_options, self.show_trace.isChecked())
        self.source_base.setEnabled(self.mode.currentText() == "Number")
        comparing = self.compare_rounding.isChecked()
        rounded = not self.exact_output.isChecked()
        self.precision.setEnabled(rounded or comparing)
        self.rounding.setVisible(rounded)
        self.result_views.setTabEnabled(self._rounding_index, comparing)
        if comparing and self.current_report() is None:
            self.result_views.setCurrentIndex(self._rounding_index)
        self.rounding.setEnabled(not self.exact_output.isChecked())
        self.form.setRowVisible(self._rounding_row, rounded)

    def update_input_hint(self) -> None:
        syntax = detect_input_syntax(self.input.text())
        description = syntax.description
        if self.mode.currentText() == "Number":
            if len(self.input.text()) > 4096:
                description = tr("Run to validate long input")
            else:
                try:
                    parse_number(self.input.text(), self.source_base.value())
                    description = tr("Valid number in selected base")
                except (ValueError, TypeError) as error:
                    description = tr(str(error))
            description = f"{self.source_base.value()} · " + description
        self._syntax_hint.setText(description)
        self._detect_button.setEnabled(syntax.kind != "invalid")

    def mark_custom(self) -> None:
        blocker = QSignalBlocker(self.preset)
        self.preset.setCurrentText("Custom")
        del blocker

    def apply_preset(self) -> None:
        presets = {"Common bases": (10, "2, 8, 10, 16"), "Decimal to Hex": (10, "16"),
                   "Hex to Decimal": (16, "10"), "Decimal to Binary": (10, "2"),
                   "Binary to Decimal": (2, "10")}
        label = self.preset.currentText()
        selected = presets.get(label)
        if selected is None:
            return
        blocker = QSignalBlocker(self.preset)
        self.mode.setCurrentText("Number")
        self.source_base.setValue(selected[0])
        self.targets.setText(selected[1])
        self.preset.setCurrentText(label)
        del blocker

    def update_swap_targets(self) -> None:
        previous = self._swap_target.currentText()
        self._swap_target.clear()
        try:
            bases = [int(value.strip()) for value in self.targets.text().split(",")]
            if any(not 2 <= base <= 36 for base in bases):
                raise ValueError("invalid target base")
        except ValueError:
            self._swap_button.setEnabled(False)
            return
        self._swap_target.addItems([str(base) for base in dict.fromkeys(bases)])
        if previous in [str(base) for base in bases]:
            self._swap_target.setCurrentText(previous)
        self._swap_button.setEnabled(bool(bases))

    def swap_bases(self) -> None:
        if self._swap_target.currentText():
            self._swap_to = int(self._swap_target.currentText())
            self.start_calculation()

    def snapshot(self) -> dict[str, object]:
        state = super().snapshot()
        state["swap_to"] = self._swap_to
        return state

    def set_result(self, report: dict[str, object], text: str | None = None) -> None:
        swapped = report.get("swapped_input")
        if isinstance(swapped, str):
            blockers = [QSignalBlocker(w) for w in (self.input, self.mode, self.source_base,
                                                   self.targets, self.preset)]
            self.input.setText(swapped)
            self.mode.setCurrentText("Number")
            self.source_base.setValue(int(str(report["swapped_source_base"])))
            self.targets.setText(str(report["swapped_target_base"]))
            self.preset.setCurrentText("Custom")
            del blockers
            self._swap_to = 0
            self.update_controls()
            self.update_input_hint()
            self.update_swap_targets()
        super().set_result(report, text)

    def calculate(self) -> None:
        self._swap_to = 0
        self.start_calculation()

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

    def result_height_hint(self) -> int:
        if self.result_views.currentIndex() == self._rounding_index:
            table = self._rounding_table
            row_height = max(table.verticalHeader().defaultSectionSize(),
                             table.verticalHeader().minimumSectionSize())
            rows_height = sum(table.rowHeight(row) if row < table.rowCount() else row_height
                              for row in range(5))
            return (table.horizontalHeader().height() + rows_height
                    + self.result_views.tabBar().sizeHint().height()
                    + self._copy_rounding.sizeHint().height() + 26)
        return super().result_height_hint()

    def clear_rounding(self) -> None:
        self._rounding_table.setRowCount(0)
        self._rounding_table.setAccessibleDescription("")
        self._copy_rounding.setEnabled(False)
        self.result_views.setTabEnabled(self._rounding_index, self.compare_rounding.isChecked())

    def show_rounding_result(self, title: str, report: dict[str, object]) -> None:
        comparison = report.get("rounding_comparison")
        if not isinstance(comparison, dict) or not isinstance(comparison.get("results"), dict):
            self.clear_rounding()
            return
        self.result_views.setTabEnabled(self._rounding_index, True)
        self._copy_rounding.setEnabled(True)
        self._rounding_table.setRowCount(len(RoundingMode))
        for row, mode in enumerate(RoundingMode):
            label = QTableWidgetItem(mode.value.capitalize())
            label.setData(UI_TEXT_ROLE, mode.value.capitalize())
            self._rounding_table.setItem(row, 0, label)
            self._rounding_table.setItem(row, 1, QTableWidgetItem(
                str(comparison["results"][mode.value])
            ))
        self._rounding_table.resizeColumnToContents(0)
        self._update_rounding_description(comparison)
        if self.compare_rounding.isChecked():
            self.result_views.setCurrentIndex(self._rounding_index)

    def _update_rounding_description(self, comparison: dict[str, object]) -> None:
        self._rounding_table.setAccessibleDescription(
            tr("Base") + " " + str(comparison["base"]) + " · "
            + tr("Fractional digits") + " " + str(comparison["precision"])
        )

    def copy_rounding(self) -> None:
        report = self.current_report()
        comparison = report.get("rounding_comparison") if report is not None else None
        if not isinstance(comparison, dict) or not isinstance(comparison.get("results"), dict):
            return
        rows = sorted({index.row() for index in self._rounding_table.selectedIndexes()})
        modes = list(RoundingMode)
        if not rows:
            rows = list(range(len(modes)))
        QApplication.clipboard().setText("\n".join(
            tr(modes[row].value.capitalize()) + "\t" + str(comparison["results"][modes[row].value])
            for row in rows
        ))

    def restore_state(self, state: dict[str, object]) -> None:
        blocker = QSignalBlocker(self.preset)
        super().restore_state(state)
        del blocker
        self._swap_to = 0
        self.update_swap_targets()
        self.update_controls()
        self.update_input_hint()
        self._comparison_digits.setValue(self.precision.value())

    def translate_ui(self) -> None:
        super().translate_ui()
        self._rounding_table.resizeColumnToContents(0)
        self.update_input_hint()
        report = self.current_report()
        comparison = report.get("rounding_comparison") if report is not None else None
        if isinstance(comparison, dict):
            self._update_rounding_description(comparison)
        trace = report.get("trace") if report is not None else None
        if isinstance(trace, dict):
            status = "Complete trace" if trace.get("complete") is True else (
                "Partial trace · step limit reached"
            )
            self._trace_summary.setText(tr(status) + " · " + str(trace.get("result", "")))
            for row in range(self._trace_table.rowCount()):
                for column in range(self._trace_table.columnCount()):
                    item = self._trace_table.item(row, column)
                    if item is not None and item.toolTip():
                        item.setToolTip(tr("Recurring digits"))
