import sys

sys.path.append("src")  # noqa: E402

import click
import streamlit as st

from life4.ddr import test1
from life4.rank_requirements.a20_plus import test2


def main():

    test1()
    test1()


    # data = DDRDataset(data_path)

    # col1, col2, col3 = st.columns(3)
    # with col1:
    #     pearl_1.visualize(data)
    # with col2:
    #     pearl_2.visualize(data)
    # with col3:
    #     pearl_3.visualize(data)

    # st.markdown("<br><br>", unsafe_allow_html=True)

    # col4, col5 = st.columns(2)
    # with col4:
    #     pearl_4.visualize(data)
    # with col5:
    #     pearl_5.visualize(data)


if __name__ == "__main__":
    main()
