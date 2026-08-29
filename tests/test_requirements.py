import pytest

from conftest import chart, dataset

from life4.life4.core import MAPointsUnknownLevel
from life4.life4.ranks.requirements import (
    ClearRequirement,
    FloorRequirement,
    PFCRequirement,
)


def played(title, level, score):
    return chart(title=title, level=level, score=score, record_on="1/1/2026")


def test_clear_without_floor_ignores_unplayed_charts():
    d = dataset(
        played("a", 19, 720_000),
        played("b", 19, 810_000),
        *[chart(title=str(i), level=19) for i in range(8)],
    )
    assert ClearRequirement(level=19, num=1).is_satisfied(d)
    assert not ClearRequirement(level=19, num=5).is_satisfied(d)
    assert ClearRequirement(level=19, num=5).get_progress(d) == "2/5"


def test_clear_with_floor_counts_only_scores_above_it():
    d = dataset(played("a", 18, 900_000), played("b", 18, 700_000))
    assert ClearRequirement(level=18, num=1, floor=810_000).is_satisfied(d)
    assert not ClearRequirement(level=18, num=2, floor=810_000).is_satisfied(d)


def test_clear_exceptions_fill_the_gap_up_to_the_limit():
    d = dataset(
        played("a", 18, 900_000),
        played("b", 18, 780_000),
        played("c", 18, 770_000),
    )
    req = ClearRequirement(
        level=18, num=3, floor=810_000, num_exceptions=1, exception_floor=760_000
    )
    assert not req.is_satisfied(d)
    assert req.get_progress(d) == "2/3"


def test_clear_exceptions_below_the_exception_floor_do_not_count():
    d = dataset(played("a", 18, 900_000), played("b", 18, 700_000))
    req = ClearRequirement(
        level=18, num=2, floor=810_000, num_exceptions=1, exception_floor=760_000
    )
    assert not req.is_satisfied(d)


def pfc(title, level, perfects):
    return chart(
        title=title,
        level=level,
        score=1_000_000 - perfects * 10,
        perfect=perfects,
        record_on="1/1/2026",
        pfc_date="1/2/2026",
    )


def test_ma_points_sums_sdps_and_mfcs():
    d = dataset(pfc("a", 14, 5), pfc("b", 12, 3))
    # SDP is 1/10 of an MFC: level 14 -> 0.8, level 12 -> 0.4
    assert d.get_ma_points() == pytest.approx(1.2)


def test_pfc_with_ten_or_more_perfects_is_not_an_sdp():
    d = dataset(pfc("a", 14, 10))
    assert d.get_ma_points() == 0


def test_sdps_at_16_and_above_are_worth_a_flat_2_point_5():
    d = dataset(pfc("a", 17, 4), pfc("b", 19, 2))
    assert d.get_ma_points() == pytest.approx(5.0)


def test_low_level_sdps_still_count_toward_ma_points():
    # 12 MFCs and 81 SDPs in the real data sit below level 8, worth 11.22
    # points. Any level filtering would silently discard them.
    d = dataset(pfc("a", 3, 4), pfc("b", 7, 2))
    assert d.get_ma_points() == pytest.approx(0.025 + 0.1)


def test_a_level_with_no_mapping_raises_an_actionable_error():
    d = dataset(pfc("a", 20, 4))
    with pytest.raises(MAPointsUnknownLevel) as exc:
        d.get_ma_points()
    assert "20" in str(exc.value)


def test_unplayed_marked_chart_does_not_block_a_floor_requirement():
    d = dataset(
        played("a", 17, 900_000),
        chart(title="roll the dice", level=17, availability="galaxy brave"),
    )
    assert FloorRequirement(level=17, floor=850_000).is_satisfied(d)


def test_played_marked_chart_counts_toward_a_pfc_count():
    d = dataset(
        pfc("a", 17, 4),
        chart(
            title="blizzard of arrows",
            level=17,
            availability="galaxy brave",
            score=999_960,
            perfect=4,
            record_on="1/1/2026",
            pfc_date="1/2/2026",
        ),
    )
    assert PFCRequirement(level=17, num=2).is_satisfied(d)


def test_a_removed_chart_still_credits_a_score_you_earned_on_it():
    # The owner's rule: a marked chart counts if played, but never counts
    # against you. A chart cleared before it left the game still credits.
    d = dataset(
        played("a", 16, 900_000),
        chart(
            title="realize",
            level=16,
            availability="removed",
            score=999_000,
            perfect=4,
            record_on="1/1/2026",
            pfc_date="1/2/2026",
        ),
    )
    assert PFCRequirement(level=16, num=1).is_satisfied(d)
    assert FloorRequirement(level=16, floor=850_000).is_satisfied(d)
