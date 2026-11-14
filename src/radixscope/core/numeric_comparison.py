"""Compare mathematical numbers and their explicitly selected numeric representations."""

from dataclasses import dataclass

from radixscope.core.expression import evaluate_expression
from radixscope.core.fixed_width import FixedWidthInteger, validate_width
from radixscope.core.ieee754 import FloatClass, IEEE754Value, IEEEFormat, encode_ieee754
from radixscope.core.inspection import inspect_number
from radixscope.core.parse import parse_number
from radixscope.core.value import ExactValue

NumericOperand = ExactValue | FixedWidthInteger | IEEE754Value


@dataclass(frozen=True, slots=True)
class NumericComparison:
    left: NumericOperand
    right: NumericOperand
    relation: str
    difference: ExactValue | None
    left_pattern: FixedWidthInteger | IEEE754Value | None
    right_pattern: FixedWidthInteger | IEEE754Value | None
    pattern_error: str
    width: int

    @property
    def xor(self) -> int | None:
        if self.left_pattern is None or self.right_pattern is None:
            return None
        return _pattern(self.left_pattern) ^ _pattern(self.right_pattern)

    @property
    def changed_positions(self) -> tuple[int, ...]:
        remaining = self.xor or 0
        positions: list[int] = []
        while remaining and len(positions) < 4096:
            lowest = remaining & -remaining
            positions.append(lowest.bit_length() - 1)
            remaining ^= lowest
        return tuple(positions)


def _pattern(value: FixedWidthInteger | IEEE754Value) -> int:
    return value.bit_pattern if isinstance(value, FixedWidthInteger) else value.pattern


def operand_exact(value: NumericOperand) -> ExactValue | None:
    return value if isinstance(value, ExactValue) else value.exact


def _order_key(value: NumericOperand) -> int | None:
    if isinstance(value, IEEE754Value):
        if value.classification is FloatClass.NAN:
            return None
        if value.classification is FloatClass.INFINITY:
            return -1 if value.sign_bit else 1
    return 0


def compare_numeric_values(
    left: NumericOperand, right: NumericOperand, *, width: int = 32,
    signed: bool = False, data_type: str = "integer",
) -> NumericComparison:
    validate_width(width)
    if not isinstance(signed, bool):
        raise TypeError("signed must be boolean")
    fmt = None if data_type == "integer" else IEEEFormat[data_type.upper()]
    selected_width = width if fmt is None else fmt.bit_width
    for value in (left, right):
        if not isinstance(value, (ExactValue, FixedWidthInteger, IEEE754Value)):
            raise TypeError("comparison operands must be numeric values")
    left_exact, right_exact = operand_exact(left), operand_exact(right)
    left_key, right_key = _order_key(left), _order_key(right)
    difference = None
    if left_key is None or right_key is None:
        relation = "unordered"
    elif left_key != right_key:
        relation = "less" if left_key < right_key else "greater"
    elif left_key:
        relation = "equal"
    else:
        assert left_exact is not None and right_exact is not None
        difference = left_exact - right_exact
        relation = "equal" if difference.numerator == 0 else (
            "less" if difference.numerator < 0 else "greater"
        )

    def representation(value: NumericOperand) -> FixedWidthInteger | IEEE754Value:
        if isinstance(value, ExactValue):
            return FixedWidthInteger.from_exact(value, width, signed) if fmt is None else (
                encode_ieee754(value, fmt)
            )
        actual_width = value.width if isinstance(value, FixedWidthInteger) else (
            value.format.bit_width
        )
        if actual_width != selected_width:
            raise ValueError("numeric patterns must have the same selected width")
        return value

    left_pattern = right_pattern = None
    error = ""
    try:
        left_pattern = representation(left)
        right_pattern = representation(right)
    except (ValueError, TypeError) as failure:
        error = str(failure)
    return NumericComparison(left, right, relation, difference, left_pattern, right_pattern,
                             error, selected_width)


def compare_numeric_inputs(
    left: str, right: str, *, base: int = 10, width: int = 32, signed: bool = False,
    data_type: str = "integer", raw: bool = False, expressions: bool = False,
) -> NumericComparison:
    def parse(text: str) -> NumericOperand:
        special = text.strip().lower().lstrip("+-") in ("nan", "inf", "infinity")
        if raw or special:
            if special and data_type == "integer":
                raise ValueError("special values require a floating-point data type")
            return inspect_number(text, base=base, width=width, signed=signed,
                                  data_type=data_type, raw=raw).value
        exact = evaluate_expression(text) if expressions else parse_number(text, base)
        if exact.numerator == 0 and text.strip().startswith("-") and data_type != "integer":
            return encode_ieee754(exact, data_type, negative_zero=True)
        return exact
    return compare_numeric_values(parse(left), parse(right), width=width,
                                  signed=signed, data_type=data_type)
