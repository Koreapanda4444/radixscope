from dataclasses import dataclass
from enum import StrEnum

from radixscope.core.errors import IntegerRangeError, InvalidNumberError
from radixscope.core.fixed_width import FixedWidthInteger, validate_width


class ByteOrder(StrEnum):
    BIG = "big"
    LITTLE = "little"


def _validate_byte_order(byteorder: object) -> ByteOrder:
    if not isinstance(byteorder, str):
        raise TypeError("byteorder must be 'big' or 'little'")
    try:
        return ByteOrder(byteorder)
    except ValueError as error:
        raise ValueError("byteorder must be 'big' or 'little'") from error


def _validate_bytes(data: bytes) -> None:
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")


@dataclass(frozen=True, slots=True)
class ByteRepresentation:
    data: bytes
    byteorder: ByteOrder

    def __post_init__(self) -> None:
        _validate_bytes(self.data)
        object.__setattr__(self, "byteorder", _validate_byte_order(self.byteorder))

    @property
    def hexadecimal(self) -> str:
        return self.data.hex(" ").upper()

    @property
    def ascii_preview(self) -> str:
        return "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in self.data)


def encode_bytes(value: FixedWidthInteger, byteorder: object = ByteOrder.BIG) -> bytes:
    if not isinstance(value, FixedWidthInteger):
        raise TypeError("value must be a FixedWidthInteger")
    order = _validate_byte_order(byteorder)
    length = (value.width + 7) // 8
    return value.bit_pattern.to_bytes(length, order.value)


def decode_bytes(
    data: bytes,
    byteorder: object = ByteOrder.BIG,
    *,
    width: object | None = None,
    signed: bool = False,
) -> FixedWidthInteger:
    _validate_bytes(data)
    order = _validate_byte_order(byteorder)
    if not data:
        raise InvalidNumberError("byte data cannot be empty")
    checked_width = len(data) * 8 if width is None else validate_width(width)
    if len(data) != (checked_width + 7) // 8:
        raise IntegerRangeError("byte count does not match the selected width")
    pattern = int.from_bytes(data, order.value)
    return FixedWidthInteger.from_bit_pattern(pattern, checked_width, signed)


def represent_bytes(
    value: FixedWidthInteger,
    byteorder: object = ByteOrder.BIG,
) -> ByteRepresentation:
    order = _validate_byte_order(byteorder)
    return ByteRepresentation(encode_bytes(value, order), order)

