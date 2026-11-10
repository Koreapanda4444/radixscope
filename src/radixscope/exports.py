import csv
import io
import json
import os
import sys
import tempfile
from pathlib import Path

from radixscope.core.value import ExactValue


def json_safe(value: object) -> object:
    if isinstance(value, int) and not isinstance(value, bool):
        limit = sys.get_int_max_str_digits()
        if limit and abs(value).bit_length() > limit * 3 and abs(value) >= 10**limit:
            return str(ExactValue(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def report_json(report: dict[str, object]) -> str:
    return json.dumps(json_safe(report), ensure_ascii=False, indent=2, allow_nan=False)


def report_csv(report: dict[str, object]) -> str:
    if isinstance(report.get("rows"), list) and isinstance(report.get("bases"), list):
        return batch_report_csv(report)
    comparison = report.get("comparison")
    if isinstance(comparison, list):
        return table_csv([row for row in comparison if isinstance(row, dict)])
    from radixscope.reports import StructuredReport

    return table_csv(
        [{"field": field.path, "value": field.text} for field in StructuredReport(report).fields]
    )


def table_csv(rows: list[dict[str, object]]) -> str:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=keys, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: json.dumps(json_safe(value), ensure_ascii=False)
                if (isinstance(value, (dict, list, tuple)))
                else json_safe(value)
                for key, value in row.items()
            }
        )
    return output.getvalue()


def write_export(path: Path, text: str) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent, suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def batch_report_csv(report: dict[str, object]) -> str:
    rows, bases = report.get("rows"), report.get("bases")
    if not isinstance(rows, list) or not isinstance(bases, list):
        raise ValueError("report is not a batch result")
    keys = ["line", "input", "exact", *[f"base_{base}" for base in bases], "error"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=keys, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("outputs"), dict):
            raise ValueError("invalid batch row")
        values = {key: row.get(key, "") for key in ("line", "input", "exact", "error")}
        values.update({f"base_{base}": row["outputs"].get(str(base), "") for base in bases})
        writer.writerow(values)
    return output.getvalue()
