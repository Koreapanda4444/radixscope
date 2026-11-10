from radixscope.core.ieee754 import FloatClass, IEEE754Value, decode_ieee754, encode_ieee754


def adjacent_float(value: IEEE754Value, direction: str) -> IEEE754Value | None:
    if not isinstance(value, IEEE754Value):
        raise TypeError("value must be an IEEE754Value")
    if direction not in ("up", "down"):
        raise ValueError("direction must be up or down")
    if value.classification is FloatClass.NAN:
        return None
    upward = direction == "up"
    if value.classification is FloatClass.INFINITY and upward != bool(value.sign_bit):
        return None
    sign = 1 << (value.format.bit_width - 1)
    if value.classification is FloatClass.ZERO:
        return decode_ieee754(1 if upward else sign | 1, value.format)
    increment = 1 if upward != bool(value.sign_bit) else -1
    return decode_ieee754(value.pattern + increment, value.format)


def float_boundaries(format_: object) -> dict[str, IEEE754Value]:
    format_value = encode_ieee754(0, format_).format
    fraction = format_value.fraction_width
    maximum_exponent = (1 << format_value.exponent_width) - 1
    patterns = {
        "positive_zero": 0,
        "minimum_subnormal": 1,
        "maximum_subnormal": (1 << fraction) - 1,
        "minimum_normal": 1 << fraction,
        "maximum_finite": (maximum_exponent << fraction) - 1,
        "positive_infinity": maximum_exponent << fraction,
    }
    return {name: decode_ieee754(pattern, format_value) for name, pattern in patterns.items()}
