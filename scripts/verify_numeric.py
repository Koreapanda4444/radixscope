"""Small deterministic numeric checks using independent standard-library oracles."""

import argparse
import json
import math
import random
import struct
import subprocess
import sys
from fractions import Fraction

from radixscope.core import (
    BitField,
    BitfieldLayout,
    ExactValue,
    FixedWidthInteger,
    IEEEFormat,
    RoundingMode,
    analyze_arithmetic,
    analyze_float_precision,
    compare_binary,
    convert_batch,
    convert_ieee754,
    decode_ieee754,
    encode_ieee754,
    encode_ieee754_special,
    evaluate_expression,
    format_exact,
    format_rounded,
    inspect_bitfields,
    parse_number,
    trace_value,
)
from radixscope.core.limits import ComputationLimitError
from radixscope.core.overflow import ArithmeticOperation


def verify_small_formats() -> None:
    patterns = 0
    for format_ in (IEEEFormat.BINARY16, IEEEFormat.BFLOAT16):
        for pattern in range(1 << 16):
            raw = pattern.to_bytes(2, "big")
            native = struct.unpack(">e", raw)[0] if format_ is IEEEFormat.BINARY16 else (
                struct.unpack(">f", raw + bytes(2))[0]
            )
            decoded = decode_ieee754(pattern, format_)
            if math.isnan(native):
                assert decoded.classification == "nan"
            elif math.isinf(native):
                assert decoded.classification == "infinity"
                assert decoded.sign_bit == int(native < 0)
            else:
                assert decoded.exact is not None
                assert decoded.exact.fraction == Fraction.from_float(native)
                negative_zero = native == 0 and math.copysign(1, native) < 0
                assert encode_ieee754(
                    decoded.exact, format_, negative_zero=negative_zero
                ).pattern == pattern
            patterns += 1
    print(f"Native-oracle verification: {patterns} complete 16-bit patterns passed")


def main(*, exhaustive: bool = False) -> None:
    checks = 0

    def check(condition: bool) -> None:
        nonlocal checks
        if not condition:
            raise AssertionError(f"numeric verification failed at check {checks + 1}")
        checks += 1

    randomizer = random.Random(4444)
    for base in range(2, 37):
        for _ in range(16):
            numerator = randomizer.randrange(-10**12, 10**12)
            denominator = randomizer.randrange(1, 80)
            value = ExactValue(numerator, denominator)
            check(parse_number(format_exact(value, base), base).fraction == (
                Fraction(numerator, denominator)
            ))
    for numerator, expected in [(5, "2"), (7, "4"), (-5, "-2"), (-7, "-4")]:
        check(format_rounded(ExactValue(numerator, 2), 10, 0) == expected)
    check(format_rounded(ExactValue(-1, 8), 10, 2, RoundingMode.FLOOR) == "-0.13")
    check(format_rounded(ExactValue(-1, 8), 10, 2, RoundingMode.CEILING) == "-0.12")
    check(evaluate_expression("0xFF + 2#11 / 10#2") == ExactValue(513, 2))
    check(parse_number("1.25e-3", 10) == ExactValue(1, 800))
    check(parse_number("1E3", 16) == ExactValue(483))
    check(evaluate_expression("10#1e-2 + 16#1E3") == ExactValue(48301, 100))
    check(parse_number("0.(3)e2", 10) == ExactValue(100, 3))
    check(evaluate_expression("-2**2 + 2**-3").fraction == -4 + Fraction(1, 8))
    for expression, expected_integer in {
        "1 | 2 ^ 3 & 4": 3, "1 << 2 + 1": 8, "32 >> 2 >> 1": 4,
        "~1 & 0xFF": 254, "-7 // 3": -3, "-7 % 3": 2,
        "(7/3) // (2/3)": 3, "2**3**2": 512,
    }.items():
        check(evaluate_expression(expression) == ExactValue(expected_integer))
    check(evaluate_expression("2**10000").numerator == 2**10000)
    check(len(str(evaluate_expression("10**5000"))) == 5001)
    try:
        evaluate_expression("2**(10**100)")
    except ComputationLimitError:
        checks += 1
    else:
        raise AssertionError("power work limit was not enforced")
    for width in (1, 5, 8, 16, 32, 64, 127):
        for signed in (False, True):
            left = FixedWidthInteger((1 << (width - int(signed))) - 1, width, signed)
            right = FixedWidthInteger(1 if width > 1 or not signed else -1, width, signed)
            analysis = analyze_arithmetic(left, right, ArithmeticOperation.ADD)
            expected_bits = (left.value + right.value) % (1 << width)
            check(analysis.wrapped.bit_pattern == expected_bits)
            check(analysis.overflowed == (not left.minimum <= (
                left.value + right.value
            ) <= left.maximum))
    for width, code in ((32, ">f"), (64, ">d")):
        for _ in range(128):
            numerator = randomizer.randrange(-10**10, 10**10)
            value = ExactValue(numerator, 256)
            expected_pattern = int.from_bytes(struct.pack(code, numerator / 256), "big")
            encoded = encode_ieee754(value, width)
            check(encoded.pattern == expected_pattern)
            decoded = decode_ieee754(encoded.pattern, width).exact
            assert decoded is not None
            check(encode_ieee754(decoded, width) == encoded)
        check(encode_ieee754(-0.0, width).sign_bit == 1)
        nan = encode_ieee754_special("nan", width, payload=7, quiet=False)
        check(decode_ieee754(nan.pattern, width).nan_payload == 7 and not nan.is_quiet_nan)
    check(encode_ieee754(ExactValue(1, 1 << 150), 32).pattern == 0)
    check(encode_ieee754(ExactValue(3, 1 << 150), 32).pattern == 2)
    check(encode_ieee754(ExactValue((1 << 24) - 1, 1 << 150), 32).pattern == 1 << 23)
    check(encode_ieee754(ExactValue((1 << 25) - 1) * ExactValue(1 << 103), 32)
          .classification == "infinity")
    trace = trace_value(ExactValue(1, 97), 10, max_steps=8)
    precision = analyze_float_precision(ExactValue(1, 10), encode_ieee754(ExactValue(1, 10), 32))
    check(precision.absolute_error == ExactValue(1, 671088640))
    check(precision.relative_error == ExactValue(1, 67108864))
    check(precision.error_ulps == ExactValue(1, 5))
    check(analyze_float_precision(ExactValue(0), encode_ieee754(0)).relative_error is None)
    for format_, one, tiny, halfway in (
        (IEEEFormat.BINARY16, 0x3C00, 24, 25),
        (IEEEFormat.BFLOAT16, 0x3F80, 133, 134),
    ):
        check(encode_ieee754(1, format_).pattern == one)
        check(encode_ieee754(ExactValue(1, 1 << tiny), format_).pattern == 1)
        check(encode_ieee754(ExactValue(1, 1 << halfway), format_).pattern == 0)
        check(decode_ieee754(one | 0x8000, format_).exact == ExactValue(-1))
        check(encode_ieee754(-0.0, format_).pattern == 0x8000)
    double_rounding = ExactValue(1) + ExactValue(1, 1 << 11) + ExactValue(1, 1 << 25)
    check(encode_ieee754(double_rounding, 16).pattern == 0x3C01)
    check(convert_ieee754(encode_ieee754(double_rounding, 32), 16).pattern == 0x3C00)
    layout = BitfieldLayout(8, (BitField("signed_byte", 0, 8, True),))
    check(BitfieldLayout.from_json(layout.to_json()) == layout)
    check(inspect_bitfields(255, 8, layout.fields)[0].integer.value == -1)
    difference = compare_binary(b"\xff\0", b"\xfe\x80")
    check(difference.changed_bits == 2 and difference.changed_bit_positions == (7, 8))
    batch = convert_batch("1\nbad!\n1e-3", mode="auto", precision=None)
    check(batch.total == 3 and bool(batch.entries[1].error))
    check(batch.entries[2].exact == ExactValue(1, 1000))
    check(convert_batch("1\n2", max_rows=1).limited)
    check(not trace.complete and not trace.terminates and trace.result.endswith("…"))
    for arguments in (
        ["convert", "FF", "--from", "16", "--to", "10"],
        ["convert", "0xFF + 1", "--auto"],
        ["expression", "0x10 + 2#11"],
        ["trace", "1/7", "--max-steps", "3"],
        ["integer", "127", "--width", "8", "--signed", "--op", "add", "--operand", "1"],
        ["ieee", "encode", "1/10", "--width", "32"],
        ["ieee", "compare", "1/10"],
        ["bytes", "3F 80 00 00"],
        ["compare", "FF00", "FE80"],
        ["batch", "0x10", "--mode", "auto"],
    ):
        result = subprocess.run(
            [sys.executable, "-m", "radixscope", *arguments, "--json"],
            capture_output=True, text=True, check=True,
        )
        check(isinstance(json.loads(result.stdout), dict) and not result.stderr)
    print(f"Numeric verification: {checks} checks passed")
    if exhaustive:
        verify_small_formats()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhaustive", action="store_true", help="check every 16-bit pattern")
    main(exhaustive=parser.parse_args().exhaustive)
