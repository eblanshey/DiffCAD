"""File responsibility: Shared models for UI views layer.

This module contains data classes and models that are shared across multiple
UI components and need to be imported without causing circular dependencies.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class HistorySelection:
    """Represents a selected item in the history list.

    Attributes:
        item_kind: One of "WORKING_TREE", "STAGING", or "COMMIT"
        commit_hash: Only set when item_kind == "COMMIT"
    """

    item_kind: Literal["WORKING_TREE", "STAGING", "COMMIT"]
    commit_hash: str | None
