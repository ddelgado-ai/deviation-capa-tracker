#!/usr/bin/env python3
"""
Deviation & CAPA Metrics Tracker
================================
Turns a flat CSV export from your QMS (deviations + CAPAs) into the metrics QA
leadership actually asks for: closure times, aging buckets, and an overdue
list -- without opening a spreadsheet.

Usage:
    python capa_metrics.py sample_data.csv
    python capa_metrics.py qms_export.csv --as-of 2026-09-28 --output-dir reports
    python capa_metrics.py qms_export.csv --no-reports   # console summary only

Expected CSV columns (header row required):
    id, record_type, title, severity, department,
    date_opened, due_date, date_closed, status

Dates are YYYY-MM-DD. date_closed is blank for open records.
Standard library only -- no dependencies to install.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

REQUIRED_COLUMNS = [
    "id",
    "record_type",
    "title",
    "severity",
    "department",
    "date_opened",
    "due_date",
    "date_closed",
    "status",
]

AGING_BUCKETS = [
    (30, "0-30 days"),
    (60, "31-60 days"),
    (90, "61-90 days"),
    (float("inf"), "90+ days"),
]


def parse_date(value: str, *, column: str, row_no: int) -> date | None:
    """Parse a YYYY-MM-DD string; blank means 'no date'. Raises on bad input."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(
            f"Row {row_no}: column '{column}' has invalid date '{value}' "
            "(expected YYYY-MM-DD)"
        )


def load_records(path: Path) -> list[dict]:
    """Load and validate the QMS export CSV."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        rows = []
        for row_no, row in enumerate(reader, start=2):
            rows.append(
                {
                    "id": row["id"].strip(),
                    "record_type": row["record_type"].strip(),
                    "title": row["title"].strip(),
                    "severity": row["severity"].strip(),
                    "department": row["department"].strip(),
                    "date_opened": parse_date(
                        row["date_opened"], column="date_opened", row_no=row_no
                    ),
                    "due_date": parse_date(
                        row["due_date"], column="due_date", row_no=row_no
                    ),
                    "date_closed": parse_date(
                        row["date_closed"], column="date_closed", row_no=row_no
                    ),
                    "status": row["status"].strip().lower(),
                }
            )
    return rows


def aging_bucket(age_days: int) -> str:
    for limit, label in AGING_BUCKETS:
        if age_days <= limit:
            return label
    return AGING_BUCKETS[-1][1]  # pragma: no cover - unreachable


def _group_breakdown(records: list[dict], key: str) -> dict:
    """Open/closed counts and average closure time grouped by `key`."""
    groups: dict[str, dict] = defaultdict(
        lambda: {"open": 0, "closed": 0, "_closure_days": []}
    )
    for r in records:
        g = groups[r[key]]
        if r["status"] == "closed":
            g["closed"] += 1
            g["_closure_days"].append((r["date_closed"] - r["date_opened"]).days)
        else:
            g["open"] += 1
    for g in groups.values():
        days = g.pop("_closure_days")
        g["avg_closure_days"] = (
            round(statistics.fmean(days), 1) if days else None
        )
    return dict(groups)


def analyze(records: list[dict], as_of: date) -> dict:
    """Compute every metric from the loaded records as of `as_of`."""
    open_items, overdue = [], []
    closure_days, open_ages = [], []

    for r in records:
        opened = r["date_opened"]
        if opened is None:
            raise ValueError(f"Record {r['id']}: date_opened is required")
        if r["status"] == "closed":
            if r["date_closed"] is None:
                raise ValueError(
                    f"Record {r['id']}: status is Closed but date_closed is blank"
                )
            days = (r["date_closed"] - opened).days
            closure_days.append(days)
        else:
            age = (as_of - opened).days
            open_ages.append(age)
            item = {**r, "age_days": age, "bucket": aging_bucket(age)}
            open_items.append(item)
            if r["due_date"] is not None and r["due_date"] < as_of:
                overdue.append(
                    {**item, "days_overdue": (as_of - r["due_date"]).days}
                )

    overdue.sort(key=lambda x: x["days_overdue"], reverse=True)
    bucket_counts = Counter(item["bucket"] for item in open_items)

    return {
        "as_of": as_of.isoformat(),
        "total": len(records),
        "open": len(open_items),
        "closed": len(closure_days),
        "overdue": len(overdue),
        "avg_closure_days": round(statistics.fmean(closure_days), 1)
        if closure_days
        else None,
        "median_closure_days": round(statistics.median(closure_days), 1)
        if closure_days
        else None,
        "avg_open_age_days": round(statistics.fmean(open_ages), 1)
        if open_ages
        else None,
        "aging_buckets": {
            label: bucket_counts.get(label, 0) for _, label in AGING_BUCKETS
        },
        "by_type": _group_breakdown(records, "record_type"),
        "by_severity": _group_breakdown(records, "severity"),
        "overdue_items": overdue,
        "open_items": open_items,
    }


def _fmt(value, suffix: str = "") -> str:
    return f"{value}{suffix}" if value is not None else "n/a"


def print_summary(result: dict) -> None:
    print("=" * 62)
    print(f"Deviation / CAPA Metrics  (as of {result['as_of']})")
    print("=" * 62)
    print(f"Total records : {result['total']}")
    print(f"Open          : {result['open']}")
    print(f"Closed        : {result['closed']}")
    print(f"Overdue       : {result['overdue']}")
    print()
    print("Closure time (closed records)")
    print(f"  Average : {_fmt(result['avg_closure_days'], ' days')}")
    print(f"  Median  : {_fmt(result['median_closure_days'], ' days')}")
    print(f"  Avg age of open items: {_fmt(result['avg_open_age_days'], ' days')}")
    print()
    print("Aging of open items")
    for label, count in result["aging_buckets"].items():
        print(f"  {label:<12}: {count}")
    print()
    print("By record type")
    for rtype, g in result["by_type"].items():
        print(
            f"  {rtype:<10}: {g['open']} open / {g['closed']} closed,"
            f" avg closure {_fmt(g['avg_closure_days'], ' days')}"
        )
    print()
    print("By severity")
    for sev, g in result["by_severity"].items():
        print(
            f"  {sev:<10}: {g['open']} open / {g['closed']} closed,"
            f" avg closure {_fmt(g['avg_closure_days'], ' days')}"
        )
    if result["overdue_items"]:
        shown = min(5, len(result["overdue_items"]))
        print()
        print(f"Most overdue ({shown} of {len(result['overdue_items'])})")
        for item in result["overdue_items"][:5]:
            print(
                f"  {item['id']}: {item['title'][:44]:<44}"
                f" {item['days_overdue']} days overdue"
            )
    print("=" * 62)


def write_reports(result: dict, output_dir: Path) -> Path:
    """Write aging, overdue, and summary CSVs. Returns the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    open_items = sorted(
        result["open_items"], key=lambda r: r["age_days"], reverse=True
    )
    with (output_dir / "aging_report.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "id",
                "record_type",
                "title",
                "severity",
                "department",
                "date_opened",
                "due_date",
                "age_days",
                "aging_bucket",
            ]
        )
        for r in open_items:
            writer.writerow(
                [
                    r["id"],
                    r["record_type"],
                    r["title"],
                    r["severity"],
                    r["department"],
                    r["date_opened"],
                    r["due_date"],
                    r["age_days"],
                    r["bucket"],
                ]
            )

    with (output_dir / "overdue_report.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "id",
                "record_type",
                "title",
                "severity",
                "department",
                "date_opened",
                "due_date",
                "days_overdue",
            ]
        )
        for r in result["overdue_items"]:
            writer.writerow(
                [
                    r["id"],
                    r["record_type"],
                    r["title"],
                    r["severity"],
                    r["department"],
                    r["date_opened"],
                    r["due_date"],
                    r["days_overdue"],
                ]
            )

    with (output_dir / "summary.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "value"])
        for key in [
            "as_of",
            "total",
            "open",
            "closed",
            "overdue",
            "avg_closure_days",
            "median_closure_days",
            "avg_open_age_days",
        ]:
            writer.writerow([key, result[key]])
        for label, count in result["aging_buckets"].items():
            writer.writerow([f"aging_{label}", count])

    return output_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Deviation/CAPA metrics tracker: closure times, aging "
        "buckets, and overdue list from a QMS CSV export."
    )
    parser.add_argument("csv_file", help="Path to the QMS export CSV")
    parser.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="Reference date as YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for the CSV reports (default: ./reports)",
    )
    parser.add_argument(
        "--no-reports",
        action="store_true",
        help="Print the console summary only; don't write report files",
    )
    args = parser.parse_args(argv)

    try:
        as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date()
    except ValueError:
        parser.error("--as-of must be YYYY-MM-DD")

    records = load_records(Path(args.csv_file))
    result = analyze(records, as_of)
    print_summary(result)
    if not args.no_reports:
        out = write_reports(result, Path(args.output_dir))
        print(f"\nReports written to: {out}/")


if __name__ == "__main__":
    main()
