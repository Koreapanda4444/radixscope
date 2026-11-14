"""Friendly table headings; canonical report paths remain available for search/export."""

from radixscope.reports import ReportField

GROUPS = ("Input values", "Calculation result", "Base representations", "Integer representation",
          "IEEE 754", "Precision analysis", "Rounded operands", "Operand-rounding path",
          "Single-rounding path", "Details")
LABELS = {
    "input": "Input value", "exact": "Exact value", "source_exact": "Exact input value",
    "exact_result": "Mathematical result", "value": "Value in selected width",
    "unsigned": "Unsigned interpretation", "twos_complement": "Signed interpretation",
    "bits": "Bit pattern", "hexadecimal": "Hexadecimal", "bytes": "Byte sequence",
    "overflowed": "Overflow", "paths_differ": "Calculation paths differ",
    "error_ulps": "Error in ULPs", "ulp": "ULP spacing",
    "left_source_exact": "Original left operand", "right_source_exact": "Original right operand",
    "exact_operation": "Exact operation result", "absolute_error": "Absolute error",
    "relative_error": "Relative error", "exactly_represented": "Exactly represented",
    "mathematical": "Mathematical result", "wrapped": "Wrapped result",
    "rounding_rule": "Rounding rule", "rounding_direction": "Rounding direction",
    "underflowed_to_zero": "Underflow to zero",
    "selected_width_error": "Selected-width error",
}


def field_group(path: str) -> str:
    root = path.split(".")[0]
    if root in ("input", "source_exact", "left_source_exact", "right_source_exact"):
        return "Input values"
    if root in ("exact", "exact_result", "value", "paths_differ", "operation_result",
                "numeric_comparison"):
        return "Calculation result"
    if root == "outputs":
        return "Base representations"
    if root in ("left_operand", "right_operand", "left_input_flags", "right_input_flags"):
        return "Rounded operands"
    if root == "rounded_operands":
        return "Operand-rounding path"
    if root == "exact_then_round":
        return "Single-rounding path"
    if root in ("absolute_error", "relative_error", "error_ulps", "ulp", "exactly_represented",
                "rounding_direction", "rounding_rule", "overflowed", "underflowed_to_zero"):
        return "Precision analysis"
    if root in ("unsigned", "twos_complement", "width_requirements", "minimum", "maximum",
                "left_representation", "right_representation", "xor_bits", "changed_bit_count"):
        return "Integer representation"
    if root in ("format", "classification", "sign", "exponent", "significand", "quiet_nan",
                "nan_payload", "exponent_bits", "fraction_bits", "bits", "hexadecimal", "bytes"):
        return "IEEE 754"  # Replaced for integer-only reports by field_heading.
    return "Details"


def field_heading(field: ReportField, report: dict[str, object]) -> tuple[str, str]:
    group = field_group(field.path)
    parts = field.path.split(".")
    root, leaf = parts[0], parts[-1]
    label = LABELS.get(leaf, leaf.replace("_", " "))
    if root == "outputs":
        label = "Base " + leaf
    if group == "IEEE 754" and "classification" not in report:
        group = "Integer representation"
    if root == "overflowed" and "classification" not in report:
        group = "Integer representation"
    if root == "exact" and "rounded_operands" in report:
        label = "Result with rounded operands"
    elif root == "source_exact" and "rounded_operands" in report:
        label = "Exact mathematical result"
    elif root == "exact" and "classification" in report:
        label = "Encoded floating-point value"
    elif root == "exact" and "outputs" in report:
        label = "Exact calculation result"
    if root in ("left_operand", "right_operand", "left_input_flags", "right_input_flags"):
        label = ("Left" if root.startswith("left") else "Right") + " · " + label
    if "flags" in parts or root.endswith("_flags"):
        label = "Exception flags · " + label
    elif "error_against_original_math" in parts:
        label = "Error against original math · " + label
    elif "operation_rounding_error" in parts:
        label = "Operation rounding error · " + label
    elif root == "width_requirements":
        label = (parts[-2] + "-bit · " + label) if "standard_widths" in parts else label
    elif root in ("neighbors", "boundaries", "numeric_comparison",
                  "left_representation", "right_representation", "trace", "field_bits"):
        label = " · ".join(LABELS.get(part, part.replace("_", " ")) for part in parts)
    return group, label


def field_order(field: ReportField, report: dict[str, object]) -> int:
    return GROUPS.index(field_heading(field, report)[0])


def is_detail(path: str) -> bool:
    return path.split(".")[0] in (
        "neighbors", "boundaries", "field_bits", "trace", "underflow_halfway", "overflow_halfway",
    ) or path.startswith("width_requirements.standard_widths.") or (
        path.startswith(("rounded_operands.", "exact_then_round.")) and path not in (
        "rounded_operands.result.exact", "rounded_operands.exact_operation",
        "exact_then_round.result.exact", "exact_then_round.exact_operation",
    ))
