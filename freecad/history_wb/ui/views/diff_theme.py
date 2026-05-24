"""File responsibility: Theme-aware diff item coloring for Qt tree views."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, cast

from ...domain.diff.models import DiffState
from ...qt import QtCore, QtGui, QtWidgets


__all__ = [
    "DIFF_STATE_ROLE",
    "DiffItemDelegate",
    "background_for_state",
    "foreground_for_background",
]


# Custom model role used by DiffItemDelegate. Qt's built-in BackgroundRole can be
# ignored by aggressive application stylesheets, so we store semantic state and
# let the delegate paint it directly.
DIFF_STATE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 20

# Minimum contrast target for normal-sized UI text. This follows the WCAG AA
# 4.5:1 guidance and keeps diff labels readable across light and dark themes.
_MIN_CONTRAST = 4.5

# Luminance below this value strongly suggests a dark item-view background.
_DARK_LUMINANCE_THRESHOLD = 0.35

# Luminance above this value strongly suggests light text. Combined with a dark
# background, this is the most reliable signal for dark FreeCAD stylesheets.
_LIGHT_TEXT_LUMINANCE_THRESHOLD = 0.65

# First-pass accent blend for dark themes. Light themes use direct pastel
# colors so they match the original bright diff highlights with black text.
_DARK_ACCENT_BLEND = 0.38

# Fallback blend ratios move gradually toward pure accent color until the chosen
# text color reaches the contrast target.
_CONTRAST_FALLBACK_BLEND_RATIOS = (0.45, 0.52, 0.60, 0.70, 0.82, 1.0)
_LAST_FALLBACK_BLEND = 0.52

# Diff accents are paired as (light-theme accent, dark-theme accent). Light
# variants preserve the original bright pastel highlights. Dark variants are
# brighter saturated targets so they remain visible when blended into dark
# palettes.
_ADDED_LIGHT_ACCENT = QtGui.QColor(200, 255, 200)
_ADDED_DARK_ACCENT = QtGui.QColor(48, 219, 91)
_DELETED_LIGHT_ACCENT = QtGui.QColor(255, 200, 200)
_DELETED_DARK_ACCENT = QtGui.QColor(255, 105, 97)
_MODIFIED_LIGHT_ACCENT = QtGui.QColor(200, 200, 255)
_MODIFIED_DARK_ACCENT = QtGui.QColor(116, 192, 252)

_ColorKey = tuple[int, int, int]
_PaletteKey = tuple[_ColorKey, _ColorKey, _ColorKey]


@dataclass(frozen=True)
class _ThemeColors:
    """Palette colors used as stable inputs for diff color generation."""

    base: QtGui.QColor
    text: QtGui.QColor
    window: QtGui.QColor


class DiffItemDelegate(QtWidgets.QStyledItemDelegate):
    """Paint diff item backgrounds with contrast-safe foreground colors."""

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> None:  # type: ignore[override]
        """Paint one tree cell using semantic diff colors when present."""
        state = index.data(DIFF_STATE_ROLE)
        if not isinstance(state, DiffState):
            super().paint(painter, option, index)
            return

        themed_option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(themed_option, index)

        # PySide exposes these attributes at runtime, but current stubs omit
        # them. Keep the cast local so the rest of the module remains typed.
        themed_option_data = cast(Any, themed_option)
        background = background_for_state(state, themed_option_data.palette)
        if background is None:
            super().paint(painter, option, index)
            return

        foreground = foreground_for_background(background, themed_option_data.palette)

        # Set both background and text roles on the style option. This lets the
        # current Qt style keep selection, padding, icons, and branch painting
        # while overriding only diff-specific colors.
        themed_option_data.backgroundBrush = QtGui.QBrush(background)
        themed_option_data.palette.setColor(QtGui.QPalette.ColorRole.Text, foreground)
        themed_option_data.palette.setColor(QtGui.QPalette.ColorRole.WindowText, foreground)
        themed_option_data.palette.setColor(QtGui.QPalette.ColorRole.Highlight, background)
        themed_option_data.palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, foreground)
        super().paint(painter, themed_option, index)


def background_for_state(state: DiffState, palette: QtGui.QPalette) -> QtGui.QColor | None:
    """Return theme-aware background color for diff state.

    Unchanged rows return None so they inherit the normal theme background.
    """
    palette_key = _palette_key(palette)
    return _cached_background_for_state(state, palette_key)


@lru_cache(maxsize=96)
def _cached_background_for_state(state: DiffState, palette_key: _PaletteKey) -> QtGui.QColor | None:
    """Return cached background for state and palette colors.

    Painting can call this once per visible cell, while many cells share the
    same application palette and diff state. Cache prevents repeating WCAG math.
    """
    palette = _palette_from_key(palette_key)
    if state == DiffState.ADDED:
        return _state_background(palette, _ADDED_LIGHT_ACCENT, _ADDED_DARK_ACCENT)
    if state == DiffState.DELETED:
        return _state_background(palette, _DELETED_LIGHT_ACCENT, _DELETED_DARK_ACCENT)
    if state == DiffState.MODIFIED:
        return _state_background(palette, _MODIFIED_LIGHT_ACCENT, _MODIFIED_DARK_ACCENT)
    return None


def foreground_for_background(background: QtGui.QColor, palette: QtGui.QPalette) -> QtGui.QColor:
    """Return readable text color for a background and current palette.

    Prefer the theme text color when possible, then fall back to black or white.
    """
    return _cached_foreground_for_background(_color_key(background), _palette_key(palette))


@lru_cache(maxsize=256)
def _cached_foreground_for_background(background_key: _ColorKey, palette_key: _PaletteKey) -> QtGui.QColor:
    """Return cached foreground for background and palette colors."""
    background = _color_from_key(background_key)
    colors = _ThemeColors(
        base=_color_from_key(palette_key[0]),
        text=_color_from_key(palette_key[1]),
        window=_color_from_key(palette_key[2]),
    )
    if not _theme_is_dark(colors):
        return QtGui.QColor(0, 0, 0)

    palette_text = _color_from_key(palette_key[1])
    black = QtGui.QColor(0, 0, 0)
    white = QtGui.QColor(255, 255, 255)
    candidates = [palette_text, black, white]
    best = max(candidates, key=lambda color: _contrast_ratio(color, background))
    if _contrast_ratio(best, background) >= _MIN_CONTRAST:
        return best
    return black if _contrast_ratio(black, background) > _contrast_ratio(white, background) else white


def _state_background(palette: QtGui.QPalette, light_accent: QtGui.QColor, dark_accent: QtGui.QColor) -> QtGui.QColor:
    """Blend state accent with theme base and adjust until text is readable."""
    colors = _theme_colors(palette)
    if _theme_is_dark(colors):
        accent = dark_accent
        initial = _blend(colors.base, accent, _DARK_ACCENT_BLEND)
    else:
        accent = light_accent
        initial = light_accent
    foreground = foreground_for_background(initial, palette)
    if _contrast_ratio(foreground, initial) >= _MIN_CONTRAST:
        return initial
    return _find_contrast_background(colors.base, accent, foreground)


def _theme_colors(palette: QtGui.QPalette) -> _ThemeColors:
    """Extract reliable palette colors for item-view backgrounds and text."""
    base = palette.color(QtGui.QPalette.ColorRole.Base)
    if not base.isValid():
        base = palette.color(QtGui.QPalette.ColorRole.Window)
    return _ThemeColors(
        base=base,
        text=palette.color(QtGui.QPalette.ColorRole.Text),
        window=palette.color(QtGui.QPalette.ColorRole.Window),
    )


def _theme_is_dark(colors: _ThemeColors) -> bool:
    """Return true when palette represents dark-theme item rendering.

    Some FreeCAD stylesheets report surprising Base colors for item views, so
    use base, window, and text luminance. A theme is dark only when item and
    window backgrounds are both dark and text is light. Light themes therefore
    keep pastel backgrounds with black text even if one palette role misleads.
    """
    base_is_dark = _is_dark(colors.base)
    window_is_dark = _is_dark(colors.window)
    text_is_light = _relative_luminance(colors.text) > _LIGHT_TEXT_LUMINANCE_THRESHOLD
    return base_is_dark and window_is_dark and text_is_light


def _palette_key(palette: QtGui.QPalette) -> _PaletteKey:
    """Create hashable cache key from palette colors that affect output."""
    colors = _theme_colors(palette)
    return _color_key(colors.base), _color_key(colors.text), _color_key(colors.window)


def _palette_from_key(palette_key: _PaletteKey) -> QtGui.QPalette:
    """Build minimal palette from cache key for existing color helpers."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Base, _color_from_key(palette_key[0]))
    palette.setColor(QtGui.QPalette.ColorRole.Text, _color_from_key(palette_key[1]))
    palette.setColor(QtGui.QPalette.ColorRole.Window, _color_from_key(palette_key[2]))
    return palette


def _color_key(color: QtGui.QColor) -> _ColorKey:
    """Create hashable cache key for opaque RGB color values."""
    return color.red(), color.green(), color.blue()


def _color_from_key(color_key: _ColorKey) -> QtGui.QColor:
    """Recreate QColor from an RGB cache key."""
    red, green, blue = color_key
    return QtGui.QColor(red, green, blue)


def _is_dark(color: QtGui.QColor) -> bool:
    """Return true when color behaves like dark theme background."""
    return _relative_luminance(color) < _DARK_LUMINANCE_THRESHOLD


def _find_contrast_background(base: QtGui.QColor, accent: QtGui.QColor, foreground: QtGui.QColor) -> QtGui.QColor:
    """Try stronger accent blends until foreground contrast is sufficient."""
    for ratio in _CONTRAST_FALLBACK_BLEND_RATIOS:
        candidate = _blend(base, accent, ratio)
        if _contrast_ratio(foreground, candidate) >= _MIN_CONTRAST:
            return candidate
    return _blend(base, accent, _LAST_FALLBACK_BLEND)


def _blend(base: QtGui.QColor, accent: QtGui.QColor, accent_ratio: float) -> QtGui.QColor:
    """Blend two RGB colors using accent_ratio as the accent weight."""
    base_ratio = 1.0 - accent_ratio
    return QtGui.QColor(
        round(base.red() * base_ratio + accent.red() * accent_ratio),
        round(base.green() * base_ratio + accent.green() * accent_ratio),
        round(base.blue() * base_ratio + accent.blue() * accent_ratio),
    )


def _contrast_ratio(foreground: QtGui.QColor, background: QtGui.QColor) -> float:
    """Calculate WCAG contrast ratio between two colors."""
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(color: QtGui.QColor) -> float:
    """Calculate WCAG relative luminance for an sRGB color."""
    red = _linear_channel(color.redF())
    green = _linear_channel(color.greenF())
    blue = _linear_channel(color.blueF())
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _linear_channel(value: float) -> float:
    """Convert one sRGB color channel to linear-light value."""
    if value <= 0.03928:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4
