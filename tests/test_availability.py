import numpy as np

from life4.data.availability import (
    AvailabilityClass,
    ChartPool,
    classify,
    pool_classes,
)


def test_blank_availability_is_a_normal_chart():
    assert classify(np.nan) is AvailabilityClass.NORMAL
    assert classify(None) is AvailabilityClass.NORMAL
    assert classify("") is AvailabilityClass.NORMAL


def test_any_marker_is_optional():
    for marker in ("removed", "galaxy brave", "course trial", "phase 2"):
        assert classify(marker) is AvailabilityClass.OPTIONAL


def test_an_unrecognised_marker_is_optional_and_never_blocks():
    # Decided 2026-08-29: a marker means "not necessarily playable on demand",
    # so it must never block progress. One rule, no lookup table.
    assert classify("some future event") is AvailabilityClass.OPTIONAL


def test_required_pool_excludes_optional_charts():
    assert pool_classes(ChartPool.REQUIRED) == frozenset({AvailabilityClass.NORMAL})


def test_earned_pool_includes_optional_charts():
    assert pool_classes(ChartPool.EARNED) == frozenset(
        {AvailabilityClass.NORMAL, AvailabilityClass.OPTIONAL}
    )
