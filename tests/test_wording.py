import pytest

from life4.life4.ranks.wording import (
    ClearType,
    article,
    count_phrase,
    exception_clause,
    folder_phrase,
    format_score,
)


@pytest.mark.parametrize(
    "level,expected", [(8, "an"), (11, "an"), (18, "an"), (14, "a"), (19, "a")]
)
def test_article_matches_life4_usage(level, expected):
    assert article(level) == expected


def test_round_thousands_render_as_k():
    assert format_score(996_000) == "996k"


def test_non_round_scores_render_with_separators():
    assert format_score(998_500) == "998,500"


def test_exception_clause_omits_absent_shadow_floor():
    assert exception_clause(1, None) == " (1E)"
    assert exception_clause(14, 980_000) == " (14E, 980k)"
    assert exception_clause(0, None) == ""


def test_990k_renders_as_aaa():
    assert count_phrase(level=15, count=120, min_score=990_000) == "AAA 120 15s"
    assert count_phrase(level=12, count=1, min_score=990_000) == "AAA a 12"


def test_scored_count_without_exceptions_leads_with_the_score():
    # LIFE4 renders this as "750k+ 5 18s", NOT "Clear 5 18s over 750k". The
    # "Clear N over X" template is selected by the presence of exceptions,
    # not by the count.
    assert count_phrase(level=18, count=5, min_score=750_000) == "750k+ 5 18s"
    assert count_phrase(level=14, count=1, min_score=960_000) == "960k+ a 14"


def test_scored_count_with_exceptions_uses_the_clear_over_template():
    assert (
        count_phrase(
            level=18,
            count=26,
            min_score=810_000,
            exceptions=6,
            exception_floor=760_000,
        )
        == "Clear 26 18s over 810k (6E, 760k)"
    )


def test_clear_type_counts_use_the_abbreviation():
    assert (
        count_phrase(level=14, count=60, clear_type=ClearType.PERFECT) == "PFC 60 14s"
    )
    assert (
        count_phrase(level=13, count=1, clear_type=ClearType.SDP, higher_diff=True)
        == "SDP a 13+"
    )
    assert (
        count_phrase(
            level=11, count=3, clear_type=ClearType.MARVELOUS, higher_diff=True
        )
        == "MFC 3 11+s"
    )


def test_bare_counts_say_clear():
    assert count_phrase(level=19, count=1) == "Clear a 19"
    assert count_phrase(level=15, count=2) == "Clear 2 15s"


def test_folder_phrases_spell_the_lamp_out_in_full():
    assert (
        folder_phrase(
            level=14,
            clear_type=ClearType.GOOD,
            min_score=991_000,
            exceptions=14,
            exception_floor=980_000,
        )
        == "Full Combo all 14s over 991k (14E, 980k)"
    )
    assert (
        folder_phrase(
            level=15,
            clear_type=ClearType.LIFE4,
            min_score=980_000,
            exceptions=19,
            exception_floor=955_000,
        )
        == "LIFE4 Clear all 15s over 980k (19E, 955k)"
    )
    assert (
        folder_phrase(
            level=16, min_score=955_000, exceptions=24, exception_floor=910_000
        )
        == "Clear all 16s over 955k (24E, 910k)"
    )


def test_folder_average_phrase():
    assert (
        folder_phrase(
            level=14,
            clear_type=ClearType.PERFECT,
            average_score=999_500,
            exceptions=4,
            exception_floor=996_000,
        )
        == "PFC all 14s with a 999,500 Folder Average (4E, 996k)"
    )
    assert (
        folder_phrase(level=14, clear_type=ClearType.PERFECT, average_score=999_700)
        == "PFC all 14s with a 999,700 Folder Average"
    )
