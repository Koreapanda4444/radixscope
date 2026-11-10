import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from radixscope import __version__
from radixscope.core import (
    ArithmeticOperation,
    ExactValue,
    FixedWidthInteger,
    FloatClass,
    RoundingMode,
    analyze_arithmetic,
    convert_bases,
    decode_ieee754,
    encode_ieee754,
    encode_ieee754_special,
    evaluate_expression,
    parse_integer,
    parse_number,
    trace_value,
)
from radixscope.core.bitfields import BitfieldLayout, inspect_bitfields
from radixscope.core.comparison import compare_float_formats
from radixscope.core.input_syntax import parse_numeric_input
from radixscope.core.inspection import inspect_number
from radixscope.reports import (
    binary_comparison_report,
    byte_report,
    comparison_report,
    ieee_report,
    inspection_report,
    integer_report,
    precision_report,
    render_report,
    trace_report,
)


def _output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="print a JSON object")


def _conversion_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--to", type=int, nargs="+", default=[2, 8, 10, 16], dest="bases")
    parser.add_argument("--precision", type=int, help="fractional digits; omitted means exact")
    parser.add_argument("--rounding", choices=list(RoundingMode), default=RoundingMode.HALF_EVEN)
    _output_options(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="radixscope", description="Exact numbers and raw bits")
    parser.add_argument("--version", action="version", version=f"RadixScope {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    compare = commands.add_parser("compare", help="compare two raw bit or byte patterns")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--input-format", choices=["hex", "binary", "base64", "utf8"],
                         default="hex")
    compare.add_argument("--byteorder", choices=["big", "little"], default="big")
    compare.add_argument("--length-policy", choices=["equal", "zero-extend"], default="equal")
    compare.add_argument("--layout", help="saved bitfield layout JSON")
    _output_options(compare)
    byte_parser = commands.add_parser("bytes", help="interpret raw bytes and selected ranges")
    byte_parser.add_argument("value")
    byte_parser.add_argument("--input-format", choices=["hex", "binary", "base64", "utf8"],
                             default="hex")
    byte_parser.add_argument("--byteorder", choices=["big", "little"], default="big")
    byte_parser.add_argument("--offset", type=int, default=0)
    byte_parser.add_argument("--length", type=int)
    byte_parser.add_argument("--layout", help="saved bitfield layout JSON for this selection")
    _output_options(byte_parser)
    inspect = commands.add_parser("inspect", help="inspect numeric, bit and byte representations")
    inspect.add_argument("value")
    inspect.add_argument("--base", type=int, default=10)
    inspect.add_argument("--width", type=int, default=32)
    inspect.add_argument(
        "--type", choices=["integer", "binary16", "bfloat16", "binary32", "binary64"],
        default="integer",
    )
    inspect.add_argument("--signed", action="store_true")
    inspect.add_argument("--pattern", action="store_true")
    inspect.add_argument("--byteorder", choices=["big", "little"], default="big")
    _output_options(inspect)
    convert = commands.add_parser("convert", help="convert a number between bases 2 through 36")
    convert.add_argument("value")
    convert.add_argument("--from", type=int, default=10, dest="source_base")
    convert.add_argument(
        "--auto", action="store_true", help="detect input syntax; overrides --from"
    )
    _conversion_options(convert)
    expression = commands.add_parser("expression", help="evaluate an exact mixed-base expression")
    expression.add_argument("value")
    _conversion_options(expression)
    trace = commands.add_parser("trace", help="show integer division and fractional multiplication")
    trace.add_argument("value")
    trace.add_argument("--from", type=int, default=10, dest="source_base")
    trace.add_argument("--to", type=int, default=2, dest="target_base")
    trace.add_argument(
        "--max-steps", type=int, help="limit fractional trace steps (positive integer)"
    )
    _output_options(trace)
    integer = commands.add_parser("integer", help="inspect fixed-width integers and operations")
    integer.add_argument("value")
    integer.add_argument("--base", type=int, default=10)
    integer.add_argument("--width", type=int, default=32)
    integer.add_argument("--signed", action="store_true")
    integer.add_argument(
        "--pattern", action="store_true", help="interpret input as unsigned raw bits"
    )
    integer.add_argument(
        "--op",
        choices=["add", "subtract", "multiply", "and", "or", "xor", "not", "shl", "shr", "lshr"],
    )
    integer.add_argument("--operand", help="same-base operand; shifts use a decimal count")
    integer.add_argument("--byteorder", choices=["big", "little"], default="big")
    _output_options(integer)
    ieee = commands.add_parser("ieee", help="encode values or decode IEEE 754 raw bits")
    ieee.add_argument("mode", choices=["encode", "decode", "compare"])
    ieee.add_argument(
        "value", help="exact expression/special value for encode, raw integer for decode"
    )
    ieee.add_argument("--width", type=int, choices=[16, 32, 64], default=64)
    ieee.add_argument(
        "--format", choices=["binary16", "bfloat16", "binary32", "binary64"],
        help="named format; overrides --width",
    )
    ieee.add_argument("--base", type=int, default=16, help="raw pattern base for decode")
    ieee.add_argument("--byteorder", choices=["big", "little"], default="big")
    ieee.add_argument("--negative-zero", action="store_true")
    ieee.add_argument("--payload", type=int, default=0, help="NaN payload excluding the quiet bit")
    ieee.add_argument("--signaling", action="store_true", help="construct a signaling NaN")
    _output_options(ieee)
    return parser


def _integer_command(args: argparse.Namespace) -> dict[str, object]:
    exact = parse_integer(args.value, args.base)
    if args.pattern:
        value = FixedWidthInteger.from_bit_pattern(exact.numerator, args.width, args.signed)
    else:
        value = FixedWidthInteger.from_exact(exact, args.width, args.signed)
    operation = args.op
    if operation is None:
        if args.operand is not None:
            raise ValueError("--operand requires --op")
        return integer_report(value, args.byteorder)
    if operation == "not":
        if args.operand is not None:
            raise ValueError("not does not take an operand")
        return integer_report(~value, args.byteorder)
    if args.operand is None:
        raise ValueError(f"{operation} requires --operand")
    if operation in ("shl", "shr", "lshr"):
        count = parse_integer(args.operand, 10).numerator
        if operation == "shl":
            result = value << count
        elif operation == "shr":
            result = value >> count
        else:
            result = value.logical_right_shift(count)
        return integer_report(result, args.byteorder)
    right = FixedWidthInteger.from_text(args.operand, args.base, args.width, args.signed)
    if operation in ("add", "subtract", "multiply"):
        analysis = analyze_arithmetic(value, right, ArithmeticOperation(operation))
        report = integer_report(analysis.wrapped, args.byteorder)
        report.update({"exact_result": analysis.exact_value, "overflowed": analysis.overflowed})
        return report
    if operation == "and":
        result = value & right
    elif operation == "or":
        result = value | right
    else:
        result = value ^ right
    return integer_report(result, args.byteorder)


def _ieee_command(args: argparse.Namespace) -> dict[str, object]:
    width = getattr(args, "format", None) or args.width
    if args.mode == "compare":
        if args.payload or args.signaling:
            raise ValueError("NaN payload options require single-format encoding")
        text = args.value.strip().lower()
        comparison_input = float(text) if text.lstrip("+-") in ("nan", "inf", "infinity") else (
            evaluate_expression(args.value)
        )
        negative_zero = args.negative_zero or (
            text.startswith("-") and comparison_input == ExactValue(0)
        )
        return comparison_report(compare_float_formats(
            comparison_input, negative_zero=negative_zero
        ))
    if args.mode == "decode":
        if args.negative_zero or args.payload or args.signaling:
            raise ValueError("special-value encoding options cannot be used with decode")
        pattern = parse_integer(args.value, args.base).numerator
        return ieee_report(decode_ieee754(pattern, width), args.byteorder)
    text = args.value.strip().lower()
    sign = int(text.startswith("-"))
    unsigned = text[1:] if text.startswith(("+", "-")) else text
    source: ExactValue | None = None
    if unsigned in ("nan", "inf", "infinity"):
        if args.negative_zero:
            raise ValueError("negative_zero requires a zero value")
        kind = FloatClass.NAN if unsigned == "nan" else FloatClass.INFINITY
        if kind is not FloatClass.NAN and args.signaling:
            raise ValueError("--signaling requires NaN")
        value = encode_ieee754_special(
            kind, width, sign_bit=sign, payload=args.payload, quiet=not args.signaling
        )
    else:
        if args.payload or args.signaling:
            raise ValueError("--payload and --signaling require NaN")
        exact = evaluate_expression(args.value)
        source = exact
        negative_zero = args.negative_zero or (text.startswith("-") and exact == ExactValue(0))
        value = encode_ieee754(exact, width, negative_zero=negative_zero)
    report = ieee_report(value, args.byteorder)
    if source is not None:
        report.update(precision_report(source, value))
    return report


def run_command(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "compare":
        comparison_layout = ""
        if args.layout:
            path = Path(args.layout)
            if path.stat().st_size > 1024 * 1024:
                raise ValueError("bitfield layout exceeds 1 MiB")
            comparison_layout = path.read_text(encoding="utf-8")
        return binary_comparison_report(
            args.left, args.right, args.input_format, args.byteorder, args.length_policy,
            comparison_layout
        )
    if args.command == "bytes":
        report = byte_report(
            args.value, args.input_format, args.byteorder, args.offset, args.length
        )
        if getattr(args, "layout", None):
            path = Path(args.layout)
            if path.stat().st_size > 1024 * 1024:
                raise ValueError("bitfield layout exceeds 1 MiB")
            layout = BitfieldLayout.from_json(path.read_text(encoding="utf-8"))
            if layout.width != report["width"]:
                raise ValueError("layout width must match the byte selection")
            bits = report["bits"]
            assert isinstance(bits, str)
            values = inspect_bitfields(int(bits, 2), layout.width, layout.fields)
            report["fields"] = [{
                "name": value.field.name, "offset": value.field.offset,
                "width": value.field.width, "signed": value.field.signed,
                "value": str(value.integer.exact), "bits": value.integer.bits,
                "hexadecimal": format(value.integer.bit_pattern, "X"),
            } for value in values]
        return report
    if args.command == "inspect":
        return inspection_report(inspect_number(
            args.value, base=args.base, width=args.width, signed=args.signed,
            data_type=args.type, raw=args.pattern, byteorder=args.byteorder,
        ))
    if args.command == "integer":
        return _integer_command(args)
    if args.command == "ieee":
        return _ieee_command(args)
    if args.command == "expression":
        value = evaluate_expression(args.value)
    else:
        value = parse_numeric_input(args.value) if getattr(args, "auto", False) else (
            parse_number(args.value, args.source_base)
        )
    if args.command == "trace":
        return trace_report(trace_value(value, args.target_base, max_steps=args.max_steps))
    outputs = convert_bases(value, args.bases, args.precision, RoundingMode(args.rounding))
    return {"exact": str(value), "outputs": {str(base): text for base, text in outputs.items()}}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_command(args)
        _write_output(json.dumps(report) if args.json else render_report(report), sys.stdout)
    except (ValueError, TypeError, ArithmeticError, OSError) as error:
        _write_output(f"radixscope: {error}", sys.stderr)
        return 2
    return 0


def _write_output(text: str, stream: TextIO) -> None:
    try:
        print(text, file=stream)
    except UnicodeEncodeError:
        encoding = stream.encoding or "utf-8"
        print(text.encode(encoding, errors="backslashreplace").decode(encoding), file=stream)
