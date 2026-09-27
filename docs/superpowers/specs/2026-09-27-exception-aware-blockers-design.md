# Exception-Aware Blockers — Design

**Date:** 2026-09-27
**Status:** Draft — awaiting review
**Branch:** `fix/exception-aware-blockers`

## Problem

Topaz 3 / Amethyst 3: "Clear all 16s over 965k (22E, 930k)". Live data:

| Chart | Score |
|---|---|
| Danmaku shinkou, Gale Rider, Hit Show Heroes, Meteora -meteor- | unplayed |
| Hou | 952,610 |
| TRIP MACHINE (xac nanoglide mix) | 958,820 |

The blockers button reads **"4 unplayed · 2 to improve"**. The "2 to improve"
is wrong. Both scored charts clear the 930k shadow floor and fit inside 22
exceptions. No score change on either one moves the requirement. The only thing
standing between the player and the checkbox is the four unplayed charts.

The cause is in `life4_ui.py`:

```python
unplayed = int(blockers["score"].isna().sum())
to_improve = len(blockers) - unplayed
```

`blockers()` returns every chart below target as a flat frame
(`song, score, needs`), and the UI decides what those rows mean without
knowing the requirement's rules. The `Requirement.blockers` docstring
acknowledges this ("Charts covered by a requirement's exception allowance are
still listed") and defers it on the grounds that choosing *which* charts an
allowance forgives is undefined.

That deferral is right about the hard case and wrong about the display. The
fix is not to choose; it is to stop presenting a choice as a verdict.

## Scope

Of the 90 in-scope folder requirements, 89 carry exceptions, and every one of
those 89 also carries an exception floor:

| Shape | Count | Example |
|---|---|---|
| Score + exceptions | 40 | Clear all 16s over 965k (22E, 930k) |
| Lamp + score + exceptions | 45 | LIFE4 Clear all 16s over 985k (17E, 965k) |
| Lamp + average + exceptions | 4 | PFC all 14s with a 999,500 Folder Average (4E, 996k) |
| Lamp + average, no exceptions | 1 | PFC all 14s with a 999,700 Folder Average |

All three exception shapes have the same bug and are fixed here. The
no-exception shape is correct today and keeps its meaning.

## LIFE4 rule

> Exceptions need to be cleared (but they don't need to meet the main
> requirement's clear type), and if an exception score is listed, they must be
> at least that score.

The exception score is also called the **shadow floor**. This is the reading
`FolderRequirement` already implements (see its docstring); `is_satisfied` and
`get_progress` do not change.

Failed plays are treated as unplayed and need no handling here.

## Principles

1. **Facts, not verdicts.** The dialog states where each chart stands. It never
   marks a chart as done, excused, or the one to work on. Least points is not
   least effort, and the app cannot know which charts the player would rather
   grind.
2. **LIFE4 vocabulary.** "Exceptions", not invented terms like "in band".
3. **Rules in one place.** The requirement computes categories, counts and
   text. The UI only draws them.

## Categories

Every chart failing a folder requirement (missing the target score, the lamp,
or both) falls into exactly one category:

| Category | Rule | Applies to |
|---|---|---|
| **Unplayed** | no score | all |
| **Must raise** | score below the shadow floor | requirements with exceptions |
| **Exception** | score at or above the shadow floor | requirements with exceptions |
| **To improve** | scored | requirements without exceptions |

A chart counts as an exception whatever its lamp is, because exceptions are
excused from the clear type.

A requirement with exceptions but no floor (none exist in the LIFE4 data, but
the constructor permits it) treats every scored failing chart as an exception.

## Report

`blockers()` returns a `BlockerReport` instead of a DataFrame.

```python
@dataclass(frozen=True)
class BlockerReport:
    rows: pd.DataFrame          # song, score, then the gap columns below
    unplayed: int
    must_raise: int
    exceptions_used: int
    exceptions_allowed: int     # 0 when the requirement has no exceptions
    to_improve: int             # only for requirements without exceptions
    average: tuple[float | None, int] | None   # (current, target) or None

    @property
    def empty(self) -> bool: ...
    def label(self) -> str: ...
    def header_lines(self) -> list[str]: ...
```

`Requirement.blockers()` (the base default, used by `CountRequirement`) returns
an empty report.

### Columns

`song` and `score` are always present. Gap columns follow, in this order,
each only when the requirement has that condition:

| Column | Present when | Cell |
|---|---|---|
| `to {floor}` e.g. `to 930k` | exceptions with a floor | `✓` if score ≥ floor, else `+{gap:,}` |
| `to {target}` e.g. `to 965k` | `min_score` | `✓` if score ≥ target, else `+{gap:,}` |
| `lamp` | `clear_type` | `✓` if the lamp is met, else `{have} → {required}` |

Header scores use `wording.format_score` (`930k`, `998,500`). Lamp names use
`ddr.LAMP_LABELS` ("Clear → LIFE4 Clear"), as the current `needs` column does.

For an unplayed chart, the first gap column reads `unplayed` and the rest are
blank. The `score` column keeps today's numeric formatting; the `—` in the
examples below stands for however Streamlit renders a missing value.

The `needs` column and `Requirement.BLOCKER_COLUMNS` are removed.

### Ordering

Rows are grouped by category, **unplayed → must raise → exception** (or
**unplayed → to improve**), then sorted alphabetically within each group,
case-insensitively.

This revises the decision in `_sorted_by_song`, which kept unplayed charts from
floating to the top. The objection there was to a *score* ordering, which reads
as the list changing its mind partway down. Category groups don't have that
problem: each group is its own alphabetical list, and the gap columns explain
why each row sits where it does.

### Label (button text)

Parts joined with ` · `. A part with a zero count is left out. "With
exceptions" means `exceptions_allowed > 0`.

- With exceptions: `N unplayed`, `N must raise`, `U/A exceptions`
- Without exceptions: `N unplayed`, `N to improve`

The no-exception label changes slightly: `0 to improve` is now left out rather
than shown.

### Header lines (dialog, under the requirement text)

- With exceptions: `Exceptions: U used / A allowed`
- With an average: `Folder average: {current:,.0f} / {target:,}`, where
  `current` is the mean of played charts (as `get_progress` computes it), or
  `-` when nothing is played

`exceptions_used` counts only charts that qualify today. A must-raise chart is
not counted. Raising one above the floor increases the count. That is intended,
because the count describes current scores, not a forecast.

## Examples

**Live data — "Clear all 16s over 965k (22E, 930k)"**

```
[ 4 unplayed · 2/22 exceptions ]

Exceptions: 2 used / 22 allowed

song                 score     to 930k   to 965k
Danmaku shinkou      —         unplayed
Gale Rider           —         unplayed
Hit Show Heroes      —         unplayed
Meteora -meteor-     —         unplayed
Hou                  952,610   ✓         +12,390
TRIP MACHINE         958,820   ✓         +6,180
```

**Over budget — "(3E, 930k)"**

```
[ 1 unplayed · 1 must raise · 4/3 exceptions ]

Exceptions: 4 used / 3 allowed

song                 score     to 930k   to 965k
Hit Show Heroes      —         unplayed
Danmaku shinkou      921,300   +8,700    +43,700
Gale Rider           944,100   ✓         +20,900
Hou                  952,610   ✓         +12,390
Meteora -meteor-     961,500   ✓         +3,500
TRIP MACHINE         958,820   ✓         +6,180
```

**Lamp — "LIFE4 Clear all 16s over 985k (17E, 965k)"**

```
[ 1 unplayed · 1 must raise · 4/17 exceptions ]

Exceptions: 4 used / 17 allowed

song                score     to 965k   to 985k   lamp
Hit Show Heroes     —         unplayed
Danmaku shinkou     958,200   +6,800    +26,800   Clear → LIFE4 Clear
Gale Rider          971,400   ✓         +13,600   ✓
Hou                 990,100   ✓         ✓         Clear → LIFE4 Clear
Meteora -meteor-    979,000   ✓         +6,000    Clear → LIFE4 Clear
TRIP MACHINE        981,650   ✓         +3,350    ✓
```

**Average — "PFC all 14s with a 999,500 Folder Average (4E, 996k)"**

```
[ 2 unplayed · 1 must raise · 3/4 exceptions ]

Exceptions: 3 used / 4 allowed
Folder average: 999,310 / 999,500

song       score     to 996k   lamp
Chart A    —         unplayed
Chart B    —         unplayed
Chart C    993,400   +2,600    Great Full Combo → Perfect Full Combo
Chart D    998,900   ✓         Great Full Combo → Perfect Full Combo
Chart E    997,250   ✓         Full Combo → Perfect Full Combo
Chart F    999,120   ✓         Great Full Combo → Perfect Full Combo
```

## Unchanged

- `is_satisfied`, `get_progress`, `display_str`.
- The button still appears only when the requirement is unsatisfied and the
  report has rows. An average requirement that fails only on its average (every
  chart PFC'd, average too low) still shows no button; the checkbox text
  already carries `Avg x/y`.

## Components

| File | Change |
|---|---|
| `src/life4/life4/ranks/requirements.py` | `BlockerReport`; `FolderRequirement.blockers` builds it; base default returns an empty one; drop `BLOCKER_COLUMNS`; `_sorted_by_song` sorts by category then song |
| `src/life4/life4_ui.py` | Button uses `report.label()`; dialog renders `header_lines()` above `rows` |
| `tests/test_blockers.py` | Rewritten against the report (see Testing) |

## Testing

Unit tests on `BlockerReport` through `FolderRequirement.blockers`, no Streamlit:

- **Regression:** the live-data case yields `4 unplayed · 2/22 exceptions`,
  with no "to improve".
- Categories: below the floor → must raise; at the floor exactly → exception;
  unplayed → unplayed.
- An exception with a lamp gap but score over target is still an exception.
- `exceptions_used` excludes must-raise charts; over budget renders `4/3`.
- Zero-count parts are left out of the label.
- No-exception requirement: `N unplayed · N to improve`, no floor column.
- Columns per shape: score-only, lamp + score, lamp + average.
- Cells: `✓`, `+gap`, `unplayed` then blanks, `have → required`.
- Ordering: category first, then case-insensitive alphabetical within each group.
- Average header line, including `-` when nothing is played.
- `CountRequirement.blockers()` is empty.
- Existing tests kept: REQUIRED pool, song-title disambiguation, the
  score/`record_on` agreement test in `test_requirements.py`.
- `test_registry.py` smoke test still exercises `blockers()` on every
  requirement.
