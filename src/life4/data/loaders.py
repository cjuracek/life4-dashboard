import logging
import io

import pandas as pd
import requests

from life4.data.schema import normalize

logger = logging.getLogger(__name__)

_EXPORT_URL = (
    "https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"
)


class GoogleSheetLoader:
    """Reads tabs via the documented CSV export endpoint.

    Deliberately not gviz/tq: that endpoint honours whatever filter view is
    active on the sheet. The WORLD tab has one (singles, level 8+), so gviz
    returned 3,415 of 10,821 rows with HTTP 200 and no warning. Today that
    filter happens to align with what the app wants; if it is ever changed,
    every denominator would shift with no error and no visible cause.

    /export?format=csv ignores filters and returns the raw grid. The app then
    applies its own singles filter explicitly.
    """

    def __init__(self, doc_id: str, timeout: int = 30):
        self.doc_id = doc_id
        self.timeout = timeout

    def csv_url(self, gid: int) -> str:
        return _EXPORT_URL.format(doc_id=self.doc_id, gid=gid)

    def load(self, gid: int, tab_name: str) -> pd.DataFrame:
        url = self.csv_url(gid)
        logger.info("Loading tab %s from %s", tab_name, url)
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return normalize(response.text, tab_name)

    def load_trials(self, gid: int) -> pd.DataFrame:
        """Trials use their own column names and are not normalized."""
        response = requests.get(self.csv_url(gid), timeout=self.timeout)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        return df.loc[:, ~df.columns.str.startswith("Unnamed:")]
