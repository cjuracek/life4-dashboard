import io

import pandas as pd

from life4.data.errors import SchemaError, ValueDefectError

#: Re-exported so existing importers keep working; the class lives in errors.py
#: alongside its siblings.
__all__ = [
    "CANONICAL_COLUMNS",
    "COLUMN_ALIASES",
    "NUMERIC_COLUMNS",
    "SchemaError",
    "SINGLES_DIFFICULTIES",
    "normalize",
]

#: The only columns the app reads. Audited 2026-08-23 against ddr.py and
#: requirements.py; everything else in the sheet is ignored on purpose.
CANONICAL_COLUMNS = (
    "diff",
    "level",
    "title",
    "score",
    "perfect",
    "record_on",
    "pfc_date",
    "gfc_date",
    "fc_date",
    "life4_date",
    "availability",
)

#: One shared table, not per-tab schemas. The WORLD tab is live and will drift;
#: the CTF tab is dormant. Per-tab definitions would mean a WORLD rename
#: silently requires a matching CTF edit that nobody remembers to make. Here,
#: adding one alias fixes both tabs at once.
#:
#: Only `perfect` needs more than one alias today -- the other ten read columns
#: are already identically named in both tabs. Add aliases when a rename
#: actually happens; do not seed speculative variants.
COLUMN_ALIASES: dict[str, frozenset[str]] = {
    "diff": frozenset({"Diff"}),
    "level": frozenset({"Level"}),
    "title": frozenset({"Title"}),
    "score": frozenset({"Score"}),
    "perfect": frozenset({"P", "Perf"}),
    "record_on": frozenset({"Record On"}),
    "pfc_date": frozenset({"PFC Date"}),
    "gfc_date": frozenset({"GFC Date"}),
    "fc_date": frozenset({"FC Date"}),
    "life4_date": frozenset({"Life4 Date"}),
    "availability": frozenset({"Availability"}),
}


#: Coerced to numeric at load so every layer below can compare them without
#: re-checking dtypes. A blank cell becomes NaN, which is how "unplayed" is
#: represented throughout.
NUMERIC_COLUMNS = ("level", "score", "perfect")

#: The chart pool the app is about. Doubles rows are dropped here rather than
#: in app.py: the value checks below must judge only rows something downstream
#: reads, or an untended doubles cell stops an app that never looks at it.
SINGLES_DIFFICULTIES = ("bSP", "BSP", "DSP", "ESP", "CSP")

#: Difficulty ratings run 1-19. Anything outside that is a bad cell, not a
#: chart -- and a NaN level is worse than a wrong one, because it silently
#: drops the row out of every get_level() bucket instead of landing in the
#: wrong one.
LEVEL_RANGE = (1, 19)

MAX_SCORE = 1_000_000

#: How many offending rows an error message names before it summarises.
_MAX_REPORTED_ROWS = 5


def _blank(values: pd.Series) -> pd.Series:
    """True where a cell is empty -- missing, or whitespace only."""
    return values.isna() | values.astype(str).str.strip().eq("")


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _cell(value) -> str:
    """Repr a cell without numpy's wrapper, which is noise to a sheet owner."""
    return repr(value.item() if hasattr(value, "item") else value)


def _describe_rows(frame: pd.DataFrame, mask: pd.Series, columns) -> str:
    """Name the offending rows by their line in the sheet.

    The index is still the CSV row order at this point, so ``+ 2`` converts it
    to the line number the user sees in Google Sheets: one for the header, one
    because sheets are 1-based.
    """
    # dict.fromkeys de-duplicates while keeping order: a check on `title`
    # names ("diff", "title", "title"), and duplicate labels would make
    # .loc[label, name] return a Series instead of a cell.
    columns = list(dict.fromkeys(columns))
    offenders = frame.loc[mask, columns]
    lines = [
        "    row {}: {}".format(
            label + 2,
            ", ".join(
                f"{name}={_cell(offenders.loc[label, name])}" for name in columns
            ),
        )
        for label in offenders.index[:_MAX_REPORTED_ROWS]
    ]
    extra = int(mask.sum()) - _MAX_REPORTED_ROWS
    if extra > 0:
        lines.append(f"    ... and {extra} more")
    return "\n".join(lines)


def _filter_to_singles(frame: pd.DataFrame, tab_name: str) -> pd.DataFrame:
    """Keep singles charts; fail on a difficulty code that is neither.

    Filtering silently is how a typo disappears: ``ESp`` matches no singles
    code, gets dropped, and the level's denominator quietly shrinks by one --
    which makes "All 16s over 920k" satisfiable while a real 16 sits below the
    floor. Doubles are recognised by their ``DP`` suffix rather than an
    allow-list, so a slot this app has never seen still drops quietly; only a
    code that is neither singles nor doubles is treated as a defect.
    """
    diff = frame["diff"]
    codes = diff.astype(str).str.strip()
    blank = _blank(diff)
    singles = codes.isin(SINGLES_DIFFICULTIES)
    doubles = codes.str.endswith("DP")

    unknown = ~(blank | singles | doubles)
    if unknown.any():
        raise ValueDefectError(
            f"Tab {tab_name!r} has "
            + _plural(int(unknown.sum()), "row")
            + " whose difficulty is neither singles nor doubles, so they "
            "would be dropped silently:\n"
            + _describe_rows(frame, unknown, ("diff", "level", "title"))
            + f"\n  Singles codes: {', '.join(SINGLES_DIFFICULTIES)}; doubles end "
            f"in 'DP'.\n"
            f"  Fix: correct the Diff cell in the sheet."
        )

    return frame[singles]


def _raise_on_coercion_loss(frame: pd.DataFrame, tab_name: str) -> None:
    """Fail on a cell that held something and became NaN under coercion.

    This is the primary value check, and it is one rule rather than a table of
    per-column ranges because every way a number gets garbled -- a typo, a
    stray space, a date where a score belongs, a column read from the wrong
    place -- arrives as the same event.

    It also catches a failure no range rule can see. ``thousands=","`` is a
    per-column decision in read_csv: one unparseable cell anywhere in `score`
    leaves the whole column as strings, and every comma-formatted value in it
    then coerces to NaN. Nulls are legal in `score` (unplayed), so a rule that
    permits them cannot distinguish that from a blank sheet.
    """
    defects = []
    for column in NUMERIC_COLUMNS:
        values = frame[column]
        lost = ~_blank(values) & pd.to_numeric(values, errors="coerce").isna()
        if lost.any():
            defects.append(
                f"  {column!r}: "
                + _plural(int(lost.sum()), "value")
                + " that could not be parsed as a number\n"
                + _describe_rows(frame, lost, ("diff", "title", column))
            )

    if defects:
        raise ValueDefectError(
            f"Tab {tab_name!r} has cells that are not numbers in numeric "
            f"columns. They would become NaN, which is indistinguishable from "
            f"'unplayed':\n" + "\n".join(defects) + "\n"
            "  Fix: correct the cells in the sheet, or add the column's real "
            "name to COLUMN_ALIASES in life4/data/schema.py if this column is "
            "being read from the wrong place."
        )


def _raise_on_bad_values(frame: pd.DataFrame, tab_name: str) -> None:
    """Range and emptiness checks for values that coerced cleanly.

    Second tier: these are the defects that survive coercion because they are
    perfectly good numbers in the wrong place -- a level of 0, a score with an
    extra digit, a title that is only whitespace.
    """
    low, high = LEVEL_RANGE
    level = frame["level"]
    score = frame["score"]

    checks = (
        (
            "level",
            level.isna(),
            "missing (a NaN level drops the row out of every "
            "level bucket instead of landing in the wrong one)",
        ),
        ("level", level.notna() & (level % 1 != 0), "not a whole number"),
        ("level", level.notna() & ~level.between(low, high), f"outside {low}-{high}"),
        (
            "score",
            score.notna() & ~score.between(0, MAX_SCORE),
            f"outside 0-{MAX_SCORE:,}",
        ),
        ("title", _blank(frame["title"]), "empty"),
    )

    defects = [
        f"  {column!r} is {problem}: "
        + _plural(int(mask.sum()), "row")
        + "\n"
        + _describe_rows(frame, mask, ("diff", "title", column))
        for column, mask, problem in checks
        if mask.any()
    ]

    if defects:
        raise ValueDefectError(
            f"Tab {tab_name!r} has unusable values:\n"
            + "\n".join(defects)
            + "\n  Fix: correct the cells in the sheet."
        )


def normalize(csv_text: str, tab_name: str) -> pd.DataFrame:
    """Parse raw CSV text into a validated frame of singles charts.

    Only the columns in CANONICAL_COLUMNS are kept, and only singles rows.
    Unread columns may be added, removed, renamed, or reordered freely. A
    *read* column that no longer matches any alias is a hard failure at load,
    and so is a cell whose value cannot be trusted -- before any number is
    computed. Silent wrongness is the failure mode this whole layer exists to
    prevent.

    Order matters. The singles filter runs before the value checks so an
    untended doubles row cannot stop the app, and the coercion-loss check runs
    before ``to_numeric`` because that is the only point where the original
    cell text still exists.
    """
    raw = pd.read_csv(io.StringIO(csv_text), thousands=",")

    rename: dict[str, str] = {}
    missing: list[str] = []
    for canonical, aliases in COLUMN_ALIASES.items():
        matches = [column for column in raw.columns if column in aliases]
        if not matches:
            missing.append(canonical)
            continue
        rename[matches[0]] = canonical

    if missing:
        raise SchemaError(
            f"Tab {tab_name!r} is missing a column for: {', '.join(sorted(missing))}.\n"
            + "\n".join(
                f"  {name!r} accepts: {', '.join(sorted(COLUMN_ALIASES[name]))}"
                for name in sorted(missing)
            )
            + f"\n  Header has: {', '.join(map(str, raw.columns))}\n"
            f"  Fix: add the new sheet column name to COLUMN_ALIASES in "
            f"life4/data/schema.py -- one entry covers every tab."
        )

    out = raw.rename(columns=rename)[list(CANONICAL_COLUMNS)].copy()
    out = _filter_to_singles(out, tab_name)

    _raise_on_coercion_loss(out, tab_name)
    for column in NUMERIC_COLUMNS:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    _raise_on_bad_values(out, tab_name)

    return out.reset_index(drop=True)
