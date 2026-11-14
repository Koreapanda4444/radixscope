import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from radixscope.cli import run_command
from radixscope.core import (
    RoundingMode,
    convert_bases,
    convert_batch,
    evaluate_expression,
    inspect_number,
    parse_number,
    parse_numeric_input,
    trace_value,
    validate_base,
)
from radixscope.reports import (
    StructuredReport,
    batch_report,
    inspection_report,
    render_report,
    trace_report,
)

MAX_RESULT_BYTES = 8 * 1024 * 1024


def calculate(workspace: str, state: dict[str, object]) -> dict[str, object]:
    def text(name: str) -> str:
        value = state[name]
        if not isinstance(value, str):
            raise ValueError(f"{name} must be text")
        return value

    def integer(name: str) -> int:
        value = state[name]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        return value

    def flag(name: str) -> bool:
        value = state[name]
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")
        return value

    input_text = text("input")
    if workspace == "Calculation":
        if text("calculation_mode") == "Fixed-width integer":
            return calculate("Programmer", state)
        adapted = dict(state, mode="Expression", source_base=10)
        return calculate("Conversion", adapted)
    if workspace == "Batch Conversion":
        return batch_report(convert_batch(
            input_text, [int(base.strip()) for base in text("targets").split(",")],
            source_base=integer("source_base"), mode=text("mode").lower(),
            precision=None if flag("exact_output") else integer("precision"),
            rounding=RoundingMode(text("rounding")), max_rows=integer("row_limit"),
        ))
    if workspace == "Number Inspector":
        expression = state.get("input_mode") == "Expression" and not flag("pattern")
        source = str(evaluate_expression(input_text)) if expression and (
            input_text.strip().lower().lstrip("+-") not in ("nan", "inf", "infinity")
        ) else input_text
        report = inspection_report(inspect_number(
            source, base=10 if expression else integer("base"), width=integer("bit_width"),
            signed=flag("signed"), data_type=text("data_type"), raw=flag("pattern"),
            byteorder=text("byteorder"),
        ))
        report["input"] = input_text
        return report
    if workspace == "Conversion":
        value = (
            evaluate_expression(input_text) if text("mode") == "Expression"
            else parse_numeric_input(input_text) if text("mode") == "Auto"
            else parse_number(input_text, integer("source_base"))
        )
        bases = [validate_base(int(part.strip())) for part in text("targets").split(",")]
        if len(set(bases)) != len(bases):
            raise ValueError("target bases must be unique")
        incomplete: list[int] = []
        if flag("exact_output"):
            outputs: dict[int, str] = {}
            for base in bases:
                trace = trace_value(value, base, max_steps=1000)
                outputs[base] = trace.result
                if not trace.complete:
                    incomplete.append(base)
        else:
            outputs = convert_bases(
                value, bases, integer("precision"), RoundingMode(text("rounding"))
            )
        report = {
            "input": input_text, "exact": str(value),
            "outputs": {str(base): result for base, result in outputs.items()},
        }
        if incomplete:
            report["display_limit_reached_in_bases"] = incomplete
        if state.get("show_trace") is True:
            report["trace"] = trace_report(trace_value(
                value, integer("target_base"), max_steps=integer("limit")
            ))
        return report
    if workspace == "Trace":
        report = trace_report(trace_value(
            parse_number(input_text, integer("source_base")),
            integer("target_base"), max_steps=integer("limit"),
        ))
    elif workspace == "Programmer":
        operation = text("operation")
        report = run_command(argparse.Namespace(
            command="integer", value=input_text, base=integer("base"),
            width=integer("bit_width"), signed=flag("signed"), pattern=flag("pattern"),
            byteorder=text("byteorder"), op=None if operation == "inspect" else operation,
            operand=text("operand") if operation not in ("inspect", "not") else None,
            extract=(integer("extract_offset"), integer("extract_width"))
            if state.get("extract") is True else None,
        ))
        report["operation"] = operation
    elif workspace == "IEEE 754":
        encoding = text("mode") == "encode"
        nan = input_text.strip().lower().lstrip("+-") == "nan"
        report = run_command(argparse.Namespace(
            command="ieee", mode="compare" if state.get("compare") is True else text("mode"),
            value=input_text,
            width=text("bit_width"), base=integer("base"), byteorder=text("byteorder"),
            negative_zero=encoding and not nan and flag("negative_zero"),
            payload=int(text("payload")) if encoding and nan else 0,
            signaling=encoding and nan and not flag("quiet"),
        ))
    else:
        raise ValueError("unknown workspace")
    report["input"] = input_text
    return report


def execute_request(directory: Path) -> int:
    try:
        request = json.loads((directory / "request.json").read_text(encoding="utf-8"))
        report = calculate(request["workspace"], request["state"])
        result: dict[str, object] = {"report": report, "text": render_report(report)}
        content = json.dumps(result, ensure_ascii=False).encode("utf-8")
        if len(content) > MAX_RESULT_BYTES:
            raise ValueError("Result exceeds the desktop size limit; reduce input or trace steps")
    except (ValueError, TypeError, ArithmeticError, KeyError, OSError, RecursionError) as error:
        content = json.dumps({"error": str(error)[:2000]}).encode("utf-8")
    temporary = directory / "result.tmp"
    temporary.write_bytes(content)
    os.replace(temporary, directory / "result.json")
    return 0


@dataclass(frozen=True)
class CalculationResult:
    report: dict[str, object] | None = None
    text: str = ""
    error: str = ""

    @property
    def structured(self) -> StructuredReport | None:
        return StructuredReport(self.report) if self.report is not None else None


class CalculationJob:
    def __init__(self, workspace: str, state: dict[str, object]) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="radixscope-job-")
        self.directory = Path(self._temporary.name)
        self.process: subprocess.Popen[bytes] | None = None
        try:
            (self.directory / "request.json").write_text(
                json.dumps({"workspace": workspace, "state": state}), encoding="utf-8"
            )
            command = (
                [sys.executable, "--worker", str(self.directory)]
                if getattr(sys, "frozen", False)
                else [sys.executable, "-m", "radixscope.worker", str(self.directory)]
            )
            self.process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)),
            )
        except BaseException:
            self._temporary.cleanup()
            raise

    def poll(self) -> CalculationResult | None:
        process = self.process
        if process is None:
            raise RuntimeError("job is already closed")
        exit_code = process.poll()
        if exit_code is None:
            return None
        try:
            if exit_code != 0:
                return CalculationResult(error=f"Calculation process exited with code {exit_code}")
            path = self.directory / "result.json"
            if path.stat().st_size > MAX_RESULT_BYTES:
                return CalculationResult(error="Calculation result is too large")
            result = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(result.get("error"), str):
                return CalculationResult(error=result["error"])
            report, text = result.get("report"), result.get("text")
            if not isinstance(report, dict) or not isinstance(text, str):
                return CalculationResult(error="Invalid calculation response")
            return CalculationResult(report=report, text=text)
        except (OSError, ValueError, AttributeError) as error:
            return CalculationResult(error=f"Could not read calculation result: {error}")
        finally:
            self.process = None
            self._temporary.cleanup()

    def cancel(self) -> None:
        process = self.process
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            self.process = None
        self._temporary.cleanup()
