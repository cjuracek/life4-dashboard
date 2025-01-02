from enum import IntEnum
from typing import List

import streamlit as st
from pydantic import BaseModel, Field, field_validator

MFC_POINT_MAPPING = {
    1: 0.1,
    2: 0.25,
    3: 0.25,
    4: 0.5,
    5: 0.5,
    6: 0.5,
    7: 1,
    8: 1,
    9: 1,
    10: 1.5,
    11: 2,
    12: 4,
    13: 6,
    14: 8,
    15: 15,
    16: 25,
}

# "An SDP is worth 1/10 points of an MFC"
SDP_POINT_MAPPING = {diff: points / 10 for diff, points in MFC_POINT_MAPPING.items()}


class Life4RankEnum(IntEnum):
    Copper = 0
    Bronze = 1
    Silver = 2
    Gold = 3
    Diamond = 4
    Platinum = 5
    Cobalt = 6
    Pearl = 7
    Amethyst = 8
    Emerald = 9
    Onyx = 10


class Life4Trial(BaseModel):
    name: str = Field(..., alias="Name")
    level: int = Field(..., gt=0, lt=20, alias="Level")
    rank: Life4RankEnum = Field(..., alias="Rank")

    @field_validator("rank", mode="before")
    def convert_rank(cls, v):
        if isinstance(v, str):
            try:
                return Life4RankEnum[v]
            except KeyError:
                raise ValueError(f"Invalid rank value: {v}")
        return v


class Life4Rank:
    def __init__(
        self,
        rank: Life4RankEnum,
        subrank: int,  # e.g. Pearl I, Pearl II
        requirements: List["Requirement"],
        substitutions: List["Requirement"],
    ):
        self.rank = rank
        self.subrank = subrank
        self.requirements = requirements
        self.substitutions = substitutions

    def __str__(self):
        return f"{self.rank.name} {self.subrank}"

    def _visualize_reqs(self, requirements: List["Requirement"], data):
        requirement_levels = range(14, 20)
        level_to_requirements = {
            level: [
                req
                for req in requirements
                if not req.multiple_levels and req.level == level
            ]
            for level in requirement_levels
        }
        for level, level_reqs in level_to_requirements.items():
            if not level_reqs:
                continue

            st.write(f"{level}s")
            _ = [level_req.create_checkbox(data) for level_req in level_reqs]

        st.write("Other")
        _ = [req.create_checkbox(data) for req in requirements if req.multiple_levels]

    def visualize(self, data: "DDRDataset"):
        """Visualize rank_requirements + substitutions as a series of Streamlit checkboxes in collapsible menu"""
        completed_requirements = len(
            [req for req in self.requirements if req.is_satisfied(data)]
        )
        total_requirements = len(self.requirements)
        available_substitutions = len(
            [sub for sub in self.substitutions if sub.is_satisfied(data)]
        )
        progress = f"{completed_requirements}/{total_requirements}"
        expander_title = f"**{self.rank.name} {self.subrank}**"

        status_emoji = (
            ":white_check_mark:"
            if completed_requirements + available_substitutions >= total_requirements
            else ":construction:"
        )
        expander_title += f" {status_emoji}"

        expander_title += f"\n\n  • {progress} requirements completed\n\n  • {available_substitutions} substitutions available"
        with st.expander(expander_title, expanded=False):
            st.write("Requirements")
            self._visualize_reqs(self.requirements, data)
            st.write("Substitutions")
            self._visualize_reqs(self.substitutions, data)
