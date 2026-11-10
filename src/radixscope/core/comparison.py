import math
from dataclasses import dataclass

from radixscope.core.ieee754 import IEEE754Value, IEEEFormat, encode_ieee754
from radixscope.core.value import ExactValue


@dataclass(frozen=True, slots=True)
class FloatFormatComparison:
    source: ExactValue | None
    values: tuple[IEEE754Value, ...]


def compare_float_formats(
    value: ExactValue | int | float, *, negative_zero: bool = False,
) -> FloatFormatComparison:
    if isinstance(value, bool) or not isinstance(value, (ExactValue, int, float)):
        raise TypeError("comparison requires an exact value, integer or float")
    source: ExactValue | None
    if isinstance(value, ExactValue):
        source = value
    elif isinstance(value, int):
        source = ExactValue(value)
    elif math.isfinite(value):
        source = ExactValue(*value.as_integer_ratio())
    else:
        source = None
    return FloatFormatComparison(
        source, tuple(encode_ieee754(value, format_, negative_zero=negative_zero)
                      for format_ in IEEEFormat),
    )
