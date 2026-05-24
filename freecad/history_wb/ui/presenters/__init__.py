"""Module responsibility: Data presentation."""

from ..state import UIState
from .diff_presenter import DiffPresenter


# Backward compatibility alias - ApplicationState renamed to UIState
ApplicationState = UIState


__all__ = ["DiffPresenter", "UIState", "ApplicationState"]
