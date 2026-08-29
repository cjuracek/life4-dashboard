from conftest import chart, dataset

from life4.life4.ranks.requirements import ClearRequirement


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
