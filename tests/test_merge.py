import pandas as pd
from conftest import chart, frame

from life4.data.merge import merge_scores


def test_primary_defines_the_chart_pool_and_levels():
    primary = frame(chart(title="drift", diff="DSP", level=15))
    secondary = frame(chart(title="drift", diff="DSP", level=14, score=900_000))
    merged = merge_scores(primary, secondary).charts
    assert len(merged) == 1
    assert merged.loc[0, "level"] == 15


def test_charts_only_in_secondary_are_dropped():
    primary = frame(chart(title="a", level=16))
    secondary = frame(
        chart(title="a", level=16), chart(title="gone", level=16, score=999_000)
    )
    assert list(merge_scores(primary, secondary).charts["title"]) == ["a"]


def test_score_is_the_max_across_sources():
    primary = frame(chart(title="a", level=16, score=980_000))
    secondary = frame(chart(title="a", level=16, score=991_000))
    assert merge_scores(primary, secondary).charts.loc[0, "score"] == 991_000


def test_a_chart_played_only_on_the_secondary_carries_over():
    primary = frame(chart(title="a", level=16))
    secondary = frame(
        chart(
            title="a", level=16, score=985_000, record_on="1/1/2026", fc_date="1/2/2026"
        )
    )
    merged = merge_scores(primary, secondary).charts
    assert merged.loc[0, "score"] == 985_000
    assert merged.loc[0, "fc_date"] == "1/2/2026"


def test_achievement_dates_union_across_sources():
    primary = frame(chart(title="a", level=16, score=991_000, record_on="3/1/2026"))
    secondary = frame(
        chart(
            title="a",
            level=16,
            score=985_000,
            record_on="1/1/2026",
            fc_date="1/2/2026",
            pfc_date="1/3/2026",
        )
    )
    merged = merge_scores(primary, secondary).charts
    # The PFC was earned on the secondary cabinet; it must survive the merge
    # even though the primary holds the higher score.
    assert merged.loc[0, "pfc_date"] == "1/3/2026"
    assert merged.loc[0, "score"] == 991_000


def test_perfect_count_travels_with_the_higher_score():
    # A PFC's score is a deterministic function of its perfect count, so the
    # max score and its perfect count always come from the same row. Taking
    # them from different rows could manufacture an SDP that never happened.
    primary = frame(chart(title="a", level=16, score=980_000, perfect=40))
    secondary = frame(chart(title="a", level=16, score=999_950, perfect=5))
    merged = merge_scores(primary, secondary).charts
    assert merged.loc[0, "score"] == 999_950
    assert merged.loc[0, "perfect"] == 5


def test_perfect_count_is_not_taken_from_the_lower_scoring_row():
    primary = frame(chart(title="a", level=16, score=999_950, perfect=5))
    secondary = frame(chart(title="a", level=16, score=980_000, perfect=40))
    merged = merge_scores(primary, secondary).charts
    assert merged.loc[0, "perfect"] == 5


def test_orphan_secondary_chart_is_reported_not_silently_dropped():
    # WORLD is a strict superset of CTF by construction, so a CTF chart with
    # no WORLD match is always a defect -- usually a drifted title. It must
    # surface, because it means A3 scores stopped counting.
    primary = frame(chart(title="Tiger rampage (sasakure.UK)", level=17))
    secondary = frame(
        chart(title="Tiger rampage", level=17, score=969_390, record_on="1/1/2026")
    )
    result = merge_scores(primary, secondary)
    assert len(result.charts) == 1
    assert pd.isna(result.charts.loc[0, "score"])
    assert list(result.orphans["title"]) == ["Tiger rampage"]


def test_no_orphans_when_every_secondary_chart_matches():
    primary = frame(chart(title="a", level=16), chart(title="b", level=16))
    secondary = frame(chart(title="a", level=16, score=900_000))
    assert len(merge_scores(primary, secondary).orphans) == 0


def test_titles_are_never_normalized_before_joining():
    # 'PARANOiA' and 'PARANOiA (kskst mix)' are different charts. Stripping
    # parentheticals to make matching forgiving would merge them.
    primary = frame(
        chart(title="PARANOiA", level=16), chart(title="PARANOiA (kskst mix)", level=16)
    )
    secondary = frame(chart(title="PARANOiA", level=16, score=950_000))
    merged = merge_scores(primary, secondary).charts
    scores = dict(zip(merged["title"], merged["score"]))
    assert scores["PARANOiA"] == 950_000
    assert pd.isna(scores["PARANOiA (kskst mix)"])


def test_unplayed_on_both_stays_unplayed():
    merged = merge_scores(
        frame(chart(title="a", level=16)), frame(chart(title="a", level=16))
    ).charts
    assert pd.isna(merged.loc[0, "score"])
