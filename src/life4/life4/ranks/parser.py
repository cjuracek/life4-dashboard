"""One LIFE4 API goal dict -> one Requirement.

Strict on purpose. An unknown goal type, clear type or field is a hard
failure, matching data/schema.py's stance that silent wrongness is the
failure mode this layer exists to prevent.

Strictness is cheap here because the input is a vendored snapshot: a new
field can only appear when someone re-runs scripts/fetch_ranks.py and is
already reading a diff, never spontaneously in production.
"""

from life4.life4.core import Life4RankEnum
from life4.life4.ranks.requirements import (
    CountRequirement,
    FolderRequirement,
    MAPointsRequirement,
    Requirement,
    TrialRequirement,
)
from life4.life4.ranks.wording import ClearType

#: Fields the songs parser understands. `id` is LIFE4's own key; we ignore it.
_SONG_FIELDS = frozenset(
    {
        "t",
        "id",
        "d",
        "higher_diff",
        "clear_type",
        "song_count",
        "score",
        "exceptions",
        "exception_score",
        "average_score",
    }
)


class GoalParseError(Exception):
    """A goal in the snapshot does not match any shape this app understands."""


def _clear_type(goal: dict) -> ClearType | None:
    raw = goal.get("clear_type")
    if raw is None:
        return None
    try:
        return ClearType(raw)
    except ValueError:
        known = ", ".join(sorted(c.value for c in ClearType))
        raise GoalParseError(
            f"unknown clear_type {raw!r} in goal {goal!r}. Known types: {known}."
        ) from None


def _parse_songs(goal: dict) -> Requirement:
    unknown = set(goal) - _SONG_FIELDS
    if unknown:
        raise GoalParseError(
            f"unknown field(s) {sorted(unknown)} in goal {goal!r}. Add support "
            f"in life4/life4/ranks/parser.py rather than ignoring them."
        )

    clear_type = _clear_type(goal)
    exceptions = goal.get("exceptions", 0)
    exception_floor = goal.get("exception_score")

    # The presence of song_count is the whole family split: with it, "at least
    # N charts"; without it, "every chart in the folder".
    if "song_count" in goal:
        return CountRequirement(
            level=goal["d"],
            count=goal["song_count"],
            clear_type=clear_type,
            min_score=goal.get("score"),
            higher_diff=goal.get("higher_diff", False),
            exceptions=exceptions,
            exception_floor=exception_floor,
        )

    return FolderRequirement(
        level=goal["d"],
        clear_type=clear_type,
        min_score=goal.get("score"),
        average_score=goal.get("average_score"),
        exceptions=exceptions,
        exception_floor=exception_floor,
    )


def _parse_trial(goal: dict) -> Requirement:
    try:
        rank = Life4RankEnum[goal["rank"].capitalize()]
    except KeyError:
        raise GoalParseError(
            f"unknown trial rank {goal['rank']!r} in goal {goal!r}"
        ) from None
    return TrialRequirement(rank=rank, num=goal["count"])


def parse_goal(goal: dict) -> Requirement:
    kind = goal.get("t")
    if kind == "songs":
        return _parse_songs(goal)
    if kind == "ma_points":
        return MAPointsRequirement(points=goal["points"])
    if kind == "trial":
        return _parse_trial(goal)
    raise GoalParseError(
        f"unsupported goal type {kind!r} in {goal!r}. 'set' and 'calories' "
        f"goals appear only in Copper-Silver, which are out of scope because "
        f"they cannot be derived from a score sheet; supporting them needs an "
        f"unverifiable-requirement concept first."
    )
