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


_LEVELS_TAKING_AN = {8, 11, 18}


def _article_for_level(level: int) -> str:
    return "an" if level in _LEVELS_TAKING_AN else "a"


def _format_score(score: int) -> str:
    if score is None:
        return ""
    if score % 1000 == 0:
        return f"{score // 1000}k"
    return f"{score:,}"


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

    #: Columns every blockers() frame returns, so the UI can render them uniformly.
    BLOCKER_COLUMNS = ("song", "score", "needs")

    @abstractmethod
    def is_satisfied(self, data: "DDRDataset"):
        pass

    @abstractmethod
    def display_str(self, data: "DDRDataset") -> str:
        pass

    def blockers(self, data: "DDRDataset") -> pd.DataFrame:
        """Charts preventing this requirement, worst first.

        Empty for count-based requirements ("PFC 5 16s"), which have no
        denominator and therefore no specific chart to name.
        """
        return pd.DataFrame(columns=list(self.BLOCKER_COLUMNS))


class ProgressDisplay(Protocol):
    def get_progress(self) -> str: ...


class LampRequirement(Requirement, ProgressDisplay):
    """E.g. 'Red Lamp' (for a given difficulty)"""

    multiple_levels = False
    pool = ChartPool.REQUIRED

    def __init__(self, level: int, lamp: Lamp):
        self.level = level
        self.lamp = lamp

    def __str__(self):
        return f"{self.lamp.name} Lamp"

    def get_progress(self, data: "DDRDataset"):
        lamps = data.get_lamps_for_level(self.level, pool=self.pool)
        valid_lamps = [lamp for lamp in lamps if lamp >= self.lamp]
        return f"{len(valid_lamps)}/{len(lamps)}"

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display

    def is_satisfied(self, data: "DDRDataset"):
        lamp = data.get_level_lamp(level=self.level, pool=self.pool)
        return lamp >= self.lamp

    def blockers(self, data: "DDRDataset") -> pd.DataFrame:
        charts = data.get_level(self.level, pool=self.pool).copy()
        charts["song"] = _song_labels(charts)
        below = charts[charts["lamp"] < self.lamp]
        out = below[["song", "score", "lamp"]].copy()
        out["needs"] = [
            f"{LAMP_LABELS[Lamp(lamp)]} → {LAMP_LABELS[self.lamp]}"
            for lamp in out["lamp"]
        ]
        out = out[list(self.BLOCKER_COLUMNS)]
        return _sorted_by_song(out)


class PFCRequirement(Requirement, ProgressDisplay):
    """E.g. 'PFC 56 14s'"""

    multiple_levels = False

    def __init__(self, level: int, num: int):
        self.level = level
        self.num_pfc = num

    def __str__(self):
        if self.num_pfc == 1:
            return f"PFC {_article_for_level(self.level)} {self.level}"
        return f"PFC {self.num_pfc} {self.level}s"

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_num_pfcs(self.level, pool=self.pool) >= self.num_pfc

    def get_progress(self, data: "DDRDataset"):
        return f"{data.get_num_pfcs(self.level, pool=self.pool)}/{self.num_pfc}"

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display


class AAARequirement(Requirement):
    """E.g. 'AAA 132 14s'"""

    multiple_levels = False

    def __init__(self, level: int, num: int):
        self.level = level
        self.num_AAA = num

    def __str__(self):
        if self.num_AAA == 1:
            return f"AAA {_article_for_level(self.level)} {self.level}"
        return f"AAA {self.num_AAA} {self.level}s"

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_num_AAA(level=self.level, pool=self.pool) >= self.num_AAA

    def get_progress(self, data: "DDRDataset"):
        return f"{data.get_num_AAA(level=self.level, pool=self.pool)}/{self.num_AAA}"

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display


class ClearRequirement(Requirement, ProgressDisplay):
    """E.g. 'Clear 18 18s' and 'Clear 44 17s over 860k (12E, 810k)'"""

    multiple_levels = False

    def __init__(
        self,
        level: int,
        num: int,
        floor: int = None,
        num_exceptions: int = 0,
        exception_floor: int = None,
    ):
        self.level = level
        self.num_required = num
        self.floor = floor
        self.num_exceptions = num_exceptions
        self.exception_floor = exception_floor

    def __str__(self):
        if self.num_required == 1:
            article = _article_for_level(self.level)
            req_str = f"Clear {article} {self.level}"
        else:
            req_str = f"Clear {self.num_required} {self.level}s"

        if self.floor:
            req_str += f" over {_format_score(self.floor)}"
        if self.num_exceptions:
            req_str += (
                f" ({self.num_exceptions}E, {_format_score(self.exception_floor)})"
            )
        return req_str

    def _get_valid_scores(self, data) -> int:
        level_scores = data.get_level_scores(level=self.level, pool=self.pool)
        if not self.floor:
            return len(level_scores)

        scores_over_floor = [score for score in level_scores if score >= self.floor]
        if len(scores_over_floor) >= self.num_required:
            return len(scores_over_floor)

        exception_scores = []
        if self.exception_floor is not None:
            exception_scores = [
                score
                for score in level_scores
                if self.exception_floor <= score < self.floor
            ]
        num_valid_exceptions = min(len(exception_scores), self.num_exceptions)
        total_valid_scores = len(scores_over_floor) + num_valid_exceptions
        return total_valid_scores

    def is_satisfied(self, data):
        return self._get_valid_scores(data) >= self.num_required

    def get_progress(self, data: "DDRDataset") -> str:
        return f"{self._get_valid_scores(data)}/{self.num_required}"

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display


class CeilingRequirement(Requirement):
    """E.g. '920k+ an 18'"""

    multiple_levels = False

    def __init__(self, level: int, ceiling: int):
        self.level = level
        self.ceiling = ceiling

    def __str__(self):
        article = _article_for_level(self.level)
        return f"{_format_score(self.ceiling)}+ {article} {self.level}"

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_ceiling(level=self.level, pool=self.pool) >= self.ceiling

    def display_str(self, data: "DDRDataset") -> str:
        return str(self)


class FloorRequirement(Requirement, ProgressDisplay):
    """E.g. 'All 16s over 920k'"""

    multiple_levels = False
    pool = ChartPool.REQUIRED

    def __init__(
        self,
        level: int,
        floor: int,
        num_exceptions: int = 0,
        exception_floor: int = None,
    ):
        self.level = level
        self.floor = floor
        self.num_exceptions = num_exceptions
        self.exception_floor = exception_floor

    def __str__(self):
        req_str = f"All {self.level}s over {_format_score(self.floor)}"
        if self.num_exceptions:
            req_str += (
                f" ({self.num_exceptions}E, {_format_score(self.exception_floor)})"
            )
        return req_str

    def is_satisfied(self, data: "DDRDataset"):
        charts = data.get_level(self.level, pool=self.pool)
        if charts["score"].isna().any():
            return False

        if self.exception_floor:
            if not data.get_songs_below_threshold(
                level=self.level, threshold=self.exception_floor, pool=self.pool
            ).empty:
                return False

        songs_below_threshold = data.get_songs_below_threshold(
            level=self.level, threshold=self.floor, pool=self.pool
        )
        return len(songs_below_threshold) <= self.num_exceptions

    def blockers(self, data: "DDRDataset") -> pd.DataFrame:
        charts = data.get_level(self.level, pool=self.pool).copy()
        charts["song"] = _song_labels(charts)
        below = charts[charts["score"].isna() | (charts["score"] < self.floor)]
        out = below[["song", "score"]].copy()
        out["needs"] = [
            "unplayed" if pd.isna(score) else f"+{self.floor - score:,.0f}"
            for score in out["score"]
        ]
        out = out[list(self.BLOCKER_COLUMNS)]
        return _sorted_by_song(out)

    def get_progress(self, data: "DDRDataset"):
        total_songs = len(data.get_level(self.level, pool=self.pool))
        songs_above_floor = len(
            data.get_songs_above_threshold(self.level, self.floor, pool=self.pool)
        )
        song_exceptions = data.get_songs_in_range(
            level=self.level,
            lower=self.exception_floor,
            upper=self.floor,
            pool=self.pool,
        )
        valid_exceptions = min(len(song_exceptions), self.num_exceptions)
        return f"{songs_above_floor + valid_exceptions}/{total_songs}"

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display


class LampFloorRequirement(Requirement, ProgressDisplay):
    """Combined lamp and floor requirement for a single level."""

    multiple_levels = False
    pool = ChartPool.REQUIRED

    def __init__(
        self,
        level: int,
        lamp: Lamp,
        floor: int,
        num_exceptions: int = 0,
        exception_floor: int = None,
    ):
        self.level = level
        self.lamp = lamp
        self.lamp_requirement = LampRequirement(level=level, lamp=lamp)
        self.floor_requirement = FloorRequirement(
            level=level,
            floor=floor,
            num_exceptions=num_exceptions,
            exception_floor=exception_floor,
        )

    def __str__(self):
        lamp_label = LAMP_LABELS.get(self.lamp, f"{self.lamp.name.title()} Lamp")
        floor_str = str(self.floor_requirement)
        if floor_str:
            floor_str = floor_str[0].lower() + floor_str[1:]
        return f"{lamp_label} {floor_str}".strip()

    def is_satisfied(self, data: "DDRDataset"):
        lamp_ok = self.lamp_requirement.is_satisfied(data)
        floor_ok = self.floor_requirement.is_satisfied(data)
        return lamp_ok and floor_ok

    def blockers(self, data: "DDRDataset") -> pd.DataFrame:
        combined = pd.concat(
            [
                self.lamp_requirement.blockers(data),
                self.floor_requirement.blockers(data),
            ],
            ignore_index=True,
        )
        deduped = combined.drop_duplicates(subset=["song"], keep="first")
        return _sorted_by_song(deduped)

    def get_progress(self, data: "DDRDataset") -> str:
        progress_parts = []
        if not self.lamp_requirement.is_satisfied(data):
            progress_parts.append(f"Lamp {self.lamp_requirement.get_progress(data)}")
        if not self.floor_requirement.is_satisfied(data):
            progress_parts.append(f"Floor {self.floor_requirement.get_progress(data)}")
        if not progress_parts:
            return self.floor_requirement.get_progress(data)
        return "; ".join(progress_parts)

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display


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


class SDPRequirement(Requirement):
    """Requirement for getting a SDP at or above a given level"""

    multiple_levels = True

    def __init__(self, level: int):
        self.level = level

    def __str__(self):
        return f"SDP a {self.level}+"

    def is_satisfied(self, data: "DDRDataset"):
        sdp_levels = data.get_sdps(pool=self.pool)["level"]
        if sdp_levels.empty:
            return False
        return max(sdp_levels) >= self.level

    def display_str(self, data: "DDRDataset") -> str:
        return str(self)


class SDPCountRequirement(Requirement, ProgressDisplay):
    """Requirement for earning multiple SDPs at or above a given level."""

    multiple_levels = True

    def __init__(self, level: int, num: int):
        self.level = level
        self.num = num

    def __str__(self):
        return f"SDP {self.num} {self.level}s+"

    def _count_sdps(self, data: "DDRDataset") -> int:
        sdps = data.get_sdps(pool=self.pool)
        return len(sdps[sdps["level"] >= self.level])

    def is_satisfied(self, data: "DDRDataset"):
        return self._count_sdps(data) >= self.num

    def get_progress(self, data: "DDRDataset") -> str:
        return f"{self._count_sdps(data)}/{self.num}"

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display


class MFCRequirement(Requirement):
    """Requirement for getting an MFC at or above a given level"""

    multiple_levels = True

    def __init__(self, level: int):
        self.level = level

    def __str__(self):
        article = _article_for_level(self.level)
        return f"MFC {article} {self.level}+"

    def is_satisfied(self, data: "DDRDataset"):
        mfc_levels = data.get_lamp(Lamp.White, pool=self.pool)["level"]
        if mfc_levels.empty:
            return False
        return max(mfc_levels) >= self.level

    def display_str(self, data: "DDRDataset") -> str:
        return str(self)


class MFCCountRequirement(Requirement, ProgressDisplay):
    """Requirement for earning multiple MFCs at or above a given level."""

    multiple_levels = True

    def __init__(self, level: int, num: int):
        self.level = level
        self.num = num

    def __str__(self):
        if self.num == 1:
            article = _article_for_level(self.level)
            return f"MFC {article} {self.level}+"
        return f"MFC {self.num} {self.level}s+"

    def _count_mfcs(self, data: "DDRDataset") -> int:
        mfcs = data.get_lamp(Lamp.White, pool=self.pool)
        return len(mfcs[mfcs["level"] >= self.level])

    def is_satisfied(self, data: "DDRDataset"):
        return self._count_mfcs(data) >= self.num

    def get_progress(self, data: "DDRDataset") -> str:
        return f"{self._count_mfcs(data)}/{self.num}"

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
