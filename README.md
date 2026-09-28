# Deviation & CAPA Metrics Tracker

A small Python CLI that turns a flat CSV export from your QMS into the quality
metrics QA leadership actually asks for: **closure times, aging buckets, and an
overdue list** — without opening a spreadsheet.

## Why I built this

After 10+ years in QA (biotech/cell therapy), I've run the same monthly ritual
at every site: export deviations and CAPAs to Excel, build pivot tables, chase
due dates, and hand-assemble the metrics deck. It's slow, error-prone, and it
steals time from actual quality work. This tool automates the whole thing in
one command.

## Features

- **Closure time stats** — average and median days-to-close, overall and broken
  down by record type (Deviation/CAPA) and severity
- **Aging buckets** — open items grouped into 0–30 / 31–60 / 61–90 / 90+ days
- **Overdue list** — open items past their due date, ranked by days overdue
- **CSV reports** — `aging_report.csv`, `overdue_report.csv`, and `summary.csv`,
  ready to attach to a quality review or paste into a deck
- **Input validation** — missing columns, bad dates, and inconsistent
  open/closed states fail loudly with the exact row number
- **Zero dependencies** — standard library only, runs anywhere Python 3.9+ lives

## Quick start

```bash
# run against the included synthetic sample data
python capa_metrics.py sample_data.csv --as-of 2026-09-28

# run against your own QMS export
python capa_metrics.py qms_export.csv

# console summary only, no report files
python capa_metrics.py qms_export.csv --no-reports
```

## Input format

Your CSV needs a header row with these columns (dates as `YYYY-MM-DD`;
`date_closed` is blank for open records):

| column        | example                          |
|---------------|----------------------------------|
| id            | DEV-2026-001                     |
| record_type   | Deviation / CAPA                 |
| title         | Temperature excursion in CR-2    |
| severity      | Critical / Major / Minor         |
| department    | Manufacturing                    |
| date_opened   | 2026-02-14                       |
| due_date      | 2026-03-16                       |
| date_closed   | 2026-03-02 (blank if open)       |
| status        | Open / Closed                    |

## Example output

```
==============================================================
Deviation / CAPA Metrics  (as of 2026-09-28)
==============================================================
Total records : 60
Open          : 24
Closed        : 36
Overdue       : 22

Closure time (closed records)
  Average : 33.1 days
  Median  : 34.0 days
  Avg age of open items: 148.3 days

Aging of open items
  0-30 days   : 2
  31-60 days  : 3
  61-90 days  : 1
  90+ days    : 18

By record type
  Deviation : 17 open / 19 closed, avg closure 34.6 days
  CAPA      : 7 open / 17 closed, avg closure 31.4 days

By severity
  Minor     : 20 open / 22 closed, avg closure 35.6 days
  Major     : 0 open / 8 closed, avg closure 22.8 days
  Critical  : 4 open / 6 closed, avg closure 37.7 days

Most overdue (5 of 22)
  DEV-2026-019: Missing second-person verification on batch  231 days overdue
  DEV-2026-037: Particulate observed in WFI loop sample poin 229 days overdue
  DEV-2026-001: Particulate observed in WFI loop sample poin 224 days overdue
  CAPA-2026-057: Replace WFI sample valves and re-qualify loo 216 days overdue
  DEV-2026-041: Temperature excursion in cold room CR-2      205 days overdue
==============================================================
```

Pre-generated reports from the sample data live in [`examples/`](examples/).

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project layout

```
deviation-capa-tracker/
├── capa_metrics.py        # the CLI — parse, analyze, report
├── sample_data.csv        # synthetic QMS export (60 records)
├── tools/
│   └── make_sample_data.py  # regenerates the sample data
├── tests/
│   └── test_capa_metrics.py # 9 unit tests
└── examples/              # sample output reports
```

## Roadmap

- Config file for custom aging buckets and due-date rules
- Trend view: closure time month-over-month
- Optional chart output (matplotlib) and a lightweight dashboard

## License

MIT
