# Exception-Aware Blockers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the blockers button from reporting charts covered by a requirement's exception allowance as "to improve", and show each failing chart's category and gaps instead.

**Architecture:** `Requirement.blockers()` returns a frozen `BlockerReport` dataclass instead of a bare DataFrame. `FolderRequirement` sorts each failing chart into a category (unplayed / must raise / exception, or unplayed / to improve when the requirement has no exceptions) and builds per-condition gap columns. The report owns the button label and dialog header text; the Streamlit UI only draws them.

**Tech Stack:** Python 3.11+, pandas, streamlit, pytest, uv, ruff.

**Spec:** `docs/superpowers/specs/2026-09-27-exception-aware-blockers-design.md`

## Global Constraints

- **Facts, not verdicts.** No row is ever marked done, excused, or recommended.
- **Vocabulary:** "unplayed", "must raise", "exceptions", "to improve". Never "in band".
- **Label:** parts joined with ` · `; zero-count parts omitted. With exceptions: `N unplayed`, `N must raise`, `U/A exceptions`. Without: `N unplayed`, `N to improve`.
- **Header lines:** `Exceptions: U used / A allowed`; `Folder average: {current:,.0f} / {target:,}` with `-` when nothing is played.
- **Shadow floor is inclusive:** `score >= exception_floor` is an exception.
- **Exceptions ignore the lamp:** a chart at or above the shadow floor is an exception whatever its lamp.
- **Column order:** `song`, `score`, `to {floor}`, `to {target}`, `lamp` — each gap column only when that condition exists. Headers use `wording.format_score`.
- **Cells:** `✓` when met, `+{gap:,.0f}` for a score gap, `{have} → {required}` using `ddr.LAMP_LABELS`; unplayed rows read `unplayed` in the first gap column and `""` in the rest.
- **Row order:** category (unplayed → must raise → exception / to improve), then case-insensitive song title.
- `is_satisfied`, `get_progress`, `display_str` do not change.
- Run tests with `uv run pytest`. Lint with `uv run ruff check` and `uv run ruff format`.
- Commit after every task.

## Review Focus

1. **A chart with a score but a blank `record_on`** — must be categorised by its score (it is played), not as unplayed. Pinned in Task 2.
2. **An average requirement failing only on its average** (every chart PFC'd, average too low) — report is empty, so no button appears, and nothing crashes. Pinned in Task 2.
3. **Must-raise charts with no qualifying exceptions** — label is `1 must raise` with no `0/3 exceptions` part. Pinned in Task 1.
4. **A duplicated title at one level split across categories** — difficulty disambiguation still applies after the category sort. Pinned in Task 2.
5. **Every one of the 583 real requirements** still builds a report without raising — covered by the existing `tests/test_registry.py` smoke test, which calls `blockers()` on each.

## File Structure

**Modify:**
- `src/life4/life4/ranks/requirements.py` — add `BlockerReport` and category constants; `Requirement.blockers()` returns an empty report; `FolderRequirement.blockers()` builds a categorised report; replace `_sorted_by_song` with `_sorted_for_display`; drop `BLOCKER_COLUMNS`.
- `src/life4/life4_ui.py` — button uses `report.label()`; dialog draws `report.header_lines()` above `report.rows`.
- `tests/test_blockers.py` — rewritten against the report.

No new files. `BlockerReport` lives beside `Requirement` because it is that class's return type.

---

### Task 1: `BlockerReport` type

**Files:**
- Modify: `src/life4/life4/ranks/requirements.py` (imports; new code between `_sorted_by_song` and `class Requirement`)
- Test: `tests/test_blockers.py` (append)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `BlockerReport(rows: pd.DataFrame, unplayed: int = 0, must_raise: int = 0, exceptions_used: int = 0, exceptions_allowed: int = 0, to_improve: int = 0, average: tuple[float | None, int] | None = None)`, frozen dataclass
  - `BlockerReport.empty -> bool` (property)
  - `BlockerReport.label() -> str`
  - `BlockerReport.header_lines() -> list[str]`

- [ ] **Step 1: Write the failing tests**

Add `import pandas as pd` at the top of `tests/test_blockers.py`, add `BlockerReport` to its `from life4.life4.ranks.requirements import (...)` block, then append:

```python
def report(**counts):
    return BlockerReport(rows=pd.DataFrame(columns=["song", "score"]), **counts)


def test_label_with_exceptions_names_unplayed_must_raise_and_exception_budget():
    r = report(unplayed=1, must_raise=1, exceptions_used=4, exceptions_allowed=3)
    assert r.label() == "1 unplayed · 1 must raise · 4/3 exceptions"


def test_label_omits_zero_count_parts():
    assert report(unplayed=4, exceptions_used=2, exceptions_allowed=22).label() == (
        "4 unplayed · 2/22 exceptions"
    )
    assert report(must_raise=1, exceptions_allowed=3).label() == "1 must raise"


def test_label_without_exceptions_says_to_improve():
    assert report(unplayed=1, to_improve=2).label() == "1 unplayed · 2 to improve"
    assert report(unplayed=1).label() == "1 unplayed"


def test_header_lines_show_exception_budget_only_when_the_requirement_has_one():
    assert report(exceptions_used=2, exceptions_allowed=22).header_lines() == [
        "Exceptions: 2 used / 22 allowed"
    ]
    assert report(unplayed=3).header_lines() == []


def test_header_lines_show_folder_average():
    r = report(exceptions_used=3, exceptions_allowed=4, average=(999_310.4, 999_500))
    assert r.header_lines() == [
        "Exceptions: 3 used / 4 allowed",
        "Folder average: 999,310 / 999,500",
    ]


def test_folder_average_reads_dash_when_nothing_is_played():
    assert report(average=(None, 999_500)).header_lines() == [
        "Folder average: - / 999,500"
    ]


def test_report_is_empty_when_it_has_no_rows():
    assert report().empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_blockers.py -v`
Expected: collection error, `ImportError: cannot import name 'BlockerReport'`.

- [ ] **Step 3: Implement `BlockerReport`**

In `src/life4/life4/ranks/requirements.py`, add `from dataclasses import dataclass` to the imports. Insert after `_sorted_by_song`, before `class Requirement`:

```python
@dataclass(frozen=True)
class BlockerReport:
    """Where each chart failing a requirement stands, and the text to show it.

    States facts only. Nothing here marks a chart as done or as the one to
    work on: when more charts sit above the shadow floor than there are
    exceptions, which ones the allowance forgives is the player's choice, and
    fewest points is not least effort.
    """

    rows: pd.DataFrame
    unplayed: int = 0
    must_raise: int = 0
    exceptions_used: int = 0
    exceptions_allowed: int = 0
    to_improve: int = 0
    # (mean of played charts, target), for Folder Average requirements.
    average: tuple[float | None, int] | None = None

    @property
    def empty(self) -> bool:
        return self.rows.empty

    def label(self) -> str:
        if self.exceptions_allowed:
            parts = [
                (self.unplayed, f"{self.unplayed} unplayed"),
                (self.must_raise, f"{self.must_raise} must raise"),
                (
                    self.exceptions_used,
                    f"{self.exceptions_used}/{self.exceptions_allowed} exceptions",
                ),
            ]
        else:
            parts = [
                (self.unplayed, f"{self.unplayed} unplayed"),
                (self.to_improve, f"{self.to_improve} to improve"),
            ]
        return " · ".join(text for count, text in parts if count)

    def header_lines(self) -> list[str]:
        lines = []
        if self.exceptions_allowed:
            lines.append(
                f"Exceptions: {self.exceptions_used} used / "
                f"{self.exceptions_allowed} allowed"
            )
        if self.average is not None:
            current, target = self.average
            current_str = "-" if current is None else f"{current:,.0f}"
            lines.append(f"Folder average: {current_str} / {target:,}")
        return lines
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_blockers.py -v`
Expected: all PASS (the existing tests are untouched and still pass).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src tests && uv run ruff format src tests
git add src/life4/life4/ranks/requirements.py tests/test_blockers.py
git commit -m "feat: add BlockerReport with exception-aware label and header"
```

---

### Task 2: Categorised `FolderRequirement.blockers()`

**Files:**
- Modify: `src/life4/life4/ranks/requirements.py` — imports (`format_score`), `_sorted_by_song` (replace), `Requirement.BLOCKER_COLUMNS` and `Requirement.blockers` (lines ~52–75), `FolderRequirement.blockers` (lines ~333–353)
- Test: `tests/test_blockers.py` (rewrite the existing FolderRequirement tests; keep Task 1's tests)

**Interfaces:**
- Consumes: `BlockerReport` from Task 1.
- Produces: `Requirement.blockers(data) -> BlockerReport`, `FolderRequirement.blockers(data) -> BlockerReport`. The report's `rows` has columns `song`, `score`, then the gap columns listed in Global Constraints.

- [ ] **Step 1: Rewrite the FolderRequirement tests**

In `tests/test_blockers.py`, delete these existing tests (their replacements follow):
`test_blockers_are_alphabetical_regardless_of_score`, `test_a_chart_failing_only_the_lamp_names_the_current_and_target_lamp`, `test_a_chart_failing_both_conditions_appears_once`, `test_an_unplayed_chart_reads_as_unplayed_not_as_a_lamp_upgrade`, `test_blockers_return_exactly_song_score_needs_columns`.

In the remaining tests that read `blockers["song"]`, change to `.rows["song"]`: `test_blockers_sort_case_insensitively`, `test_unique_title_at_a_level_renders_bare_with_no_parenthetical`, `test_title_appearing_twice_at_a_level_suffixes_each_with_its_own_difficulty`, `test_three_way_collision_suffixes_all_three`. Tests using `.empty` need no change.

Remove `Requirement` from the import block if nothing else uses it. Add these tests:

```python
def sixteens(**kwargs):
    return FolderRequirement(level=16, min_score=965_000, **kwargs)


def test_charts_within_the_exception_allowance_are_not_to_improve():
    # The reported bug: Amethyst 3 read "4 unplayed · 2 to improve" although
    # both scored charts sit above the shadow floor inside 22 exceptions.
    data = dataset(
        chart(title="Danmaku shinkou", level=16),
        chart(title="Gale Rider", level=16),
        chart(title="Hit Show Heroes", level=16),
        chart(title="Meteora -meteor-", level=16),
        played("Hou", 16, 952_610),
        played("TRIP MACHINE", 16, 958_820),
        played("passing", 16, 990_000),
    )
    report = sixteens(exceptions=22, exception_floor=930_000).blockers(data)
    assert report.label() == "4 unplayed · 2/22 exceptions"
    assert report.header_lines() == ["Exceptions: 2 used / 22 allowed"]
    assert report.rows.to_dict("records")[-2:] == [
        {"song": "Hou", "score": 952_610, "to 930k": "✓", "to 965k": "+12,390"},
        {"song": "TRIP MACHINE", "score": 958_820, "to 930k": "✓", "to 965k": "+6,180"},
    ]


def test_the_shadow_floor_is_inclusive():
    data = dataset(played("at", 16, 930_000), played("below", 16, 929_999))
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert (report.must_raise, report.exceptions_used) == (1, 1)


def test_over_budget_counts_only_qualifying_charts_as_exceptions():
    data = dataset(
        chart(title="Hit Show Heroes", level=16),
        played("Danmaku shinkou", 16, 921_300),
        played("Gale Rider", 16, 944_100),
        played("Hou", 16, 952_610),
        played("Meteora", 16, 961_500),
        played("TRIP MACHINE", 16, 958_820),
    )
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert report.label() == "1 unplayed · 1 must raise · 4/3 exceptions"
    danmaku = report.rows[report.rows["song"] == "Danmaku shinkou"].iloc[0]
    assert (danmaku["to 930k"], danmaku["to 965k"]) == ("+8,700", "+43,700")


def test_a_chart_over_target_missing_only_the_lamp_is_an_exception():
    data = dataset(played("Hou", 16, 990_100))
    req = FolderRequirement(
        level=16,
        clear_type=ClearType.LIFE4,
        min_score=985_000,
        exceptions=17,
        exception_floor=965_000,
    )
    report = req.blockers(data)
    assert report.exceptions_used == 1
    assert report.rows.to_dict("records") == [
        {
            "song": "Hou",
            "score": 990_100,
            "to 965k": "✓",
            "to 985k": "✓",
            "lamp": "Clear → LIFE4 Clear",
        }
    ]


def test_a_met_lamp_reads_as_a_check():
    data = dataset(played("gale", 16, 971_400, life4_date="1/2/2026"))
    req = FolderRequirement(
        level=16,
        clear_type=ClearType.LIFE4,
        min_score=985_000,
        exceptions=17,
        exception_floor=965_000,
    )
    assert req.blockers(data).rows.loc[0, "lamp"] == "✓"


def test_an_unplayed_chart_fills_only_the_first_gap_column():
    data = dataset(chart(title="unplayed", level=16))
    req = FolderRequirement(
        level=16,
        clear_type=ClearType.LIFE4,
        min_score=985_000,
        exceptions=17,
        exception_floor=965_000,
    )
    row = req.blockers(data).rows.iloc[0]
    assert (row["to 965k"], row["to 985k"], row["lamp"]) == ("unplayed", "", "")


def test_a_scored_chart_with_no_record_on_is_played_not_unplayed():
    # Review focus 1: unplayed is derived from score alone, as in
    # test_folder_agrees_on_unplayed_when_score_present_but_no_record_on.
    data = dataset(chart(title="a", level=16, score=950_000))
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert (report.unplayed, report.exceptions_used) == (0, 1)


def test_without_exceptions_every_scored_failure_is_to_improve():
    data = dataset(chart(title="u", level=16), played("s", 16, 900_000))
    report = FolderRequirement(level=16, min_score=950_000).blockers(data)
    assert report.label() == "1 unplayed · 1 to improve"
    assert report.header_lines() == []
    assert list(report.rows.columns) == ["song", "score", "to 950k"]


def test_folder_average_columns_and_header():
    data = dataset(
        played("c", 14, 993_400, gfc_date="1/2/2026"),
        played("d", 14, 998_900, gfc_date="1/2/2026"),
        played("pfc", 14, 999_900, pfc_date="1/2/2026"),
    )
    req = FolderRequirement(
        level=14,
        clear_type=ClearType.PERFECT,
        average_score=999_500,
        exceptions=4,
        exception_floor=996_000,
    )
    report = req.blockers(data)
    assert list(report.rows.columns) == ["song", "score", "to 996k", "lamp"]
    assert report.label() == "1 must raise · 1/4 exceptions"
    assert report.header_lines() == [
        "Exceptions: 1 used / 4 allowed",
        "Folder average: 997,400 / 999,500",
    ]
    assert report.rows.loc[0, "lamp"] == "Great Full Combo → Perfect Full Combo"


def test_an_average_only_failure_has_no_rows():
    # Review focus 2: every chart PFC'd but the average is short. The
    # checkbox text already carries "Avg x/y"; there is no chart to list.
    data = dataset(played("a", 14, 999_000, pfc_date="1/2/2026"))
    req = FolderRequirement(
        level=14,
        clear_type=ClearType.PERFECT,
        average_score=999_500,
        exceptions=4,
        exception_floor=996_000,
    )
    assert not req.is_satisfied(data)
    assert req.blockers(data).empty


def test_blockers_group_by_category_then_sort_alphabetically():
    data = dataset(
        played("apple", 16, 950_000),
        played("Banana", 16, 920_000),
        chart(title="cherry", level=16),
        played("avocado", 16, 925_000),
        chart(title="Apricot", level=16),
        played("blueberry", 16, 940_000),
    )
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert list(report.rows["song"]) == [
        "Apricot",
        "cherry",
        "avocado",
        "Banana",
        "apple",
        "blueberry",
    ]


def test_disambiguated_titles_survive_the_category_sort():
    # Review focus 4: two charts of one song at one level, in different
    # categories, still carry their own difficulty.
    data = dataset(
        chart(title="Ace out", level=16, diff="CSP"),
        played("Ace out", 16, 950_000, diff="ESP"),
    )
    report = sixteens(exceptions=3, exception_floor=930_000).blockers(data)
    assert list(report.rows["song"]) == ["Ace out (CSP)", "Ace out (ESP)"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_blockers.py -v`
Expected: the new FolderRequirement tests FAIL (`AttributeError: 'DataFrame' object has no attribute 'label'` / `'rows'`); Task 1's tests still PASS.

- [ ] **Step 3: Replace the sort helper and add category constants**

In `src/life4/life4/ranks/requirements.py`, add `format_score` to the `from life4.life4.ranks.wording import (...)` block. Replace the whole `_sorted_by_song` function with:

```python
UNPLAYED = "unplayed"
MUST_RAISE = "must raise"
EXCEPTION = "exception"
TO_IMPROVE = "to improve"

# Exception and to-improve never occur in the same report, so they share a slot.
_CATEGORY_ORDER = {UNPLAYED: 0, MUST_RAISE: 1, EXCEPTION: 2, TO_IMPROVE: 2}

CHECK = "✓"


def _sorted_for_display(rows: pd.DataFrame, category: pd.Series) -> pd.DataFrame:
    """Blockers grouped by category, then alphabetical by song within each.

    Deliberately NOT ordered by score. The list is read to find a specific
    song, so each group is alphabetical; a score ordering reads as the list
    changing its mind halfway down. Grouping by category does not have that
    problem because the gap columns say why each row sits where it does.
    Case-insensitive because a plain sort strands lowercase titles after
    every capitalised one.
    """
    keyed = rows.assign(
        _order=category.map(_CATEGORY_ORDER).to_numpy(),
        _song=rows["song"].str.casefold().to_numpy(),
    )
    return (
        keyed.sort_values(["_order", "_song"], kind="stable")
        .drop(columns=["_order", "_song"])
        .reset_index(drop=True)
    )


def _score_gap(score: float, target: int) -> str:
    return CHECK if score >= target else f"+{target - score:,.0f}"
```

- [ ] **Step 4: Update the base `Requirement`**

Delete the `BLOCKER_COLUMNS` comment and constant. Replace `Requirement.blockers` with:

```python
    def blockers(self, data: "DDRDataset") -> BlockerReport:
        """Charts standing between this requirement and satisfaction.

        Empty for count-based requirements ("PFC 5 16s"), which have no
        denominator and therefore no specific chart to name.
        """
        return BlockerReport(rows=pd.DataFrame(columns=["song", "score"]))
```

`BlockerReport` is defined above `Requirement`, so no forward reference is needed.

- [ ] **Step 5: Rewrite `FolderRequirement.blockers`**

Replace the whole `FolderRequirement.blockers` method with these four methods:

```python
    def _categories(self, failing: pd.DataFrame) -> pd.Series:
        scored = failing["score"].notna()
        category = pd.Series(UNPLAYED, index=failing.index, dtype=object)
        if not self.exceptions:
            category[scored] = TO_IMPROVE
            return category
        # An exception is excused from the clear type, so only score decides.
        qualifies = scored
        if self.exception_floor is not None:
            qualifies = scored & (failing["score"] >= self.exception_floor)
        category[qualifies] = EXCEPTION
        category[scored & ~qualifies] = MUST_RAISE
        return category

    def _gap_columns(self) -> list[str]:
        columns = []
        if self.exceptions and self.exception_floor is not None:
            columns.append(f"to {format_score(self.exception_floor)}")
        if self.min_score is not None:
            columns.append(f"to {format_score(self.min_score)}")
        if self.clear_type is not None:
            columns.append("lamp")
        return columns

    def _gap_cells(self, row: pd.Series) -> list[str]:
        cells = []
        if self.exceptions and self.exception_floor is not None:
            cells.append(_score_gap(row["score"], self.exception_floor))
        if self.min_score is not None:
            cells.append(_score_gap(row["score"], self.min_score))
        if self.clear_type is not None:
            required = LAMP_FOR_CLEAR_TYPE[self.clear_type]
            if row["lamp"] >= required:
                cells.append(CHECK)
            else:
                have = LAMP_LABELS[Lamp(row["lamp"])]
                cells.append(f"{have} → {LAMP_LABELS[required]}")
        return cells

    def blockers(self, data: "DDRDataset") -> BlockerReport:
        charts = self._charts(data).copy()
        charts["song"] = _song_labels(charts)
        failing = self._failing(charts)
        category = self._categories(failing)

        columns = self._gap_columns()
        unplayed_cells = [UNPLAYED] + [""] * (len(columns) - 1) if columns else []
        cells = [
            unplayed_cells if cat == UNPLAYED else self._gap_cells(row)
            for (_, row), cat in zip(failing.iterrows(), category)
        ]
        rows = failing[["song", "score"]].copy()
        for i, name in enumerate(columns):
            rows[name] = [chart_cells[i] for chart_cells in cells]

        average = None
        if self.average_score is not None:
            mean = charts["score"].mean()
            average = (None if pd.isna(mean) else float(mean), self.average_score)

        counts = category.value_counts()
        return BlockerReport(
            rows=_sorted_for_display(rows, category),
            unplayed=int(counts.get(UNPLAYED, 0)),
            must_raise=int(counts.get(MUST_RAISE, 0)),
            exceptions_used=int(counts.get(EXCEPTION, 0)),
            exceptions_allowed=self.exceptions,
            to_improve=int(counts.get(TO_IMPROVE, 0)),
            average=average,
        )
```

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: all PASS, including `tests/test_registry.py` (every one of the 583 requirements builds a report) and `tests/test_requirements.py::test_folder_agrees_on_unplayed_when_score_present_but_no_record_on` (uses `.empty`).

If a `to_dict("records")` comparison fails on `score` because pandas returns `952610.0`: that still compares equal to `952_610`; a failure there means a column name or cell is wrong, not the number type.

- [ ] **Step 7: Lint and commit**

```bash
uv run ruff check src tests && uv run ruff format src tests
git add src/life4/life4/ranks/requirements.py tests/test_blockers.py
git commit -m "fix: categorise blockers by exception allowance instead of listing all as to improve"
```

---

### Task 3: UI wiring and live check

**Files:**
- Modify: `src/life4/life4_ui.py:1-44`

**Interfaces:**
- Consumes: `Requirement.blockers(data) -> BlockerReport`; `BlockerReport.empty`, `.label()`, `.header_lines()`, `.rows`.
- Produces: nothing.

- [ ] **Step 1: Update the dialog**

In `src/life4/life4_ui.py`, drop `import pandas as pd` (no longer used) and import `BlockerReport`. The imports become:

```python
from typing import List

import streamlit as st

from life4.ddr import DDRDataset
from life4.life4.core import Life4Rank
from life4.life4.ranks.requirements import BlockerReport, Requirement
```

Replace `_show_blockers` with:

```python
@st.dialog("Charts below target", width="large")
def _show_blockers(requirement_label: str, report: BlockerReport) -> None:
    st.caption(requirement_label)
    for line in report.header_lines():
        st.caption(line)
    st.dataframe(report.rows, hide_index=True, width="stretch")
```

- [ ] **Step 2: Update the button**

In `create_checkbox`, replace everything from `blockers = requirement.blockers(self.data)` to the end of the method with:

```python
        report = requirement.blockers(self.data)
        if report.empty:
            return

        if st.button(
            report.label(), key=f"{self.life4_rank}|{group}|{requirement}|blockers"
        ):
            _show_blockers(requirement.display_str(self.data), report)
```

The button key is unchanged, so no widget identity shifts.

- [ ] **Step 3: Run the suite and lint**

```bash
uv run pytest -q
uv run ruff check src tests && uv run ruff format src tests
```
Expected: all PASS; ruff clean (it will flag `pandas` if still imported unused).

- [ ] **Step 4: Check against live data**

Run: `uv run streamlit run app.py`, select **AMETHYST**, open sub-rank 3.

Expected on "Clear all 16s over 965k (22E, 930k)":
- Button reads `4 unplayed · 2/22 exceptions`.
- Dialog shows `Exceptions: 2 used / 22 allowed`, then four unplayed rows (alphabetical) followed by Hou and TRIP MACHINE with `✓` under `to 930k` and `+12,390` / `+6,180` under `to 965k`.

Also open one LIFE4-lamp requirement (e.g. "LIFE4 Clear all 16s over 985k (17E, 965k)") and confirm a `lamp` column appears.

If the app can't be run in this session, say so explicitly and ask the user to do this check; do not report it as done.

- [ ] **Step 5: Commit**

```bash
git add src/life4/life4_ui.py
git commit -m "fix: render exception-aware blocker label and dialog header"
```
