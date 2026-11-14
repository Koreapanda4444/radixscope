from enum import StrEnum

from radixscope.core.digits import digit_char, validate_base
from radixscope.core.errors import NonIntegerValueError
from radixscope.core.limits import MAX_EXPANSION_DIGITS, ComputationLimitError, check_expansion
from radixscope.core.value import ExactValue


class RoundingMode(StrEnum):
    TRUNCATE = "truncate"
    HALF_UP = "half-up"
    HALF_EVEN = "half-even"
    FLOOR = "floor"
    CEILING = "ceiling"


def compare_rounding(value: ExactValue, base: object, precision: object) -> dict[RoundingMode, str]:
    """Compare every rounding rule at one radix/precision using the original exact value.

    Precision counts fractional digits in the target radix. Dictionary order follows
    RoundingMode; results have exactly the same semantics as format_rounded().
    """
    checked_base = validate_base(base)
    checked_precision = _validated_precision(precision)
    return {
        mode: format_rounded(value, checked_base, checked_precision, mode)
        for mode in RoundingMode
    }


def format_integer(value: ExactValue, base: object) -> str:
    checked_base = validate_base(base)
    if not isinstance(value, ExactValue):
        raise TypeError("value must be an ExactValue")
    if not value.is_integer:
        raise NonIntegerValueError("integer formatting requires an integer value")
    number = abs(value.numerator)
    if number == 0:
        return "0"
    digits: list[str] = []
    while number:
        number, remainder = divmod(number, checked_base)
        digits.append(digit_char(remainder))
    prefix = "-" if value.numerator < 0 else ""
    return prefix + "".join(reversed(digits))


def _fractional_expansion(
    remainder: int,
    denominator: int,
    base: int,
    max_digits: int | None = None,
) -> tuple[list[str], list[str], bool]:
    digits: list[str] = []
    positions: dict[int, int] = {}
    while remainder:
        if remainder in positions:
            start = positions[remainder]
            return digits[:start], digits[start:], True
        if max_digits is not None and len(digits) >= max_digits:
            return digits, [], False
        check_expansion(len(digits), denominator)
        positions[remainder] = len(digits)
        remainder *= base
        digit, remainder = divmod(remainder, denominator)
        digits.append(digit_char(digit))
    return digits, [], True


def format_exact(value: ExactValue, base: object) -> str:
    checked_base = validate_base(base)
    if not isinstance(value, ExactValue):
        raise TypeError("value must be an ExactValue")
    if value.is_integer:
        return format_integer(value, checked_base)
    absolute_numerator = abs(value.numerator)
    integer_part, remainder = divmod(absolute_numerator, value.denominator)
    integer_text = format_integer(ExactValue(integer_part), checked_base)
    finite_digits, recurring_digits, _ = _fractional_expansion(
        remainder,
        value.denominator,
        checked_base,
    )
    fractional_text = "".join(finite_digits)
    if recurring_digits:
        fractional_text += f"({''.join(recurring_digits)})"
    prefix = "-" if value.numerator < 0 else ""
    return f"{prefix}{integer_text}.{fractional_text}"


def _validated_precision(precision: object) -> int:
    if isinstance(precision, bool) or not isinstance(precision, int):
        raise ValueError("precision must be an integer")
    if precision < 0:
        raise ValueError("precision cannot be negative")
    if precision > MAX_EXPANSION_DIGITS:
        raise ComputationLimitError(f"precision exceeds {MAX_EXPANSION_DIGITS} digits")
    return precision


def _rounded_scaled_integer(
    value: ExactValue,
    scale: int,
    mode: RoundingMode,
) -> int:
    absolute_scaled_numerator = abs(value.numerator) * scale
    quotient, remainder = divmod(absolute_scaled_numerator, value.denominator)
    increment = False
    if mode is RoundingMode.HALF_UP:
        increment = remainder * 2 >= value.denominator
    elif mode is RoundingMode.HALF_EVEN:
        doubled_remainder = remainder * 2
        increment = doubled_remainder > value.denominator or (
            doubled_remainder == value.denominator and quotient % 2 == 1
        )
    elif mode is RoundingMode.FLOOR:
        increment = value.numerator < 0 and remainder != 0
    elif mode is RoundingMode.CEILING:
        increment = value.numerator > 0 and remainder != 0
    rounded = quotient + int(increment)
    return -rounded if value.numerator < 0 else rounded


def format_rounded(
    value: ExactValue,
    base: object,
    precision: object,
    mode: RoundingMode = RoundingMode.HALF_EVEN,
) -> str:
    checked_base = validate_base(base)
    checked_precision = _validated_precision(precision)
    if not isinstance(value, ExactValue):
        raise TypeError("value must be an ExactValue")
    if not isinstance(mode, RoundingMode):
        raise TypeError("mode must be a RoundingMode")
    scale = checked_base**checked_precision
    scaled_integer = _rounded_scaled_integer(value, scale, mode)
    absolute_scaled_integer = abs(scaled_integer)
    integer_part, fractional_part = divmod(absolute_scaled_integer, scale)
    prefix = "-" if scaled_integer < 0 else ""
    integer_text = format_integer(ExactValue(integer_part), checked_base)
    if checked_precision == 0:
        return prefix + integer_text
    fractional_text = format_integer(ExactValue(fractional_part), checked_base).rjust(
        checked_precision,
        "0",
    )
    return f"{prefix}{integer_text}.{fractional_text}"


def format_value(
    value: ExactValue,
    base: object,
    precision: object | None = None,
    rounding: RoundingMode = RoundingMode.HALF_EVEN,
) -> str:
    if precision is None:
        return format_exact(value, base)
    return format_rounded(value, base, precision, rounding)


def format_preview(value: ExactValue, base: object, max_digits: int = 1000) -> tuple[str, bool]:
    """Bound the fractional display without constructing an unrelated integer trace."""
    checked_base = validate_base(base)
    if not isinstance(value, ExactValue):
        raise TypeError("value must be an ExactValue")
    if type(max_digits) is not int or not 1 <= max_digits <= MAX_EXPANSION_DIGITS:
        raise ValueError("display digit limit must be between 1 and 100000")
    if value.is_integer:
        return format_integer(value, checked_base), True
    integer, remainder = divmod(abs(value.numerator), value.denominator)
    digits, recurring, complete = _fractional_expansion(
        remainder, value.denominator, checked_base, max_digits
    )
    text = "".join(digits)
    text += "(" + "".join(recurring) + ")" if recurring else "" if complete else "…"
    prefix = "-" if value.numerator < 0 else ""
    return prefix + format_integer(ExactValue(integer), checked_base) + "." + text, complete
