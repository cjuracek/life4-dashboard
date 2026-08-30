from enum import IntEnum
from typing import TYPE_CHECKING

import pandas as pd

from life4.data.availability import ChartPool, classify, pool_classes
from life4.life4.core import MAPointsUnknownLevel, MFC_POINT_MAPPING, SDP_POINT_MAPPING

if TYPE_CHECKING:
    from life4.life4.core import Life4Trial


class Lamp(IntEnum):
    NO_LAMP = 0
    Clear = 1
    Red = 2
    Blue = 3
    Green = 4
    Gold = 5
    White = 6


#: How each lamp is written in the UI. LIFE4's own vocabulary, not enum names.
LAMP_LABELS = {
    Lamp.NO_LAMP: "Not played",
    Lamp.Clear: "Clear",
    Lamp.Red: "LIFE4 Clear",
    Lamp.Blue: "Full Combo",
    Lamp.Green: "Great Full Combo",
    Lamp.Gold: "Perfect Full Combo",
    Lamp.White: "Marvelous Full Combo",
}


class DDRDataset:
    """Chart history with lamps derived. Takes a prepared canonical frame.

    Loading, filtering, and merging happen upstream in life4.data so this
    class can be constructed from a handful of rows in a test.
    """

    def __init__(self, data: pd.DataFrame, trials: "list[Life4Trial] | None" = None):
        self._data = data.copy()
        self._data["lamp"] = self._data.apply(self._get_lamp, axis=1)
        self._data["availability_class"] = self._data["availability"].map(classify)
        self.trials = list(trials or [])

    def _get_lamp(self, row) -> Lamp:
        if row["score"] == 1_000_000:
            return Lamp.White
        missing = row.isna()
        if missing["record_on"]:
            return Lamp.NO_LAMP
        elif not missing["pfc_date"]:
            return Lamp.Gold
        elif not missing["gfc_date"]:
            return Lamp.Green
        elif not missing["fc_date"]:
            return Lamp.Blue
        elif not missing["life4_date"]:
            return Lamp.Red
        return Lamp.Clear

    def charts(self, pool: ChartPool = ChartPool.EARNED) -> pd.DataFrame:
        allowed = pool_classes(pool)
        return self._data[self._data["availability_class"].isin(allowed)]

    def get_level(self, level: int, *, pool: ChartPool = ChartPool.EARNED):
        charts = self.charts(pool)
        return charts[charts["level"] == level]

    def get_lamp(self, lamp: Lamp, *, pool: ChartPool = ChartPool.EARNED):
        charts = self.charts(pool)
        return charts[charts["lamp"] == lamp]

    def get_lamps_for_level(
        self, level: int, *, pool: ChartPool = ChartPool.EARNED
    ) -> list[Lamp]:
        # The "lamp" column is int64 internally (pandas coerces the IntEnum on
        # assignment in __init__), so this must convert back to Lamp on the
        # way out or the annotation is a lie.
        return [Lamp(lamp) for lamp in self.get_level(level, pool=pool)["lamp"]]

    def get_level_lamp(self, level: int, *, pool: ChartPool = ChartPool.EARNED) -> Lamp:
        lamps = self.get_lamps_for_level(level, pool=pool)
        return min(lamps) if lamps else Lamp.NO_LAMP

    def get_num_pfcs(self, level: int, *, pool: ChartPool = ChartPool.EARNED) -> int:
        return int((self.get_level(level, pool=pool)["lamp"] == Lamp.Gold).sum())

    def get_num_AAA(self, level: int, *, pool: ChartPool = ChartPool.EARNED) -> int:
        return int((self.get_level(level, pool=pool)["score"] >= 990_000).sum())

    def get_ceiling(self, level: int, *, pool: ChartPool = ChartPool.EARNED):
        return self.get_level(level, pool=pool)["score"].max()

    def get_songs_below_threshold(
        self, level: int, threshold: int, *, pool: ChartPool = ChartPool.EARNED
    ) -> pd.DataFrame:
        level_songs = self.get_level(level, pool=pool)
        return level_songs[level_songs["score"] < threshold]

    def get_songs_above_threshold(
        self, level: int, threshold: int, *, pool: ChartPool = ChartPool.EARNED
    ) -> pd.DataFrame:
        level_songs = self.get_level(level, pool=pool)
        return level_songs[level_songs["score"] >= threshold]

    def get_songs_in_range(
        self, level: int, lower: int, upper: int, *, pool: ChartPool = ChartPool.EARNED
    ) -> pd.DataFrame:
        level_songs = self.get_level(level, pool=pool)
        return level_songs[
            (level_songs["score"] >= lower) & (level_songs["score"] < upper)
        ]

    def get_sdps(self, *, pool: ChartPool = ChartPool.EARNED) -> pd.DataFrame:
        charts = self.charts(pool)
        return charts[(charts["lamp"] == Lamp.Gold) & (charts["perfect"] < 10)]

    def get_ma_points(self, *, pool: ChartPool = ChartPool.EARNED) -> float:
        sdp_levels = self.get_sdps(pool=pool)["level"]
        mfc_levels = self.get_lamp(Lamp.White, pool=pool)["level"]
        for level in (*sdp_levels, *mfc_levels):
            if level not in MFC_POINT_MAPPING:
                raise MAPointsUnknownLevel(
                    f"No MA point value defined for level {level}. "
                    f"MFC_POINT_MAPPING covers levels "
                    f"{min(MFC_POINT_MAPPING)}-{max(MFC_POINT_MAPPING)}; "
                    f"source the value from life4ddr.com and add it."
                )
        sdp_points = sum(SDP_POINT_MAPPING[level] for level in sdp_levels)
        mfc_points = sum(MFC_POINT_MAPPING[level] for level in mfc_levels)
        return sdp_points + mfc_points

    def get_level_scores(
        self, level: int, *, pool: ChartPool = ChartPool.EARNED
    ) -> pd.Series:
        """Scores for charts actually played at this level. Unplayed excluded."""
        return self.get_level(level, pool=pool)["score"].dropna()
