"""Small deterministic numeric checks using independent standard-library oracles."""

import json
import random
import struct
import subprocess
import sys
from fractions import Fraction

from radixscope.core import (
    ExactValue,
    FixedWidthInteger,
    RoundingMode,
    analyze_arithmetic,
    decode_ieee754,
    encode_ieee754,
    encode_ieee754_special,
    evaluate_expression,
    format_exact,
    format_rounded,
    parse_number,
    trace_value,
)
from radixscope.core.limits import ComputationLimitError
from radixscope.core.overflow import ArithmeticOperation


def main() -> None:
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
    check(evaluate_expression("-2**2 + 2**-3").fraction == -4 + Fraction(1, 8))
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
    check(not trace.complete and not trace.terminates and trace.result.endswith("…"))
    for arguments in (
        ["convert", "FF", "--from", "16", "--to", "10"],
        ["expression", "0x10 + 2#11"],
        ["trace", "1/7", "--max-steps", "3"],
        ["integer", "127", "--width", "8", "--signed", "--op", "add", "--operand", "1"],
        ["ieee", "encode", "1/10", "--width", "32"],
    ):
        result = subprocess.run(
            [sys.executable, "-m", "radixscope", *arguments, "--json"],
            capture_output=True, text=True, check=True,
        )
        check(isinstance(json.loads(result.stdout), dict) and not result.stderr)
    print(f"Numeric verification: {checks} checks passed")


if __name__ == "__main__":
    main()
