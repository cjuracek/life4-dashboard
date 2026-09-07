import logging
import io

import pandas as pd
import requests

from life4.data.schema import normalize

logger = logging.getLogger(__name__)

# The sheet's own CSV download endpoint -- undocumented but long stable.
# `gid` identifies a tab; read it from the `#gid=` fragment in the URL.
_EXPORT_URL = (
    "https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"
)


class GoogleSheetLoader:
    """Reads tabs via the sheet's CSV export endpoint.

    Not gviz/tq: it silently honours the sheet's active filter views and
    returned only a fraction of WORLD's rows with HTTP 200. This endpoint
    returns the raw grid; the app applies its own singles filter.
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
