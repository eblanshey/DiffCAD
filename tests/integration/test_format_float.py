# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Integration tests for Qt-backed float formatting.

import pytest
from freecad.history_wb.utils import format_float


@pytest.mark.parametrize(
    ("value", "precision", "expected"),
    [
        (1.0, 2, "1.00"),
        (3.14, 2, "3.14"),
        (0.0, 2, "0.00"),
        (-1.5, 2, "-1.50"),
        (1.567, 2, "1.57"),
        (3.14159, 0, "3"),
        (3.14159, 3, "3.142"),
    ],
)
def test_format_float_uses_qt_locale(value: float, precision: int, expected: str) -> None:
    assert format_float(value, precision) == expected
