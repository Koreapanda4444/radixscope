from __future__ import annotations

import sys
from dataclasses import dataclass
from fractions import Fraction


def _decimal_integer(number: int) -> str:
    """Render exact integers without changing Python's process-wide security settings."""
    limit = sys.get_int_max_str_digits()
    if not limit or abs(number).bit_length() <= limit * 3:
        return str(number)
    magnitude = abs(number)
    chunks: list[int] = []
    while magnitude:
        magnitude, chunk = divmod(magnitude, 1_000_000_000)
        chunks.append(chunk)
    return ("-" if number < 0 else "") + str(chunks[-1]) + "".join(
        f"{chunk:09d}" for chunk in reversed(chunks[:-1])
    )


@dataclass(frozen=True, slots=True)
class ExactValue:
    numerator: int
    denominator: int = 1

    def __post_init__(self) -> None:
        value = Fraction(self.numerator, self.denominator)
        object.__setattr__(self, "numerator", value.numerator)
        object.__setattr__(self, "denominator", value.denominator)

    @classmethod
    def from_fraction(cls, value: Fraction) -> ExactValue:
        return cls(value.numerator, value.denominator)

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    @property
    def is_integer(self) -> bool:
        return self.denominator == 1

    @property
    def sign(self) -> int:
        return (self.numerator > 0) - (self.numerator < 0)

    def reciprocal(self) -> ExactValue:
        if self.numerator == 0:
            raise ZeroDivisionError("zero has no reciprocal")
        return ExactValue(self.denominator, self.numerator)

    def __add__(self, other: ExactValue) -> ExactValue:
        return ExactValue.from_fraction(self.fraction + other.fraction)

    def __sub__(self, other: ExactValue) -> ExactValue:
        return ExactValue.from_fraction(self.fraction - other.fraction)

    def __mul__(self, other: ExactValue) -> ExactValue:
        return ExactValue.from_fraction(self.fraction * other.fraction)

    def __truediv__(self, other: ExactValue) -> ExactValue:
        return ExactValue.from_fraction(self.fraction / other.fraction)

    def __pow__(self, exponent: int) -> ExactValue:
        return ExactValue.from_fraction(self.fraction**exponent)

    def __neg__(self) -> ExactValue:
        return ExactValue(-self.numerator, self.denominator)

    def __abs__(self) -> ExactValue:
        return ExactValue(abs(self.numerator), self.denominator)

    def __str__(self) -> str:
        if self.is_integer:
            return _decimal_integer(self.numerator)
        return f"{_decimal_integer(self.numerator)}/{_decimal_integer(self.denominator)}"
