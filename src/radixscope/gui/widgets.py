from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QCloseEvent, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from radixscope.calculations import CalculationJob
from radixscope.reports import render_report


class Workspace(QWidget):
    result_ready = Signal(str, object)
    result_invalidated = Signal()

    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.title = title
        self.job: CalculationJob | None = None
        self.job_state: dict[str, object] = {}
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll_calculation)
        self.form = QFormLayout()
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.output.setAccessibleName(f"{title} result")
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
        self.copy_button.clicked.connect(self.copy_result)
        actions = QHBoxLayout()
        actions.addWidget(self.run_button)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.status)
        actions.addStretch()
        actions.addWidget(self.copy_button)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("heading")
        subtitle = QLabel(description)
        subtitle.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addLayout(self.form)
        layout.addLayout(actions)
        layout.addWidget(self.error)
        layout.addWidget(self.output, 1)

    def set_result(self, report: dict[str, object], text: str | None = None) -> None:
        self.error.clear()
        self.status.setText("Complete")
        self.output.setPlainText(render_report(report) if text is None else text)
        self.result_ready.emit(self.title, report)

    def set_error(self, message: str) -> None:
        self.output.clear()
        self.error.setText(message)
        self.status.setText("Error")

    def bind_inputs(self) -> None:
        for widget in vars(self).values():
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self.invalidate_result)
            elif isinstance(widget, QCheckBox):
                widget.toggled.connect(self.invalidate_result)
            elif isinstance(widget, QSpinBox):
                widget.valueChanged.connect(self.invalidate_result)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.invalidate_result)

    def invalidate_result(self) -> None:
        self.cancel_calculation()
        self.output.clear()
        self.error.clear()
        self.status.setText("Ready")
        self.result_invalidated.emit()

    def set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.copy_button.setEnabled(not busy)

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
            self.output.clear()
            self.status.setText("Cancelled")
        self.set_busy(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cancel_calculation()
        super().closeEvent(event)

    def copy_result(self) -> None:
        QApplication.clipboard().setText(self.output.toPlainText())

    def snapshot(self) -> dict[str, object]:
        state: dict[str, object] = {}
        for name, widget in vars(self).items():
            if isinstance(widget, QLineEdit):
                state[name] = widget.text()
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
