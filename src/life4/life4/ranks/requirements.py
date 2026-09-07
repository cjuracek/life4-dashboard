from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

import pandas as pd

from life4.data.availability import ChartPool
from life4.ddr import LAMP_LABELS, Lamp
from life4.life4.core import Life4RankEnum
from life4.life4.ranks.wording import (
    LAMP_FOR_CLEAR_TYPE,
    ClearType,
    count_phrase,
    folder_phrase,
)

if TYPE_CHECKING:
    from life4.ddr import DDRDataset


def _song_labels(charts: pd.DataFrame) -> pd.Series:
    """Song titles, disambiguated by difficulty only where a title repeats.

    Within one level a title is almost always unique, so a difficulty column
    would be dead weight on ~99% of rows. Where a song does have two charts at
    the same level, each row carries its own difficulty: "Ace out (CSP)" and
    "Ace out (ESP)".
    """
    repeated = charts.groupby("title")["title"].transform("size") > 1
    return charts["title"].where(
        ~repeated, charts["title"] + " (" + charts["diff"] + ")"
    )


def _sorted_by_song(blockers: pd.DataFrame) -> pd.DataFrame:
    """Blockers in alphabetical order by song title, case-insensitively.

    Deliberately NOT ordered by score. The list is read to find a specific
    song, so alphabetical is what makes it scannable; a score ordering put
    unplayed charts first and then re-sorted the rest, which reads as the
    list changing its mind halfway down. Case-insensitive because a plain
    sort strands lowercase titles after every capitalised one.
    """
    return blockers.sort_values(
        "song", key=lambda song: song.str.casefold()
    ).reset_index(drop=True)


class Requirement(ABC):
    multiple_levels: bool
    pool: ChartPool = ChartPool.EARNED

    # Columns every blockers() frame returns, so the UI can render them uniformly.
    BLOCKER_COLUMNS = ("song", "score", "needs")

    @abstractmethod
    def is_satisfied(self, data: "DDRDataset"):
        pass

    @abstractmethod
    def display_str(self, data: "DDRDataset") -> str:
        pass

    def blockers(self, data: "DDRDataset") -> pd.DataFrame:
        """Charts standing between this requirement and satisfaction.

        Ordered alphabetically by song -- see _sorted_by_song for why not by
        score. Empty for count-based requirements ("PFC 5 16s"), which have no
        denominator and therefore no specific chart to name.

        Charts covered by a requirement's exception allowance are still listed:
        the frame is every chart below target, not the subset that is strictly
        blocking. Narrowing it means deciding which of the N below-floor charts
        the allowance forgives, which no requirement defines today.
        """
        return pd.DataFrame(columns=list(self.BLOCKER_COLUMNS))


class ProgressDisplay(Protocol):
    def get_progress(self) -> str: ...


class MAPointsRequirement(Requirement, ProgressDisplay):
    """E.g. 'MA Points: 4'"""

    multiple_levels = True

    def __init__(self, points: int):
        self.points_required = points

    def __str__(self):
        return f"MA Points: {self.points_required}"

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_ma_points(pool=self.pool) >= self.points_required

    def get_progress(self, data: "DDRDataset"):
        return f"{data.get_ma_points(pool=self.pool):.2f}/{self.points_required}"

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display


class TrialRequirement(Requirement):
    multiple_levels = True

    def __init__(self, rank: Life4RankEnum, num: int):
        self.rank = rank
        self.num = num

    def __str__(self):
        trial_str = "Trial" if self.num == 1 else "Trials"
        return f"Earn {self.rank.name} or above on {self.num} {trial_str}"

    def is_satisfied(self, data):
        valid_trials = [trial for trial in data.trials if trial.rank >= self.rank]
        return len(valid_trials) >= self.num

    def display_str(self, data: "DDRDataset") -> str:
        return str(self)


class CountRequirement(Requirement, ProgressDisplay):
    """At least N charts at a level (or above) satisfy a predicate.

    Absorbs what were PFCRequirement, AAARequirement, ClearRequirement,
    CeilingRequirement, MFC/SDPRequirement and MFC/SDPCountRequirement. "AAA"
    is not a concept in the LIFE4 API -- it is min_score=990_000. A "ceiling"
    is this class with count=1.

    Pool is EARNED: a chart removed from the game still credits the score you
    earned on it.
    """

    pool = ChartPool.EARNED

    def __init__(
        self,
        level: int,
        count: int,
        *,
        clear_type: ClearType | None = None,
        min_score: int | None = None,
        higher_diff: bool = False,
        exceptions: int = 0,
        exception_floor: int | None = None,
    ):
        if clear_type is not None and exceptions:
            raise ValueError(
                "clear_type and exceptions never co-occur in the LIFE4 data; "
                "refusing to guess how they interact"
            )
        self.level = level
        self.count = count
        self.clear_type = clear_type
        self.min_score = min_score
        self.higher_diff = higher_diff
        self.exceptions = exceptions
        self.exception_floor = exception_floor
        # A "d+" goal spans levels, so the UI groups it under "Other" rather
        # than beneath a single difficulty heading.
        self.multiple_levels = higher_diff

    def __str__(self):
        return count_phrase(
            level=self.level,
            count=self.count,
            clear_type=self.clear_type,
            min_score=self.min_score,
            higher_diff=self.higher_diff,
            exceptions=self.exceptions,
            exception_floor=self.exception_floor,
        )

    def _charts(self, data: "DDRDataset") -> pd.DataFrame:
        if self.higher_diff:
            return data.get_levels_from(self.level, pool=self.pool)
        return data.get_level(self.level, pool=self.pool)

    def _qualifying(self, data: "DDRDataset") -> int:
        if self.clear_type is ClearType.SDP:
            # SDP is a predicate over perfect counts, not a lamp, so it cannot
            # go through the lamp comparison below.
            sdps = data.get_sdp_or_better(pool=self.pool)
            if self.higher_diff:
                return int((sdps["level"] >= self.level).sum())
            return int((sdps["level"] == self.level).sum())

        charts = self._charts(data)
        if self.clear_type is not None:
            return int((charts["lamp"] >= LAMP_FOR_CLEAR_TYPE[self.clear_type]).sum())

        scores = charts["score"].dropna()
        if self.min_score is None:
            return len(scores)

        over = scores[scores >= self.min_score]
        if len(over) >= self.count or not self.exceptions:
            return len(over)

        slack = scores[(scores >= self.exception_floor) & (scores < self.min_score)]
        return len(over) + min(len(slack), self.exceptions)

    def is_satisfied(self, data: "DDRDataset") -> bool:
        return self._qualifying(data) >= self.count

    def get_progress(self, data: "DDRDataset") -> str:
        return f"{self._qualifying(data)}/{self.count}"

    def display_str(self, data: "DDRDataset") -> str:
        if self.is_satisfied(data):
            return str(self)
        return f"{self} ({self.get_progress(data)})"


class FolderRequirement(Requirement, ProgressDisplay):
    """Every chart at a level satisfies a predicate, minus exceptions.

    Absorbs LampRequirement, FloorRequirement and LampFloorRequirement, and
    adds the Folder Average case.

    Pool is REQUIRED: an optional chart must never appear here, or a chart you
    cannot play on demand blocks the requirement forever.

    Exception semantics are unified. An exception excuses a chart from the
    *whole* requirement -- lamp included -- provided it clears the shadow
    floor, rather than excusing only the score while holding the lamp
    absolute. The evidence is "PFC all 14s with a 999,500 Folder Average
    (4E, 996k)": a PFC scores exactly 1,000,000 - 10 x perfects, so a PFC
    below 996,000 needs more than 400 Perfects on one chart -- impossible
    under ~400 notes and vanishingly rare otherwise. Under a lamp-absolute
    reading that clause excuses something that cannot happen, i.e. it is dead
    syntax. A reading that renders LIFE4's own syntax inert is the wrong
    reading.
    """

    multiple_levels = False
    pool = ChartPool.REQUIRED

    def __init__(
        self,
        level: int,
        *,
        clear_type: ClearType | None = None,
        min_score: int | None = None,
        average_score: int | None = None,
        exceptions: int = 0,
        exception_floor: int | None = None,
    ):
        if (min_score is None) == (average_score is None):
            raise ValueError(
                "a folder requirement takes exactly one of min_score or average_score"
            )
        self.level = level
        self.clear_type = clear_type
        self.min_score = min_score
        self.average_score = average_score
        self.exceptions = exceptions
        self.exception_floor = exception_floor

    def __str__(self):
        return folder_phrase(
            level=self.level,
            clear_type=self.clear_type,
            min_score=self.min_score,
            average_score=self.average_score,
            exceptions=self.exceptions,
            exception_floor=self.exception_floor,
        )

    def _charts(self, data: "DDRDataset") -> pd.DataFrame:
        return data.get_level(self.level, pool=self.pool)

    def _lamp_ok(self, charts: pd.DataFrame) -> pd.Series:
        if self.clear_type is None:
            return pd.Series(True, index=charts.index)
        return charts["lamp"] >= LAMP_FOR_CLEAR_TYPE[self.clear_type]

    def _score_ok(self, charts: pd.DataFrame) -> pd.Series:
        if self.min_score is None:
            # An average requirement has no per-chart floor, but an unplayed
            # chart still fails.
            return charts["score"].notna()
        return charts["score"] >= self.min_score

    def _failing(self, charts: pd.DataFrame) -> pd.DataFrame:
        return charts[~(self._lamp_ok(charts) & self._score_ok(charts))]

    def is_satisfied(self, data: "DDRDataset") -> bool:
        charts = self._charts(data)
        if charts["score"].isna().any():
            return False

        failing = self._failing(charts)
        if len(failing) > self.exceptions:
            return False
        if self.exception_floor is not None and not failing.empty:
            if (failing["score"] < self.exception_floor).any():
                return False

        if self.average_score is not None:
            if charts["score"].mean() < self.average_score:
                return False
        return True

    def get_progress(self, data: "DDRDataset") -> str:
        charts = self._charts(data)
        total = len(charts)
        parts = []
        if self.clear_type is not None:
            passing = int(self._lamp_ok(charts).sum())
            if passing < total:
                parts.append(f"Lamp {passing}/{total}")
        if self.min_score is not None:
            passing = int(self._score_ok(charts).sum())
            if passing < total:
                parts.append(f"Floor {passing}/{total}")
        if self.average_score is not None:
            mean = charts["score"].mean()
            mean_str = "-" if pd.isna(mean) else f"{mean:,.0f}"
            parts.append(f"Avg {mean_str}/{self.average_score:,}")
        if not parts:
            return f"{total}/{total}"
        return "; ".join(parts)

    def display_str(self, data: "DDRDataset") -> str:
        if self.is_satisfied(data):
            return str(self)
        return f"{self} ({self.get_progress(data)})"

    def blockers(self, data: "DDRDataset") -> pd.DataFrame:
        charts = self._charts(data).copy()
        charts["song"] = _song_labels(charts)
        failing = self._failing(charts)

        needs = []
        for _, row in failing.iterrows():
            if pd.isna(row["score"]):
                needs.append("unplayed")
            elif self.min_score is not None and row["score"] < self.min_score:
                # The score gap is the actionable number, so it wins when a
                # chart fails both conditions.
                needs.append(f"+{self.min_score - row['score']:,.0f}")
            else:
                required = LAMP_FOR_CLEAR_TYPE[self.clear_type]
                have = LAMP_LABELS[Lamp(row["lamp"])]
                needs.append(f"{have} → {LAMP_LABELS[required]}")

        out = failing[["song", "score"]].copy()
        out["needs"] = needs
        return _sorted_by_song(out[list(self.BLOCKER_COLUMNS)])
