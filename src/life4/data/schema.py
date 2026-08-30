import io

import pandas as pd

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


class SchemaError(Exception):
    """A tab is missing a column the app reads."""


def normalize(csv_text: str, tab_name: str) -> pd.DataFrame:
    """Parse raw CSV text into a frame with canonical column names.

    Only the columns in CANONICAL_COLUMNS are kept. Unread columns may be
    added, removed, renamed, or reordered freely. A *read* column that no
    longer matches any alias is a hard failure at load, before any number is
    computed -- silent wrongness is the failure mode this whole layer exists
    to prevent.
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
    for column in NUMERIC_COLUMNS:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out
