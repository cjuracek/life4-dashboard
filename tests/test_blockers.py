from conftest import chart, dataset

from life4.ddr import Lamp
from life4.life4.ranks.requirements import (
    AAARequirement,
    FloorRequirement,
    LampFloorRequirement,
    LampRequirement,
    PFCRequirement,
    Requirement,
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
    assert list(blockers["song"]) == ["c", "b"]
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
    assert list(blockers["song"]) == ["just_cleared"]
    assert list(blockers["needs"]) == ["Clear → Full Combo"]


def test_lamp_floor_blockers_merge_both_and_do_not_duplicate_a_chart():
    data = dataset(
        played("weak", 16, 900_000),
        chart(title="unplayed", level=16),
    )
    blockers = LampFloorRequirement(level=16, lamp=Lamp.Blue, floor=950_000).blockers(
        data
    )
    assert len(blockers) == len(set(blockers["song"]))
    assert set(blockers["song"]) == {"weak", "unplayed"}


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


def test_blockers_return_exactly_song_score_needs_columns():
    data = dataset(chart(title="a", level=16))
    blockers = FloorRequirement(level=16, floor=950_000).blockers(data)
    assert tuple(blockers.columns) == ("song", "score", "needs")
    assert "title" not in blockers.columns
    assert "diff" not in blockers.columns
    assert tuple(Requirement.BLOCKER_COLUMNS) == ("song", "score", "needs")


def test_unique_title_at_a_level_renders_bare_with_no_parenthetical():
    data = dataset(chart(title="Ace out", level=14, diff="CSP"))
    blockers = FloorRequirement(level=14, floor=950_000).blockers(data)
    assert list(blockers["song"]) == ["Ace out"]


def test_title_appearing_twice_at_a_level_suffixes_each_with_its_own_difficulty():
    data = dataset(
        chart(title="Ace out", level=14, diff="CSP"),
        chart(title="Ace out", level=14, diff="ESP"),
    )
    blockers = FloorRequirement(level=14, floor=950_000).blockers(data)
    assert set(blockers["song"]) == {"Ace out (CSP)", "Ace out (ESP)"}


def test_three_way_collision_suffixes_all_three():
    data = dataset(
        chart(title="collider", level=11, diff="CSP"),
        chart(title="collider", level=11, diff="DSP"),
        chart(title="collider", level=11, diff="ESP"),
    )
    blockers = FloorRequirement(level=11, floor=950_000).blockers(data)
    assert set(blockers["song"]) == {
        "collider (CSP)",
        "collider (DSP)",
        "collider (ESP)",
    }


def test_lamp_requirement_emits_human_wording_for_unplayed_chart():
    data = dataset(chart(title="unplayed", level=16))
    blockers = LampRequirement(level=16, lamp=Lamp.Red).blockers(data)
    assert list(blockers["needs"]) == ["Not played → LIFE4 Clear"]


def test_lamp_floor_requirement_str_is_unchanged_by_the_lamp_labels_refactor():
    # LAMP_LABELS replaces a private duplicate map inside __str__; the
    # rendered text must not move.
    req = LampFloorRequirement(
        level=16,
        lamp=Lamp.Red,
        floor=980_000,
        num_exceptions=10,
        exception_floor=955_000,
    )
    assert str(req) == "LIFE4 Clear all 16s over 980k (10E, 955k)"


def test_lamp_floor_blockers_still_dedupes_a_chart_failing_both_halves():
    # A chart that fails both the lamp test and the floor test must appear
    # once in the merged list, not twice.
    data = dataset(chart(title="fails_both", level=16))
    blockers = LampFloorRequirement(level=16, lamp=Lamp.Blue, floor=950_000).blockers(
        data
    )
    assert list(blockers["song"]) == ["fails_both"]
