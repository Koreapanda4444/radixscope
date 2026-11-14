from dataclasses import dataclass

from radixscope.core.errors import (
    IntegerRangeError,
    InvalidNumberError,
    InvalidWidthError,
    NonIntegerValueError,
)
from radixscope.core.limits import MAX_COMPUTED_BITS, ComputationLimitError
from radixscope.core.parse import parse_integer, parse_number
from radixscope.core.value import ExactValue


def validate_width(width: object) -> int:
    if isinstance(width, bool) or not isinstance(width, int):
        raise InvalidWidthError("width must be an integer")
    if width < 1:
        raise InvalidWidthError("width must be at least one bit")
    if width > MAX_COMPUTED_BITS:
        raise ComputationLimitError(f"width exceeds the {MAX_COMPUTED_BITS}-bit computation budget")
    return width


def integer_bounds(width: object, signed: bool = False) -> tuple[int, int]:
    checked_width = validate_width(width)
    if not isinstance(signed, bool):
        raise TypeError("signed must be a boolean")
    if signed:
        limit = 1 << (checked_width - 1)
        return -limit, limit - 1
    return 0, (1 << checked_width) - 1


def _validate_shift_count(count: object) -> int:
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("shift count must be an integer")
    if count < 0:
        raise ValueError("shift count cannot be negative")
    return count


@dataclass(frozen=True, slots=True)
class FixedWidthInteger:
    value: int
    width: int
    signed: bool = False

    def __post_init__(self) -> None:
        checked_width = validate_width(self.width)
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise TypeError("value must be an integer")
        if not isinstance(self.signed, bool):
            raise TypeError("signed must be a boolean")
        minimum, maximum = integer_bounds(checked_width, self.signed)
        if not minimum <= self.value <= maximum:
            kind = "signed" if self.signed else "unsigned"
            raise IntegerRangeError(
                f"{self.value} is outside the {checked_width}-bit {kind} range "
                f"{minimum} through {maximum}"
            )
        object.__setattr__(self, "width", checked_width)

    @classmethod
    def from_exact(
        cls,
        value: ExactValue,
        width: object,
        signed: bool = False,
    ) -> "FixedWidthInteger":
        if not isinstance(value, ExactValue):
            raise TypeError("value must be an ExactValue")
        if not value.is_integer:
            raise NonIntegerValueError("fixed-width integers require an integer value")
        return cls(value.numerator, validate_width(width), signed)

    @classmethod
    def from_text(
        cls,
        text: str,
        base: object,
        width: object,
        signed: bool = False,
    ) -> "FixedWidthInteger":
        return cls.from_exact(parse_number(text, base), width, signed)

    @property
    def exact(self) -> ExactValue:
        return ExactValue(self.value)

    def resize(self, width: object) -> "FixedWidthInteger":
        return type(self)(self.value, validate_width(width), self.signed)

    @property
    def minimum(self) -> int:
        return integer_bounds(self.width, self.signed)[0]

    @property
    def maximum(self) -> int:
        return integer_bounds(self.width, self.signed)[1]

    @property
    def modulus(self) -> int:
        return 1 << self.width

    @property
    def is_negative(self) -> bool:
        return self.value < 0

    @property
    def bit_pattern(self) -> int:
        return self.value % self.modulus

    @property
    def bits(self) -> str:
        return format(self.bit_pattern, f"0{self.width}b")

    @classmethod
    def from_bit_pattern(
        cls,
        pattern: object,
        width: object,
        signed: bool = False,
    ) -> "FixedWidthInteger":
        checked_width = validate_width(width)
        if isinstance(pattern, bool) or not isinstance(pattern, int):
            raise TypeError("bit pattern must be an integer")
        if not isinstance(signed, bool):
            raise TypeError("signed must be a boolean")
        maximum = (1 << checked_width) - 1
        if not 0 <= pattern <= maximum:
            raise IntegerRangeError(
                f"bit pattern must be between 0 and {maximum} for width {checked_width}"
            )
        sign_bit = 1 << (checked_width - 1)
        value = pattern - (1 << checked_width) if signed and pattern & sign_bit else pattern
        return cls(value, checked_width, signed)

    def extract_bits(
        self, offset: int, width: int, signed: bool = False,
    ) -> "FixedWidthInteger":
        """Extract a checked bit range, with bit zero at the least significant bit."""
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("bit offset must be a nonnegative integer")
        checked_width = validate_width(width)
        if offset + checked_width > self.width:
            raise IntegerRangeError("bit range exceeds the selected integer width")
        pattern = (self.bit_pattern >> offset) & ((1 << checked_width) - 1)
        return type(self).from_bit_pattern(pattern, checked_width, signed)

    def reinterpret(self, signed: bool) -> "FixedWidthInteger":
        return self.from_bit_pattern(self.bit_pattern, self.width, signed)

    @classmethod
    def from_bits(
        cls,
        bits: str,
        width: object | None = None,
        signed: bool = False,
    ) -> "FixedWidthInteger":
        if not isinstance(bits, str):
            raise TypeError("bits must be text")
        if not bits or any(bit not in "01" for bit in bits):
            raise InvalidNumberError("bits must contain only zero and one and cannot be empty")
        checked_width = len(bits) if width is None else validate_width(width)
        if len(bits) > checked_width:
            raise IntegerRangeError("bit text is longer than the selected width")
        return cls.from_bit_pattern(int(bits, 2), checked_width, signed)

    def _require_matching(self, other: "FixedWidthInteger") -> None:
        if not isinstance(other, FixedWidthInteger):
            raise TypeError("operand must be a FixedWidthInteger")
        if self.width != other.width or self.signed != other.signed:
            raise ValueError("operands must have the same width and signedness")

    def _pattern_result(self, pattern: int) -> "FixedWidthInteger":
        return type(self).from_bit_pattern(pattern & (self.modulus - 1), self.width, self.signed)

    def __and__(self, other: "FixedWidthInteger") -> "FixedWidthInteger":
        self._require_matching(other)
        return self._pattern_result(self.bit_pattern & other.bit_pattern)

    def __or__(self, other: "FixedWidthInteger") -> "FixedWidthInteger":
        self._require_matching(other)
        return self._pattern_result(self.bit_pattern | other.bit_pattern)

    def __xor__(self, other: "FixedWidthInteger") -> "FixedWidthInteger":
        self._require_matching(other)
        return self._pattern_result(self.bit_pattern ^ other.bit_pattern)

    def __invert__(self) -> "FixedWidthInteger":
        return self._pattern_result(~self.bit_pattern)

    def __lshift__(self, count: object) -> "FixedWidthInteger":
        checked_count = _validate_shift_count(count)
        return self._pattern_result(self.bit_pattern << min(checked_count, self.width))

    def __rshift__(self, count: object) -> "FixedWidthInteger":
        checked_count = _validate_shift_count(count)
        value = self.value >> min(checked_count, self.width)
        return type(self)(value, self.width, self.signed)

    def logical_right_shift(self, count: object) -> "FixedWidthInteger":
        checked_count = _validate_shift_count(count)
        return self._pattern_result(self.bit_pattern >> min(checked_count, self.width))


@dataclass(frozen=True, slots=True)
class IntegerInterpretation:
    pattern: int
    width: int

    def __post_init__(self) -> None:
        FixedWidthInteger.from_bit_pattern(self.pattern, self.width)

    @property
    def unsigned_value(self) -> int:
        return self.pattern

    @property
    def signed_value(self) -> int:
        return FixedWidthInteger.from_bit_pattern(self.pattern, self.width, signed=True).value

    @property
    def sign_bit(self) -> int:
        return self.pattern >> (self.width - 1)

    @property
    def binary(self) -> str:
        return format(self.pattern, f"0{self.width}b")

    @property
    def hexadecimal(self) -> str:
        return format(self.pattern, f"0{(self.width + 3) // 4}X")


def interpret_bit_pattern(pattern: object, width: object) -> IntegerInterpretation:
    value = FixedWidthInteger.from_bit_pattern(pattern, width)
    return IntegerInterpretation(value.bit_pattern, value.width)


def parse_bit_pattern(
    text: str,
    base: object,
    width: object,
    signed: bool = False,
) -> FixedWidthInteger:
    pattern = parse_integer(text, base)
    return FixedWidthInteger.from_bit_pattern(pattern.numerator, width, signed)


def encode_twos_complement(value: object, width: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("value must be an integer")
    return FixedWidthInteger(value, validate_width(width), signed=True).bit_pattern


def decode_twos_complement(pattern: object, width: object) -> int:
    return FixedWidthInteger.from_bit_pattern(pattern, width, signed=True).value


def format_twos_complement(value: object, width: object) -> str:
    checked_width = validate_width(width)
    return format(encode_twos_complement(value, checked_width), f"0{checked_width}b")


def parse_twos_complement(bits: str) -> FixedWidthInteger:
    return FixedWidthInteger.from_bits(bits, signed=True)


@dataclass(frozen=True, slots=True)
class IntegerWidthAnalysis:
    value: int
    minimum_signed_width: int
    minimum_unsigned_width: int | None
    selected_width: int
    selected_signed: bool
    minimum: int
    maximum: int
    fits_selected: bool

    def fits(self, width: int, signed: bool = False) -> bool:
        low, high = integer_bounds(width, signed)
        return low <= self.value <= high


def analyze_integer_width(
    value: int, width: int = 32, signed: bool = False,
) -> IntegerWidthAnalysis:
    """Analyze mathematical integers without wrapping or accepting an invalid pattern."""
    if type(value) is not int:
        raise TypeError("value must be an integer")
    minimum, maximum = integer_bounds(width, signed)
    signed_width = max(1, value.bit_length() + 1 if value >= 0 else (~value).bit_length() + 1)
    unsigned_width = max(1, value.bit_length()) if value >= 0 else None
    return IntegerWidthAnalysis(value, signed_width, unsigned_width, width, signed,
                                minimum, maximum, minimum <= value <= maximum)
