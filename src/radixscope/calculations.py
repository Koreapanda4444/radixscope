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
    IEEEFormat,
    IntegerRangeError,
    RoundingMode,
    compare_numeric_inputs,
    convert_bases,
    convert_batch,
    evaluate_expression,
    experiment_float_arithmetic,
    inspect_number,
    parse_float_operand,
    parse_number,
    parse_numeric_input,
    trace_value,
    validate_base,
)
from radixscope.core.formatting import format_preview
from radixscope.reports import (
    StructuredReport,
    batch_report,
    float_arithmetic_report,
    inspection_report,
    integer_width_report,
    numeric_comparison_report,
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
    if workspace == "Calculation" and text("calculation_mode") != "Fixed-width integer":
        adapted = dict(state, mode="Expression", source_base=10, show_trace=False)
        report = calculate("Conversion", adapted)
        exact = parse_number(str(report["exact"]), 10)
        if exact.is_integer:
            report["width_requirements"] = integer_width_report(
                exact.numerator, integer("bit_width"), flag("signed")
            )
        return report
    if workspace == "Batch Conversion":
        return batch_report(convert_batch(
            input_text, [int(base.strip()) for base in text("targets").split(",")],
            source_base=integer("source_base"), mode=text("mode").lower(),
            precision=None if flag("exact_output") else integer("precision"),
            rounding=RoundingMode(text("rounding")), max_rows=integer("row_limit"),
        ))
    if workspace == "Number Inspector":
        if state.get("analysis") == "Floating-point arithmetic":
            fmt = text("data_type")
            left = parse_float_operand(input_text, fmt, raw=flag("pattern"), base=integer("base"))
            right = parse_float_operand(text("other_input"), fmt, raw=flag("pattern"),
                                        base=integer("base"))
            report = float_arithmetic_report(experiment_float_arithmetic(
                left, right, text("float_operation"), fmt
            ), text("byteorder"))
            report["input"] = input_text
            return report
        if state.get("analysis") == "Numeric comparison":
            report = numeric_comparison_report(compare_numeric_inputs(
                input_text, text("other_input"), base=integer("base"), width=integer("bit_width"),
                signed=flag("signed"), data_type=text("data_type"), raw=flag("pattern"),
                expressions=state.get("input_mode") == "Expression",
            ), text("byteorder"))
            report["input"] = input_text
            return report
        raw = flag("pattern") and state.get("analysis") != "Format comparison"
        special = input_text.strip().lower().lstrip("+-") in ("nan", "inf", "infinity")
        expression = state.get("input_mode") == "Expression" and not raw
        source = input_text if special or raw else str(
            evaluate_expression(input_text) if expression else (
                parse_number(input_text, integer("base"))
            )
        )
        comparison = state.get("analysis") == "Format comparison"
        if comparison or (text("data_type") != "integer" and not raw):
            fmt = text("data_type") if text("data_type") != "integer" else "binary32"
            report = run_command(argparse.Namespace(
                command="ieee", mode="compare" if comparison else "encode", value=source,
                width=fmt, base=integer("base"), byteorder=text("byteorder"),
                negative_zero=state.get("negative_zero") is True or (
                    input_text.strip().startswith("-") and not special and parse_number(source, 10)
                    == parse_number("0", 10)
                ), payload=int(text("payload")) if special and source.lower().lstrip("+-") == "nan"
                and not comparison else 0,
                signaling=state.get("quiet") is False and source.lower().lstrip("+-") == "nan"
                and not comparison,
            ))
            if not comparison:
                bits = report["bits"]
                assert isinstance(bits, str)
                numeric = inspection_report(inspect_number(
                    str(int(bits, 2)), width=IEEEFormat[fmt.upper()].bit_width,
                    data_type=fmt, raw=True, byteorder=text("byteorder"),
                ))
                numeric.update(report)
                report = numeric
        else:
            try:
                report = inspection_report(inspect_number(
                    source, base=integer("base") if raw else 10, width=integer("bit_width"),
                    signed=flag("signed"), data_type=text("data_type"), raw=raw,
                    byteorder=text("byteorder"),
                ))
            except IntegerRangeError as error:
                if raw or text("data_type") != "integer":
                    raise
                exact = parse_number(source, 10)
                report = {
                    "exact": str(exact), "representation_error": str(error),
                    "width_requirements": integer_width_report(
                        exact.numerator, integer("bit_width"), flag("signed")
                    ),
                }
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
                outputs[base], complete = format_preview(value, base)
                if not complete:
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
    elif workspace == "Calculation":
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
