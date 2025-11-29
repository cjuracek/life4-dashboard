from enum import IntEnum
from typing import List

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
    10: 1,
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
    Topaz = 8
    Amethyst = 9
    Emerald = 10
    Onyx = 11


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
