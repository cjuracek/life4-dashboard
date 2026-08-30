import pandas as pd
import streamlit as st

from life4.data.loaders import GoogleSheetLoader
from life4.data.merge import merge_scores
from life4.ddr import DDRDataset
from life4.life4.core import Life4Trial
from life4.life4.ranks.a20_plus import amethyst, emerald
from life4.life4_ui import Life4RankDisplay

SINGLES_DIFFICULTIES = ("bSP", "BSP", "DSP", "ESP", "CSP")

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


def _singles(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["diff"].isin(SINGLES_DIFFICULTIES)]


def load_dataset() -> tuple[DDRDataset, pd.DataFrame]:
    world, a3, trials = load_frames()
    result = merge_scores(_singles(world), _singles(a3))
    trial_models = [Life4Trial(**row) for _, row in trials.iterrows()]
    return DDRDataset(result.charts, trials=trial_models), result.orphans


def main() -> None:
    if st.button("Refresh data"):
        load_frames.clear()

    data, orphans = load_dataset()

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

    rank_choice = st.selectbox("Select rank", ("Amethyst", "Emerald"), index=1)
    rank = amethyst if rank_choice == "Amethyst" else emerald

    for sub_rank, column in zip(rank, st.columns(5)):
        with column:
            Life4RankDisplay(sub_rank, data).visualize()


main()
