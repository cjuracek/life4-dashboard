import math
import re
import unicodedata
from typing import List

import streamlit as st

from life4.ddr import DDRDataset
from life4.life4.core import Life4Rank
from life4.life4.ranks.requirements import FLARE_NOTE, BlockerReport, Requirement


# A handful of titles run long even romanized ("Kanbu de tomatte sugu tokeru ~
# kyouki no Udongein (overdrive)"). Sizing to those would push the score far
# from every other song and keep the dialog large, so they cut off instead.
_MAX_TEXT_WIDTH = 420


def _text_width(header: str, values) -> int:
    # Source Sans at 14px: Latin runs at most ~7px a character (all caps
    # included), CJK ~14px. Overshooting leaves a little air; undershooting
    # cuts the text off.
    def px(text: str) -> int:
        return sum(14 if unicodedata.east_asian_width(c) in "WF" else 7 for c in text)

    widest = 24 + max(px(header), *(px(str(v)) for v in values))
    return min(widest, _MAX_TEXT_WIDTH)


def _column_widths(rows) -> dict[str, int]:
    # The grid sizes a column from a sample of its first rows and ignores
    # outliers, so a long title or lamp further down gets cut off. Size each
    # column from its longest value instead.
    widths = {name: _text_width(name, rows[name]) for name in rows.columns}
    widths["score"] = _text_width("score", (f"{v:,.0f}" for v in rows["score"]))
    return widths


def _header(name: str) -> str:
    # Capitalize the first letter only: "to LIFE4 Clear" -> "To LIFE4 Clear".
    return name[:1].upper() + name[1:]


def _blocker_table(rows) -> None:
    widths = _column_widths(rows)
    column_config = {
        name: st.column_config.Column(_header(name), width=width)
        for name, width in widths.items()
    }
    # "%,d" always groups with commas; "localized" would follow the viewer's
    # browser locale.
    column_config["score"] = st.column_config.NumberColumn(
        _header("score"), format="%,d", width=widths["score"]
    )
    st.dataframe(
        rows,
        hide_index=True,
        # "stretch" pads every column to fill the dialog, pushing the numbers
        # far from the song they belong to.
        width="content",
        column_config=column_config,
    )


def _title_grid(titles: list[str], n_columns: int = 3) -> None:
    # A title is the only thing to show for these, so a one-column table
    # would leave most of the dialog empty and scroll past ten rows. Fill
    # down then across, so the list still reads alphabetically.
    per_column = math.ceil(len(titles) / n_columns)
    for column, start in zip(st.columns(n_columns), range(0, len(titles), per_column)):
        chunk = titles[start : start + per_column]
        column.markdown("\n".join(f"- {_escape_markdown(t)}" for t in chunk))


def _escape_markdown(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|~<>$])", r"\\\1", text)


# A "medium" dialog is 750px wide with 24px padding on each side.
_MEDIUM_DIALOG_CONTENT = 702


def _dialog_width(report: BlockerReport) -> str:
    # Tables are sized to their contents, so a "large" dialog is mostly empty
    # space unless a wide table needs it. A collapsed table still counts:
    # expanding it must not scroll sideways.
    tables = [report.required_rows, report.exception_rows]
    widest = max(
        (sum(_column_widths(t).values()) for t in tables if not t.empty), default=0
    )
    return "medium" if widest <= _MEDIUM_DIALOG_CONTENT else "large"


def _show_blockers(requirement_label: str, report: BlockerReport) -> None:
    # The requirement is what the player came to look at, so it takes the
    # title slot. The decorator only takes a fixed title, so build it here.
    st.dialog(requirement_label, width=_dialog_width(report))(_blocker_dialog)(report)


# A dialog title holds one line, so the header captions stand in for a
# subtitle. Streamlit spaces them like any other element, which leaves them
# floating between the title and the tables; this pulls them up under it.
# The style sits inside the gapless container, where its empty element adds
# no space.
_DIALOG_HEADER_KEY = "blocker-header"
_DIALOG_HEADER_CSS = (
    f"<style>.st-key-{_DIALOG_HEADER_KEY} {{margin-top: -1.625rem; gap: 0}}</style>"
)


def _section(title: str, *, expanded: bool):
    # Compact: a bordered expander around a bordered table reads as a box in
    # a box. Every section uses it, so the three headings match.
    return st.expander(f"**{title}**", expanded=expanded, type="compact")


def _blocker_dialog(report: BlockerReport) -> None:
    if lines := report.header_lines():
        with st.container(key=_DIALOG_HEADER_KEY):
            st.html(_DIALOG_HEADER_CSS)
            for line in lines:
                # Markdown would turn the footnote's leading "* " into a bullet.
                st.caption(_escape_markdown(line))
    if not report.unplayed_rows.empty:
        # Every one of these has to be played, so they lead, open.
        with _section(report.unplayed_title(), expanded=True):
            _title_grid(list(report.unplayed_rows["song"]))
    if not report.required_rows.empty:
        with _section(report.required_title(), expanded=True):
            _blocker_table(report.required_rows)
    if not report.exceptions_allowed:
        return
    if report.exception_rows.empty:
        # No table to title, but the budget is still worth seeing.
        st.caption(f"**{report.exceptions_title()}**")
        return
    # Under budget nothing in the pool has to change, so it starts closed;
    # over budget the player has to pick from it, so it opens.
    with _section(report.exceptions_title(), expanded=report.over_budget):
        _blocker_table(report.exception_rows)


class Life4RankDisplay:
    def __init__(self, life4_rank: Life4Rank, data: DDRDataset):
        self.life4_rank = life4_rank
        self.data = data

    def create_checkbox(self, requirement: Requirement, group: str):
        satisfied = requirement.is_satisfied(self.data)
        label = _escape_markdown(requirement.display_str(self.data))
        # A keyed checkbox's identity is its key alone, so Streamlit keeps its
        # session value and ignores `value=` on later reruns. Keying on
        # `satisfied` makes a flip after "Refresh data" a new widget.
        st.checkbox(
            label,
            disabled=True,
            value=satisfied,
            # On the requirement itself: a note under a long list is one the
            # player has to go looking for.
            help=FLARE_NOTE if requirement.flare_counts else None,
            key=f"{self.life4_rank}|{group}|{requirement}|{satisfied}",
        )
        if satisfied:
            return

        report = requirement.blockers(self.data)
        if report.empty:
            return

        if st.button(
            report.label(), key=f"{self.life4_rank}|{group}|{requirement}|blockers"
        ):
            title = _escape_markdown(requirement.blocker_title(self.data))
            _show_blockers(title, report)

    def _visualize_reqs(self, requirements: List[Requirement], group: str):
        requirement_levels = range(14, 20)
        level_to_requirements = {
            level: [
                req
                for req in requirements
                if not req.multiple_levels and req.level == level
            ]
            for level in requirement_levels
        }
        for level, level_reqs in level_to_requirements.items():
            if not level_reqs:
                continue

            st.write(f"{level}s")
            _ = [self.create_checkbox(level_req, group) for level_req in level_reqs]

        st.write("Other")
        _ = [
            self.create_checkbox(req, group)
            for req in requirements
            if req.multiple_levels
        ]

    def visualize(self):
        """Visualize ranks + substitutions as a series of Streamlit checkboxes in collapsible menu"""
        completed_requirements = len(
            [req for req in self.life4_rank.requirements if req.is_satisfied(self.data)]
        )
        total_requirements = len(self.life4_rank.requirements)
        available_substitutions = len(
            [
                sub
                for sub in self.life4_rank.substitutions
                if sub.is_satisfied(self.data)
            ]
        )
        expander_title = f"**{self.life4_rank.rank.name} {self.life4_rank.subrank}**"

        status_emoji = (
            ":white_check_mark:"
            if completed_requirements + available_substitutions >= total_requirements
            else ":construction:"
        )
        expander_title += f" {status_emoji}"

        progress = f"{completed_requirements}/{total_requirements}"
        expander_title += f"\n\n  • {progress} requirements completed\n\n  • {available_substitutions} substitutions available"
        with st.expander(expander_title, expanded=False):
            st.markdown("Requirements")
            self._visualize_reqs(self.life4_rank.requirements, group="req")
            st.markdown("Substitutions")
            self._visualize_reqs(self.life4_rank.substitutions, group="sub")
