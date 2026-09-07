from enum import Enum

import pandas as pd


class AvailabilityClass(Enum):
    """How a chart's availability marker affects requirement evaluation."""

    NORMAL = "normal"
    OPTIONAL = "optional"


class ChartPool(Enum):
    """Which charts a requirement is evaluated against.

    REQUIRED -- "all 16s over 955k" style requirements. Optional charts must
    not appear here, or an unplayable chart blocks the requirement forever.

    EARNED -- "PFC 26 16s" style counts. Optional charts count if played: a
    chart removed from the game still credits the score you earned on it.
    """

    REQUIRED = "required"
    EARNED = "earned"


_POOLS = {
    ChartPool.REQUIRED: frozenset({AvailabilityClass.NORMAL}),
    ChartPool.EARNED: frozenset({AvailabilityClass.NORMAL, AvailabilityClass.OPTIONAL}),
}


def classify(value) -> AvailabilityClass:
    """Blank means an ordinary chart; any marker means "counts, never blocks".

    There is deliberately no lookup table and no EXCLUDED class. A marker means
    the chart is not necessarily playable on demand, so it must never count
    against the player -- but a score earned on it still counts for them.
    """
    if value is None or pd.isna(value) or str(value).strip() == "":
        return AvailabilityClass.NORMAL
    return AvailabilityClass.OPTIONAL


def pool_classes(pool: ChartPool) -> frozenset[AvailabilityClass]:
    return _POOLS[pool]
