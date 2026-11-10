from dataclasses import dataclass

from radixscope.core.ieee754 import FloatClass, IEEE754Value
from radixscope.core.value import ExactValue


def power_of_two(exponent: int) -> ExactValue:
    return ExactValue(1 << exponent) if exponent >= 0 else ExactValue(1, 1 << -exponent)


@dataclass(frozen=True, slots=True)
class FloatPrecisionAnalysis:
    source: ExactValue
    encoded: IEEE754Value

    @property
    def error(self) -> ExactValue | None:
        actual = self.encoded.exact
        return actual - self.source if actual is not None else None

    @property
    def absolute_error(self) -> ExactValue | None:
        error = self.error
        return abs(error) if error is not None else None

    @property
    def relative_error(self) -> ExactValue | None:
        error = self.absolute_error
        return error / abs(self.source) if error is not None and self.source.numerator else None

    @property
    def ulp(self) -> ExactValue | None:
        exponent = self.encoded.exponent
        return power_of_two(exponent - self.encoded.format.fraction_width) if (
            exponent is not None
        ) else None

    @property
    def error_ulps(self) -> ExactValue | None:
        error, ulp = self.absolute_error, self.ulp
        return error / ulp if error is not None and ulp is not None else None

    @property
    def exactly_represented(self) -> bool:
        return self.error == ExactValue(0)

    @property
    def rounding_direction(self) -> str:
        error = self.error
        if error is None:
            return "overflow" if self.encoded.classification is FloatClass.INFINITY else "undefined"
        return "exact" if error.numerator == 0 else (
            "toward positive" if error.numerator > 0 else "toward negative"
        )


def analyze_float_precision(source: ExactValue, encoded: IEEE754Value) -> FloatPrecisionAnalysis:
    if not isinstance(source, ExactValue) or not isinstance(encoded, IEEE754Value):
        raise TypeError("precision analysis requires an exact source and an IEEE754Value")
    return FloatPrecisionAnalysis(source, encoded)
