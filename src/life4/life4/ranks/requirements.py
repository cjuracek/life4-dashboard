from abc import ABC, abstractmethod
from typing import Protocol

from life4.ddr import Lamp
from life4.life4.core import Life4RankEnum


_LEVELS_TAKING_AN = {8, 11, 18}


def _article_for_level(level: int) -> str:
    return "an" if level in _LEVELS_TAKING_AN else "a"


def _format_score(score: int) -> str:
    if score is None:
        return ""
    if score % 1000 == 0:
        return f"{score // 1000}k"
    return f"{score:,}"


class Requirement(ABC):
    multiple_levels: bool

    @abstractmethod
    def is_satisfied(self, data: "DDRDataset"):
        pass

    @abstractmethod
    def display_str(self, data: "DDRDataset") -> str:
        pass


class ProgressDisplay(Protocol):
    def get_progress(self) -> str:
        ...


class LampRequirement(Requirement, ProgressDisplay):
    """E.g. 'Red Lamp' (for a given difficulty)"""

    multiple_levels = False

    def __init__(self, level: int, lamp: "Lamp"):
        self.level = level
        self.lamp = lamp

    def __str__(self):
        return f"{self.lamp.name} Lamp"

    def get_progress(self, data: "DDRDataset"):
        lamps = data.get_lamps_for_level(self.level)
        valid_lamps = [lamp for lamp in lamps if lamp >= self.lamp]
        return f"{len(valid_lamps)}/{len(lamps)}"

    def display_str(self, data: "DDRDataset") -> str:
        str_to_display = str(self)
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display

    def is_satisfied(self, data: "DDRDataset"):
        lamp = data.get_level_lamp(level=self.level)
        return lamp >= self.lamp


class PFCRequirement(Requirement, ProgressDisplay):
    """E.g. 'PFC 56 14s'"""

    multiple_levels = False

    def __init__(self, level: int, num: int):
        self.level = level
        self.num_pfc = num

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_num_pfcs(self.level) >= self.num_pfc

    def get_progress(self, data: "DDRDataset"):
        return f"{data.get_num_pfcs(self.level)}/{self.num_pfc}"

    def display_str(self, data: "DDRDataset") -> str:
        if self.num_pfc == 1:
            article = _article_for_level(self.level)
            str_to_display = f"PFC {article} {self.level}"
        else:
            str_to_display = f"PFC {self.num_pfc} {self.level}s"
        if not self.is_satisfied(data):
            str_to_display += f" ({self.get_progress(data)})"
        return str_to_display


class AAARequirement(Requirement):
    """E.g. 'AAA 132 14s'"""

    multiple_levels = False

    def __init__(self, level: int, num: int):
        self.level = level
        self.num_AAA = num

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_num_AAA(level=self.level) >= self.num_AAA

    def get_progress(self, data: "DDRDataset"):
        return f"{data.get_num_AAA(level=self.level)}/{self.num_AAA}"

    def display_str(self, data: "DDRDataset") -> str:
        if self.num_AAA == 1:
            article = _article_for_level(self.level)
            str_to_display = f"AAA {article} {self.level}"
        else:
            str_to_display = f"AAA {self.num_AAA} {self.level}s"
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
        req_str = f"Clear {self.num_required} {self.level}s"
        if self.floor:
            req_str += f" over {_format_score(self.floor)}"
        if self.num_exceptions:
            req_str += (
                f" ({self.num_exceptions}E, {_format_score(self.exception_floor)})"
            )
        return req_str

    def _get_valid_scores(self, data) -> int:
        level_scores = data.get_level_scores(level=self.level, return_zero=False)
        if not self.floor:
            return len(level_scores)

        scores_over_floor = [score for score in level_scores if score >= self.floor]
        if len(scores_over_floor) >= self.num_required:
            return len(scores_over_floor)

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
        return data.get_ceiling(level=self.level) >= self.ceiling

    def display_str(self, data: "DDRDataset") -> str:
        return str(self)


class FloorRequirement(Requirement, ProgressDisplay):
    """E.g. 'All 16s over 920k'"""

    multiple_levels = False

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
        if data.get_level_lamp(self.level) == Lamp.NO_LAMP:
            return False

        if self.exception_floor:
            if not data.get_songs_below_threshold(
                level=self.level, threshold=self.exception_floor
            ).empty:
                return False

        songs_below_threshold = data.get_songs_below_threshold(
            level=self.level, threshold=self.floor
        )
        return len(songs_below_threshold) <= self.num_exceptions

    def get_progress(self, data: "DDRDataset"):
        total_songs = len(data.get_level(self.level))
        songs_above_floor = len(data.get_songs_above_threshold(self.level, self.floor))
        song_exceptions = data.get_songs_in_range(
            level=self.level, lower=self.exception_floor, upper=self.floor
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

    def __init__(
        self,
        level: int,
        lamp: "Lamp",
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
        lamp_label_map = {
            Lamp.Clear: "Clear",
            Lamp.Red: "Life4 Clear",
            Lamp.Blue: "Full Combo",
            Lamp.Green: "Great Full Combo",
            Lamp.Gold: "Perfect Full Combo",
            Lamp.White: "Marvelous Full Combo",
        }
        lamp_label = lamp_label_map.get(self.lamp, f"{self.lamp.name.title()} Lamp")
        floor_str = str(self.floor_requirement)
        if floor_str:
            floor_str = floor_str[0].lower() + floor_str[1:]
        return f"{lamp_label} {floor_str}".strip()

    def is_satisfied(self, data: "DDRDataset"):
        lamp_ok = self.lamp_requirement.is_satisfied(data)
        floor_ok = self.floor_requirement.is_satisfied(data)
        return lamp_ok and floor_ok

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
        return data.get_ma_points() >= self.points_required

    def get_progress(self, data: "DDRDataset"):
        return f"{data.get_ma_points():.2f}/{self.points_required}"

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
        return max(data.get_sdps()["Level"]) >= self.level

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
        sdps = data.get_sdps()
        return len(sdps[sdps["Level"] >= self.level])

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
        return max(data.get_lamp(Lamp.White)["Level"]) >= self.level

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
        mfcs = data.get_lamp(Lamp.White)
        return len(mfcs[mfcs["Level"] >= self.level])

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
