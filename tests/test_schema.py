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
