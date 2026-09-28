#!/usr/bin/env python3
"""Generate a synthetic QMS export (sample_data.csv) for demos and testing.

The data is fictional but shaped like a real deviation/CAPA export: a mix of
open and closed records, some past their due dates, across departments and
severities. Run from the project root:

    python tools/make_sample_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

DEV_TITLES = [
    "Temperature excursion in cold room CR-2",
    "Missing second-person verification on batch record BR-1042",
    "pH out of specification during buffer prep",
    "Particulate observed in WFI loop sample point",
    "Incorrect label applied to in-process bulk container",
    "Environmental monitoring action limit exceeded in Grade B",
    "Calibration overdue on analytical balance AB-07",
    "Growth promotion failure on media lot M-2281",
    "Documentation error: wrong form revision used for cleaning log",
    "Freezer FZ-3 alarm not acknowledged within 1 hour",
    "Bioburden result above alert limit for purified water",
    "Training record incomplete for new manufacturing operator",
]

CAPA_TITLES = [
    "Install continuous temperature monitoring with SMS alerts",
    "Revise line-clearance SOP and retrain all operators",
    "Implement automated pH trending with weekly review",
    "Replace WFI sample valves and re-qualify loop",
    "Add barcode verification to labeling step",
    "Increase EM sampling frequency during campaign runs",
    "Create calibration due-date dashboard for QC",
    "Qualify alternate media vendor and update specification",
    "Deploy electronic logbooks with revision control",
    "Tighten alarm response procedure and add shift handover check",
]

DEPARTMENTS = ["Manufacturing", "QC", "QA", "Engineering", "Validation", "Warehouse"]
SEVERITIES = ["Minor"] * 5 + ["Major"] * 3 + ["Critical"] * 2  # weighted

START = date(2026, 1, 5)
END = date(2026, 9, 20)
CLAMP = date(2026, 9, 27)  # nothing closes "in the future" vs the demo as-of date


def rand_date(a: date, b: date) -> date:
    return a + timedelta(days=random.randint(0, (b - a).days))


def main() -> None:
    rows = []
    for i in range(1, 61):
        is_capa = random.random() < 0.35
        opened = rand_date(START, END)
        due = opened + timedelta(days=30)
        status = "Closed" if random.random() < 0.65 else "Open"
        closed = ""
        if status == "Closed":
            closed_date = min(
                opened + timedelta(days=random.randint(4, 60)), CLAMP
            )
            closed = closed_date.isoformat()
        rows.append(
            {
                "id": f"{'CAPA' if is_capa else 'DEV'}-2026-{i:03d}",
                "record_type": "CAPA" if is_capa else "Deviation",
                "title": random.choice(CAPA_TITLES if is_capa else DEV_TITLES),
                "severity": random.choice(SEVERITIES),
                "department": random.choice(DEPARTMENTS),
                "date_opened": opened.isoformat(),
                "due_date": due.isoformat(),
                "date_closed": closed,
                "status": status,
            }
        )

    out = Path(__file__).resolve().parent.parent / "sample_data.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "record_type",
                "title",
                "severity",
                "department",
                "date_opened",
                "due_date",
                "date_closed",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
