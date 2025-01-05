from life4 import Life4Rank, Life4RankEnum
from life4.ddr import Lamp
from life4.requirements import (
    CeilingRequirement,
    ClearRequirement,
    FloorRequirement,
    LampRequirement,
    MFCRequirement,
    AAARequirement,
    MAPointsRequirement,
    SDPRequirement,
    TrialRequirement,
    PFCRequirement,
)

amethyst_substitutions = [
    # 15s
    LampRequirement(level=15, lamp=Lamp.Green),
    # 16s
    LampRequirement(level=16, lamp=Lamp.Blue),
    # 17s
    LampRequirement(level=17, lamp=Lamp.Red),
    # 18s
    FloorRequirement(
        level=18, floor=900_000, num_exceptions=15, exception_floor=850_000
    ),
    # 19s
    CeilingRequirement(level=19, ceiling=850_000),
    # Other
    MFCRequirement(level=11),
]

amethyst_1 = Life4Rank(
    rank=Life4RankEnum.Amethyst,
    subrank=1,
    requirements=[
        # 14s
        LampRequirement(level=14, lamp=Lamp.Blue),
        FloorRequirement(
            level=14, floor=991_000, num_exceptions=4, exception_floor=980_000
        ),
        PFCRequirement(level=14, num=88),
        # 15s
        LampRequirement(level=15, lamp=Lamp.Red),
        FloorRequirement(
            level=15, floor=980_000, num_exceptions=9, exception_floor=955_000
        ),
        PFCRequirement(level=15, num=48),
        AAARequirement(level=15, num=106),
        # 16s
        LampRequirement(level=16, lamp=Lamp.Clear),
        FloorRequirement(
            level=16, floor=955_000, num_exceptions=14, exception_floor=910_000
        ),
        PFCRequirement(level=16, num=14),
        AAARequirement(level=16, num=48),
        # 17s
        LampRequirement(level=17, lamp=Lamp.Clear),
        FloorRequirement(
            level=17, floor=910_000, num_exceptions=19, exception_floor=860_000
        ),
        AAARequirement(level=17, num=12),
        # 18s
        ClearRequirement(
            level=18, num=32, floor=810_000, num_exceptions=12, exception_floor=760_000
        ),
        CeilingRequirement(level=18, ceiling=960_000),
        # 19s
        CeilingRequirement(level=19, ceiling=720_000),
        # Other
        MAPointsRequirement(points=12),
        SDPRequirement(level=9),
        MFCRequirement(level=6),
        TrialRequirement(rank=Life4RankEnum.Pearl, num=1),
    ],
    substitutions=amethyst_substitutions,
)

amethyst_2 = Life4Rank(
    rank=Life4RankEnum.Amethyst,
    subrank=2,
    requirements=[
        # 14s
        LampRequirement(level=14, lamp=Lamp.Blue),
        FloorRequirement(
            level=14, floor=992_000, num_exceptions=3, exception_floor=982_000
        ),
        PFCRequirement(level=14, num=96),
        # 15s
        LampRequirement(level=15, lamp=Lamp.Red),
        FloorRequirement(
            level=15, floor=982_000, num_exceptions=8, exception_floor=960_000
        ),
        PFCRequirement(level=15, num=56),
        AAARequirement(level=15, num=112),
        # 16s
        LampRequirement(level=16, lamp=Lamp.Clear),
        FloorRequirement(
            level=16, floor=960_000, num_exceptions=13, exception_floor=920_000
        ),
        PFCRequirement(level=16, num=18),
        AAARequirement(level=16, num=56),
        # 17s
        LampRequirement(level=17, lamp=Lamp.Clear),
        FloorRequirement(
            level=17, floor=920_000, num_exceptions=18, exception_floor=870_000
        ),
        AAARequirement(level=17, num=14),
        # 18s
        ClearRequirement(
            level=18, num=34, floor=820_000, num_exceptions=14, exception_floor=770_000
        ),
        CeilingRequirement(level=18, ceiling=970_000),
        # 19s
        CeilingRequirement(level=19, ceiling=740_000),
        # Other
        MAPointsRequirement(points=14),
        SDPRequirement(level=9),
        MFCRequirement(level=7),
        TrialRequirement(rank=Life4RankEnum.Pearl, num=1),
    ],
    substitutions=amethyst_substitutions,
)
