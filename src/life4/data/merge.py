import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from life4.data.schema import CANONICAL_COLUMNS

logger = logging.getLogger(__name__)

KEY_COLUMNS = ["title", "diff"]


@dataclass(frozen=True)
class MergeResult:
    """Merged chart history, plus any secondary rows that failed to join.

    WORLD is a strict superset of CTF by construction, so a non-empty
    ``orphans`` is always a defect -- a drifted title or a removed song. It
    means A3 scores have silently stopped counting, so the app surfaces it
    rather than only logging it.
    """

    charts: pd.DataFrame
    orphans: pd.DataFrame


#: Tied to `score` -- a PFC's score is a deterministic function of its perfect
#: count, so this must come from whichever row holds the max score. Taking it
#: independently could manufacture an SDP that never happened.
SCORE_BOUND_COLUMNS = ("perfect",)

#: Unioning these yields max(lamp) for free: _get_lamp tests pfc -> gfc -> fc
#: -> life4 in descending order, so a lamp earned on either cabinet surfaces.
DATE_COLUMNS = ("record_on", "pfc_date", "gfc_date", "fc_date", "life4_date")

#: Taken from the primary source, which defines the chart pool.
PRIMARY_COLUMNS = ("title", "diff", "level", "availability")


def _raise_on_duplicate_keys(frame: pd.DataFrame, label: str) -> None:
    """Raise loudly if ``frame`` has more than one row for any (title, diff).

    A duplicate key fans out silently across a merge -- one chart becomes two
    merged rows, with no warning, no log, no orphan. Both sides of the merge
    must fail the same way when this happens, so this is checked on primary
    and secondary alike before either merge runs.
    """
    dup_mask = frame.duplicated(subset=KEY_COLUMNS, keep=False)
    if not dup_mask.any():
        return
    dup_keys = (
        frame.loc[dup_mask, KEY_COLUMNS].drop_duplicates().apply(tuple, axis=1).tolist()
    )
    raise ValueError(
        f"{label} has duplicate (title, diff) rows, which would silently fan "
        f"out the merge: {dup_keys}"
    )


def merge_scores(primary: pd.DataFrame, secondary: pd.DataFrame) -> MergeResult:
    """Union two cabinets' histories into one row per chart.

    ``primary`` (WORLD) defines which charts exist, their level, and their
    availability. ``secondary`` (A3) contributes score and achievement history
    only, joined on (title, diff).

    Score is the max across sources; achievement dates are unioned; the
    judgment columns travel as a unit from whichever source holds the higher
    score.
    """
    _raise_on_duplicate_keys(primary, "primary")
    _raise_on_duplicate_keys(secondary, "secondary")

    matched = secondary.merge(
        primary[KEY_COLUMNS],
        on=KEY_COLUMNS,
        how="left",
        indicator=True,
        validate="many_to_one",
    )
    orphans = secondary[(matched["_merge"] == "left_only").to_numpy()]
    if len(orphans):
        logger.warning(
            "%d secondary charts have no primary match; their scores will not "
            "count. Usually a drifted title.",
            len(orphans),
        )

    m = primary.merge(
        secondary,
        on=KEY_COLUMNS,
        how="left",
        suffixes=("_p", "_s"),
        validate="one_to_one",
    )

    primary_score = m["score_p"]
    secondary_score = m["score_s"]
    take_secondary = secondary_score.notna() & (
        primary_score.isna() | (secondary_score > primary_score)
    )

    out = pd.DataFrame(index=m.index)
    for column in PRIMARY_COLUMNS:
        out[column] = m[column] if column in KEY_COLUMNS else m[f"{column}_p"]

    out["score"] = m[["score_p", "score_s"]].max(axis=1)

    for column in SCORE_BOUND_COLUMNS:
        out[column] = np.where(take_secondary, m[f"{column}_s"], m[f"{column}_p"])

    for column in DATE_COLUMNS:
        out[column] = m[f"{column}_p"].combine_first(m[f"{column}_s"])

    charts = out[list(CANONICAL_COLUMNS)].reset_index(drop=True)
    return MergeResult(charts=charts, orphans=orphans.reset_index(drop=True))
