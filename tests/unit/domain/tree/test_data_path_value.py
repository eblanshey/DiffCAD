# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for PropertyPathValue including factory creation
# from Python values and precision-based float equality behavior.
"""Unit tests for PropertyPathValue class."""

import pytest

from freecad.diff_wb.domain.tree.data_path import PropertyPathType, PropertyPathValue


class TestPropertyPathValueFromPython:
    """Tests for PropertyPathValue.from_python factory method."""

    @pytest.mark.parametrize(
        ("value", "expected_type", "expected_value"),
        [
            (None, PropertyPathType.NULL, None),
            (True, PropertyPathType.BOOL, True),
            (False, PropertyPathType.BOOL, False),
            (42, PropertyPathType.INT, 42),
            (-7, PropertyPathType.INT, -7),
            (3.14, PropertyPathType.FLOAT, 3.14),
            (0.0, PropertyPathType.FLOAT, 0.0),
            ("hello", PropertyPathType.STRING, "hello"),
            ("", PropertyPathType.STRING, ""),
        ],
    )
    def test_from_python_dispatches_correct_type(
        self, value: object, expected_type: PropertyPathType, expected_value: object
    ) -> None:
        """Test that from_python creates the correct PropertyPathType for various inputs."""
        pv = PropertyPathValue.from_python(value)
        assert pv.type_ == expected_type
        assert pv.value == expected_value
        assert pv.expression is None

    def test_from_python_with_expression(self) -> None:
        """Test that expression is preserved when provided."""
        pv = PropertyPathValue.from_python(42, expression="Sketch001.X")
        assert pv.type_ == PropertyPathType.INT
        assert pv.value == 42
        assert pv.expression == "Sketch001.X"

    def test_from_python_bool_before_int(self) -> None:
        """Test that booleans are dispatched before integers (bool is subclass of int)."""
        pv_true = PropertyPathValue.from_python(True)
        assert pv_true.type_ == PropertyPathType.BOOL

        pv_false = PropertyPathValue.from_python(False)
        assert pv_false.type_ == PropertyPathType.BOOL


class TestPropertyPathValueEquality:
    """Tests for PropertyPathValue equality with precision-based float comparison."""

    def test_same_type_and_value_are_equal(self) -> None:
        """Test equality for identical values."""
        pv1 = PropertyPathValue(PropertyPathType.INT, 42)
        pv2 = PropertyPathValue(PropertyPathType.INT, 42)
        assert pv1 == pv2

    def test_different_type_not_equal(self) -> None:
        """Test that values with different types are not equal."""
        pv1 = PropertyPathValue(PropertyPathType.INT, 42)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 42.0)
        assert pv1 != pv2

    def test_different_value_not_equal(self) -> None:
        """Test that values with different values are not equal."""
        pv1 = PropertyPathValue(PropertyPathType.INT, 42)
        pv2 = PropertyPathValue(PropertyPathType.INT, 43)
        assert pv1 != pv2

    @pytest.mark.parametrize(
        ("v1", "v2", "expected_equal"),
        [
            (1.0, 1.0 + 1e-10, True),  # both round to 1.00 at precision 2
            (1.0, 1.0 + 1e-8, True),  # both round to 1.00 at precision 2
            (0.0, 1e-10, True),  # both round to 0.00 at precision 2
            (1e6, 1e6 + 1e-4, True),  # both round to 1000000.00 at precision 2
            (1e6, 1e6 + 0.001, True),  # both round to 1000000.00 at precision 2
            (1e6, 1e6 + 0.01, False),  # 1000000.00 vs 1000000.01 — different
            (1.567, 1.569, True),  # both round to 1.57
            (1.567, 1.579, False),  # 1.57 vs 1.58 — different
            (1.0, 1.1, False),  # 1.00 vs 1.10 — different
            (0.0, 0.004, True),  # both round to 0.00 at precision 2
            (0.0, 0.005, False),  # 0.00 vs 0.01 due to float representation — different
        ],
    )
    def test_float_equality_with_precision(self, v1: float, v2: float, expected_equal: bool) -> None:
        """Test float equality uses precision-based rounding (default 2 decimal places)."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, v1)
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, v2)
        if expected_equal:
            assert pv1 == pv2
        else:
            assert pv1 != pv2

    def test_different_expression_not_equal(self) -> None:
        """Test that same values with different expressions are not equal."""
        pv1 = PropertyPathValue(PropertyPathType.INT, 42, expression="A")
        pv2 = PropertyPathValue(PropertyPathType.INT, 42, expression="B")
        assert pv1 != pv2

    def test_expression_vs_none_not_equal(self) -> None:
        """Test that value with expression differs from value without."""
        pv1 = PropertyPathValue(PropertyPathType.INT, 42, expression="Some.Expression")
        pv2 = PropertyPathValue(PropertyPathType.INT, 42)
        assert pv1 != pv2

    def test_same_expression_same_value_equal(self) -> None:
        """Test that same value and expression are equal."""
        pv1 = PropertyPathValue(PropertyPathType.STRING, "hello", expression="Doc.Name")
        pv2 = PropertyPathValue(PropertyPathType.STRING, "hello", expression="Doc.Name")
        assert pv1 == pv2

    def test_float_expression_affects_equality(self) -> None:
        """Test that float values with different expressions are not equal."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0, expression="A")
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.0 + 1e-10, expression="B")
        assert pv1 != pv2

    def test_none_values_equal(self) -> None:
        """Test that None values are equal."""
        pv1 = PropertyPathValue(PropertyPathType.NULL, None)
        pv2 = PropertyPathValue(PropertyPathType.NULL, None)
        assert pv1 == pv2

    def test_bool_values_equal(self) -> None:
        """Test that bool values are equal."""
        pv1 = PropertyPathValue(PropertyPathType.BOOL, True)
        pv2 = PropertyPathValue(PropertyPathType.BOOL, True)
        assert pv1 == pv2

    def test_string_values_equal(self) -> None:
        """Test that string values are equal."""
        pv1 = PropertyPathValue(PropertyPathType.STRING, "hello")
        pv2 = PropertyPathValue(PropertyPathType.STRING, "hello")
        assert pv1 == pv2

    def test_not_implemented_for_non_value(self) -> None:
        """Test that comparing with non-PropertyPathValue returns NotImplemented."""
        pv = PropertyPathValue(PropertyPathType.INT, 42)
        result = pv.__eq__("not a value")
        assert result is NotImplemented
