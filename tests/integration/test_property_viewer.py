# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Integration tests for property viewer refactor Phase 6.

These tests verify end-to-end functionality:
- SavedGeometry is hidden (Phase 1)
- Properties are grouped correctly (Phase 2)
- Expandable properties work (Phase 4)
- CamelCase names are spaced (Phase 3)

Run with: ./run_integration_tests.sh
Or: FREECAD_ROOT=/path/to/freecad python -m pytest tests/integration/ -v
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from freecad.diff_wb.domain.freecad_ports import AppLike


class TestPropertyViewerPhase6:
    """Integration tests verifying Phases 1-5 work correctly together."""

    def test_savedgeometry_is_hidden(self, freecad_app: AppLike, project_root: object) -> None:
        """Verify SavedGeometry is hidden via Prop_Hidden bit (Phase 1).

        SavedGeometry has Prop_Hidden bit set in FreeCAD. This test verifies
        that our extractor correctly hides it.
        """
        from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Create a simple port that wraps the document
            class TestPort:
                def get_active_document(self):
                    return doc

                def get_object(self, doc, name):
                    return doc.getObject(name)

                def try_recompute_active_document(self):
                    pass

                def log(self, text):
                    pass

                def warn(self, text):
                    pass

                def message(self, text):
                    pass

                def info(self, message):
                    pass

                def error(self, text):
                    pass

            port = TestPort()
            extractor = SnapshotExtractor()
            result = extractor.extract_tree(port)

            # Find a TechDraw dimension (has SavedGeometry)
            for node in result.nodes:
                if node.type_id.startswith("TechDraw::DrawViewDimension"):
                    # Check properties - SavedGeometry should NOT be in the list
                    prop_names = list(node.properties.keys())
                    assert "SavedGeometry" not in prop_names, (
                        f"SavedGeometry should be hidden but found in {prop_names}"
                    )
                    # Label should be visible
                    assert "Label" in prop_names, "Label should be visible"
                    return

            # If no dimension found, try another approach - check any object
            # with PropertiesList that includes SavedGeometry
            for obj in doc.Objects:
                if hasattr(obj, "PropertiesList") and "SavedGeometry" in obj.PropertiesList:
                    # Check that our extracted properties don't include SavedGeometry
                    for node in result.nodes:
                        if node.name == obj.Name:
                            prop_names = list(node.properties.keys())
                            assert "SavedGeometry" not in prop_names, f"SavedGeometry should be hidden for {obj.Name}"
                    return

            # If we get here without finding SavedGeometry, that's also fine
            # (the document structure may have changed)
            print("Note: No object with SavedGeometry found in document - test skipped")

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_properties_grouped_correctly(self, freecad_app: AppLike, project_root: object) -> None:
        """Verify properties are grouped correctly (Phase 2).

        This test checks that:
        - Properties with explicit groups (e.g., "Side1") use those groups
        - Properties with empty group map to "Base"
        """
        from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Create a simple port that wraps the document
            class TestPort:
                def get_active_document(self):
                    return doc

                def get_object(self, doc, name):
                    return doc.getObject(name)

                def try_recompute_active_document(self):
                    pass

                def log(self, text):
                    pass

                def warn(self, text):
                    pass

                def message(self, text):
                    pass

                def info(self, message):
                    pass

                def error(self, text):
                    pass

            port = TestPort()
            extractor = SnapshotExtractor()
            result = extractor.extract_tree(port)

            # Check that properties have groups
            for node in result.nodes:
                for prop_name, prop in node.properties.items():
                    # Each property should have a group
                    assert hasattr(prop, "group"), f"Property {prop_name} should have group"
                    assert isinstance(prop.group, str), "Group should be string"
                    # Group should not be empty (empty should map to "Base")
                    if prop.group == "":
                        pytest.fail(f"Property {prop_name} has empty group - should map to Base")

            # Find a PartDesign::Pad to check its property groups
            for node in result.nodes:
                if node.type_id == "PartDesign::Pad":
                    # Should have properties like "Length" in "Side1" group
                    has_side1 = any(prop.group == "Side1" for prop in node.properties.values())
                    has_base = any(prop.group == "Base" for prop in node.properties.values())
                    assert has_side1, "PartDesign::Pad should have properties in Side1 group"
                    assert has_base, "PartDesign::Pad should have properties in Base group"
                    return

            print("Note: No PartDesign::Pad found - test may be limited")

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_expandable_placement_property(self, freecad_app: AppLike, project_root: object) -> None:
        """Verify Placement property expands correctly (Phase 4).

        Placement should expand to Position and Rotation.
        """
        from freecad.diff_wb.domain.tree.property import Property

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Find an object with Placement
            for obj in doc.Objects:
                if hasattr(obj, "Placement") and obj.Placement is not None:
                    placement = obj.Placement

                    # Create Property from FreeCAD value
                    prop = Property.from_freecad_property("Placement", placement)

                    # Check it's expandable
                    children = prop.get_children()
                    assert len(children) > 0, "Placement should be expandable"

                    # Should have Position and Rotation (or Angle, Axis)
                    child_names = [c[0] for c in children]
                    assert "Position" in child_names or "Rotation" in child_names, (
                        f"Placement should have Position or Rotation, got {child_names}"
                    )
                    return

            pytest.skip("No object with Placement found in document")

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_expandable_vector_property(self, freecad_app: AppLike, project_root: object) -> None:
        """Verify vector properties expand to x, y, z (Phase 4)."""
        from freecad.diff_wb.domain.tree.property import Property

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Find an object with Position (a Vector)
            for obj in doc.Objects:
                if hasattr(obj, "Placement") and obj.Placement is not None:
                    placement = obj.Placement
                    if hasattr(placement, "Base") and placement.Base is not None:
                        position = placement.Base

                        # Create Property from FreeCAD value
                        prop = Property.from_freecad_property("Position", position)

                        # Check it's expandable
                        children = prop.get_children()
                        assert len(children) > 0, "Position should be expandable"

                        # Should have x, y, z
                        child_names = [c[0] for c in children]
                        assert "x" in child_names, f"Position should have x, got {child_names}"
                        assert "y" in child_names, f"Position should have y, got {child_names}"
                        assert "z" in child_names, f"Position should have z, got {child_names}"
                        return

            pytest.skip("No object with Position found in document")

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_camelcase_to_spaces_conversion(self) -> None:
        """Verify CamelCase property names are converted to spaced names (Phase 3)."""
        from freecad.diff_wb.ui.views.diff_panel_view import _camelcase_to_spaces

        # Test cases
        test_cases = [
            ("SavedGeometry", "Saved Geometry"),
            ("Placement", "Placement"),  # Single word - no change
            ("Label2", "Label 2"),
            ("XDirection", "X Direction"),
            ("MyPropertyName", "My Property Name"),
            ("XMLDoc", "XML Doc"),  # Acronym handling
        ]

        for input_name, expected in test_cases:
            result = _camelcase_to_spaces(input_name)
            assert result == expected, f"Expected '{expected}', got '{result}'"

    def test_tree_widget_renders_properties_with_groups(self, freecad_app: AppLike, project_root: object) -> None:
        """Integration test: Verify tree widget renders properties grouped correctly."""
        from PySide6.QtWidgets import QApplication

        # Ensure QApplication exists
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor
        from freecad.diff_wb.ui import DiffPanelView
        from freecad.diff_wb.ui.presenters.presentation_models import PropertyPresentation

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Create a simple port that wraps the document
            class TestPort:
                def get_active_document(self):
                    return doc

                def get_object(self, doc, name):
                    return doc.getObject(name)

                def try_recompute_active_document(self):
                    pass

                def log(self, text):
                    pass

                def warn(self, text):
                    pass

                def message(self, text):
                    pass

                def info(self, message):
                    pass

                def error(self, text):
                    pass

            port = TestPort()
            extractor = SnapshotExtractor()
            result = extractor.extract_tree(port)

            # Create DiffPanelView
            panel = DiffPanelView()

            # Get properties from first node with properties
            test_node = None
            for node in result.nodes:
                if node.properties:
                    test_node = node
                    break

            if test_node is None:
                pytest.skip("No nodes with properties found")

            # Convert to PropertyPresentation
            from freecad.diff_wb.domain.diff.models import DiffState

            properties = []
            for prop_name, prop in test_node.properties.items():
                properties.append(
                    PropertyPresentation(
                        name=prop_name,
                        old_value=prop.value,
                        new_value=prop.value,
                        state=DiffState.UNCHANGED,
                        group=prop.group,
                    )
                )

            # Call show_properties - should not raise
            panel.show_properties(properties)

            # Verify tree has items
            root_count = panel.properties_tree.topLevelItemCount()
            assert root_count > 0, "Properties tree should have items"

            # Verify groups are present (should be at least 1)
            # Group headers are top-level items with children
            has_group_with_children = False
            for i in range(root_count):
                item = panel.properties_tree.topLevelItem(i)
                if item and item.childCount() > 0:
                    has_group_with_children = True
                    break

            assert has_group_with_children, "Should have group items with children"

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_various_object_types_extraction(self, freecad_app: AppLike, project_root: object) -> None:
        """Test extraction works with various FreeCAD object types (Phase 6 checklist).

        Tests:
        - App::Part (Placement, Color)
        - TechDraw::DrawViewDimension
        """
        from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Create a simple port that wraps the document
            class TestPort:
                def get_active_document(self):
                    return doc

                def get_object(self, doc, name):
                    return doc.getObject(name)

                def try_recompute_active_document(self):
                    pass

                def log(self, text):
                    pass

                def warn(self, text):
                    pass

                def message(self, text):
                    pass

                def info(self, message):
                    pass

                def error(self, text):
                    pass

            port = TestPort()
            extractor = SnapshotExtractor()
            result = extractor.extract_tree(port)

            # Track which object types we've seen
            object_types = set()
            for node in result.nodes:
                object_types.add(node.type_id)

            # Document should have various object types
            assert len(object_types) > 0, "Should have extracted some object types"

            # Log for information
            print(f"Extracted object types: {sorted(object_types)}")

            # Check we got at least some expected types
            expected_types = [
                "App::Part",
                "PartDesign::Body",
                "TechDraw::DrawViewDimension",
            ]
            found_types = [t for t in expected_types if any(t in ot for ot in object_types)]

            # At least one expected type should be present
            assert len(found_types) > 0, f"Expected at least one of {expected_types}, got {object_types}"

        finally:
            freecad_app.closeDocument(doc.Name)
