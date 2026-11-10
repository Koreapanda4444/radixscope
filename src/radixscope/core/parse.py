import re

from radixscope.core.digits import digit_value, validate_base, validate_digits
from radixscope.core.errors import InvalidNumberError
from radixscope.core.limits import MAX_COMPUTED_BITS, ComputationLimitError, check_input
from radixscope.core.value import ExactValue


def _normalized_text(text: str) -> str:
    if not isinstance(text, str):
        raise InvalidNumberError("number must be text")
    check_input(text)
    normalized = text.strip()
    if not normalized:
        raise InvalidNumberError("number cannot be empty")
    if any(character.isspace() for character in normalized):
        raise InvalidNumberError("internal whitespace is not allowed")
    return normalized


def _split_sign(text: str) -> tuple[int, str]:
    if text[0] == "+":
        return 1, text[1:]
    if text[0] == "-":
        return -1, text[1:]
    return 1, text


def _parse_unsigned_digits(digits: str, base: int) -> int:
    normalized_digits = validate_digits(digits, base)
    value = 0
    for digit in normalized_digits:
        value = value * base + digit_value(digit)
    return value


def parse_integer(text: str, base: object) -> ExactValue:
    checked_base = validate_base(base)
    sign, digits = _split_sign(_normalized_text(text))
    if not digits:
        raise InvalidNumberError("an integer requires at least one digit")
    return ExactValue(sign * _parse_unsigned_digits(digits, checked_base))


def parse_finite(text: str, base: object) -> ExactValue:
    checked_base = validate_base(base)
    sign, unsigned = _split_sign(_normalized_text(text))
    if unsigned.count(".") != 1:
        raise InvalidNumberError("a finite fraction requires one decimal point")
    integer_digits, fractional_digits = unsigned.split(".")
    if not integer_digits or not fractional_digits:
        raise InvalidNumberError("digits are required on both sides of the decimal point")
    integer_value = _parse_unsigned_digits(integer_digits, checked_base)
    fractional_value = _parse_unsigned_digits(fractional_digits, checked_base)
    denominator = checked_base ** len(fractional_digits)
    numerator = integer_value * denominator + fractional_value
    return ExactValue(sign * numerator, denominator)


def parse_ratio(text: str, base: object) -> ExactValue:
    checked_base = validate_base(base)
    normalized = _normalized_text(text)
    if normalized.count("/") != 1:
        raise InvalidNumberError("a ratio requires one fraction separator")
    numerator_text, denominator_text = normalized.split("/")
    if not numerator_text or not denominator_text:
        raise InvalidNumberError("a ratio requires a numerator and denominator")
    numerator = parse_integer(numerator_text, checked_base)
    denominator = parse_integer(denominator_text, checked_base)
    if denominator.numerator == 0:
        raise InvalidNumberError("denominator cannot be zero")
    return ExactValue(numerator.numerator, denominator.numerator)


def parse_recurring(text: str, base: object) -> ExactValue:
    checked_base = validate_base(base)
    sign, unsigned = _split_sign(_normalized_text(text))
    if unsigned.count(".") != 1:
        raise InvalidNumberError("a recurring fraction requires one decimal point")
    if unsigned.count("(") != 1 or unsigned.count(")") != 1 or not unsigned.endswith(")"):
        raise InvalidNumberError("a recurring fraction requires one final recurring group")
    integer_digits, fractional_section = unsigned.split(".")
    nonrecurring_digits, recurring_section = fractional_section.split("(")
    recurring_digits = recurring_section[:-1]
    if not integer_digits:
        raise InvalidNumberError("a recurring fraction requires an integer part")
    if not recurring_digits:
        raise InvalidNumberError("a recurring group cannot be empty")
    integer_value = _parse_unsigned_digits(integer_digits, checked_base)
    nonrecurring_value = (
        _parse_unsigned_digits(nonrecurring_digits, checked_base)
        if nonrecurring_digits
        else 0
    )
    recurring_value = _parse_unsigned_digits(recurring_digits, checked_base)
    prefix_scale = checked_base ** len(nonrecurring_digits)
    recurring_scale = checked_base ** len(recurring_digits) - 1
    denominator = prefix_scale * recurring_scale
    numerator = (
        integer_value * denominator
        + nonrecurring_value * recurring_scale
        + recurring_value
    )
    return ExactValue(sign * numerator, denominator)


def parse_number(text: str, base: object) -> ExactValue:
    normalized = _normalized_text(text)
    checked_base = validate_base(base)
    if "/" in normalized:
        return parse_ratio(normalized, checked_base)
    if checked_base == 10 and ("e" in normalized or "E" in normalized):
        return parse_scientific(normalized)
    if "(" in normalized or ")" in normalized:
        return parse_recurring(normalized, base)
    if "." in normalized:
        return parse_finite(normalized, base)
    return parse_integer(normalized, base)


def parse_scientific(text: str) -> ExactValue:
    normalized = _normalized_text(text)
    match = re.fullmatch(r"(.+?)[eE]([+-]?[0-9]+)", normalized)
    if match is None or "/" in match.group(1):
        raise InvalidNumberError("scientific notation requires a mantissa and integer exponent")
    mantissa, exponent_text = match.groups()
    if "e" in mantissa.lower():
        raise InvalidNumberError("scientific notation requires exactly one exponent")
    source = parse_number(mantissa, 10)
    if source.numerator == 0:
        return source
    digits = exponent_text.lstrip("+-").lstrip("0") or "0"
    if len(digits) > 7:
        raise ComputationLimitError("scientific exponent exceeds the computation budget")
    exponent = int(digits) * (-1 if exponent_text.startswith("-") else 1)
    size = max(abs(source.numerator).bit_length(), source.denominator.bit_length())
    if abs(exponent) * 4 + size > MAX_COMPUTED_BITS:
        raise ComputationLimitError("scientific exponent exceeds the computation budget")
    scale = ExactValue(10 ** abs(exponent))
    return source * scale if exponent >= 0 else source / scale
