# LIFE4 Dashboard Overhaul — Design

**Date:** 2026-08-16
**Status:** Approved for planning

## Context

The dashboard reads a single Google Sheets tab of DDR scores and renders progress
toward LIFE4 rank requirements as Streamlit checkboxes. Three things have drifted
out from under it:

1. The requirements encoded in `a20_plus.py` are A20+ requirements. The live
   ruleset is DDR World, and the numbers have moved.
2. The player has switched cabinets. A3 scores live in the `CTF` tab; WORLD
   scores live in a separate tab. The two servers share nothing, so the app
   currently sees 8% of the player's actual history.
3. There are no tests, and at least one requirement has been reporting satisfied
   when it is not.

This design covers all four workstreams plus a test suite.

## Goals

- Fix confirmed correctness bugs in requirement evaluation.
- Load sheets through a documented, non-truncating endpoint.
- Present LIFE4 progress as the union of A3 and WORLD play history.
- Replace A20+ requirements with DDR World requirements for Pearl through Emerald.
- Establish a test suite over requirement logic.

## Non-Goals

- Ranks outside Pearl–Emerald. Copper–Gold, Diamond, Cobalt, Onyx and Ruby are
  not transcribed. Ruby is added to the rank enum only so trial requirements can
  reference it.
- Doubles. Singles only, as today.
- Official LIFE4 submission conformance. See "Known divergence from official rules".
- Multi-user support. This remains a personal dashboard reading one document.

## Known divergence from official rules

The LIFE4 FAQ states that A20+ submissions cannot use A3 scores. A merged
A3 ∪ WORLD figure is therefore **not** what would be submitted for an actual
rank-up, and will read higher than official standing. This is an accepted,
deliberate divergence: the dashboard measures personal progress, not submission
eligibility.

Requirements satisfied only because of A3 carryover should be visually
distinguishable in the UI so the divergence stays honest. Treated as a
nice-to-have, not a blocker.

---

## Findings that drove the design

Each of these was measured against the live document on 2026-08-16, not inferred.

### The gviz endpoint silently truncates

The current loader uses `gviz/tq?tqx=out:csv&sheet=<TabName>`, an undocumented
endpoint of the deprecated Google Visualization API. Measured against the WORLD
tab:

| Endpoint | Rows returned |
|---|---|
| `/export?format=csv&gid=638900183` | 10,814 |
| `/gviz/tq?tqx=out:csv&gid=638900183` | 3,408 |
| `/gviz/...&tq=select * limit 20000` | 3,408 |

7,406 rows are dropped. HTTP 200, no warning, and the returned keys are a strict
subset of the full set. The same endpoint returns the `CTF` tab (5,124 rows)
complete, so the failure is size-dependent and unpredictable.

**All 200 played charts survive the truncation.** What is dropped is unplayed
rows — which are precisely the denominators. Under gviz, `get_level_lamp` returns
a better lamp than reality (the `NO_LAMP` rows vanished) and `FloorRequirement`
denominators shrink, so "All 16s over 955k" becomes satisfiable when it is not.
Every resulting error flatters progress.

This is the reason to move off gviz. The URL-format-change risk that originally
motivated the workstream is real but secondary.

### The two tabs do not share a schema

```
CTF (A3):  Diff,Level,Title,# times,Last played,MA Ratio,Marv,Perf,Great,Good,O.K.,Miss,EX,Score,...,Availability
WORLD:     Diff,Level,Title,# times,Last played,M,P,Gr,Go,O.K.,M,EX,Score,...,Availability,MA
```

Three distinct problems:

- Different names for the same fields. `get_sdps()` reads `Score["Perf"]`, which
  does not exist in the WORLD tab. **The current code cannot read WORLD at all.**
- `M` appears **twice** in the WORLD header (Marvelous at index 5, Miss at index
  10). Pandas disambiguates positionally into `M` and `M.1`. Nothing would detect
  a swap, and confusing Marvelous with Miss would corrupt SDP logic invisibly.
- Different column order: `MA Ratio` at index 5 in A3, `MA` at index 20 in WORLD.

### The join is clean

Measured on singles rows:

```
JOIN on (Title, Diff)
  in both     : 5,124
  WORLD only  : 1,021     new charts, expected
  A3 only     :     0     WORLD is a strict superset
LEVEL DRIFT   :     1     BREAKING THE FUTURE DSP, 14 -> 15
```

No fuzzy matching, normalization table, or manual alias file is needed. This was
the largest perceived risk in the project and it is not a risk.

### The union is the whole point

```
played on BOTH : 121     A3 only : 1,471     WORLD only : 15
A3 has the better score on 70 of the 121 shared; WORLD on 51

        WORLD-only   union
  L14         34      203   (+169)
  L16         16      158   (+142)
  L18          1       51    (+50)
```

Neither sheet dominates, so field-wise best genuinely draws from both.

---

## Architecture

Four layers, each independently testable.

```
  loaders          SheetLoader          -> raw DataFrame per tab
  normalization    CanonicalSchema      -> uniform columns, validated
  merge            ScoreMerger          -> one row per (title, diff)
  domain           DDRDataset           -> two chart-pool views
  rules            Requirement classes  -> is_satisfied / display_str
  ui               Life4RankDisplay     -> Streamlit
```

### 1. Loading

Replace `GoogleSheetsDataSource` URL strings with document ID plus per-tab gid:

```toml
[sheets]
doc_id = "1o664te8mE0nnD-PyEW7kEW8CszLPQ3E_"

[sheets.tabs]
world  = 638900183
a3     = <CTF gid>
trials = <trials gid>
```

The loader builds `/export?format=csv&gid={gid}`. No credentials — the document
is public and anonymous `curl` returns 200.

Wrapped in `@st.cache_data(ttl=...)` with an explicit "Refresh data" button. The
app currently re-downloads and re-parses on every checkbox render; with two tabs
that becomes four round-trips per interaction.

Delete `OnedriveDataSource`. It is unreferenced, and its `load_trials` reads
`sheet_name="Trials"` while `load_scores` reads sheet 0 of the same workbook.

### 2. Canonical schema

One canonical column set:

```
diff, level, title, times_played, last_played,
marvelous, perfect, great, good, ok, miss, ex, score,
record_on, aaa_date, pfc_date, gfc_date, fc_date, life4_date,
availability, ma_ratio
```

Each tab declares a mapping onto it. Because the WORLD header contains `M` twice,
**mappings are positional, not by name**, and each tab's expected raw header line
is asserted verbatim before mapping. A header change fails loudly at load with a
message naming the tab and the offending column, rather than surfacing as a
`KeyError` from inside `_get_lamp` or as a silent Marvelous/Miss swap.

### 3. Merge

WORLD defines the chart pool and every chart's level. A3 contributes score and
achievement history only, joined on `(title, diff)`.

Per merged chart:

| Field | Rule |
|---|---|
| `level`, `availability` | From WORLD |
| `score` | `max` across sources, NaN-aware |
| date columns | Earliest non-null across sources |
| judgment block (`marvelous`…`ex`, `ma_ratio`) | Taken as a unit from the higher-scoring source |

Unioning the date columns yields `max(lamp)` for free: `_get_lamp` tests
`pfc_date` → `gfc_date` → `fc_date` → `life4_date` in descending order, so a
lamp achieved on either cabinet surfaces automatically. No separate lamp merge
is needed.

The judgment block moves as a unit because those columns are only meaningful
together. Taking `max(score)` with `min(perfect)` independently could in
principle manufacture an achievement — though in practice a PFC's score is a
deterministic function of its perfect count (5 perfects → 999,950), so max-score
and min-perfect always come from the same row anyway. Moving the block as a unit
makes that safe by construction rather than by coincidence.

Trials are single-source. No trial merge.

### 4. Two chart-pool views

The FAQ says Extra Stage-only songs "aren't required but count if earned." Each
`availability` value is classified:

| Class | Values | Counts in numerators | Counts in denominators |
|---|---|---|---|
| `NORMAL` | *(blank)* | yes | yes |
| `OPTIONAL` | `extra exclusive`, `phase 2` | yes | no |
| `EXCLUDED` | `course trial`, `Other`, `removed` | no | no |

Unknown markers default to `EXCLUDED` with a logged warning — an allowlist, so a
new marker added to the sheet is never silently counted. (Today's denylist misses
`extra exclusive` and `phase 2` entirely.)

`DDRDataset` exposes two views instead of one filtered frame, and each
`Requirement` subclass declares which it consumes:

- **Count-based** (`PFCRequirement`, `AAARequirement`, `ClearRequirement`,
  `CeilingRequirement`, `SDP*`, `MFC*`, `MAPointsRequirement`) → `NORMAL | OPTIONAL`
- **All-chart** (`FloorRequirement`, `LampRequirement`, `LampFloorRequirement`) → `NORMAL` only

Concrete impact: `Eon Break CSP 18` is unplayed and `extra exclusive`. Today it
drags level 18's lamp to `NO_LAMP` and blocks every 18s `FloorRequirement`.
`get_level()` is the single chokepoint every requirement calls, so it is the seam
to split.

`removed` charts stay excluded from both, even though two are played with good
scores. LIFE4's target counts are calibrated against the live chart pool.

### 5. Requirements

Pearl I through Emerald V — 20 tiers — transcribed verbatim from
`life4ddr.com/rank-requirements`, requirements and substitutions both.

Substitutions are the **same tier of the next rank** (Amethyst I's substitutions
are Emerald I's requirements). The FAQ's claim that substitutions come from
"tier V of the next rank" contradicts the requirement pages; the pages win.
Verbatim transcription means Onyx never needs to enter the codebase.

The existing rank-completion rule — `completed + available_substitutions >= total`
— matches the "a line for a line, no cap" rule and is **correct as written**. No
change.

New work:

- `Life4RankEnum` gains `Ruby`.
- A folder-average requirement class, for lines like
  `PFC all 14s with a 999,500 Folder Average (4E, 996k)`.
- `MFC_POINT_MAPPING` extended past level 16 (see open questions).
- `_visualize_reqs` must stop hardcoding `range(14, 20)`; it should derive the
  level range from the requirements it is given, or any sub-14 requirement will
  vanish from the UI without error.

---

## Bugs

| # | Location | Status | Description |
|---|---|---|---|
| 1 | `requirements.py:154` | **Live** | `ClearRequirement` with no floor returns `len(level_scores)` — every chart at that level, played or not. `ClearRequirement(level=19, num=1)` evaluates `10 >= 1 → True` on 2 played 19s. The `return_zero=False` argument is accepted by `get_level_scores` and ignored. |
| 2 | `ddr.py` filters | **Live** | `extra exclusive` and `phase 2` are not classified. See "two chart-pool views". |
| 3 | `backends.py` | **Live** | gviz truncation. See findings. |
| 4 | `backends.py` / `ddr.py` | **Live** | WORLD's `P`/`M`/`Gr` columns break `get_sdps()`'s `Perf` lookup. Blocks the merge outright. |
| 5 | `app.py:17` | **Live** | `data_source_info.pop("source")` mutates `st.secrets`, which persists across Streamlit reruns. |
| 6 | `core.py:6` | Latent | `MFC_POINT_MAPPING` stops at level 16; `get_ma_points()` raises `KeyError` on the first SDP or MFC at 17+. Currently returns 30.92 because the highest SDP is a 14. |
| 7 | `ddr.py:43` | Latent | `self._data["Lamp"] = ...` writes to the result of chained `.query()` calls — a write to a possible view. |

Investigated and **not** bugs, recorded so they are not re-raised:

- `max()` on empty in `SDPRequirement` / `MFCRequirement` — returns `False`
  cleanly on real data.
- `FloorRequirement.get_progress` with `exception_floor=None` — pandas compares a
  numeric Series to `None` as all-False rather than raising. Returns `34/74`.
- The substitution completion rule in `life4_ui.py:61` — correct per the ruleset.
- gviz type inference — `Level` returns `int64`, `Score` `float64`, no coercion
  damage observed.

## Code health

Addressed as part of the work, not as separate refactoring:

- **`app.py` fights Streamlit.** `@click.command()` wrapping a Streamlit script
  means Click parses Streamlit's `argv`, `default=st.secrets[...]` evaluates at
  import time, `type=dict` is not a real Click type, and Click calls `sys.exit()`
  on completion. Remove the CLI layer; Streamlit has its own config mechanism.
- **`ignore = ["F821"]` disables undefined-name checking repo-wide** to hide
  `data: "DDRDataset"` annotations in `requirements.py` that were never imported.
  Replace with a `TYPE_CHECKING` import and delete the global ignore.
- **`key=str(uuid.uuid4())`** per checkbox per rerun (`life4_ui.py:21`) grows
  session state without bound.
- **`sys.path.append("src")`** in `app.py` makes startup depend on the working
  directory while an installed package already exists.

Deferred, noted only: the `src/life4/life4/ranks/` package nesting.

## Testing

Unit tests over requirement logic against small hand-built DataFrames. No
network, no Streamlit, no fixtures pulled from the live document.

```
tests/
  conftest.py            # dataset builders
  test_lamps.py          # _get_lamp precedence, NO_LAMP propagation
  test_requirements.py   # one test per Requirement subclass
  test_merge.py          # field-wise merge, level drift, join integrity
  test_schema.py         # canonical mapping, header assertion failures
```

The bug that motivated this is five lines to prevent:

```python
def test_clear_requirement_without_floor_ignores_unplayed():
    data = dataset_with(level=19, scores=[720_000, 810_000] + [None] * 8)
    assert not ClearRequirement(level=19, num=5).is_satisfied(data)
```

Out of scope: UI tests, loader network tests, golden-file snapshots against live
data (the snapshot would change on every play session).

## Sequencing

1. **Bugs + tests.** Bugs 1, 5, 6, 7 with covering tests. Smallest, most isolated,
   and establishes the fixtures everything later depends on.
2. **Loading.** `/export` + gid config, canonical schema with header assertion,
   caching, delete `OnedriveDataSource`. Fixes bugs 3 and 4 and unblocks the merge.
3. **Merge.** `ScoreMerger`, two chart-pool views, availability classification.
   Fixes bug 2.
4. **World requirements.** Transcribe Pearl–Emerald, add Ruby and the
   folder-average class, fix the `range(14, 20)` hardcode.

Requirements go last deliberately: it touches the most files and benefits from a
stable data layer underneath.

## Open questions

Non-blocking; resolve during the phase that needs them.

1. **`galaxy brave` availability.** Two charts in the WORLD tab carry a marker not
   present in the A3 tab. Likely event-exclusive and therefore `OPTIONAL`, but
   unconfirmed. Defaults to `EXCLUDED` under the allowlist until classified.
2. **MA point values above level 16.** `MFC_POINT_MAPPING` must be extended to 19.
   Values need to come from the LIFE4 site, not be interpolated.
3. **Do Pearl or Topaz have requirements below level 14?** Determines how much the
   `range(14, 20)` fix has to generalize. Answered by reading the pages during
   phase 4.
4. **`CTF` and trials tab gids.** Only the WORLD gid (638900183) is known. Both
   are readable from the tab URLs.
5. **Marking A3-carryover requirements in the UI.** Wanted for honesty about the
   official-rules divergence. Not scoped.
