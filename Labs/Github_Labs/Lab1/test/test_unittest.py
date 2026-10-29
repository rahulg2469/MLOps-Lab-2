"""Unittest tests for src/calculator.py.

CHANGE: reads the same data/test_cases.csv using subTest, and adds
error-handling tests for invalid inputs and division by zero.
"""
import csv
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from src import calculator  # noqa: E402

DATA_FILE = os.path.join(PROJECT_ROOT, "data", "test_cases.csv")


def _to_number(text):
    return float(text) if "." in text else int(text)


class TestCalculator(unittest.TestCase):

    def test_cases_from_csv(self):
        with open(DATA_FILE, newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertGreater(len(rows), 0)
        for row in rows:
            args = [_to_number(row[k]) for k in ("x", "y", "z") if row[k] != ""]
            expected = _to_number(row["expected"])
            with self.subTest(function=row["function"], args=args):
                func = getattr(calculator, row["function"])
                self.assertAlmostEqual(func(*args), expected, places=5)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculator.fun1("a", 1)
        with self.assertRaises(ValueError):
            calculator.fun4(1, 2, "3")
        with self.assertRaises(ValueError):
            calculator.fun5(None, 2)

    def test_divide_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            calculator.fun5(5, 0)


if __name__ == "__main__":
    unittest.main()
