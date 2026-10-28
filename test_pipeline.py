import csv
import tempfile
import unittest
from pathlib import Path
from main import profile, compare_profiles, read_csv


class PipelineTests(unittest.TestCase):
    def test_null_rate_and_duplicate_detection(self):
        rows = [
            {"record_id": "1", "event_timestamp": "2026-10-28T08:00:00+00:00", "customer_id": "", "amount": "10"},
            {"record_id": "1", "event_timestamp": "2026-10-28T09:00:00+00:00", "customer_id": "C2", "amount": "20"},
        ]
        p = profile(rows, ["record_id", "event_timestamp", "customer_id", "amount"])
        self.assertEqual(p["duplicate_key_count"], 1)
        self.assertEqual(p["null_rates"]["customer_id"], 0.5)

    def test_volume_alert(self):
        base = {"columns": ["record_id"], "row_count": 100, "null_rates": {}, "numeric": {},
                "duplicate_key_count": 0, "invalid_timestamp_count": 0, "latest_timestamp": None}
        current = {"columns": ["record_id"], "row_count": 50, "null_rates": {}, "numeric": {},
                   "duplicate_key_count": 0, "invalid_timestamp_count": 0, "latest_timestamp": None}
        alerts = compare_profiles(base, current)
        self.assertTrue(any(a["check"] == "volume" for a in alerts))

    def test_schema_change_alert(self):
        base = {"columns": ["a"], "row_count": 1, "null_rates": {}, "numeric": {},
                "duplicate_key_count": 0, "invalid_timestamp_count": 0, "latest_timestamp": None}
        current = {"columns": ["b"], "row_count": 1, "null_rates": {}, "numeric": {},
                   "duplicate_key_count": 0, "invalid_timestamp_count": 0, "latest_timestamp": None}
        alerts = compare_profiles(base, current)
        self.assertTrue(any(a["check"] == "schema" for a in alerts))


if __name__ == "__main__":
    unittest.main()
