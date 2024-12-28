from life4 import Life4Rank, Life4RankEnum
from life4.ddr import Lamp
from life4.requirements import (
    AAARequirement,
    CeilingRequirement,
    ClearRequirement,
    FloorRequirement,
    LampRequirement,
    MAPointsRequirement,
    MFCRequirement,
    PFCRequirement,
    SDPRequirement,
    TrialRequirement,
)

pearl_substitutions = [
    # 14s
    LampRequirement(level=14, lamp=Lamp.Green),
    FloorRequirement(level=14, floor=995_000),
    # 15s
    LampRequirement(level=15, lamp=Lamp.Blue),
    FloorRequirement(
        level=15, floor=990_000, num_exceptions=5, exception_floor=975_000
    ),
    # 16s
    LampRequirement(level=16, lamp=Lamp.Red),
    FloorRequirement(
        level=16, floor=975_000, num_exceptions=10, exception_floor=950_000
    ),
    AAARequirement(level=16, num=80),
    # 17s
    PFCRequirement(level=17, num=1),
    # 18s
    AAARequirement(level=18, num=1),
    # 19s
    CeilingRequirement(level=19, ceiling=800_000),
    # Other
    MFCRequirement(level=8),
]

pearl_1 = Life4Rank(
    rank=Life4RankEnum.Pearl,
    subrank=1,
    requirements=[
        # 14s
        LampRequirement(level=14, lamp=Lamp.Red),
        FloorRequirement(
            level=14, floor=980_000, num_exceptions=9, exception_floor=955_000
        ),
        PFCRequirement(level=14, num=48),
        AAARequirement(level=14, num=116),
        # 15s
        LampRequirement(level=15, lamp=Lamp.Clear),
        FloorRequirement(
            level=15, floor=955_000, num_exceptions=14, exception_floor=910_000
        ),
        PFCRequirement(level=15, num=16),
        AAARequirement(level=15, num=60),
        # 16s
        LampRequirement(level=16, lamp=Lamp.Clear),
        FloorRequirement(
            level=16, floor=910_000, num_exceptions=19, exception_floor=860_000
        ),
        PFCRequirement(level=16, num=2),
        AAARequirement(level=16, num=24),
        # 17s
        ClearRequirement(
            level=17, num=44, floor=860_000, num_exceptions=12, exception_floor=810_000
        ),
        AAARequirement(level=17, num=2),
        # 18s
        ClearRequirement(level=18, num=14),
        CeilingRequirement(level=18, ceiling=910_000),
        # Other
        MAPointsRequirement(num=2),
        SDPRequirement(level=6),
        MFCRequirement(level=2),
        TrialRequirement(rank=Life4RankEnum.Cobalt, num=1),
    ],
    substitutions=pearl_substitutions,
)

pearl_2 = Life4Rank(
    rank=Life4RankEnum.Pearl,
    subrank=2,
    requirements=[
        # 14s
        LampRequirement(level=14, lamp=Lamp.Red),
        FloorRequirement(
            level=14, floor=982_000, num_exceptions=8, exception_floor=960_000
        ),
        PFCRequirement(level=14, num=56),
        AAARequirement(level=14, num=132),
        # 15s
        LampRequirement(level=15, lamp=Lamp.Clear),
        FloorRequirement(
            level=15, floor=960_000, num_exceptions=13, exception_floor=920_000
        ),
        PFCRequirement(level=15, num=22),
        AAARequirement(level=15, num=70),
        # 16s
        LampRequirement(level=16, lamp=Lamp.Clear),
        FloorRequirement(
            level=16, floor=920_000, num_exceptions=18, exception_floor=870_000
        ),
        PFCRequirement(level=16, num=4),
        AAARequirement(level=16, num=28),
        # 17s
        ClearRequirement(
            level=17, num=48, floor=870_000, num_exceptions=14, exception_floor=820_000
        ),
        AAARequirement(level=17, num=4),
        # 18s
        ClearRequirement(level=18, num=18),
        CeilingRequirement(level=18, ceiling=920_000),
        # Other
        MAPointsRequirement(num=4),
        SDPRequirement(level=7),
        MFCRequirement(level=3),
        TrialRequirement(rank=Life4RankEnum.Cobalt, num=1),
    ],
    substitutions=pearl_substitutions,
)

pearl_3 = Life4Rank(
    rank=Life4RankEnum.Pearl,
    subrank=3,
    requirements=[
        # 14s
        LampRequirement(level=14, lamp=Lamp.Red),
        FloorRequirement(
            level=14, floor=985_000, num_exceptions=7, exception_floor=965_000
        ),
        PFCRequirement(level=14, num=64),
        AAARequirement(level=14, num=110),
        # 15s
        LampRequirement(level=15, lamp=Lamp.Clear),
        FloorRequirement(
            level=15, floor=965_000, num_exceptions=12, exception_floor=930_000
        ),
        PFCRequirement(level=15, num=28),
        AAARequirement(level=15, num=80),
        # 16s
        LampRequirement(level=16, lamp=Lamp.Clear),
        FloorRequirement(
            level=16, floor=930_000, num_exceptions=17, exception_floor=880_000
        ),
        PFCRequirement(level=16, num=6),
        AAARequirement(level=16, num=32),
        # 17s
        ClearRequirement(
            level=17, num=52, floor=880_000, num_exceptions=16, exception_floor=830_000
        ),
        AAARequirement(level=17, num=6),
        # 18s
        ClearRequirement(level=18, num=22),
        CeilingRequirement(level=18, ceiling=930_000),
        # Other
        MAPointsRequirement(num=6),
        SDPRequirement(level=7),
        MFCRequirement(level=4),
        TrialRequirement(rank=Life4RankEnum.Cobalt, num=2),
    ],
    substitutions=pearl_substitutions,
)

pearl_4 = Life4Rank(
    rank=Life4RankEnum.Pearl,
    subrank=4,
    requirements=[
        # 14s
        LampRequirement(level=14, lamp=Lamp.Red),
        FloorRequirement(
            level=14, floor=987_000, num_exceptions=6, exception_floor=970_000
        ),
        PFCRequirement(level=14, num=72),
        AAARequirement(level=14, num=120),
        # 15s
        LampRequirement(level=15, lamp=Lamp.Clear),
        FloorRequirement(
            level=15, floor=970_000, num_exceptions=11, exception_floor=940_000
        ),
        PFCRequirement(level=15, num=34),
        AAARequirement(level=15, num=90),
        # 16s
        LampRequirement(level=16, lamp=Lamp.Clear),
        FloorRequirement(
            level=16, floor=940_000, num_exceptions=16, exception_floor=890_000
        ),
        PFCRequirement(level=16, num=8),
        AAARequirement(level=16, num=36),
        # 17s
        ClearRequirement(
            level=17, num=56, floor=890_000, num_exceptions=18, exception_floor=840_000
        ),
        AAARequirement(level=17, num=8),
        # 18s
        ClearRequirement(level=18, num=26),
        CeilingRequirement(level=18, ceiling=940_000),
        # Other
        MAPointsRequirement(num=8),
        SDPRequirement(level=8),
        MFCRequirement(level=5),
        TrialRequirement(rank=Life4RankEnum.Cobalt, num=2),
    ],
    substitutions=pearl_substitutions,
)

pearl_5 = Life4Rank(
    rank=Life4RankEnum.Pearl,
    subrank=5,
    requirements=[
        # 14s
        LampRequirement(level=14, lamp=Lamp.Blue),
        FloorRequirement(
            level=14, floor=990_000, num_exceptions=5, exception_floor=975_000
        ),
        PFCRequirement(level=14, num=80),
        # 15s
        LampRequirement(level=15, lamp=Lamp.Red),
        FloorRequirement(
            level=15, floor=975_000, num_exceptions=10, exception_floor=950_000
        ),
        PFCRequirement(level=15, num=40),
        AAARequirement(level=15, num=100),
        # 16s
        LampRequirement(level=16, lamp=Lamp.Clear),
        FloorRequirement(
            level=16, floor=950_000, num_exceptions=15, exception_floor=900_000
        ),
        PFCRequirement(level=16, num=10),
        AAARequirement(level=16, num=40),
        # 17s
        LampRequirement(level=17, lamp=Lamp.Clear),
        FloorRequirement(
            level=17, floor=900_000, num_exceptions=20, exception_floor=850_000
        ),
        AAARequirement(level=17, num=10),
        # 18s
        ClearRequirement(
            level=18, num=30, floor=800_000, num_exceptions=10, exception_floor=750_000
        ),
        CeilingRequirement(level=18, ceiling=950_000),
        # 19s
        CeilingRequirement(level=19, ceiling=700_000),
        # Other
        MAPointsRequirement(num=10),
        SDPRequirement(level=8),
        MFCRequirement(level=6),
        TrialRequirement(rank=Life4RankEnum.Pearl, num=1),
    ],
    substitutions=pearl_substitutions,
)
