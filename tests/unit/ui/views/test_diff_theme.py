"""File responsibility: Unit tests for theme-aware diff color helpers."""

import pytest
from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.qt import QtGui
from freecad.history_wb.ui.views.diff_theme import background_for_state, foreground_for_background


def _palette(base: QtGui.QColor, text: QtGui.QColor, window: QtGui.QColor) -> QtGui.QPalette:
    """Build a minimal palette for diff theme tests."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Base, base)
    palette.setColor(QtGui.QPalette.ColorRole.Text, text)
    palette.setColor(QtGui.QPalette.ColorRole.Window, window)
    return palette


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (DiffState.ADDED, QtGui.QColor(200, 255, 200)),
        (DiffState.DELETED, QtGui.QColor(255, 200, 200)),
        (DiffState.MODIFIED, QtGui.QColor(200, 200, 255)),
    ],
)
def test_light_theme_uses_original_bright_backgrounds_with_black_text(state: DiffState, expected: QtGui.QColor) -> None:
    """Light themes keep original bright highlight colors and black text."""
    palette = _palette(base=QtGui.QColor(255, 255, 255), text=QtGui.QColor(0, 0, 0), window=QtGui.QColor(245, 245, 245))

    background = background_for_state(state, palette)

    assert background == expected
    assert foreground_for_background(expected, palette) == QtGui.QColor(0, 0, 0)


def test_unchanged_state_uses_normal_theme_background() -> None:
    """UNCHANGED rows have no custom background color."""
    palette = _palette(base=QtGui.QColor(255, 255, 255), text=QtGui.QColor(0, 0, 0), window=QtGui.QColor(245, 245, 245))

    assert background_for_state(DiffState.UNCHANGED, palette) is None


def test_dark_theme_uses_blended_background_instead_of_light_pastel() -> None:
    """Dark themes avoid original pastels because they clash with light text."""
    palette = _palette(base=QtGui.QColor(30, 30, 30), text=QtGui.QColor(240, 240, 240), window=QtGui.QColor(20, 20, 20))

    background = background_for_state(DiffState.ADDED, palette)

    assert background is not None
    assert background != QtGui.QColor(200, 255, 200)
