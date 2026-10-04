"""Tests for streaming CSV profiling and study filtering."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from evs_profile.config import KEY_VARIABLES, WEIGHT_VARIABLES
from evs_profile.reader import profile_csv


class ReaderTests(unittest.TestCase):
    def make_fixture(self, directory: Path) -> Path:
        path = directory / "fixture.csv"
        fieldnames = [
            "study",
            "uniqid",
            "cntry_AN",
            "year",
            "mode",
            *KEY_VARIABLES,
            *WEIGHT_VARIABLES,
        ]

        def row(study: str, uniqid: str, country: str) -> dict[str, str]:
            values = {column: "1" for column in fieldnames}
            values.update(
                {
                    "study": study,
                    "uniqid": uniqid,
                    "cntry_AN": country,
                    "year": "2018",
                    "mode": "1",
                    "X003": "30",
                    "gwght": "1.5",
                    "pwght": "2.0",
                    "wght_eq1000": "0.5",
                }
            )
            if study == "1":
                values["X047_WVS7"] = "-4"
            else:
                values["X047E_EVS5"] = "-4"
            return values

        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row("1", "evs-1", "CZ"))
            writer.writerow(row("2", "wvs-1", "US"))
        return path

    def test_evs_filter_keeps_only_evs_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = profile_csv(self.make_fixture(Path(temp_dir)), "1")
        self.assertEqual(profile.row_count, 1)
        self.assertEqual(profile.study_counts, {"1": 1})
        self.assertEqual(profile.country_counts, {"CZ": 1})
        self.assertEqual(profile.key_counts["A170"]["1"], 1)
        self.assertEqual(profile.key_counts["X047_WVS7"]["-4"], 1)

    def test_no_filter_keeps_both_studies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = profile_csv(self.make_fixture(Path(temp_dir)), None)
        self.assertEqual(profile.row_count, 2)
        self.assertEqual(profile.study_counts, {"1": 1, "2": 1})
        self.assertEqual(profile.duplicate_uniqids, 0)


if __name__ == "__main__":
    unittest.main()

