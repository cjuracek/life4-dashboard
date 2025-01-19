from typing import Protocol

import pandas as pd


class ScoreTrialFetcher(Protocol):
    def load_scores(self) -> pd.DataFrame:
        ...

    def load_trials(self) -> pd.DataFrame:
        ...
