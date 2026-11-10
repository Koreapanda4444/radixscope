import csv
import io


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
