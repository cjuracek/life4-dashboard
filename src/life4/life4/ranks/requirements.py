import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import pandas as pd

from life4.data.availability import ChartPool
from life4.life4.core import Life4RankEnum
from life4.life4.ranks.wording import (
    CLEAR_TYPE_LABELS,
    LAMP_FOR_CLEAR_TYPE,
    ClearType,
    count_phrase,
    folder_phrase,
    format_score,
)

if TYPE_CHECKING:
    from life4.ddr import DDRDataset


_JAPANESE_SCRIPTS = (
    "CJK",
    "HIRAGANA",
    "KATAKANA",
    "HALFWIDTH KATAKANA",
    "IDEOGRAPHIC",
    "HANGUL",
)


def _has_japanese(text: str) -> bool:
    return any(unicodedata.name(c, "").startswith(_JAPANESE_SCRIPTS) for c in text)


def _romanized(title: str) -> str:
    """The romanized form of a title the sheet stores in two scripts.

    Titles in Japanese script or with stylised characters carry a trailing
    "(romanization, artist)": "ΩVERSOUL (OVERSOUL, BlackY)" shows as
    "OVERSOUL". The romanization can itself hold ", " ("*Hello, Planet.") and
    the artist can list names ("そらまふうらさか, RPG"), so the cut is the
    last ", " that leaves no Japanese before it. A few titles run the other
    way, "Wakusei lollipop (惑星☆ロリポップ, ...)", and keep what precedes the
    parentheses. A trailing group with no ", " is a subtitle and stays.
    """
    if not title.endswith(")"):
        return title
    depth = 0
    for start in range(len(title) - 1, -1, -1):
        depth += {")": 1, "(": -1}.get(title[start], 0)
        if depth == 0:
            break
    head, inner = title[:start].rstrip(), title[start + 1 : -1]

    cuts, depth = [], 0
    for i, char in enumerate(inner):
        depth += {"(": 1, ")": -1}.get(char, 0)
        if depth == 0 and inner.startswith(", ", i):
            cuts.append(i)
    if not head or not cuts:
        return title
    latin = [inner[:cut] for cut in cuts if not _has_japanese(inner[:cut])]
    return latin[-1] if latin else head


def _song_labels(charts: pd.DataFrame) -> pd.Series:
    """Romanized song titles, disambiguated by difficulty only where one repeats.

    Within one level a title is almost always unique, so a difficulty column
    would be dead weight on ~99% of rows. Where a song does have two charts at
    the same level, each row carries its own difficulty: "Ace out (CSP)" and
    "Ace out (ESP)". Repeats are found after romanizing, because the sheet
    spells a few songs both ways.
    """
    titles = charts["title"].map(_romanized)
    repeated = titles.groupby(titles).transform("size") > 1
    return titles.where(~repeated, titles + " (" + charts["diff"] + ")")


UNPLAYED = "unplayed"
MUST_RAISE = "must raise"
EXCEPTION = "exception"
TO_IMPROVE = "to improve"

CHECK = "✓"
CROSS = "✗"

# What an exception still needs before it stops using one up.
NEEDS_SCORE = "Needs score"
NEEDS_LAMP = "Needs lamp"
NEEDS_BOTH = "Needs both"

#: A LIFE4 ruling, not a DDR fact, so it lives here rather than in the lamp:
#: a FLARE VIII, IX or EX counts wherever a LIFE4 Clear is required. Full
#: combos already outrank the red lamp, so nothing else changes.
FLARE_FOR_LIFE4_CLEAR = 8
#: The list page's tooltip sits apart from the words it explains, so it names
#: them. The blocker dialog marks them in its title and footnotes the mark
#: directly beneath.
FLARE_NOTE = (
    f"Flare {FLARE_FOR_LIFE4_CLEAR}+ also counts as a "
    f"{CLEAR_TYPE_LABELS[ClearType.LIFE4]}"
)
FLARE_MARK = "*"
FLARE_FOOTNOTE = f"{FLARE_MARK} Flare {FLARE_FOR_LIFE4_CLEAR}+ also counts"


def _meets_clear_type(charts, clear_type: ClearType):
    """Whether each chart meets a lamp-based clear type.

    Takes a frame or a single row, so the requirement check and the blocker
    cell cannot disagree about what counts.
    """
    meets = charts["lamp"] >= LAMP_FOR_CLEAR_TYPE[clear_type]
    if clear_type is ClearType.LIFE4:
        meets = meets | (charts["flare"] >= FLARE_FOR_LIFE4_CLEAR)
    return meets


#: The blocker table's lamp column says only whether the chart has the lamp,
#: so it is named for the lamp rather than a distance to it ("to 987k"):
#: listing the chart's current lamp read "Clear" as if the target were met.
_LAMP_COLUMNS = {
    ClearType.LIFE4: "LIFE4 Clear",
    ClearType.GOOD: "FC",
    ClearType.GREAT: "GFC",
    ClearType.PERFECT: "PFC",
    ClearType.MARVELOUS: "MFC",
}


def _sorted_for_display(rows: pd.DataFrame) -> pd.DataFrame:
    """One section's blockers, worst score first.

    Every chart in a section is measured against the same threshold, so the
    lowest score is the biggest gap. Ties fall back to the title,
    case-insensitively, because a plain sort strands lowercase titles after
    every capitalised one. Unplayed scores are all NaN, so that section
    sorts by title alone: those charts are looked up by name.
    """
    keyed = rows.assign(_song=rows["song"].str.casefold().to_numpy())
    return (
        keyed.sort_values(["score", "_song"], kind="stable")
        .drop(columns="_song")
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

    The rows come in three sections because the groups follow different
    rules. Unplayed charts all have to be played, and a title is all there
    is to say about them. Required charts (must raise, to improve) all have
    to change, each by its own gap. The exceptions are a pool: under budget
    none of them has to change, and over budget the player picks which to
    raise.
    """

    unplayed_rows: pd.DataFrame = field(default_factory=_no_rows)
    required_rows: pd.DataFrame = field(default_factory=_no_rows)
    exception_rows: pd.DataFrame = field(default_factory=_no_rows)
    unplayed: int = 0
    must_raise: int = 0
    exceptions_used: int = 0
    exceptions_allowed: int = 0
    to_improve: int = 0
    # (mean of played charts, target), for Folder Average requirements.
    average: tuple[float | None, int] | None = None
    # Whether a flare can stand in for the lamp, which the header footnotes.
    flare_counts: bool = False
    # The exceptions split by what each still needs, for the dialog's filter.
    # Empty groups are left out.
    exception_groups: dict[str, pd.DataFrame] = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        return (
            self.unplayed_rows.empty
            and self.required_rows.empty
            and self.exception_rows.empty
        )

    @property
    def over_budget(self) -> bool:
        return self.exceptions_used > self.exceptions_allowed

    def _played_part(self) -> tuple[int, str]:
        if self.exceptions_allowed:
            return (self.must_raise, f"{self.must_raise} must raise")
        return (self.to_improve, f"{self.to_improve} to improve")

    @staticmethod
    def _joined(parts: list[tuple[int, str]]) -> str:
        return " · ".join(text for count, text in parts if count)

    def label(self) -> str:
        parts = [(self.unplayed, f"{self.unplayed} unplayed"), self._played_part()]
        if self.exceptions_allowed:
            parts.append(
                (
                    self.exceptions_used,
                    f"{self.exceptions_used}/{self.exceptions_allowed} exceptions",
                )
            )
        return self._joined(parts)

    def unplayed_title(self) -> str:
        noun = "chart" if self.unplayed == 1 else "charts"
        return f"Unplayed — {self.unplayed} {noun}"

    def required_title(self) -> str:
        return f"Required — {self._joined([self._played_part()])}"

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
        if self.flare_counts:
            lines.append(FLARE_FOOTNOTE)
        return lines


class Requirement(ABC):
    multiple_levels: bool
    pool: ChartPool = ChartPool.EARNED
    clear_type: ClearType | None = None

    @property
    def flare_counts(self) -> bool:
        return self.clear_type is ClearType.LIFE4

    @abstractmethod
    def is_satisfied(self, data: "DDRDataset"):
        pass

    @abstractmethod
    def display_str(self, data: "DDRDataset") -> str:
        pass

    def blocker_title(self, data: "DDRDataset") -> str:
        """The label, marked after "LIFE4 Clear" for the dialog's footnote."""
        text = self.display_str(data)
        if not self.flare_counts:
            return text
        label = CLEAR_TYPE_LABELS[ClearType.LIFE4]
        return text.replace(label, label + FLARE_MARK, 1)

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
            return int(_meets_clear_type(charts, self.clear_type).sum())

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
        text = str(self)
        if self.is_satisfied(data):
            return text
        return f"{text} ({self.get_progress(data)})"


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
        return _meets_clear_type(charts, self.clear_type)

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
        text = str(self)
        if self.average_score is None or self.is_satisfied(data):
            return text
        mean = self._charts(data)["score"].mean()
        if mean >= self.average_score:
            return text
        mean_str = "-" if pd.isna(mean) else f"{mean:,.0f}"
        return f"{text} (Avg {mean_str}/{self.average_score:,})"

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
            columns.append(_LAMP_COLUMNS[self.clear_type])
        return columns

    def _gap_cells(self, row: pd.Series) -> list[str]:
        cells = []
        if self.exceptions and self.exception_floor is not None:
            cells.append(_score_gap(row["score"], self.exception_floor))
        if self.min_score is not None:
            cells.append(_score_gap(row["score"], self.min_score))
        if self.clear_type is not None:
            met = _meets_clear_type(row, self.clear_type)
            cells.append(CHECK if met else CROSS)
        return cells

    def _exception_groups(
        self, rows: pd.DataFrame, charts: pd.DataFrame
    ) -> dict[str, pd.DataFrame]:
        """Exceptions by what they still need.

        A chart stops using an exception only once it meets both the score
        and the lamp, so the groups do not overlap: a gauge clear frees every
        "Needs lamp" chart and none of the "Needs both". Each group drops the
        columns its name already answers, as the exceptions table drops the
        floor column: every row in a group shares its lamp, and every "Needs
        lamp" row meets the score.
        """
        score = ~self._score_ok(charts).to_numpy()
        lamp = ~self._lamp_ok(charts).to_numpy()
        lamp_column = _LAMP_COLUMNS.get(self.clear_type)
        score_column = None
        if self.min_score is not None:
            score_column = f"to {format_score(self.min_score)}"
        groups = {
            NEEDS_SCORE: (score & ~lamp, {lamp_column}),
            NEEDS_LAMP: (lamp & ~score, {lamp_column, score_column}),
            NEEDS_BOTH: (score & lamp, {lamp_column}),
        }
        return {
            name: _sorted_for_display(
                rows[mask].drop(columns=[c for c in rows.columns if c in answered])
            )
            for name, (mask, answered) in groups.items()
            if mask.any()
        }

    def blockers(self, data: "DDRDataset") -> BlockerReport:
        charts = self._charts(data).copy()
        charts["song"] = _song_labels(charts)
        failing = self._failing(charts)
        category = self._categories(failing)

        is_unplayed = (category == UNPLAYED).to_numpy()
        unplayed_rows = _sorted_for_display(failing.loc[is_unplayed, ["song", "score"]])
        played, category = failing[~is_unplayed], category[~is_unplayed]

        cells = [self._gap_cells(row) for _, row in played.iterrows()]
        rows = played[["song", "score"]].copy()
        for i, name in enumerate(self._gap_columns()):
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
            unplayed_rows=unplayed_rows[["song"]],
            required_rows=_sorted_for_display(rows[~is_exception]),
            exception_rows=_sorted_for_display(exception_rows),
            unplayed=int(is_unplayed.sum()),
            must_raise=int(counts.get(MUST_RAISE, 0)),
            exceptions_used=int(counts.get(EXCEPTION, 0)),
            exceptions_allowed=self.exceptions,
            to_improve=int(counts.get(TO_IMPROVE, 0)),
            average=average,
            flare_counts=self.flare_counts,
            exception_groups=self._exception_groups(
                exception_rows, played[is_exception]
            ),
        )
