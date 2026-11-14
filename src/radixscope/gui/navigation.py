from typing import Literal

from radixscope.reports import StructuredReport


def _integer_width(value: int) -> int:
    return max(8, (-value - 1).bit_length() + 1 if value < 0 else value.bit_length())


def transfer_state(
    report: dict[str, object],
    target: str,
    state: dict[str, object],
    raw: bool,
) -> dict[str, object]:
    result = dict(state)
    order: Literal["little", "big"] = "little" if report.get("byteorder") == "little" else "big"
    bits = report.get("bits")
    if raw:
        if not isinstance(bits, str) or not bits or any(bit not in "01" for bit in bits):
            raise ValueError("This result has no raw bit pattern; send its numeric value")
        if len(bits) > 4096 and target in ("Number Inspector", "Calculation"):
            raise ValueError("Desktop bit editing supports at most 4096 bits")
        result.update({"input": format(int(bits, 2), "X"), "base": 16})
        if target == "Number Inspector":
            data_type = (
                str(report.get("format", f"binary{len(bits)}"))
                if ("classification" in report)
                else "integer"
            )
            result.update(
                {
                    "pattern": True,
                    "bit_width": len(bits),
                    "signed": report.get("signed") is True,
                    "data_type": data_type,
                }
            )
        elif target == "Calculation":
            result.update(
                {
                    "pattern": True,
                    "bit_width": len(bits),
                    "operation": "inspect",
                    "calculation_mode": "Fixed-width integer",
                    "signed": report.get("signed") is True,
                }
            )
        elif target == "IEEE 754" and len(bits) in (16, 32, 64):
            format_name = "bfloat16" if report.get("format") == "bfloat16" else str(len(bits))
            result.update({"mode": "decode", "bit_width": format_name, "compare": False})
        elif target in ("Conversion", "Batch Conversion", "Trace"):
            result["source_base"] = 16
            if target != "Trace":
                result["mode"] = "Number"
        else:
            raise ValueError("Raw IEEE bits require 16, 32 or 64 bits; Conversion accepts values")
        result["byteorder"] = order
        return result
    exact = StructuredReport(report).exact_value
    if exact is None:
        raise ValueError("This result has no finite numeric value; send its raw bits")
    result["input"] = str(exact)
    if target in ("Conversion", "Batch Conversion", "Trace"):
        result["source_base"] = 10
        if target != "Trace":
            result["mode"] = "Number"
    elif target == "Calculation":
        result["calculation_mode"] = "Exact expression"
    elif target == "Number Inspector":
        if target == "Calculation" and not exact.is_integer:
            raise ValueError("Programmer requires an integer; use Number Inspector for fractions")
        width = _integer_width(exact.numerator)
        if width > 4096:
            raise ValueError("Desktop integer inspection supports at most 4096 bits")
        result.update(
            {"base": 10, "pattern": False, "bit_width": width, "signed": exact.numerator < 0}
        )
        if target == "Number Inspector":
            result["data_type"] = "integer" if exact.is_integer else "binary64"
        else:
            result["operation"] = "inspect"
            result["calculation_mode"] = "Fixed-width integer"
    elif target == "IEEE 754":
        result.update(
            {
                "mode": "encode",
                "negative_zero": False,
                "payload": "0",
                "quiet": True,
                "compare": False,
            }
        )
    else:
        raise ValueError("Unknown destination workspace")
    return result
