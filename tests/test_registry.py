from life4.life4.core import Life4RankEnum
from life4.life4.ranks.registry import IN_SCOPE, load_ranks


def test_scope_is_pearl_through_emerald():
    assert IN_SCOPE == (
        Life4RankEnum.Pearl,
        Life4RankEnum.Topaz,
        Life4RankEnum.Amethyst,
        Life4RankEnum.Emerald,
    )


def test_every_in_scope_tier_has_five_subranks():
    ranks = load_ranks()
    assert set(ranks) == set(IN_SCOPE)
    for tier, subranks in ranks.items():
        assert [r.subrank for r in subranks] == [1, 2, 3, 4, 5], tier


def test_out_of_scope_tiers_are_filtered_before_validation():
    # Copper carries `calories` and `set` goals the parser rejects. If the
    # filter ran after validation this call would raise.
    load_ranks()


def test_amethyst_one_matches_the_published_requirements():
    amethyst = load_ranks()[Life4RankEnum.Amethyst][0]
    assert [str(r) for r in amethyst.requirements] == [
        "Full Combo all 14s over 991k (14E, 980k)",
        "PFC 60 14s",
        "LIFE4 Clear all 15s over 980k (19E, 955k)",
        "PFC 26 15s",
        "AAA 120 15s",
        "Clear all 16s over 955k (24E, 910k)",
        "PFC 8 16s",
        "AAA 60 16s",
        "Clear all 17s over 910k (19E, 860k)",
        "AAA 12 17s",
        "Clear 26 18s over 810k (6E, 760k)",
        "960k+ an 18",
        "MFC a 6+",
        "SDP a 13+",
        "MA Points: 6",
        "Earn Topaz or above on 1 Trial",
    ]


def test_emerald_five_has_the_folder_average_substitution():
    emerald_5 = load_ranks()[Life4RankEnum.Emerald][4]
    assert emerald_5.substitutions
    assert "PFC all 14s with a 999,700 Folder Average" in [
        str(s) for s in emerald_5.substitutions
    ]


def test_total_in_scope_goal_count():
    ranks = load_ranks()
    total = sum(
        len(r.requirements) + len(r.substitutions)
        for subranks in ranks.values()
        for r in subranks
    )
    assert total == 583
