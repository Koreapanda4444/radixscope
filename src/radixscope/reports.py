import json
from dataclasses import asdict, dataclass

from radixscope.core import (
    ConversionTrace,
    ExactValue,
    FixedWidthInteger,
    IEEE754Value,
    interpret_bit_pattern,
    parse_number,
    represent_bytes,
)
from radixscope.core.batch import BatchConversion
from radixscope.core.binary_comparison import compare_binary
from radixscope.core.bitfields import BitfieldLayout
from radixscope.core.byte_inspection import parse_byte_input, select_bytes
from radixscope.core.comparison import FloatFormatComparison
from radixscope.core.ieee754 import FloatClass, IEEEFormat, convert_ieee754, encode_ieee754
from radixscope.core.inspection import NumberInspection
from radixscope.core.neighbors import adjacent_float, float_boundaries
from radixscope.core.precision import analyze_float_precision


@dataclass(frozen=True, slots=True)
class ReportField:
    path: str
    value: object

    @property
    def text(self) -> str:
        if isinstance(self.value, (dict, list)):
            return json.dumps(self.value, ensure_ascii=False)
        return str(self.value)


@dataclass(frozen=True, slots=True)
class StructuredReport:
    """Presentation adapter: legacy JSON stays unchanged, numeric data stays exact."""

    data: dict[str, object]

    @property
    def exact_value(self) -> ExactValue | None:
        exact = self.data.get("exact", self.data.get("value"))
        if isinstance(exact, int) and not isinstance(exact, bool):
            return ExactValue(exact)
        if isinstance(exact, str):
            return parse_number(exact, 10)
        return None

    @property
    def pattern(self) -> int | None:
        bits = self.data.get("bits")
        return int(bits, 2) if isinstance(bits, str) and bits else None

    @property
    def byte_data(self) -> bytes | None:
        text = self.data.get("bytes")
        return bytes.fromhex(text) if isinstance(text, str) else None

    @property
    def fields(self) -> tuple[ReportField, ...]:
        rows: list[ReportField] = []

        def flatten(path: str, value: object) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    flatten(f"{path}.{key}" if path else str(key), item)
            else:
                rows.append(ReportField(path, value))

        for key, value in self.data.items():
            flatten(key, value)
        return tuple(rows)


def integer_report(value: FixedWidthInteger, byteorder: str = "big") -> dict[str, object]:
    interpretation = interpret_bit_pattern(value.bit_pattern, value.width)
    data = represent_bytes(value, byteorder)
    return {
        "value": value.value,
        "width": value.width,
        "signed": value.signed,
        "minimum": value.minimum,
        "maximum": value.maximum,
        "unsigned": interpretation.unsigned_value,
        "twos_complement": interpretation.signed_value,
        "bits": value.bits,
        "hexadecimal": interpretation.hexadecimal,
        "byteorder": byteorder,
        "bytes": data.hexadecimal,
        "ascii": data.ascii_preview,
    }


def ieee_report(value: IEEE754Value, byteorder: str = "big") -> dict[str, object]:
    exact = value.exact
    significand = value.significand
    report: dict[str, object] = {
        "width": value.format.bit_width,
        "format": value.format.label,
        "classification": value.classification.value,
        "sign": value.sign_bit,
        "exponent_bits": value.exponent_bits,
        "fraction_bits": value.fraction_bits,
        "field_bits": {
            "sign": str(value.sign_bit),
            "exponent": format(value.exponent_bits, f"0{value.format.exponent_width}b"),
            "fraction": format(value.fraction_bits, f"0{value.format.fraction_width}b"),
        },
        "exponent": value.exponent,
        "significand": str(significand) if significand is not None else None,
        "exact": str(exact) if exact is not None else None,
        "bits": value.bits,
        "hexadecimal": value.hexadecimal,
        "quiet_nan": value.is_quiet_nan,
        "nan_payload": value.nan_payload,
        "byteorder": byteorder,
        "bytes": value.to_bytes(byteorder).hex(" ").upper(),
    }
    report.update(float_neighborhood_report(value))
    return report


def float_neighborhood_report(value: IEEE754Value) -> dict[str, object]:
    def preview(item: IEEE754Value | None) -> dict[str, object] | None:
        if item is None:
            return None
        exact = item.exact
        return {"hexadecimal": item.hexadecimal, "exact": str(exact) if exact is not None else None,
                "classification": item.classification.value}

    previous, next_ = adjacent_float(value, "down"), adjacent_float(value, "up")
    exact = value.exact
    previous_exact = previous.exact if previous is not None else None
    next_exact = next_.exact if next_ is not None else None
    boundaries = float_boundaries(value.format)
    tiny, maximum = boundaries["minimum_subnormal"].exact, boundaries["maximum_finite"].exact
    assert tiny is not None and maximum is not None
    ulp = analyze_float_precision(maximum, boundaries["maximum_finite"]).ulp
    assert ulp is not None
    return {
        "neighbors": {"previous": preview(previous), "next": preview(next_),
                      "previous_gap": str(exact - previous_exact) if (
                          exact is not None and previous_exact is not None
                      ) else None,
                      "next_gap": str(next_exact - exact) if (
                          exact is not None and next_exact is not None
                      ) else None},
        "boundaries": {name: preview(item) for name, item in boundaries.items()},
        "underflow_halfway": str(tiny / ExactValue(2)),
        "overflow_halfway": str(maximum + ulp / ExactValue(2)),
    }


def inspection_report(inspection: NumberInspection) -> dict[str, object]:
    value = inspection.value
    if isinstance(value, FixedWidthInteger):
        report = integer_report(value, inspection.byteorder)
    else:
        report = ieee_report(value, inspection.byteorder)
    interpretation = interpret_bit_pattern(inspection.pattern, inspection.width)
    report.update({
        "source_exact": (
            str(inspection.source_exact) if inspection.source_exact is not None else None
        ),
        "exact": str(inspection.exact) if inspection.exact is not None else None,
        "unsigned": interpretation.unsigned_value,
        "twos_complement": interpretation.signed_value,
        "outputs": {str(base): text for base, text in inspection.outputs.items()},
        "data_type": "integer" if isinstance(value, FixedWidthInteger) else (
            value.format.label
        ),
    })
    if isinstance(value, IEEE754Value) and inspection.source_exact is not None:
        report.update(precision_report(inspection.source_exact, value))
    return report


def precision_report(source: ExactValue, encoded: IEEE754Value) -> dict[str, object]:
    analysis = analyze_float_precision(source, encoded)
    rational_fields = {
        "absolute_error": analysis.absolute_error, "relative_error": analysis.relative_error,
        "ulp": analysis.ulp, "error_ulps": analysis.error_ulps,
    }
    report: dict[str, object] = {
        key: str(value) if value is not None else None for key, value in rational_fields.items()
    }
    report.update({
        "source_exact": str(source), "exactly_represented": analysis.exactly_represented,
        "rounding_direction": analysis.rounding_direction,
        "rounding_rule": "nearest, ties to even",
        "overflowed": encoded.classification.value == "infinity",
        "underflowed_to_zero": encoded.classification.value == "zero" and source.numerator != 0,
    })
    return report


def comparison_report(comparison: FloatFormatComparison) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    source = comparison.source
    for value in comparison.values:
        exact = value.exact
        row: dict[str, object] = {
            "format": value.format.label, "width": value.format.bit_width,
            "hexadecimal": value.hexadecimal, "bits": value.bits,
            "classification": value.classification.value,
            "exact": str(exact) if exact is not None else None,
            "precision_bits": value.format.fraction_width + 1,
            "effective_significand_bits": value.fraction_bits.bit_length() if (
                value.classification is FloatClass.SUBNORMAL
            ) else (value.format.fraction_width + 1 if (
                value.classification is FloatClass.NORMAL
            ) else 0),
        }
        if source is not None:
            row.update(precision_report(source, value))
        for intermediate in (IEEEFormat.BINARY32, IEEEFormat.BINARY64):
            different = None
            if source is not None and value.format.fraction_width < intermediate.fraction_width:
                rounded = encode_ieee754(source, intermediate, negative_zero=(
                    source.numerator == 0 and bool(value.sign_bit)
                ))
                different = convert_ieee754(rounded, value.format).pattern != value.pattern
            row[f"double_rounding_via_{intermediate.label}"] = different
        rows.append(row)
    return {"source_exact": str(source) if source is not None else None,
            "comparison": rows, "rounding_rule": "nearest, ties to even"}


def byte_report(
    text: str, input_format: str = "hex", byteorder: str = "big", offset: int = 0,
    length: int | None = None,
) -> dict[str, object]:
    data = parse_byte_input(text, input_format)
    selection = select_bytes(data, offset, length, byteorder)
    floating = []
    for value in selection.floating:
        exact = value.exact
        floating.append({
            "format": value.format.label, "hexadecimal": value.hexadecimal,
            "classification": value.classification.value,
            "exact": str(exact) if exact is not None else None,
            "quiet_nan": value.is_quiet_nan, "nan_payload": value.nan_payload,
        })
    return {
        "input_format": input_format, "byteorder": byteorder, "total_length": len(data),
        "offset": offset, "length": len(selection.data), "width": len(selection.data) * 8,
        "bytes": selection.data.hex(" ").upper(),
        "bits": "".join(f"{byte:08b}" for byte in (
            selection.data if byteorder == "big" else selection.data[::-1]
        )),
        "unsigned": str(ExactValue(selection.unsigned)),
        "exact": str(ExactValue(selection.unsigned)), "data_type": "integer", "signed": False,
        "hexadecimal": format(selection.unsigned, f"0{len(selection.data) * 2}X"),
        "twos_complement": str(ExactValue(selection.signed)),
        "ascii": selection.ascii_preview, "utf8": selection.utf8_preview,
        "utf8_valid": selection.utf8_valid, "floating": floating,
        "rows": [{"offset": position, "hex": data[position:position + 16].hex(" ").upper(),
                  "ascii": "".join(chr(byte) if 32 <= byte <= 126 else "."
                                   for byte in data[position:position + 16])}
                 for position in range(0, len(data), 16)],
    }


def trace_report(trace: ConversionTrace) -> dict[str, object]:
    return {
        "exact": str(trace.value),
        "base": trace.base,
        "sign": trace.sign,
        "result": trace.result,
        "terminates": trace.terminates,
        "complete": trace.complete,
        "recurring_start": trace.recurring_start,
        "integer_steps": [asdict(step) for step in trace.integer_steps],
        "fractional_steps": [asdict(step) for step in trace.fractional_steps],
    }


def binary_comparison_report(
    left_text: str, right_text: str, input_format: str = "hex", byteorder: str = "big",
    length_policy: str = "equal", layout_json: str = "",
) -> dict[str, object]:
    layout = BitfieldLayout.from_json(layout_json) if layout_json else None
    difference = compare_binary(
        parse_byte_input(left_text, input_format), parse_byte_input(right_text, input_format),
        byteorder=byteorder, length_policy=length_policy, fields=layout.fields if layout else (),
    )
    if layout is not None and layout.width != difference.width:
        raise ValueError("layout width must match the aligned pattern width")
    left, right = difference.aligned
    positions = difference.changed_bit_positions
    return {
        "width": difference.width, "byteorder": byteorder, "length_policy": length_policy,
        "left_original_length": len(difference.left),
        "right_original_length": len(difference.right),
        "left_zero_padding": len(left) - len(difference.left),
        "right_zero_padding": len(right) - len(difference.right),
        "original_bytes_equal": difference.left == difference.right,
        "patterns_equal": difference.changed_bits == 0,
        "left_bytes": left.hex(" ").upper(), "right_bytes": right.hex(" ").upper(),
        "xor_bytes": difference.xor.hex(" ").upper(),
        "left_bits": format(int.from_bytes(left, difference.byteorder.value),
                            f"0{difference.width}b"),
        "right_bits": format(int.from_bytes(right, difference.byteorder.value),
                             f"0{difference.width}b"),
        "changed_bits": difference.changed_bits,
        "changed_bytes": len(difference.changed_byte_offsets),
        "changed_byte_offsets": list(difference.changed_byte_offsets[:4096]),
        "changed_bit_positions": list(positions[:4096]),
        "bit_positions_complete": len(positions) <= 4096,
        "byte_positions_complete": len(difference.changed_byte_offsets) <= 4096,
        "bit_numbering": "lsb0 after byte-order decoding",
        "fields": list(difference.field_differences),
    }


def batch_report(batch: BatchConversion) -> dict[str, object]:
    return {
        "bases": list(batch.bases), "total": batch.total, "processed": len(batch.entries),
        "limited": batch.limited, "cancelled": batch.cancelled,
        "errors": sum(bool(entry.error) for entry in batch.entries),
        "rows": [{"line": entry.line, "input": entry.input,
                  "exact": str(entry.exact) if entry.exact is not None else None,
                  "outputs": {str(base): text for base, text in entry.outputs.items()},
                  "error": entry.error} for entry in batch.entries],
    }


def render_report(report: dict[str, object]) -> str:
    lines: list[str] = []
    for key, value in report.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            lines.extend(f"  {name}: {item}" for name, item in value.items())
        elif isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  {json.dumps(item, ensure_ascii=False)}" for item in value)
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)
