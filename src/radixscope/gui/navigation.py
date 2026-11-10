from radixscope.reports import StructuredReport


def transfer_state(
    report: dict[str, object], target: str, state: dict[str, object], raw: bool,
) -> dict[str, object]:
    result = dict(state)
    bits = report.get("bits")
    if raw:
        if not isinstance(bits, str) or not bits or any(bit not in "01" for bit in bits):
            raise ValueError("This result has no raw bit pattern; send its numeric value")
        if len(bits) > 4096:
            raise ValueError("Desktop bit editing supports at most 4096 bits")
        result.update({"input": format(int(bits, 2), "X"), "base": 16})
        if target == "Number Inspector":
            data_type = f"binary{len(bits)}" if "classification" in report else "integer"
            result.update({"pattern": True, "bit_width": len(bits),
                           "signed": report.get("signed") is True, "data_type": data_type})
        elif target == "Programmer":
            result.update({"pattern": True, "bit_width": len(bits), "operation": "inspect",
                           "signed": report.get("signed") is True})
        elif target == "IEEE 754" and len(bits) in (32, 64):
            result.update({"mode": "decode", "bit_width": str(len(bits))})
        else:
            raise ValueError("Raw IEEE bits require 32 or 64 bits; Conversion accepts values")
        order = report.get("byteorder")
        if order in ("big", "little"):
            result["byteorder"] = order
        return result
    exact = StructuredReport(report).exact_value
    if exact is None:
        raise ValueError("This result has no finite numeric value; send its raw bits")
    result["input"] = str(exact)
    if target == "Conversion":
        result.update({"mode": "Number", "source_base": 10})
    elif target in ("Number Inspector", "Programmer"):
        if target == "Programmer" and not exact.is_integer:
            raise ValueError("Programmer requires an integer; use Number Inspector for fractions")
        width = max(8, abs(exact.numerator).bit_length() + int(exact.numerator < 0))
        if width > 4096:
            raise ValueError("Desktop integer inspection supports at most 4096 bits")
        result.update({"base": 10, "pattern": False, "bit_width": width,
                       "signed": exact.numerator < 0})
        if target == "Number Inspector":
            result["data_type"] = "integer" if exact.is_integer else "binary64"
        else:
            result["operation"] = "inspect"
    elif target == "IEEE 754":
        result.update({"mode": "encode", "negative_zero": False, "payload": "0", "quiet": True})
    else:
        raise ValueError("Unknown destination workspace")
    return result
