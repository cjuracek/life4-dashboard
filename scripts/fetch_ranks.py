"""Refresh the vendored LIFE4 rank-requirements snapshot.

    uv run scripts/fetch_ranks.py            # rewrite the snapshot
    uv run scripts/fetch_ranks.py --check    # exit 1 if live differs

The snapshot is what the app parses. Fetching live at runtime would make the
dashboard depend on someone else's uptime and let thresholds change with no
diff to review; vendoring turns a LIFE4 patch into a reviewable commit.

Committed pretty-printed on purpose. The raw response is a single 105KB line,
which git would diff as one changed line the width of the file.
"""

import argparse
import json
import sys
from pathlib import Path

import requests

API_URL = "https://life4ddr.com/api/ranks"
SNAPSHOT = (
    Path(__file__).resolve().parent.parent / "src/life4/life4/ranks/data/ranks.json"
)


def render(payload) -> str:
    return json.dumps(payload, indent=2) + "\n"


def fetch() -> str:
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    return render(response.json())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare live against the snapshot without writing; exit 1 on drift",
    )
    args = parser.parse_args()

    live = fetch()
    if args.check:
        current = SNAPSHOT.read_text(encoding="utf-8") if SNAPSHOT.exists() else ""
        if live == current:
            print(f"up to date ({len(json.loads(live))} sub-ranks)")
            return 0
        print(
            f"DRIFT: {API_URL} differs from the vendored snapshot.\n"
            f"  {SNAPSHOT}\n"
            "Run without --check and review the diff.",
            file=sys.stderr,
        )
        return 1

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(live, encoding="utf-8")
    print(f"wrote {SNAPSHOT} ({len(json.loads(live))} sub-ranks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
