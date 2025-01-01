from enum import IntEnum
import streamlit as st

import pandas as pd

from life4 import MFC_POINT_MAPPING, SDP_POINT_MAPPING, Life4Trial

def test1():
    st.write("Test 1 success (DDR)")

class Lamp(IntEnum):
    NO_LAMP = 0
    Clear = 1
    Red = 2
    Blue = 3
    Green = 4
    Gold = 5
    White = 6


class DDRDataset:
    def __init__(
        self,
        data_path,  # Local path or onedrive link
        filter_doubles=True,
        filter_course_trials=True,
        filter_other=True,
    ):
        print(f"Reading data from: {data_path}")
        self._data = pd.read_excel(data_path)
        if filter_doubles:
            singles_diff = ["bSP", "BSP", "DSP", "ESP", "CSP"]  # noqa: F841
            self._data = self._data.query("Diff in @singles_diff")

        if filter_course_trials:
            self._data = self._data.query("Availability != 'course trial'")

        if filter_other:
            self._data = self._data.query("Availability != 'Other'")

        # Add lamp information
        self._data["Lamp"] = self._data.apply(func=self._get_lamp, axis=1)

        # Add trials information
        trials_df = pd.read_excel(data_path, sheet_name="Trials")
        self.trials = [
            Life4Trial(**trial.to_dict()) for _, trial in trials_df.iterrows()
        ]

    def _get_lamp(self, row) -> Lamp:
        if row["Score"] == 1_000_000:
            return Lamp.White
        is_record_missing = row.isna()
        if is_record_missing["Record On"]:
            return Lamp.NO_LAMP
        elif not is_record_missing["PFC Date"]:
            return Lamp.Gold
        elif not is_record_missing["GFC Date"]:
            return Lamp.Green
        elif not is_record_missing["FC Date"]:
            return Lamp.Blue
        elif not is_record_missing["Life4 Date"]:
            return Lamp.Red
        else:
            return Lamp.Clear

    def get_lamp(self, lamp: Lamp):
        return self._data[self._data["Lamp"] == lamp]

    def get_level(self, level: int):
        return self._data.query("Level == @level")

    def get_level_lamp(self, level: int):
        lamps = self.get_level(level=level)["Lamp"]
        return min(lamps)

    def get_num_pfcs(self, level: int):
        diff_df = self.get_level(level)
        return len(diff_df[diff_df["Lamp"] == Lamp.Gold])

    def get_num_AAA(self, level: int):
        diff_df = self.get_level(level)
        return len(diff_df[diff_df["Score"] >= 990_000])

    def get_num_clears(self, level: int):
        lamps = self.get_level(level)["Lamp"]
        num_clears = sum(x >= Lamp.Clear for x in lamps)
        return num_clears

    def get_ceiling(self, level: int):
        return max(self.get_level(level)["Score"])

    def get_songs_below_threshold(self, level: int, threshold: int):
        level_songs = self.get_level(level)
        return level_songs[level_songs["Score"] < threshold]

    def get_sdps(self):
        sdps = self._data[(self._data["Lamp"] == Lamp.Gold) & (self._data["Perf"] < 10)]
        return sdps

    def get_ma_points(self):
        sdps = self.get_sdps()
        sdp_points = sum(SDP_POINT_MAPPING[level] for level in sdps["Level"])
        mfcs = self._data[self._data["Lamp"] == Lamp.White]
        mfc_points = sum(MFC_POINT_MAPPING[level] for level in mfcs["Level"])
        return sdp_points + mfc_points

    def get_level_scores(self, level: int, return_zero=True):
        level_scores = self.get_level(level)["Score"]
        return level_scores
