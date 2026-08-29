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
- Load sheets through a documented endpoint that ignores the sheet's filter view.
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

## Availability markers (resolved 2026-08-29)

The WORLD tab was created by copying the CTF (A3) tab, so its `Availability`
column started life as A3 annotation. On 2026-08-23 the two tabs agreed on
availability for **0 of 5,124** shared charts — one annotation duplicated, not
per-version data — and four markers were provably wrong (charts marked
`course trial` that had been played on World in the previous month).

**The owner re-annotated the WORLD tab on 2026-08-29.** 28 of the 32 markers were
cleared: every `course trial` (17), `phase 2` (7), `extra exclusive` (2), and
`Other` (2) chart is a normal, on-demand song in DDR World. An A3 course-trial
unlock or Extra Stage song frequently becomes a default World song.

Four markers remain:

| Marker | Charts |
|---|---|
| `removed` | Realize ESP 14 · タイガーランペイジ (Tiger rampage) CSP 17 |
| `galaxy brave` | Blizzard of Arrows CSP 17 · Roll the Dice CSP 17 |

All four are unplayed, so only denominators move: **L14 262 → 261**,
**L17 148 → 145**.

The CTF tab keeps its original A3-era markers. This is harmless: `availability`
is taken from WORLD in the merge (see "Merge"), so CTF's markers are never read.

### Classification

The owner's rule: **a marked chart counts if played, but never counts against
you.** A `removed` chart you cleared before it was removed should still credit;
an unplayable chart should not block "all Ns over X".

That collapses the earlier three-class scheme to one rule with no lookup table:

| `availability` | Class | Counts in numerators | Counts in denominators |
|---|---|---|---|
| blank | `NORMAL` | yes | yes |
| **any** marker | `OPTIONAL` | yes | no |

There is no `EXCLUDED` class. An unrecognised marker is `OPTIONAL` like any
other — decided 2026-08-29, on the grounds that a marker means "not necessarily
playable on demand" and so must never block progress. The accepted cost is that
a new marker silently shrinks a denominator; the blocker display below is the
counterweight.

### Blocker display (adopted)

Marking incompleteness is a *separate* defect from marking staleness, and it
fails the opposite way. A genuinely unplayable chart that carries no marker is
counted in the denominator, so the requirement reads harder than reality and can
be permanently unachievable. Unlike the stale markers — 32 cells, now reviewed —
this is not fixable by inspection: it would mean sweeping every unplayed 14–19
chart, which is hundreds.

So it is surfaced rather than annotated. Blockers split into two categories that
behave differently (measured 2026-08-29 against merged data, before `OPTIONAL`
exclusion):

| requirement | total | below floor | unplayed | played-low |
|---|---|---|---|---|
| Amethyst I L14 | 262 | 35 | 32 | 3 |
| Amethyst I L15 | 271 | 62 | 62 | 0 |
| Amethyst I L17 | 148 | 32 | 32 | 0 |
| Emerald I L16 | 217 | 60 | 51 | 9 |
| Emerald I L17 | 148 | 48 | 32 | 16 |

**Unplayed count is a property of the level, not the requirement** — L14 has 32
unplayed charts regardless of target rank (L15: 62, L16: 51, L17: 32, L18: 48,
L19: 10). That set shrinks monotonically as the player plays, and whatever
remains unplayed once everything else is cleared *is* the unplayable set. The
played-low set is a pure practice list and grows with rank; its names are never
useful.

Display: counts always inline, names behind an `st.popover` containing a
scrollable `st.dataframe` sorted by distance from target. Early on the counts are
the information and the list stays closed; late, the list is short and is exactly
the information needed. Same widget in both regimes.

`st.popover` is required because requirement checkboxes already render inside a
rank `st.expander`, and Streamlit does not permit nested expanders.

**Streamlit floor raised to `>=1.62`** (1.62.0 released 2026-08-19; the venv held
1.51.0 against a `>=1.41.1` pin). 1.61 added `st.cache_data(refresh_mode=
"background")`, adopted for the refresh button so re-downloading ~21k rows across
two tabs does not block the page.

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

Each of these was measured against the live document, not inferred. Dates noted
per finding; the gviz diagnosis was corrected on 2026-08-23.

### The gviz endpoint inherits the sheet's filter view

The current loader uses `gviz/tq?tqx=out:csv&sheet=<TabName>`, an undocumented
endpoint of the deprecated Google Visualization API. Measured against the WORLD
tab:

| Endpoint | Rows returned |
|---|---|
| `/export?format=csv&gid=638900183` | 10,821 |
| `/gviz/tq?tqx=out:csv&gid=638900183` | 3,415 |
| `/gviz/...&tq=select * limit 20000` | 3,415 |

**This is not truncation.** An earlier revision of this spec diagnosed it as a
size-dependent row cap; that was wrong. The rule is exact — verified against all
10,821 rows with **zero** mismatches:

```
gviz returns a row  <=>  Diff in {bSP,BSP,DSP,ESP,CSP}  AND  Level >= 8
```

That is a **filter view applied to the WORLD tab** (singles only, level 8+).
`gviz/tq` honours the sheet's active filter; `/export?format=csv` ignores it and
returns the raw grid.

**Both tabs are filtered.** An earlier revision claimed the CTF tab was
unaffected "because it contains no doubles" — that was wrong, and only looked
true because gviz was the only view of CTF available at the time. Loaded via
`/export?format=csv&gid=1003204842` on 2026-08-29:

| CTF tab | Rows |
|---|---|
| `/export` | 9,010 |
| `gviz` | 5,124 |

CTF's filter is singles-only (all four doubles difficulties hidden, 100% of
singles kept, no level component). It caused no visible damage because the app
filters to singles anyway — **but that is coincidence, not safety.** Zero played
charts are hidden by it, so no earlier measurement was affected.

The lesson is the general one: every tab may carry a filter, the filter is
invisible from the response, and it can change at any time from the spreadsheet
UI.

**The conclusion stands, for a better reason.** A data loader must not inherit a
view setting. Today the filter happens to align with what the app wants; if the
filter is ever changed — to inspect level 15+, say — every denominator in the
dashboard silently changes with it, with no error and no visible cause. Progress
numbers must not depend on what the spreadsheet is currently displaying.

Consequence: **the app applies its own singles filter** and never relies on the
sheet's. Already specified in "Loading" below; now for a stated reason rather
than by accident.

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

**Only the columns the app actually reads are mapped.** Audited 2026-08-23:

| | Columns |
|---|---|
| **Read (11)** | `Diff` `Level` `Title` `Score` `Perf`/`P` `Record On` `PFC Date` `GFC Date` `FC Date` `Life4 Date` `Availability` |
| **Unread (10)** | `Marv` `Great` `Good` `O.K.` `Miss` `EX` `MA Ratio` `# times` `Last played` `AAA Date` |

This audit removes the reason for positional mapping. The duplicate `M` in the
WORLD header is Marvelous and Miss — **both unread**. `P` is unambiguous. So
mapping is **by name**, and the duplicate-header problem never arises.

Mapping is **one shared alias table**, not a per-tab schema:

```python
COLUMN_ALIASES = {
    "diff":         {"Diff"},
    "level":        {"Level"},
    "title":        {"Title"},
    "score":        {"Score"},
    "perfect":      {"P", "Perf"},      # WORLD: P, CTF: Perf
    "record_on":    {"Record On"},
    "pfc_date":     {"PFC Date"},
    "gfc_date":     {"GFC Date"},
    "fc_date":      {"FC Date"},
    "life4_date":   {"Life4 Date"},
    "availability": {"Availability"},
}
```

One shared table rather than per-tab dicts, because the tabs have different
maintenance lifecycles: WORLD is live and will drift, CTF is dormant. Per-tab
definitions would mean a WORLD rename silently requires a matching CTF edit that
nobody will remember. With a shared table there is no CTF-specific definition to
forget — adding one alias fixes both tabs at once.

Measured: **10 of the 11 read columns are already identically named in both
tabs.** Only `perfect` differs, so `perfect` is the only entry needing more than
one alias today. Aliases are added when a rename actually happens; no speculative
variants.

**Behaviour on drift:**

| Change | Result |
|---|---|
| Rename/add/reorder an *unread* column | Nothing. Ignored entirely. |
| Add a new column | Nothing. |
| Reorder read columns | Nothing — mapping is by name. |
| Rename a *read* column | **Hard fail at load**, naming tab, canonical field, accepted names, and the actual header. |

Hard failure is deliberate. The two defects this overhaul exists to fix — gviz
the gviz filter leak and stale availability markers — were both *silent*. A load-time
failure fixed by adding one string is strictly better than a dashboard that
quietly reports a rank as closer than it is.

### 3. Merge

WORLD defines the chart pool and every chart's level. A3 contributes score and
achievement history only, joined on `(title, diff)`.

A3 is **dormant, not frozen** — the owner does not currently play it but would
update the tab if they did. Nothing may snapshot, cache to disk, or otherwise
freeze the A3 tab; both tabs are re-read on every load. (Measured 2026-08-23:
scores were *not* copied between tabs — 0 of 168 charts played on both have
identical scores — so the two histories are genuinely independent.)

Per merged chart:

| Field | Rule |
|---|---|
| `level`, `availability` | From WORLD |
| `score` | `max` across sources, NaN-aware |
| date columns | First non-null, WORLD preferred. Only null-ness affects lamp derivation, so no date parsing is needed |
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

#### Title drift and orphan detection

Titles are matched **exactly**. They are never normalized, stripped, or fuzzy
matched.

Measured 2026-08-23: 431 of 1,504 WORLD titles (28.7%) contain a parenthetical.
The owner's markup convention for foreign-language titles — `原題 (romanization,
artist)` — is syntactically **indistinguishable** from DDR's own version markers
`(X-Special)`, `(kskst mix)`, `(PLUS step)`. Stripping the parenthetical to make
matching more forgiving collides on **80 stems**, merging genuinely distinct
charts:

```
'PARANOiA'  ->  PARANOiA  |  PARANOiA(X-Special)  |  PARANOiA (kskst mix)
'革命'       ->  革命 (KAKUMEI, ...)  |  革命 (X-Special) (KAKUMEI (X-Special), ...)
```

Fuzzy matching would trade a rare, detectable failure for a common, silent one.

Detection instead. **WORLD is a strict superset of CTF by construction** (the
WORLD tab was created by copying CTF), so a CTF chart with no WORLD match is
always a defect — a drifted title or a removed song — never normal. Measured
today: **0 orphans**, 245 WORLD-only titles (new songs since the copy, expected).

`merge_scores` returns orphans alongside the merged frame, and the app surfaces
the count and titles. An orphan means A3 scores silently stop counting toward
every requirement — the exact silent-failure class this overhaul exists to
eliminate — so it must be visible in the UI, not only in a log.

### 4. Two chart-pool views

Classification is the one rule from "Availability markers" above: blank is
`NORMAL`, any marker is `OPTIONAL`. `DDRDataset` exposes two views instead of one
filtered frame, and each `Requirement` subclass declares which it consumes:

- **Count-based** (`PFCRequirement`, `AAARequirement`, `ClearRequirement`,
  `CeilingRequirement`, `SDP*`, `MFC*`, `MAPointsRequirement`) → `NORMAL | OPTIONAL`
- **All-chart** (`FloorRequirement`, `LampRequirement`, `LampFloorRequirement`) → `NORMAL` only

`get_level()` is the single chokepoint every requirement calls, so it is the seam
to split.

**No level filtering, ever.** MA points are earned from MFCs and SDPs at *any*
difficulty, and the owner's history is weighted toward low levels: 12 MFCs and 81
SDPs sit below level 8. Restricting the load to level 8+ — which is what the
WORLD tab's filter view does, and what `gviz` therefore returned — costs **11.22
MA points**, dropping the total from 31.72 to 20.50. Emerald I requires 12 and
Emerald V requires 20, so that one filter is worth more than a rank tier. The
only row filter the app applies is singles-vs-doubles.

Filtering doubles is verified safe: the WORLD tab holds 4,669 doubles rows and
**none has a score**, so no MA points are lost.

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
| 2 | `ddr.py` filters | **Live** | Availability is a denylist that drops marked charts from numerators too. Should be: blank counts everywhere, any marker counts if played but never blocks. See "Two chart-pool views". |
| 3 | `backends.py` | **Live** | gviz inherits the sheet's filter view. See findings. |
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

2. **MA point values above level 16.** `MFC_POINT_MAPPING` must be extended to 19.
   Values need to come from the LIFE4 site, not be interpolated.
3. **Do Pearl or Topaz have requirements below level 14?** Determines how much the
   `range(14, 20)` fix has to generalize. Answered by reading the pages during
   phase 4.
4. **`CTF` and trials tab gids.** Only the WORLD gid (638900183) is known. Both
   are readable from the tab URLs.
5. **Marking A3-carryover requirements in the UI.** Wanted for honesty about the
   official-rules divergence. Not scoped.
