"""Module responsibility: Data presentation."""

from ..state import UIState
from .diff_presenter import DiffPresenter
from .snapshot_presenter import SnapshotPresenter


# Backward compatibility alias - ApplicationState renamed to UIState
ApplicationState = UIState


__all__ = ["SnapshotPresenter", "DiffPresenter", "UIState", "ApplicationState"]
