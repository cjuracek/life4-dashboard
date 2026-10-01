from conftest import chart, dataset

from life4.life4.ranks.requirements import (
    BlockerReport,
    CountRequirement,
    FolderRequirement,
)
from life4.life4.ranks.wording import ClearType


def played(title, level, score, **extra):
    return chart(title=title, level=level, score=score, record_on="1/1/2026", **extra)


def test_blockers_sort_case_insensitively():
    # A plain sort strands lowercase titles after every capitalised one,
    # putting "fluctus" below "THE SAFARI".
    data = dataset(
        chart(title="THE SAFARI", level=16),
        chart(title="fluctus", level=16),
        chart(title="Arcadia", level=16),
    )
    blockers = FolderRequirement(level=16, min_score=950_000).blockers(data)
    assert list(blockers.unplayed_rows["song"]) == ["Arcadia", "fluctus", "THE SAFARI"]


def test_blockers_are_empty_when_every_chart_clears_the_floor():
    data = dataset(played("a", 16, 999_000))
    assert FolderRequirement(level=16, min_score=950_000).blockers(data).empty


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


def test_unique_title_at_a_level_renders_bare_with_no_parenthetical():
    data = dataset(chart(title="Ace out", level=14, diff="CSP"))
    blockers = FolderRequirement(level=14, min_score=950_000).blockers(data)
    assert list(blockers.unplayed_rows["song"]) == ["Ace out"]


def test_title_appearing_twice_at_a_level_suffixes_each_with_its_own_difficulty():
    data = dataset(
        chart(title="Ace out", level=14, diff="CSP"),
        chart(title="Ace out", level=14, diff="ESP"),
    )
    blockers = FolderRequirement(level=14, min_score=950_000).blockers(data)
    assert set(blockers.unplayed_rows["song"]) == {"Ace out (CSP)", "Ace out (ESP)"}


def test_three_way_collision_suffixes_all_three():
    data = dataset(
        chart(title="collider", level=11, diff="CSP"),
        chart(title="collider", level=11, diff="DSP"),
        chart(title="collider", level=11, diff="ESP"),
    )
    blockers = FolderRequirement(level=11, min_score=950_000).blockers(data)
    assert set(blockers.unplayed_rows["song"]) == {
        "collider (CSP)",
        "collider (DSP)",
        "collider (ESP)",
    }


def report(**counts):
    return BlockerReport(**counts)


def test_label_with_exceptions_names_unplayed_must_raise_and_exception_budget():
    r = report(unplayed=1, must_raise=1, exceptions_used=4, exceptions_allowed=3)
    assert r.label() == "1 unplayed · 1 must raise · 4/3 exceptions"


def test_label_omits_zero_count_parts():
    assert report(unplayed=4, exceptions_used=2, exceptions_allowed=22).label() == (
        "4 unplayed · 2/22 exceptions"
    )
    assert report(must_raise=1, exceptions_allowed=3).label() == "1 must raise"


def test_label_without_exceptions_says_to_improve():
    assert report(unplayed=1, to_improve=2).label() == "1 unplayed · 2 to improve"
    assert report(unplayed=1).label() == "1 unplayed"


def test_header_lines_leave_the_exception_budget_to_the_exceptions_title():
    assert report(exceptions_used=2, exceptions_allowed=22).header_lines() == []


def test_header_lines_show_folder_average():
    r = report(exceptions_used=3, exceptions_allowed=4, average=(999_310.4, 999_500))
    assert r.header_lines() == ["Folder average: 999,310 / 999,500"]


def test_required_title_counts_only_the_played_charts_in_its_table():
    # Unplayed charts have a section of their own, with its own count.
    r = report(unplayed=1, must_raise=3, exceptions_used=4, exceptions_allowed=12)
    assert r.required_title() == "Required — 3 must raise"
    assert report(unplayed=1, to_improve=2).required_title() == (
        "Required — 2 to improve"
    )


def test_unplayed_title_counts_the_charts():
    assert report(unplayed=1).unplayed_title() == "Unplayed — 1 chart"
    assert report(unplayed=23).unplayed_title() == "Unplayed — 23 charts"


def test_exceptions_title_shows_the_budget_and_any_overrun():
    assert report(exceptions_used=9, exceptions_allowed=12).exceptions_title() == (
        "Exceptions — 9 used / 12 allowed"
    )
    assert report(exceptions_used=12, exceptions_allowed=12).exceptions_title() == (
        "Exceptions — 12 used / 12 allowed"
    )
    assert report(exceptions_used=14, exceptions_allowed=12).exceptions_title() == (
        "Exceptions — 14 used / 12 allowed (2 over)"
    )


def test_over_budget_only_when_more_exceptions_are_used_than_allowed():
    assert not report(exceptions_used=12, exceptions_allowed=12).over_budget
    assert report(exceptions_used=13, exceptions_allowed=12).over_budget


def test_folder_average_reads_dash_when_nothing_is_played():
    assert report(average=(None, 999_500)).header_lines() == [
        "Folder average: - / 999,500"
    ]


def test_report_is_empty_when_it_has_no_rows():
    assert report().empty


def test_unplayed_charts_alone_make_a_report_non_empty():
    data = dataset(chart(title="u", level=16))
    assert not FolderRequirement(level=16, min_score=950_000).blockers(data).empty


def sixteens(**kwargs):
    return FolderRequirement(level=16, min_score=965_000, **kwargs)


def test_charts_within_the_exception_allowance_are_not_to_improve():
    # The reported bug: Amethyst 3 read "4 unplayed · 2 to improve" although
    # both scored charts sit above the shadow floor inside 22 exceptions.
    data = dataset(
        chart(title="Danmaku shinkou", level=16),
        chart(title="Gale Rider", level=16),
        chart(title="Hit Show Heroes", level=16),
        chart(title="Meteora -meteor-", level=16),
        played("Hou", 16, 952_610),
        played("TRIP MACHINE", 16, 958_820),
        played("passing", 16, 990_000),
    )
    report = sixteens(exceptions=22, exception_floor=930_000).blockers(data)
    assert report.label() == "4 unplayed · 2/22 exceptions"
    assert list(report.unplayed_rows["song"]) == [
        "Danmaku shinkou",
        "Gale Rider",
        "Hit Show Heroes",
        "Meteora -meteor-",
    ]
    assert report.required_rows.empty
    # Every exception is over the floor, so the floor column is left out.
    assert report.exception_rows.to_dict("records") == [
        {"song": "Hou", "score": 952_610, "to 965k": "+12,390"},
        {"song": "TRIP MACHINE", "score": 958_820, "to 965k": "+6,180"},
    ]


def test_the_shadow_floor_is_inclusive():
    data = dataset(played("at", 16, 930_000), played("below", 16, 929_999))
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert (report.must_raise, report.exceptions_used) == (1, 1)


def test_over_budget_counts_only_qualifying_charts_as_exceptions():
    data = dataset(
        chart(title="Hit Show Heroes", level=16),
        played("Danmaku shinkou", 16, 921_300),
        played("Gale Rider", 16, 944_100),
        played("Hou", 16, 952_610),
        played("Meteora", 16, 961_500),
        played("TRIP MACHINE", 16, 958_820),
    )
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert report.label() == "1 unplayed · 1 must raise · 4/3 exceptions"
    assert report.over_budget
    assert list(report.unplayed_rows["song"]) == ["Hit Show Heroes"]
    assert list(report.required_rows["song"]) == ["Danmaku shinkou"]
    danmaku = report.required_rows.iloc[0]
    assert (danmaku["to 930k"], danmaku["to 965k"]) == ("+8,700", "+43,700")
    assert len(report.exception_rows) == 4


def test_a_chart_over_target_missing_only_the_lamp_is_an_exception():
    data = dataset(played("Hou", 16, 990_100))
    req = FolderRequirement(
        level=16,
        clear_type=ClearType.LIFE4,
        min_score=985_000,
        exceptions=17,
        exception_floor=965_000,
    )
    report = req.blockers(data)
    assert report.exceptions_used == 1
    assert report.required_rows.empty
    assert report.exception_rows.to_dict("records") == [
        {
            "song": "Hou",
            "score": 990_100,
            "to 985k": "✓",
            "lamp": "Clear → LIFE4 Clear",
        }
    ]


def test_a_met_lamp_reads_as_a_check():
    data = dataset(played("gale", 16, 971_400, life4_date="1/2/2026"))
    req = FolderRequirement(
        level=16,
        clear_type=ClearType.LIFE4,
        min_score=985_000,
        exceptions=17,
        exception_floor=965_000,
    )
    assert req.blockers(data).exception_rows.loc[0, "lamp"] == "✓"


def test_an_unplayed_chart_is_listed_by_name_alone():
    # No score, no lamp, every target missed: only the title says anything.
    data = dataset(chart(title="unplayed", level=16))
    req = FolderRequirement(
        level=16,
        clear_type=ClearType.LIFE4,
        min_score=985_000,
        exceptions=17,
        exception_floor=965_000,
    )
    report = req.blockers(data)
    assert report.unplayed_rows.to_dict("records") == [{"song": "unplayed"}]
    assert report.required_rows.empty


def test_a_scored_chart_with_no_record_on_is_played_not_unplayed():
    # Review focus 1: unplayed is derived from score alone, as in
    # test_folder_agrees_on_unplayed_when_score_present_but_no_record_on.
    data = dataset(chart(title="a", level=16, score=950_000))
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert (report.unplayed, report.exceptions_used) == (0, 1)


def test_without_exceptions_every_scored_failure_is_to_improve():
    data = dataset(chart(title="u", level=16), played("s", 16, 900_000))
    report = FolderRequirement(level=16, min_score=950_000).blockers(data)
    assert report.label() == "1 unplayed · 1 to improve"
    assert report.header_lines() == []
    assert list(report.required_rows.columns) == ["song", "score", "to 950k"]
    assert report.exception_rows.empty


def test_without_exceptions_a_lamp_only_failure_is_required():
    # The lamp is mandatory only when there is no allowance to excuse it.
    data = dataset(played("s", 16, 990_000))
    req = FolderRequirement(level=16, clear_type=ClearType.LIFE4, min_score=950_000)
    report = req.blockers(data)
    assert report.required_rows.to_dict("records") == [
        {"song": "s", "score": 990_000, "to 950k": "✓", "lamp": "Clear → LIFE4 Clear"}
    ]
    assert report.exception_rows.empty


def test_folder_average_columns_and_header():
    data = dataset(
        played("c", 14, 993_400, gfc_date="1/2/2026"),
        played("d", 14, 998_900, gfc_date="1/2/2026"),
        played("pfc", 14, 999_900, pfc_date="1/2/2026"),
    )
    req = FolderRequirement(
        level=14,
        clear_type=ClearType.PERFECT,
        average_score=999_500,
        exceptions=4,
        exception_floor=996_000,
    )
    report = req.blockers(data)
    assert list(report.required_rows.columns) == ["song", "score", "to 996k", "lamp"]
    assert list(report.exception_rows.columns) == ["song", "score", "lamp"]
    assert report.label() == "1 must raise · 1/4 exceptions"
    assert report.header_lines() == ["Folder average: 997,400 / 999,500"]
    assert report.required_rows.loc[0, "lamp"] == (
        "Great Full Combo → Perfect Full Combo"
    )


def test_an_average_only_failure_has_no_rows():
    # Review focus 2: every chart PFC'd but the average is short. The
    # checkbox text already carries "Avg x/y"; there is no chart to list.
    data = dataset(played("a", 14, 999_000, pfc_date="1/2/2026"))
    req = FolderRequirement(
        level=14,
        clear_type=ClearType.PERFECT,
        average_score=999_500,
        exceptions=4,
        exception_floor=996_000,
    )
    assert not req.is_satisfied(data)
    assert req.blockers(data).empty


def test_unplayed_sort_alphabetically_and_played_sort_worst_score_first():
    # Unplayed charts are looked up by name. Played charts lead with the
    # lowest score -- the biggest gap -- so the worst sit on top.
    data = dataset(
        played("apple", 16, 950_000),
        played("Banana", 16, 920_000),
        chart(title="cherry", level=16),
        played("avocado", 16, 925_000),
        chart(title="Apricot", level=16),
        played("blueberry", 16, 940_000),
    )
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert list(report.unplayed_rows["song"]) == ["Apricot", "cherry"]
    assert list(report.required_rows["song"]) == ["Banana", "avocado"]
    assert list(report.exception_rows["song"]) == ["blueberry", "apple"]


def test_to_improve_charts_sort_worst_score_first():
    data = dataset(played("a", 16, 940_000), played("b", 16, 900_000))
    report = FolderRequirement(level=16, min_score=950_000).blockers(data)
    assert list(report.required_rows["song"]) == ["b", "a"]


def test_equal_scores_fall_back_to_case_insensitive_title():
    data = dataset(played("beta", 16, 950_000), played("Alpha", 16, 950_000))
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert list(report.exception_rows["song"]) == ["Alpha", "beta"]


def test_disambiguated_titles_survive_the_split_into_sections():
    # Review focus 4: two charts of one song at one level, in different
    # sections, still carry their own difficulty.
    data = dataset(
        chart(title="Ace out", level=16, diff="CSP"),
        played("Ace out", 16, 950_000, diff="ESP"),
    )
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert list(report.unplayed_rows["song"]) == ["Ace out (CSP)"]
    assert list(report.exception_rows["song"]) == ["Ace out (ESP)"]
