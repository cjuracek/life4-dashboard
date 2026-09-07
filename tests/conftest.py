import numpy as np
import pandas as pd
import pytest

from life4.data.schema import CANONICAL_COLUMNS, NUMERIC_COLUMNS
from life4.ddr import DDRDataset


def chart(**overrides):
    """One chart row. Everything defaults to unplayed; override what matters."""
    row = dict.fromkeys(CANONICAL_COLUMNS, np.nan)
    row.update(diff="ESP", level=16, title="untitled")
    row.update(overrides)
    return row


def frame(*charts):
    """Build a frame with the same dtypes normalize() produces from real CSV."""
    df = pd.DataFrame(list(charts), columns=list(CANONICAL_COLUMNS))
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def dataset(*charts, trials=None):
    return DDRDataset(frame(*charts), trials=trials or [])


@pytest.fixture
def make_dataset():
    return dataset
