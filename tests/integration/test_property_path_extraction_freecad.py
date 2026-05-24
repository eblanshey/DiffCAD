# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Integration tests for FreeCAD property path extraction.
# Tests verify placement nested expressions, constraint item expressions,
# and quantity primitive dispatch with real FreeCAD runtime.
"""Integration tests for FreeCAD property path extraction.

Phase 5: Focused FreeCAD Integration Validation.

Tests:
- Placement nested expressions captured with normalized keys
- Constraint item expressions captured at root/item level only
- Quantity extraction maps to PrimitiveData with a QUANTITY path
- Root expressions on primitives
- Vector sub-path expressions within Placement

Run with: ./run_integration_tests.sh
"""

from __future__ import annotations

import pytest


class TestPlacementNestedExpressions:
    """Test placement nested expressions are captured with normalized keys."""

    def test_placement_base_x_expression(self, temp_document):
        """Placement.Base.x expression should normalize to 'Base.x' key."""
        from freecad.history_wb.domain.snapshots.gui_extractor import (
            _build_expression_map_for_property,
            _extract_property_value,
        )
        from freecad.history_wb.domain.tree.data_path import PlacementData

        doc = temp_document
        pad = doc.addObject("PartDesign::Pad", "TestPad")
        pad.Length = 10.0
        doc.recompute()

        # Set expression on Placement.Base.x
        pad.setExpression("Placement.Base.x", "10 mm")
        doc.recompute()

        # Test expression map
        expr_map = _build_expression_map_for_property("Placement", pad.ExpressionEngine)
        assert "Base.x" in expr_map
        assert expr_map["Base.x"] == "10 mm"
        # Should NOT have full path as a key
        assert "Placement.Base.x" not in expr_map

        # Test property extraction
        prop = _extract_property_value(pad, "Placement")
        assert prop is not None
        assert isinstance(prop.value, PlacementData)
        assert prop.value.paths["Base.x"].expression == "10 mm"

    def test_placement_multiple_subpath_expressions(self, temp_document):
        """Multiple placement sub-path expressions should all be captured."""
        from freecad.history_wb.domain.snapshots.gui_extractor import (
            _build_expression_map_for_property,
            _extract_property_value,
        )
        from freecad.history_wb.domain.tree.data_path import PlacementData

        doc = temp_document
        pad = doc.addObject("PartDesign::Pad", "TestPad")
        pad.Length = 10.0
        doc.recompute()

        pad.setExpression("Placement.Base.x", "5 mm")
        pad.setExpression("Placement.Base.y", "8 mm")
        doc.recompute()

        expr_map = _build_expression_map_for_property("Placement", pad.ExpressionEngine)
        assert expr_map.get("Base.x") == "5 mm"
        assert expr_map.get("Base.y") == "8 mm"

        # Verify extraction produces PlacementData with correct expressions
        prop = _extract_property_value(pad, "Placement")
        assert prop is not None
        assert isinstance(prop.value, PlacementData)
        assert prop.value.paths["Base.x"].expression == "5 mm"
        assert prop.value.paths["Base.y"].expression == "8 mm"


class TestConstraintItemExpression:
    """Test constraint item expression is captured at root/item level only."""

    def test_constraint_index_expression(self, temp_document):
        """Constraint[0] expression should map to key '[0]', not '[0].Value'."""
        import Sketcher
        from FreeCAD import Vector
        from freecad.history_wb.domain.snapshots.gui_extractor import (
            _build_expression_map_for_property,
        )
        from Part import LineSegment

        doc = temp_document
        sketch = doc.addObject("Sketcher::SketchObject", "TestSketch")
        # Add a simple line geometry
        line = LineSegment(Vector(0, 0, 0), Vector(10, 0, 0))
        sketch.addGeometry(line, False)
        sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 1, 0, 2))
        doc.recompute()

        # Set expression on the first constraint
        sketch.setExpression("Constraints[0]", "5 mm")
        doc.recompute()

        expr_map = _build_expression_map_for_property("Constraints", sketch.ExpressionEngine)
        assert "[0]" in expr_map
        assert expr_map["[0]"] == "5 mm"
        # Verify field-level paths are NOT captured
        assert "[0].Value" not in expr_map
        assert "[0].Type" not in expr_map

        # Verify FreeCAD rejects field-level constraint paths
        with pytest.raises(ValueError, match="Invalid constraint path"):
            sketch.setExpression("Constraints[0].Value", "5 mm")


class TestQuantityExtraction:
    """Test quantity extraction maps to PrimitiveData with QUANTITY path."""

    def test_quantity_property_type(self, temp_document):
        """Quantity property should extract with QUANTITY type and unit field."""
        from freecad.history_wb.domain.snapshots.gui_extractor import (
            _extract_property_value,
        )
        from freecad.history_wb.domain.tree.data_path import PrimitiveData, PropertyPathType

        doc = temp_document
        pad = doc.addObject("PartDesign::Pad", "TestPad")
        pad.Length = "10 mm"
        doc.recompute()

        prop = _extract_property_value(pad, "Length")
        assert prop is not None
        assert isinstance(prop.value, PrimitiveData)
        assert set(prop.value.paths.keys()) == {"."}
        assert prop.value.paths["."].type_ == PropertyPathType.QUANTITY
        assert prop.value.paths["."].value == pytest.approx(10.0)
        assert prop.value.paths["."].unit == "mm"

    def test_quantity_with_expression(self, temp_document):
        """Quantity property with expression should preserve expression on root path."""
        from freecad.history_wb.domain.snapshots.gui_extractor import (
            _build_expression_map_for_property,
            _extract_property_value,
        )
        from freecad.history_wb.domain.tree.data_path import PrimitiveData, PropertyPathType

        doc = temp_document
        pad = doc.addObject("PartDesign::Pad", "TestPad")
        pad.Length = "10 mm"
        doc.recompute()

        pad.setExpression("Length", "5 mm")
        doc.recompute()

        prop = _extract_property_value(pad, "Length")
        assert prop is not None
        assert isinstance(prop.value, PrimitiveData)
        # Quantity stores expression on the same root path "."
        assert prop.value.paths["."].expression == "5 mm"
        assert prop.value.paths["."].type_ == PropertyPathType.QUANTITY
        assert prop.value.paths["."].value == pytest.approx(5.0)
        assert prop.value.paths["."].unit == "mm"

        expr_map = _build_expression_map_for_property("Length", pad.ExpressionEngine)
        assert expr_map.get(".") == "5 mm"


class TestRootExpressionOnPrimitive:
    """Test root expression capture on primitive properties."""

    def test_primitive_with_expression(self, temp_document):
        """Simple property with expression should capture at root '.'."""
        from freecad.history_wb.domain.snapshots.gui_extractor import (
            _build_expression_map_for_property,
            _extract_property_value,
        )
        from freecad.history_wb.domain.tree.data_path import PrimitiveData

        doc = temp_document
        pad = doc.addObject("PartDesign::Pad", "TestPad")
        pad.Length = 10.0
        doc.recompute()

        # Use AllowMultiFace (bool) as a primitive property
        pad.setExpression("AllowMultiFace", "Body.Active")
        doc.recompute()

        prop = _extract_property_value(pad, "AllowMultiFace")
        assert prop is not None
        assert isinstance(prop.value, PrimitiveData)
        assert prop.value.paths["."].expression == "Body.Active"

        expr_map = _build_expression_map_for_property("AllowMultiFace", pad.ExpressionEngine)
        assert expr_map.get(".") == "Body.Active"


class TestVectorSubPathExpressions:
    """Test vector sub-path expressions are captured correctly."""

    def test_vector_subpath_expressions(self, temp_document):
        """Vector sub-path expressions within Placement should be captured."""
        from freecad.history_wb.domain.snapshots.gui_extractor import (
            _extract_property_value,
        )
        from freecad.history_wb.domain.tree.data_path import PlacementData

        doc = temp_document
        obj = doc.addObject("PartDesign::Pad", "TestPad")
        obj.Length = 10.0
        doc.recompute()

        # Set expressions on vector sub-paths of Placement
        obj.setExpression("Placement.Base.x", "5 mm")
        obj.setExpression("Placement.Base.y", "8 mm")
        doc.recompute()

        # Placement extraction produces PlacementData with Base.x/Base.y keys
        prop = _extract_property_value(obj, "Placement")
        assert prop is not None
        assert isinstance(prop.value, PlacementData)
        assert prop.value.paths["Base.x"].expression == "5 mm"
        assert prop.value.paths["Base.y"].expression == "8 mm"


class TestExpressionMapNormalization:
    """Test expression map normalization with dotted vs undotted forms."""

    def test_dotted_wins_duplicate_resolution(self, temp_document):
        """When both dotted and undotted forms exist, dotted should win."""
        from freecad.history_wb.domain.snapshots.gui_extractor import (
            _build_expression_map_for_property,
        )

        doc = temp_document
        pad = doc.addObject("PartDesign::Pad", "TestPad")
        pad.Length = 10.0
        doc.recompute()

        # Set both forms (FreeCAD may store both)
        pad.setExpression("Length", "5 mm")
        pad.setExpression(".Length", "10 mm")
        doc.recompute()

        expr_map = _build_expression_map_for_property("Length", pad.ExpressionEngine)
        # Dotted form wins
        assert expr_map.get(".") == "10 mm"
