import json
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer

from radixscope import __version__
from radixscope.gui.app import MainWindow, create_application
from radixscope.gui.conversion import ConversionWorkspace, TraceWorkspace
from radixscope.gui.programmer import IEEEWorkspace, ProgrammerWorkspace
from radixscope.settings import SettingsStore


def run(output: Path) -> int:
    application = create_application()
    checks: list[str] = []
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="radixscope-smoke-") as directory:
        window = MainWindow(SettingsStore(Path(directory) / "state.json"))
        application.aboutToQuit.connect(window.shutdown)
        conversion, trace, programmer, ieee = window.workspaces
        assert isinstance(conversion, ConversionWorkspace)
        assert isinstance(trace, TraceWorkspace)
        assert isinstance(programmer, ProgrammerWorkspace)
        assert isinstance(ieee, IEEEWorkspace)
        window.show()
        phase = 0
        timer = QTimer(window)
        timer.setInterval(25)

        def finish() -> None:
            timer.stop()
            window.close()
            application.quit()

        def tick() -> None:
            nonlocal phase
            try:
                if phase == 0:
                    assert window.isVisible() and not application.windowIcon().isNull()
                    checks.append("gui-startup")
                    conversion.input.setText("FF")
                    conversion.source_base.setValue(16)
                    conversion.calculate()
                    phase = 1
                elif phase == 1 and conversion.job is None:
                    assert "exact: 255" in conversion.output.toPlainText(), conversion.error.text()
                    checks.append("conversion-worker")
                    trace.calculate()
                    phase = 2
                elif phase == 2 and trace.job is None:
                    assert "result: 0.(01)" in trace.output.toPlainText(), trace.error.text()
                    checks.append("trace-worker")
                    programmer.signed.setChecked(True)
                    programmer.input.setText("127")
                    programmer.operation.setCurrentText("add")
                    programmer.calculate()
                    phase = 3
                elif phase == 3 and programmer.job is None:
                    assert "overflowed: True" in programmer.output.toPlainText()
                    programmer.bit_editor.buttons[0].click()
                    assert "value: -127" in programmer.output.toPlainText()
                    checks.append("integer-worker-and-bits")
                    ieee.bit_width.setCurrentText("64")
                    ieee.input.setText("-nan")
                    ieee.payload.setText("123")
                    ieee.quiet.setChecked(False)
                    ieee.calculate()
                    phase = 4
                elif phase == 4 and ieee.job is None:
                    assert "nan_payload: 123" in ieee.output.toPlainText(), ieee.error.text()
                    ieee.bit_editor.buttons[63].click()
                    assert "nan_payload: 123" in ieee.output.toPlainText()
                    assert "quiet_nan: False" in ieee.output.toPlainText()
                    assert "sign: 0" in ieee.output.toPlainText()
                    checks.append("ieee-worker-and-bits")
                    conversion.mode.setCurrentText("Expression")
                    conversion.input.setText("2 ** 1000000000")
                    conversion.calculate()
                    phase = 5
                elif phase == 5:
                    assert conversion.job is not None
                    job = conversion.job
                    process = job.process
                    conversion.cancel_button.click()
                    assert conversion.job is None and not job.directory.exists()
                    assert process is not None and process.poll() is not None
                    assert not conversion.output.toPlainText()
                    checks.extend(["event-loop-responsive", "cancel-worker"])
                    conversion.input.setText("9")
                    conversion.calculate()
                    phase = 6
                elif phase == 6 and conversion.job is None:
                    assert "exact: 9" in conversion.output.toPlainText()
                    assert len(window.store.history) >= 4
                    checks.append("restart-after-cancel")
                    conversion.calculate()
                    finish()
                    assert all(workspace.job is None for workspace in window.workspaces)
                    checks.append("gui-shutdown")
            except Exception as error:
                failures.append(f"phase {phase}: {type(error).__name__}: {error}")
                finish()

        def timeout() -> None:
            failures.append(f"desktop verification timed out in phase {phase}")
            finish()

        timer.timeout.connect(tick)
        watchdog = QTimer(window)
        watchdog.setSingleShot(True)
        watchdog.timeout.connect(timeout)
        watchdog.start(60000)
        timer.start()
        application.exec()
        watchdog.stop()
    output.write_text(json.dumps({
        "version": __version__, "status": "failed" if failures else "ok",
        "checks": checks, "errors": failures,
    }, indent=2), encoding="utf-8")
    return 1 if failures else 0
