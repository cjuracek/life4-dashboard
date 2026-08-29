import logging
from enum import IntEnum
from typing import TYPE_CHECKING

import pandas as pd

from life4.life4.core import MFC_POINT_MAPPING, SDP_POINT_MAPPING

if TYPE_CHECKING:
    from life4.life4.core import Life4Trial

logger = logging.getLogger(__name__)


class Lamp(IntEnum):
    NO_LAMP = 0
    Clear = 1
    Red = 2
    Blue = 3
    Green = 4
    Gold = 5
    White = 6


class DDRDataset:
    """Chart history with lamps derived. Takes a prepared canonical frame.

    Loading, filtering, and merging happen upstream in life4.data so this
    class can be constructed from a handful of rows in a test.
    """

    def __init__(self, data: pd.DataFrame, trials: "list[Life4Trial] | None" = None):
        self._data = data.copy()
        self._data["lamp"] = self._data.apply(self._get_lamp, axis=1)
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

    def get_level(self, level: int) -> pd.DataFrame:
        return self._data[self._data["level"] == level]

    def get_lamp(self, lamp: Lamp) -> pd.DataFrame:
        return self._data[self._data["lamp"] == lamp]

    def get_lamps_for_level(self, level: int) -> list[Lamp]:
        return self.get_level(level)["lamp"].to_list()

    def get_level_lamp(self, level: int) -> Lamp:
        lamps = self.get_lamps_for_level(level)
        return min(lamps) if lamps else Lamp.NO_LAMP

    def get_num_pfcs(self, level: int) -> int:
        return int((self.get_level(level)["lamp"] == Lamp.Gold).sum())

    def get_num_AAA(self, level: int) -> int:
        return int((self.get_level(level)["score"] >= 990_000).sum())

    def get_ceiling(self, level: int):
        return self.get_level(level)["score"].max()

    def get_songs_below_threshold(self, level: int, threshold: int) -> pd.DataFrame:
        level_songs = self.get_level(level)
        return level_songs[level_songs["score"] < threshold]

    def get_songs_above_threshold(self, level: int, threshold: int) -> pd.DataFrame:
        level_songs = self.get_level(level)
        return level_songs[level_songs["score"] >= threshold]

    def get_songs_in_range(self, level: int, lower: int, upper: int) -> pd.DataFrame:
        level_songs = self.get_level(level)
        return level_songs[
            (level_songs["score"] >= lower) & (level_songs["score"] < upper)
        ]

    def get_sdps(self) -> pd.DataFrame:
        return self._data[
            (self._data["lamp"] == Lamp.Gold) & (self._data["perfect"] < 10)
        ]

    def get_ma_points(self):
        sdps = self.get_sdps()
        sdp_points = sum(SDP_POINT_MAPPING[level] for level in sdps["Level"])
        mfcs = self._data[self._data["Lamp"] == Lamp.White]
        mfc_points = sum(MFC_POINT_MAPPING[level] for level in mfcs["Level"])
        return sdp_points + mfc_points

    def get_level_scores(self, level: int) -> pd.Series:
        """Scores for charts actually played at this level. Unplayed excluded."""
        return self.get_level(level)["score"].dropna()
