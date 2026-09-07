"""Regenerate the goal-to-string snapshot pinned by tests/test_conformance.py.

    uv run scripts/write_rendered_snapshot.py

The test used to write this file itself when it was missing, which made it
an expectation the code under test could author -- it could not fail on a
fresh checkout. Regenerating is a deliberate act now: run this, then review
the diff before committing.

Reviewing the diff is the whole point. Membership against LIFE4's rendered
output cannot catch a swap (goal A rendered with goal B's string, both
legitimately published), so this file is what pins goal to string. A diff
accepted without reading it forfeits that.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from test_conformance import SNAPSHOT, rendered_report  # noqa: E402


def main() -> int:
    SNAPSHOT.write_text(rendered_report(), encoding="utf-8")
    print(f"wrote {SNAPSHOT}")
    print("Review the diff before committing -- see this script's docstring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
