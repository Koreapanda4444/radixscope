import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from radixscope.core import ExactValue, trace_value
from radixscope.gui.conversion import ConversionWorkspace, TraceWorkspace
from tests.conftest import wait_for_workspace


def test_conversion_and_expression_controls(qt_app: QApplication) -> None:
    workspace = ConversionWorkspace()
    workspace.input.setText("FF")
    workspace.source_base.setValue(16)
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "exact: 255" in workspace.output.toPlainText()
    assert "16: FF" in workspace.output.toPlainText()
    workspace.mode.setCurrentText("Expression")
    assert not workspace.source_base.isEnabled()
    workspace.input.setText("0x10 + 2#11 / 10#2")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "exact: 35/2" in workspace.output.toPlainText()
    workspace.input.setText("1/0")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert workspace.error.text() and workspace.output.toPlainText() == ""
    workspace.close()


def test_rounding_and_duplicate_target_errors(qt_app: QApplication) -> None:
    workspace = ConversionWorkspace()
    workspace.input.setText("1/8")
    workspace.targets.setText("10")
    workspace.exact_output.setChecked(False)
    workspace.precision.setValue(2)
    assert workspace.precision.isEnabled()
    workspace.rounding.setCurrentText("half-up")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "10: 0.13" in workspace.output.toPlainText()
    workspace.targets.setText("2, 2")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "unique" in workspace.error.text()
    workspace.close()


def test_trace_reports_partial_output_and_recurring_cycle(qt_app: QApplication) -> None:
    workspace = TraceWorkspace()
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "result: 0.(01)" in workspace.output.toPlainText()
    workspace.limit.setValue(1)
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert "complete: False" in workspace.output.toPlainText()
    assert "result: 0.0\u2026" in workspace.output.toPlainText()
    workspace.input.setText("bad")
    workspace.run_button.click()
    wait_for_workspace(workspace, qt_app)
    assert workspace.error.text()
    workspace.close()


def test_bounded_trace_distinguishes_partial_terminated_and_recurring() -> None:
    partial = trace_value(ExactValue(-22, 7), 10, max_steps=2)
    assert partial.value == ExactValue(-22, 7)
    assert partial.result == "-3.14\u2026"
    assert not partial.complete and not partial.terminates
    terminated = trace_value(ExactValue(1, 2), 10, max_steps=1)
    assert terminated.complete and terminated.terminates
    recurring = trace_value(ExactValue(1, 3), 10, max_steps=1)
    assert recurring.complete and not recurring.terminates
    for limit in (0, -1, True):
        with pytest.raises(ValueError):
            trace_value(ExactValue(1, 7), 10, max_steps=limit)


def test_running_calculation_keeps_events_live_and_discards_changed_input(
    qt_app: QApplication,
) -> None:
    workspace = ConversionWorkspace()
    workspace.mode.setCurrentText("Expression")
    workspace.input.setText("2 ** 1000000000")
    workspace.calculate()
    assert workspace.job is not None and workspace.cancel_button.isEnabled()
    process = workspace.job.process
    heartbeat: list[bool] = []
    QTimer.singleShot(0, lambda: heartbeat.append(True))
    qt_app.processEvents()
    assert heartbeat == [True]
    workspace.input.setText("7")
    assert workspace.job is None and process is not None and process.poll() is not None
    assert not workspace.output.toPlainText()
    workspace.calculate()
    wait_for_workspace(workspace, qt_app)
    assert "exact: 7" in workspace.output.toPlainText()
    workspace.calculate()
    workspace.cancel_button.click()
    assert workspace.status.text() == "Cancelled" and not workspace.output.toPlainText()
    workspace.calculate()
    job = workspace.job
    assert job is not None
    workspace.close()
    assert workspace.job is None and not job.directory.exists()
