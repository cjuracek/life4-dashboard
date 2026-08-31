from conftest import chart, dataset

from life4.life4.ranks.requirements import (
    CountRequirement,
    FolderRequirement,
    Requirement,
)
from life4.life4.ranks.wording import ClearType


def played(title, level, score, **extra):
    return chart(title=title, level=level, score=score, record_on="1/1/2026", **extra)


def test_blockers_are_alphabetical_regardless_of_score():
    # The list is read to find a specific song, so it sorts by title. An
    # unplayed chart does NOT float to the top -- a score-based order reads
    # as the list changing its mind partway down.
    data = dataset(
        played("apple", 16, 999_000),
        played("cherry", 16, 940_000),
        chart(title="banana", level=16),
        played("damson", 16, 900_000),
    )
    blockers = FolderRequirement(level=16, min_score=950_000).blockers(data)
    assert list(blockers["song"]) == ["banana", "cherry", "damson"]
    assert list(blockers["needs"]) == ["unplayed", "+10,000", "+50,000"]


def test_blockers_sort_case_insensitively():
    # A plain sort strands lowercase titles after every capitalised one,
    # putting "fluctus" below "THE SAFARI".
    data = dataset(
        chart(title="THE SAFARI", level=16),
        chart(title="fluctus", level=16),
        chart(title="Arcadia", level=16),
    )
    blockers = FolderRequirement(level=16, min_score=950_000).blockers(data)
    assert list(blockers["song"]) == ["Arcadia", "fluctus", "THE SAFARI"]


def test_blockers_are_empty_when_every_chart_clears_the_floor():
    data = dataset(played("a", 16, 999_000))
    assert FolderRequirement(level=16, min_score=950_000).blockers(data).empty


def test_a_chart_failing_only_the_lamp_names_the_current_and_target_lamp():
    data = dataset(
        played("full_combo", 16, 980_000, fc_date="1/2/2026"),
        played("just_cleared", 16, 970_000),
    )
    req = FolderRequirement(level=16, clear_type=ClearType.GOOD, min_score=950_000)
    blockers = req.blockers(data)
    assert list(blockers["song"]) == ["just_cleared"]
    assert list(blockers["needs"]) == ["Clear → Full Combo"]


def test_a_chart_failing_both_conditions_appears_once():
    # The two conditions used to live on separate delegate objects whose
    # frames were concatenated and deduped. They are one check now, so a
    # chart can only produce one row -- and the score gap is the actionable
    # number, so it wins over the lamp label.
    data = dataset(played("aaa", 14, 900_000))
    req = FolderRequirement(level=14, clear_type=ClearType.GOOD, min_score=991_000)
    blockers = req.blockers(data)
    assert len(blockers) == 1
    assert blockers.loc[0, "needs"] == "+91,000"


def test_an_unplayed_chart_reads_as_unplayed_not_as_a_lamp_upgrade():
    data = dataset(chart(title="unplayed", level=16))
    req = FolderRequirement(level=16, clear_type=ClearType.LIFE4, min_score=950_000)
    assert list(req.blockers(data)["needs"]) == ["unplayed"]


def test_count_based_requirements_report_no_blockers():
    # "PFC 5 16s" has no denominator, so there is no chart to name.
    data = dataset(played("a", 16, 999_000))
    req = CountRequirement(level=16, count=5, clear_type=ClearType.PERFECT)
    assert req.blockers(data).empty


def test_blockers_respect_the_required_pool():
    # A marked chart must never appear as a blocker -- that is the whole
    # point of the REQUIRED pool.
    data = dataset(
        played("a", 16, 999_000),
        chart(title="marked", level=16, availability="removed"),
    )
    assert FolderRequirement(level=16, min_score=950_000).blockers(data).empty


def test_requirements_have_stable_string_forms():
    # The checkbox key embeds str(requirement); the default object.__str__
    # would embed a memory address and change on module reload.
    pfc_60 = CountRequirement(level=14, count=60, clear_type=ClearType.PERFECT)
    assert str(pfc_60) == "PFC 60 14s"
    assert (
        str(CountRequirement(level=18, count=1, clear_type=ClearType.PERFECT))
        == "PFC an 18"
    )
    assert (
        str(CountRequirement(level=15, count=105, min_score=990_000)) == "AAA 105 15s"
    )
    assert str(CountRequirement(level=18, count=1, min_score=990_000)) == "AAA an 18"
    assert "object at 0x" not in str(pfc_60)


def test_folder_requirement_str_matches_life4_wording():
    req = FolderRequirement(
        level=16,
        clear_type=ClearType.LIFE4,
        min_score=980_000,
        exceptions=10,
        exception_floor=955_000,
    )
    assert str(req) == "LIFE4 Clear all 16s over 980k (10E, 955k)"


def test_blockers_return_exactly_song_score_needs_columns():
    data = dataset(chart(title="a", level=16))
    blockers = FolderRequirement(level=16, min_score=950_000).blockers(data)
    assert tuple(blockers.columns) == ("song", "score", "needs")
    assert "title" not in blockers.columns
    assert "diff" not in blockers.columns
    assert tuple(Requirement.BLOCKER_COLUMNS) == ("song", "score", "needs")


def test_unique_title_at_a_level_renders_bare_with_no_parenthetical():
    data = dataset(chart(title="Ace out", level=14, diff="CSP"))
    blockers = FolderRequirement(level=14, min_score=950_000).blockers(data)
    assert list(blockers["song"]) == ["Ace out"]


def test_title_appearing_twice_at_a_level_suffixes_each_with_its_own_difficulty():
    data = dataset(
        chart(title="Ace out", level=14, diff="CSP"),
        chart(title="Ace out", level=14, diff="ESP"),
    )
    blockers = FolderRequirement(level=14, min_score=950_000).blockers(data)
    assert set(blockers["song"]) == {"Ace out (CSP)", "Ace out (ESP)"}


def test_three_way_collision_suffixes_all_three():
    data = dataset(
        chart(title="collider", level=11, diff="CSP"),
        chart(title="collider", level=11, diff="DSP"),
        chart(title="collider", level=11, diff="ESP"),
    )
    blockers = FolderRequirement(level=11, min_score=950_000).blockers(data)
    assert set(blockers["song"]) == {
        "collider (CSP)",
        "collider (DSP)",
        "collider (ESP)",
    }
