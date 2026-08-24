# LIFE4 Dashboard Data Layer Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the dashboard read both the A3 and WORLD score tabs through a non-truncating endpoint, merge them into one chart history, and stop reporting requirements as satisfied when they are not.

**Architecture:** Four separable layers replace the current single `backends.py` → `DDRDataset` path. A pure schema module maps each tab's header onto the 11 canonical columns the app actually reads, by name, via one shared alias table; unread columns are ignored and a missing read column is a hard failure. A loader fetches `/export?format=csv&gid=`. A merge module joins the two tabs on `(title, diff)`, taking max score, unioned achievement dates, and the perfect count from the higher-scoring row. `DDRDataset` then exposes two chart-pool views — one that includes optional charts (for counting) and one that excludes them (for "all charts at this level" requirements) — and each `Requirement` subclass declares which it consumes.

**Tech Stack:** Python 3.11+, pandas, pydantic, Streamlit, pytest, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-16-life4-dashboard-overhaul-design.md`

## Global Constraints

- Python `>=3.11`. Dependencies managed by `uv`; add with `uv add`, dev deps with `uv add --dev`.
- Document ID is `1o664te8mE0nnD-PyEW7kEW8CszLPQ3E_`. WORLD tab gid is `638900183`. The A3 (`CTF`) and trials gids are **not yet known** — Task 8 includes reading them off the tab URLs.
- Singles difficulties only: `bSP`, `BSP`, `DSP`, `ESP`, `CSP`.
- Canonical column names are lowercase snake_case throughout. No code below the loader may reference a raw sheet header.
- Tests never touch the network and never import `streamlit`.
- Only these 11 columns are read: `diff` `level` `title` `score` `perfect` `record_on` `pfc_date` `gfc_date` `fc_date` `life4_date` `availability`. Everything else in the sheet is ignored on purpose. Mapping is **by name**; the duplicate `M` in the WORLD header is Marvelous and Miss, both unread.
- Streamlit floor is `>=1.62`. Use `st.cache_data(refresh_mode="background")` for data refresh; `st.popover` (not a nested `st.expander`, which Streamlit forbids) for in-expander disclosure.
- `uv run pytest` is the test command. `uv run ruff check .` must pass before every commit.

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/life4/data/schema.py` | **new** — 11 canonical columns, one shared `COLUMN_ALIASES` table, `normalize()` |
| `src/life4/data/availability.py` | **new** — `AvailabilityClass`, `ChartPool`, `classify()` |
| `src/life4/data/merge.py` | **new** — `merge_scores()` |
| `src/life4/data/loaders.py` | **new** — `GoogleSheetLoader`, replaces `backends.py` |
| `src/life4/data/backends.py` | **deleted** — gviz URLs and dead `OnedriveDataSource` |
| `src/life4/data/interfaces.py` | modified — drop `ScoreTrialFetcher`, superseded by the loader |
| `src/life4/ddr.py` | modified — takes a prepared canonical frame; two pool views |
| `src/life4/life4/core.py` | modified — MA point mapping domain |
| `src/life4/life4/ranks/requirements.py` | modified — `pool` attribute, `TYPE_CHECKING` import, `ClearRequirement` fix |
| `app.py` | modified — remove Click, stop mutating `st.secrets`, wire the new layers |
| `pyproject.toml` | modified — add pytest, drop the global `F821` ignore |
| `tests/conftest.py` | **new** — canonical-frame builders |
| `tests/test_schema.py`, `test_lamps.py`, `test_requirements.py`, `test_availability.py`, `test_merge.py` | **new** |

---

## Task 1: Canonical schema by name-alias

Maps each tab's header onto canonical column names, mapping **only the 11 columns
the app actually reads**. Mapping is by name via one shared alias table — not
positional, and not per-tab.

Audited 2026-08-23: the duplicate `M` in the WORLD header is Marvelous and Miss,
**both unread**, so the duplicate-header problem that originally forced positional
mapping does not exist. 10 of the 11 read columns are identically named in both
tabs; only `perfect` differs (`P` in WORLD, `Perf` in CTF).

**Files:**
- Create: `src/life4/data/schema.py`
- Test: `tests/test_schema.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nothing.
- Produces: `CANONICAL_COLUMNS: tuple[str, ...]`; `NUMERIC_COLUMNS: tuple[str, ...]`; `COLUMN_ALIASES: dict[str, frozenset[str]]`; `SchemaError(Exception)`; `normalize(csv_text: str, tab_name: str) -> pd.DataFrame`. `normalize` owns dtypes: `level`, `score`, `perfect` are always numeric, blanks as `NaN`.

- [ ] **Step 1: Add pytest**

```bash
uv add --dev pytest
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_schema.py`:

```python
import pytest

import pandas as pd

from life4.data.schema import CANONICAL_COLUMNS, SchemaError, normalize

WORLD_CSV = (
    "Diff,Level,Title,# times,Last played,M,P,Gr,Go,O.K.,M,EX,Score,"
    "Record On,AAA Date,PFC Date,GFC Date,FC Date,Life4 Date,Availability,MA\n"
    "ESP,16,Metamorphic,3,4/17/2026,900,4,0,0,0,1,1800,999670,"
    "4/1/2026,4/2/2026,4/3/2026,,,,0.99\n"
)

A3_CSV = (
    '"Diff","Level","Title","# times","Last played","MA Ratio","Marv","Perf",'
    '"Great","Good","O.K.","Miss","EX","Score","Record On","AAA Date",'
    '"PFC Date","GFC Date","FC Date","Life4 Date","Availability"\n'
    '"ESP","16","Metamorphic","5","2/19/2026","0.98","880","20","0","0","0",'
    '"0","1780","998000","1/1/2026","1/2/2026","1/3/2026","","","",""\n'
)


def test_maps_world_p_to_perfect():
    df = normalize(WORLD_CSV, "world")
    assert df.loc[0, "perfect"] == 4


def test_maps_a3_perf_to_perfect():
    df = normalize(A3_CSV, "a3")
    assert df.loc[0, "perfect"] == 20


def test_both_tabs_produce_the_same_columns():
    assert list(normalize(WORLD_CSV, "world").columns) == list(CANONICAL_COLUMNS)
    assert list(normalize(A3_CSV, "a3").columns) == list(CANONICAL_COLUMNS)


def test_duplicate_m_header_is_ignored_because_neither_is_read():
    # WORLD's header has "M" twice (Marvelous and Miss). Neither is read, so
    # the ambiguity must never reach the caller.
    df = normalize(WORLD_CSV, "world")
    assert "marvelous" not in df.columns
    assert "miss" not in df.columns


def test_unread_columns_may_be_renamed_freely():
    changed = WORLD_CSV.replace("EX", "ExScore", 1).replace("# times", "Plays", 1)
    df = normalize(changed, "world")
    assert df.loc[0, "score"] == 999670


def test_extra_column_is_ignored():
    changed = WORLD_CSV.replace("Availability,MA\n", "Availability,MA,Notes\n", 1)
    changed = changed.replace("0.99\n", "0.99,hello\n", 1)
    assert normalize(changed, "world").loc[0, "score"] == 999670


def test_reordering_read_columns_is_fine():
    reordered = (
        "Title,Diff,Level,Score,P,Record On,PFC Date,GFC Date,FC Date,"
        "Life4 Date,Availability\n"
        "Metamorphic,ESP,16,999670,4,4/1/2026,4/3/2026,,,,\n"
    )
    df = normalize(reordered, "world")
    assert df.loc[0, "score"] == 999670
    assert df.loc[0, "perfect"] == 4


def test_renaming_a_read_column_fails_with_an_actionable_message():
    broken = WORLD_CSV.replace(",Score,", ",Money Score,", 1)
    with pytest.raises(SchemaError) as exc:
        normalize(broken, "world")
    message = str(exc.value)
    assert "world" in message
    assert "score" in message
    assert "COLUMN_ALIASES" in message


def test_thousands_separators_parse_as_numbers():
    with_commas = WORLD_CSV.replace("999670", '"999,670"')
    assert normalize(with_commas, "world").loc[0, "score"] == 999670


def test_numeric_columns_are_numeric_even_when_the_tab_is_all_blanks():
    blanks = (
        "Diff,Level,Title,Score,P,Record On,PFC Date,GFC Date,FC Date,"
        "Life4 Date,Availability\n"
        "ESP,16,Untouched,,,,,,,,\n"
    )
    df = normalize(blanks, "world")
    assert df["score"].dtype.kind == "f"
    assert df["perfect"].dtype.kind == "f"
    assert pd.isna(df.loc[0, "score"])
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'life4.data.schema'`

- [ ] **Step 4: Write the implementation**

Create `src/life4/data/schema.py`:

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_schema.py -v`
Expected: 9 passed

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check . && uv run ruff format .
git add src/life4/data/schema.py tests/test_schema.py pyproject.toml uv.lock
git commit -m "feat(data): canonical schema mapping read columns by name alias"
```

---
## Task 2: Fixture builders and DDRDataset on canonical columns

`DDRDataset` currently loads, filters, and validates inside `__init__`, which makes it untestable without a network round-trip and a dataset containing every level 14–19. This task separates construction from loading and moves it onto canonical column names.

**Files:**
- Create: `tests/conftest.py`, `tests/test_lamps.py`
- Modify: `src/life4/ddr.py`, `src/life4/life4/ranks/requirements.py`

**Interfaces:**
- Consumes: `CANONICAL_COLUMNS` from Task 1.
- Produces: `DDRDataset(data: pd.DataFrame, trials: list[Life4Trial] | None = None)`; `Lamp` unchanged; all `DDRDataset` accessors now read canonical lowercase columns. Fixture helper `chart(**overrides) -> dict` and `dataset(*charts) -> DDRDataset`.

- [ ] **Step 1: Write the fixture builders**

Create `tests/conftest.py`:

```python
import numpy as np
import pandas as pd
import pytest

from life4.data.schema import CANONICAL_COLUMNS, NUMERIC_COLUMNS
from life4.ddr import DDRDataset


def chart(**overrides):
    """One chart row. Everything defaults to unplayed; override what matters."""
    row = dict.fromkeys(CANONICAL_COLUMNS, np.nan)
    row.update(diff="ESP", level=16, title="untitled")
    row.update(overrides)
    return row


def frame(*charts):
    """Build a frame with the same dtypes normalize() produces from real CSV."""
    df = pd.DataFrame(list(charts), columns=list(CANONICAL_COLUMNS))
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def dataset(*charts, trials=None):
    return DDRDataset(frame(*charts), trials=trials or [])


@pytest.fixture
def make_dataset():
    return dataset
```

- [ ] **Step 2: Write the failing lamp tests**

Create `tests/test_lamps.py`:

```python
from conftest import chart, dataset

from life4.ddr import Lamp


def test_unplayed_chart_has_no_lamp():
    d = dataset(chart(title="a", level=16))
    assert d.get_lamps_for_level(16) == [Lamp.NO_LAMP]


def test_score_of_one_million_is_marvelous_full_combo():
    d = dataset(chart(title="a", level=16, score=1_000_000, record_on="1/1/2026"))
    assert d.get_lamps_for_level(16) == [Lamp.White]


def test_pfc_date_outranks_lower_lamp_dates():
    d = dataset(
        chart(
            title="a",
            level=16,
            score=999_950,
            record_on="1/1/2026",
            pfc_date="1/2/2026",
            fc_date="1/3/2026",
            life4_date="1/4/2026",
        )
    )
    assert d.get_lamps_for_level(16) == [Lamp.Gold]


def test_level_lamp_is_the_weakest_chart_at_that_level():
    d = dataset(
        chart(title="a", level=16, score=999_950, record_on="1/1/2026", pfc_date="1/2/2026"),
        chart(title="b", level=16),
    )
    assert d.get_level_lamp(16) == Lamp.NO_LAMP


def test_level_lamp_of_a_level_with_no_charts_is_no_lamp():
    d = dataset(chart(title="a", level=16))
    assert d.get_level_lamp(19) == Lamp.NO_LAMP
```

- [ ] **Step 3: Run to verify they fail**

Run: `uv run pytest tests/test_lamps.py -v`
Expected: FAIL — `DDRDataset.__init__() got an unexpected keyword argument 'trials'`

- [ ] **Step 4: Rewrite DDRDataset**

Replace the contents of `src/life4/ddr.py` above `get_lamp` with:

```python
import logging
from enum import IntEnum
from typing import TYPE_CHECKING

import pandas as pd

from life4.life4.core import MFC_POINT_MAPPING, SDP_POINT_MAPPING

if TYPE_CHECKING:
    from life4.life4.core import Life4Trial

logger = logging.getLogger(__name__)


class Lamp(IntEnum):
    NO_LAMP = 0
    Clear = 1
    Red = 2
    Blue = 3
    Green = 4
    Gold = 5
    White = 6


class DDRDataset:
    """Chart history with lamps derived. Takes a prepared canonical frame.

    Loading, filtering, and merging happen upstream in life4.data so this
    class can be constructed from a handful of rows in a test.
    """

    def __init__(self, data: pd.DataFrame, trials: "list[Life4Trial] | None" = None):
        self._data = data.copy()
        self._data["lamp"] = self._data.apply(self._get_lamp, axis=1)
        self.trials = list(trials or [])

    def _get_lamp(self, row) -> Lamp:
        if row["score"] == 1_000_000:
            return Lamp.White
        missing = row.isna()
        if missing["record_on"]:
            return Lamp.NO_LAMP
        elif not missing["pfc_date"]:
            return Lamp.Gold
        elif not missing["gfc_date"]:
            return Lamp.Green
        elif not missing["fc_date"]:
            return Lamp.Blue
        elif not missing["life4_date"]:
            return Lamp.Red
        return Lamp.Clear
```

Then rewrite each accessor onto canonical names. `get_level_lamp` must stop
raising on an empty level:

```python
    def get_level(self, level: int) -> pd.DataFrame:
        return self._data[self._data["level"] == level]

    def get_lamp(self, lamp: Lamp) -> pd.DataFrame:
        return self._data[self._data["lamp"] == lamp]

    def get_lamps_for_level(self, level: int) -> list[Lamp]:
        return self.get_level(level)["lamp"].to_list()

    def get_level_lamp(self, level: int) -> Lamp:
        lamps = self.get_lamps_for_level(level)
        return min(lamps) if lamps else Lamp.NO_LAMP

    def get_num_pfcs(self, level: int) -> int:
        return int((self.get_level(level)["lamp"] == Lamp.Gold).sum())

    def get_num_AAA(self, level: int) -> int:
        return int((self.get_level(level)["score"] >= 990_000).sum())

    def get_ceiling(self, level: int):
        return self.get_level(level)["score"].max()

    def get_songs_below_threshold(self, level: int, threshold: int) -> pd.DataFrame:
        level_songs = self.get_level(level)
        return level_songs[level_songs["score"] < threshold]

    def get_songs_above_threshold(self, level: int, threshold: int) -> pd.DataFrame:
        level_songs = self.get_level(level)
        return level_songs[level_songs["score"] >= threshold]

    def get_songs_in_range(self, level: int, lower: int, upper: int) -> pd.DataFrame:
        level_songs = self.get_level(level)
        return level_songs[
            (level_songs["score"] >= lower) & (level_songs["score"] < upper)
        ]

    def get_sdps(self) -> pd.DataFrame:
        return self._data[
            (self._data["lamp"] == Lamp.Gold) & (self._data["perfect"] < 10)
        ]
```

Delete `_validate_data` and the `filter_*` constructor arguments entirely —
filtering now happens upstream.

- [ ] **Step 5: Update requirements.py column references**

In `src/life4/life4/ranks/requirements.py`, replace `["Level"]` with
`["level"]` and `["Score"]` with `["score"]` in `SDPRequirement.is_satisfied`,
`SDPCountRequirement._count_sdps`, `MFCRequirement.is_satisfied`, and
`MFCCountRequirement._count_mfcs`.

- [ ] **Step 6: Run to verify they pass**

Run: `uv run pytest tests/test_lamps.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
uv run ruff check . && uv run ruff format .
git add src/life4/ddr.py src/life4/life4/ranks/requirements.py tests/
git commit -m "refactor(ddr): construct from a prepared canonical frame"
```

---

## Task 3: Fix ClearRequirement counting unplayed charts

Bug #1 in the spec. `ClearRequirement(level=19, num=1)` currently evaluates
`10 >= 1 → True` against 10 charts of which 2 are played.

**Files:**
- Modify: `src/life4/life4/ranks/requirements.py:154-176`, `src/life4/ddr.py`
- Test: `tests/test_requirements.py`

**Interfaces:**
- Consumes: `DDRDataset` from Task 2.
- Produces: `DDRDataset.get_level_scores(level: int) -> pd.Series` returning **played scores only**. The `return_zero` parameter is removed.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_requirements.py`:

```python
from conftest import chart, dataset

from life4.life4.ranks.requirements import ClearRequirement


def played(title, level, score):
    return chart(title=title, level=level, score=score, record_on="1/1/2026")


def test_clear_without_floor_ignores_unplayed_charts():
    d = dataset(
        played("a", 19, 720_000),
        played("b", 19, 810_000),
        *[chart(title=str(i), level=19) for i in range(8)],
    )
    assert ClearRequirement(level=19, num=1).is_satisfied(d)
    assert not ClearRequirement(level=19, num=5).is_satisfied(d)
    assert ClearRequirement(level=19, num=5).get_progress(d) == "2/5"


def test_clear_with_floor_counts_only_scores_above_it():
    d = dataset(played("a", 18, 900_000), played("b", 18, 700_000))
    assert ClearRequirement(level=18, num=1, floor=810_000).is_satisfied(d)
    assert not ClearRequirement(level=18, num=2, floor=810_000).is_satisfied(d)


def test_clear_exceptions_fill_the_gap_up_to_the_limit():
    d = dataset(
        played("a", 18, 900_000),
        played("b", 18, 780_000),
        played("c", 18, 770_000),
    )
    req = ClearRequirement(
        level=18, num=3, floor=810_000, num_exceptions=1, exception_floor=760_000
    )
    assert not req.is_satisfied(d)
    assert req.get_progress(d) == "2/3"


def test_clear_exceptions_below_the_exception_floor_do_not_count():
    d = dataset(played("a", 18, 900_000), played("b", 18, 700_000))
    req = ClearRequirement(
        level=18, num=2, floor=810_000, num_exceptions=1, exception_floor=760_000
    )
    assert not req.is_satisfied(d)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_requirements.py -v`
Expected: `test_clear_without_floor_ignores_unplayed_charts` FAILS — asserts `not satisfied` for `num=5` but gets satisfied, because unplayed charts are counted.

- [ ] **Step 3: Fix `get_level_scores`**

In `src/life4/ddr.py`, replace `get_level_scores`:

```python
    def get_level_scores(self, level: int) -> pd.Series:
        """Scores for charts actually played at this level. Unplayed excluded."""
        return self.get_level(level)["score"].dropna()
```

- [ ] **Step 4: Update the caller**

In `requirements.py`, `ClearRequirement._get_valid_scores`, change the first
line to drop the removed argument:

```python
        level_scores = data.get_level_scores(level=self.level)
```

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest tests/test_requirements.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
uv run ruff check . && uv run ruff format .
git add src/life4/ddr.py src/life4/life4/ranks/requirements.py tests/test_requirements.py
git commit -m "fix(requirements): ClearRequirement no longer counts unplayed charts

ClearRequirement with no floor returned len(level_scores), which included
every chart at that level whether played or not. 'Clear a 19' evaluated
satisfied against 10 charts of which 2 were played."
```

---

## Task 4: MA points fail loudly above the mapped range

Bug #6. `MFC_POINT_MAPPING` covers levels 1–16; `get_ma_points()` raises a bare
`KeyError` on the first SDP or MFC at 17+.

The correct point values for 17–19 are **not yet known** and must come from the
LIFE4 site — do not interpolate. This task converts the crash into an
actionable error and adds the extension point.

**Files:**
- Modify: `src/life4/life4/core.py`, `src/life4/ddr.py`
- Test: `tests/test_requirements.py`

**Interfaces:**
- Consumes: `DDRDataset` from Task 2.
- Produces: `MAPointsUnknownLevel(Exception)` in `life4.life4.core`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_requirements.py`:

```python
import pytest

from life4.life4.core import MAPointsUnknownLevel


def pfc(title, level, perfects):
    return chart(
        title=title,
        level=level,
        score=1_000_000 - perfects * 10,
        perfect=perfects,
        record_on="1/1/2026",
        pfc_date="1/2/2026",
    )


def test_ma_points_sums_sdps_and_mfcs():
    d = dataset(pfc("a", 14, 5), pfc("b", 12, 3))
    # SDP is 1/10 of an MFC: level 14 -> 0.8, level 12 -> 0.4
    assert d.get_ma_points() == pytest.approx(1.2)


def test_pfc_with_ten_or_more_perfects_is_not_an_sdp():
    d = dataset(pfc("a", 14, 10))
    assert d.get_ma_points() == 0


def test_sdp_above_the_mapped_range_raises_an_actionable_error():
    d = dataset(pfc("a", 17, 4))
    with pytest.raises(MAPointsUnknownLevel) as exc:
        d.get_ma_points()
    assert "17" in str(exc.value)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_requirements.py -k ma_points -v`
Expected: FAIL — `ImportError: cannot import name 'MAPointsUnknownLevel'`

- [ ] **Step 3: Add the exception**

In `src/life4/life4/core.py`, below the mappings:

```python
class MAPointsUnknownLevel(Exception):
    """An SDP or MFC was earned at a level with no defined MA point value.

    MFC_POINT_MAPPING covers levels 1-16. Values for 17+ must be sourced
    from life4ddr.com rather than interpolated -- the existing curve
    (8, 15, 25 at levels 14, 15, 16) is not a formula.
    """
```

- [ ] **Step 4: Use it in `get_ma_points`**

In `src/life4/ddr.py`:

```python
    def get_ma_points(self) -> float:
        sdp_levels = self.get_sdps()["level"]
        mfc_levels = self.get_lamp(Lamp.White)["level"]
        for level in (*sdp_levels, *mfc_levels):
            if level not in MFC_POINT_MAPPING:
                raise MAPointsUnknownLevel(
                    f"No MA point value defined for level {level}. "
                    f"MFC_POINT_MAPPING covers levels "
                    f"{min(MFC_POINT_MAPPING)}-{max(MFC_POINT_MAPPING)}; "
                    f"source the value from life4ddr.com and add it."
                )
        sdp_points = sum(SDP_POINT_MAPPING[level] for level in sdp_levels)
        mfc_points = sum(MFC_POINT_MAPPING[level] for level in mfc_levels)
        return sdp_points + mfc_points
```

Add `MAPointsUnknownLevel` to the existing `life4.life4.core` import in `ddr.py`.

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest tests/test_requirements.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
uv run ruff check . && uv run ruff format .
git add src/life4/life4/core.py src/life4/ddr.py tests/test_requirements.py
git commit -m "fix(core): raise an actionable error for MA points above level 16"
```

---

## Task 5: Availability classification

Bug #2. `extra exclusive` and `phase 2` are currently counted in every
denominator. Per the FAQ, Extra Stage songs are "not required but count if
earned."

**Files:**
- Create: `src/life4/data/availability.py`
- Test: `tests/test_availability.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `AvailabilityClass` (`NORMAL`, `OPTIONAL`, `EXCLUDED`); `ChartPool` (`REQUIRED`, `EARNED`); `classify(value) -> AvailabilityClass`; `pool_classes(pool: ChartPool) -> frozenset[AvailabilityClass]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_availability.py`:

```python
import numpy as np

from life4.data.availability import (
    AvailabilityClass,
    ChartPool,
    classify,
    pool_classes,
)


def test_blank_availability_is_a_normal_chart():
    assert classify(np.nan) is AvailabilityClass.NORMAL
    assert classify(None) is AvailabilityClass.NORMAL


def test_extra_stage_and_phase_two_are_optional():
    assert classify("extra exclusive") is AvailabilityClass.OPTIONAL
    assert classify("phase 2") is AvailabilityClass.OPTIONAL


def test_removed_and_course_trial_are_excluded():
    assert classify("removed") is AvailabilityClass.EXCLUDED
    assert classify("course trial") is AvailabilityClass.EXCLUDED
    assert classify("Other") is AvailabilityClass.EXCLUDED


def test_unknown_marker_defaults_to_excluded(caplog):
    assert classify("galaxy brave") is AvailabilityClass.EXCLUDED
    assert "galaxy brave" in caplog.text


def test_required_pool_excludes_optional_charts():
    assert pool_classes(ChartPool.REQUIRED) == frozenset({AvailabilityClass.NORMAL})


def test_earned_pool_includes_optional_charts():
    assert pool_classes(ChartPool.EARNED) == frozenset(
        {AvailabilityClass.NORMAL, AvailabilityClass.OPTIONAL}
    )
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_availability.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'life4.data.availability'`

- [ ] **Step 3: Write the implementation**

Create `src/life4/data/availability.py`:

```python
import logging
from enum import Enum

import pandas as pd

logger = logging.getLogger(__name__)


class AvailabilityClass(Enum):
    """How a chart's availability marker affects requirement evaluation."""

    NORMAL = "normal"
    OPTIONAL = "optional"
    EXCLUDED = "excluded"


class ChartPool(Enum):
    """Which charts a requirement is evaluated against.

    REQUIRED -- "all 16s over 955k" style requirements. Optional charts must
    not appear here or an unplayed Extra Stage chart blocks the requirement.

    EARNED -- "PFC 26 16s" style counts. Optional charts count if played,
    per the FAQ: Extra Stage songs "aren't required but count if earned."
    """

    REQUIRED = "required"
    EARNED = "earned"


_CLASSES = {
    "extra exclusive": AvailabilityClass.OPTIONAL,
    "phase 2": AvailabilityClass.OPTIONAL,
    "course trial": AvailabilityClass.EXCLUDED,
    "Other": AvailabilityClass.EXCLUDED,
    "removed": AvailabilityClass.EXCLUDED,
}

_POOLS = {
    ChartPool.REQUIRED: frozenset({AvailabilityClass.NORMAL}),
    ChartPool.EARNED: frozenset(
        {AvailabilityClass.NORMAL, AvailabilityClass.OPTIONAL}
    ),
}


def classify(value) -> AvailabilityClass:
    """An allowlist: an unrecognised marker is excluded, never silently counted."""
    if value is None or pd.isna(value):
        return AvailabilityClass.NORMAL
    try:
        return _CLASSES[value]
    except KeyError:
        logger.warning(
            "Unrecognised availability marker %r; excluding these charts. "
            "Classify it in life4.data.availability if it should count.",
            value,
        )
        return AvailabilityClass.EXCLUDED


def pool_classes(pool: ChartPool) -> frozenset[AvailabilityClass]:
    return _POOLS[pool]
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_availability.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
uv run ruff check . && uv run ruff format .
git add src/life4/data/availability.py tests/test_availability.py
git commit -m "feat(data): classify chart availability as normal/optional/excluded"
```

---

## Task 6: Two chart-pool views on DDRDataset

**Files:**
- Modify: `src/life4/ddr.py`, `src/life4/life4/ranks/requirements.py`
- Test: `tests/test_requirements.py`

**Interfaces:**
- Consumes: `ChartPool`, `classify`, `pool_classes` from Task 5.
- Produces: every `DDRDataset` accessor gains a keyword-only `pool: ChartPool = ChartPool.EARNED` argument. Every `Requirement` subclass gains a class attribute `pool: ChartPool`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_requirements.py`:

```python
from life4.life4.ranks.requirements import FloorRequirement, PFCRequirement


def test_unplayed_optional_chart_does_not_block_a_floor_requirement():
    d = dataset(
        played("a", 18, 900_000),
        chart(title="eon break", level=18, availability="extra exclusive"),
    )
    assert FloorRequirement(level=18, floor=850_000).is_satisfied(d)


def test_played_optional_chart_counts_toward_a_pfc_count():
    d = dataset(
        pfc("a", 16, 4),
        chart(
            title="metamorphic",
            level=16,
            availability="phase 2",
            score=999_960,
            perfect=4,
            record_on="1/1/2026",
            pfc_date="1/2/2026",
        ),
    )
    assert PFCRequirement(level=16, num=2).is_satisfied(d)


def test_excluded_charts_count_in_neither_pool():
    d = dataset(
        played("a", 16, 900_000),
        chart(title="realize", level=16, availability="removed", score=999_000,
              record_on="1/1/2026", pfc_date="1/2/2026"),
    )
    assert not PFCRequirement(level=16, num=1).is_satisfied(d)
    assert FloorRequirement(level=16, floor=850_000).is_satisfied(d)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_requirements.py -k optional -v`
Expected: FAIL — the unplayed `extra exclusive` chart drags level 18's lamp to `NO_LAMP`, so `FloorRequirement.is_satisfied` returns False.

- [ ] **Step 3: Add pool filtering to DDRDataset**

In `DDRDataset.__init__`, after deriving lamps:

```python
        self._data["availability_class"] = self._data["availability"].map(classify)
```

Change `get_level` and `get_lamp` to filter by pool, and thread the keyword
through every accessor that calls them:

```python
    def charts(self, pool: ChartPool = ChartPool.EARNED) -> pd.DataFrame:
        allowed = pool_classes(pool)
        return self._data[self._data["availability_class"].isin(allowed)]

    def get_level(self, level: int, *, pool: ChartPool = ChartPool.EARNED):
        charts = self.charts(pool)
        return charts[charts["level"] == level]

    def get_lamp(self, lamp: Lamp, *, pool: ChartPool = ChartPool.EARNED):
        charts = self.charts(pool)
        return charts[charts["lamp"] == lamp]
```

Each remaining accessor (`get_lamps_for_level`, `get_level_lamp`,
`get_num_pfcs`, `get_num_AAA`, `get_ceiling`, `get_songs_below_threshold`,
`get_songs_above_threshold`, `get_songs_in_range`, `get_level_scores`,
`get_sdps`) takes `*, pool: ChartPool = ChartPool.EARNED` and passes it down.

- [ ] **Step 4: Declare the pool on each Requirement subclass**

In `requirements.py`, add to the `Requirement` ABC:

```python
class Requirement(ABC):
    multiple_levels: bool
    pool: ChartPool = ChartPool.EARNED
```

Set `pool = ChartPool.REQUIRED` on `LampRequirement`, `FloorRequirement`, and
`LampFloorRequirement`. Leave every other subclass on the `EARNED` default.

Then pass `pool=self.pool` at each `data.*` call site inside those three
classes. `LampFloorRequirement` delegates to `LampRequirement` and
`FloorRequirement`, which carry their own pool, so it needs no call-site change.

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
uv run ruff check . && uv run ruff format .
git add src/life4/ddr.py src/life4/life4/ranks/requirements.py tests/test_requirements.py
git commit -m "fix(ddr): optional charts count when earned but never block requirements"
```

---

## Task 7: Merge A3 and WORLD histories

**Files:**
- Create: `src/life4/data/merge.py`
- Test: `tests/test_merge.py`

**Interfaces:**
- Consumes: `CANONICAL_COLUMNS` from Task 1.
- Produces: `MergeResult(charts: pd.DataFrame, orphans: pd.DataFrame)`; `merge_scores(primary, secondary) -> MergeResult`. `primary` defines the chart pool, every chart's `level`, and `availability`. `charts` has one row per `(title, diff)` in `primary`; `orphans` holds secondary rows with no primary match.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_merge.py`:

```python
import pandas as pd
from conftest import chart, frame

from life4.data.merge import merge_scores


def test_primary_defines_the_chart_pool_and_levels():
    primary = frame(chart(title="drift", diff="DSP", level=15))
    secondary = frame(chart(title="drift", diff="DSP", level=14, score=900_000))
    merged = merge_scores(primary, secondary).charts
    assert len(merged) == 1
    assert merged.loc[0, "level"] == 15


def test_charts_only_in_secondary_are_dropped():
    primary = frame(chart(title="a", level=16))
    secondary = frame(
        chart(title="a", level=16), chart(title="gone", level=16, score=999_000)
    )
    assert list(merge_scores(primary, secondary).charts["title"]) == ["a"]


def test_score_is_the_max_across_sources():
    primary = frame(chart(title="a", level=16, score=980_000))
    secondary = frame(chart(title="a", level=16, score=991_000))
    assert merge_scores(primary, secondary).charts.loc[0, "score"] == 991_000


def test_a_chart_played_only_on_the_secondary_carries_over():
    primary = frame(chart(title="a", level=16))
    secondary = frame(
        chart(title="a", level=16, score=985_000, record_on="1/1/2026", fc_date="1/2/2026")
    )
    merged = merge_scores(primary, secondary).charts
    assert merged.loc[0, "score"] == 985_000
    assert merged.loc[0, "fc_date"] == "1/2/2026"


def test_achievement_dates_union_across_sources():
    primary = frame(chart(title="a", level=16, score=991_000, record_on="3/1/2026"))
    secondary = frame(
        chart(
            title="a", level=16, score=985_000,
            record_on="1/1/2026", fc_date="1/2/2026", pfc_date="1/3/2026",
        )
    )
    merged = merge_scores(primary, secondary).charts
    # The PFC was earned on the secondary cabinet; it must survive the merge
    # even though the primary holds the higher score.
    assert merged.loc[0, "pfc_date"] == "1/3/2026"
    assert merged.loc[0, "score"] == 991_000


def test_perfect_count_travels_with_the_higher_score():
    # A PFC's score is a deterministic function of its perfect count, so the
    # max score and its perfect count always come from the same row. Taking
    # them from different rows could manufacture an SDP that never happened.
    primary = frame(chart(title="a", level=16, score=980_000, perfect=40))
    secondary = frame(chart(title="a", level=16, score=999_950, perfect=5))
    merged = merge_scores(primary, secondary).charts
    assert merged.loc[0, "score"] == 999_950
    assert merged.loc[0, "perfect"] == 5


def test_perfect_count_is_not_taken_from_the_lower_scoring_row():
    primary = frame(chart(title="a", level=16, score=999_950, perfect=5))
    secondary = frame(chart(title="a", level=16, score=980_000, perfect=40))
    merged = merge_scores(primary, secondary).charts
    assert merged.loc[0, "perfect"] == 5


def test_orphan_secondary_chart_is_reported_not_silently_dropped():
    # WORLD is a strict superset of CTF by construction, so a CTF chart with
    # no WORLD match is always a defect -- usually a drifted title. It must
    # surface, because it means A3 scores stopped counting.
    primary = frame(chart(title="Tiger rampage (sasakure.UK)", level=17))
    secondary = frame(
        chart(title="Tiger rampage", level=17, score=969_390, record_on="1/1/2026")
    )
    result = merge_scores(primary, secondary)
    assert len(result.charts) == 1
    assert pd.isna(result.charts.loc[0, "score"])
    assert list(result.orphans["title"]) == ["Tiger rampage"]


def test_no_orphans_when_every_secondary_chart_matches():
    primary = frame(chart(title="a", level=16), chart(title="b", level=16))
    secondary = frame(chart(title="a", level=16, score=900_000))
    assert len(merge_scores(primary, secondary).orphans) == 0


def test_titles_are_never_normalized_before_joining():
    # 'PARANOiA' and 'PARANOiA (kskst mix)' are different charts. Stripping
    # parentheticals to make matching forgiving would merge them.
    primary = frame(
        chart(title="PARANOiA", level=16), chart(title="PARANOiA (kskst mix)", level=16)
    )
    secondary = frame(chart(title="PARANOiA", level=16, score=950_000))
    merged = merge_scores(primary, secondary).charts
    scores = dict(zip(merged["title"], merged["score"]))
    assert scores["PARANOiA"] == 950_000
    assert pd.isna(scores["PARANOiA (kskst mix)"])


def test_unplayed_on_both_stays_unplayed():
    merged = merge_scores(
        frame(chart(title="a", level=16)), frame(chart(title="a", level=16))
    ).charts
    assert pd.isna(merged.loc[0, "score"])
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_merge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'life4.data.merge'`

- [ ] **Step 3: Write the implementation**

Create `src/life4/data/merge.py`:

```python
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


def merge_scores(primary: pd.DataFrame, secondary: pd.DataFrame) -> pd.DataFrame:
    """Union two cabinets' histories into one row per chart.

    ``primary`` (WORLD) defines which charts exist, their level, and their
    availability. ``secondary`` (A3) contributes score and achievement history
    only, joined on (title, diff).

    Score is the max across sources; achievement dates are unioned; the
    judgment columns travel as a unit from whichever source holds the higher
    score.
    """
    matched = secondary.merge(
        primary[KEY_COLUMNS], on=KEY_COLUMNS, how="left", indicator=True
    )
    orphans = secondary[(matched["_merge"] == "left_only").to_numpy()]
    if len(orphans):
        logger.warning(
            "%d secondary charts have no primary match; their scores will not "
            "count. Usually a drifted title.", len(orphans)
        )

    m = primary.merge(secondary, on=KEY_COLUMNS, how="left", suffixes=("_p", "_s"))

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
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_merge.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
uv run ruff check . && uv run ruff format .
git add src/life4/data/merge.py tests/test_merge.py
git commit -m "feat(data): merge A3 and WORLD chart histories on (title, diff)"
```

---

## Task 8: Loader on the documented export endpoint

Bug #3. The gviz endpoint returns 3,415 of the WORLD tab's 10,821 rows because
it **inherits the sheet's filter view** (singles only, level 8+) — verified
exactly, zero mismatches across all rows. A loader must not inherit a view
setting: change the filter while inspecting the sheet and every denominator in
the dashboard silently changes with it.

**Files:**
- Create: `src/life4/data/loaders.py`
- Delete: `src/life4/data/backends.py`
- Modify: `src/life4/data/interfaces.py`, `.streamlit/secrets.toml`
- Test: `tests/test_loaders.py`

**Interfaces:**
- Consumes: `normalize` from Task 1.
- Produces: `GoogleSheetLoader(doc_id: str)` with `csv_url(gid: int) -> str`, `load(gid: int, tab_name: str) -> pd.DataFrame`, and `load_trials(gid: int) -> pd.DataFrame`.

- [ ] **Step 1: Read the missing gids**

Open the spreadsheet, click the `CTF` tab and the trials tab, and read `gid=`
off each tab's URL. Record both — they are needed in Step 5.

- [ ] **Step 2: Add requests**

```bash
uv add requests
```

- [ ] **Step 3: Write the failing test**

Create `tests/test_loaders.py`:

```python
from life4.data.loaders import GoogleSheetLoader


def test_builds_the_documented_export_url():
    loader = GoogleSheetLoader(doc_id="ABC123")
    assert loader.csv_url(638900183) == (
        "https://docs.google.com/spreadsheets/d/ABC123/export"
        "?format=csv&gid=638900183"
    )


def test_url_does_not_use_the_gviz_endpoint():
    # gviz silently truncated the WORLD tab to 3,408 of 10,814 rows.
    assert "gviz" not in GoogleSheetLoader(doc_id="ABC123").csv_url(0)
```

- [ ] **Step 4: Run to verify it fails**

Run: `uv run pytest tests/test_loaders.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'life4.data.loaders'`

- [ ] **Step 5: Write the implementation**

Create `src/life4/data/loaders.py`:

```python
import logging
import io

import pandas as pd
import requests

from life4.data.schema import normalize

logger = logging.getLogger(__name__)

_EXPORT_URL = "https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"


class GoogleSheetLoader:
    """Reads tabs via the documented CSV export endpoint.

    Deliberately not gviz/tq: that endpoint honours whatever filter view is
    active on the sheet. The WORLD tab has one (singles, level 8+), so gviz
    returned 3,415 of 10,821 rows with HTTP 200 and no warning. Today that
    filter happens to align with what the app wants; if it is ever changed,
    every denominator would shift with no error and no visible cause.

    /export?format=csv ignores filters and returns the raw grid. The app then
    applies its own singles filter explicitly.
    """

    def __init__(self, doc_id: str, timeout: int = 30):
        self.doc_id = doc_id
        self.timeout = timeout

    def csv_url(self, gid: int) -> str:
        return _EXPORT_URL.format(doc_id=self.doc_id, gid=gid)

    def load(self, gid: int, tab_name: str) -> pd.DataFrame:
        url = self.csv_url(gid)
        logger.info("Loading tab %s from %s", tab_name, url)
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return normalize(response.text, tab_name)
```

- [ ] **Step 6: Delete the old backend**

```bash
git rm src/life4/data/backends.py
```

Remove `ScoreTrialFetcher` from `src/life4/data/interfaces.py`; if that leaves
the file empty, delete it too.

- [ ] **Step 7: Rewrite secrets**

Replace `.streamlit/secrets.toml` with the gids from Step 1:

```toml
[sheets]
doc_id = "1o664te8mE0nnD-PyEW7kEW8CszLPQ3E_"

[sheets.tabs]
world = 638900183
a3 = <gid read in Step 1>
trials = <gid read in Step 1>
```

- [ ] **Step 8: Run to verify it passes**

Run: `uv run pytest tests/test_loaders.py -v`
Expected: 2 passed

- [ ] **Step 9: Verify against the live document (manual, one-off)**

```bash
uv run python -c "
from life4.data.loaders import GoogleSheetLoader
loader = GoogleSheetLoader('1o664te8mE0nnD-PyEW7kEW8CszLPQ3E_')
df = loader.load(gid=638900183, tab_name='world')
print(len(df), list(df.columns))
"
```

Expected: a number in the ten-thousands, and **doubles must be present** — their
absence means a filter leaked in. Assert a floor, not equality; the sheet is live
and grows (10,814 on 2026-08-16; 10,821 on 2026-08-23).

```python
assert len(df) > 9000, 'sheet filter may have leaked into the load'
assert (~df['diff'].isin(['bSP','BSP','DSP','ESP','CSP'])).any(), 'no doubles: filtered'
assert (df['level'] < 8).any(), 'no sub-8 charts: filtered'
```

- [ ] **Step 10: Commit**

```bash
uv run ruff check . && uv run ruff format .
git add -A
git commit -m "fix(data): load sheets via /export so the sheet filter cannot leak in

gviz/tq honours the WORLD tab's active filter view (singles, level 8+),
returning 3,415 of 10,821 rows with HTTP 200. Verified exactly: gviz
membership == (singles AND level >= 8), zero mismatches. A loader must
not inherit a view setting -- changing the filter would silently move
every requirement denominator."
```

---

## Task 9: Wire it together and clean up the entrypoint

**Files:**
- Modify: `app.py`, `pyproject.toml`, `src/life4/life4/ranks/requirements.py`

**Interfaces:**
- Consumes: everything from Tasks 1–8.
- Produces: `load_dataset() -> DDRDataset`, cached.

- [ ] **Step 1: Replace app.py**

```python
import pandas as pd
import streamlit as st

from life4.data.loaders import GoogleSheetLoader
from life4.data.merge import merge_scores
from life4.ddr import DDRDataset
from life4.life4.core import Life4Trial
from life4.life4.ranks.a20_plus import amethyst, emerald
from life4.life4_ui import Life4RankDisplay

SINGLES_DIFFICULTIES = ("bSP", "BSP", "DSP", "ESP", "CSP")

st.set_page_config(layout="wide")


@st.cache_data(ttl=600)
def load_frames():
    secrets = st.secrets["sheets"]
    loader = GoogleSheetLoader(doc_id=secrets["doc_id"])
    tabs = secrets["tabs"]
    world = loader.load(gid=tabs["world"], tab_name="world")
    a3 = loader.load(gid=tabs["a3"], tab_name="a3")
    trials = loader.load_trials(gid=tabs["trials"])
    return world, a3, trials


def load_dataset() -> tuple[DDRDataset, pd.DataFrame]:
    world, a3, trials = load_frames()
    singles = lambda df: df[df["diff"].isin(SINGLES_DIFFICULTIES)]
    result = merge_scores(singles(world), singles(a3))
    trial_models = [Life4Trial(**row) for _, row in trials.iterrows()]
    return DDRDataset(result.charts, trials=trial_models), result.orphans


def main() -> None:
    if st.button("Refresh data"):
        load_frames.clear()

    data, orphans = load_dataset()

    if len(orphans):
        st.warning(
            f"{len(orphans)} A3 charts no longer match any WORLD chart, so "
            f"their scores are not counting. Usually a drifted title."
        )
        with st.expander("Show unmatched A3 charts"):
            st.dataframe(orphans[["title", "diff", "level", "score"]], height=200)


    _, center, _ = st.columns(3)
    with center:
        st.image("assets/life4-logo.png", use_container_width=True)

    rank_choice = st.selectbox("Select rank", ("Amethyst", "Emerald"), index=1)
    rank = amethyst if rank_choice == "Amethyst" else emerald

    for sub_rank, column in zip(rank, st.columns(5)):
        with column:
            Life4RankDisplay(sub_rank, data).visualize()


main()
```

This removes: the `click` command wrapper (which parsed Streamlit's `argv`,
evaluated `st.secrets` at import time, and called `sys.exit()` on completion),
the `data_source_info.pop("source")` mutation of `st.secrets` that broke on the
second rerun, and the `sys.path.append("src")` working-directory dependency.

- [ ] **Step 2: Add the trials loader**

Add to `GoogleSheetLoader` in `src/life4/data/loaders.py`:

```python
    def load_trials(self, gid: int) -> pd.DataFrame:
        response = requests.get(self.csv_url(gid), timeout=self.timeout)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text))
```

Add `import io` at the top of the file.

- [ ] **Step 3: Fix the TYPE_CHECKING import and drop the F821 ignore**

At the top of `src/life4/life4/ranks/requirements.py`:

```python
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from life4.ddr import DDRDataset
```

Remove `from life4.ddr import Lamp`'s string-annotation workarounds where they
are no longer needed, then delete from `pyproject.toml`:

```toml
[tool.ruff.lint]
ignore = ["F821"]
```

and the now-unneeded `[tool.ruff.lint.per-file-ignores]` entry for `app.py`.

- [ ] **Step 4: Verify the linter now catches what it was hiding**

Run: `uv run ruff check .`
Expected: clean. If undefined names surface elsewhere, fix them — that is the
ignore having hidden real defects.

- [ ] **Step 5: Give checkboxes stable keys**

`life4_ui.py:21` uses `key=str(uuid.uuid4())`, generating a fresh key for every
checkbox on every rerun and growing Streamlit's session state without bound.
Replace with a key derived from what the checkbox represents:

```python
    def create_checkbox(self, requirement: Requirement, group: str):
        st.checkbox(
            requirement.display_str(self.data),
            disabled=True,
            value=requirement.is_satisfied(self.data),
            key=f"{self.life4_rank}|{group}|{requirement}",
        )
```

Pass `group="req"` from the requirements loop and `group="sub"` from the
substitutions loop in `_visualize_reqs`, so a requirement appearing in both
lists does not collide. Delete the now-unused `import uuid`.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: all tests pass

- [ ] **Step 7: Smoke-test the app**

Run: `uv run streamlit run app.py`

Confirm: the page renders, "Clear a 19" under Emerald I now shows **unsatisfied**
(2 of your 10 nineteens are played), and 18s floor requirements are no longer
blocked by the unplayed `Eon Break CSP`.

- [ ] **Step 8: Commit**

```bash
uv run ruff check . && uv run ruff format .
git add -A
git commit -m "refactor(app): drop the Click wrapper and wire the merged data layer"
```

**Files touched by this task** also include `src/life4/life4_ui.py` (Step 5).

---

## Not in this plan

**Phase 4 — DDR World requirements (Pearl → Emerald).** Transcribing 20 tiers of
requirements and substitutions verbatim from `life4ddr.com/rank-requirements`,
adding `Ruby` to `Life4RankEnum`, building a folder-average requirement class,
and removing the `range(14, 20)` hardcode from `_visualize_reqs`. This is bulk
transcription against 20 pages that have to be read as the plan is written;
planning it before reading them would produce placeholders. It gets its own plan.

**Open questions carried forward:**

1. MA point values for levels 17–19 (Task 4 makes the gap fail loudly; the
   values still need sourcing).
2. Whether `galaxy brave` should be `OPTIONAL` rather than `EXCLUDED`.
3. Whether Pearl or Topaz have requirements below level 14.
4. Marking A3-carryover requirements in the UI, for honesty about the
   divergence from official LIFE4 submission rules.
