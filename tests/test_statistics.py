"""Tests for pure profile calculations."""

from __future__ import annotations

import unittest
from collections import Counter

from evs_profile.statistics import (
    human_bytes,
    invalid_count,
    median_from_counts,
    percentage,
    valid_counter,
    variable_family_counts,
)


class StatisticsTests(unittest.TestCase):
    def test_percentage_handles_values_and_zero_denominator(self) -> None:
        self.assertEqual(percentage(1, 4), "25.00%")
        self.assertEqual(percentage(0, 0), "n/a")

    def test_human_bytes_uses_binary_units(self) -> None:
        self.assertEqual(human_bytes(1024), "1.0 KiB")
        self.assertEqual(human_bytes(1024**2), "1.0 MiB")

    def test_valid_counter_excludes_missing_and_invalid_values(self) -> None:
        counts = Counter({"1": 2, "10": 3, "-1": 4, "11": 5, "bad": 6})
        self.assertEqual(valid_counter("A170", counts), Counter({"10": 3, "1": 2}))

    def test_invalid_count_ignores_official_missing_codes(self) -> None:
        counts = Counter({"1": 2, "10": 3, "-1": 4, "11": 5, "bad": 6})
        self.assertEqual(invalid_count("A170", counts), 11)

    def test_median_from_counts_handles_even_and_odd_samples(self) -> None:
        self.assertEqual(median_from_counts(Counter({"1": 1, "3": 2})), 3)
        self.assertEqual(median_from_counts(Counter({"1": 1, "3": 1})), 2)

    def test_variable_family_counts_matches_documented_groups(self) -> None:
        counts = variable_family_counts(["study", "A170", "Y002", "X003", "x026_01"])
        self.assertEqual(counts["Administrative, ID, protocol and weights"], 1)
        self.assertEqual(counts["A - perceptions of life"], 1)
        self.assertEqual(counts["E/Y - politics and society"], 1)
        self.assertEqual(counts["X - respondent demographics"], 2)


if __name__ == "__main__":
    unittest.main()

