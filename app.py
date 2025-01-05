import sys

sys.path.append("src")

import click  # noqa: E402
import streamlit as st  # noqa: E402
from life4.data.backends import OnedriveDataSource, GoogleSheetsDataSource  # noqa: E402

from life4.ddr import DDRDataset  # noqa: E402
from life4.rank_requirements.a20_plus.pearl import (  # noqa: E402
    pearl_1,
    pearl_2,
    pearl_3,
    pearl_4,
    pearl_5,
)

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

    columns = st.columns(5)
    for rank, column in zip([pearl_1, pearl_2, pearl_3, pearl_4, pearl_5], columns):
        with column:
            rank.visualize(data)


if __name__ == "__main__":
    main()
