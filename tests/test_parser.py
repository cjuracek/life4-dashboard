import pytest

from life4.life4.core import Life4RankEnum
from life4.life4.ranks.parser import GoalParseError, parse_goal
from life4.life4.ranks.requirements import (
    CountRequirement,
    FolderRequirement,
    MAPointsRequirement,
    TrialRequirement,
)


def test_count_goal_with_score():
    req = parse_goal({"t": "songs", "d": 18, "score": 960000, "song_count": 1})
    assert isinstance(req, CountRequirement)
    assert str(req) == "960k+ an 18"


def test_count_goal_with_clear_type_and_higher_diff():
    req = parse_goal(
        {
            "t": "songs",
            "d": 13,
            "clear_type": "sdp",
            "song_count": 1,
            "higher_diff": True,
        }
    )
    assert str(req) == "SDP a 13+"
    assert req.multiple_levels


def test_folder_goal():
    req = parse_goal(
        {
            "t": "songs",
            "d": 15,
            "clear_type": "life4",
            "score": 980000,
            "exceptions": 19,
            "exception_score": 955000,
        }
    )
    assert isinstance(req, FolderRequirement)
    assert str(req) == "LIFE4 Clear all 15s over 980k (19E, 955k)"


def test_folder_average_goal():
    req = parse_goal(
        {
            "t": "songs",
            "d": 14,
            "clear_type": "perfect",
            "average_score": 999500,
            "exceptions": 4,
            "exception_score": 996000,
        }
    )
    assert str(req) == "PFC all 14s with a 999,500 Folder Average (4E, 996k)"


def test_ma_points_goal():
    req = parse_goal({"t": "ma_points", "points": 12})
    assert isinstance(req, MAPointsRequirement)
    assert str(req) == "MA Points: 12"


def test_trial_goal():
    req = parse_goal({"t": "trial", "rank": "amethyst", "count": 1})
    assert isinstance(req, TrialRequirement)
    assert req.rank is Life4RankEnum.Amethyst
    assert str(req) == "Earn Amethyst or above on 1 Trial"


def test_id_is_ignored():
    parse_goal({"t": "songs", "d": 18, "score": 960000, "song_count": 1, "id": 42})


def test_unknown_goal_type_raises():
    with pytest.raises(GoalParseError, match="calories"):
        parse_goal({"t": "calories", "count": 800})


def test_set_goal_raises():
    with pytest.raises(GoalParseError, match="set"):
        parse_goal({"t": "set", "diff_nums": [11, 11, 11], "higher_diff": True})


def test_unknown_clear_type_raises():
    with pytest.raises(GoalParseError, match="quadruple"):
        parse_goal({"t": "songs", "d": 14, "clear_type": "quadruple", "song_count": 1})


def test_unknown_field_raises():
    with pytest.raises(GoalParseError, match="stamina_bonus"):
        parse_goal({"t": "songs", "d": 14, "song_count": 1, "stamina_bonus": True})


def test_unknown_trial_rank_raises():
    with pytest.raises(GoalParseError, match="mithril"):
        parse_goal({"t": "trial", "rank": "mithril", "count": 1})
