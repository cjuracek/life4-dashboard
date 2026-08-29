from conftest import chart, dataset

from life4.ddr import Lamp
from life4.life4.ranks.requirements import (
    AAARequirement,
    FloorRequirement,
    LampFloorRequirement,
    LampRequirement,
    PFCRequirement,
)


def played(title, level, score, **extra):
    return chart(title=title, level=level, score=score, record_on="1/1/2026", **extra)


def test_floor_blockers_list_unplayed_first_then_low_scores():
    data = dataset(
        played("a", 16, 999_000),
        played("b", 16, 940_000),
        chart(title="c", level=16),
    )
    blockers = FloorRequirement(level=16, floor=950_000).blockers(data)
    assert list(blockers["title"]) == ["c", "b"]
    assert list(blockers["needs"]) == ["unplayed", "+10,000"]


def test_floor_blockers_are_empty_when_every_chart_clears_the_floor():
    data = dataset(played("a", 16, 999_000))
    assert FloorRequirement(level=16, floor=950_000).blockers(data).empty


def test_lamp_blockers_name_the_current_and_target_lamp():
    data = dataset(
        played("full_combo", 16, 980_000, fc_date="1/2/2026"),
        played("just_cleared", 16, 940_000),
    )
    blockers = LampRequirement(level=16, lamp=Lamp.Blue).blockers(data)
    assert list(blockers["title"]) == ["just_cleared"]
    assert list(blockers["needs"]) == ["Clear -> Blue"]


def test_lamp_floor_blockers_merge_both_and_do_not_duplicate_a_chart():
    data = dataset(
        played("weak", 16, 900_000),
        chart(title="unplayed", level=16),
    )
    blockers = LampFloorRequirement(level=16, lamp=Lamp.Blue, floor=950_000).blockers(
        data
    )
    assert len(blockers) == len(set(zip(blockers["title"], blockers["diff"])))
    assert set(blockers["title"]) == {"weak", "unplayed"}


def test_count_based_requirements_report_no_blockers():
    # "PFC 5 16s" has no denominator, so there is no chart to name.
    data = dataset(played("a", 16, 999_000))
    assert PFCRequirement(level=16, num=5).blockers(data).empty


def test_blockers_respect_the_required_pool():
    # A marked chart must never appear as a blocker -- that is the whole point
    # of the REQUIRED pool.
    data = dataset(
        played("a", 16, 999_000),
        chart(title="marked", level=16, availability="removed"),
    )
    assert FloorRequirement(level=16, floor=950_000).blockers(data).empty


def test_pfc_and_aaa_have_stable_string_forms():
    # The checkbox key embeds str(requirement); the default object.__str__
    # would embed a memory address and change on module reload.
    assert str(PFCRequirement(level=14, num=60)) == "PFC 60 14s"
    assert str(PFCRequirement(level=18, num=1)) == "PFC an 18"
    assert str(AAARequirement(level=15, num=105)) == "AAA 105 15s"
    assert str(AAARequirement(level=18, num=1)) == "AAA an 18"
    assert "object at 0x" not in str(PFCRequirement(level=14, num=1))
