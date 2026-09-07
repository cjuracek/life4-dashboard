"""Exception types for defects in the source sheet.

Every one of these means the same thing to the person running the app: the
spreadsheet is wrong, it was caught at load before any number was computed,
and the message says what to fix. They are distinct classes so tests can
assert on the specific defect, and they share ``DataError`` so ``app.py``
needs exactly one handler no matter which check trips.
"""


class DataError(Exception):
    """The source sheet is unusable. Caught at the app boundary."""


class SchemaError(DataError):
    """A tab is missing a column the app reads."""


class DuplicateKeyError(DataError):
    """A tab has more than one row for the same (title, diff)."""


class ValueDefectError(DataError):
    """A tab has a cell whose *value* is unusable.

    Distinct from SchemaError: the column resolved fine, but what is in it
    cannot be trusted -- a garbled number, a level outside 1-19, a difficulty
    code that is neither singles nor doubles.
    """
