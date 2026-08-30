from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

import pandas as pd

from life4.data.availability import ChartPool
from life4.ddr import LAMP_LABELS, Lamp
from life4.life4.core import Life4RankEnum

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
        return out.sort_values("score", na_position="first").reset_index(drop=True)


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
        return out.sort_values("score", na_position="first").reset_index(drop=True)

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
        return deduped.sort_values("score", na_position="first").reset_index(drop=True)

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
