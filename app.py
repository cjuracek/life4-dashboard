import sys

sys.path.append("src")

import click
import streamlit as st

from life4.data.backends import GoogleSheetsDataSource, OnedriveDataSource
from life4.ddr import DDRDataset
from life4.life4.ranks.a20_plus import pearl, amethyst, emerald
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

    rank_choice = st.selectbox("Select rank", ("Pearl", "Amethyst", "Emerald"), index=1)
    if rank_choice == "Pearl":
        rank = pearl
    elif rank_choice == "Amethyst":
        rank = amethyst
    else:
        rank = emerald

    columns = st.columns(5)
    placeholders = [column.empty() for column in columns]

    for sub_rank, placeholder in zip(rank, placeholders):
        with placeholder:
            rank_display = Life4RankDisplay(sub_rank, data)
            rank_display.visualize()


if __name__ == "__main__":
    main()
