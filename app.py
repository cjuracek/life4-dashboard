import sys

sys.path.append("src")  # noqa: E402

import click
import streamlit as st

st.set_page_config(layout="wide")

from life4.ddr import DDRDataset
from life4.rank_requirements.a20_plus import pearl_1, pearl_2, pearl_3, pearl_4, pearl_5


@click.command()
@click.option(
    "--data-path",
    default=st.secrets["onedrive_data_link"],
    type=str,
    help="Path to data file",
)
def main(data_path: str):
    data = DDRDataset(data_path)

    columns = st.columns(5)
    for rank, column in zip([pearl_1, pearl_2, pearl_3, pearl_4, pearl_5], columns):
        with column:
            rank.visualize(data)


if __name__ == "__main__":
    main()
