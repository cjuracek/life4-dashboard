import click
import streamlit as st

from life4.ddr import DDRDataset
from life4.rank_requirements.a20_plus import pearl_1, pearl_2, pearl_3


@click.command()
@click.option("--data-path", required=True, type=str, help="Path to data file")
def main(data_path: str):
    data = DDRDataset(data_path)
    col1, col2, col3 = st.columns(3)
    with col1:
        pearl_1.visualize(data)
    with col2:
        pearl_2.visualize(data)
    with col3:
        pearl_3.visualize(data)


if __name__ == "__main__":
    main()
