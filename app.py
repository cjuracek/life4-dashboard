import pandas as pd
import streamlit as st

from life4.data.errors import DataError
from life4.data.loaders import GoogleSheetLoader
from life4.data.merge import merge_scores
from life4.ddr import DDRDataset
from life4.life4.core import Life4RankEnum, Life4Trial
from life4.life4.ranks.registry import IN_SCOPE, load_ranks
from life4.life4_ui import Life4RankDisplay

st.set_page_config(layout="wide")


@st.cache_data(ttl=600, refresh_mode="background")
def load_frames():
    secrets = st.secrets["sheets"]
    loader = GoogleSheetLoader(doc_id=secrets["doc_id"])
    tabs = secrets["tabs"]
    world = loader.load(gid=tabs["world"], tab_name="world")
    a3 = loader.load(gid=tabs["a3"], tab_name="a3")
    trials = loader.load_trials(gid=tabs["trials"])
    return world, a3, trials


def load_dataset() -> tuple[DDRDataset, pd.DataFrame]:
    world, a3, trials = load_frames()
    result = merge_scores(world, a3)
    trial_models = [Life4Trial(**row) for _, row in trials.iterrows()]
    return DDRDataset(result.charts, trials=trial_models), result.orphans


def main() -> None:
    if st.button("Refresh data"):
        load_frames.clear()

    try:
        data, orphans = load_dataset()
    except DataError as exc:
        # Every load-time defect lands here: a renamed column, a garbled cell,
        # a duplicate key. The exceptions carry the remedy in their message, so
        # render that text as text rather than as a traceback.
        st.error("The source sheet could not be loaded.")
        st.code(str(exc), language=None)
        st.stop()

    if len(orphans):
        st.warning(
            f"{len(orphans)} A3 charts no longer match any WORLD chart, so "
            f"their scores are not counting. Usually a drifted title."
        )
        with st.expander("Show unmatched A3 charts"):
            st.dataframe(orphans[["title", "diff", "level", "score"]], height=200)

    _, center, _ = st.columns(3)
    with center:
        st.image("assets/life4-logo.png", width="stretch")

    names = tuple(tier.name for tier in IN_SCOPE)
    rank_choice = st.selectbox("Select rank", names, index=len(names) - 1)
    subranks = load_ranks()[Life4RankEnum[rank_choice]]

    for sub_rank, column in zip(subranks, st.columns(5)):
        with column:
            Life4RankDisplay(sub_rank, data).visualize()


main()
