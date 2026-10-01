import math
import re
from typing import List

import streamlit as st

from life4.ddr import DDRDataset
from life4.life4.core import Life4Rank
from life4.life4.ranks.requirements import BlockerReport, Requirement


def _blocker_table(rows) -> None:
    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        # "%,d" always groups with commas; "localized" would follow the
        # viewer's browser locale.
        column_config={"score": st.column_config.NumberColumn(format="%,d")},
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


def _show_blockers(requirement_label: str, report: BlockerReport) -> None:
    # The requirement is what the player came to look at, so it takes the
    # title slot. The decorator only takes a fixed title, so build it here.
    st.dialog(requirement_label, width="large")(_blocker_dialog)(report)


def _section(title: str, *, expanded: bool):
    # Compact: a bordered expander around a bordered table reads as a box in
    # a box. Every section uses it, so the three headings match.
    return st.expander(f"**{title}**", expanded=expanded, type="compact")


def _blocker_dialog(report: BlockerReport) -> None:
    for line in report.header_lines():
        st.caption(line)
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
        # A keyed checkbox's identity is its key alone, so Streamlit keeps its
        # session value and ignores `value=` on later reruns. Keying on
        # `satisfied` makes a flip after "Refresh data" a new widget.
        st.checkbox(
            requirement.display_str(self.data),
            disabled=True,
            value=satisfied,
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
            _show_blockers(requirement.display_str(self.data), report)

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
            st.write("Requirements")
            self._visualize_reqs(self.life4_rank.requirements, group="req")
            st.write("Substitutions")
            self._visualize_reqs(self.life4_rank.substitutions, group="sub")
