# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for utility functions including float formatting
# and float comparison helpers.
"""Unit tests for utility functions in the Diff Workbench."""

import pytest

from freecad.diff_wb.config import FLOAT_PRECISION
from freecad.diff_wb.utils import float_values_equal, format_float


class TestFloatValuesEqual:
    """Tests for float_values_equal utility function."""

    @pytest.mark.parametrize(
        ("v1", "v2", "precision", "expected"),
        [
            (1.0, 1.0, 2, True),
            (1.0, 1.0 + 1e-10, 2, True),
            (1.0, 1.0 + 1e-8, 2, True),
            (1.567, 1.569, 2, True),
            (1.567, 1.579, 2, False),
            (1.0, 1.1, 2, False),
            (0.0, 0.004, 2, True),  # both round to 0.00
            (0.0, 0.005, 2, False),  # 0.00 vs 0.01 (float representation)
            (1e6, 1e6 + 1e-4, 2, True),
            (0.0, 1e-9, 2, True),
            (-1.5, -1.5, 2, True),
            (-1.5, -1.51, 2, False),
            (0.14, 0.16, 2, False),  # 0.14 vs 0.16 — different
        ],
    )
    def test_float_values_equal_various_inputs(self, v1: float, v2: float, precision: int, expected: bool) -> None:
        """Test float_values_equal with various input combinations."""
        assert float_values_equal(v1, v2, precision) is expected

    def test_float_values_equal_uses_default_precision(self) -> None:
        """Test that float_values_equal uses the configured precision."""
        assert float_values_equal(1.0, 1.0 + 1e-8, FLOAT_PRECISION) is True
        assert float_values_equal(1.0, 1.1, FLOAT_PRECISION) is False


class TestFormatFloat:
    """Tests for format_float utility function.

    These tests require Qt runtime and are skipped in unit test environments.
    They are intended for integration tests where Qt is available.
    """

    @pytest.mark.skip(reason="Requires Qt runtime (PyQt5)")
    @pytest.mark.parametrize(
        ("value", "precision", "expected"),
        [
            (1.0, 2, "1.00"),
            (3.14, 2, "3.14"),
            (0.0, 2, "0.00"),
            (-1.5, 2, "-1.50"),
            (1.567, 2, "1.57"),
            (1.564, 2, "1.56"),
            (0.005, 2, "0.00"),
            (123.456, 2, "123.46"),
            (1e6, 2, "1000000.00"),
            (-0.01, 2, "-0.01"),
            (0.0056789, 2, "0.01"),
        ],
    )
    def test_format_float_various_inputs(self, value: float, precision: int, expected: str) -> None:
        """Test format_float with various float values and precisions."""
        result = format_float(value, precision)
        assert result == expected

    @pytest.mark.skip(reason="Requires Qt runtime (PyQt5)")
    def test_format_float_precision_zero(self) -> None:
        """Test format_float with zero precision."""
        result = format_float(3.14159, 0)
        assert result == "3"

    @pytest.mark.skip(reason="Requires Qt runtime (PyQt5)")
    def test_format_float_precision_three(self) -> None:
        """Test format_float with three decimal places."""
        result = format_float(3.14159, 3)
        assert result == "3.142"
