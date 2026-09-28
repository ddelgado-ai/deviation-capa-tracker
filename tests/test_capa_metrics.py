import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import capa_metrics


def rec(id_, rtype, status, opened, closed=None, due=None, severity="Major"):
    return {
        "id": id_,
        "record_type": rtype,
        "title": "test record",
        "severity": severity,
        "department": "QA",
        "date_opened": opened,
        "due_date": due,
        "date_closed": closed,
        "status": status,
    }


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.as_of = date(2026, 9, 28)
        self.records = [
            # closed in 10 days
            rec("DEV-1", "Deviation", "closed",
                date(2026, 9, 1), date(2026, 9, 11), date(2026, 10, 1)),
            # open, age 58 days, 28 days overdue
            rec("DEV-2", "Deviation", "open",
                date(2026, 8, 1), None, date(2026, 8, 31)),
            # closed in 10 days
            rec("CAPA-1", "CAPA", "closed",
                date(2026, 9, 10), date(2026, 9, 20), date(2026, 10, 10)),
            # open, age 8 days, not overdue
            rec("CAPA-2", "CAPA", "open",
                date(2026, 9, 20), None, date(2026, 10, 20)),
        ]
        self.result = capa_metrics.analyze(self.records, self.as_of)

    def test_counts(self):
        self.assertEqual(self.result["total"], 4)
        self.assertEqual(self.result["open"], 2)
        self.assertEqual(self.result["closed"], 2)

    def test_closure_stats(self):
        self.assertEqual(self.result["avg_closure_days"], 10.0)
        self.assertEqual(self.result["median_closure_days"], 10.0)

    def test_overdue_detection(self):
        self.assertEqual(self.result["overdue"], 1)
        item = self.result["overdue_items"][0]
        self.assertEqual(item["id"], "DEV-2")
        self.assertEqual(item["days_overdue"], 28)

    def test_aging_buckets(self):
        buckets = self.result["aging_buckets"]
        self.assertEqual(buckets["0-30 days"], 1)    # CAPA-2, age 8
        self.assertEqual(buckets["31-60 days"], 1)   # DEV-2, age 58
        self.assertEqual(buckets["61-90 days"], 0)
        self.assertEqual(buckets["90+ days"], 0)

    def test_breakdowns(self):
        by_type = self.result["by_type"]
        self.assertEqual(by_type["Deviation"]["open"], 1)
        self.assertEqual(by_type["Deviation"]["closed"], 1)
        self.assertEqual(by_type["CAPA"]["avg_closure_days"], 10.0)


class TestBucketEdges(unittest.TestCase):
    def test_edges(self):
        self.assertEqual(capa_metrics.aging_bucket(0), "0-30 days")
        self.assertEqual(capa_metrics.aging_bucket(30), "0-30 days")
        self.assertEqual(capa_metrics.aging_bucket(31), "31-60 days")
        self.assertEqual(capa_metrics.aging_bucket(90), "61-90 days")
        self.assertEqual(capa_metrics.aging_bucket(91), "90+ days")


class TestParsing(unittest.TestCase):
    def test_bad_date_raises(self):
        with self.assertRaises(ValueError):
            capa_metrics.parse_date("09/28/2026", column="date_opened", row_no=2)

    def test_blank_date_is_none(self):
        self.assertIsNone(
            capa_metrics.parse_date("", column="date_closed", row_no=2)
        )

    def test_missing_column_raises(self):
        import tempfile

        with tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, newline=""
        ) as fh:
            fh.write("id,title\n1,hello\n")
            tmp = fh.name
        try:
            with self.assertRaises(ValueError):
                capa_metrics.load_records(Path(tmp))
        finally:
            Path(tmp).unlink()


if __name__ == "__main__":
    unittest.main()
