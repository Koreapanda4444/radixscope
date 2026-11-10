from collections.abc import Callable, Iterable
from dataclasses import dataclass

from radixscope.core.conversion import convert_bases
from radixscope.core.digits import validate_base
from radixscope.core.expression import evaluate_expression
from radixscope.core.formatting import RoundingMode, format_value
from radixscope.core.input_syntax import parse_numeric_input
from radixscope.core.limits import check_input
from radixscope.core.parse import parse_number
from radixscope.core.value import ExactValue

MAX_BATCH_ROWS = 1000
MAX_BATCH_OUTPUT = 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class BatchEntry:
    line: int
    input: str
    exact: ExactValue | None
    outputs: dict[int, str]
    error: str = ""


@dataclass(frozen=True, slots=True)
class BatchConversion:
    entries: tuple[BatchEntry, ...]
    bases: tuple[int, ...]
    total: int
    limited: bool = False
    cancelled: bool = False


def convert_batch(
    text: str,
    bases: Iterable[int] = (2, 8, 10, 16),
    *,
    source_base: int = 10,
    mode: str = "number",
    precision: int | None = 16,
    rounding: RoundingMode = RoundingMode.HALF_EVEN,
    max_rows: int = MAX_BATCH_ROWS,
    cancelled: Callable[[], bool] | None = None,
) -> BatchConversion:
    if not isinstance(text, str):
        raise TypeError("batch input must be text")
    check_input(text)
    checked_bases = tuple(validate_base(base) for base in bases)
    if not checked_bases or len(set(checked_bases)) != len(checked_bases):
        raise ValueError("batch target bases must be nonempty and unique")
    validate_base(source_base)
    if mode not in ("number", "expression", "auto"):
        raise ValueError("batch mode must be number, expression or auto")
    if (
        isinstance(max_rows, bool)
        or not isinstance(max_rows, int)
        or not 1 <= max_rows <= MAX_BATCH_ROWS
    ):
        raise ValueError("batch row limit must be 1 through 1000")
    format_value(ExactValue(0), 10, precision, rounding)
    lines = [
        (line, value.strip()) for line, value in enumerate(text.splitlines(), 1) if value.strip()
    ]
    if not lines:
        raise ValueError("batch input requires at least one nonempty line")
    entries: list[BatchEntry] = []
    output_size = 0
    limited = len(lines) > max_rows
    for line, input_ in lines[:max_rows]:
        if cancelled is not None and cancelled():
            return BatchConversion(tuple(entries), checked_bases, len(lines), limited, True)
        value = None
        try:
            value = (
                evaluate_expression(input_)
                if mode == "expression"
                else (
                    parse_numeric_input(input_)
                    if mode == "auto"
                    else parse_number(input_, source_base)
                )
            )
            outputs = convert_bases(value, checked_bases, precision, rounding)
            size = len(str(value)) + len(input_) + sum(len(text) for text in outputs.values())
            if output_size + size > MAX_BATCH_OUTPUT:
                entries.append(BatchEntry(line, input_, None, {}, "Batch output limit reached"))
                limited = True
                break
            output_size += size
            entries.append(BatchEntry(line, input_, value, outputs))
        except (ValueError, TypeError, ArithmeticError) as error:
            message = str(error)[:1000]
            output_size += len(input_) + len(message)
            entries.append(BatchEntry(line, input_, None, {}, message))
    return BatchConversion(tuple(entries), checked_bases, len(lines), limited)
