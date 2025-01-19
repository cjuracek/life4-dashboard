import sys

sys.path.append("src")

import click
import streamlit as st

from life4.data.backends import GoogleSheetsDataSource, OnedriveDataSource
from life4.ddr import DDRDataset
from life4.life4.ranks.a20_plus import (
    amethyst_1,
    amethyst_2,
    amethyst_3,
    amethyst_4,
    amethyst_5,
    pearl_1,
    pearl_2,
    pearl_3,
    pearl_4,
    pearl_5,
)
from life4.life4_ui import Life4RankDisplay

st.set_page_config(layout="wide")


def data_source_factory(data_source_info: dict):
    source = data_source_info.pop("source")
    if source == "onedrive":
        return OnedriveDataSource(**data_source_info)
    elif source == "google":
        return GoogleSheetsDataSource(**data_source_info)
    else:
        raise ValueError("Unsupported data source URL")


@click.command()
@click.option(
    "--data-source",
    default=st.secrets["data_source"],
    type=dict,
    help="Information about the data source to read from",
)
def main(data_source: dict):
    data_source = data_source_factory(data_source)
    data = DDRDataset(data_source=data_source)

    _, cent_co, _ = st.columns(3)
    with cent_co:
        st.image("assets/life4-logo.png", width=10, use_container_width=True)

    rank_choice = st.selectbox("Select rank", ("Pearl", "Amethyst"), index=0)
    if rank_choice == "Pearl":
        subranks = [pearl_1, pearl_2, pearl_3, pearl_4, pearl_5]
    else:
        subranks = [amethyst_1, amethyst_2, amethyst_3, amethyst_4, amethyst_5]

    columns = st.columns(5)
    for rank, column in zip(subranks, columns):
        column = column.empty()
        with column:
            rank_display = Life4RankDisplay(rank, data)
            rank_display.visualize()


if __name__ == "__main__":
    main()
