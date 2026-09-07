import pytest

import pandas as pd

from life4.data.errors import ValueDefectError
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


# --- singles filter ---------------------------------------------------------


def _rows(*csv_rows: str) -> str:
    header = (
        "Diff,Level,Title,Score,P,Record On,PFC Date,GFC Date,FC Date,"
        "Life4 Date,Availability\n"
    )
    return header + "".join(csv_rows)


def test_doubles_rows_are_dropped():
    csv = _rows(
        "ESP,16,Singles,999670,4,4/1/2026,,,,,\n",
        "EDP,16,Doubles,999670,4,4/1/2026,,,,,\n",
    )
    df = normalize(csv, "world")
    assert df["title"].tolist() == ["Singles"]


def test_an_unrecognised_doubles_slot_is_still_dropped_quietly():
    # Doubles are recognised by their DP suffix, not an allow-list, so a slot
    # this app has never seen must not stop it.
    csv = _rows("XDP,16,Exotic,999670,4,4/1/2026,,,,,\n")
    assert normalize(csv, "world").empty


def test_a_typod_singles_code_fails_instead_of_vanishing():
    csv = _rows("ESp,16,Typo,999670,4,4/1/2026,,,,,\n")
    with pytest.raises(ValueDefectError) as exc:
        normalize(csv, "world")
    assert "ESp" in str(exc.value)


def test_doubles_defects_do_not_stop_the_app():
    # The doubles half of the sheet is not curated. Nothing downstream reads
    # it, so its bad cells must not gate startup.
    csv = _rows(
        "ESP,16,Singles,999670,4,4/1/2026,,,,,\n",
        "EDP,,Doubles,not-a-score,4,4/1/2026,,,,,\n",
    )
    assert normalize(csv, "world")["title"].tolist() == ["Singles"]


# --- coercion loss ----------------------------------------------------------


def test_a_garbled_number_fails_rather_than_becoming_nan():
    csv = _rows("ESP,16,Broken,9x9670,4,4/1/2026,,,,,\n")
    with pytest.raises(ValueDefectError) as exc:
        normalize(csv, "world")
    message = str(exc.value)
    assert "score" in message
    assert "9x9670" in message


def test_one_junk_cell_does_not_silently_nan_every_comma_formatted_score():
    # thousands="," is a per-column decision in read_csv: one unparseable cell
    # leaves the whole column as strings, and every comma-formatted value in it
    # then coerces to NaN. Nulls are legal in score, so no range rule sees this.
    csv = _rows(
        'ESP,16,Good,"999,670",4,4/1/2026,,,,,\n',
        "ESP,16,Junk,pending,4,4/1/2026,,,,,\n",
    )
    with pytest.raises(ValueDefectError) as exc:
        normalize(csv, "world")
    assert "pending" in str(exc.value)


def test_the_message_leads_with_the_junk_cell_not_its_innocent_neighbours():
    # Follows from the case above. Once one bad cell strings the column, the
    # comma-formatted scores outnumber the culprit and sort ahead of it, so a
    # truncated list named five innocent rows and hid the only cell worth
    # fixing. The genuinely unparseable cells must lead.
    good = "".join(f'ESP,16,Good{i},"99{i},670",4,4/1/2026,,,,,\n' for i in range(9))
    csv = _rows(good, "ESP,16,TheCulprit,pending,4,4/1/2026,,,,,\n")
    with pytest.raises(ValueDefectError) as exc:
        normalize(csv, "world")
    message = str(exc.value)
    assert "pending" in message
    assert "TheCulprit" in message


def test_a_blank_numeric_cell_is_not_a_coercion_loss():
    csv = _rows("ESP,16,Unplayed,,,,,,,,\n")
    assert pd.isna(normalize(csv, "world").loc[0, "score"])


def test_the_message_names_the_sheet_row():
    csv = _rows(
        "ESP,16,Fine,999670,4,4/1/2026,,,,,\n",
        "ESP,16,Broken,9x9670,4,4/1/2026,,,,,\n",
    )
    with pytest.raises(ValueDefectError) as exc:
        normalize(csv, "world")
    # Header is line 1, the good row is line 2, so the offender is line 3.
    assert "row 3" in str(exc.value)


# --- value ranges -----------------------------------------------------------


def test_a_missing_level_fails():
    # A NaN level drops the row out of every get_level() bucket, so a real 16
    # disappears from "All 16s over 920k" instead of blocking it.
    csv = _rows("ESP,,No Level,999670,4,4/1/2026,,,,,\n")
    with pytest.raises(ValueDefectError) as exc:
        normalize(csv, "world")
    assert "level" in str(exc.value)


def test_a_level_outside_1_to_19_fails():
    csv = _rows("ESP,20,Too High,999670,4,4/1/2026,,,,,\n")
    with pytest.raises(ValueDefectError):
        normalize(csv, "world")


def test_a_fractional_level_fails():
    csv = _rows("ESP,16.5,Fractional,999670,4,4/1/2026,,,,,\n")
    with pytest.raises(ValueDefectError):
        normalize(csv, "world")


def test_a_score_above_the_maximum_fails():
    csv = _rows("ESP,16,Extra Digit,9996700,4,4/1/2026,,,,,\n")
    with pytest.raises(ValueDefectError) as exc:
        normalize(csv, "world")
    assert "score" in str(exc.value)


def test_a_null_score_is_allowed_because_it_means_unplayed():
    csv = _rows("ESP,16,Unplayed,,,,,,,,\n")
    assert pd.isna(normalize(csv, "world").loc[0, "score"])


def test_a_blank_title_fails():
    csv = _rows("ESP,16, ,999670,4,4/1/2026,,,,,\n")
    with pytest.raises(ValueDefectError) as exc:
        normalize(csv, "world")
    assert "title" in str(exc.value)


def test_perfect_is_not_range_checked():
    # Only its coercion is guarded; there is no known bound on the count.
    csv = _rows("ESP,16,Odd,999670,9999,4/1/2026,,,,,\n")
    assert normalize(csv, "world").loc[0, "perfect"] == 9999
