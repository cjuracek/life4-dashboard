"""Rebuild the conformance fixture from LIFE4's rendered requirements page.

    uv run scripts/fetch_rendered_strings.py

The served HTML contains every rendered requirement string for all 65
sub-ranks. We keep the *strings*, not the sections: section boundaries in
that HTML are damaged -- some lists are truncated and neighbours merge --
but the strings themselves are intact, so membership is the assertion that
holds.

If tests/test_conformance.py fails, fix the formatter, not this fixture.
The fixture is the only ground truth in the suite that is not our own
output; editing it to make a test pass destroys the one check that can
catch a real formatting error.
"""

import html
import re
from pathlib import Path

import requests

PAGE_URL = "https://life4ddr.com/rank-requirements"
FIXTURE = Path(__file__).resolve().parent.parent / "tests/fixtures/life4_rendered.txt"
_MARKER = re.compile(
    r"^(Requirements:|Substitutions:|Complete \d+ of these \d+ requirements:)$"
)


def text_nodes(page: str) -> list[str]:
    stripped = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", page)
    parts = re.sub(r"(?s)<[^>]+>", "\x00", stripped).split("\x00")
    return [text for text in (html.unescape(p).strip() for p in parts) if text]


def requirement_strings(page: str) -> set[str]:
    parts = text_nodes(page)
    marks = [i for i, part in enumerate(parts) if _MARKER.match(part)]
    found: set[str] = set()
    for position, start in enumerate(marks):
        end = marks[position + 1] if position + 1 < len(marks) else len(parts)
        body = [p for p in parts[start + 1 : end] if p not in ("✓", "⇄")]
        # "MA Points" and its value arrive as two separate text nodes.
        merged: list[str] = []
        for part in body:
            if merged and merged[-1] == "MA Points":
                merged[-1] = "MA Points: " + part.lstrip(": ").strip()
                continue
            merged.append(part)
        found.update(merged)
    return found


def main() -> int:
    response = requests.get(PAGE_URL, timeout=30)
    response.raise_for_status()
    strings = sorted(requirement_strings(response.text))
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text("\n".join(strings) + "\n", encoding="utf-8")
    print(f"wrote {FIXTURE} ({len(strings)} strings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
