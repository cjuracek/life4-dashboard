from life4.ddr import Lamp
from life4.requirements import (
    CeilingRequirement,
    FloorRequirement,
    LampRequirement,
    MFCRequirement,
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
