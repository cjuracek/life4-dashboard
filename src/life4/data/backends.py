from life4.data.interfaces import ScoreTrialFetcher
import pandas as pd


class GoogleSheetsDataSource(ScoreTrialFetcher):
    def __init__(self, scores_url: str, trials_url: str):
        self.scores_url = scores_url
        self.trials_url = trials_url

    def load_scores(self) -> pd.DataFrame:
        return pd.read_csv(self.scores_url, thousands=",")

    def load_trials(self) -> pd.DataFrame:
        return pd.read_csv(self.trials_url)


class OnedriveDataSource(ScoreTrialFetcher):
    def __init__(self, onedrive_url: str):
        self.onedrive_url = onedrive_url

    def load_scores(self) -> pd.DataFrame:
        return pd.read_excel(self.onedrive_url)

    def load_trials(self) -> pd.DataFrame:
        return pd.read_excel(self.onedrive_url, sheet_name="Trials")
