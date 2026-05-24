# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for float comparison helper functions.
"""Unit tests for utility functions in the Diff Workbench."""

import pytest
from freecad.history_wb.domain.config import FLOAT_PRECISION
from freecad.history_wb.utils import float_values_equal


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
