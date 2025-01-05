from abc import ABC, abstractmethod


from life4 import Life4RankEnum
from life4.ddr import Lamp


class Requirement(ABC):
    multiple_levels: bool

    @abstractmethod
    def is_satisfied(self, data: "DDRDataset"):
        pass


class LampRequirement(Requirement):
    """E.g. 'Red Lamp' (for a given difficulty)"""

    multiple_levels = False

    def __init__(self, level: int, lamp: "Lamp"):
        self.level = level
        self.lamp = lamp

    def __str__(self):
        return f"{self.lamp.name} Lamp"

    def is_satisfied(self, data: "DDRDataset"):
        lamp = data.get_level_lamp(level=self.level)
        return lamp >= self.lamp


class PFCRequirement(Requirement):
    """E.g. 'PFC 56 14s'"""

    multiple_levels = False

    def __init__(self, level: int, num: int):
        self.level = level
        self.num_pfc = num

    def __str__(self):
        return f"PFC {self.num_pfc} {self.level}s"

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_num_pfcs(self.level) >= self.num_pfc


class AAARequirement(Requirement):
    """E.g. 'AAA 132 14s'"""

    multiple_levels = False

    def __init__(self, level: int, num: int):
        self.level = level
        self.num_AAA = num

    def __str__(self):
        return f"AAA {self.num_AAA} {self.level}s"

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_num_AAA(level=self.level) >= self.num_AAA


class ClearRequirement(Requirement):
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
            req_str += f" over {str(self.floor)[:3]}k"
        if self.num_exceptions:
            req_str += f" ({self.num_exceptions}E, {str(self.exception_floor)[:3]}k)"
        return req_str

    def is_satisfied(self, data):
        level_scores = data.get_level_scores(level=self.level, return_zero=False)
        if not self.floor:
            return len(level_scores) >= self.num_required

        scores_over_floor = [score for score in level_scores if score >= self.floor]
        if len(scores_over_floor) >= self.num_required:
            return True

        exception_scores = [
            score
            for score in level_scores
            if self.exception_floor <= score < self.floor
        ]
        num_valid_exceptions = min(len(exception_scores), self.num_exceptions)
        total_valid_scores = len(scores_over_floor) + num_valid_exceptions
        return total_valid_scores >= self.num_required


class CeilingRequirement(Requirement):
    """E.g. '920k+ an 18'"""

    multiple_levels = False

    def __init__(self, level: int, ceiling: int):
        self.level = level
        self.ceiling = ceiling

    def __str__(self):
        return f"{str(self.ceiling)[:3]}k+ an {self.level}"

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_ceiling(level=self.level) >= self.ceiling


class FloorRequirement(Requirement):
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
        req_str = f"All {self.level}s over {str(self.floor)[:3]}k"
        if self.num_exceptions:
            req_str += f" ({self.num_exceptions}E, {str(self.exception_floor)[:3]}k)"
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


class MAPointsRequirement(Requirement):
    """E.g. 'MA Points: 4'"""

    multiple_levels = True

    def __init__(self, points: int):
        self.points_required = points

    def __str__(self):
        return f"MA Points: {self.points_required}"

    def is_satisfied(self, data: "DDRDataset"):
        return data.get_ma_points() >= self.points_required


class SDPRequirement(Requirement):
    """Requirement for getting a SDP at or above a given level"""

    multiple_levels = True

    def __init__(self, level: int):
        self.level = level

    def __str__(self):
        return f"SDP a {self.level}+"

    def is_satisfied(self, data: "DDRDataset"):
        return max(data.get_sdps()["Level"]) >= self.level


class MFCRequirement(Requirement):
    """Requirement for getting an MFC at or above a given level"""

    multiple_levels = True

    def __init__(self, level: int):
        self.level = level

    def __str__(self):
        return f"MFC a {self.level}+"

    def is_satisfied(self, data: "DDRDataset"):
        return max(data.get_lamp(Lamp.White)["Level"]) >= self.level


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
