"""Pytest tests for src/calculator.py.

CHANGE: test cases are read from data/test_cases.csv and run with
@pytest.mark.parametrize, so adding a test = adding a CSV row.
"""
import csv
from pathlib import Path

import pytest

from src import calculator

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "test_cases.csv"


def _to_number(text):
    return float(text) if "." in text else int(text)


def load_cases():
    """Return a list of (function_name, args, expected) from the CSV."""
    cases = []
    with open(DATA_FILE, newline="") as f:
        for row in csv.DictReader(f):
            args = [_to_number(row[k]) for k in ("x", "y", "z") if row[k] != ""]
            cases.append((row["function"], args, _to_number(row["expected"])))
    return cases


CASES = load_cases()


def test_csv_covers_every_function():
    names = {name for name, _, _ in CASES}
    assert names == {"fun1", "fun2", "fun3", "fun4", "fun5"}


@pytest.mark.parametrize(
    "func_name, args, expected",
    CASES,
    ids=[f"{n}{tuple(a)}" for n, a, _ in CASES],
)
def test_calculator_from_csv(func_name, args, expected):
    func = getattr(calculator, func_name)
    assert func(*args) == pytest.approx(expected, rel=1e-5)


@pytest.mark.parametrize(
    "func, args",
    [
        (calculator.fun1, ("a", 1)),
        (calculator.fun2, (1, None)),
        (calculator.fun3, ([1], 2)),
        (calculator.fun4, (1, 2, "3")),
        (calculator.fun5, ("10", 2)),
    ],
)
def test_invalid_inputs_raise_value_error(func, args):
    with pytest.raises(ValueError):
        func(*args)


def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        calculator.fun5(5, 0)
