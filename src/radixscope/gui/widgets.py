import re
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QFontDatabase,
    QKeySequence,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from radixscope.calculations import CalculationJob
from radixscope.exports import report_csv, report_json, write_export
from radixscope.gui.bits import BitEditor
from radixscope.gui.i18n import (
    UI_CONTEXT_ROLE,
    UI_TEXT_ROLE,
    LocalizedComboBox,
    gui_report,
    localize,
    tr,
)
from radixscope.gui.presentation import field_heading, field_order, is_detail
from radixscope.reports import ReportField, StructuredReport, render_report
from radixscope.workspaces import transfer_destinations


def control_row(*controls: QWidget | str) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for control in controls:
        widget = QLabel(control) if isinstance(control, str) else control
        if isinstance(widget, QComboBox):
            widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            widget.setMinimumContentsLength(7)
        layout.addWidget(widget)
    return row


class Workspace(QWidget):
    result_ready = Signal(str, object)
    result_invalidated = Signal()
    transfer_requested = Signal(str, bool, object)

    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.title = title
        self._report: dict[str, object] | None = None
        self._english_report = ""
        self.job: CalculationJob | None = None
        self.job_state: dict[str, object] = {}
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll_calculation)
        self.form = QFormLayout()
        self.form.setHorizontalSpacing(14)
        self.form.setVerticalSpacing(9)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.form.setContentsMargins(2, 2, 8, 2)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.form.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.form_container = QWidget()
        self.form_container.setLayout(self.form)
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.form_scroll.setMinimumHeight(70)
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
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setMinimumHeight(80)
        self.result_table.setWordWrap(False)
        self.result_table.verticalHeader().setDefaultSectionSize(31)
        self.result_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.result_table.cellDoubleClicked.connect(self.copy_selected)
        copy_action = QAction(self.result_table)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        copy_action.triggered.connect(self.copy_selected)
        self.result_table.addAction(copy_action)
        self.result_views = QTabWidget()
        self._result_filter = QLineEdit()
        self._result_filter.setPlaceholderText("Filter result fields")
        self._result_filter.textChanged.connect(self.filter_results)
        results_page = QWidget()
        results_page.setObjectName("resultsPanel")
        results_layout = QVBoxLayout(results_page)
        results_layout.setContentsMargins(0, 6, 0, 0)
        results_layout.addWidget(self._result_filter)
        self._empty_result = QLabel("Run a calculation to see results")
        self._empty_result.setWordWrap(True)
        self._empty_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_result.setParent(self.result_table.viewport())
        self._empty_result.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.result_table.viewport().installEventFilter(self)
        results_layout.addWidget(self.result_table)
        self.result_views.addTab(results_page, "Results")
        self.result_views.addTab(self.output, "Text report")
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setObjectName("error")
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        self.error.hide()
        self.run_button = QPushButton("Run")
        self.run_button.setObjectName("primary")
        self.run_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel_calculation)
        self.status = QLabel("Ready")
        self.status.setObjectName("actionStatus")
        self.status.setWordWrap(True)
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.status.setMinimumWidth(0)
        self.status.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.run_button.setMinimumWidth(106)
        self.cancel_button.setMinimumWidth(76)
        self.copy_button = QPushButton("Copy all")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_result)
        self.copy_selected_button = QPushButton("Copy selected")
        self.copy_selected_button.clicked.connect(self.copy_selected)
        self.copy_selected_button.setEnabled(False)
        # One consistent footer for all workspaces. Keep actions out of the
        # scrolling form, with status on the left and buttons on the right.
        self.action_bar = QWidget()
        self.action_bar.setObjectName("actionBar")
        actions = QHBoxLayout(self.action_bar)
        actions.setContentsMargins(2, 8, 2, 2)
        actions.setSpacing(8)
        actions.addWidget(self.status, 1)
        actions.addWidget(self.cancel_button, 0)
        actions.addWidget(self.run_button, 0)
        copies = QHBoxLayout()
        results_layout.removeWidget(self._result_filter)
        copies.addWidget(self._result_filter, 1)
        self._show_details = QCheckBox("Detailed fields")
        self._show_details.toggled.connect(self.filter_results)
        copies.addWidget(self._show_details)
        copies.addWidget(self.copy_selected_button)
        copies.addWidget(self.copy_button)
        results_layout.insertLayout(0, copies)
        self._destination = LocalizedComboBox()
        self._destination.addItems(transfer_destinations(title))
        self._transfer_mode = LocalizedComboBox()
        self._transfer_mode.addItems(["Numeric value", "Raw bits"])
        self._transfer_button = QPushButton("Send to workspace")
        self._transfer_button.setEnabled(False)
        self._transfer_button.clicked.connect(self.request_transfer)
        self._utilities = QWidget()
        transfer = QGridLayout(self._utilities)
        transfer.setContentsMargins(0, 0, 0, 0)
        transfer.addWidget(self._destination, 0, 0)
        transfer.addWidget(self._transfer_mode, 0, 1)
        transfer.addWidget(self._transfer_button, 0, 2)
        self._export_format = LocalizedComboBox()
        self._export_format.addItems(["Text", "JSON", "CSV"])
        self._export_button = QPushButton("Export result")
        self._export_button.setEnabled(False)
        self._export_button.clicked.connect(lambda: self.export_report())
        transfer.addWidget(self._export_format, 1, 1)
        transfer.addWidget(self._export_button, 1, 2)
        self._utilities.setVisible(False)
        self._utility_toggle = QToolButton()
        self._utility_toggle.setText("Reuse / export")
        self._utility_toggle.setCheckable(True)
        self._utility_toggle.toggled.connect(self._utilities.setVisible)
        self.result_views.setCornerWidget(self._utility_toggle)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("heading")
        subtitle = QLabel(description)
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(subtitle)
        input_panel = QWidget()
        input_panel.setObjectName("inputPanel")
        self.form_container.setObjectName("inputForm")
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(8, 8, 8, 6)
        input_layout.addWidget(self.form_scroll, 1)
        input_layout.addWidget(self._utilities)
        input_layout.addWidget(self.error)
        input_layout.addWidget(self.action_bar, 0)
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(input_panel)
        self._splitter.addWidget(self.result_views)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setSizes([410, 180])
        layout.addWidget(self._splitter, 1)
        self._input_panel = input_panel
        self._splitter_customized = False
        self._manual_ratio = 0.6
        self._last_preferred = 0
        self._last_available = 0
        self._splitter.handle(1).installEventFilter(self)
        self._splitter.handle(1).setToolTip("Double-click to restore automatic layout")
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.timeout.connect(self._fit_input_to_content)
        self._splitter.splitterMoved.connect(self._mark_splitter_customized)
        self.form_container.installEventFilter(self)
        self.form_scroll.viewport().installEventFilter(self)
        self._utilities.installEventFilter(self)

    def _mark_splitter_customized(self, position: int, index: int) -> None:
        self._splitter_customized = True
        sizes = self._splitter.sizes()
        self._manual_ratio = sizes[0] / max(1, sum(sizes))

    def _schedule_input_fit(self) -> None:
        self._fit_timer.start(0)

    def reset_splitter(self) -> None:
        self._splitter_customized = False
        self._schedule_input_fit()

    def result_height_hint(self) -> int:
        return 150

    def _fit_input_to_content(self) -> None:
        if not self.isVisible():
            return
        available = self._splitter.height() - self._splitter.handleWidth()
        if available <= 0:
            return
        width = max(100, self.form_scroll.viewport().width())
        # QFormLayout excludes hidden rows and measures labels at the current
        # width, using Qt's logical pixels and the active language/font metrics.
        form_height = self.form.heightForWidth(width) if self.form.hasHeightForWidth() else -1
        if form_height < 0:
            form_height = self.form.sizeHint().height()
        # The scroll area's actual content can require more height than
        # QFormLayout.heightForWidth() reports after rows are hidden/shown.
        form_height = max(form_height, self.form_container.sizeHint().height())
        panel_layout = self._input_panel.layout()
        if panel_layout is None:
            return
        margins = panel_layout.contentsMargins()
        heights = []
        for index in range(panel_layout.count()):
            item = panel_layout.itemAt(index)
            if item is None or item.widget() is self.form_scroll or item.isEmpty():
                continue
            height = item.heightForWidth(width) if item.hasHeightForWidth() else -1
            heights.append(height if height >= 0 else item.sizeHint().height())
        overhead = margins.top() + margins.bottom() + sum(heights)
        overhead += max(0, panel_layout.spacing()) * len(heights)
        preferred = form_height + overhead + 20
        result_hint = 150 if self._splitter_customized else self.result_height_hint()
        result_minimum = min(result_hint, max(80, available * 3 // 5))
        minimum = self._input_panel.minimumSizeHint().height()
        maximum = max(minimum, available - result_minimum)
        current = self._splitter.sizes()[0]
        target = preferred
        if self._splitter_customized:
            target = current
            if available != self._last_available:
                target = round(available * self._manual_ratio)
            elif preferred > self._last_preferred and current >= self._last_preferred - 8:
                # Follow newly revealed controls only when the form previously
                # fitted. A deliberately compressed form continues to scroll.
                target += preferred - self._last_preferred
        target = max(minimum, min(target, maximum))
        self._last_preferred = preferred
        self._last_available = available
        if abs(current - target) >= 3:
            blocker = QSignalBlocker(self._splitter)
            self._splitter.setSizes([target, max(result_minimum, available - target)])
            del blocker

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._schedule_input_fit()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._schedule_input_fit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (watched is self._splitter.handle(1)
                and event.type() == QEvent.Type.MouseButtonDblClick):
            self.reset_splitter()
            return True
        if watched is self.result_table.viewport() and event.type() == QEvent.Type.Resize:
            self._empty_result.setGeometry(self.result_table.viewport().rect())
        elif (watched in (self.form_container, self._utilities) and (
            event.type() == QEvent.Type.LayoutRequest
        )) or (watched is self.form_scroll.viewport() and event.type() == QEvent.Type.Resize):
            self._schedule_input_fit()
        return super().eventFilter(watched, event)

    def set_result(self, report: dict[str, object], text: str | None = None) -> None:
        self.error.clear()
        self.error.hide()
        self._empty_result.hide()
        self._report = report
        self._transfer_button.setEnabled(True)
        self._export_button.setEnabled(True)
        self.status.setText("Complete")
        self._english_report = render_report(report) if text is None else text
        self.output.setPlainText(self._english_report)
        self.report_fields = tuple(sorted(
            StructuredReport(report).fields, key=lambda field: field_order(field, report),
        ))
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["Group", "Item", "Value"])
        for column in (0, 1):
            self.result_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.result_table.horizontalHeader().setMaximumSectionSize(270)
        self.result_table.setRowCount(len(self.report_fields))
        previous_group = ""
        for row, field in enumerate(self.report_fields):
            group, heading = field_heading(field, report)
            group_item = QTableWidgetItem(group if group != previous_group else "")
            group_item.setData(UI_TEXT_ROLE, group if group != previous_group else "")
            font = group_item.font()
            font.setBold(True)
            group_item.setFont(font)
            group_item.setToolTip(group)
            self.result_table.setItem(row, 0, group_item)
            previous_group = group
            label = QTableWidgetItem(heading)
            label.setData(UI_TEXT_ROLE, heading)
            label.setData(UI_CONTEXT_ROLE, "field")
            label.setToolTip(field.path)
            self.result_table.setItem(row, 1, label)
            display = field.text if not isinstance(field.value, list) else (
                f"{len(field.value)} items · Text report / Copy selected"
            )
            if field.value is None:
                display = "—"
            item = QTableWidgetItem(display[:4000])
            if (isinstance(field.value, (bool, list)) or field.value is None
                    or field.path.split(".")[-1] in (
                        "classification", "rounding_direction", "rounding_rule", "error",
                        "relation", "tininess_rule", "pattern_error", "representation_error",
                    )):
                item.setData(UI_TEXT_ROLE, display[:4000])
            item.setFont(self.output.font())
            item.setToolTip(display[:300])
            self.result_table.setItem(row, 2, item)
        self.copy_button.setEnabled(True)
        self.copy_selected_button.setEnabled(True)
        self.filter_results()
        self.result_ready.emit(self.title, report)
        self.translate_ui()

    def translate_ui(self) -> None:
        localize(self)
        report = self.current_report()
        if report is not None:
            self.output.setPlainText(gui_report(
                report, self._english_report if report is self._report else None
            ))
        self.filter_results()

    def filter_results(self) -> None:
        query = self._result_filter.text().casefold().strip()
        last_visible_group = ""
        for row in range(self.result_table.rowCount()):
            values = [self.result_table.item(row, column) for column in (
                range(self.result_table.columnCount())
            )]
            filtered = bool(query) and not any(
                query in (item.text() + " " + item.toolTip()).casefold()
                for item in values if item is not None
            )
            detailed = False
            grouped = self.result_table.columnCount() == 3
            if grouped and row < len(self.report_fields):
                detailed = is_detail(self.report_fields[row].path)
            hidden = filtered or (detailed and not self._show_details.isChecked() and not query)
            self.result_table.setRowHidden(row, hidden)
            if grouped:
                group_item = self.result_table.item(row, 0)
                if group_item is not None:
                    # Every row keeps its canonical group in the tooltip.
                    # Repeat its heading on the first *visible* row after filtering.
                    group = group_item.toolTip()
                    heading = group if not hidden and group != last_visible_group else ""
                    group_item.setData(UI_TEXT_ROLE, heading)
                    group_item.setText(tr(heading))
                    if not hidden:
                        last_visible_group = group

    def set_error(self, message: str) -> None:
        self.clear_output()
        self.result_invalidated.emit()
        self.error.setText(message)
        self.error.setVisible(bool(message))
        self._empty_result.setText("Calculation failed · check the input above")
        self.status.setText("Error")
        position = re.search(r"at position (\d+)", message)
        input_widget = getattr(self, "input", None)
        if position is not None and isinstance(input_widget, QLineEdit):
            input_widget.setCursorPosition(min(int(position.group(1)), len(input_widget.text())))
            input_widget.setFocus()
        self.translate_ui()

    def clear_output(self) -> None:
        self._report = None
        self._empty_result.setText("Run a calculation to see results")
        self._empty_result.show()
        self._english_report = ""
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
        self.error.hide()
        self.status.setText("Input changed · Run to update")
        self.result_invalidated.emit()
        self.translate_ui()

    def set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.cancel_button.setVisible(busy)
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
        self.translate_ui()
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
        running = self.job is not None
        self.timer.stop()
        if self.job is not None:
            self.job.cancel()
            self.job = None
            self.clear_output()
            self.status.setText("Cancelled")
        self.set_busy(False)
        if running:
            self.translate_ui()

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

    def view_state(self) -> dict[str, object]:
        toggles = {}
        for name in ("_utility_toggle", "_show_bits", "_show_special", "_show_details"):
            widget = getattr(self, name, None)
            if isinstance(widget, (QCheckBox, QToolButton)):
                toggles[name] = widget.isChecked()
        editor = getattr(self, "bit_editor", None)
        return {"splitter": self._splitter.sizes(),
                "splitter_customized": self._splitter_customized,
                "toggles": toggles,
                "bit_group_size": editor.group_width if isinstance(editor, BitEditor) else 4}

    def restore_view_state(self, state: object) -> None:
        if not isinstance(state, dict):
            return
        editor = getattr(self, "bit_editor", None)
        group = state.get("bit_group_size")
        if isinstance(editor, BitEditor) and type(group) is int and group in (4, 8):
            editor.set_group_width(group)
        # Old states stored the undersized default splitter too. Auto-fit those.
        self._splitter_customized = state.get("splitter_customized") is True
        sizes = state.get("splitter")
        if (self._splitter_customized and isinstance(sizes, list) and len(sizes) == 2
                and all(type(size) is int and 0 <= size <= 10000 for size in sizes)
                and sum(sizes) > 0):
            blocker = QSignalBlocker(self._splitter)
            self._splitter.setSizes(sizes)
            del blocker
            self._manual_ratio = sizes[0] / sum(sizes)
        elif self._splitter_customized:
            self._splitter_customized = False
        toggles = state.get("toggles")
        if isinstance(toggles, dict):
            for name, checked in toggles.items():
                if name not in ("_utility_toggle", "_show_bits", "_show_special", "_show_details"):
                    continue
                widget = getattr(self, name, None)
                if isinstance(widget, (QCheckBox, QToolButton)) and isinstance(checked, bool):
                    widget.setChecked(checked)
        self._schedule_input_fit()

    def export_report(self, format_: str | None = None) -> None:
        report = self.current_report()
        if report is None:
            return
        selected = (format_ or self._export_format.currentText()).lower()
        extension = "txt" if selected == "text" else selected
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export result"), "", f"{selected.upper()} (*.{extension})"
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
            self.error.show()
            self.translate_ui()

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
        self.invalidate_result()
        for name, value in state.items():
            widget = vars(self).get(name)
            blocker = QSignalBlocker(widget) if isinstance(widget, QWidget) else None
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
            del blocker
