"""Reconstructs LIFE4's exact requirement wording from the API's goal fields.

The API discards vocabulary the display has to put back: `score: 990000` is
rendered "AAA", `clear_type: "life4"` is "LIFE4 Clear", and `song_count: 1`
picks an article. Three reconstruction rules, three places to be quietly
wrong.

Every rule here is verified against LIFE4's own rendered output by
tests/test_conformance.py, which checks all 583 in-scope goals. Change nothing
in this module without re-running it -- and if it fails, fix this module, not
the fixture.
"""

from enum import Enum

from life4.ddr import Lamp


class ClearType(str, Enum):
    """The API's `clear_type` vocabulary.

    SDP is in here because the API puts it here, but it is not a lamp -- it is
    a predicate over perfect counts. It never appears on a folder goal.
    """

    GOOD = "good"
    LIFE4 = "life4"
    GREAT = "great"
    PERFECT = "perfect"
    MARVELOUS = "marvelous"
    SDP = "sdp"


#: How LIFE4 writes each clear type in a requirement line. Deliberately not
#: ddr.LAMP_LABELS: that names lamps for the blocker table ("Perfect Full
#: Combo"), whereas requirement lines abbreviate PFC and MFC while spelling
#: "Full Combo" and "Great Full Combo" out in full.
CLEAR_TYPE_LABELS = {
    ClearType.GOOD: "Full Combo",
    ClearType.LIFE4: "LIFE4 Clear",
    ClearType.GREAT: "Great Full Combo",
    ClearType.PERFECT: "PFC",
    ClearType.MARVELOUS: "MFC",
    ClearType.SDP: "SDP",
}

#: SDP is absent on purpose -- see ClearType. Callers must special-case it.
LAMP_FOR_CLEAR_TYPE = {
    ClearType.GOOD: Lamp.Blue,
    ClearType.LIFE4: Lamp.Red,
    ClearType.GREAT: Lamp.Green,
    ClearType.PERFECT: Lamp.Gold,
    ClearType.MARVELOUS: Lamp.White,
}

#: "AAA" is not a concept in the API. It is this number.
AAA_SCORE = 990_000

_LEVELS_TAKING_AN = {8, 11, 18}


def article(level: int) -> str:
    return "an" if level in _LEVELS_TAKING_AN else "a"


def format_score(value: int) -> str:
    if value % 1000 == 0:
        return f"{value // 1000}k"
    return f"{value:,}"


def exception_clause(exceptions: int, exception_floor: int | None) -> str:
    if not exceptions:
        return ""
    if exception_floor is None:
        return f" ({exceptions}E)"
    return f" ({exceptions}E, {format_score(exception_floor)})"


def count_phrase(
    *,
    level: int,
    count: int,
    clear_type: ClearType | None = None,
    min_score: int | None = None,
    higher_diff: bool = False,
    exceptions: int = 0,
    exception_floor: int | None = None,
) -> str:
    suffix = exception_clause(exceptions, exception_floor)

    # The "Clear N over X" template is selected by the presence of exceptions,
    # not by the count. Without them LIFE4 leads with the score: "750k+ 5 18s",
    # never "Clear 5 18s over 750k".
    if min_score is not None and clear_type is None and exceptions:
        return f"Clear {count} {level}s over {format_score(min_score)}{suffix}"

    if clear_type is not None:
        head = CLEAR_TYPE_LABELS[clear_type]
    elif min_score == AAA_SCORE:
        head = "AAA"
    elif min_score is not None:
        head = f"{format_score(min_score)}+"
    else:
        head = "Clear"

    plus = "+" if higher_diff else ""
    if count == 1:
        body = f"{article(level)} {level}{plus}"
    else:
        body = f"{count} {level}{plus}s"
    return f"{head} {body}{suffix}"


def folder_phrase(
    *,
    level: int,
    clear_type: ClearType | None = None,
    min_score: int | None = None,
    average_score: int | None = None,
    exceptions: int = 0,
    exception_floor: int | None = None,
) -> str:
    verb = CLEAR_TYPE_LABELS[clear_type] if clear_type is not None else "Clear"
    suffix = exception_clause(exceptions, exception_floor)
    if average_score is not None:
        return f"{verb} all {level}s with a {average_score:,} Folder Average{suffix}"
    return f"{verb} all {level}s over {format_score(min_score)}{suffix}"
