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
        chart(
            title="a",
            level=16,
            score=999_950,
            record_on="1/1/2026",
            pfc_date="1/2/2026",
        ),
        chart(title="b", level=16),
    )
    assert d.get_level_lamp(16) == Lamp.NO_LAMP


def test_level_lamp_of_a_level_with_no_charts_is_no_lamp():
    d = dataset(chart(title="a", level=16))
    assert d.get_level_lamp(19) == Lamp.NO_LAMP
