import math
import struct
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from radixscope.core.fixed_width import FixedWidthInteger
from radixscope.core.representations import ByteOrder, decode_bytes, encode_bytes
from radixscope.core.value import ExactValue


class IEEEFormat(IntEnum):
    BINARY16 = 16
    BFLOAT16 = 116
    BINARY32 = 32
    BINARY64 = 64

    @property
    def bit_width(self) -> int:
        return 16 if self is IEEEFormat.BFLOAT16 else self.value

    @property
    def label(self) -> str:
        return self.name.lower()

    @property
    def fraction_width(self) -> int:
        return {IEEEFormat.BINARY16: 10, IEEEFormat.BFLOAT16: 7,
                IEEEFormat.BINARY32: 23, IEEEFormat.BINARY64: 52}[self]

    @property
    def exponent_width(self) -> int:
        return {IEEEFormat.BINARY16: 5, IEEEFormat.BFLOAT16: 8,
                IEEEFormat.BINARY32: 8, IEEEFormat.BINARY64: 11}[self]

    @property
    def bias(self) -> int:
        return (1 << (self.exponent_width - 1)) - 1


class FloatClass(StrEnum):
    ZERO = "zero"
    SUBNORMAL = "subnormal"
    NORMAL = "normal"
    INFINITY = "infinity"
    NAN = "nan"


def _validate_format(width: object) -> IEEEFormat:
    if isinstance(width, str):
        labels = {format_.label: format_ for format_ in IEEEFormat}
        labels.update({str(format_.bit_width): format_ for format_ in IEEEFormat
                       if format_ is not IEEEFormat.BFLOAT16})
        if width.lower() in labels:
            return labels[width.lower()]
        raise ValueError("format must be binary16, bfloat16, binary32 or binary64")
    if isinstance(width, bool) or not isinstance(width, int):
        raise TypeError("IEEE format must be 16, 32, 64 or a format name")
    try:
        return IEEEFormat(width)
    except ValueError as error:
        raise ValueError("format must be binary16, bfloat16, binary32 or binary64") from error


@dataclass(frozen=True, slots=True)
class IEEE754Value:
    pattern: int
    format: IEEEFormat

    def __post_init__(self) -> None:
        checked_format = _validate_format(self.format)
        FixedWidthInteger.from_bit_pattern(self.pattern, checked_format.bit_width)
        object.__setattr__(self, "format", checked_format)

    @property
    def sign_bit(self) -> int:
        return self.pattern >> (self.format.bit_width - 1)

    @property
    def exponent_bits(self) -> int:
        mask = (1 << self.format.exponent_width) - 1
        return (self.pattern >> self.format.fraction_width) & mask

    @property
    def fraction_bits(self) -> int:
        return self.pattern & ((1 << self.format.fraction_width) - 1)

    @property
    def classification(self) -> FloatClass:
        if self.exponent_bits == (1 << self.format.exponent_width) - 1:
            return FloatClass.NAN if self.fraction_bits else FloatClass.INFINITY
        if self.exponent_bits == 0:
            return FloatClass.SUBNORMAL if self.fraction_bits else FloatClass.ZERO
        return FloatClass.NORMAL

    @property
    def exponent(self) -> int | None:
        if self.classification in (FloatClass.INFINITY, FloatClass.NAN):
            return None
        return (self.exponent_bits or 1) - self.format.bias

    @property
    def significand(self) -> ExactValue | None:
        if self.exponent is None:
            return None
        leading = 1 << self.format.fraction_width if self.exponent_bits else 0
        return ExactValue(leading + self.fraction_bits, 1 << self.format.fraction_width)

    @property
    def exact(self) -> ExactValue | None:
        exponent = self.exponent
        significand = self.significand
        if exponent is None or significand is None:
            return None
        if exponent >= 0:
            value = significand * ExactValue(1 << exponent)
        else:
            value = significand / ExactValue(1 << -exponent)
        return -value if self.sign_bit else value

    @property
    def is_quiet_nan(self) -> bool:
        quiet_bit = 1 << (self.format.fraction_width - 1)
        return self.classification is FloatClass.NAN and bool(self.fraction_bits & quiet_bit)

    @property
    def nan_payload(self) -> int | None:
        if self.classification is not FloatClass.NAN:
            return None
        return self.fraction_bits & ((1 << (self.format.fraction_width - 1)) - 1)

    @property
    def bits(self) -> str:
        return format(self.pattern, f"0{self.format.bit_width}b")

    @property
    def hexadecimal(self) -> str:
        return format(self.pattern, f"0{self.format.bit_width // 4}X")

    def to_bytes(self, byteorder: object = ByteOrder.BIG) -> bytes:
        return encode_bytes(FixedWidthInteger(self.pattern, self.format.bit_width), byteorder)

    def to_float(self) -> float:
        if self.format is IEEEFormat.BFLOAT16:
            result: float = struct.unpack(">f", (self.pattern << 16).to_bytes(4, "big"))[0]
            return result
        code = {IEEEFormat.BINARY16: ">e", IEEEFormat.BINARY32: ">f",
                IEEEFormat.BINARY64: ">d"}[self.format]
        result = struct.unpack(code, self.to_bytes())[0]
        return result


def decode_ieee754(pattern: object, width: object = IEEEFormat.BINARY64) -> IEEE754Value:
    checked_format = _validate_format(width)
    value = FixedWidthInteger.from_bit_pattern(pattern, checked_format.bit_width)
    return IEEE754Value(value.bit_pattern, checked_format)


def decode_ieee754_bytes(
    data: bytes,
    width: object = IEEEFormat.BINARY64,
    byteorder: object = ByteOrder.BIG,
) -> IEEE754Value:
    checked_format = _validate_format(width)
    value = decode_bytes(data, byteorder, width=checked_format.bit_width)
    return IEEE754Value(value.bit_pattern, checked_format)


def encode_ieee754_special(
    classification: object,
    width: object = IEEEFormat.BINARY64,
    *,
    sign_bit: object = 0,
    payload: object = 0,
    quiet: bool = True,
) -> IEEE754Value:
    checked_format = _validate_format(width)
    if not isinstance(classification, str):
        raise TypeError("classification must be zero, infinity or nan")
    kind = FloatClass(classification)
    if kind not in (FloatClass.ZERO, FloatClass.INFINITY, FloatClass.NAN):
        raise ValueError("classification must be zero, infinity or nan")
    if isinstance(sign_bit, bool) or not isinstance(sign_bit, int):
        raise TypeError("sign bit must be an integer")
    if sign_bit not in (0, 1):
        raise ValueError("sign bit must be zero or one")
    if isinstance(payload, bool) or not isinstance(payload, int):
        raise TypeError("payload must be an integer")
    quiet_bit = 1 << (checked_format.fraction_width - 1)
    if not 0 <= payload < quiet_bit:
        raise ValueError("payload does not fit below the quiet bit")
    if not isinstance(quiet, bool):
        raise TypeError("quiet must be a boolean")
    if kind is not FloatClass.NAN and payload:
        raise ValueError("only NaN has a payload")
    pattern = sign_bit << (checked_format.bit_width - 1)
    if kind is not FloatClass.ZERO:
        pattern |= ((1 << checked_format.exponent_width) - 1) << checked_format.fraction_width
    if kind is FloatClass.NAN:
        if not quiet and payload == 0:
            raise ValueError("signaling NaN requires a nonzero payload")
        pattern |= payload | (quiet_bit if quiet else 0)
    return IEEE754Value(pattern, checked_format)


def _round_scaled_ratio(numerator: int, denominator: int, exponent: int) -> int:
    if exponent >= 0:
        denominator <<= exponent
    else:
        numerator <<= -exponent
    quotient, remainder = divmod(numerator, denominator)
    twice_remainder = remainder * 2
    increment = twice_remainder > denominator or (
        twice_remainder == denominator and quotient % 2 == 1
    )
    return quotient + int(increment)


def _encode_finite(value: ExactValue, format_: IEEEFormat, sign_bit: int) -> IEEE754Value:
    numerator = abs(value.numerator)
    denominator = value.denominator
    sign_pattern = sign_bit << (format_.bit_width - 1)
    if numerator == 0:
        return IEEE754Value(sign_pattern, format_)
    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        below_power = numerator < denominator << exponent
    else:
        below_power = numerator << -exponent < denominator
    if below_power:
        exponent -= 1
    minimum_exponent = 1 - format_.bias
    if exponent > format_.bias:
        return encode_ieee754_special(FloatClass.INFINITY, format_, sign_bit=sign_bit)
    if exponent < minimum_exponent:
        fraction = _round_scaled_ratio(
            numerator, denominator, minimum_exponent - format_.fraction_width
        )
        return IEEE754Value(sign_pattern | fraction, format_)
    significand = _round_scaled_ratio(numerator, denominator, exponent - format_.fraction_width)
    if significand == 1 << (format_.fraction_width + 1):
        significand >>= 1
        exponent += 1
    if exponent > format_.bias:
        return encode_ieee754_special(FloatClass.INFINITY, format_, sign_bit=sign_bit)
    exponent_pattern = (exponent + format_.bias) << format_.fraction_width
    fraction = significand - (1 << format_.fraction_width)
    return IEEE754Value(sign_pattern | exponent_pattern | fraction, format_)


def encode_ieee754(
    value: ExactValue | int | float,
    width: object = IEEEFormat.BINARY64,
    *,
    negative_zero: bool = False,
) -> IEEE754Value:
    checked_format = _validate_format(width)
    if not isinstance(negative_zero, bool):
        raise TypeError("negative_zero must be a boolean")
    if isinstance(value, bool) or not isinstance(value, (ExactValue, int, float)):
        raise TypeError("value must be an ExactValue, integer or float")
    if isinstance(value, float):
        sign_bit = int(math.copysign(1, value) < 0)
        if not math.isfinite(value):
            if negative_zero:
                raise ValueError("negative_zero requires a zero value")
            kind = FloatClass.NAN if math.isnan(value) else FloatClass.INFINITY
            return encode_ieee754_special(kind, checked_format, sign_bit=sign_bit)
        exact = ExactValue(*value.as_integer_ratio())
    else:
        exact = value if isinstance(value, ExactValue) else ExactValue(value)
        sign_bit = int(exact.numerator < 0)
    if negative_zero:
        if exact.numerator:
            raise ValueError("negative_zero requires a zero value")
        sign_bit = 1
    return _encode_finite(exact, checked_format, sign_bit)


def convert_ieee754(value: IEEE754Value, width: object) -> IEEE754Value:
    """Convert the represented value; rounding a previously rounded input may round twice."""
    if not isinstance(value, IEEE754Value):
        raise TypeError("value must be an IEEE754Value")
    target = _validate_format(width)
    exact = value.exact
    if exact is not None:
        return encode_ieee754(
            exact, target, negative_zero=exact.numerator == 0 and bool(value.sign_bit)
        )
    return encode_ieee754_special(
        value.classification, target, sign_bit=value.sign_bit,
        payload=value.nan_payload or 0, quiet=value.is_quiet_nan,
    )
