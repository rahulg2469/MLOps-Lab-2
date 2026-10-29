"""Simple calculator functions used to demonstrate testing and CI."""


def _check_numbers(*args):
    """Raise ValueError if any argument is not an int or float."""
    for value in args:
        if not isinstance(value, (int, float)):
            raise ValueError("All inputs must be numbers.")


def fun1(x, y):
    """Return x + y. Raises ValueError for non-numeric input."""
    _check_numbers(x, y)
    return x + y


def fun2(x, y):
    """Return x - y. Raises ValueError for non-numeric input."""
    _check_numbers(x, y)
    return x - y


def fun3(x, y):
    """Return x * y. Raises ValueError for non-numeric input."""
    _check_numbers(x, y)
    return x * y


def fun4(x, y, z):
    """Return x + y + z. Raises ValueError for non-numeric input.

    CHANGE: now validates inputs like the other functions.
    """
    _check_numbers(x, y, z)
    return x + y + z


def fun5(x, y):
    """Return x / y.

    CHANGE: new function.
    Raises ValueError for non-numeric input and ZeroDivisionError if y is 0.
    """
    _check_numbers(x, y)
    if y == 0:
        raise ZeroDivisionError("Cannot divide by zero.")
    return x / y
