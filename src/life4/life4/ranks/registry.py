"""Loads the vendored LIFE4 snapshot into Life4Rank objects.

Only the in-scope tiers are parsed. The filter runs *before* validation on
purpose: Copper-Silver carry `calories` and `set` goals that the strict
parser rejects, and they are out of scope precisely because neither can be
derived from a score sheet.
"""

import json
from functools import cache
from importlib.resources import files

from life4.life4.core import Life4Rank, Life4RankEnum
from life4.life4.ranks.parser import parse_goal

#: Widening this is the only change needed to admit Gold-Diamond or Onyx-Ruby;
#: they share the in-scope structure and introduce no new goal shapes.
#: Copper-Silver do not -- see the module docstring.
IN_SCOPE = (
    Life4RankEnum.Pearl,
    Life4RankEnum.Topaz,
    Life4RankEnum.Amethyst,
    Life4RankEnum.Emerald,
)

_SNAPSHOT = files("life4.life4.ranks").joinpath("data/ranks.json")


@cache
def load_ranks() -> dict[Life4RankEnum, list[Life4Rank]]:
    payload = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    in_scope_names = {rank.name for rank in IN_SCOPE}

    ranks: dict[Life4RankEnum, list[Life4Rank]] = {tier: [] for tier in IN_SCOPE}
    for entry in payload:
        if entry["name"] not in in_scope_names:
            continue
        tier = Life4RankEnum[entry["name"]]
        requirements = entry["requirements"]
        ranks[tier].append(
            Life4Rank(
                rank=tier,
                subrank=entry["tier"],
                requirements=[parse_goal(goal) for goal in requirements["goals"]],
                substitutions=[
                    parse_goal(goal) for goal in requirements.get("substitutions") or []
                ],
            )
        )

    for subranks in ranks.values():
        subranks.sort(key=lambda rank: rank.subrank)
    return ranks
