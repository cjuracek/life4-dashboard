# WORLD Rank Requirements — Design

**Date:** 2026-08-30
**Status:** Agreed
**Supersedes:** the hand-written A20+ requirements in `src/life4/life4/ranks/a20_plus.py`

## Problem

`a20_plus.py` hand-transcribes LIFE4 rank requirements as Python constructor
calls. Two things are wrong with it:

1. **The numbers are stale.** LIFE4 has published a new generation of
   requirements for DDR WORLD. The *shape* is unchanged but the values moved
   throughout. Amethyst I alone:

   | Requirement | `a20_plus.py` | WORLD |
   |---|---|---|
   | FC all 14s over 991k | `(9E, 980k)` | `(14E, 980k)` |
   | LIFE4 all 15s over 980k | `(10E, 955k)` | `(19E, 955k)` |
   | AAA 15s | `105` | `120` |
   | Clear all 16s over 955k | `(14E, 910k)` | `(24E, 910k)` |
   | AAA 16s | `44` | `60` |
   | Clear 18s over 810k | `22` | `26` |

2. **Hand-transcription has no failure signal.** Nothing in the codebase could
   have detected the drift above. The next LIFE4 patch reintroduces the same
   problem.

## Source of truth

LIFE4 serves the complete requirements as unauthenticated JSON:

```
GET https://life4ddr.com/api/ranks
```

65 sub-ranks (13 tiers x 5). Verified byte-identical across repeated fetches,
with stable ordering and stable per-goal `id`s, so it diffs cleanly.

**Decision:** vendor a pretty-printed snapshot of the full response into the
repo. Parse it at load. Refresh it deliberately via a script, so a LIFE4
change arrives as a reviewable git diff.

Rejected alternatives:

- *Keep hand-writing Python.* Repeats the failure above forever.
- *Fetch live at runtime.* Makes the dashboard depend on someone else's uptime
  and lets thresholds change with no diff to review.

The snapshot has a second dividend: it makes strict parsing free. A new field
or an unknown goal type can only appear at the moment the maintainer re-runs
the fetch script and is already reading a diff — never spontaneously in
production. So the parser hard-fails on anything unrecognised, consistent with
`SchemaError` in `life4/data/schema.py` ("silent wrongness is the failure mode
this whole layer exists to prevent").

## Goal vocabulary

Five goal types across the whole API:

| `t` | fields |
|---|---|
| `songs` | `d`, `higher_diff`, `clear_type`, `song_count`, `score`, `exceptions`, `exception_score`, `average_score` |
| `set` | `diff_nums` — "clear 3 11+s in a row" |
| `calories` | `count` |
| `trial` | `rank`, `count` |
| `ma_points` | `points` |

`clear_type` is one of `good`, `life4`, `great`, `perfect`, `marvelous`, `sdp`.

Note that **AAA is not in the data.** It is `score: 990000` — 121 of the 165
scored count-goals in scope. `"AAA"` is a display convention the formatter must
reconstruct.

## Scope

**Pearl, Topaz, Amethyst, Emerald** — 20 sub-ranks, 583 goals.

Copper–Silver are excluded. They use a different structure (`{goals,
required: N}` — choose N of M) and contain `calories` and `set` goals that
cannot be derived from a score sheet. Supporting them would widen
`Requirement.is_satisfied` from a predicate to a tri-state throughout the app,
for ranks with no informational value to this user.

Gold–Diamond, Onyx and Ruby are excluded for now purely as scope. They share
the in-scope structure, so admitting them later is a one-line change to the
scope constant plus whatever new requirement shapes they introduce (Ruby
introduces none beyond Folder Average, which is in scope already).

The snapshot is vendored **in full** (all 65 sub-ranks) even though only four
tiers are parsed. Filtering at fetch time would mix "I want more tiers" with
"LIFE4 changed the numbers" in a single diff. The scope filter runs at parse
time, and must run **before** validation, or Copper's `calories` and `set`
goals trip the strict parser on every load.

## Two requirement families

The `songs` goal splits cleanly on whether `song_count` is present:

| Family | Signature | Meaning | Chart pool |
|---|---|---|---|
| **Count** | `song_count` present | at least N charts at level *d* (or >= *d*) satisfy a predicate | `EARNED` |
| **Folder** | `song_count` absent | *every* chart at level *d* satisfies it, minus exceptions | `REQUIRED` |

This boundary was independently discovered by the existing code: `pool`
defaults to `EARNED`, and exactly three classes override it to `REQUIRED` —
`LampRequirement`, `FloorRequirement`, `LampFloorRequirement`. That is the
Folder family precisely. The `EARNED`/`REQUIRED` distinction (a removed chart
still credits a score you earned, but must never block an "all Xs"
requirement) maps onto the two families exactly.

The field combinations were audited against all 583 in-scope goals. There are
ten, with **zero anomalies**:

```
FOLDER (145)                            COUNT (403)
  (clear_type, exceptions, exception_score, score)   (score, song_count)
  (exceptions, exception_score, score)               (clear_type, song_count)
  (average_score, clear_type, exceptions,            (clear_type, higher_diff, song_count)
   exception_score)                                  (exceptions, exception_score, score, song_count)
  (average_score, clear_type)                        (song_count)
                                                     (exceptions, score, song_count)
```

Invariants confirmed across the whole API:

- `higher_diff` appears **only** on Count goals, and **only** with
  `clear_type` in `{sdp, marvelous}`. Every `sdp`/`marvelous` goal has it;
  no other goal does.
- `average_score` never co-occurs with `score` or `song_count`.
- `exception_score` never appears without `exceptions`.
- `clear_type: sdp` never appears on a Folder goal, so the SDP predicate is
  confined to the Count family.

**Decision:** collapse the 13 existing `Requirement` subclasses to four —
`CountRequirement`, `FolderRequirement`, `MAPointsRequirement`,
`TrialRequirement`. `AAARequirement(15, 105)` *is*
`CountRequirement(level=15, count=105, min_score=990_000)`;
`CeilingRequirement(18, 960_000)` *is* the same class with `count=1`. A
13-class hierarchy whose parser must reverse-engineer which class a goal
belongs to is a hierarchy fighting its input.

`multiple_levels` becomes an instance attribute equal to `higher_diff` on
`CountRequirement` (and `False` on `FolderRequirement`). This preserves
today's UI behaviour: `SDP a 13+` and `MFC an 11+` group under "Other" rather
than under a difficulty heading.

## Exception semantics

An exception excuses a chart from **the whole requirement**, not just its
score component, provided the chart clears the shadow floor.

```
chart passes  <=>  (lamp >= required) AND (score >= floor)
otherwise     <=>  may consume an exception slot if score >= shadow_floor
```

This differs from the current `LampFloorRequirement`, which composes
`LampRequirement AND FloorRequirement` and lets only the floor consume
exceptions — making the lamp absolute.

The evidence is `PFC all 14s with a 999,500 Folder Average (4E, 996k)`. A
PFC's score is exactly `1,000,000 - 10 x perfects`, so a PFC below 996,000
requires more than 400 Perfects on one chart — impossible on charts under
~400 notes, and vanishingly rare otherwise (real PFCs sit at 999,000+). Under
the lamp-absolute reading the `(4E, 996k)` clause excuses a thing that cannot
happen, i.e. it is dead syntax. Under the unified reading it does real work:
four charts need not be PFCs at all, provided they clear 996k.

A reading that renders LIFE4's own syntax inert is the wrong reading.

*(Note: the intuition that "980k cannot be a Full Combo score" is false and is
not the basis for this decision. `Lamp.Blue` is a Good FC — Greats and Goods
both allowed. On a ~400-note 14 a Great costs ~1,000 and a Good ~2,000, so
980k is 20 Greats or 10 Goods: an ordinary sloppy FC.)*

## Folder Average

`{d, clear_type, average_score, exceptions, exception_score}` — five goals,
all Emerald substitutions, all at level 14, all `clear_type: perfect`.

Satisfied when:

1. Every chart at the level in the `REQUIRED` pool is **played**. An unplayed
   chart fails the requirement, as `FloorRequirement` already does.
2. Every chart satisfies `lamp >= Gold`, except at most `exceptions` charts,
   which must score >= `exception_score` (the unified rule above).
3. `mean(score)` over **all** charts in the pool >= `average_score`.

Exception charts count toward the mean. If they did not, `exception_score`
would be doing nothing — a carved-out chart cannot affect an average it is not
part of, so bounding its score would be pointless. The shadow floor only earns
its place if those charts are in the denominator.

Progress renders as `Lamp 187/191; Avg 999,412/999,500`, reusing the existing
`LampFloorRequirement` semicolon convention. `blockers()` lists only charts
failing the lamp condition — the average has no single culprit chart.

## SDP vs MFC

An MFC **satisfies** an SDP requirement. `clear_type: sdp` appears 40 times in
scope (`SDP a 13+`, `SDP 5 14+s`). An MFC is a full combo with zero Perfects;
zero is a single digit, and an MFC is strictly better than any SDP. Today
`get_sdps()` filters `lamp == Lamp.Gold`, and `_get_lamp` returns `Lamp.White`
for a 1,000,000 — so lamps are mutually exclusive and `SDP a 13+` is currently
unsatisfiable by the best possible score at that level.

An MFC does **not** contribute SDP points to MA Points. That table is a
scoring lookup, not a predicate: a chart falls in exactly one row, and an MFC
takes the MFC value. A level-15 MFC is worth 15 points, not 16.5.

**Decision:** two functions.

- `DDRDataset.get_sdp_or_better()` — requirement predicate. `lamp >= Gold AND
  (perfect < 10 OR lamp == White)`.
- `DDRDataset.get_sdps()` — unchanged, used only by `get_ma_points()`.

## Wording

Requirement strings must reproduce LIFE4's rendering **exactly**. This is what
repays the readability lost by deleting 500 lines of literals: a generated
snapshot is only a substitute for greppable source if it is verifiably the
same sentences LIFE4 prints.

The data discards vocabulary the display must reconstruct — `score: 990000` ->
`"AAA"`, `clear_type: "life4"` -> `"LIFE4 Clear"`, `song_count: 1` -> `"a"`/
`"an"`. Three reconstruction rules, three places to be quietly wrong.

Rules, derived from LIFE4's own i18n templates and verified against their
rendered output:

```
clear type labels   good -> "Full Combo"    life4 -> "LIFE4 Clear"
                    great -> "Great Full Combo"
                    perfect -> "PFC"   marvelous -> "MFC"   sdp -> "SDP"

score token         990000 -> "AAA";  round thousands -> "996k";  else "998,500"
article             "an" before 8, 11, 18; "a" otherwise

COUNT, no exceptions   "{head} {article} {d}{+}"     when song_count == 1
                       "{head} {count} {d}{+}s"      otherwise
                       head = clear-type label, else score token, else "Clear"
COUNT, exceptions      "Clear {count} {d}s over {score}"
FOLDER                 "{verb} all {d}s over {score}"
FOLDER, average        "{verb} all {d}s with a {avg:,} Folder Average"
exception clause       " ({n}E, {score})"  or  " ({n}E)"
```

The exception-vs-count distinction in the Count family is **not** cosmetic and
was initially got wrong: the template keys off whether exceptions are present,
not off the count. LIFE4 renders `{d: 18, score: 750000, song_count: 5}` as
`750k+ 5 18s`, not `Clear 5 18s over 750k`.

### Conformance

The served HTML of `https://life4ddr.com/rank-requirements` contains all 1263
rendered requirement strings for all 65 sub-ranks. With the rules above,
**every one of the 1259 generated strings appears verbatim in that output**
(the 4 remaining DOM strings are MA Points table cells, not requirements).

The fixture is **string-level, not section-level**. Section boundaries in the
served HTML are damaged — some lists are truncated and neighbours merge — but
the strings themselves are intact. Two tests:

1. **Conformance** — every generated in-scope string is a member of the
   committed set of LIFE4-rendered strings. This is the only test in the
   design that can show the formatter is *wrong* rather than merely *changed*.
2. **Regression snapshot** — the full generated output per sub-rank, committed.
   Membership alone would let a swap (rendering goal A's string for goal B)
   pass, since both strings are legitimate somewhere. The snapshot pins the
   goal-to-string mapping so a swap surfaces as a reviewable diff.

## Rank enum

`Life4RankEnum` currently has `Diamond = 4, Platinum = 5`. The real order is
Gold -> Platinum -> Diamond. `TrialRequirement.is_satisfied` does
`trial.rank >= self.rank`, so this is a live comparison bug, dormant only
because the app renders tiers whose trial gates sit above both. Fix the order
and add `Ruby`, which the API's `trial.rank` domain already includes.

## UI

Minimal. The selectbox is driven off the parsed registry so it lists Pearl,
Topaz, Amethyst and Emerald. Everything else is untouched.

`Life4RankDisplay._visualize_reqs` groups by `range(14, 20)`; verified safe for
this scope, since every in-scope goal is either at level 14-19 or is an
`sdp`/`marvelous` `N+` goal that sets `multiple_levels` and lands under
"Other".

Deliberately **not** done: reworking navigation to answer "which sub-rank am I
on". That needs a definition of current sub-rank that the data does not
contain (LIFE4 holds the approved rank, not this sheet), and is a separate
design tree.

Also deliberately not done: distinguishing "complete" from "complete via
substitutions" in the status glyph. This dashboard is not a submission tool,
so the distinction buys nothing.

## Refresh

`scripts/fetch_ranks.py` rewrites the vendored snapshot; `--check` fetches and
compares, exiting nonzero on drift without writing. The test suite stays
offline — no test hits the network.

Automating `--check` on a schedule is tracked separately in
[issue #28](https://github.com/cjuracek/life4-dashboard/issues/28) and is out
of scope here.

## Out of scope

- Copper–Silver tiers; `calories` and `set` goal types
- Gold, Platinum, Diamond, Cobalt, Onyx, Ruby tiers
- Retaining A20+ requirements as a selectable generation — `a20_plus.py` is
  deleted. LIFE4 no longer supports those requirements and the user plays
  WORLD exclusively; git retains the file.
- The scheduled CI drift check (issue #28)
