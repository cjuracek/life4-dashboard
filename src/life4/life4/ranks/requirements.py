from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
    format_score,
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


UNPLAYED = "unplayed"
MUST_RAISE = "must raise"
EXCEPTION = "exception"
TO_IMPROVE = "to improve"

# Must-raise and to-improve never occur in the same report, so they share a
# slot. Exceptions get a table of their own and never meet the others.
_CATEGORY_ORDER = {UNPLAYED: 0, MUST_RAISE: 1, TO_IMPROVE: 1, EXCEPTION: 2}

CHECK = "✓"


def _sorted_for_display(rows: pd.DataFrame, category: pd.Series) -> pd.DataFrame:
    """Blockers grouped by category; within each, worst score first.

    Unplayed charts have no score and are looked up by name, so they sort
    alphabetically. Played charts sort lowest score first: every chart in a
    category is measured against the same threshold, so the lowest score is
    the biggest gap. Ties fall back to the title, case-insensitively,
    because a plain sort strands lowercase titles after every capitalised
    one.
    """
    keyed = rows.assign(
        _order=category.map(_CATEGORY_ORDER).to_numpy(),
        _song=rows["song"].str.casefold().to_numpy(),
    )
    # Unplayed scores are all NaN, so within that group only _song decides.
    return (
        keyed.sort_values(["_order", "score", "_song"], kind="stable")
        .drop(columns=["_order", "_song"])
        .reset_index(drop=True)
    )


def _score_gap(score: float, target: int) -> str:
    return CHECK if score >= target else f"+{target - score:,.0f}"


def _no_rows() -> pd.DataFrame:
    return pd.DataFrame(columns=["song", "score"])


@dataclass(frozen=True)
class BlockerReport:
    """Where each chart failing a requirement stands, and the text to show it.

    States facts only. Nothing here marks a chart as done or as the one to
    work on: when more charts sit above the shadow floor than there are
    exceptions, which ones the allowance forgives is the player's choice, and
    fewest points is not least effort.

    The rows come in two tables because the groups follow different rules.
    Every required chart (unplayed, must raise, to improve) has to change
    whatever the budget. The exceptions are a pool: under budget none of
    them has to change, and over budget the player picks which to raise.
    """

    required_rows: pd.DataFrame = field(default_factory=_no_rows)
    exception_rows: pd.DataFrame = field(default_factory=_no_rows)
    unplayed: int = 0
    must_raise: int = 0
    exceptions_used: int = 0
    exceptions_allowed: int = 0
    to_improve: int = 0
    # (mean of played charts, target), for Folder Average requirements.
    average: tuple[float | None, int] | None = None

    @property
    def empty(self) -> bool:
        return self.required_rows.empty and self.exception_rows.empty

    @property
    def over_budget(self) -> bool:
        return self.exceptions_used > self.exceptions_allowed

    def _required_parts(self) -> list[tuple[int, str]]:
        second = (
            (self.must_raise, f"{self.must_raise} must raise")
            if self.exceptions_allowed
            else (self.to_improve, f"{self.to_improve} to improve")
        )
        return [(self.unplayed, f"{self.unplayed} unplayed"), second]

    @staticmethod
    def _joined(parts: list[tuple[int, str]]) -> str:
        return " · ".join(text for count, text in parts if count)

    def label(self) -> str:
        parts = self._required_parts()
        if self.exceptions_allowed:
            parts.append(
                (
                    self.exceptions_used,
                    f"{self.exceptions_used}/{self.exceptions_allowed} exceptions",
                )
            )
        return self._joined(parts)

    def required_title(self) -> str:
        return f"Required — {self._joined(self._required_parts())}"

    def exceptions_title(self) -> str:
        title = (
            f"Exceptions — {self.exceptions_used} used / "
            f"{self.exceptions_allowed} allowed"
        )
        if self.over_budget:
            title += f" ({self.exceptions_used - self.exceptions_allowed} over)"
        return title

    def header_lines(self) -> list[str]:
        lines = []
        if self.average is not None:
            current, target = self.average
            current_str = "-" if current is None else f"{current:,.0f}"
            lines.append(f"Folder average: {current_str} / {target:,}")
        return lines


class Requirement(ABC):
    multiple_levels: bool
    pool: ChartPool = ChartPool.EARNED

    @abstractmethod
    def is_satisfied(self, data: "DDRDataset"):
        pass

    @abstractmethod
    def display_str(self, data: "DDRDataset") -> str:
        pass

    def blockers(self, data: "DDRDataset") -> BlockerReport:
        """Charts standing between this requirement and satisfaction.

        Empty for count-based requirements ("PFC 5 16s"), which have no
        denominator and therefore no specific chart to name.
        """
        return BlockerReport()


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
        or_higher: bool = False,
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
        self.or_higher = or_higher
        self.exceptions = exceptions
        self.exception_floor = exception_floor
        # A "d+" goal spans levels, so the UI groups it under "Other" rather
        # than beneath a single level heading.
        self.multiple_levels = or_higher

    def __str__(self):
        return count_phrase(
            level=self.level,
            count=self.count,
            clear_type=self.clear_type,
            min_score=self.min_score,
            or_higher=self.or_higher,
            exceptions=self.exceptions,
            exception_floor=self.exception_floor,
        )

    def _charts(self, data: "DDRDataset") -> pd.DataFrame:
        if self.or_higher:
            return data.get_levels_from(self.level, pool=self.pool)
        return data.get_level(self.level, pool=self.pool)

    def _qualifying(self, data: "DDRDataset") -> int:
        if self.clear_type is ClearType.SDP:
            # SDP is a predicate over perfect counts, not a lamp, so it cannot
            # go through the lamp comparison below.
            sdps = data.get_sdp_or_better(pool=self.pool)
            if self.or_higher:
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


class FolderRequirement(Requirement):
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

    def display_str(self, data: "DDRDataset") -> str:
        # Chart counts live in the blocker dialog, which knows about
        # exceptions. A short average names no chart, so no dialog opens for
        # it, and the checkbox text is the only place it can show.
        if self.average_score is None or self.is_satisfied(data):
            return str(self)
        mean = self._charts(data)["score"].mean()
        if mean >= self.average_score:
            return str(self)
        mean_str = "-" if pd.isna(mean) else f"{mean:,.0f}"
        return f"{self} (Avg {mean_str}/{self.average_score:,})"

    def _categories(self, failing: pd.DataFrame) -> pd.Series:
        scored = failing["score"].notna()
        category = pd.Series(UNPLAYED, index=failing.index, dtype=object)
        if not self.exceptions:
            category[scored] = TO_IMPROVE
            return category
        # An exception is excused from the clear type, so only score decides.
        qualifies = scored
        if self.exception_floor is not None:
            qualifies = scored & (failing["score"] >= self.exception_floor)
        category[qualifies] = EXCEPTION
        category[scored & ~qualifies] = MUST_RAISE
        return category

    def _gap_columns(self) -> list[str]:
        columns = []
        if self.exceptions and self.exception_floor is not None:
            columns.append(f"to {format_score(self.exception_floor)}")
        if self.min_score is not None:
            columns.append(f"to {format_score(self.min_score)}")
        if self.clear_type is not None:
            columns.append("lamp")
        return columns

    def _gap_cells(self, row: pd.Series) -> list[str]:
        cells = []
        if self.exceptions and self.exception_floor is not None:
            cells.append(_score_gap(row["score"], self.exception_floor))
        if self.min_score is not None:
            cells.append(_score_gap(row["score"], self.min_score))
        if self.clear_type is not None:
            required = LAMP_FOR_CLEAR_TYPE[self.clear_type]
            if row["lamp"] >= required:
                cells.append(CHECK)
            else:
                have = LAMP_LABELS[Lamp(row["lamp"])]
                cells.append(f"{have} → {LAMP_LABELS[required]}")
        return cells

    def blockers(self, data: "DDRDataset") -> BlockerReport:
        charts = self._charts(data).copy()
        charts["song"] = _song_labels(charts)
        failing = self._failing(charts)
        category = self._categories(failing)

        columns = self._gap_columns()
        unplayed_cells = [UNPLAYED] + [""] * (len(columns) - 1) if columns else []
        cells = [
            unplayed_cells if cat == UNPLAYED else self._gap_cells(row)
            for (_, row), cat in zip(failing.iterrows(), category)
        ]
        rows = failing[["song", "score"]].copy()
        for i, name in enumerate(columns):
            rows[name] = [chart_cells[i] for chart_cells in cells]

        average = None
        if self.average_score is not None:
            mean = charts["score"].mean()
            average = (None if pd.isna(mean) else float(mean), self.average_score)

        is_exception = (category == EXCEPTION).to_numpy()
        exception_rows = rows[is_exception]
        if self.exceptions and self.exception_floor is not None:
            # Every exception clears the floor, so its column is all ticks.
            exception_rows = exception_rows.drop(
                columns=f"to {format_score(self.exception_floor)}"
            )

        counts = category.value_counts()
        return BlockerReport(
            required_rows=_sorted_for_display(
                rows[~is_exception], category[~is_exception]
            ),
            exception_rows=_sorted_for_display(exception_rows, category[is_exception]),
            unplayed=int(counts.get(UNPLAYED, 0)),
            must_raise=int(counts.get(MUST_RAISE, 0)),
            exceptions_used=int(counts.get(EXCEPTION, 0)),
            exceptions_allowed=self.exceptions,
            to_improve=int(counts.get(TO_IMPROVE, 0)),
            average=average,
        )
