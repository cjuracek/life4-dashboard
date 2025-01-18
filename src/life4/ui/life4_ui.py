import uuid
from typing import List

import streamlit as st

from src.life4 import Life4Rank
from src.life4.ddr import DDRDataset


class Life4RankDisplay:
    def __init__(self, life4_rank: Life4Rank, data: DDRDataset):
        self.life4_rank = life4_rank
        self.data = data

    def create_checkbox(self, requirement: "Requirement"):
        st.checkbox(
            requirement.display_str(self.data),
            disabled=True,
            value=requirement.is_satisfied(self.data),
            key=str(uuid.uuid4()),
        )

    def _visualize_reqs(self, requirements: List["Requirement"]):
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
            _ = [self.create_checkbox(level_req) for level_req in level_reqs]

        st.write("Other")
        _ = [self.create_checkbox(req) for req in requirements if req.multiple_levels]

    def visualize(self):
        """Visualize rank_requirements + substitutions as a series of Streamlit checkboxes in collapsible menu"""
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
            self._visualize_reqs(self.life4_rank.requirements)
            st.write("Substitutions")
            self._visualize_reqs(self.life4_rank.substitutions)
