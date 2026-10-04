"""Tests for the reproducible EVS Parquet build."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import pyarrow.parquet as pq

from evs_profile.dataset import build_evs_parquet, sha256_file


class DatasetBuildTests(unittest.TestCase):
    def test_build_filters_evs_and_preserves_missing_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            source = directory / "joint.csv"
            output = directory / "evs.parquet"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=[
                        "study",
                        "uniqid",
                        "A170",
                        "X047E_EVS5",
                        "X047_WVS7",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "study": 1,
                        "uniqid": 1001,
                        "A170": 8,
                        "X047E_EVS5": -1,
                        "X047_WVS7": -4,
                    }
                )
                writer.writerow(
                    {
                        "study": 2,
                        "uniqid": 2001,
                        "A170": 7,
                        "X047E_EVS5": -4,
                        "X047_WVS7": 5,
                    }
                )

            result = build_evs_parquet(
                source,
                output,
                expected_source_rows=2,
                expected_source_columns=5,
                expected_rows=1,
                expected_columns=4,
            )
            table = pq.read_table(output)
            manifest = json.loads(output.with_suffix(".metadata.json").read_text())

            self.assertEqual(result.rows, 1)
            self.assertEqual(result.columns, 4)
            self.assertEqual(result.dropped_columns, ["X047_WVS7"])
            self.assertEqual(table.column_names, ["study", "uniqid", "A170", "X047E_EVS5"])
            self.assertEqual(table["X047E_EVS5"].to_pylist(), [-1])
            self.assertEqual(table.schema.metadata[b"filter"], b"study == 1")
            self.assertEqual(manifest["source_sha256"], sha256_file(source))


if __name__ == "__main__":
    unittest.main()
