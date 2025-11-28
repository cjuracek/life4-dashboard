from life4.ddr import Lamp
from life4.life4.core import Life4Rank, Life4RankEnum
from life4.life4.ranks.requirements import (
    AAARequirement,
    CeilingRequirement,
    ClearRequirement,
    FloorRequirement,
    LampFloorRequirement,
    LampRequirement,
    MAPointsRequirement,
    MFCCountRequirement,
    MFCRequirement,
    PFCRequirement,
    SDPCountRequirement,
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
        MAPointsRequirement(points=2),
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
        MAPointsRequirement(points=4),
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
        MAPointsRequirement(points=6),
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
        MAPointsRequirement(points=8),
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
        MAPointsRequirement(points=10),
        SDPRequirement(level=8),
        MFCRequirement(level=6),
        TrialRequirement(rank=Life4RankEnum.Pearl, num=1),
    ],
    substitutions=pearl_substitutions,
)

pearl = [pearl_1, pearl_2, pearl_3, pearl_4, pearl_5]


amethyst_1_substitutions = [
    # 14s
    LampFloorRequirement(
        level=14,
        lamp=Lamp.Green,
        floor=996_000,
        num_exceptions=9,
        exception_floor=991_000,
    ),
    PFCRequirement(level=14, num=105),
    # 15s
    PFCRequirement(level=15, num=56),
    # 16s
    LampFloorRequirement(
        level=16,
        lamp=Lamp.Red,
        floor=980_000,
        num_exceptions=10,
        exception_floor=955_000,
    ),
    PFCRequirement(level=16, num=24),
    AAARequirement(level=16, num=67),
    # 17s
    LampFloorRequirement(
        level=17,
        lamp=Lamp.Clear,
        floor=955_000,
        num_exceptions=14,
        exception_floor=910_000,
    ),
    PFCRequirement(level=17, num=1),
    AAARequirement(level=17, num=26),
    # 18s
    AAARequirement(level=18, num=2),
    # 19s
    CeilingRequirement(level=19, ceiling=700_000),
    # Other
    MFCRequirement(level=11),
    SDPRequirement(level=14),
]

amethyst_1 = Life4Rank(
    rank=Life4RankEnum.Amethyst,
    subrank=1,
    requirements=[
        # 14s
        LampFloorRequirement(
            level=14,
            lamp=Lamp.Blue,
            floor=991_000,
            num_exceptions=9,
            exception_floor=980_000,
        ),
        PFCRequirement(level=14, num=60),
        # 15s
        LampFloorRequirement(
            level=15,
            lamp=Lamp.Red,
            floor=980_000,
            num_exceptions=10,
            exception_floor=955_000,
        ),
        PFCRequirement(level=15, num=26),
        AAARequirement(level=15, num=105),
        # 16s
        LampFloorRequirement(
            level=16,
            lamp=Lamp.Clear,
            floor=955_000,
            num_exceptions=14,
            exception_floor=910_000,
        ),
        PFCRequirement(level=16, num=8),
        AAARequirement(level=16, num=44),
        # 17s
        LampFloorRequirement(
            level=17,
            lamp=Lamp.Clear,
            floor=910_000,
            num_exceptions=19,
            exception_floor=860_000,
        ),
        AAARequirement(level=17, num=12),
        # 18s
        ClearRequirement(
            level=18,
            num=22,
            floor=810_000,
            num_exceptions=6,
            exception_floor=760_000,
        ),
        CeilingRequirement(level=18, ceiling=960_000),
        # Other
        MFCRequirement(level=6),
        SDPRequirement(level=13),
        MAPointsRequirement(points=6),
        TrialRequirement(rank=Life4RankEnum.Topaz, num=1),
    ],
    substitutions=amethyst_1_substitutions,
)

amethyst_2_substitutions = [
    # 14s
    LampFloorRequirement(
        level=14,
        lamp=Lamp.Green,
        floor=997_000,
        num_exceptions=5,
        exception_floor=992_000,
    ),
    PFCRequirement(level=14, num=110),
    # 15s
    PFCRequirement(level=15, num=62),
    # 16s
    LampFloorRequirement(
        level=16,
        lamp=Lamp.Red,
        floor=982_000,
        num_exceptions=10,
        exception_floor=960_000,
    ),
    PFCRequirement(level=16, num=28),
    AAARequirement(level=16, num=74),
    # 17s
    LampFloorRequirement(
        level=17,
        lamp=Lamp.Clear,
        floor=960_000,
        num_exceptions=13,
        exception_floor=920_000,
    ),
    PFCRequirement(level=17, num=2),
    AAARequirement(level=17, num=32),
    # 18s
    AAARequirement(level=18, num=4),
    # 19s
    CeilingRequirement(level=19, ceiling=750_000),
    # Other
    MFCCountRequirement(level=11, num=3),
    SDPCountRequirement(level=14, num=2),
]

amethyst_3_substitutions = [
    # 14s
    LampFloorRequirement(
        level=14,
        lamp=Lamp.Green,
        floor=998_000,
        num_exceptions=5,
        exception_floor=993_000,
    ),
    PFCRequirement(level=14, num=115),
    # 15s
    PFCRequirement(level=15, num=68),
    # 16s
    LampFloorRequirement(
        level=16,
        lamp=Lamp.Red,
        floor=985_000,
        num_exceptions=10,
        exception_floor=965_000,
    ),
    PFCRequirement(level=16, num=32),
    AAARequirement(level=16, num=81),
    # 17s
    LampFloorRequirement(
        level=17,
        lamp=Lamp.Clear,
        floor=965_000,
        num_exceptions=12,
        exception_floor=930_000,
    ),
    PFCRequirement(level=17, num=3),
    AAARequirement(level=17, num=38),
    # 18s
    AAARequirement(level=18, num=6),
    # 19s
    CeilingRequirement(level=19, ceiling=800_000),
    # Other
    MFCRequirement(level=12),
    SDPCountRequirement(level=14, num=3),
]

amethyst_4_substitutions = [
    # 14s
    LampFloorRequirement(
        level=14,
        lamp=Lamp.Green,
        floor=998_500,
        num_exceptions=5,
        exception_floor=994_000,
    ),
    PFCRequirement(level=14, num=120),
    # 15s
    PFCRequirement(level=15, num=74),
    # 16s
    LampFloorRequirement(
        level=16,
        lamp=Lamp.Red,
        floor=987_000,
        num_exceptions=10,
        exception_floor=970_000,
    ),
    PFCRequirement(level=16, num=36),
    AAARequirement(level=16, num=88),
    # 17s
    LampFloorRequirement(
        level=17,
        lamp=Lamp.Clear,
        floor=970_000,
        num_exceptions=11,
        exception_floor=940_000,
    ),
    PFCRequirement(level=17, num=4),
    AAARequirement(level=17, num=44),
    # 18s
    AAARequirement(level=18, num=8),
    # 19s
    CeilingRequirement(level=19, ceiling=850_000),
    # Other
    MFCCountRequirement(level=12, num=2),
    SDPCountRequirement(level=14, num=4),
]

amethyst_5_substitutions = [
    # 14s
    LampFloorRequirement(
        level=14,
        lamp=Lamp.Green,
        floor=999_000,
        num_exceptions=5,
        exception_floor=995_000,
    ),
    PFCRequirement(level=14, num=125),
    # 15s
    PFCRequirement(level=15, num=80),
    # 16s
    LampFloorRequirement(
        level=16,
        lamp=Lamp.Red,
        floor=990_000,
        num_exceptions=10,
        exception_floor=975_000,
    ),
    PFCRequirement(level=16, num=40),
    # 17s
    LampFloorRequirement(
        level=17,
        lamp=Lamp.Clear,
        floor=975_000,
        num_exceptions=10,
        exception_floor=950_000,
    ),
    PFCRequirement(level=17, num=5),
    AAARequirement(level=17, num=50),
    # 18s
    AAARequirement(level=18, num=10),
    # 19s
    CeilingRequirement(level=19, ceiling=900_000),
    # Other
    MFCCountRequirement(level=12, num=5),
    SDPCountRequirement(level=14, num=5),
]

amethyst_2 = Life4Rank(
    rank=Life4RankEnum.Amethyst,
    subrank=2,
    requirements=[
        # 14s
        LampFloorRequirement(
            level=14,
            lamp=Lamp.Blue,
            floor=992_000,
            num_exceptions=8,
            exception_floor=982_000,
        ),
        PFCRequirement(level=14, num=70),
        # 15s
        LampFloorRequirement(
            level=15,
            lamp=Lamp.Red,
            floor=982_000,
            num_exceptions=10,
            exception_floor=960_000,
        ),
        PFCRequirement(level=15, num=32),
        AAARequirement(level=15, num=110),
        # 16s
        LampFloorRequirement(
            level=16,
            lamp=Lamp.Clear,
            floor=960_000,
            num_exceptions=13,
            exception_floor=920_000,
        ),
        PFCRequirement(level=16, num=11),
        AAARequirement(level=16, num=48),
        # 17s
        LampFloorRequirement(
            level=17,
            lamp=Lamp.Clear,
            floor=920_000,
            num_exceptions=18,
            exception_floor=870_000,
        ),
        AAARequirement(level=17, num=14),
        # 18s
        ClearRequirement(
            level=18,
            num=24,
            floor=820_000,
            num_exceptions=7,
            exception_floor=770_000,
        ),
        CeilingRequirement(level=18, ceiling=970_000),
        # Other
        MFCRequirement(level=7),
        SDPCountRequirement(level=13, num=2),
        MAPointsRequirement(points=7),
        TrialRequirement(rank=Life4RankEnum.Topaz, num=1),
    ],
    substitutions=amethyst_2_substitutions,
)

amethyst_3 = Life4Rank(
    rank=Life4RankEnum.Amethyst,
    subrank=3,
    requirements=[
        # 14s
        LampFloorRequirement(
            level=14,
            lamp=Lamp.Blue,
            floor=993_000,
            num_exceptions=7,
            exception_floor=985_000,
        ),
        PFCRequirement(level=14, num=80),
        # 15s
        LampFloorRequirement(
            level=15,
            lamp=Lamp.Red,
            floor=985_000,
            num_exceptions=10,
            exception_floor=965_000,
        ),
        PFCRequirement(level=15, num=38),
        AAARequirement(level=15, num=115),
        # 16s
        LampFloorRequirement(
            level=16,
            lamp=Lamp.Clear,
            floor=965_000,
            num_exceptions=12,
            exception_floor=930_000,
        ),
        PFCRequirement(level=16, num=14),
        AAARequirement(level=16, num=52),
        # 17s
        LampFloorRequirement(
            level=17,
            lamp=Lamp.Clear,
            floor=930_000,
            num_exceptions=17,
            exception_floor=880_000,
        ),
        AAARequirement(level=17, num=16),
        # 18s
        ClearRequirement(
            level=18,
            num=26,
            floor=830_000,
            num_exceptions=8,
            exception_floor=780_000,
        ),
        CeilingRequirement(level=18, ceiling=980_000),
        # Other
        MFCRequirement(level=8),
        SDPCountRequirement(level=13, num=3),
        MAPointsRequirement(points=8),
        TrialRequirement(rank=Life4RankEnum.Topaz, num=2),
    ],
    substitutions=amethyst_3_substitutions,
)

amethyst_4 = Life4Rank(
    rank=Life4RankEnum.Amethyst,
    subrank=4,
    requirements=[
        # 14s
        LampFloorRequirement(
            level=14,
            lamp=Lamp.Blue,
            floor=994_000,
            num_exceptions=6,
            exception_floor=987_000,
        ),
        PFCRequirement(level=14, num=90),
        # 15s
        LampFloorRequirement(
            level=15,
            lamp=Lamp.Red,
            floor=987_000,
            num_exceptions=10,
            exception_floor=970_000,
        ),
        PFCRequirement(level=15, num=44),
        AAARequirement(level=15, num=120),
        # 16s
        LampFloorRequirement(
            level=16,
            lamp=Lamp.Clear,
            floor=970_000,
            num_exceptions=11,
            exception_floor=940_000,
        ),
        PFCRequirement(level=16, num=17),
        AAARequirement(level=16, num=56),
        # 17s
        LampFloorRequirement(
            level=17,
            lamp=Lamp.Clear,
            floor=940_000,
            num_exceptions=16,
            exception_floor=890_000,
        ),
        AAARequirement(level=17, num=18),
        # 18s
        ClearRequirement(
            level=18,
            num=28,
            floor=840_000,
            num_exceptions=9,
            exception_floor=790_000,
        ),
        CeilingRequirement(level=18, ceiling=985_000),
        # Other
        MFCRequirement(level=9),
        SDPCountRequirement(level=13, num=4),
        MAPointsRequirement(points=9),
        TrialRequirement(rank=Life4RankEnum.Topaz, num=2),
    ],
    substitutions=amethyst_4_substitutions,
)

amethyst_5 = Life4Rank(
    rank=Life4RankEnum.Amethyst,
    subrank=5,
    requirements=[
        # 14s
        LampFloorRequirement(
            level=14,
            lamp=Lamp.Blue,
            floor=995_000,
            num_exceptions=5,
            exception_floor=990_000,
        ),
        PFCRequirement(level=14, num=100),
        # 15s
        LampFloorRequirement(
            level=15,
            lamp=Lamp.Red,
            floor=990_000,
            num_exceptions=10,
            exception_floor=975_000,
        ),
        PFCRequirement(level=15, num=50),
        # 16s
        LampFloorRequirement(
            level=16,
            lamp=Lamp.Clear,
            floor=975_000,
            num_exceptions=10,
            exception_floor=950_000,
        ),
        PFCRequirement(level=16, num=20),
        AAARequirement(level=16, num=60),
        # 17s
        LampFloorRequirement(
            level=17,
            lamp=Lamp.Clear,
            floor=950_000,
            num_exceptions=15,
            exception_floor=900_000,
        ),
        AAARequirement(level=17, num=20),
        # 18s
        ClearRequirement(
            level=18,
            num=30,
            floor=850_000,
            num_exceptions=10,
            exception_floor=800_000,
        ),
        AAARequirement(level=18, num=1),
        # Other
        MFCRequirement(level=10),
        SDPCountRequirement(level=13, num=5),
        MAPointsRequirement(points=10),
        TrialRequirement(rank=Life4RankEnum.Amethyst, num=1),
    ],
    substitutions=amethyst_5_substitutions,
)

amethyst = [amethyst_1, amethyst_2, amethyst_3, amethyst_4, amethyst_5]


emerald_1_substitutions = [
    # 14s
    FloorRequirement(
        level=14, floor=999_500, num_exceptions=4, exception_floor=996_000
    ),
    # 15s
    PFCRequirement(level=15, num=88),
    # 16s
    LampFloorRequirement(
        level=16,
        lamp=Lamp.Blue,
        floor=991_000,
        num_exceptions=9,
        exception_floor=980_000,
    ),
    PFCRequirement(level=16, num=44),
    # 17s
    LampFloorRequirement(
        level=17,
        lamp=Lamp.Red,
        floor=980_000,
        num_exceptions=10,
        exception_floor=955_000,
    ),
    PFCRequirement(level=17, num=8),
    AAARequirement(level=17, num=60),
    # 18s
    LampFloorRequirement(
        level=18,
        lamp=Lamp.Clear,
        floor=910_000,
        num_exceptions=19,
        exception_floor=860_000,
    ),
    AAARequirement(level=18, num=12),
    # 19s
    CeilingRequirement(level=19, ceiling=910_000),
    # Other
    MFCRequirement(level=13),
    SDPRequirement(level=15),
]

emerald_1 = Life4Rank(
    rank=Life4RankEnum.Emerald,
    subrank=1,
    requirements=[
        # 14s
        LampFloorRequirement(
            level=14,
            lamp=Lamp.Green,
            floor=996_000,
            num_exceptions=9,
            exception_floor=991_000,
        ),
        PFCRequirement(level=14, num=105),
        # 15s
        LampFloorRequirement(
            level=15,
            lamp=Lamp.Blue,
            floor=991_000,
            num_exceptions=9,
            exception_floor=980_000,
        ),
        PFCRequirement(level=15, num=56),
        # 16s
        LampFloorRequirement(
            level=16,
            lamp=Lamp.Red,
            floor=980_000,
            num_exceptions=10,
            exception_floor=955_000,
        ),
        PFCRequirement(level=16, num=24),
        AAARequirement(level=16, num=67),
        # 17s
        LampFloorRequirement(
            level=17,
            lamp=Lamp.Clear,
            floor=955_000,
            num_exceptions=14,
            exception_floor=910_000,
        ),
        PFCRequirement(level=17, num=1),
        AAARequirement(level=17, num=26),
        # 18s
        ClearRequirement(
            level=18, num=32, floor=860_000, num_exceptions=12, exception_floor=810_000
        ),
        AAARequirement(level=18, num=2),
        # 19s
        ClearRequirement(level=19, num=1),
        CeilingRequirement(level=19, ceiling=700_000),
        # Other
        MFCRequirement(level=11),
        SDPRequirement(level=14),
        MAPointsRequirement(points=12),
        TrialRequirement(rank=Life4RankEnum.Amethyst, num=1),
    ],
    substitutions=emerald_1_substitutions,
)

emerald = [emerald_1]
