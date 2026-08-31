# WORLD Rank Requirements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stale hand-written A20+ rank requirements with a strict parser over a vendored snapshot of LIFE4's `/api/ranks`, covering Pearl through Emerald.

**Architecture:** A pretty-printed snapshot of the full 65-sub-rank API response is committed to the repo and parsed at load into four `Requirement` classes (down from 13). The 13 collapse to two chart families the data actually has — `CountRequirement` (`song_count` present, `EARNED` pool) and `FolderRequirement` (`song_count` absent, `REQUIRED` pool) — plus `MAPointsRequirement` and `TrialRequirement`. A separate `wording` module reconstructs LIFE4's exact phrasing, pinned by a conformance fixture scraped from their site.

**Tech Stack:** Python 3.11+, pandas, pydantic, streamlit, pytest, uv, ruff.

**Spec:** `docs/superpowers/specs/2026-08-30-world-rank-requirements-design.md`

## Global Constraints

- **Scope is Pearl, Topaz, Amethyst, Emerald.** 20 sub-ranks, 583 goals. The scope filter runs **before** validation.
- **Vendor the snapshot in full** (all 65 sub-ranks), pretty-printed with `indent=2`, `sort_keys=False`, trailing newline.
- **The test suite never hits the network.** Drift detection lives in `scripts/fetch_ranks.py --check` only.
- **Strict parsing.** An unknown `t`, unknown `clear_type`, or a field combination outside the ten audited ones raises. No silent skipping.
- **Exception semantics (unified rule):** a chart passes if `lamp >= required AND score >= floor`; otherwise it may consume an exception slot if `score >= shadow_floor`. Exceptions excuse the whole requirement, not just the score.
- **Wording must be byte-exact** against LIFE4's rendered output.
- **An MFC satisfies an SDP requirement**, but contributes only MFC points to MA Points.
- Run tests with `uv run pytest`. Lint with `uv run ruff check` and `uv run ruff format`.
- Commit after every task.

## File Structure

**Create:**
- `src/life4/life4/ranks/wording.py` — `ClearType`, labels, score/article formatting, the two phrase builders. Isolated because it is what the conformance test targets.
- `src/life4/life4/ranks/parser.py` — one goal dict to one `Requirement`; strict validation.
- `src/life4/life4/ranks/registry.py` — snapshot loading, scope filter, `Life4Rank` construction.
- `src/life4/life4/ranks/data/ranks.json` — vendored snapshot.
- `scripts/fetch_ranks.py` — refresh the snapshot; `--check` compares without writing.
- `scripts/fetch_rendered_strings.py` — rebuild the conformance fixture from LIFE4's HTML.
- `tests/fixtures/life4_rendered.txt` — LIFE4's rendered requirement strings, one per line, sorted.
- `tests/test_wording.py`, `tests/test_parser.py`, `tests/test_registry.py`, `tests/test_conformance.py`

**Modify:**
- `src/life4/ddr.py` — add `get_levels_from`, `get_sdp_or_better`; drop methods no longer used.
- `src/life4/life4/core.py` — fix `Life4RankEnum` order, add `Ruby`.
- `src/life4/life4/ranks/requirements.py` — rewrite to four classes.
- `app.py` — drive the selectbox off the registry.
- `pyproject.toml` — package-data for the snapshot.
- `tests/test_requirements.py`, `tests/test_blockers.py` — rewrite against the new classes.

**Delete:**
- `src/life4/life4/ranks/a20_plus.py`

---

### Task 1: Fix the rank enum and add the SDP-or-better predicate

**Files:**
- Modify: `src/life4/life4/core.py:44-56`
- Modify: `src/life4/ddr.py:117-119`
- Test: `tests/test_requirements.py`

**Interfaces:**
- Produces: `Life4RankEnum` with correct ordering and a `Ruby` member; `DDRDataset.get_sdp_or_better(*, pool=ChartPool.EARNED) -> pd.DataFrame`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_requirements.py`:

```python
def test_rank_enum_orders_platinum_below_diamond():
    assert Life4RankEnum.Gold < Life4RankEnum.Platinum < Life4RankEnum.Diamond


def test_rank_enum_has_ruby_above_onyx():
    assert Life4RankEnum.Ruby > Life4RankEnum.Onyx


def mfc(title, level):
    return chart(
        title=title,
        level=level,
        score=1_000_000,
        perfect=0,
        record_on="1/1/2026",
        pfc_date="1/2/2026",
    )


def test_mfc_counts_as_an_sdp_for_requirements():
    d = dataset(mfc("a", 13))
    assert len(d.get_sdp_or_better()) == 1


def test_mfc_does_not_add_sdp_points_on_top_of_mfc_points():
    # A level 15 MFC is worth 15, not 15 + 1.5.
    d = dataset(mfc("a", 15))
    assert d.get_ma_points() == pytest.approx(15.0)


def test_pfc_with_ten_perfects_is_not_sdp_or_better():
    d = dataset(pfc("a", 14, 10))
    assert len(d.get_sdp_or_better()) == 0
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_requirements.py -k "rank_enum or sdp_or_better or mfc" -v`
Expected: FAIL — `AttributeError: Ruby`, `AttributeError: get_sdp_or_better`.

- [ ] **Step 3: Fix the enum**

In `src/life4/life4/core.py`, replace the `Life4RankEnum` body:

```python
class Life4RankEnum(IntEnum):
    Copper = 0
    Bronze = 1
    Silver = 2
    Gold = 3
    Platinum = 4
    Diamond = 5
    Cobalt = 6
    Pearl = 7
    Topaz = 8
    Amethyst = 9
    Emerald = 10
    Onyx = 11
    Ruby = 12
```

Note the swap: `Platinum` was 5 and `Diamond` 4. `TrialRequirement` compares
these with `>=`, so the old order made "Diamond or above" accept a Platinum
trial.

- [ ] **Step 4: Add the predicate**

In `src/life4/ddr.py`, below `get_sdps`:

```python
    def get_sdp_or_better(
        self, *, pool: ChartPool = ChartPool.EARNED
    ) -> pd.DataFrame:
        """Charts that satisfy an "SDP" requirement.

        An MFC is a full combo with zero Perfects, and zero is a single digit,
        so every MFC is an SDP and a strictly better one. Lamps are mutually
        exclusive (a 1,000,000 is White, never Gold), so the MFC case has to be
        named explicitly or "SDP a 13+" is unsatisfiable by the best possible
        score at that level.

        Deliberately separate from get_sdps(), which backs the MA Points table.
        That table is a scoring lookup, not a predicate: a chart falls in
        exactly one row, and an MFC takes the MFC value.
        """
        charts = self.charts(pool)
        return charts[
            (charts["lamp"] >= Lamp.Gold)
            & ((charts["perfect"] < 10) | (charts["lamp"] == Lamp.White))
        ]
```

- [ ] **Step 5: Run to verify they pass**

Run: `uv run pytest tests/test_requirements.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/life4/life4/core.py src/life4/ddr.py tests/test_requirements.py
git commit -m "fix: correct Platinum/Diamond rank order, add Ruby and SDP-or-better"
```

---

### Task 2: The wording module

**Files:**
- Create: `src/life4/life4/ranks/wording.py`
- Test: `tests/test_wording.py`

**Interfaces:**
- Produces: `ClearType` (str-valued `Enum`), `CLEAR_TYPE_LABELS`, `LAMP_FOR_CLEAR_TYPE`, `article(level) -> str`, `format_score(value) -> str`, `exception_clause(exceptions, exception_floor) -> str`, `count_phrase(...) -> str`, `folder_phrase(...) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wording.py`:

```python
import pytest

from life4.life4.ranks.wording import (
    ClearType,
    article,
    count_phrase,
    exception_clause,
    folder_phrase,
    format_score,
)


@pytest.mark.parametrize(
    "level,expected", [(8, "an"), (11, "an"), (18, "an"), (14, "a"), (19, "a")]
)
def test_article_matches_life4_usage(level, expected):
    assert article(level) == expected


def test_round_thousands_render_as_k():
    assert format_score(996_000) == "996k"


def test_non_round_scores_render_with_separators():
    assert format_score(998_500) == "998,500"


def test_exception_clause_omits_absent_shadow_floor():
    assert exception_clause(1, None) == " (1E)"
    assert exception_clause(14, 980_000) == " (14E, 980k)"
    assert exception_clause(0, None) == ""


def test_990k_renders_as_aaa():
    assert count_phrase(level=15, count=120, min_score=990_000) == "AAA 120 15s"
    assert count_phrase(level=12, count=1, min_score=990_000) == "AAA a 12"


def test_scored_count_without_exceptions_leads_with_the_score():
    # LIFE4 renders this as "750k+ 5 18s", NOT "Clear 5 18s over 750k".
    # The "Clear N over X" template is selected by the presence of
    # exceptions, not by the count.
    assert count_phrase(level=18, count=5, min_score=750_000) == "750k+ 5 18s"
    assert count_phrase(level=14, count=1, min_score=960_000) == "960k+ a 14"


def test_scored_count_with_exceptions_uses_the_clear_over_template():
    assert (
        count_phrase(
            level=18, count=26, min_score=810_000, exceptions=6,
            exception_floor=760_000,
        )
        == "Clear 26 18s over 810k (6E, 760k)"
    )


def test_clear_type_counts_use_the_abbreviation():
    assert count_phrase(level=14, count=60, clear_type=ClearType.PERFECT) == "PFC 60 14s"
    assert (
        count_phrase(level=13, count=1, clear_type=ClearType.SDP, higher_diff=True)
        == "SDP a 13+"
    )
    assert (
        count_phrase(level=11, count=3, clear_type=ClearType.MARVELOUS, higher_diff=True)
        == "MFC 3 11+s"
    )


def test_bare_counts_say_clear():
    assert count_phrase(level=19, count=1) == "Clear a 19"
    assert count_phrase(level=15, count=2) == "Clear 2 15s"


def test_folder_phrases_spell_the_lamp_out_in_full():
    assert (
        folder_phrase(
            level=14, clear_type=ClearType.GOOD, min_score=991_000,
            exceptions=14, exception_floor=980_000,
        )
        == "Full Combo all 14s over 991k (14E, 980k)"
    )
    assert (
        folder_phrase(
            level=15, clear_type=ClearType.LIFE4, min_score=980_000,
            exceptions=19, exception_floor=955_000,
        )
        == "LIFE4 Clear all 15s over 980k (19E, 955k)"
    )
    assert (
        folder_phrase(level=16, min_score=955_000, exceptions=24, exception_floor=910_000)
        == "Clear all 16s over 955k (24E, 910k)"
    )


def test_folder_average_phrase():
    assert (
        folder_phrase(
            level=14, clear_type=ClearType.PERFECT, average_score=999_500,
            exceptions=4, exception_floor=996_000,
        )
        == "PFC all 14s with a 999,500 Folder Average (4E, 996k)"
    )
    assert (
        folder_phrase(level=14, clear_type=ClearType.PERFECT, average_score=999_700)
        == "PFC all 14s with a 999,700 Folder Average"
    )
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_wording.py -v`
Expected: FAIL — `ModuleNotFoundError: life4.life4.ranks.wording`.

- [ ] **Step 3: Write the module**

Create `src/life4/life4/ranks/wording.py`:

```python
"""Reconstructs LIFE4's exact requirement wording from the API's goal fields.

The API discards vocabulary the display has to put back: `score: 990000` is
rendered "AAA", `clear_type: "life4"` is "LIFE4 Clear", `song_count: 1` picks
an article. Every rule here is verified against LIFE4's own rendered output by
tests/test_conformance.py -- change nothing in this module without re-running
it.
"""

from enum import Enum

from life4.ddr import Lamp


class ClearType(str, Enum):
    """The API's `clear_type` vocabulary. `sdp` is not a lamp."""

    GOOD = "good"
    LIFE4 = "life4"
    GREAT = "great"
    PERFECT = "perfect"
    MARVELOUS = "marvelous"
    SDP = "sdp"


#: How LIFE4 writes each clear type in a requirement. Note these are the
#: requirement-line spellings, which abbreviate PFC and MFC but spell out
#: "Full Combo" and "Great Full Combo" -- not the same as ddr.LAMP_LABELS,
#: which names lamps for the blocker table.
CLEAR_TYPE_LABELS = {
    ClearType.GOOD: "Full Combo",
    ClearType.LIFE4: "LIFE4 Clear",
    ClearType.GREAT: "Great Full Combo",
    ClearType.PERFECT: "PFC",
    ClearType.MARVELOUS: "MFC",
    ClearType.SDP: "SDP",
}

#: SDP is absent on purpose: it is a predicate over perfect counts, not a
#: lamp, and it never appears on a folder goal.
LAMP_FOR_CLEAR_TYPE = {
    ClearType.GOOD: Lamp.Blue,
    ClearType.LIFE4: Lamp.Red,
    ClearType.GREAT: Lamp.Green,
    ClearType.PERFECT: Lamp.Gold,
    ClearType.MARVELOUS: Lamp.White,
}

#: A "AAA" is not a concept in the API -- it is this number.
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
    # not by the count. Without exceptions LIFE4 writes "750k+ 5 18s".
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_wording.py -v`
Expected: PASS, 12 tests.

- [ ] **Step 5: Commit**

```bash
git add src/life4/life4/ranks/wording.py tests/test_wording.py
git commit -m "feat: add wording module reproducing LIFE4 requirement phrasing"
```

---

### Task 3: `CountRequirement`

**Files:**
- Modify: `src/life4/ddr.py`
- Modify: `src/life4/life4/ranks/requirements.py`
- Test: `tests/test_requirements.py`

**Interfaces:**
- Consumes: `wording.ClearType`, `wording.count_phrase`, `wording.LAMP_FOR_CLEAR_TYPE`, `DDRDataset.get_sdp_or_better`.
- Produces: `DDRDataset.get_levels_from(level, *, pool)`; `CountRequirement(level, count, *, clear_type=None, min_score=None, higher_diff=False, exceptions=0, exception_floor=None)` with `.is_satisfied`, `.display_str`, `.get_progress`, `.blockers`, `.multiple_levels`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_requirements.py` (replacing the `ClearRequirement`, `PFCRequirement`, `AAARequirement`, `CeilingRequirement`, `MFC*`, `SDP*` tests):

```python
from life4.life4.ranks.requirements import CountRequirement
from life4.life4.ranks.wording import ClearType


def test_bare_count_ignores_unplayed_charts():
    d = dataset(
        played("a", 19, 720_000),
        played("b", 19, 810_000),
        *[chart(title=str(i), level=19) for i in range(8)],
    )
    assert CountRequirement(level=19, count=1).is_satisfied(d)
    assert not CountRequirement(level=19, count=5).is_satisfied(d)
    assert CountRequirement(level=19, count=5).get_progress(d) == "2/5"


def test_min_score_counts_only_charts_above_it():
    d = dataset(played("a", 18, 900_000), played("b", 18, 700_000))
    assert CountRequirement(level=18, count=1, min_score=810_000).is_satisfied(d)
    assert not CountRequirement(level=18, count=2, min_score=810_000).is_satisfied(d)


def test_exceptions_fill_the_gap_up_to_the_limit():
    d = dataset(
        played("a", 18, 900_000),
        played("b", 18, 780_000),
        played("c", 18, 770_000),
    )
    req = CountRequirement(
        level=18, count=3, min_score=810_000, exceptions=1, exception_floor=760_000
    )
    assert not req.is_satisfied(d)
    assert req.get_progress(d) == "2/3"


def test_exceptions_below_the_shadow_floor_do_not_count():
    d = dataset(played("a", 18, 900_000), played("b", 18, 700_000))
    req = CountRequirement(
        level=18, count=2, min_score=810_000, exceptions=1, exception_floor=760_000
    )
    assert not req.is_satisfied(d)


def test_lamp_count_accepts_better_lamps():
    d = dataset(pfc("a", 16, 3), mfc("b", 16))
    assert CountRequirement(level=16, count=2, clear_type=ClearType.PERFECT).is_satisfied(d)


def test_higher_diff_counts_charts_at_and_above_the_level():
    d = dataset(mfc("a", 11), mfc("b", 14), mfc("c", 9))
    req = CountRequirement(
        level=11, count=2, clear_type=ClearType.MARVELOUS, higher_diff=True
    )
    assert req.is_satisfied(d)
    assert req.get_progress(d) == "2/2"


def test_sdp_count_accepts_an_mfc():
    d = dataset(mfc("a", 13))
    req = CountRequirement(
        level=13, count=1, clear_type=ClearType.SDP, higher_diff=True
    )
    assert req.is_satisfied(d)


def test_higher_diff_requirements_group_under_other():
    assert CountRequirement(
        level=13, count=1, clear_type=ClearType.SDP, higher_diff=True
    ).multiple_levels
    assert not CountRequirement(level=16, count=8, clear_type=ClearType.PERFECT).multiple_levels


def test_display_str_appends_progress_only_when_unsatisfied():
    d = dataset(played("a", 18, 900_000))
    assert CountRequirement(level=18, count=1).display_str(d) == "Clear a 18"
    assert CountRequirement(level=18, count=3).display_str(d) == "Clear 3 18s (1/3)"


def test_clear_type_and_exceptions_never_co_occur():
    # Verified against all 583 in-scope goals; guard so a future snapshot
    # that breaks the invariant fails loudly rather than being mis-evaluated.
    with pytest.raises(ValueError):
        CountRequirement(
            level=16, count=8, clear_type=ClearType.PERFECT, exceptions=2
        )
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_requirements.py -k count -v`
Expected: FAIL — `ImportError: cannot import name 'CountRequirement'`.

- [ ] **Step 3: Add the dataset accessor**

In `src/life4/ddr.py`, below `get_level`:

```python
    def get_levels_from(
        self, level: int, *, pool: ChartPool = ChartPool.EARNED
    ) -> pd.DataFrame:
        """Charts at this level or harder -- the API's `higher_diff` flag."""
        charts = self.charts(pool)
        return charts[charts["level"] >= level]
```

- [ ] **Step 4: Write `CountRequirement`**

In `src/life4/life4/ranks/requirements.py`, keep the `Requirement` ABC,
`_song_labels` and `_sorted_by_song` helpers, and add:

```python
class CountRequirement(Requirement):
    """At least N charts at a level (or above) satisfy a predicate.

    Absorbs what used to be PFCRequirement, AAARequirement, ClearRequirement,
    CeilingRequirement, MFC/SDPRequirement and MFC/SDPCountRequirement. "AAA"
    is not a concept in the API -- it is min_score=990_000; a "ceiling" is this
    class with count=1.

    Pool is EARNED: a chart removed from the game still credits the score you
    earned on it.
    """

    pool = ChartPool.EARNED

    def __init__(
        self,
        level: int,
        count: int,
        *,
        clear_type: ClearType | None = None,
        min_score: int | None = None,
        higher_diff: bool = False,
        exceptions: int = 0,
        exception_floor: int | None = None,
    ):
        if clear_type is not None and exceptions:
            raise ValueError(
                "clear_type and exceptions never co-occur in the LIFE4 data; "
                "refusing to guess how they interact"
            )
        self.level = level
        self.count = count
        self.clear_type = clear_type
        self.min_score = min_score
        self.higher_diff = higher_diff
        self.exceptions = exceptions
        self.exception_floor = exception_floor
        # A "d+" goal spans levels, so the UI groups it under "Other" rather
        # than beneath a single difficulty heading.
        self.multiple_levels = higher_diff

    def __str__(self):
        return count_phrase(
            level=self.level,
            count=self.count,
            clear_type=self.clear_type,
            min_score=self.min_score,
            higher_diff=self.higher_diff,
            exceptions=self.exceptions,
            exception_floor=self.exception_floor,
        )

    def _charts(self, data: "DDRDataset") -> pd.DataFrame:
        if self.higher_diff:
            return data.get_levels_from(self.level, pool=self.pool)
        return data.get_level(self.level, pool=self.pool)

    def _qualifying(self, data: "DDRDataset") -> int:
        if self.clear_type is ClearType.SDP:
            sdps = data.get_sdp_or_better(pool=self.pool)
            if self.higher_diff:
                return int((sdps["level"] >= self.level).sum())
            return int((sdps["level"] == self.level).sum())

        charts = self._charts(data)
        if self.clear_type is not None:
            lamp = LAMP_FOR_CLEAR_TYPE[self.clear_type]
            return int((charts["lamp"] >= lamp).sum())

        scores = charts["score"].dropna()
        if self.min_score is None:
            return len(scores)

        over = scores[scores >= self.min_score]
        if len(over) >= self.count or not self.exceptions:
            return len(over)

        slack = scores[
            (scores >= self.exception_floor) & (scores < self.min_score)
        ]
        return len(over) + min(len(slack), self.exceptions)

    def is_satisfied(self, data: "DDRDataset") -> bool:
        return self._qualifying(data) >= self.count

    def get_progress(self, data: "DDRDataset") -> str:
        return f"{self._qualifying(data)}/{self.count}"

    def display_str(self, data: "DDRDataset") -> str:
        if self.is_satisfied(data):
            return str(self)
        return f"{self} ({self.get_progress(data)})"
```

`blockers()` is inherited from `Requirement` and returns an empty frame: a
count requirement has no denominator, so there is no specific chart to name.

Add the imports at the top of the module:

```python
from life4.life4.ranks.wording import (
    LAMP_FOR_CLEAR_TYPE,
    ClearType,
    count_phrase,
    folder_phrase,
)
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/test_requirements.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/life4/ddr.py src/life4/life4/ranks/requirements.py tests/test_requirements.py
git commit -m "feat: add CountRequirement, collapsing six requirement classes"
```

---

### Task 4: `FolderRequirement`

**Files:**
- Modify: `src/life4/life4/ranks/requirements.py`
- Test: `tests/test_requirements.py`, `tests/test_blockers.py`

**Interfaces:**
- Consumes: `wording.folder_phrase`, `wording.LAMP_FOR_CLEAR_TYPE`, `ddr.LAMP_LABELS`.
- Produces: `FolderRequirement(level, *, clear_type=None, min_score=None, average_score=None, exceptions=0, exception_floor=None)`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_requirements.py`:

```python
from life4.life4.ranks.requirements import FolderRequirement


def fc(title, level, score):
    return chart(
        title=title, level=level, score=score,
        record_on="1/1/2026", fc_date="1/2/2026",
    )


def test_unplayed_chart_fails_a_folder_requirement():
    d = dataset(played("a", 16, 999_000), chart(title="b", level=16))
    assert not FolderRequirement(level=16, min_score=955_000).is_satisfied(d)


def test_folder_passes_when_every_chart_clears_the_floor():
    d = dataset(played("a", 16, 960_000), played("b", 16, 999_000))
    assert FolderRequirement(level=16, min_score=955_000).is_satisfied(d)


def test_exception_excuses_the_lamp_not_just_the_score():
    # The unified rule: a chart failing the lamp condition may still take an
    # exception slot if it clears the shadow floor. Under the old
    # lamp-absolute reading this would fail.
    d = dataset(fc("a", 14, 995_000), played("b", 14, 985_000))
    req = FolderRequirement(
        level=14, clear_type=ClearType.GOOD, min_score=991_000,
        exceptions=1, exception_floor=980_000,
    )
    assert req.is_satisfied(d)


def test_a_chart_below_the_shadow_floor_cannot_be_excused():
    d = dataset(fc("a", 14, 995_000), played("b", 14, 970_000))
    req = FolderRequirement(
        level=14, clear_type=ClearType.GOOD, min_score=991_000,
        exceptions=1, exception_floor=980_000,
    )
    assert not req.is_satisfied(d)


def test_exception_budget_is_finite():
    d = dataset(
        fc("a", 14, 995_000),
        played("b", 14, 985_000),
        played("c", 14, 985_000),
    )
    req = FolderRequirement(
        level=14, clear_type=ClearType.GOOD, min_score=991_000,
        exceptions=1, exception_floor=980_000,
    )
    assert not req.is_satisfied(d)


def test_folder_average_includes_the_exception_charts():
    # Two PFCs at 999,900 and one non-PFC exception at 996,000.
    # mean = 998,600, which is below the 999,500 target.
    d = dataset(pfc("a", 14, 10), pfc("b", 14, 10), played("c", 14, 996_000))
    req = FolderRequirement(
        level=14, clear_type=ClearType.PERFECT, average_score=999_500,
        exceptions=1, exception_floor=996_000,
    )
    assert not req.is_satisfied(d)


def test_folder_average_passes_when_the_mean_clears_the_target():
    d = dataset(pfc("a", 14, 1), pfc("b", 14, 1))
    req = FolderRequirement(
        level=14, clear_type=ClearType.PERFECT, average_score=999_500
    )
    assert req.is_satisfied(d)


def test_folder_average_progress_reports_both_conditions():
    d = dataset(pfc("a", 14, 10), played("b", 14, 900_000))
    req = FolderRequirement(
        level=14, clear_type=ClearType.PERFECT, average_score=999_500
    )
    progress = req.get_progress(d)
    assert "Lamp 1/2" in progress
    assert "Avg" in progress
```

Add to `tests/test_blockers.py`:

```python
def test_folder_blockers_name_the_failing_charts():
    d = dataset(
        played("aaa", 16, 999_000),
        played("bbb", 16, 900_000),
        chart(title="ccc", level=16),
    )
    blockers = FolderRequirement(level=16, min_score=955_000).blockers(d)
    assert list(blockers["song"]) == ["bbb", "ccc"]
    assert list(blockers["needs"]) == ["+55,000", "unplayed"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_requirements.py tests/test_blockers.py -k folder -v`
Expected: FAIL — `ImportError: cannot import name 'FolderRequirement'`.

- [ ] **Step 3: Write `FolderRequirement`**

```python
class FolderRequirement(Requirement, ProgressDisplay):
    """Every chart at a level satisfies a predicate, minus exceptions.

    Absorbs LampRequirement, FloorRequirement and LampFloorRequirement, and
    adds the Folder Average case.

    Pool is REQUIRED: an optional chart must never appear here, or an
    unplayable chart blocks the requirement forever.

    Exception semantics are unified -- an exception excuses a chart from the
    *whole* requirement (lamp included) provided it clears the shadow floor,
    rather than excusing only the score while holding the lamp absolute. The
    evidence is "PFC all 14s with a 999,500 Folder Average (4E, 996k)": a PFC
    scores exactly 1,000,000 - 10 x perfects, so a PFC below 996,000 needs
    more than 400 Perfects on one chart. Under a lamp-absolute reading that
    clause excuses something that essentially cannot happen -- dead syntax.
    """

    multiple_levels = False
    pool = ChartPool.REQUIRED

    def __init__(
        self,
        level: int,
        *,
        clear_type: ClearType | None = None,
        min_score: int | None = None,
        average_score: int | None = None,
        exceptions: int = 0,
        exception_floor: int | None = None,
    ):
        if (min_score is None) == (average_score is None):
            raise ValueError(
                "a folder requirement takes exactly one of min_score or "
                "average_score"
            )
        self.level = level
        self.clear_type = clear_type
        self.min_score = min_score
        self.average_score = average_score
        self.exceptions = exceptions
        self.exception_floor = exception_floor

    def __str__(self):
        return folder_phrase(
            level=self.level,
            clear_type=self.clear_type,
            min_score=self.min_score,
            average_score=self.average_score,
            exceptions=self.exceptions,
            exception_floor=self.exception_floor,
        )

    def _charts(self, data: "DDRDataset") -> pd.DataFrame:
        return data.get_level(self.level, pool=self.pool)

    def _lamp_ok(self, charts: pd.DataFrame) -> pd.Series:
        if self.clear_type is None:
            return pd.Series(True, index=charts.index)
        return charts["lamp"] >= LAMP_FOR_CLEAR_TYPE[self.clear_type]

    def _score_ok(self, charts: pd.DataFrame) -> pd.Series:
        if self.min_score is None:
            return charts["score"].notna()
        return charts["score"] >= self.min_score

    def _failing(self, charts: pd.DataFrame) -> pd.DataFrame:
        return charts[~(self._lamp_ok(charts) & self._score_ok(charts))]

    def is_satisfied(self, data: "DDRDataset") -> bool:
        charts = self._charts(data)
        if charts["score"].isna().any():
            return False

        failing = self._failing(charts)
        if len(failing) > self.exceptions:
            return False
        if self.exception_floor is not None and not failing.empty:
            if (failing["score"] < self.exception_floor).any():
                return False

        if self.average_score is not None:
            if charts["score"].mean() < self.average_score:
                return False
        return True

    def get_progress(self, data: "DDRDataset") -> str:
        charts = self._charts(data)
        total = len(charts)
        parts = []
        if self.clear_type is not None:
            passing = int(self._lamp_ok(charts).sum())
            if passing < total:
                parts.append(f"Lamp {passing}/{total}")
        if self.min_score is not None:
            passing = int(self._score_ok(charts).sum())
            if passing < total:
                parts.append(f"Floor {passing}/{total}")
        if self.average_score is not None:
            mean = charts["score"].mean()
            mean_str = "-" if pd.isna(mean) else f"{mean:,.0f}"
            parts.append(f"Avg {mean_str}/{self.average_score:,}")
        if not parts:
            return f"{total}/{total}"
        return "; ".join(parts)

    def display_str(self, data: "DDRDataset") -> str:
        if self.is_satisfied(data):
            return str(self)
        return f"{self} ({self.get_progress(data)})"

    def blockers(self, data: "DDRDataset") -> pd.DataFrame:
        charts = self._charts(data).copy()
        charts["song"] = _song_labels(charts)
        failing = self._failing(charts)

        needs = []
        for _, row in failing.iterrows():
            if pd.isna(row["score"]):
                needs.append("unplayed")
            elif self.min_score is not None and row["score"] < self.min_score:
                needs.append(f"+{self.min_score - row['score']:,.0f}")
            else:
                required = LAMP_FOR_CLEAR_TYPE[self.clear_type]
                have = LAMP_LABELS[Lamp(row["lamp"])]
                needs.append(f"{have} -> {LAMP_LABELS[required]}")

        out = failing[["song", "score"]].copy()
        out["needs"] = needs
        return _sorted_by_song(out[list(self.BLOCKER_COLUMNS)])
```

- [ ] **Step 4: Delete the superseded classes**

Remove `LampRequirement`, `PFCRequirement`, `AAARequirement`, `ClearRequirement`, `CeilingRequirement`, `FloorRequirement`, `LampFloorRequirement`, `SDPRequirement`, `SDPCountRequirement`, `MFCRequirement`, `MFCCountRequirement` from `requirements.py`. Keep `MAPointsRequirement` and `TrialRequirement` unchanged.

- [ ] **Step 5: Rewrite `tests/test_blockers.py` against the new classes**

This is a real rewrite, not an import fix: the file is 175 lines with 28
references to the deleted classes. Every `FloorRequirement`,
`LampRequirement` and `LampFloorRequirement` case becomes a
`FolderRequirement` case, and the three separate blocker behaviours collapse
into one method, so the tests that asserted the old dedup-across-two-frames
behaviour no longer describe anything real -- delete those rather than
translating them.

Preserve these behaviours, which the spec keeps unchanged:

- unplayed charts render `needs` as `"unplayed"`
- a chart below the floor renders `+N` with thousands separators
- a chart failing only the lamp renders `"<have> -> <required>"` using
  `LAMP_LABELS`
- rows are sorted case-insensitively by song title, not by score
- titles are disambiguated by difficulty only where a title repeats at a level

Add one case that could not exist before, since the two conditions used to be
evaluated by separate objects:

```python
def test_a_chart_failing_both_conditions_appears_once():
    d = dataset(played("aaa", 14, 900_000))
    req = FolderRequirement(
        level=14, clear_type=ClearType.GOOD, min_score=991_000,
        exceptions=0, exception_floor=None,
    )
    blockers = req.blockers(d)
    assert len(blockers) == 1
    # The score gap is the actionable number, so it wins over the lamp label.
    assert blockers.loc[0, "needs"] == "+91,000"
```

`tests/test_lamps.py` needs no changes -- it exercises `Lamp` and
`LAMP_LABELS` directly and never touches a requirement class.

- [ ] **Step 5b: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/life4/life4/ranks/requirements.py tests/
git commit -m "feat: add FolderRequirement with unified exception semantics"
```

---

### Task 5: Vendor the snapshot and the fetch script

**Files:**
- Create: `scripts/fetch_ranks.py`, `src/life4/life4/ranks/data/ranks.json`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `scripts/fetch_ranks.py` with `--check`; `SNAPSHOT_PATH` importable from `life4.life4.ranks.registry` (Task 7).

- [ ] **Step 1: Write the script**

Create `scripts/fetch_ranks.py`:

```python
"""Refresh the vendored LIFE4 rank-requirements snapshot.

    uv run scripts/fetch_ranks.py            # rewrite the snapshot
    uv run scripts/fetch_ranks.py --check    # exit 1 if live differs

The snapshot is what the app parses. Fetching live at runtime would make the
dashboard depend on someone else's uptime and let thresholds change with no
diff to review; vendoring turns a LIFE4 patch into a reviewable commit.
"""

import argparse
import json
import sys
from pathlib import Path

import requests

API_URL = "https://life4ddr.com/api/ranks"
SNAPSHOT = (
    Path(__file__).resolve().parent.parent
    / "src/life4/life4/ranks/data/ranks.json"
)


def render(payload) -> str:
    return json.dumps(payload, indent=2) + "\n"


def fetch() -> str:
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    return render(response.json())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare live against the snapshot without writing; exit 1 on drift",
    )
    args = parser.parse_args()

    live = fetch()
    if args.check:
        current = SNAPSHOT.read_text() if SNAPSHOT.exists() else ""
        if live == current:
            print(f"up to date ({len(json.loads(live))} sub-ranks)")
            return 0
        print(
            f"DRIFT: {API_URL} differs from {SNAPSHOT.relative_to(Path.cwd())}.\n"
            "Run without --check and review the diff.",
            file=sys.stderr,
        )
        return 1

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(live)
    print(f"wrote {SNAPSHOT} ({len(json.loads(live))} sub-ranks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Fetch the snapshot**

Run: `uv run scripts/fetch_ranks.py`
Expected: `wrote .../ranks.json (65 sub-ranks)`

- [ ] **Step 3: Verify `--check` is clean**

Run: `uv run scripts/fetch_ranks.py --check`
Expected: `up to date (65 sub-ranks)`, exit 0.

- [ ] **Step 4: Ship the snapshot with the package**

Add to `pyproject.toml` after the `[tool.setuptools.packages.find]` block:

```toml
[tool.setuptools.package-data]
"life4.life4.ranks" = ["data/*.json"]
```

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_ranks.py src/life4/life4/ranks/data/ranks.json pyproject.toml
git commit -m "feat: vendor LIFE4 ranks snapshot with refresh and drift-check script"
```

---

### Task 6: The goal parser

**Files:**
- Create: `src/life4/life4/ranks/parser.py`
- Test: `tests/test_parser.py`

**Interfaces:**
- Consumes: `CountRequirement`, `FolderRequirement`, `MAPointsRequirement`, `TrialRequirement`, `ClearType`, `Life4RankEnum`.
- Produces: `parse_goal(goal: dict) -> Requirement`, `GoalParseError`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_parser.py`:

```python
import pytest

from life4.life4.core import Life4RankEnum
from life4.life4.ranks.parser import GoalParseError, parse_goal
from life4.life4.ranks.requirements import (
    CountRequirement,
    FolderRequirement,
    MAPointsRequirement,
    TrialRequirement,
)


def test_count_goal_with_score():
    req = parse_goal({"t": "songs", "d": 18, "score": 960000, "song_count": 1})
    assert isinstance(req, CountRequirement)
    assert str(req) == "960k+ an 18"


def test_count_goal_with_clear_type_and_higher_diff():
    req = parse_goal(
        {"t": "songs", "d": 13, "clear_type": "sdp", "song_count": 1,
         "higher_diff": True}
    )
    assert str(req) == "SDP a 13+"
    assert req.multiple_levels


def test_folder_goal():
    req = parse_goal(
        {"t": "songs", "d": 15, "clear_type": "life4", "score": 980000,
         "exceptions": 19, "exception_score": 955000}
    )
    assert isinstance(req, FolderRequirement)
    assert str(req) == "LIFE4 Clear all 15s over 980k (19E, 955k)"


def test_folder_average_goal():
    req = parse_goal(
        {"t": "songs", "d": 14, "clear_type": "perfect", "average_score": 999500,
         "exceptions": 4, "exception_score": 996000}
    )
    assert str(req) == "PFC all 14s with a 999,500 Folder Average (4E, 996k)"


def test_ma_points_goal():
    req = parse_goal({"t": "ma_points", "points": 12})
    assert isinstance(req, MAPointsRequirement)
    assert str(req) == "MA Points: 12"


def test_trial_goal():
    req = parse_goal({"t": "trial", "rank": "amethyst", "count": 1})
    assert isinstance(req, TrialRequirement)
    assert req.rank is Life4RankEnum.Amethyst
    assert str(req) == "Earn Amethyst or above on 1 Trial"


def test_id_is_ignored():
    parse_goal({"t": "songs", "d": 18, "score": 960000, "song_count": 1, "id": 42})


def test_unknown_goal_type_raises():
    with pytest.raises(GoalParseError, match="calories"):
        parse_goal({"t": "calories", "count": 800})


def test_unknown_clear_type_raises():
    with pytest.raises(GoalParseError, match="quadruple"):
        parse_goal({"t": "songs", "d": 14, "clear_type": "quadruple", "song_count": 1})


def test_unknown_field_raises():
    with pytest.raises(GoalParseError, match="stamina_bonus"):
        parse_goal(
            {"t": "songs", "d": 14, "song_count": 1, "stamina_bonus": True}
        )
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the parser**

Create `src/life4/life4/ranks/parser.py`:

```python
"""One LIFE4 API goal dict -> one Requirement.

Strict on purpose. An unknown goal type, clear type or field is a hard
failure, matching data/schema.py's stance that silent wrongness is the failure
mode this layer exists to prevent.

Strictness is cheap here because the input is a vendored snapshot: a new field
can only appear when someone re-runs scripts/fetch_ranks.py and is already
reading a diff, never spontaneously in production.
"""

from life4.life4.core import Life4RankEnum
from life4.life4.ranks.requirements import (
    CountRequirement,
    FolderRequirement,
    MAPointsRequirement,
    Requirement,
    TrialRequirement,
)
from life4.life4.ranks.wording import ClearType

#: Fields the songs parser understands. `id` is LIFE4's own key; we ignore it.
_SONG_FIELDS = frozenset(
    {
        "t", "id", "d", "higher_diff", "clear_type", "song_count",
        "score", "exceptions", "exception_score", "average_score",
    }
)


class GoalParseError(Exception):
    """A goal in the snapshot does not match any shape this app understands."""


def _clear_type(goal: dict) -> ClearType | None:
    raw = goal.get("clear_type")
    if raw is None:
        return None
    try:
        return ClearType(raw)
    except ValueError:
        raise GoalParseError(
            f"unknown clear_type {raw!r} in goal {goal!r}. Known types: "
            f"{', '.join(sorted(c.value for c in ClearType))}."
        ) from None


def _parse_songs(goal: dict) -> Requirement:
    unknown = set(goal) - _SONG_FIELDS
    if unknown:
        raise GoalParseError(
            f"unknown field(s) {sorted(unknown)} in goal {goal!r}. Add support "
            f"in life4/life4/ranks/parser.py rather than ignoring them."
        )

    clear_type = _clear_type(goal)
    exceptions = goal.get("exceptions", 0)
    exception_floor = goal.get("exception_score")

    if "song_count" in goal:
        return CountRequirement(
            level=goal["d"],
            count=goal["song_count"],
            clear_type=clear_type,
            min_score=goal.get("score"),
            higher_diff=goal.get("higher_diff", False),
            exceptions=exceptions,
            exception_floor=exception_floor,
        )

    return FolderRequirement(
        level=goal["d"],
        clear_type=clear_type,
        min_score=goal.get("score"),
        average_score=goal.get("average_score"),
        exceptions=exceptions,
        exception_floor=exception_floor,
    )


def _parse_trial(goal: dict) -> Requirement:
    name = goal["rank"].capitalize()
    try:
        rank = Life4RankEnum[name]
    except KeyError:
        raise GoalParseError(f"unknown trial rank {goal['rank']!r}") from None
    return TrialRequirement(rank=rank, num=goal["count"])


def parse_goal(goal: dict) -> Requirement:
    kind = goal.get("t")
    if kind == "songs":
        return _parse_songs(goal)
    if kind == "ma_points":
        return MAPointsRequirement(points=goal["points"])
    if kind == "trial":
        return _parse_trial(goal)
    raise GoalParseError(
        f"unsupported goal type {kind!r} in {goal!r}. 'set' and 'calories' "
        f"goals appear only in Copper-Silver, which are out of scope; if you "
        f"widened the scope, they need an unverifiable-requirement concept "
        f"first."
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_parser.py -v`
Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
git add src/life4/life4/ranks/parser.py tests/test_parser.py
git commit -m "feat: add strict goal parser for the LIFE4 ranks snapshot"
```

---

### Task 7: The registry

**Files:**
- Create: `src/life4/life4/ranks/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: `parse_goal`, `Life4Rank`, `Life4RankEnum`.
- Produces: `IN_SCOPE: tuple[Life4RankEnum, ...]`, `load_ranks() -> dict[Life4RankEnum, list[Life4Rank]]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_registry.py`:

```python
from life4.life4.core import Life4RankEnum
from life4.life4.ranks.registry import IN_SCOPE, load_ranks


def test_scope_is_pearl_through_emerald():
    assert IN_SCOPE == (
        Life4RankEnum.Pearl,
        Life4RankEnum.Topaz,
        Life4RankEnum.Amethyst,
        Life4RankEnum.Emerald,
    )


def test_every_in_scope_tier_has_five_subranks():
    ranks = load_ranks()
    assert set(ranks) == set(IN_SCOPE)
    for tier, subranks in ranks.items():
        assert [r.subrank for r in subranks] == [1, 2, 3, 4, 5], tier


def test_out_of_scope_tiers_are_filtered_before_validation():
    # Copper carries `calories` and `set` goals the parser rejects. If the
    # filter ran after validation this call would raise.
    load_ranks()


def test_amethyst_one_matches_the_published_requirements():
    amethyst = load_ranks()[Life4RankEnum.Amethyst][0]
    rendered = [str(r) for r in amethyst.requirements]
    assert rendered == [
        "Full Combo all 14s over 991k (14E, 980k)",
        "PFC 60 14s",
        "LIFE4 Clear all 15s over 980k (19E, 955k)",
        "PFC 26 15s",
        "AAA 120 15s",
        "Clear all 16s over 955k (24E, 910k)",
        "PFC 8 16s",
        "AAA 60 16s",
        "Clear all 17s over 910k (19E, 860k)",
        "AAA 12 17s",
        "Clear 26 18s over 810k (6E, 760k)",
        "960k+ an 18",
        "MFC a 6+",
        "SDP a 13+",
        "MA Points: 6",
        "Earn Topaz or above on 1 Trial",
    ]


def test_emerald_five_has_substitutions():
    emerald_5 = load_ranks()[Life4RankEnum.Emerald][4]
    assert emerald_5.substitutions
    assert "PFC all 14s with a 999,700 Folder Average" in [
        str(s) for s in emerald_5.substitutions
    ]


def test_total_in_scope_goal_count():
    ranks = load_ranks()
    total = sum(
        len(r.requirements) + len(r.substitutions)
        for subranks in ranks.values()
        for r in subranks
    )
    assert total == 583
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the registry**

Create `src/life4/life4/ranks/registry.py`:

```python
"""Loads the vendored LIFE4 snapshot into Life4Rank objects.

Only the in-scope tiers are parsed. The filter runs *before* validation on
purpose: Copper-Silver carry `calories` and `set` goals that the strict parser
rejects, and they are out of scope precisely because they cannot be derived
from a score sheet.
"""

import json
from functools import cache
from importlib.resources import files

from life4.life4.core import Life4Rank, Life4RankEnum
from life4.life4.ranks.parser import parse_goal

#: Widening this is the only change needed to admit Gold-Diamond or Onyx-Ruby;
#: they share the in-scope structure. Copper-Silver do not -- see the module
#: docstring.
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
                requirements=[parse_goal(g) for g in requirements["goals"]],
                substitutions=[
                    parse_goal(g) for g in requirements.get("substitutions") or []
                ],
            )
        )

    for tier, subranks in ranks.items():
        subranks.sort(key=lambda rank: rank.subrank)
    return ranks
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_registry.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add src/life4/life4/ranks/registry.py tests/test_registry.py
git commit -m "feat: parse the ranks snapshot into Pearl-Emerald rank objects"
```

---

### Task 8: Conformance against LIFE4's rendered wording

**Files:**
- Create: `scripts/fetch_rendered_strings.py`, `tests/fixtures/life4_rendered.txt`, `tests/test_conformance.py`

**Interfaces:**
- Consumes: `load_ranks`.
- Produces: the committed fixture and the two tests that guard wording.

- [ ] **Step 1: Write the fixture builder**

Create `scripts/fetch_rendered_strings.py`:

```python
"""Rebuild the conformance fixture from LIFE4's rendered requirements page.

    uv run scripts/fetch_rendered_strings.py

The served HTML contains every rendered requirement string for all 65
sub-ranks. We keep the *strings*, not the sections: section boundaries in that
HTML are damaged (some lists are truncated and neighbours merge), but the
strings themselves are intact, so membership is the reliable assertion.
"""

import html
import re
from pathlib import Path

import requests

PAGE_URL = "https://life4ddr.com/rank-requirements"
FIXTURE = (
    Path(__file__).resolve().parent.parent / "tests/fixtures/life4_rendered.txt"
)
_MARKER = re.compile(
    r"^(Requirements:|Substitutions:|Complete \d+ of these \d+ requirements:)$"
)


def text_nodes(page: str) -> list[str]:
    stripped = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", page)
    parts = re.sub(r"(?s)<[^>]+>", "\x00", stripped).split("\x00")
    return [text for text in (html.unescape(p).strip() for p in parts) if text]


def requirement_strings(page: str) -> set[str]:
    parts = text_nodes(page)
    marks = [i for i, part in enumerate(parts) if _MARKER.match(part)]
    found: set[str] = set()
    for position, start in enumerate(marks):
        end = marks[position + 1] if position + 1 < len(marks) else len(parts)
        body = [p for p in parts[start + 1 : end] if p not in ("✓", "⇄")]
        # "MA Points" and its value are separate nodes.
        merged: list[str] = []
        for part in body:
            if merged and merged[-1] == "MA Points":
                merged[-1] = "MA Points: " + part.lstrip(": ").strip()
                continue
            merged.append(part)
        found.update(merged)
    return found


def main() -> int:
    response = requests.get(PAGE_URL, timeout=30)
    response.raise_for_status()
    strings = sorted(requirement_strings(response.text))
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text("\n".join(strings) + "\n", encoding="utf-8")
    print(f"wrote {FIXTURE} ({len(strings)} strings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Build the fixture**

Run: `uv run scripts/fetch_rendered_strings.py`
Expected: `wrote .../life4_rendered.txt (812 strings)`

- [ ] **Step 3: Write the conformance test**

Create `tests/test_conformance.py`:

```python
"""Pins requirement wording against LIFE4's own rendered output.

This is the only test that can show the formatter is *wrong* rather than
merely *changed* -- everything else compares generated output to generated
output. It is what makes the generated snapshot an honest substitute for the
hand-written literals this work deleted.
"""

from pathlib import Path

from life4.life4.ranks.registry import load_ranks

FIXTURE = Path(__file__).parent / "fixtures/life4_rendered.txt"


def life4_strings() -> set[str]:
    return set(FIXTURE.read_text(encoding="utf-8").splitlines())


def generated() -> list[str]:
    return [
        str(requirement)
        for subranks in load_ranks().values()
        for rank in subranks
        for requirement in (*rank.requirements, *rank.substitutions)
    ]


def test_every_generated_string_is_one_life4_actually_prints():
    published = life4_strings()
    strings = generated()
    assert strings, "no requirements were generated"
    unpublished = sorted({s for s in strings if s not in published})
    assert not unpublished, (
        "these renderings appear nowhere in LIFE4's output:\n  "
        + "\n  ".join(unpublished)
    )


def test_conformance_covers_every_in_scope_goal():
    assert len(generated()) == 583
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_conformance.py -v`
Expected: PASS. If it fails, the formatter is wrong — fix `wording.py`, not the fixture.

- [ ] **Step 5: Add the regression snapshot**

Membership alone would let a swap through (rendering goal A's string for goal B — both are legitimate strings somewhere). Append to `tests/test_conformance.py`:

```python
SNAPSHOT = Path(__file__).parent / "fixtures/rendered_requirements.txt"


def rendered_report() -> str:
    lines = []
    for tier, subranks in load_ranks().items():
        for rank in subranks:
            lines.append(f"## {tier.name} {rank.subrank}")
            lines.extend(f"  req: {r}" for r in rank.requirements)
            lines.extend(f"  sub: {s}" for s in rank.substitutions)
    return "\n".join(lines) + "\n"


def test_rendered_requirements_match_the_committed_snapshot():
    """Pins goal-to-string mapping, which membership alone cannot.

    To accept an intended change: delete the snapshot, re-run, review the
    diff before committing.
    """
    report = rendered_report()
    if not SNAPSHOT.exists():
        SNAPSHOT.write_text(report, encoding="utf-8")
    assert report == SNAPSHOT.read_text(encoding="utf-8")
```

- [ ] **Step 6: Generate and review the snapshot**

Run: `uv run pytest tests/test_conformance.py -v`

Then read `tests/fixtures/rendered_requirements.txt` end to end and spot-check
Amethyst I and Emerald V against https://life4ddr.com/rank-requirements. This
file is the replacement for the deleted literals — it is worth reading once.

- [ ] **Step 7: Commit**

```bash
git add scripts/fetch_rendered_strings.py tests/fixtures/ tests/test_conformance.py
git commit -m "test: pin requirement wording against LIFE4's rendered output"
```

---

### Task 9: Wire up the app and delete A20+

**Files:**
- Modify: `app.py:8`, `app.py:56-61`
- Delete: `src/life4/life4/ranks/a20_plus.py`

**Interfaces:**
- Consumes: `load_ranks`, `IN_SCOPE`.

- [ ] **Step 1: Update `app.py`**

Replace the import on line 8:

```python
from life4.life4.ranks.registry import IN_SCOPE, load_ranks
```

Replace lines 56-61:

```python
    ranks = load_ranks()
    names = tuple(tier.name for tier in IN_SCOPE)
    rank_choice = st.selectbox("Select rank", names, index=len(names) - 1)
    subranks = ranks[Life4RankEnum[rank_choice]]

    for sub_rank, column in zip(subranks, st.columns(5)):
        with column:
            Life4RankDisplay(sub_rank, data).visualize()
```

Add `Life4RankEnum` to the existing `life4.life4.core` import.

- [ ] **Step 2: Delete the superseded module**

```bash
git rm src/life4/life4/ranks/a20_plus.py
```

- [ ] **Step 3: Confirm nothing still references it**

Run: `grep -rn "a20_plus\|AAARequirement\|CeilingRequirement\|LampFloorRequirement\|ClearRequirement\|FloorRequirement\|PFCRequirement\|SDPCountRequirement\|MFCCountRequirement" --include="*.py" .`
Expected: no output.

- [ ] **Step 4: Run the full suite and lint**

Run: `uv run pytest -v && uv run ruff check && uv run ruff format --check`
Expected: PASS.

- [ ] **Step 5: Launch the app and confirm all four tiers render**

Run: `uv run streamlit run app.py`

Check: the selectbox lists Pearl, Topaz, Amethyst, Emerald; each shows five
sub-rank columns; an unsatisfied folder requirement still opens its blocker
dialog; `SDP a 13+` and `MFC an 11+` appear under "Other", not under a
difficulty heading.

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: render Pearl-Emerald WORLD requirements, drop A20+"
```

---

### Task 10: Prune dead dataset methods

**Files:**
- Modify: `src/life4/ddr.py`

- [ ] **Step 1: Find what is now unused**

Run: `for m in get_num_pfcs get_num_AAA get_ceiling get_songs_below_threshold get_songs_above_threshold get_songs_in_range get_level_scores get_lamps_for_level get_level_lamp get_lamp; do echo "== $m: $(grep -rn "$m" --include='*.py' . | grep -v 'def '"$m" | wc -l)"; done`

- [ ] **Step 2: Delete methods with zero remaining callers**

`CountRequirement` and `FolderRequirement` read the frame directly, so several
of the old single-purpose accessors are now dead. Delete only those the step-1
scan shows are unreferenced outside their own definition — `get_ma_points`,
`get_sdps`, `get_sdp_or_better`, `get_level`, `get_levels_from` and `charts`
all stay.

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS. Any failure means a test was the only caller — check whether
the test is still meaningful before deleting either.

- [ ] **Step 4: Commit**

```bash
git add src/life4/ddr.py tests/
git commit -m "refactor: drop dataset accessors the new requirement classes replaced"
```

---

## Verification

Before opening the PR:

```bash
uv run pytest -v
uv run ruff check && uv run ruff format --check
uv run scripts/fetch_ranks.py --check
```

Manual: read `tests/fixtures/rendered_requirements.txt` once, end to end. It is
the artifact that replaces the deleted literals, and reading it is the check
that the collapse from 13 classes to 4 did not quietly change a requirement.
