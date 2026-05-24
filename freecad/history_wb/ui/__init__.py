"""Module responsibility: User interface."""

# Lazy imports for UI widgets - load through project Qt wrapper boundary
try:
    from .views.diff_panel_view import DiffPanelView
except ImportError:
    # Qt binding not available (running outside FreeCAD)
    DiffPanelView = None  # type: ignore

__all__ = ["DiffPanelView"]
