from dataclasses import dataclass

from radixscope.core.fixed_width import FixedWidthInteger
from radixscope.core.formatting import format_exact
from radixscope.core.ieee754 import (
    IEEE754Value,
    decode_ieee754,
    encode_ieee754,
    encode_ieee754_special,
)
from radixscope.core.parse import parse_integer, parse_number
from radixscope.core.representations import ByteOrder, encode_bytes
from radixscope.core.value import ExactValue


@dataclass(frozen=True, slots=True)
class NumberInspection:
    value: FixedWidthInteger | IEEE754Value
    source_exact: ExactValue | None = None
    byteorder: ByteOrder = ByteOrder.BIG

    def __post_init__(self) -> None:
        if not isinstance(self.value, (FixedWidthInteger, IEEE754Value)):
            raise TypeError("inspection requires a fixed-width integer or floating-point value")
        object.__setattr__(self, "byteorder", ByteOrder(self.byteorder))

    @property
    def width(self) -> int:
        return self.value.width if isinstance(self.value, FixedWidthInteger) else (
            self.value.format.value
        )

    @property
    def pattern(self) -> int:
        return self.value.bit_pattern if isinstance(self.value, FixedWidthInteger) else (
            self.value.pattern
        )

    @property
    def exact(self) -> ExactValue | None:
        return self.value.exact

    @property
    def data(self) -> bytes:
        return encode_bytes(FixedWidthInteger(self.pattern, self.width), self.byteorder)

    @property
    def outputs(self) -> dict[int, str]:
        exact = self.exact
        return {base: format_exact(exact, base) for base in (2, 8, 10, 16)} if (
            exact is not None
        ) else {}


def inspect_number(
    text: str,
    *,
    base: int = 10,
    width: int = 32,
    signed: bool = False,
    data_type: str = "integer",
    raw: bool = False,
    byteorder: str = "big",
) -> NumberInspection:
    order = ByteOrder(byteorder)
    if not isinstance(raw, bool) or not isinstance(signed, bool):
        raise TypeError("raw and signed must be booleans")
    if data_type not in ("integer", "binary32", "binary64"):
        raise ValueError("data type must be integer, binary32 or binary64")
    if data_type == "integer":
        exact = parse_integer(text, base)
        integer = FixedWidthInteger.from_bit_pattern(exact.numerator, width, signed) if raw else (
            FixedWidthInteger.from_exact(exact, width, signed)
        )
        return NumberInspection(integer, None if raw else exact, order)
    float_width = int(data_type.removeprefix("binary"))
    if raw:
        floating = decode_ieee754(parse_integer(text, base).numerator, float_width)
        return NumberInspection(floating, byteorder=order)
    normalized = text.strip().lower()
    special = normalized.lstrip("+-")
    if special in ("nan", "inf", "infinity"):
        floating = encode_ieee754_special(
            "nan" if special == "nan" else "infinity", float_width,
            sign_bit=int(normalized.startswith("-")),
        )
        return NumberInspection(floating, byteorder=order)
    source = parse_number(text, base)
    floating = encode_ieee754(
        source, float_width, negative_zero=source.numerator == 0 and normalized.startswith("-")
    )
    return NumberInspection(floating, source, order)
