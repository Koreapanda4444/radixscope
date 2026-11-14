"""Single-operation, round-to-nearest-even experiments using exact rational arithmetic."""

from dataclasses import dataclass
from enum import StrEnum

from radixscope.core.expression import evaluate_expression
from radixscope.core.ieee754 import (
    FloatClass,
    IEEE754Value,
    IEEEFormat,
    _validate_format,
    convert_ieee754,
    decode_ieee754,
    encode_ieee754,
    encode_ieee754_special,
)
from radixscope.core.limits import MAX_COMPUTED_BITS, ComputationLimitError
from radixscope.core.parse import parse_integer
from radixscope.core.precision import power_of_two
from radixscope.core.value import ExactValue

FloatOperand = ExactValue | IEEE754Value


class FloatOperation(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


@dataclass(frozen=True, slots=True)
class FloatFlags:
    invalid: bool = False
    divide_by_zero: bool = False
    overflow: bool = False
    underflow: bool = False
    inexact: bool = False


@dataclass(frozen=True, slots=True)
class FloatArithmeticPath:
    exact: ExactValue | None
    value: IEEE754Value
    flags: FloatFlags


@dataclass(frozen=True, slots=True)
class FloatArithmeticExperiment:
    operation: FloatOperation
    left_source: FloatOperand
    right_source: FloatOperand
    left: IEEE754Value
    right: IEEE754Value
    left_conversion: FloatFlags
    right_conversion: FloatFlags
    rounded_operands: FloatArithmeticPath
    exact_then_round: FloatArithmeticPath


def _exact(value: FloatOperand) -> ExactValue | None:
    return value if isinstance(value, ExactValue) else value.exact


def _sign(value: FloatOperand) -> int:
    return int(value.numerator < 0) if isinstance(value, ExactValue) else value.sign_bit


def _is(value: FloatOperand, kind: FloatClass) -> bool:
    return isinstance(value, IEEE754Value) and value.classification is kind


def _check_budget(value: ExactValue) -> None:
    if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > MAX_COMPUTED_BITS:
        raise ComputationLimitError("floating-point experiment exceeds the computation budget")


def _round_finite(value: ExactValue, fmt: IEEEFormat, sign: int = 0) -> FloatArithmeticPath:
    _check_budget(value)
    encoded = encode_ieee754(value, fmt, negative_zero=value.numerator == 0 and bool(sign))
    overflow = encoded.classification is FloatClass.INFINITY
    inexact = overflow or encoded.exact != value
    # Tininess AFTER rounding uses an unbounded exponent range at the destination
    # precision, not merely the final subnormal classification (SoftFloat FAQ).
    minimum_normal = power_of_two(1 - fmt.bias)
    minimum_subnormal = power_of_two(1 - fmt.bias - fmt.fraction_width)
    threshold = minimum_normal - minimum_subnormal / ExactValue(4)
    tiny = value.numerator != 0 and abs(value).fraction < threshold.fraction
    return FloatArithmeticPath(value, encoded, FloatFlags(
        overflow=overflow, underflow=tiny and inexact, inexact=inexact
    ))


def _evaluate(
    left: FloatOperand, right: FloatOperand, operation: FloatOperation, fmt: IEEEFormat,
) -> FloatArithmeticPath:
    def special(kind: FloatClass, sign: int = 0, *, invalid: bool = False,
                divide_by_zero: bool = False) -> FloatArithmeticPath:
        return FloatArithmeticPath(None, encode_ieee754_special(kind, fmt, sign_bit=sign),
                                   FloatFlags(invalid=invalid, divide_by_zero=divide_by_zero))

    nans = [value for value in (left, right) if _is(value, FloatClass.NAN)]
    if nans:
        first = nans[0]
        assert isinstance(first, IEEE754Value)
        invalid = any(isinstance(v, IEEE754Value) and not v.is_quiet_nan for v in nans)
        nan_result = encode_ieee754_special(FloatClass.NAN, fmt, sign_bit=first.sign_bit,
                                        payload=first.nan_payload or 0, quiet=True)
        return FloatArithmeticPath(None, nan_result, FloatFlags(invalid=invalid))
    a, b = _exact(left), _exact(right)
    sign_a, sign_b = _sign(left), _sign(right)
    inf_a, inf_b = _is(left, FloatClass.INFINITY), _is(right, FloatClass.INFINITY)
    if operation in (FloatOperation.ADD, FloatOperation.SUBTRACT):
        effective_sign_b = sign_b ^ int(operation is FloatOperation.SUBTRACT)
        if inf_a or inf_b:
            if inf_a and inf_b and sign_a != effective_sign_b:
                return special(FloatClass.NAN, invalid=True)
            return special(FloatClass.INFINITY, sign_a if inf_a else effective_sign_b)
        assert a is not None and b is not None
        result = a + b if operation is FloatOperation.ADD else a - b
        zero_sign = int(sign_a == effective_sign_b == 1)
        return _round_finite(result, fmt, zero_sign)
    sign = sign_a ^ sign_b
    if operation is FloatOperation.MULTIPLY:
        if (inf_a and b == ExactValue(0)) or (inf_b and a == ExactValue(0)):
            return special(FloatClass.NAN, invalid=True)
        if inf_a or inf_b:
            return special(FloatClass.INFINITY, sign)
        assert a is not None and b is not None
        return _round_finite(a * b, fmt, sign)
    if (inf_a and inf_b) or (a == ExactValue(0) and b == ExactValue(0)):
        return special(FloatClass.NAN, invalid=True)
    if inf_a:
        return special(FloatClass.INFINITY, sign)
    if inf_b:
        return FloatArithmeticPath(ExactValue(0), encode_ieee754_special(
            FloatClass.ZERO, fmt, sign_bit=sign
        ), FloatFlags())
    assert a is not None and b is not None
    if b.numerator == 0:
        return special(FloatClass.INFINITY, sign, divide_by_zero=True)
    return _round_finite(a / b, fmt, sign)


def experiment_float_arithmetic(
    left: FloatOperand, right: FloatOperand, operation: FloatOperation | str = FloatOperation.ADD,
    format_: object = IEEEFormat.BINARY32,
) -> FloatArithmeticExperiment:
    fmt, op = _validate_format(format_), FloatOperation(operation)
    def convert(value: FloatOperand) -> FloatArithmeticPath:
        if isinstance(value, ExactValue):
            return _round_finite(value, fmt)
        if not isinstance(value, IEEE754Value):
            raise TypeError("operands must be exact numbers or IEEE values")
        if value.exact is not None:
            return _round_finite(value.exact, fmt, value.sign_bit)
        return FloatArithmeticPath(None, convert_ieee754(value, fmt), FloatFlags())
    a, b = convert(left), convert(right)
    return FloatArithmeticExperiment(op, left, right, a.value, b.value, a.flags, b.flags,
                                     _evaluate(a.value, b.value, op, fmt),
                                     _evaluate(left, right, op, fmt))


def parse_float_operand(
    text: str, format_: object = IEEEFormat.BINARY32, *, raw: bool = False, base: int = 16,
) -> FloatOperand:
    fmt = _validate_format(format_)
    if raw:
        return decode_ieee754(parse_integer(text, base).numerator, fmt)
    normalized = text.strip().lower()
    special = normalized.lstrip("+-")
    if special in ("nan", "inf", "infinity"):
        return encode_ieee754_special(FloatClass.NAN if special == "nan" else FloatClass.INFINITY,
                                      fmt, sign_bit=int(normalized.startswith("-")))
    exact = evaluate_expression(text)
    if exact.numerator == 0 and normalized.startswith("-"):
        return encode_ieee754_special(FloatClass.ZERO, fmt, sign_bit=1)
    return exact
